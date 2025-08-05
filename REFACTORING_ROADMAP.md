# Fantasy Draft Engine - Refactoring Roadmap
*A Comprehensive Guide to Improving Code Quality, Maintainability, and Reliability*

---

## Executive Summary

This roadmap identifies critical refactoring opportunities in the Fantasy Draft Engine codebase, prioritized by impact and effort. The codebase shows signs of rapid development with technical debt accumulation, particularly in the areas of code duplication, error handling, and architectural design. This document provides a structured approach to systematically improve code quality while maintaining functionality.

**Key Findings:**
- 🔴 **Critical**: Long god functions (300+ lines), minimal error handling, tight coupling
- 🟡 **Medium**: Code duplication, magic numbers, missing abstractions
- 🟢 **Low**: Missing type hints, inconsistent naming, documentation gaps

---

## 1. Code Smell Detection

### Issue: Duplicate Code - Feature Mapping Logic
**Location**: Multiple files including `generate_draft_rankings.py` (lines 304-382, 522-611), `predict_fantasy_points_baseline()`, `predict_fantasy_points()`
**Severity**: 🔴 High
**Impact**: Changes to feature mappings must be made in multiple places, increasing maintenance burden and bug risk

**Current Code**:
```python
# Repeated in multiple functions
feature_mapping = {
    'age': 'birth_date',
    'games_played': 'games',
    'passing_attempts': 'passing_attempts',
    'rushing_attempts': 'carries',
    # ... 30+ more mappings
}

# Logic repeated for handling mappings
if expected_feature == 'age' and mapped_col == 'birth_date':
    # Convert birth_date to age
    current_year = 2025
    birth_dates = pd.to_datetime(result_df['birth_date'], errors='coerce')
    ages = current_year - birth_dates.dt.year
    X[expected_feature] = ages.fillna(25)
```

**Proposed Refactoring**:
```python
# src/core/feature_mapper.py
class FeatureMapper:
    """Centralized feature mapping logic for model compatibility."""
    
    FEATURE_MAPPINGS = {
        'age': 'birth_date',
        'games_played': 'games',
        'passing_attempts': 'passing_attempts',
        'rushing_attempts': 'carries',
        # All mappings in one place
    }
    
    @classmethod
    def map_features(cls, df: pd.DataFrame, target_features: List[str]) -> pd.DataFrame:
        """Map dataframe columns to expected model features."""
        result = pd.DataFrame(index=df.index)
        
        for feature in target_features:
            if feature == 'age' and 'birth_date' in df.columns:
                result[feature] = cls._calculate_age(df['birth_date'])
            elif feature in cls.FEATURE_MAPPINGS:
                source_col = cls.FEATURE_MAPPINGS[feature]
                if source_col in df.columns:
                    result[feature] = df[source_col]
                else:
                    result[feature] = 0  # Or appropriate default
            else:
                result[feature] = df.get(feature, 0)
        
        return result
    
    @staticmethod
    def _calculate_age(birth_dates: pd.Series, target_year: int = 2025) -> pd.Series:
        """Convert birth dates to ages."""
        dates = pd.to_datetime(birth_dates, errors='coerce')
        return (target_year - dates.dt.year).fillna(25)
```

**Benefits**:
- Single source of truth for feature mappings
- Easier to maintain and test
- Reusable across all prediction functions
- Clear separation of concerns

**Implementation Effort**: ⏱️ 2 hours

---

### Issue: Long God Functions
**Location**: `generate_draft_rankings.py` - `predict_fantasy_points()` (355 lines), `load_position_data()` (189 lines)
**Severity**: 🔴 High  
**Impact**: Functions are doing too many things, making them hard to test, understand, and maintain

**Current Code**:
```python
def predict_fantasy_points(df: pd.DataFrame, model, position: str, target_col: str = 'fantasy_points_per_game') -> pd.DataFrame:
    # 355 lines doing:
    # - Feature validation and logging
    # - Feature mapping
    # - Data type conversion
    # - Model type detection
    # - Prediction
    # - Error handling with fallbacks
    # - Result validation
    # ... all in one function
```

