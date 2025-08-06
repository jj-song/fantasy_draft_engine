"""
Core utilities for configuration service.
"""

from .error_handling import ConfigurationError
from .logging_config import get_logger

__all__ = ['ConfigurationError', 'get_logger']