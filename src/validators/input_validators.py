"""
Input Validation for Fantasy Football Operations

This module provides comprehensive input validation to prevent runtime errors,
ensure data quality, and provide clear error messages. It implements fail-fast
validation with specific error types for different validation failures.

Key Features:
- DataFrame structure and content validation
- Position and model validation
- Data quality checks (null values, ranges, types)
- Decorator-based validation for clean integration
- Detailed error messages for easy debugging
"""

from typing import Any, List, Optional, Union, Callable, Dict
import pandas as pd
import numpy as np
import logging
from functools import wraps

from src.constants.fantasy_constants import (
    VALID_POSITIONS, CORE_POSITIONS, FANTASY_DEFAULTS, VALIDATION_THRESHOLDS
)

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Base class for validation errors."""
    pass


class DataFrameValidationError(ValidationError):
    """Raised when DataFrame validation fails."""
    pass


class PositionValidationError(ValidationError):
    """Raised when position validation fails."""
    pass


class ModelValidationError(ValidationError):
    """Raised when model validation fails."""
    pass


class DataQualityError(ValidationError):
    """Raised when data quality checks fail."""
    pass


class InputValidator:
    """Comprehensive input validation for fantasy football operations.
    
    This class provides validation methods for all common input types used
    throughout the fantasy football system, with detailed error messages
    and data quality checks.
    """
    
    @classmethod
    def validate_dataframe(cls, 
                          df: Any, 
                          name: str = "dataframe",
                          min_rows: int = 1,
                          required_columns: Optional[List[str]] = None,
                          allow_empty: bool = False) -> pd.DataFrame:
        """Validate input is a proper DataFrame with required structure.
        
        Args:
            df: Input to validate
            name: Name for error messages
            min_rows: Minimum number of rows required
            required_columns: List of columns that must be present
            allow_empty: Whether to allow empty DataFrames
            
        Returns:
            Validated DataFrame
            
        Raises:
            DataFrameValidationError: If validation fails
        """
        # Check if input exists
        if df is None:
            raise DataFrameValidationError(f"{name} cannot be None")
        
        # Check type
        if not isinstance(df, pd.DataFrame):
            raise DataFrameValidationError(
                f"{name} must be a pandas DataFrame, got {type(df).__name__}"
            )
        
        # Check if empty (unless explicitly allowed)
        if df.empty and not allow_empty:
            raise DataFrameValidationError(f"{name} cannot be empty")
        
        # Check minimum rows
        if len(df) < min_rows:
            raise DataFrameValidationError(
                f"{name} must have at least {min_rows} rows, got {len(df)}"
            )
        
        # Check required columns
        if required_columns:
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                raise DataFrameValidationError(
                    f"{name} missing required columns: {missing_columns}. "
                    f"Available columns: {list(df.columns)}"
                )
        
        # Log validation success
        logger.debug(f"Validated {name}: {len(df)} rows, {len(df.columns)} columns")
        
        return df
    
    @classmethod
    def validate_position(cls, 
                         position: Any,
                         allow_multiple: bool = False,
                         core_only: bool = False) -> Union[str, List[str]]:
        """Validate position is valid fantasy football position.
        
        Args:
            position: Position string or list of positions
            allow_multiple: Whether to allow list of positions
            core_only: Whether to restrict to core positions (no K/DST)
            
        Returns:
            Validated position string or list
            
        Raises:
            PositionValidationError: If validation fails
        """
        if position is None:
            raise PositionValidationError("Position cannot be None")
        
        # Determine valid positions
        valid_positions = CORE_POSITIONS if core_only else VALID_POSITIONS
        
        # Handle multiple positions
        if isinstance(position, (list, tuple)):
            if not allow_multiple:
                raise PositionValidationError(
                    f"Multiple positions not allowed, got: {position}"
                )
            
            if not position:
                raise PositionValidationError("Position list cannot be empty")
            
            validated_positions = []
            for pos in position:
                validated_pos = cls._validate_single_position(pos, valid_positions)
                validated_positions.append(validated_pos)
            
            return validated_positions
        
        # Handle single position
        return cls._validate_single_position(position, valid_positions)
    
    @classmethod
    def _validate_single_position(cls, position: Any, valid_positions: List[str]) -> str:
        """Validate a single position string."""
        if not isinstance(position, str):
            raise PositionValidationError(
                f"Position must be a string, got {type(position).__name__}"
            )
        
        if not position.strip():
            raise PositionValidationError("Position cannot be empty")
        
        position_upper = position.strip().upper()
        
        if position_upper not in valid_positions:
            raise PositionValidationError(
                f"Invalid position: {position}. Valid positions: {valid_positions}"
            )
        
        return position_upper
    
    @classmethod
    def validate_model(cls, 
                      model: Any,
                      required_methods: Optional[List[str]] = None,
                      model_name: str = "model") -> Any:
        """Validate model has required methods and attributes.
        
        Args:
            model: Model object to validate
            required_methods: List of method names that must exist
            model_name: Name for error messages
            
        Returns:
            Validated model object
            
        Raises:
            ModelValidationError: If validation fails
        """
        if model is None:
            raise ModelValidationError(f"{model_name} cannot be None")
        
        # Default required methods
        if required_methods is None:
            required_methods = ['predict']
        
        # Check for required methods
        missing_methods = []
        for method in required_methods:
            if not hasattr(model, method):
                missing_methods.append(method)
        
        if missing_methods:
            available_methods = [attr for attr in dir(model) 
                               if callable(getattr(model, attr)) and not attr.startswith('_')]
            raise ModelValidationError(
                f"{model_name} missing required methods: {missing_methods}. "
                f"Available methods: {available_methods[:10]}..."
            )
        
        # Check if model appears to be trained (for sklearn-like models)
        if hasattr(model, 'n_features_in_') and hasattr(model, 'feature_names_in_'):
            # This is likely a trained sklearn model
            logger.debug(f"Validated trained {model_name} with {model.n_features_in_} features")
        elif hasattr(model, 'model') and hasattr(model.model, 'n_features_in_'):
            # This might be our custom model wrapper
            logger.debug(f"Validated wrapped {model_name}")
        else:
            logger.warning(f"Cannot verify if {model_name} is trained - proceeding with caution")
        
        return model
    
    @classmethod
    def validate_predictions(cls,
                           predictions: Any,
                           position: str,
                           expected_length: Optional[int] = None,
                           allow_negative: bool = False) -> np.ndarray:
        """Validate model predictions are reasonable.
        
        Args:
            predictions: Prediction values
            position: Position for range validation
            expected_length: Expected number of predictions
            allow_negative: Whether negative values are allowed
            
        Returns:
            Validated predictions as numpy array
            
        Raises:
            ValidationError: If validation fails
        """
        if predictions is None:
            raise ValidationError("Predictions cannot be None")
        
        # Convert to numpy array
        try:
            pred_array = np.asarray(predictions, dtype=float)
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Cannot convert predictions to numeric array: {e}")
        
        # Check for correct length
        if expected_length is not None and len(pred_array) != expected_length:
            raise ValidationError(
                f"Expected {expected_length} predictions, got {len(pred_array)}"
            )
        
        # Check for NaN/infinite values
        if np.any(np.isnan(pred_array)):
            nan_count = np.sum(np.isnan(pred_array))
            raise ValidationError(f"Predictions contain {nan_count} NaN values")
        
        if np.any(np.isinf(pred_array)):
            inf_count = np.sum(np.isinf(pred_array))
            raise ValidationError(f"Predictions contain {inf_count} infinite values")
        
        # Check for negative values if not allowed
        if not allow_negative and np.any(pred_array < 0):
            negative_count = np.sum(pred_array < 0)
            min_value = np.min(pred_array)
            raise ValidationError(
                f"Predictions contain {negative_count} negative values (min: {min_value:.2f})"
            )
        
        # Check position-specific ranges
        try:
            min_val, max_val = VALIDATION_THRESHOLDS.get_position_range(position)
            out_of_range = np.sum((pred_array < min_val) | (pred_array > max_val))
            
            if out_of_range > 0:
                logger.warning(
                    f"{out_of_range}/{len(pred_array)} predictions outside typical "
                    f"{position} range ({min_val}-{max_val})"
                )
                
                # Log extreme values for debugging
                extreme_low = pred_array[pred_array < min_val]
                extreme_high = pred_array[pred_array > max_val]
                
                if len(extreme_low) > 0:
                    logger.warning(f"Low outliers: {extreme_low[:5]}")
                if len(extreme_high) > 0:
                    logger.warning(f"High outliers: {extreme_high[:5]}")
                    
        except Exception as e:
            logger.warning(f"Could not validate position ranges: {e}")
        
        logger.debug(
            f"Validated {len(pred_array)} predictions: "
            f"range {pred_array.min():.1f}-{pred_array.max():.1f}, "
            f"mean {pred_array.mean():.1f}"
        )
        
        return pred_array
    
    @classmethod
    def validate_data_quality(cls,
                            df: pd.DataFrame,
                            critical_columns: Optional[List[str]] = None,
                            max_null_ratio: float = None) -> pd.DataFrame:
        """Validate data quality of a DataFrame.
        
        Args:
            df: DataFrame to validate
            critical_columns: Columns that cannot have null values
            max_null_ratio: Maximum ratio of null values allowed
            
        Returns:
            Validated DataFrame
            
        Raises:
            DataQualityError: If data quality is insufficient
        """
        if max_null_ratio is None:
            max_null_ratio = FANTASY_DEFAULTS.MAX_NULL_PERCENTAGE
        
        # Check for completely empty columns
        empty_columns = df.columns[df.isnull().all()].tolist()
        if empty_columns:
            raise DataQualityError(f"Completely empty columns found: {empty_columns}")
        
        # Check critical columns for null values
        if critical_columns:
            for col in critical_columns:
                if col in df.columns:
                    null_count = df[col].isnull().sum()
                    if null_count > 0:
                        raise DataQualityError(
                            f"Critical column '{col}' has {null_count} null values"
                        )
        
        # Check overall null ratio
        total_cells = len(df) * len(df.columns)
        total_nulls = df.isnull().sum().sum()
        null_ratio = total_nulls / total_cells if total_cells > 0 else 0
        
        if null_ratio > max_null_ratio:
            raise DataQualityError(
                f"Data quality insufficient: {null_ratio:.1%} null values "
                f"(max allowed: {max_null_ratio:.1%})"
            )
        
        # Check for suspicious duplicate rows
        duplicate_count = df.duplicated().sum()
        duplicate_ratio = duplicate_count / len(df) if len(df) > 0 else 0
        
        if duplicate_ratio > 0.1:  # More than 10% duplicates
            logger.warning(f"High duplicate ratio: {duplicate_ratio:.1%}")
        
        # Log data quality metrics
        logger.debug(
            f"Data quality check passed: "
            f"null_ratio={null_ratio:.1%}, "
            f"duplicate_ratio={duplicate_ratio:.1%}"
        )
        
        return df
    
    @classmethod
    def validate_feature_list(cls,
                            features: Any,
                            min_features: int = 1,
                            max_features: int = 1000) -> List[str]:
        """Validate list of feature names.
        
        Args:
            features: Feature list to validate
            min_features: Minimum number of features required
            max_features: Maximum number of features allowed
            
        Returns:
            Validated list of feature names
            
        Raises:
            ValidationError: If validation fails
        """
        if features is None:
            raise ValidationError("Feature list cannot be None")
        
        # Convert to list if needed
        if isinstance(features, str):
            features = [features]
        elif not isinstance(features, (list, tuple, np.ndarray)):
            try:
                features = list(features)
            except (TypeError, ValueError):
                raise ValidationError(f"Cannot convert features to list: {type(features)}")
        
        # Check length
        if len(features) < min_features:
            raise ValidationError(
                f"Need at least {min_features} features, got {len(features)}"
            )
        
        if len(features) > max_features:
            raise ValidationError(
                f"Too many features: {len(features)} (max: {max_features})"
            )
        
        # Check for valid feature names
        invalid_features = []
        for feature in features:
            if not isinstance(feature, str):
                invalid_features.append(f"{feature} ({type(feature).__name__})")
            elif not feature.strip():
                invalid_features.append("empty string")
        
        if invalid_features:
            raise ValidationError(f"Invalid feature names: {invalid_features}")
        
        # Check for duplicates
        unique_features = list(set(features))
        if len(unique_features) != len(features):
            duplicates = [f for f in features if features.count(f) > 1]
            logger.warning(f"Duplicate features found: {set(duplicates)}")
        
        return [f.strip() for f in features]


# Decorator functions for easy validation
def validate_inputs(df_param: str = 'df',
                   position_param: str = 'position', 
                   model_param: str = 'model'):
    """Decorator to validate common function inputs.
    
    Args:
        df_param: Name of DataFrame parameter
        position_param: Name of position parameter  
        model_param: Name of model parameter
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature to map parameters
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate DataFrame if present
            if df_param in bound_args.arguments:
                df = bound_args.arguments[df_param]
                validated_df = InputValidator.validate_dataframe(df, df_param)
                bound_args.arguments[df_param] = validated_df
            
            # Validate position if present
            if position_param in bound_args.arguments:
                position = bound_args.arguments[position_param]
                validated_position = InputValidator.validate_position(position)
                bound_args.arguments[position_param] = validated_position
            
            # Validate model if present
            if model_param in bound_args.arguments:
                model = bound_args.arguments[model_param]
                validated_model = InputValidator.validate_model(model)
                bound_args.arguments[model_param] = validated_model
            
            return func(*bound_args.args, **bound_args.kwargs)
        
        return wrapper
    return decorator