**Proposed Refactoring**:
```python
# src/predictions/fantasy_predictor.py
class FantasyPredictor:
    """Handles fantasy point predictions with proper separation of concerns."""
    
    def predict(self, df: pd.DataFrame, model: Any, position: str) -> pd.DataFrame:
        """Main prediction method with clear steps."""
        # Step 1: Validate features
        validation_result = self._validate_features(df, position)
        if not validation_result.is_valid:
            return self._handle_invalid_features(df, position, validation_result)
        
        # Step 2: Prepare features
        features = self._prepare_features(df, model)
        
        # Step 3: Make predictions
        try:
            predictions = self._make_predictions(features, model, position)
        except PredictionError as e:
            return self._handle_prediction_error(df, position, e)
        
        # Step 4: Post-process results
        return self._post_process_predictions(df, predictions, position)
    
    def _validate_features(self, df: pd.DataFrame, position: str) -> ValidationResult:
        """Validate that required features are present."""
        validator = FeatureValidator(position)
        return validator.validate(df)
    
    def _prepare_features(self, df: pd.DataFrame, model: Any) -> pd.DataFrame:
        """Prepare features for model input."""
        mapper = FeatureMapper()
        expected_features = self._get_expected_features(model)
        return mapper.map_features(df, expected_features)
    
    def _make_predictions(self, features: pd.DataFrame, model: Any, position: str) -> np.ndarray:
        """Make predictions with appropriate model handler."""
        handler = ModelHandlerFactory.get_handler(model)
        return handler.predict(features, position)
    
    def _post_process_predictions(self, df: pd.DataFrame, predictions: np.ndarray, position: str) -> pd.DataFrame:
        """Scale and validate predictions."""
        processor = PredictionPostProcessor(position)
        return processor.process(df, predictions)
```

**Benefits**:
- Each method has a single responsibility
- Easy to test individual components
- Clear flow of operations
- Extensible for new features

**Implementation Effort**: ⏱️ 1 day

---

### Issue: Magic Numbers
**Location**: Throughout codebase - VOR calculations, tier thresholds, default values
**Severity**: 🟡 Medium
**Impact**: Hard to understand what numbers represent, difficult to adjust configurations

**Current Code**:
```python
# Scattered throughout the code
replacement_value = df_sorted.loc[replacement_rank - 1, 'predicted_points']
if vor_value >= 18:
    tier = "ELITE"
elif vor_value >= 14:
    tier = "PREMIUM"
# ...
ages = current_year - birth_dates.dt.year
X[expected_feature] = ages.fillna(25)  # Why 25?
baseline_values = {'QB': 255.0, 'RB': 170.0, 'WR': 136.0}  # What are these?
```

**Proposed Refactoring**:
```python
# src/constants/fantasy_constants.py
from dataclasses import dataclass
from typing import Dict

@dataclass
class VORTiers:
    """Value Over Replacement tier thresholds."""
    ELITE: float = 18.0
    PREMIUM: float = 14.0
    SOLID: float = 10.0
    DEPTH: float = 6.0
    
    def get_tier(self, vor_value: float) -> str:
        """Get tier name for a VOR value."""
        if vor_value >= self.ELITE:
            return "ELITE"
        elif vor_value >= self.PREMIUM:
            return "PREMIUM"
        elif vor_value >= self.SOLID:
            return "SOLID"
        elif vor_value >= self.DEPTH:
            return "DEPTH"
        else:
            return "BENCH"

@dataclass
class FantasyDefaults:
    """Default values used throughout the system."""
    DEFAULT_AGE: int = 25  # Average NFL player age
    DEFAULT_GAMES_IN_SEASON: int = 17
    PREDICTION_YEAR: int = 2025
    
    # Baseline seasonal fantasy points by position
    POSITION_BASELINES: Dict[str, float] = None
    
    def __post_init__(self):
        self.POSITION_BASELINES = {
            'QB': 255.0,  # Average QB seasonal points
            'RB': 170.0,  # Average RB seasonal points
            'WR': 136.0,  # Average WR seasonal points
            'TE': 102.0,  # Average TE seasonal points
            'K': 136.0,   # Average K seasonal points
            'DST': 136.0  # Average DST seasonal points
        }

# Usage
from src.constants import VORTiers, FantasyDefaults

tiers = VORTiers()
tier_name = tiers.get_tier(vor_value)

defaults = FantasyDefaults()
age = defaults.DEFAULT_AGE
```

