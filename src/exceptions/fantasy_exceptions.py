"""
Fantasy Football Custom Exceptions

This module defines specific exception classes for the Fantasy Draft Engine,
providing clear, actionable error messages and enabling better error handling
throughout the system.

Design Philosophy:
- Specific exception types for different failure modes
- Clear error messages with context and suggestions
- Hierarchical exception structure for logical grouping
- Include debugging information where helpful
"""

from typing import Optional, List, Dict, Any


class FantasyFootballError(Exception):
    """Base exception for all fantasy football related errors.
    
    All custom exceptions in the system inherit from this base class,
    allowing for catch-all error handling when needed.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize with message and optional debugging details.
        
        Args:
            message: Human-readable error message
            details: Optional dictionary with debugging information
        """
        super().__init__(message)
        self.details = details or {}
    
    def __str__(self) -> str:
        """Return formatted error message with details if available."""
        base_message = super().__str__()
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{base_message} (Details: {detail_str})"
        return base_message


# Data-related exceptions
class DataError(FantasyFootballError):
    """Base class for data-related errors."""
    pass


class DataAcquisitionError(DataError):
    """Raised when external data cannot be acquired."""
    
    def __init__(self, message: str, source: Optional[str] = None, year: Optional[int] = None):
        details = {}
        if source:
            details['source'] = source
        if year:
            details['year'] = year
        super().__init__(message, details)


class DataSourceUnavailableError(DataAcquisitionError):
    """Raised when external data source is unavailable or unreachable."""
    
    def __init__(self, source: str, message: Optional[str] = None):
        if message is None:
            message = f"Data source '{source}' is currently unavailable"
        super().__init__(message, source=source)


class DataValidationError(DataError):
    """Raised when data fails validation checks."""
    
    def __init__(self, message: str, validation_type: Optional[str] = None, 
                 failed_records: Optional[int] = None):
        details = {}
        if validation_type:
            details['validation_type'] = validation_type
        if failed_records:
            details['failed_records'] = failed_records
        super().__init__(message, details)


class DataQualityError(DataError):
    """Raised when data quality is insufficient for processing."""
    
    def __init__(self, message: str, quality_metrics: Optional[Dict[str, float]] = None):
        super().__init__(message, quality_metrics)


class DataIntegrityError(DataError):
    """Raised when data integrity checks fail."""
    
    def __init__(self, message: str, integrity_check: Optional[str] = None):
        details = {'integrity_check': integrity_check} if integrity_check else {}
        super().__init__(message, details)


# Feature engineering exceptions
class FeatureEngineeringError(FantasyFootballError):
    """Base class for feature engineering errors."""
    pass


class FeatureMappingError(FeatureEngineeringError):
    """Raised when feature mapping fails."""
    
    def __init__(self, message: str, missing_features: Optional[List[str]] = None,
                 available_features: Optional[List[str]] = None):
        details = {}
        if missing_features:
            details['missing_features'] = missing_features
        if available_features:
            details['available_features'] = len(available_features)
        super().__init__(message, details)


class FeatureValidationError(FeatureEngineeringError):
    """Raised when engineered features fail validation."""
    
    def __init__(self, message: str, invalid_features: Optional[List[str]] = None):
        details = {'invalid_features': invalid_features} if invalid_features else {}
        super().__init__(message, details)


class FeatureGenerationError(FeatureEngineeringError):
    """Raised when feature generation process fails."""
    
    def __init__(self, message: str, feature_type: Optional[str] = None, 
                 position: Optional[str] = None):
        details = {}
        if feature_type:
            details['feature_type'] = feature_type
        if position:
            details['position'] = position
        super().__init__(message, details)


# Model-related exceptions
class ModelError(FantasyFootballError):
    """Base class for model-related errors."""
    pass


class ModelLoadError(ModelError):
    """Raised when model cannot be loaded from disk."""
    
    def __init__(self, message: str, model_path: Optional[str] = None, 
                 model_type: Optional[str] = None, position: Optional[str] = None):
        details = {}
        if model_path:
            details['model_path'] = model_path
        if model_type:
            details['model_type'] = model_type
        if position:
            details['position'] = position
        super().__init__(message, details)


class ModelTrainingError(ModelError):
    """Raised when model training fails."""
    
    def __init__(self, message: str, model_type: Optional[str] = None, 
                 position: Optional[str] = None, training_samples: Optional[int] = None):
        details = {}
        if model_type:
            details['model_type'] = model_type
        if position:
            details['position'] = position
        if training_samples:
            details['training_samples'] = training_samples
        super().__init__(message, details)


