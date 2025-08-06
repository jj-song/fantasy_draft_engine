"""
Standardized error handling for the Fantasy Draft Engine.

This module provides a consistent hierarchy of exceptions and error handling
utilities to improve debugging and error recovery throughout the system.
"""

import logging
import traceback
from typing import Optional, Dict, Any, List
from datetime import datetime


class FantasyFootballError(Exception):
    """
    Base exception class for all fantasy football related errors.
    
    This provides a consistent interface for error handling and includes
    additional context information for better debugging.
    """
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None,
                 original_error: Optional[Exception] = None):
        """
        Initialize the fantasy football error.
        
        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
            context: Optional dictionary of context information
            original_error: Optional original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.original_error = original_error
        self.timestamp = datetime.now()
        
        # Store the traceback for debugging
        self.traceback_str = traceback.format_exc()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary for logging or serialization.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'original_error': str(self.original_error) if self.original_error else None
        }
    
    def __str__(self) -> str:
        """String representation of the error."""
        base_msg = self.message
        
        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"
        
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base_msg = f"{base_msg} (Context: {context_str})"
        
        return base_msg


class DataProcessingError(FantasyFootballError):
    """
    Exception raised when data processing operations fail.
    
    This includes errors in data loading, cleaning, validation, and transformation.
    """
    
    def __init__(self, message: str, data_source: Optional[str] = None,
                 row_count: Optional[int] = None, **kwargs):
        """
        Initialize data processing error.
        
        Args:
            message: Error message
            data_source: Optional source of the data being processed
            row_count: Optional number of rows being processed
            **kwargs: Additional arguments passed to parent class
        """
        context = kwargs.get('context', {})
        if data_source:
            context['data_source'] = data_source
        if row_count is not None:
            context['row_count'] = row_count
        
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class ModelError(FantasyFootballError):
    """
    Exception raised when model operations fail.
    
    This includes errors in model training, prediction, loading, and saving.
    """
    
    def __init__(self, message: str, model_type: Optional[str] = None,
                 position: Optional[str] = None, **kwargs):
        """
        Initialize model error.
        
        Args:
            message: Error message  
            model_type: Optional type of model (e.g., 'RandomForest', 'LightGBM')
            position: Optional player position the model is for
            **kwargs: Additional arguments passed to parent class
        """
        context = kwargs.get('context', {})
        if model_type:
            context['model_type'] = model_type
        if position:
            context['position'] = position
        
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class FeatureEngineeringError(FantasyFootballError):
    """
    Exception raised when feature engineering operations fail.
    
    This includes errors in feature calculation, validation, and transformation.
    """
    
    def __init__(self, message: str, position: Optional[str] = None,
                 feature_type: Optional[str] = None, **kwargs):
        """
        Initialize feature engineering error.
        
        Args:
            message: Error message
            position: Optional player position for position-specific features
            feature_type: Optional type of feature being engineered
            **kwargs: Additional arguments passed to parent class
        """
        context = kwargs.get('context', {})
        if position:
            context['position'] = position
        if feature_type:
            context['feature_type'] = feature_type
        
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class ConfigurationError(FantasyFootballError):
    """
    Exception raised when configuration is invalid or missing.
    
    This includes errors in configuration loading, validation, and access.
    """
    
    def __init__(self, message: str, config_key: Optional[str] = None,
                 config_file: Optional[str] = None, **kwargs):
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            config_key: Optional configuration key that caused the error
            config_file: Optional configuration file path
            **kwargs: Additional arguments passed to parent class
        """
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
        if config_file:
            context['config_file'] = config_file
        
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class ErrorHandler:
    """
    Utility class for consistent error handling and reporting.
    
    This class provides methods for handling errors consistently across
    the fantasy football system, including logging and recovery strategies.
    """
    
    def __init__(self, logger: logging.Logger, 
                 enable_recovery: bool = True):
        """
        Initialize the error handler.
        
        Args:
            logger: Logger instance to use for error reporting
            enable_recovery: Whether to attempt error recovery strategies
        """
        self.logger = logger
        self.enable_recovery = enable_recovery
        self.error_counts = {}  # Track error frequency
    
    def handle_error(self, error: Exception, 
                    operation: str,
                    recovery_strategy: Optional[str] = None,
                    reraise: bool = True) -> Optional[Any]:
        """
        Handle an error with logging and optional recovery.
        
        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            recovery_strategy: Optional recovery strategy to attempt
            reraise: Whether to re-raise the exception after handling
            
        Returns:
            Recovery result if recovery was successful, None otherwise
            
        Raises:
            The original exception if reraise=True and no recovery
        """
        # Convert to our error type if needed
        if not isinstance(error, FantasyFootballError):
            if isinstance(error, (ValueError, TypeError)):
                ff_error = DataProcessingError(
                    f"{operation} failed: {str(error)}",
                    original_error=error
                )
            else:
                ff_error = FantasyFootballError(
                    f"{operation} failed: {str(error)}",
                    original_error=error
                )
        else:
            ff_error = error
        
        # Log the error
        self.logger.error(f"Error in {operation}: {ff_error}")
        self.logger.debug(f"Error details: {ff_error.to_dict()}")
        
        # Track error frequency
        error_type = ff_error.__class__.__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Attempt recovery if enabled and strategy provided
        if self.enable_recovery and recovery_strategy:
            try:
                recovery_result = self._attempt_recovery(ff_error, recovery_strategy)
                if recovery_result is not None:
                    self.logger.info(f"Successfully recovered from error in {operation}")
                    return recovery_result
            except Exception as recovery_error:
                self.logger.warning(f"Recovery failed for {operation}: {recovery_error}")
        
        # Re-raise if requested
        if reraise:
            raise ff_error
        
        return None
    
    def _attempt_recovery(self, error: FantasyFootballError, 
                         strategy: str) -> Optional[Any]:
        """
        Attempt to recover from an error using the specified strategy.
        
        Args:
            error: The error to recover from
            strategy: Recovery strategy to use
            
        Returns:
            Recovery result if successful, None otherwise
        """
        if strategy == 'return_empty_dataframe':
            import pandas as pd
            return pd.DataFrame()
        
        elif strategy == 'return_zero':
            return 0
        
        elif strategy == 'return_empty_list':
            return []
        
        elif strategy == 'return_default_config':
            return {'default': True}
        
        elif strategy == 'use_fallback_model':
            # This would need to be implemented based on the specific use case
            self.logger.info("Using fallback model recovery strategy")
            return None
        
        else:
            self.logger.warning(f"Unknown recovery strategy: {strategy}")
            return None
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get a summary of errors handled by this error handler.
        
        Returns:  
            Dictionary containing error statistics
        """
        total_errors = sum(self.error_counts.values())
        
        return {
            'total_errors': total_errors,
            'error_counts': self.error_counts.copy(),
            'most_common_error': max(self.error_counts, key=self.error_counts.get) if self.error_counts else None
        }
    
    def reset_error_counts(self) -> None:
        """Reset error count statistics."""
        self.error_counts = {}


def create_error_context(operation: str, **kwargs) -> Dict[str, Any]:
    """
    Create a standardized error context dictionary.
    
    Args:
        operation: Name of the operation being performed
        **kwargs: Additional context information
        
    Returns:
        Dictionary containing error context
    """
    context = {
        'operation': operation,
        'timestamp': datetime.now().isoformat()
    }
    context.update(kwargs)
    return context


def safe_execute(func, *args, default_return=None, 
                error_handler: Optional[ErrorHandler] = None,
                operation_name: Optional[str] = None, **kwargs):
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        *args: Arguments to pass to the function
        default_return: Value to return if function fails
        error_handler: Optional error handler to use
        operation_name: Optional name of the operation for logging
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Function result or default_return if function fails
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        operation = operation_name or f"{func.__name__}"
        
        if error_handler:
            return error_handler.handle_error(
                e, operation, recovery_strategy='return_default', reraise=False
            ) or default_return
        else:
            # Simple logging if no error handler provided
            logging.getLogger(__name__).error(f"Error in {operation}: {e}")
            return default_return