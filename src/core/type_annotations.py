"""
Type Annotations for Fantasy Football System

This module provides comprehensive type hints and type aliases for the Fantasy Football
Draft Engine, improving code clarity, IDE support, and type safety throughout the system.

Key Features:
- Common type aliases for complex types
- Protocol classes for duck typing
- Type guards for runtime type checking
- Generic types for reusable components
"""

from typing import (
    Dict, List, Tuple, Optional, Union, Any, Callable, TypeVar, Generic, 
    Protocol, runtime_checkable, Literal, overload
)
import pandas as pd
import numpy as np
from pathlib import Path
from abc import ABC, abstractmethod

# Basic type aliases
PlayerID = str
PositionType = Literal['QB', 'RB', 'WR', 'TE', 'K', 'DST']
SeasonYear = int
FantasyPoints = float
VORValue = float
RankPosition = int

# Complex type aliases
PlayerDataFrame = pd.DataFrame  # DataFrame with player data
FeatureMatrix = pd.DataFrame    # DataFrame with engineered features
PredictionArray = np.ndarray    # Array of predictions
ModelWeights = Dict[str, float] # Dictionary of model weights

# Collection types
PositionData = Dict[PositionType, PlayerDataFrame]
PositionRankings = Dict[PositionType, PlayerDataFrame]
FeatureMappings = Dict[str, str]
ValidationResults = Dict[str, Any]

# Function signature types
PredictionFunction = Callable[[pd.DataFrame, Any, str], pd.DataFrame]
ValidationFunction = Callable[[Any], bool]
TransformFunction = Callable[[pd.DataFrame], pd.DataFrame]

# Configuration types
ModelConfig = Dict[str, Any]
ScoringConfig = Dict[str, float]
VORConfig = Dict[str, Union[int, float]]
PathConfig = Dict[str, Union[str, Path]]

# Generic types
T = TypeVar('T')
ModelType = TypeVar('ModelType')
DataType = TypeVar('DataType', bound=pd.DataFrame)


@runtime_checkable
class FantasyModel(Protocol):
    """Protocol for fantasy football prediction models."""
    
    def predict(self, features: pd.DataFrame, context: Optional[pd.DataFrame] = None) -> np.ndarray:
        """Make predictions on the given features."""
        ...
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance scores."""
        ...


@runtime_checkable
class DataProcessor(Protocol):
    """Protocol for data processing components."""
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Process the input data."""
        ...
    
    def validate(self, data: pd.DataFrame) -> bool:
        """Validate the data quality."""
        ...


@runtime_checkable
class FeatureEngineer(Protocol):
    """Protocol for feature engineering components."""
    
    def engineer_features(self, data: pd.DataFrame, position: str) -> pd.DataFrame:
        """Engineer features for the given position."""
        ...
    
    def get_feature_names(self) -> List[str]:
        """Get list of engineered feature names."""
        ...


# Type guards for runtime type checking
def is_valid_position(position: Any) -> bool:
    """Type guard to check if position is valid."""
    return isinstance(position, str) and position.upper() in ['QB', 'RB', 'WR', 'TE', 'K', 'DST']


def is_player_dataframe(df: Any) -> bool:
    """Type guard to check if DataFrame contains player data."""
    if not isinstance(df, pd.DataFrame):
        return False
    
    required_columns = {'player_name', 'position'}
    return required_columns.issubset(set(df.columns))


def is_prediction_array(predictions: Any) -> bool:
    """Type guard to check if predictions are valid."""
    if not isinstance(predictions, (np.ndarray, list)):
        return False
    
    try:
        pred_array = np.asarray(predictions, dtype=float)
        return not (np.any(np.isnan(pred_array)) or np.any(np.isinf(pred_array)))
    except (ValueError, TypeError):
        return False


# Generic classes for type safety
class TypedDict(Generic[T]):
    """Generic typed dictionary for type-safe data structures."""
    
    def __init__(self, data: Dict[str, T]):
        self._data = data
    
    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        return self._data.get(key, default)
    
    def keys(self) -> List[str]:
        return list(self._data.keys())
    
    def values(self) -> List[T]:
        return list(self._data.values())
    
    def items(self) -> List[Tuple[str, T]]:
        return list(self._data.items())


class PositionTypedData(TypedDict[PlayerDataFrame]):
    """Type-safe container for position-specific data."""
    
    def get_position_data(self, position: PositionType) -> Optional[PlayerDataFrame]:
        """Get data for a specific position with type safety."""
        return self.get(position)
    
    def add_position_data(self, position: PositionType, data: PlayerDataFrame) -> None:
        """Add data for a position with validation."""
        if not is_player_dataframe(data):
            raise ValueError(f"Invalid player DataFrame for position {position}")
        self._data[position] = data


# Overloaded function signatures for better type inference
@overload
def process_player_data(data: pd.DataFrame, positions: List[PositionType]) -> PositionData:
    ...


@overload  
def process_player_data(data: pd.DataFrame, position: PositionType) -> PlayerDataFrame:
    ...


def process_player_data(
    data: pd.DataFrame, 
    positions: Union[PositionType, List[PositionType]]
) -> Union[PlayerDataFrame, PositionData]:
    """Process player data for one or multiple positions."""
    if isinstance(positions, str):
        # Single position
        return data[data['position'] == positions].copy()
    else:
        # Multiple positions
        result = {}
        for position in positions:
            result[position] = data[data['position'] == position].copy()
        return result