class ModelValidationError(ModelError):
    """Raised when model validation fails."""
    
    def __init__(self, message: str, validation_metric: Optional[str] = None,
                 actual_value: Optional[float] = None, threshold: Optional[float] = None):
        details = {}
        if validation_metric:
            details['validation_metric'] = validation_metric
        if actual_value is not None:
            details['actual_value'] = actual_value
        if threshold is not None:
            details['threshold'] = threshold
        super().__init__(message, details)


class ModelCompatibilityError(ModelError):
    """Raised when model is incompatible with provided data."""
    
    def __init__(self, message: str, expected_features: Optional[int] = None,
                 provided_features: Optional[int] = None, missing_features: Optional[List[str]] = None):
        details = {}
        if expected_features:
            details['expected_features'] = expected_features
        if provided_features:
            details['provided_features'] = provided_features
        if missing_features:
            details['missing_features'] = missing_features
        super().__init__(message, details)


# Prediction-related exceptions
class PredictionError(FantasyFootballError):
    """Base class for prediction-related errors."""
    pass


class PredictionValidationError(PredictionError):
    """Raised when predictions fail validation checks."""
    
    def __init__(self, message: str, position: Optional[str] = None,
                 invalid_count: Optional[int] = None, total_count: Optional[int] = None):
        details = {}
        if position:
            details['position'] = position
        if invalid_count and total_count:
            details['invalid_ratio'] = invalid_count / total_count
        super().__init__(message, details)


class PredictionRangeError(PredictionError):
    """Raised when predictions are outside reasonable ranges."""
    
    def __init__(self, message: str, position: Optional[str] = None,
                 min_prediction: Optional[float] = None, max_prediction: Optional[float] = None,
                 valid_range: Optional[tuple] = None):
        details = {}
        if position:
            details['position'] = position
        if min_prediction is not None:
            details['min_prediction'] = min_prediction
        if max_prediction is not None:
            details['max_prediction'] = max_prediction
        if valid_range:
            details['valid_range'] = valid_range
        super().__init__(message, details)


class PredictionInconsistencyError(PredictionError):
    """Raised when predictions are internally inconsistent."""
    
    def __init__(self, message: str, inconsistency_type: Optional[str] = None):
        details = {'inconsistency_type': inconsistency_type} if inconsistency_type else {}
        super().__init__(message, details)


# Configuration and setup exceptions
class ConfigurationError(FantasyFootballError):
    """Base class for configuration-related errors."""
    pass


class InvalidPositionError(ConfigurationError):
    """Raised when an invalid fantasy position is specified."""
    
    def __init__(self, position: str, valid_positions: Optional[List[str]] = None):
        if valid_positions:
            message = f"Invalid position '{position}'. Valid positions: {valid_positions}"
        else:
            message = f"Invalid position '{position}'"
        super().__init__(message, {'position': position, 'valid_positions': valid_positions})


class InvalidScoringSystemError(ConfigurationError):
    """Raised when scoring system configuration is invalid."""
    
    def __init__(self, message: str, scoring_type: Optional[str] = None):
        details = {'scoring_type': scoring_type} if scoring_type else {}
        super().__init__(message, details)


class InvalidLeagueSettingsError(ConfigurationError):
    """Raised when league settings are invalid or inconsistent."""
    
    def __init__(self, message: str, setting: Optional[str] = None, value: Optional[Any] = None):
        details = {}
        if setting:
            details['setting'] = setting
        if value is not None:
            details['value'] = value
        super().__init__(message, details)


# Ranking and VOR exceptions
class RankingError(FantasyFootballError):
    """Base class for ranking-related errors."""
    pass


class VORCalculationError(RankingError):
    """Raised when VOR calculation fails."""
    
    def __init__(self, message: str, position: Optional[str] = None,
                 replacement_level: Optional[int] = None):
        details = {}
        if position:
            details['position'] = position
        if replacement_level:
            details['replacement_level'] = replacement_level
        super().__init__(message, details)


class RankingValidationError(RankingError):
    """Raised when generated rankings fail validation."""
    
    def __init__(self, message: str, validation_type: Optional[str] = None,
                 total_players: Optional[int] = None):
        details = {}
        if validation_type:
            details['validation_type'] = validation_type
        if total_players:
            details['total_players'] = total_players
        super().__init__(message, details)


class TierGenerationError(RankingError):
    """Raised when tier generation fails."""
    
    def __init__(self, message: str, tier_method: Optional[str] = None):
        details = {'tier_method': tier_method} if tier_method else {}
        super().__init__(message, details)


