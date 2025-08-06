"""
Configuration manager for the Fantasy Draft Engine.

This module provides centralized configuration management that coordinates
all configuration classes and provides a unified interface for the application.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import logging

from .base_config import BaseConfig
from .data_config import DataConfig
from .league_config import LeagueConfig
from .model_config import ModelConfig
from .position_config import PositionConfig
from .scoring_config import ScoringConfig

# Use absolute imports to avoid relative import issues
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from ..core.error_handling import ConfigurationError
from ..core.logging_config import get_logger


class ConfigManager:
    """
    Central configuration manager that coordinates all configuration classes.
    
    This class provides a unified interface to access all configuration
    settings and ensures consistency across different configuration domains.
    """
    
    def __init__(self, environment: str = 'development', 
                 config_dir: Optional[Union[str, Path]] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the configuration manager.
        
        Args:
            environment: Environment name ('development', 'production', 'test')
            config_dir: Optional directory containing configuration files
            logger: Optional logger instance
        """
        self.environment = environment
        self.logger = logger or get_logger(f"{self.__class__.__name__}_{environment}")
        
        # Default config directory
        if config_dir is None:
            # Look for config files in project root
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent.parent
            config_dir = project_root / 'config'
        
        self.config_dir = Path(config_dir)
        
        # Initialize all configuration classes
        self._initialize_configs()
        
        # Load environment-specific overrides
        self._load_environment_configs()
        
        # Validate cross-configuration consistency
        self._validate_consistency()
        
        self.logger.info(f"Configuration manager initialized for environment: {environment}")
    
    def _initialize_configs(self) -> None:
        """Initialize all configuration class instances."""
        try:
            self.data = DataConfig(environment=self.environment, logger=self.logger)
            self.league = LeagueConfig(environment=self.environment, logger=self.logger)
            self.model = ModelConfig(environment=self.environment, logger=self.logger)
            self.position = PositionConfig(environment=self.environment, logger=self.logger)
            self.scoring = ScoringConfig(environment=self.environment, logger=self.logger)
            
            self.logger.info("All configuration classes initialized successfully")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize configuration classes: {str(e)}")
    
    def _load_environment_configs(self) -> None:
        """Load environment-specific configuration overrides."""
        try:
            # Load from environment variables
            self._load_env_variables()
            
            # Load from configuration files
            self._load_config_files()
            
        except Exception as e:
            self.logger.warning(f"Failed to load environment configurations: {e}")
    
    def _load_env_variables(self) -> None:
        """Load configuration from environment variables."""
        config_classes = {
            'DATA': self.data,
            'LEAGUE': self.league,
            'MODEL': self.model,
            'POSITION': self.position,
            'SCORING': self.scoring
        }
        
        for prefix, config_obj in config_classes.items():
            try:
                config_obj.load_from_env(prefix=f"FF_{prefix}_")
            except Exception as e:
                self.logger.debug(f"No environment variables found for {prefix}: {e}")
    
    def _load_config_files(self) -> None:
        """Load configuration from files if they exist."""
        config_files = {
            'data': (self.data, 'data_config'),
            'league': (self.league, 'league_config'),
            'model': (self.model, 'model_config'),
            'position': (self.position, 'position_config'),
            'scoring': (self.scoring, 'scoring_config')
        }
        
        for config_name, (config_obj, filename) in config_files.items():
            # Try both YAML and JSON formats
            for ext in ['.yaml', '.yml', '.json']:
                config_file = self.config_dir / f"{filename}{ext}"
                if config_file.exists():
                    try:
                        config_obj.load_from_file(config_file, merge=True)
                        self.logger.info(f"Loaded {config_name} configuration from {config_file}")
                        break
                    except Exception as e:
                        self.logger.warning(f"Failed to load {config_file}: {e}")
            
            # Try environment-specific files
            env_file = self.config_dir / f"{filename}_{self.environment}.yaml"
            if env_file.exists():
                try:
                    config_obj.load_from_file(env_file, merge=True)
                    self.logger.info(f"Loaded environment-specific {config_name} config from {env_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to load environment config {env_file}: {e}")
    
    def _validate_consistency(self) -> None:
        """Validate consistency across different configuration domains."""
        try:
            # Validate position consistency
            self._validate_position_consistency()
            
            # Validate scoring system consistency
            self._validate_scoring_consistency()
            
            # Validate model-data consistency
            self._validate_model_data_consistency()
            
            self.logger.info("Configuration consistency validation passed")
            
        except Exception as e:
            raise ConfigurationError(f"Configuration consistency validation failed: {str(e)}")
    
    def _validate_position_consistency(self) -> None:
        """Validate that positions are consistent across all configurations."""
        # Get positions from different configs
        data_positions = set(self.data.positions)
        core_positions = set(self.data.core_positions)
        position_positions = set(self.position.positions)
        model_positions = set(self.model.get_supported_positions())
        
        # Check that core positions are subset of all positions
        if not core_positions.issubset(data_positions):
            raise ValueError("Core positions must be subset of all positions")
        
        # Check that position config covers all positions
        if not data_positions.issubset(position_positions):
            raise ValueError("Position config must cover all data positions")
        
        # Check that model config covers core positions
        if not core_positions.issubset(model_positions):
            raise ValueError("Model config must cover all core positions")
    
    def _validate_scoring_consistency(self) -> None:
        """Validate scoring system consistency."""
        # Check that league PPR setting matches scoring system
        league_ppr = self.league.ppr_scoring
        scoring_system = self.scoring.get_scoring_system()
        
        expected_ppr = scoring_system.get('receptions', 0)
        
        if abs(league_ppr - expected_ppr) > 0.01:
            self.logger.warning(
                f"PPR mismatch: league={league_ppr}, scoring={expected_ppr}. "
                f"Using league setting."
            )
            # Override scoring system with league setting
            self.scoring.fantasy_points['receptions'] = league_ppr
    
    def _validate_model_data_consistency(self) -> None:
        """Validate model and data configuration consistency."""
        # Check that training years don't exceed data years
        training_years = self.data.get_training_years()
        data_years = self.data.get_years_range()
        
        if not set(training_years).issubset(set(data_years)):
            raise ValueError("Training years must be subset of data years")
        
        # Check that inference year is valid
        inference_year = self.data.inference_data_year
        if inference_year > self.data.data_end_year:
            raise ValueError("Inference year cannot exceed data end year")
    
    def get_config(self, domain: str) -> BaseConfig:
        """
        Get configuration object for a specific domain.
        
        Args:
            domain: Configuration domain ('data', 'league', 'model', 'position', 'scoring')
            
        Returns:
            Configuration object for the specified domain
        """
        domain_mapping = {
            'data': self.data,
            'league': self.league,
            'model': self.model,
            'position': self.position,
            'scoring': self.scoring
        }
        
        if domain not in domain_mapping:
            raise ValueError(f"Unknown configuration domain: {domain}")
        
        return domain_mapping[domain]
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation across domains.
        
        Args:
            key: Configuration key in format 'domain.key' or 'domain.section.key'
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        parts = key.split('.')
        
        if len(parts) < 2:
            raise ValueError(f"Configuration key must include domain: {key}")
        
        domain = parts[0]
        config_key = '.'.join(parts[1:])
        
        try:
            config_obj = self.get_config(domain)
            return config_obj.get(config_key, default)
        except Exception:
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            key: Configuration key in format 'domain.key'
            value: Value to set
        """
        parts = key.split('.')
        
        if len(parts) < 2:
            raise ValueError(f"Configuration key must include domain: {key}")
        
        domain = parts[0]
        config_key = '.'.join(parts[1:])
        
        config_obj = self.get_config(domain)
        config_obj.set(config_key, value)
    
    def get_all_positions(self) -> List[str]:
        """Get list of all supported positions."""
        return self.position.get_all_positions()
    
    def get_core_positions(self) -> List[str]:
        """Get list of core positions with full feature engineering."""
        return self.data.core_positions.copy()
    
    def get_league_summary(self) -> Dict[str, Any]:
        """Get summary of league configuration."""
        return self.league.get_league_summary()
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of data configuration."""
        return {
            'data_years': f"{self.data.data_start_year}-{self.data.data_end_year}",
            'training_years': f"{self.data.data_start_year}-{self.data.training_data_end_year}",
            'inference_year': self.data.inference_data_year,
            'current_season': self.data.current_season,
            'positions': self.data.positions,
            'core_positions': self.data.core_positions
        }
    
    def get_model_summary(self) -> Dict[str, Any]:
        """Get summary of model configuration."""
        return {
            'model_types': self.model.get_available_model_types(),
            'supported_positions': self.model.get_supported_positions(),
            'default_weights': self.model.model_weights,
            'feature_selection_enabled': self.model.should_use_feature_selection(),
            'hyperopt_enabled': self.model.should_optimize_hyperparameters()
        }
    
    def export_all_configs(self, output_dir: Union[str, Path], 
                          format: str = 'yaml') -> List[Path]:
        """
        Export all configurations to files.
        
        Args:
            output_dir: Directory to save configuration files
            format: File format ('yaml' or 'json')
            
        Returns:
            List of saved file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        configs = {
            'data_config': self.data,
            'league_config': self.league,
            'model_config': self.model,
            'position_config': self.position,
            'scoring_config': self.scoring
        }
        
        for filename, config_obj in configs.items():
            file_path = output_dir / f"{filename}_{self.environment}.{format}"
            config_obj.save_to_file(file_path, format=format)
            saved_files.append(file_path)
        
        # Also save a combined summary
        summary_path = output_dir / f"config_summary_{self.environment}.{format}"
        summary_data = {
            'environment': self.environment,
            'data': self.get_data_summary(),
            'league': self.get_league_summary(),
            'model': self.get_model_summary()
        }
        
        if format == 'yaml':
            import yaml
            with open(summary_path, 'w') as f:
                yaml.dump(summary_data, f, default_flow_style=False)
        else:
            import json
            with open(summary_path, 'w') as f:
                json.dump(summary_data, f, indent=2)
        
        saved_files.append(summary_path)
        
        self.logger.info(f"Exported all configurations to {output_dir}")
        return saved_files
    
    def reload_configs(self) -> None:
        """Reload all configurations from files and environment variables."""
        self.logger.info("Reloading all configurations...")
        
        # Re-initialize all configs
        self._initialize_configs()
        
        # Re-load environment-specific overrides
        self._load_environment_configs()
        
        # Re-validate consistency
        self._validate_consistency()
        
        self.logger.info("Configuration reload completed")
    
    def get_environment(self) -> str:
        """Get current environment."""
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
        """String representation of the configuration manager."""
        return f"ConfigManager(environment='{self.environment}')"


# Global configuration manager instance
_global_config_manager: Optional[ConfigManager] = None


def get_config(environment: str = None, **kwargs) -> ConfigManager:
    """
    Get the global configuration manager instance.
    
    Args:
        environment: Environment name (if None, uses current environment)
        **kwargs: Additional arguments for ConfigManager
        
    Returns:
        ConfigManager instance
    """
    global _global_config_manager
    
    if _global_config_manager is None or (environment and environment != _global_config_manager.environment):
        # Determine environment
        if environment is None:
            environment = os.environ.get('FF_ENVIRONMENT', 'development')
        
        _global_config_manager = ConfigManager(environment=environment, **kwargs)
    
    return _global_config_manager


def reload_config() -> None:
    """Reload the global configuration."""
    global _global_config_manager
    
    if _global_config_manager is not None:
        _global_config_manager.reload_configs()


def reset_config() -> None:
    """Reset the global configuration (forces reinitialization)."""
    global _global_config_manager
    _global_config_manager = None