**Benefits**:
- Self-documenting code with meaningful constant names
- Easy to adjust values in one place
- Type safety with dataclasses
- Reusable across the codebase

**Implementation Effort**: ⏱️ 1 hour

---

### Issue: Complex Nested Conditionals
**Location**: Feature validation, model selection logic, prediction fallbacks
**Severity**: 🟡 Medium
**Impact**: Hard to follow logic flow, difficult to test all branches

**Current Code**:
```python
if advanced_features_available:
    if matchup_cols:
        if position == 'QB' and len(matchup_cols) < 10:
            print("WARNING...")
            if fallback_available:
                model = load_baseline_model()
            else:
                raise ValueError()
        else:
            model = load_ensemble_model()
    else:
        model = load_advanced_model()
else:
    model = load_baseline_model()
```

**Proposed Refactoring**:
```python
# src/core/model_selector.py
class ModelSelector:
    """Handles model selection logic with clear rules."""
    
    def select_model(self, position: str, features: pd.DataFrame) -> Any:
        """Select appropriate model based on available features."""
        feature_analyzer = FeatureAnalyzer(features)
        
        strategy = self._determine_strategy(position, feature_analyzer)
        return strategy.load_model(position)
    
    def _determine_strategy(self, position: str, analyzer: FeatureAnalyzer) -> ModelLoadStrategy:
        """Determine which model loading strategy to use."""
        if not analyzer.has_advanced_features():
            return BaselineModelStrategy()
        
        if position == 'QB' and not analyzer.has_sufficient_matchup_features():
            logger.warning(f"QB missing matchup features, using baseline model")
            return BaselineModelStrategy()
        
        if analyzer.has_ensemble_features():
            return EnsembleModelStrategy()
        
        return AdvancedModelStrategy()

# Strategy pattern for model loading
class ModelLoadStrategy(ABC):
    @abstractmethod
    def load_model(self, position: str) -> Any:
        pass

class EnsembleModelStrategy(ModelLoadStrategy):
    def load_model(self, position: str) -> Any:
        return load_ensemble_model(position)
```

**Benefits**:
- Clear, testable decision logic
- Strategy pattern allows easy extension
- No deeply nested conditionals
- Each decision point is explicit

**Implementation Effort**: ⏱️ 2 hours

---

## 2. Architecture Issues

### Issue: Tight Coupling - Direct File Dependencies
**Location**: Throughout - hardcoded paths, direct imports between modules
**Severity**: 🔴 High
**Impact**: Changes to file structure break multiple modules, hard to test in isolation

**Current Code**:
```python
# Direct file path dependencies
ensemble_model_path = os.path.join(project_root, f'saved_models/{position}_ensemble_model.joblib')
config_path = '../config.yaml'
sys.path.insert(0, os.path.join(project_root, 'src'))
```

**Proposed Refactoring**:
```python
# src/core/path_manager.py
class PathManager:
    """Centralized path management with dependency injection."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or self._find_project_root()
        self._validate_paths()
    
    @property
    def models_dir(self) -> Path:
        return self.project_root / 'saved_models'
    
    @property
    def data_dir(self) -> Path:
        return self.project_root / 'data'
    
    def get_model_path(self, position: str, model_type: str = 'ensemble') -> Path:
        """Get path for a specific model file."""
        filename = f"{position}_{model_type}_model.joblib"
        return self.models_dir / filename
    
    def get_data_path(self, data_type: str, filename: str) -> Path:
        """Get path for data files."""
        return self.data_dir / data_type / filename

# Dependency injection in classes
class ModelLoader:
    def __init__(self, path_manager: PathManager):
        self.path_manager = path_manager
    
    def load_model(self, position: str) -> Any:
        model_path = self.path_manager.get_model_path(position)
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        return joblib.load(model_path)
```

**Benefits**:
- No hardcoded paths in business logic
- Easy to test with mock paths
- Single place to update path structure
- Clear dependencies

**Implementation Effort**: ⏱️ 4 hours