def validate_dataframe_input(required_columns: Optional[List[str]] = None,
                           min_rows: int = 1):
    """Decorator to validate DataFrame input with specific requirements.
    
    Args:
        required_columns: Columns that must be present
        min_rows: Minimum number of rows
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(df: pd.DataFrame, *args, **kwargs):
            validated_df = InputValidator.validate_dataframe(
                df, 
                func.__name__ + ".df",
                min_rows=min_rows,
                required_columns=required_columns
            )
            return func(validated_df, *args, **kwargs)
        return wrapper
    return decorator


def validate_position_input(allow_multiple: bool = False, core_only: bool = False):
    """Decorator to validate position input.
    
    Args:
        allow_multiple: Whether to allow multiple positions
        core_only: Whether to restrict to core positions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Find position parameter (assume second parameter after df)
            if len(args) >= 2:
                position = args[1]
                validated_position = InputValidator.validate_position(
                    position, allow_multiple=allow_multiple, core_only=core_only
                )
                args = (args[0], validated_position) + args[2:]
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    # Demo and testing
    print("Input Validation Demo")
    print("=" * 50)
    
    # Test DataFrame validation
    try:
        valid_df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        InputValidator.validate_dataframe(valid_df, "test_df")
        print("✅ DataFrame validation passed")
    except ValidationError as e:
        print(f"❌ DataFrame validation failed: {e}")
    
    # Test position validation
    try:
        valid_position = InputValidator.validate_position("RB")
        print(f"✅ Position validation passed: {valid_position}")
    except ValidationError as e:
        print(f"❌ Position validation failed: {e}")
    
    # Test invalid position
    try:
        InputValidator.validate_position("INVALID")
    except ValidationError as e:
        print(f"✅ Correctly caught invalid position: {e}")
    
    # Test predictions validation
    try:
        valid_predictions = np.array([150.5, 200.0, 175.2])
        validated = InputValidator.validate_predictions(valid_predictions, "RB")
        print(f"✅ Predictions validation passed: mean={validated.mean():.1f}")
    except ValidationError as e:
        print(f"❌ Predictions validation failed: {e}")
    
    print("\n✅ All validation tests completed!")