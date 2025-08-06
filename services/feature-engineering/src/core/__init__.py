"""
Core foundational classes and utilities for the Fantasy Draft Engine.

This module contains abstract base classes and shared utilities that provide
consistent interfaces and reduce code duplication throughout the system.
"""

from .base_feature_engineer import BaseFeatureEngineer
from .base_data_processor import BaseDataProcessor
from .column_mapper import ColumnMapper
from .error_handling import FantasyFootballError, DataProcessingError, ModelError, FeatureEngineeringError, ConfigurationError
from .logging_config import setup_logger, get_logger
from .model_factory import ModelFactory, get_model_factory, load_model
from .feature_utils import FeatureCalculator, get_feature_calculator, calculate_per_game_stats, calculate_efficiency_ratios, calculate_usage_shares

__all__ = [
    'BaseFeatureEngineer',
    'BaseDataProcessor', 
    'ColumnMapper',
    'FantasyFootballError',
    'DataProcessingError',
    'ModelError',
    'FeatureEngineeringError',
    'ConfigurationError',
    'setup_logger',
    'get_logger',
    'ModelFactory',
    'get_model_factory',
    'load_model',
    'FeatureCalculator',
    'get_feature_calculator',
    'calculate_per_game_stats',
    'calculate_efficiency_ratios',
    'calculate_usage_shares'
]