---

### Issue: Missing Abstractions - No Model Interface
**Location**: Model classes, prediction functions
**Severity**: 🟡 Medium
**Impact**: Each model type handled differently, no common interface

**Current Code**:
```python
# Different handling for each model type
if hasattr(model, 'predict') and hasattr(model, 'rf_model'):
    # Ensemble model
    predictions = model.predict(X, player_data)
else:
    # Single model
    predictions = model.predict(X)
```

**Proposed Refactoring**:
```python
# src/models/interfaces.py
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
import numpy as np

class IFantasyModel(ABC):
    """Interface for all fantasy prediction models."""
    
    @abstractmethod
    def predict(self, features: pd.DataFrame, context: Optional[pd.DataFrame] = None) -> np.ndarray:
        """Make predictions on the given features."""
        pass
    
    @abstractmethod
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance scores."""
        pass
    
    @abstractmethod
    def validate_features(self, features: pd.DataFrame) -> bool:
        """Validate that required features are present."""
        pass

class ModelAdapter:
    """Adapter to make existing models conform to IFantasyModel."""
    
    def __init__(self, model: Any):
        self.model = model
    
    def predict(self, features: pd.DataFrame, context: Optional[pd.DataFrame] = None) -> np.ndarray:
        if hasattr(self.model, 'rf_model'):  # Ensemble
            return self.model.predict(features, context)
        else:  # Single model
            return self.model.predict(features)
    
    def get_feature_importance(self) -> pd.DataFrame:
        if hasattr(self.model, 'feature_importances_'):
            return pd.DataFrame({
                'feature': self.model.feature_names_in_,
                'importance': self.model.feature_importances_
            })
        return pd.DataFrame()
```

**Benefits**:
- Consistent interface for all models
- Easy to add new model types
- Clear contract for model behavior
- Simplified client code

**Implementation Effort**: ⏱️ 4 hours

---

## 3. Error Handling & Reliability

### Issue: Minimal Error Handling in Data Pipeline
**Location**: `data_acquisition.py`, `feature_engineering.py`, data loading functions
**Severity**: 🔴 High
**Impact**: Silent failures, data corruption, difficult debugging

**Current Code**:
```python
def fetch_player_season_stats(year, positions=None):
    try:
        seasonal_stats = nfl.import_seasonal_data([year])
        # ... lots of processing
        return merged_stats
    except Exception as e:
        logger.error(f"Error fetching data for {year} season: {str(e)}")
        raise  # Generic re-raise
```

**Proposed Refactoring**:
```python
# src/exceptions/data_exceptions.py
class DataAcquisitionError(Exception):
    """Base exception for data acquisition errors."""
    pass

class DataSourceUnavailableError(DataAcquisitionError):
    """Raised when external data source is unavailable."""
    pass

class DataValidationError(DataAcquisitionError):
    """Raised when fetched data fails validation."""
    pass

# src/data/robust_data_fetcher.py
class RobustDataFetcher:
    """Data fetcher with comprehensive error handling and retry logic."""
    
    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    @retry(max_attempts=3, exceptions=(DataSourceUnavailableError,))
    def fetch_seasonal_data(self, year: int, positions: List[str]) -> pd.DataFrame:
        """Fetch seasonal data with retry and validation."""
        try:
            logger.info(f"Fetching data for {year} season")
            data = nfl.import_seasonal_data([year])
            
            if data.empty:
                raise DataValidationError(f"No data returned for {year}")
            
            # Validate critical columns exist
            required_columns = ['player_id', 'position', 'team']
            missing_columns = set(required_columns) - set(data.columns)
            if missing_columns:
                raise DataValidationError(f"Missing required columns: {missing_columns}")
            
            # Validate data quality
            null_players = data['player_id'].isnull().sum()
            if null_players > len(data) * 0.1:  # More than 10% null
                raise DataValidationError(f"Too many null player IDs: {null_players}")
            
            return data
            
        except ConnectionError as e:
            logger.error(f"Connection error fetching {year} data: {e}")
            raise DataSourceUnavailableError(f"Cannot connect to data source: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching {year} data: {e}")
            raise DataAcquisitionError(f"Failed to fetch data: {e}")
```

