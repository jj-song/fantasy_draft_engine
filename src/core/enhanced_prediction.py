"""
Enhanced Prediction Module with Refactored Components

This module demonstrates how to integrate the refactored components (constants,
feature mapping, validation, error handling) into the existing prediction
functions with improved type safety and error handling.

This serves as a bridge between the old monolithic functions and the new
modular architecture, showing how to gradually refactor the codebase.
"""

from typing import Optional, Union, Any, List, Dict
import pandas as pd
import numpy as np
import logging

# Import our new refactored components
from src.constants.fantasy_constants import (
    FANTASY_DEFAULTS, VOR_CONFIG, VALIDATION_THRESHOLDS, VALID_POSITIONS
)
from src.core.feature_mapper import FeatureMapper, map_features_for_model
from src.validators.input_validators import InputValidator, validate_inputs
from src.exceptions.fantasy_exceptions import (
    PredictionError, FeatureMappingError, ModelCompatibilityError,
    create_prediction_range_error, FantasyErrorContext
)
from src.core.type_annotations import (
    PlayerDataFrame, PositionType, PredictionArray, FantasyModel,
    PredictionResult, ValidationResult
)

logger = logging.getLogger(__name__)


class EnhancedPredictor:
    """Enhanced prediction class using refactored components.
    
    This class demonstrates how to use the new refactored components together
    to create cleaner, more maintainable prediction logic.
    """
    
    def __init__(self, target_year: int = None):
        """Initialize the enhanced predictor.
        
        Args:
            target_year: Year for predictions (defaults to FANTASY_DEFAULTS.PREDICTION_YEAR)
        """
        self.target_year = target_year or FANTASY_DEFAULTS.PREDICTION_YEAR
        self.feature_mapper = FeatureMapper(target_year=self.target_year)
    
    @validate_inputs(df_param='df', position_param='position', model_param='model')
    def predict_fantasy_points(self,
                             df: PlayerDataFrame,
                             model: FantasyModel,
                             position: PositionType,
                             target_col: str = 'fantasy_points_per_game') -> PlayerDataFrame:
        """Enhanced prediction function with comprehensive error handling.
        
        This function replaces the 355-line monolithic predict_fantasy_points
        function with a cleaner, more maintainable version that uses our
        refactored components.
        
        Args:
            df: Input player DataFrame
            model: Trained model for predictions
            position: Player position
            target_col: Target column name for predictions
            
        Returns:
            DataFrame with predictions added
            
        Raises:
            PredictionError: If prediction fails
            FeatureMappingError: If feature mapping fails
            ModelCompatibilityError: If model is incompatible with data
        """
        with FantasyErrorContext("enhanced_prediction", position=position, players=len(df)):
            logger.info(f"Starting enhanced prediction for {len(df)} {position} players")
            
            # Step 1: Validate and prepare features
            try:
                prepared_features = self._prepare_features(df, model, position)
                logger.info(f"Successfully prepared {len(prepared_features.columns)} features")
            except Exception as e:
                raise FeatureMappingError(f"Feature preparation failed: {e}")
            
            # Step 2: Make predictions with the model
            try:
                raw_predictions = self._make_model_predictions(prepared_features, model, position)
                logger.info(f"Generated {len(raw_predictions)} raw predictions")
            except Exception as e:
                raise PredictionError(f"Model prediction failed: {e}")
            
            # Step 3: Post-process and validate predictions
            try:
                processed_predictions = self._post_process_predictions(
                    df, raw_predictions, position, target_col
                )
                logger.info(f"Successfully processed predictions for {position}")
            except Exception as e:
                raise PredictionError(f"Prediction post-processing failed: {e}")
            
            return processed_predictions
    
    def _prepare_features(self, 
                         df: PlayerDataFrame, 
                         model: FantasyModel, 
                         position: PositionType) -> pd.DataFrame:
        """Prepare features for model input using FeatureMapper.
        
        Args:
            df: Input DataFrame
            model: Model requiring features
            position: Player position
            
        Returns:
            DataFrame with mapped features
        """
        # Get expected features from model
        expected_features = self._get_model_features(model)
        
        # Log feature analysis
        self._log_feature_analysis(df, expected_features, position)
        
        # Map features using our FeatureMapper
        try:
            mapped_features = self.feature_mapper.map_features(df, expected_features, position)
        except Exception as e:
            # Get mapping info for better error message
            mapping_info = self.feature_mapper.get_mapping_info(df, expected_features, position)
            missing_features = mapping_info['missing']
            
            if len(missing_features) > len(expected_features) * 0.5:
                raise ModelCompatibilityError(
                    f"Too many missing features ({len(missing_features)}/{len(expected_features)}) "
                    f"for {position} model",
                    expected_features=len(expected_features),
                    provided_features=len(expected_features) - len(missing_features),
                    missing_features=missing_features
                )
            else:
                logger.warning(f"Some features missing, proceeding with defaults: {missing_features}")
                mapped_features = self.feature_mapper.map_features(df, expected_features, position)
        
        # Validate mapped features
        self._validate_prepared_features(mapped_features, expected_features)
        
        return mapped_features
    
    def _make_model_predictions(self,
                               features: pd.DataFrame,
                               model: FantasyModel,
                               position: PositionType) -> PredictionArray:
        """Make predictions with the model.
        
        Args:
            features: Prepared feature matrix
            model: Trained model
            position: Player position
            
        Returns:
            Array of predictions
        """
        # Handle different model types
        if hasattr(model, 'predict'):
            if hasattr(model, 'rf_model') and hasattr(model, 'lgb_model'):
                # Ensemble model - may need additional context
                try:
                    # Try ensemble prediction with context
                    context_data = self._create_model_context(features, position)
                    predictions = model.predict(features, context_data)
                except Exception as e:
                    logger.warning(f"Ensemble prediction with context failed: {e}, trying without context")
                    predictions = model.predict(features)
            else:
                # Single model
                predictions = model.predict(features)
        else:
            raise ModelCompatibilityError(f"Model for {position} has no predict method")
        
        # Validate predictions
        validated_predictions = InputValidator.validate_predictions(
            predictions, position, expected_length=len(features)
        )
        
        return validated_predictions
    
    def _post_process_predictions(self,
                                original_df: PlayerDataFrame,
                                predictions: PredictionArray,
                                position: PositionType,
                                target_col: str) -> PlayerDataFrame:
        """Post-process predictions and add to DataFrame.
        
        Args:
            original_df: Original input DataFrame
            predictions: Model predictions
            position: Player position
            target_col: Target column name
            
        Returns:
            DataFrame with processed predictions
        """
        result_df = original_df.copy()
        
        # Scale predictions if needed (per-game to seasonal)
        if target_col == 'fantasy_points_per_game':
            # Convert per-game predictions to seasonal totals
            scaled_predictions = predictions * FANTASY_DEFAULTS.DEFAULT_GAMES_IN_SEASON
            result_df['predicted_points'] = scaled_predictions
            logger.info(f"Scaled per-game predictions to seasonal totals")
        else:
            result_df['predicted_points'] = predictions
        
        # Validate prediction ranges
        self._validate_prediction_ranges(result_df['predicted_points'], position)
        
        # Add confidence indicators
        result_df['prediction_confidence'] = self._calculate_confidence_scores(
            result_df, position
        )
        
        return result_df
    
    def _get_model_features(self, model: FantasyModel) -> List[str]:
        """Extract expected features from model.
        
        Args:
            model: Model object
            
        Returns:
            List of expected feature names
        """
        if hasattr(model, 'feature_names_in_'):
            return list(model.feature_names_in_)
        elif hasattr(model, 'feature_name_'):
            return list(model.feature_name_)
        elif hasattr(model, 'model') and hasattr(model.model, 'feature_names_in_'):
            return list(model.model.feature_names_in_)
        else:
            raise ModelCompatibilityError("Cannot determine expected features from model")
    
    def _log_feature_analysis(self,
                            df: PlayerDataFrame,
                            expected_features: List[str],
                            position: PositionType) -> None:
        """Log comprehensive feature analysis.
        
        Args:
            df: Input DataFrame
            expected_features: Expected feature names
            position: Player position
        """
        logger.info(f"Feature Analysis for {position}:")
        logger.info(f"  Input columns: {len(df.columns)}")
        logger.info(f"  Expected features: {len(expected_features)}")
        
        # Analyze feature categories
        matchup_features = [f for f in df.columns if 'next_' in f or 'sos_' in f]
        opportunity_features = [f for f in df.columns if any(x in f.lower() 
                               for x in ['target_share', 'air_yards', 'wopr'])]
        usage_features = [f for f in df.columns if any(x in f.lower() 
                         for x in ['snap_share', 'route_participation'])]
        
        logger.info(f"  Matchup features: {len(matchup_features)}")
        logger.info(f"  Opportunity features: {len(opportunity_features)}")
        logger.info(f"  Usage features: {len(usage_features)}")
    
    def _validate_prepared_features(self,
                                  features: pd.DataFrame,
                                  expected_features: List[str]) -> None:
        """Validate that feature preparation was successful.
        
        Args:
            features: Prepared feature DataFrame
            expected_features: Expected feature names
        """
        # Check all expected features are present
        missing_features = set(expected_features) - set(features.columns)
        if missing_features:
            raise FeatureMappingError(f"Missing features after mapping: {missing_features}")
        
        # Check for excessive null values
        null_ratios = features.isnull().sum() / len(features)
        high_null_features = null_ratios[null_ratios > 0.5]
        
        if not high_null_features.empty:
            logger.warning(f"Features with high null rates: {high_null_features.to_dict()}")
        
        # Ensure all features are numeric
        non_numeric = features.select_dtypes(exclude=[np.number]).columns
        if len(non_numeric) > 0:
            logger.warning(f"Non-numeric features detected: {list(non_numeric)}")
    
    def _create_model_context(self,
                            features: pd.DataFrame,
                            position: PositionType) -> pd.DataFrame:
        """Create context data for ensemble models.
        
        Args:
            features: Feature matrix
            position: Player position
            
        Returns:
            Context DataFrame for dynamic weighting
        """
        context = pd.DataFrame({
            'position': [position] * len(features),
            'feature_count': [len(features.columns)] * len(features)
        })
        
        # Add position-specific context
        if position == 'RB':
            if 'carries' in features.columns:
                context['carries'] = features['carries']
        elif position in ['WR', 'TE']:
            if 'targets' in features.columns:
                context['targets'] = features['targets']
        
        return context
    
    def _validate_prediction_ranges(self,
                                  predictions: pd.Series,
                                  position: PositionType) -> None:
        """Validate that predictions are within reasonable ranges.
        
        Args:
            predictions: Prediction values
            position: Player position
        """
        min_val, max_val = VALIDATION_THRESHOLDS.get_position_range(position)
        out_of_range = ((predictions < min_val) | (predictions > max_val)).sum()
        
        if out_of_range > len(predictions) * 0.1:  # More than 10% out of range
            logger.warning(
                f"{out_of_range}/{len(predictions)} {position} predictions "
                f"outside typical range ({min_val}-{max_val})"
            )
    
    def _calculate_confidence_scores(self,
                                   df: PlayerDataFrame,
                                   position: PositionType) -> pd.Series:
        """Calculate confidence scores for predictions.
        
        Args:
            df: DataFrame with predictions
            position: Player position
            
        Returns:
            Series with confidence scores (0-1)
        """
        # Base confidence on data quality indicators
        confidence = pd.Series(0.7, index=df.index)  # Base confidence
        
        # Adjust based on games played
        if 'games' in df.columns:
            games_factor = np.clip(df['games'] / FANTASY_DEFAULTS.DEFAULT_GAMES_IN_SEASON, 0.5, 1.0)
            confidence *= games_factor
        
        # Adjust based on age (younger players less predictable)
        if 'age' in df.columns:
            age_factor = np.where(df['age'] < 25, 0.9, 1.0)  # Rookie discount
            age_factor = np.where(df['age'] > 30, 0.95, age_factor)  # Veteran reliability
            confidence *= age_factor
        
        return confidence.clip(0.1, 0.95)


