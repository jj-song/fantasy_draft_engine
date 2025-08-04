"""
Factory pattern implementation for model creation and management.

This module provides centralized model creation, loading, and management
to eliminate code duplication and provide consistent interfaces.
"""

import os
import joblib
from pathlib import Path
from typing import Dict, List, Optional, Union, Type, Any
from abc import ABC, abstractmethod
import logging

from .logging_config import get_logger
from .error_handling import ModelError, ErrorHandler


class ModelFactory:
    """
    Factory class for creating and loading fantasy football models.
    
    This class centralizes model creation logic and provides a consistent
    interface for loading different types of models across positions.
    """
    
    def __init__(self, model_directory: Optional[Union[str, Path]] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the model factory.
        
        Args:
            model_directory: Base directory where models are stored
            logger: Optional logger instance
        """
        self.logger = logger or get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler(self.logger)
        
        # Set default model directory
        if model_directory is None:
            # Default to saved_models in project root
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            model_directory = project_root / 'saved_models'
        
        self.model_directory = Path(model_directory)
        self.model_directory.mkdir(parents=True, exist_ok=True)
        
        # Registry of available model types
        self._model_registry = {}
        self._register_default_models()
    
    def _register_default_models(self) -> None:
        """Register default model types available in the system."""
        # This would be expanded to register different model types
        self._model_registry.update({
            'ensemble': {
                'class_path': 'src.ensemble_model.EnsembleFantasyModel',
                'file_suffix': '_ensemble_model.joblib',
                'priority': 1  # Higher priority models are tried first
            },
            'advanced_engineering': {
                'class_path': 'src.models.base_model.BaseModel',
                'file_suffix': '_advanced_engineering_model.joblib',
                'priority': 2
            },
            'baseline': {
                'class_path': 'src.models.base_model.BaseModel', 
                'file_suffix': '_baseline_model.joblib',
                'priority': 3
            }
        })
    
    def register_model_type(self, model_type: str, class_path: str, 
                           file_suffix: str, priority: int = 10) -> None:
        """
        Register a new model type with the factory.
        
        Args:
            model_type: Name of the model type
            class_path: Python import path to the model class
            file_suffix: File suffix for saved models of this type
            priority: Priority for model loading (lower = higher priority)
        """
        self._model_registry[model_type] = {
            'class_path': class_path,
            'file_suffix': file_suffix,
            'priority': priority
        }
        self.logger.info(f"Registered model type: {model_type}")
    
    def get_available_models(self, position: str) -> List[Dict[str, Any]]:
        """
        Get list of available models for a specific position.
        
        Args:
            position: Player position (QB, RB, WR, TE, K, DST)
            
        Returns:
            List of dictionaries containing model information
        """
        available_models = []
        
        for model_type, config in self._model_registry.items():
            model_path = self._get_model_path(position, model_type)
            
            if model_path.exists():
                model_info = {
                    'type': model_type,
                    'position': position,
                    'path': str(model_path),
                    'priority': config['priority'],
                    'exists': True,
                    'size_mb': model_path.stat().st_size / (1024 * 1024)
                }
                available_models.append(model_info)
        
        # Sort by priority
        available_models.sort(key=lambda x: x['priority'])
        
        return available_models
    
    def _get_model_path(self, position: str, model_type: str) -> Path:
        """
        Get the file path for a specific model.
        
        Args:
            position: Player position
            model_type: Type of model
            
        Returns:
            Path to the model file
        """
        if model_type not in self._model_registry:
            raise ModelError(f"Unknown model type: {model_type}")
        
        config = self._model_registry[model_type]
        filename = f"{position.upper()}{config['file_suffix']}"
        return self.model_directory / filename
    
    def load_model(self, position: str, 
                  model_type: Optional[str] = None,
                  fallback_to_available: bool = True) -> Any:
        """
        Load a model for the specified position and type.
        
        Args:
            position: Player position (QB, RB, WR, TE, K, DST)
            model_type: Specific model type to load (if None, uses best available)
            fallback_to_available: Whether to fallback to other available models
            
        Returns:
            Loaded model instance
            
        Raises:
            ModelError: If model cannot be loaded
        """
        position = position.upper()
        
        # If no specific type requested, try to load best available
        if model_type is None:
            return self._load_best_available_model(position)
        
        # Try to load specific model type
        try:
            return self._load_specific_model(position, model_type)
        except ModelError as e:
            if fallback_to_available:
                self.logger.warning(f"Failed to load {model_type} model for {position}, trying fallback")
                return self._load_best_available_model(position)
            else:
                raise e
    
    def _load_specific_model(self, position: str, model_type: str) -> Any:
        """
        Load a specific model type for a position.
        
        Args:
            position: Player position
            model_type: Model type to load
            
        Returns:
            Loaded model instance
            
        Raises:
            ModelError: If model cannot be loaded
        """
        if model_type not in self._model_registry:
            raise ModelError(f"Unknown model type: {model_type}", 
                           model_type=model_type, position=position)
        
        model_path = self._get_model_path(position, model_type)
        
        if not model_path.exists():
            raise ModelError(f"{model_type} model not found for {position}",
                           model_type=model_type, position=position,
                           context={'expected_path': str(model_path)})
        
        try:
            self.logger.info(f"Loading {model_type} model for {position} from {model_path}")
            
            # Load based on model type
            if model_type == 'ensemble':
                # Special loading for ensemble models
                model = self._load_ensemble_model(model_path)
            else:
                # Standard joblib loading
                model = joblib.load(model_path)
            
            self.logger.info(f"Successfully loaded {model_type} model for {position}")
            return model
            
        except Exception as e:
            raise ModelError(f"Failed to load {model_type} model for {position}: {str(e)}",
                           model_type=model_type, position=position,
                           original_error=e, context={'model_path': str(model_path)})
    
    def _load_ensemble_model(self, model_path: Path) -> Any:
        """
        Load an ensemble model with special handling.
        
        Args:
            model_path: Path to the ensemble model file
            
        Returns:
            Loaded ensemble model
        """
        try:
            # Import ensemble model class
            from src.ensemble_model import EnsembleFantasyModel
            return EnsembleFantasyModel.load(str(model_path))
        except ImportError as e:
            raise ModelError(f"Cannot import EnsembleFantasyModel: {str(e)}", 
                           original_error=e)
    
    def _load_best_available_model(self, position: str) -> Any:
        """
        Load the best available model for a position based on priority.
        
        Args:
            position: Player position
            
        Returns:
            Best available model instance
            
        Raises:
            ModelError: If no models are available
        """
        available_models = self.get_available_models(position)
        
        if not available_models:
            raise ModelError(f"No models available for position {position}",
                           position=position)
        
        # Try models in priority order
        for model_info in available_models:
            try:
                model = self._load_specific_model(position, model_info['type'])
                self.logger.info(f"Loaded {model_info['type']} model for {position} (priority {model_info['priority']})")
                return model
            except ModelError as e:
                self.logger.warning(f"Failed to load {model_info['type']} model for {position}: {e}")
                continue
        
        # If we get here, no models could be loaded
        model_types = [m['type'] for m in available_models]
        raise ModelError(f"Failed to load any available models for {position}",
                       position=position, context={'attempted_types': model_types})
    
    def create_model(self, position: str, model_type: str, **kwargs) -> Any:
        """
        Create a new model instance (not loaded from file).
        
        Args:
            position: Player position
            model_type: Type of model to create
            **kwargs: Additional arguments for model initialization
            
        Returns:
            New model instance
            
        Raises:
            ModelError: If model cannot be created
        """
        if model_type not in self._model_registry:
            raise ModelError(f"Unknown model type: {model_type}")
        
        try:
            config = self._model_registry[model_type]
            
            # Import the model class
            module_path, class_name = config['class_path'].rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            model_class = getattr(module, class_name)
            
            # Create instance
            model = model_class(position=position, **kwargs)
            
            self.logger.info(f"Created new {model_type} model for {position}")
            return model
            
        except Exception as e:
            raise ModelError(f"Failed to create {model_type} model for {position}: {str(e)}",
                           model_type=model_type, position=position, original_error=e)
    
    def save_model(self, model: Any, position: str, model_type: str,
                  overwrite: bool = False) -> Path:
        """
        Save a model to the standard location.
        
        Args:
            model: Model instance to save
            position: Player position
            model_type: Type of model
            overwrite: Whether to overwrite existing model
            
        Returns:
            Path where model was saved
            
        Raises:
            ModelError: If save fails
        """
        model_path = self._get_model_path(position, model_type)
        
        if model_path.exists() and not overwrite:
            raise ModelError(f"Model file already exists: {model_path}. Use overwrite=True to replace.",
                           model_type=model_type, position=position)
        
        try:
            # Special handling for ensemble models
            if model_type == 'ensemble' and hasattr(model, 'save'):
                model.save(str(model_path))
            else:
                # Standard joblib save
                joblib.dump(model, model_path)
            
            self.logger.info(f"Saved {model_type} model for {position} to {model_path}")
            return model_path
            
        except Exception as e:
            raise ModelError(f"Failed to save {model_type} model for {position}: {str(e)}",
                           model_type=model_type, position=position, original_error=e)
    
    def list_all_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all available models grouped by position.
        
        Returns:
            Dictionary mapping positions to lists of available models
        """
        positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
        all_models = {}
        
        for position in positions:
            available = self.get_available_models(position)
            if available:
                all_models[position] = available
        
        return all_models
    
    def cleanup_old_models(self, keep_latest: int = 3) -> List[str]:
        """
        Clean up old model files, keeping only the most recent versions.
        
        Args:
            keep_latest: Number of latest models to keep per position/type
            
        Returns:
            List of file paths that were deleted
        """
        deleted_files = []
        
        # This would implement cleanup logic based on file timestamps
        # For now, just return empty list as placeholder
        self.logger.info(f"Model cleanup completed. {len(deleted_files)} files deleted.")
        
        return deleted_files
    
    def validate_model(self, model: Any, position: str) -> Dict[str, Any]:
        """
        Validate that a model is properly configured for a position.
        
        Args:
            model: Model instance to validate
            position: Expected position
            
        Returns:
            Dictionary containing validation results
        """
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Check if model has required methods
            required_methods = ['predict']
            for method in required_methods:
                if not hasattr(model, method):
                    validation_results['errors'].append(f"Model missing required method: {method}")
                    validation_results['valid'] = False
            
            # Check position compatibility if model has position attribute
            if hasattr(model, 'position') or hasattr(model, 'get_position'):
                model_position = getattr(model, 'position', None) or getattr(model, 'get_position', lambda: None)()
                if model_position and model_position.upper() != position.upper():
                    validation_results['warnings'].append(f"Model position mismatch: expected {position}, got {model_position}")
            
        except Exception as e:
            validation_results['errors'].append(f"Validation failed: {str(e)}")
            validation_results['valid'] = False
        
        return validation_results
    
    @staticmethod
    def create_feature_engineer(position: str):
        """
        Create a position-specific feature engineer.
        
        Args:
            position: Player position (QB, RB, WR, TE, K, DST)
            
        Returns:
            Feature engineer instance for the position, or None if not available
        """
        logger = get_logger(f"ModelFactory.create_feature_engineer")
        
        try:
            position_upper = position.upper()
            
            # Import and create the appropriate feature engineer
            if position_upper == 'QB':
                from src.data.feature_engineering.position.qb_features_v2 import QBFeatureEngineer
                return QBFeatureEngineer()
            elif position_upper == 'RB':
                from src.data.feature_engineering.position.rb_features_v2 import RBFeatureEngineer
                return RBFeatureEngineer()
            elif position_upper == 'WR':
                from src.data.feature_engineering.position.wr_features_v2 import WRFeatureEngineer
                return WRFeatureEngineer()
            elif position_upper == 'TE':
                from src.data.feature_engineering.position.te_features_v2 import TEFeatureEngineer
                return TEFeatureEngineer()
            elif position_upper == 'K':
                from src.data.feature_engineering.position.k_features_v2 import KFeatureEngineer
                return KFeatureEngineer()
            elif position_upper in ['DST', 'DEF', 'D/ST']:
                from src.data.feature_engineering.position.dst_features_v2 import DSTFeatureEngineer
                return DSTFeatureEngineer()
            else:
                logger.warning(f"Unknown position: {position}")
                return None
                
        except ImportError as e:
            logger.error(f"Failed to import feature engineer for {position}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create feature engineer for {position}: {e}")
            return None


# Global model factory instance
_global_model_factory: Optional[ModelFactory] = None


def get_model_factory(**kwargs) -> ModelFactory:
    """
    Get the global model factory instance.
    
    Args:
        **kwargs: Arguments passed to ModelFactory if creating new instance
        
    Returns:
        ModelFactory instance
    """
    global _global_model_factory
    
    if _global_model_factory is None:
        _global_model_factory = ModelFactory(**kwargs)
    
    return _global_model_factory


def load_model(position: str, model_type: Optional[str] = None, **kwargs) -> Any:
    """
    Convenience function to load a model using the global factory.
    
    Args:
        position: Player position
        model_type: Optional model type
        **kwargs: Additional arguments
        
    Returns:
        Loaded model instance
    """
    factory = get_model_factory()
    return factory.load_model(position, model_type, **kwargs)