**Benefits**:
- Specific exception types for different failures
- Automatic retry for transient errors
- Data validation prevents corrupt data
- Clear error messages for debugging

**Implementation Effort**: ⏱️ 4 hours

---

### Issue: No Input Validation
**Location**: User-facing functions, model predictions, data processing
**Severity**: 🔴 High
**Impact**: Runtime errors, incorrect results, security vulnerabilities

**Current Code**:
```python
def predict_fantasy_points(df: pd.DataFrame, model, position: str) -> pd.DataFrame:
    # No validation of inputs
    # df could be None, empty, or have wrong structure
    # model could be None or wrong type
    # position could be invalid
```

**Proposed Refactoring**:
```python
# src/validators/input_validators.py
from typing import List, Any
import pandas as pd

class InputValidator:
    """Validates inputs for fantasy football operations."""
    
    VALID_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
    
    @classmethod
    def validate_dataframe(cls, df: Any, name: str = "dataframe") -> pd.DataFrame:
        """Validate input is a non-empty DataFrame."""
        if df is None:
            raise ValueError(f"{name} cannot be None")
        
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"{name} must be a pandas DataFrame, got {type(df)}")
        
        if df.empty:
            raise ValueError(f"{name} cannot be empty")
        
        return df
    
    @classmethod
    def validate_position(cls, position: str) -> str:
        """Validate position is valid."""
        if not position:
            raise ValueError("Position cannot be empty")
        
        position_upper = position.upper()
        if position_upper not in cls.VALID_POSITIONS:
            raise ValueError(f"Invalid position: {position}. Must be one of {cls.VALID_POSITIONS}")
        
        return position_upper
    
    @classmethod
    def validate_model(cls, model: Any, required_methods: List[str] = None) -> Any:
        """Validate model has required methods."""
        if model is None:
            raise ValueError("Model cannot be None")
        
        required_methods = required_methods or ['predict']
        for method in required_methods:
            if not hasattr(model, method):
                raise ValueError(f"Model must have '{method}' method")
        
        return model

# Usage with decorator
def validate_inputs(func):
    """Decorator to validate common inputs."""
    def wrapper(df: pd.DataFrame, model: Any, position: str, *args, **kwargs):
        df = InputValidator.validate_dataframe(df, "Input dataframe")
        model = InputValidator.validate_model(model)
        position = InputValidator.validate_position(position)
        return func(df, model, position, *args, **kwargs)
    return wrapper

@validate_inputs
def predict_fantasy_points(df: pd.DataFrame, model: Any, position: str) -> pd.DataFrame:
    # Now we know inputs are valid
    ...
```

**Benefits**:
- Fail fast with clear error messages
- Consistent validation across codebase
- Protection against invalid inputs
- Reusable validation logic

**Implementation Effort**: ⏱️ 3 hours

---

## 4. Performance Bottlenecks

### Issue: Redundant Data Loading
**Location**: Feature engineering, model training, predictions
**Severity**: 🟡 Medium
**Impact**: Slow execution, high memory usage, unnecessary I/O

**Current Code**:
```python
# Data loaded multiple times in different functions
def load_position_data(position):
    df = engineer_features_for_season(2024)  # Loads all data
    return df[df['position'] == position]  # Filters after loading

# Called for each position separately
for position in positions:
    df = load_position_data(position)  # Reloads data each time
```