# Legacy function wrapper for backward compatibility
def enhanced_predict_fantasy_points(df: PlayerDataFrame,
                                  model: FantasyModel,
                                  position: PositionType,
                                  target_col: str = 'fantasy_points_per_game') -> PlayerDataFrame:
    """Legacy wrapper for the enhanced prediction function.
    
    This function provides backward compatibility while using the new
    enhanced prediction logic internally.
    """
    predictor = EnhancedPredictor()
    return predictor.predict_fantasy_points(df, model, position, target_col)


if __name__ == "__main__":
    # Demo of enhanced prediction system
    print("Enhanced Prediction System Demo")
    print("=" * 50)
    
    # Create sample data
    sample_data = pd.DataFrame({
        'player_name': ['Josh Allen', 'Derrick Henry', 'Cooper Kupp'],
        'position': ['QB', 'RB', 'WR'],
        'birth_date': ['1996-05-21', '1996-06-07', '1993-06-15'],
        'games': [16, 14, 17],
        'carries': [0, 287, 5],
        'passing_yards': [4283, 0, 0],
        'targets': [0, 85, 145],
        'receptions': [0, 70, 128]
    })
    
    print("Sample data created:")
    print(sample_data)
    
    # Test feature mapping
    predictor = EnhancedPredictor()
    expected_features = ['age', 'games', 'carries', 'targets']
    
    try:
        mapped = predictor.feature_mapper.map_features(sample_data, expected_features, 'RB')
        print(f"\n✅ Feature mapping successful: {len(mapped.columns)} features")
        print(mapped.head())
    except Exception as e:
        print(f"❌ Feature mapping failed: {e}")
    
    print("\n✅ Enhanced prediction system ready!")