# Enhanced function signatures for key components
class EnhancedFunctionSignatures:
    """Enhanced type signatures for existing functions."""
    
    @staticmethod
    def load_position_data(
        position: PositionType,
        include_matchup_intelligence: bool = False,
        weeks_ahead_sos: int = 4
    ) -> PlayerDataFrame:
        """Enhanced signature for load_position_data function."""
        pass
    
    @staticmethod
    def predict_fantasy_points(
        df: PlayerDataFrame,
        model: FantasyModel,
        position: PositionType,
        target_col: str = 'fantasy_points_per_game'
    ) -> PlayerDataFrame:
        """Enhanced signature for predict_fantasy_points function."""
        pass
    
    @staticmethod
    def calculate_value_over_replacement(
        df_by_pos: PositionData,
        include_matchup_adjustments: bool = False
    ) -> PositionData:
        """Enhanced signature for VOR calculation function."""
        pass
    
    @staticmethod
    def create_overall_rankings(
        df_by_pos: PositionData,
        use_schedule_adjusted_vor: bool = False
    ) -> PlayerDataFrame:
        """Enhanced signature for overall rankings function."""
        pass
    
    @staticmethod
    def validate_predictions(
        predictions: PredictionArray,
        position: PositionType,
        expected_length: Optional[int] = None
    ) -> PredictionArray:
        """Enhanced signature for prediction validation."""
        pass


# Result types for complex operations
class PredictionResult:
    """Type-safe container for prediction results."""
    
    def __init__(self, 
                 predictions: PredictionArray,
                 confidence_intervals: Optional[Tuple[PredictionArray, PredictionArray]] = None,
                 feature_importance: Optional[pd.DataFrame] = None):
        self.predictions = predictions
        self.confidence_intervals = confidence_intervals
        self.feature_importance = feature_importance
    
    @property
    def has_confidence_intervals(self) -> bool:
        return self.confidence_intervals is not None
    
    @property
    def has_feature_importance(self) -> bool:
        return self.feature_importance is not None


class RankingResult:
    """Type-safe container for ranking results."""
    
    def __init__(self,
                 overall_rankings: PlayerDataFrame,
                 position_rankings: PositionRankings,
                 vor_calculations: PositionData):
        self.overall_rankings = overall_rankings
        self.position_rankings = position_rankings
        self.vor_calculations = vor_calculations
    
    def get_top_players(self, n: int = 10) -> PlayerDataFrame:
        """Get top N players from overall rankings."""
        return self.overall_rankings.head(n)
    
    def get_position_top_players(self, position: PositionType, n: int = 5) -> PlayerDataFrame:
        """Get top N players for a specific position."""
        if position in self.position_rankings:
            return self.position_rankings[position].head(n)
        return pd.DataFrame()


class ValidationResult:
    """Type-safe container for validation results."""
    
    def __init__(self,
                 is_valid: bool,
                 errors: List[str],
                 warnings: List[str],
                 validation_details: ValidationResults):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings
        self.validation_details = validation_details
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    def get_summary(self) -> str:
        """Get a summary of validation results."""
        status = "VALID" if self.is_valid else "INVALID"
        return f"Validation {status}: {len(self.errors)} errors, {len(self.warnings)} warnings"


# Type aliases for common return types
LoadDataReturn = Tuple[PlayerDataFrame, ValidationResult]
ModelTrainingReturn = Tuple[FantasyModel, ValidationResult]
PipelineReturn = Tuple[RankingResult, ValidationResult]

# Configuration type definitions
class TypedConfig:
    """Type-safe configuration container."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict
    
    def get_positions(self) -> List[PositionType]:
        """Get list of valid positions from config."""
        positions = self._config.get('positions', ['QB', 'RB', 'WR', 'TE'])
        return [pos for pos in positions if is_valid_position(pos)]
    
    def get_scoring_config(self) -> ScoringConfig:
        """Get scoring configuration."""
        return self._config.get('scoring', {})
    
    def get_vor_config(self) -> VORConfig:
        """Get VOR configuration."""
        return self._config.get('vor', {})
    
    def get_model_config(self) -> ModelConfig:
        """Get model configuration."""
        return self._config.get('model', {})


if __name__ == "__main__":
    # Demo of type system
    print("Fantasy Football Type System Demo")
    print("=" * 50)
    
    # Test type guards
    print(f"✅ is_valid_position('RB'): {is_valid_position('RB')}")
    print(f"❌ is_valid_position('INVALID'): {is_valid_position('INVALID')}")
    
    # Test typed containers
    sample_data = pd.DataFrame({
        'player_name': ['Josh Allen', 'Derrick Henry'],
        'position': ['QB', 'RB'],
        'fantasy_points': [300, 250]
    })
    
    print(f"✅ is_player_dataframe(sample): {is_player_dataframe(sample_data)}")
    
    # Test prediction validation
    sample_predictions = np.array([300.0, 250.0, 200.0])
    print(f"✅ is_prediction_array(sample): {is_prediction_array(sample_predictions)}")
    
    # Test result containers
    result = PredictionResult(sample_predictions)
    print(f"✅ PredictionResult created: {len(result.predictions)} predictions")
    
    print("\n✅ Type system working correctly!")