**Proposed Refactoring**:
```python
# src/data/data_cache.py
from functools import lru_cache
from typing import Dict, Optional
import pandas as pd

class DataCache:
    """Centralized data caching to prevent redundant loads."""
    
    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
        self._feature_cache: Dict[tuple, pd.DataFrame] = {}
    
    @lru_cache(maxsize=10)
    def load_season_data(self, season: int) -> pd.DataFrame:
        """Load season data with caching."""
        cache_key = f"season_{season}"
        
        if cache_key not in self._cache:
            logger.info(f"Loading season {season} data from disk")
            self._cache[cache_key] = self._load_from_disk(season)
        else:
            logger.info(f"Using cached data for season {season}")
        
        return self._cache[cache_key].copy()  # Return copy to prevent mutations
    
    def get_position_data(self, season: int, position: str) -> pd.DataFrame:
        """Get data for specific position without reloading."""
        all_data = self.load_season_data(season)
        return all_data[all_data['position'] == position].copy()
    
    def get_engineered_features(self, season: int, feature_set: str) -> pd.DataFrame:
        """Get engineered features with caching."""
        cache_key = (season, feature_set)
        
        if cache_key not in self._feature_cache:
            logger.info(f"Engineering {feature_set} features for season {season}")
            base_data = self.load_season_data(season)
            self._feature_cache[cache_key] = self._engineer_features(base_data, feature_set)
        
        return self._feature_cache[cache_key].copy()
    
    def clear_cache(self):
        """Clear all cached data to free memory."""
        self._cache.clear()
        self._feature_cache.clear()
        self.load_season_data.cache_clear()

# Usage
cache = DataCache()
all_positions_data = cache.load_season_data(2024)

# Process each position without reloading
for position in positions:
    position_data = all_positions_data[all_positions_data['position'] == position]
    # Process position_data
```

**Benefits**:
- Data loaded once and reused
- Significant performance improvement
- Lower memory usage with controlled caching
- Easy to clear cache when needed

**Implementation Effort**: ⏱️ 3 hours

---

### Issue: Inefficient Feature Engineering Loops
**Location**: Feature engineering functions with nested loops
**Severity**: 🟡 Medium
**Impact**: Slow feature generation, especially for large datasets

**Current Code**:
```python
# Inefficient nested loops
for idx, player in df.iterrows():
    for game in player['games']:
        for stat in stats_to_calculate:
            # Calculate each stat individually
            value = calculate_stat(player, game, stat)
            df.at[idx, f"{stat}_game_{game}"] = value
```

**Proposed Refactoring**:
```python
# src/features/vectorized_feature_engineer.py
class VectorizedFeatureEngineer:
    """Efficient feature engineering using vectorized operations."""
    
    def calculate_rolling_stats(self, df: pd.DataFrame, windows: List[int]) -> pd.DataFrame:
        """Calculate rolling statistics efficiently."""
        # Group by player once
        grouped = df.groupby('player_id')
        
        # Vectorized calculations for all windows
        results = []
        for window in windows:
            # Calculate all stats at once for this window
            rolling_stats = grouped[self.NUMERIC_COLUMNS].rolling(
                window=window, min_periods=1
            ).agg(['mean', 'std', 'max'])
            
            # Flatten column names
            rolling_stats.columns = [f'{col}_{stat}_last{window}' 
                                    for col, stat in rolling_stats.columns]
            results.append(rolling_stats)
        
        # Combine all results at once
        return pd.concat(results, axis=1)
    
    def calculate_advanced_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate advanced metrics using vectorized operations."""
        # Avoid iterrows - use vectorized operations
        df['yards_per_target'] = df['receiving_yards'] / df['targets'].replace(0, 1)
        df['yards_per_carry'] = df['rushing_yards'] / df['carries'].replace(0, 1)
        df['td_rate'] = (df['total_tds'] / df['games']).fillna(0)
        
        # Use numpy for complex calculations
        df['efficiency_score'] = np.where(
            df['position'] == 'RB',
            df['yards_per_carry'] * 0.6 + df['yards_per_target'] * 0.4,
            df['yards_per_target'] * 0.8 + df['td_rate'] * 0.2
        )
        
        return df
```

**Benefits**:
- 10-100x faster for large datasets
- Uses pandas/numpy optimized C code
- More readable and maintainable
- Less memory overhead

**Implementation Effort**: ⏱️ 4 hours

---

## 5. Testing & Maintainability

### Issue: Missing Type Hints
**Location**: Throughout codebase
**Severity**: 🟢 Low (but high impact on maintainability)
**Impact**: Hard to understand function contracts, IDE can't help with autocomplete

**Current Code**:
```python
def calculate_value_over_replacement(df_by_pos, include_matchup_adjustments=False):
    # What type is df_by_pos? What does it return?
    ...

def create_visual_draft_board(overall_rankings, position_rankings):
    # What are the expected types?
    ...
```