# Pipeline and workflow exceptions
class PipelineError(FantasyFootballError):
    """Base class for pipeline execution errors."""
    pass


class PipelineStageError(PipelineError):
    """Raised when a specific pipeline stage fails."""
    
    def __init__(self, message: str, stage: Optional[str] = None, 
                 stage_input: Optional[Dict[str, Any]] = None):
        details = {}
        if stage:
            details['stage'] = stage
        if stage_input:
            details['stage_input_keys'] = list(stage_input.keys())
        super().__init__(message, details)


class PipelineValidationError(PipelineError):
    """Raised when pipeline validation fails."""
    
    def __init__(self, message: str, expected_output: Optional[str] = None,
                 actual_output: Optional[str] = None):
        details = {}
        if expected_output:
            details['expected_output'] = expected_output
        if actual_output:
            details['actual_output'] = actual_output
        super().__init__(message, details)


class DependencyError(PipelineError):
    """Raised when pipeline dependencies are not met."""
    
    def __init__(self, message: str, missing_dependencies: Optional[List[str]] = None):
        details = {'missing_dependencies': missing_dependencies} if missing_dependencies else {}
        super().__init__(message, details)


# Utility functions for creating common exceptions
def create_data_quality_error(null_ratio: float, max_allowed: float, 
                            dataset_name: str = "dataset") -> DataQualityError:
    """Create a standardized data quality error."""
    return DataQualityError(
        f"{dataset_name} has {null_ratio:.1%} null values, exceeding maximum allowed {max_allowed:.1%}",
        quality_metrics={'null_ratio': null_ratio, 'max_allowed': max_allowed}
    )


def create_feature_mapping_error(missing_features: List[str], 
                               position: Optional[str] = None) -> FeatureMappingError:
    """Create a standardized feature mapping error."""
    pos_str = f" for {position}" if position else ""
    return FeatureMappingError(
        f"Cannot map {len(missing_features)} required features{pos_str}: {missing_features[:5]}...",
        missing_features=missing_features
    )


def create_model_compatibility_error(expected_features: List[str], 
                                   provided_features: List[str],
                                   position: str) -> ModelCompatibilityError:
    """Create a standardized model compatibility error."""
    missing = set(expected_features) - set(provided_features)
    return ModelCompatibilityError(
        f"{position} model expects {len(expected_features)} features but {len(missing)} are missing",
        expected_features=len(expected_features),
        provided_features=len(provided_features),
        missing_features=list(missing)
    )


def create_prediction_range_error(predictions, position: str, 
                                valid_range: tuple) -> PredictionRangeError:
    """Create a standardized prediction range error."""
    import numpy as np
    min_pred = float(np.min(predictions))
    max_pred = float(np.max(predictions))
    
    return PredictionRangeError(
        f"{position} predictions outside valid range {valid_range}: got {min_pred:.1f}-{max_pred:.1f}",
        position=position,
        min_prediction=min_pred,
        max_prediction=max_pred,
        valid_range=valid_range
    )


# Exception context manager for enhanced error reporting
class FantasyErrorContext:
    """Context manager for enhanced error reporting with automatic details."""
    
    def __init__(self, operation: str, **context_details):
        """Initialize error context.
        
        Args:
            operation: Description of the operation being performed
            **context_details: Additional context information
        """
        self.operation = operation
        self.context_details = context_details
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type and issubclass(exc_type, FantasyFootballError):
            # Enhance the exception with context information
            if hasattr(exc_value, 'details'):
                exc_value.details.update(self.context_details)
                exc_value.details['operation'] = self.operation
        
        # Don't suppress the exception
        return False


if __name__ == "__main__":
    # Demo and testing of exception classes
    print("Fantasy Football Exceptions Demo")
    print("=" * 50)
    
    # Test basic exception
    try:
        raise FeatureMappingError(
            "Test error", 
            missing_features=['age', 'games'], 
            available_features=['name', 'position']
        )
    except FeatureMappingError as e:
        print(f"✅ Basic exception: {e}")
    
    # Test utility function
    try:
        raise create_data_quality_error(0.15, 0.10, "player_stats")
    except DataQualityError as e:
        print(f"✅ Utility function: {e}")
    
    # Test context manager
    try:
        with FantasyErrorContext("model_training", position="RB", model_type="ensemble"):
            raise ModelTrainingError("Training failed")
    except ModelTrainingError as e:
        print(f"✅ Context manager: {e}")
    
    print("\n✅ Exception system working correctly!")