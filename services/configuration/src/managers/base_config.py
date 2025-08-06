"""
Base configuration class for the Fantasy Draft Engine.

This module provides the foundation for all configuration classes with
validation, serialization, and environment-specific loading capabilities.
"""

import os
import json
import yaml
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
from dataclasses import dataclass, asdict, fields
import logging

from ..core.error_handling import ConfigurationError
from ..core.logging_config import get_logger


class BaseConfig(ABC):
    """
    Abstract base class for all configuration classes.
    
    This class provides common functionality for configuration validation,
    serialization, and environment-specific overrides.
    """
    
    def __init__(self, environment: str = 'development', logger: Optional[logging.Logger] = None):
        """
        Initialize the base configuration.
        
        Args:
            environment: Environment name (development, production, test)
            logger: Optional logger instance
        """
        self.environment = environment
        self.logger = logger or get_logger(f"{self.__class__.__name__}_{environment}")
        self._initialized = False
        self._overrides = {}
        
        # Initialize configuration
        self._initialize()
        self._validate()
        self._initialized = True
        
        self.logger.info(f"Initialized {self.__class__.__name__} for environment: {environment}")
    
    @abstractmethod
    def _initialize(self) -> None:
        """Initialize configuration values. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _validate(self) -> None:
        """Validate configuration values. Must be implemented by subclasses."""
        pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value with optional default.
        
        Args:
            key: Configuration key (supports dot notation like 'section.subsection.key')
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        # Check for overrides first
        if key in self._overrides:
            return self._overrides[key]
        
        # Navigate nested keys using dot notation
        keys = key.split('.')
        value = self
        
        try:
            for k in keys:
                if hasattr(value, k):
                    value = getattr(value, k)
                elif isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
        except (AttributeError, KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value override.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self._overrides[key] = value
        self.logger.debug(f"Set override: {key} = {value}")
    
    def load_from_file(self, file_path: Union[str, Path], 
                      merge: bool = True) -> None:
        """
        Load configuration from a file.
        
        Args:
            file_path: Path to configuration file (JSON or YAML)
            merge: Whether to merge with existing config or replace
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif file_path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    raise ConfigurationError(f"Unsupported file format: {file_path.suffix}")
            
            if merge:
                self._merge_config(data)
            else:
                self._replace_config(data)
            
            self.logger.info(f"Loaded configuration from {file_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {file_path}: {str(e)}")
    
    def load_from_env(self, prefix: Optional[str] = None) -> None:
        """
        Load configuration from environment variables.
        
        Args:
            prefix: Optional prefix for environment variables
        """
        if prefix is None:
            prefix = f"{self.__class__.__name__.upper().replace('CONFIG', '')}_"
        
        env_vars = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                
                # Try to parse as JSON for complex values
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # Use string value if JSON parsing fails
                    parsed_value = value
                
                env_vars[config_key] = parsed_value
        
        if env_vars:
            self._merge_config(env_vars)
            self.logger.info(f"Loaded {len(env_vars)} environment variables with prefix {prefix}")
    
    def _merge_config(self, data: Dict[str, Any]) -> None:
        """
        Merge configuration data with existing configuration.
        
        Args:
            data: Configuration data to merge
        """
        for key, value in data.items():
            self.set(key, value)
    
    def _replace_config(self, data: Dict[str, Any]) -> None:
        """
        Replace entire configuration with new data.
        
        Args:
            data: Configuration data to use
        """
        self._overrides = data.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        result = {}
        
        # Get all attributes that don't start with underscore
        for attr_name in dir(self):
            if not attr_name.startswith('_') and not callable(getattr(self, attr_name)):
                attr_value = getattr(self, attr_name)
                
                # Skip logger and other non-serializable attributes
                if attr_name in ['logger', 'environment']:
                    continue
                
                result[attr_name] = attr_value
        
        # Apply overrides
        result.update(self._overrides)
        
        return result
    
    def save_to_file(self, file_path: Union[str, Path], 
                    format: str = 'yaml') -> None:
        """
        Save configuration to file.
        
        Args:
            file_path: Path to save configuration
            format: File format ('yaml' or 'json')
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = self.to_dict()
        
        try:
            with open(file_path, 'w') as f:
                if format.lower() == 'yaml':
                    yaml.dump(data, f, default_flow_style=False)
                elif format.lower() == 'json':
                    json.dump(data, f, indent=2)
                else:
                    raise ConfigurationError(f"Unsupported format: {format}")
            
            self.logger.info(f"Saved configuration to {file_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration to {file_path}: {str(e)}")
    
    def validate_required_fields(self, required_fields: List[str]) -> None:
        """
        Validate that required fields are present and not None.
        
        Args:
            required_fields: List of required field names
            
        Raises:
            ConfigurationError: If required fields are missing
        """
        missing_fields = []
        
        for field in required_fields:
            value = self.get(field)
            if value is None:
                missing_fields.append(field)
        
        if missing_fields:
            raise ConfigurationError(
                f"Missing required configuration fields in {self.__class__.__name__}: {missing_fields}"
            )
    
    def validate_types(self, type_mapping: Dict[str, type]) -> None:
        """
        Validate that configuration values have expected types.
        
        Args:
            type_mapping: Dictionary mapping field names to expected types
            
        Raises:
            ConfigurationError: If types don't match expectations
        """
        type_errors = []
        
        for field, expected_type in type_mapping.items():
            value = self.get(field)
            if value is not None and not isinstance(value, expected_type):
                type_errors.append(f"{field}: expected {expected_type.__name__}, got {type(value).__name__}")
        
        if type_errors:
            raise ConfigurationError(
                f"Type validation errors in {self.__class__.__name__}: {'; '.join(type_errors)}"
            )
    
    def validate_ranges(self, range_mapping: Dict[str, tuple]) -> None:
        """
        Validate that numeric values are within expected ranges.
        
        Args:
            range_mapping: Dictionary mapping field names to (min, max) tuples
            
        Raises:
            ConfigurationError: If values are out of range
        """
        range_errors = []
        
        for field, (min_val, max_val) in range_mapping.items():
            value = self.get(field)
            if value is not None and isinstance(value, (int, float)):
                if min_val is not None and value < min_val:
                    range_errors.append(f"{field}: {value} < minimum {min_val}")
                if max_val is not None and value > max_val:
                    range_errors.append(f"{field}: {value} > maximum {max_val}")
        
        if range_errors:
            raise ConfigurationError(
                f"Range validation errors in {self.__class__.__name__}: {'; '.join(range_errors)}"
            )
    
    def get_environment(self) -> str:
        """Get the current environment."""
        return self.environment
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == 'development'
    
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.environment.lower() == 'test'
    
    def __repr__(self) -> str:
        """String representation of the configuration."""
        return f"{self.__class__.__name__}(environment='{self.environment}')"
    
    def __str__(self) -> str:
        """String representation showing key configuration values."""
        key_values = []
        config_dict = self.to_dict()
        
        # Show first few key-value pairs
        for i, (key, value) in enumerate(config_dict.items()):
            if i >= 5:  # Limit to first 5 items
                key_values.append("...")
                break
            key_values.append(f"{key}={value}")
        
        return f"{self.__class__.__name__}({', '.join(key_values)})"