**Proposed Refactoring**:
```python
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
from pathlib import Path

def calculate_value_over_replacement(
    df_by_pos: Dict[str, pd.DataFrame], 
    include_matchup_adjustments: bool = False
) -> Dict[str, pd.DataFrame]:
    """
    Calculate Value Over Replacement for each position.
    
    Args:
        df_by_pos: Dictionary mapping position strings to DataFrames
        include_matchup_adjustments: Whether to include schedule adjustments
        
    Returns:
        Dictionary mapping positions to DataFrames with VOR columns added
    """
    ...

def create_visual_draft_board(
    overall_rankings: pd.DataFrame,
    position_rankings: Dict[str, pd.DataFrame]
) -> None:
    """
    Create visual draft board charts.
    
    Args:
        overall_rankings: DataFrame with overall player rankings
        position_rankings: Dict mapping positions to their ranking DataFrames
    """
    ...
```

**Benefits**:
- Clear function contracts
- Better IDE support
- Easier to catch type errors
- Self-documenting code

**Implementation Effort**: ⏱️ 2 hours (for critical functions)

---

## 6. Design Pattern Opportunities

### Factory Pattern for Model Creation
**Location**: Model loading and creation logic
**Severity**: 🟡 Medium
**Impact**: Scattered model creation logic, hard to add new model types

**Proposed Refactoring**:
```python
# src/models/model_factory.py
from abc import ABC, abstractmethod
from typing import Any, Dict
import joblib

class ModelFactory:
    """Factory for creating fantasy football models."""
    
    _model_classes = {
        'random_forest': 'RandomForestModel',
        'lightgbm': 'LightGBMModel',
        'ensemble': 'EnsembleModel',
        'baseline': 'BaselineModel'
    }
    
    @classmethod
    def create_model(cls, model_type: str, position: str, **kwargs) -> IFantasyModel:
        """Create a model instance of the specified type."""
        if model_type not in cls._model_classes:
            raise ValueError(f"Unknown model type: {model_type}")
        
        model_class = cls._get_model_class(model_type)
        return model_class(position=position, **kwargs)
    
    @classmethod
    def load_model(cls, model_type: str, position: str, path_manager: PathManager) -> IFantasyModel:
        """Load a trained model from disk."""
        model_path = path_manager.get_model_path(position, model_type)
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        model_data = joblib.load(model_path)
        return cls._reconstruct_model(model_type, model_data)
    
    @classmethod
    def register_model_type(cls, name: str, model_class: type):
        """Register a new model type."""
        cls._model_classes[name] = model_class.__name__
```

**Benefits**:
- Centralized model creation
- Easy to add new model types
- Consistent model interface
- Separation of concerns

**Implementation Effort**: ⏱️ 4 hours

---

### Repository Pattern for Data Access
**Location**: Data loading, saving, and querying
**Severity**: 🟡 Medium
**Impact**: Data access logic scattered throughout codebase

**Proposed Refactoring**:
```python
# src/data/repositories.py
from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd

class IPlayerRepository(ABC):
    """Interface for player data access."""
    
    @abstractmethod
    def get_by_position(self, position: str, season: int) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def get_by_team(self, team: str, season: int) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def save_predictions(self, predictions: pd.DataFrame, season: int) -> None:
        pass

class PlayerRepository(IPlayerRepository):
    """Concrete implementation of player repository."""
    
    def __init__(self, data_cache: DataCache, path_manager: PathManager):
        self.cache = data_cache
        self.paths = path_manager
    
    def get_by_position(self, position: str, season: int) -> pd.DataFrame:
        """Get all players for a position in a season."""
        return self.cache.get_position_data(season, position)
    
    def get_by_team(self, team: str, season: int) -> pd.DataFrame:
        """Get all players for a team in a season."""
        all_data = self.cache.load_season_data(season)
        return all_data[all_data['team'] == team]
    
    def save_predictions(self, predictions: pd.DataFrame, season: int) -> None:
        """Save prediction results."""
        output_path = self.paths.get_data_path('predictions', f'predictions_{season}.parquet')
        predictions.to_parquet(output_path)

# Usage
repo = PlayerRepository(cache, path_manager)
rbs = repo.get_by_position('RB', 2024)
```

**Benefits**:
- Clear data access interface
- Easy to mock for testing
- Centralized data logic
- Can swap implementations

**Implementation Effort**: ⏱️ 6 hours

---

## 7. Technical Debt Priority Matrix

| Refactoring Task | Impact | Effort | Priority | Dependencies |
|------------------|--------|--------|----------|--------------|
| Extract magic numbers to constants | High | Low | 🔥 **Do First** | None |
| Add input validation | High | Low | 🔥 **Do First** | None |
| Create FeatureMapper class | High | Medium | 🔥 **Do First** | None |
| Add comprehensive error handling | High | Medium | 📅 **Plan** | Input validation |
| Implement data caching | High | Medium | 📅 **Plan** | None |
| Break down god functions | High | High | 📅 **Plan** | FeatureMapper |
| Create model interfaces | Medium | Medium | 🎯 **Quick Win** | None |
| Add type hints | Medium | Low | 🎯 **Quick Win** | None |
| Implement path manager | Medium | Medium | 🎯 **Quick Win** | None |
| Vectorize feature engineering | Medium | High | 💭 **Consider** | Data caching |
| Factory pattern for models | Low | Medium | 💭 **Consider** | Model interfaces |
| Repository pattern | Low | High | 💭 **Consider** | Path manager |

---

## 8. Breaking Changes Assessment

### High Risk Refactorings (May Break Existing Code)
1. **Model Interface Changes**: Requires updating all model usage
   - Migration: Create adapter classes first
   - Keep old interface with deprecation warnings

2. **Path Management**: Changes how files are located
   - Migration: Implement alongside old system
   - Gradual transition with fallbacks

### Low Risk Refactorings (Backward Compatible)
1. **Constants Extraction**: Can be done incrementally
2. **Input Validation**: Additive changes only
3. **Error Handling**: Enhances existing code
4. **Type Hints**: No runtime impact

---

## 9. Implementation Roadmap

### Phase 1: Quick Wins (Week 1)
- [ ] Extract magic numbers to constants file
- [ ] Add input validation to main functions
- [ ] Add type hints to public APIs
- [ ] Create basic error handling framework

### Phase 2: Core Refactoring (Week 2-3)
- [ ] Implement FeatureMapper class
- [ ] Create DataCache for performance
- [ ] Break down predict_fantasy_points function
- [ ] Add comprehensive error handling

### Phase 3: Architecture Improvements (Week 4-5)
- [ ] Implement model interfaces and adapters
- [ ] Create PathManager for dependency injection
- [ ] Refactor feature engineering for performance
- [ ] Add comprehensive testing

### Phase 4: Advanced Patterns (Week 6+)
- [ ] Implement factory pattern for models
- [ ] Create repository pattern for data access
- [ ] Build plugin system for new features
- [ ] Complete documentation

---

## 10. Refactoring Checklist

Before starting any refactoring:
- [ ] Current functionality is tested
- [ ] Create feature branch
- [ ] Document current behavior
- [ ] Plan incremental changes

During refactoring:
- [ ] Make one change at a time
- [ ] Run tests after each change
- [ ] Keep old code with deprecation warnings
- [ ] Update documentation

After refactoring:
- [ ] All tests pass
- [ ] Performance benchmarked
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Deprecation timeline set

---

## Anti-patterns to Avoid

1. **God Object**: Don't create new classes that do everything
2. **Primitive Obsession**: Use domain objects, not just dicts/lists
3. **Feature Envy**: Keep related data and behavior together
4. **Shotgun Surgery**: Changes shouldn't require editing many files
5. **Copy-Paste Programming**: Extract common code to shared functions

---

## Conclusion

This refactoring roadmap provides a structured approach to improving the Fantasy Draft Engine codebase. Start with the quick wins to see immediate benefits, then progressively tackle larger architectural improvements. Remember:

- **Incremental Progress**: Small, focused changes are better than large rewrites
- **Maintain Functionality**: Always ensure the system works after each change
- **Test Coverage**: Add tests before refactoring to ensure correctness
- **Documentation**: Update docs as you go, not after

The goal is not perfection, but continuous improvement toward a more maintainable, reliable, and extensible codebase.