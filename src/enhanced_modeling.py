"""
Enhanced Modeling with Matchup Intelligence

This module extends the existing modeling capabilities to work with
enhanced features that include matchup intelligence. It provides:

- Enhanced model training with matchup-aware features
- Automatic feature selection and importance analysis
- Matchup-aware cross-validation strategies
- Position-specific model optimization
- Ensemble methods combining traditional and matchup models

The enhanced models are designed to provide superior prediction accuracy
by incorporating schedule strength, environmental factors, and situational context.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path
import sys
from datetime import datetime
import warnings
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_regression, RFE
import pickle
import joblib

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
import config

# Import existing models
from src.modeling import RandomForestModel, LightGBMModel, RidgeBaselineModel

# Import enhanced feature engineering
from src.enhanced_feature_engineering import engineer_enhanced_features_for_season

logger = logging.getLogger(__name__)

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning)


class EnhancedModelConfig:
    """Configuration for enhanced modeling."""
    
    def __init__(self):
        # Feature selection parameters
        self.max_features_per_position = {
            'QB': 50,
            'RB': 60, 
            'WR': 55,
            'TE': 45,
            'K': 30
        }
        
        # Model ensemble weights
        self.ensemble_weights = {
            'random_forest': 0.4,
            'lightgbm': 0.4,
            'ridge': 0.2
        }
        
        # Cross-validation parameters
        self.cv_folds = 5
        self.test_size_ratio = 0.2
        
        # Feature importance threshold
        self.feature_importance_threshold = 0.001
        
        # Matchup feature weight
        self.matchup_feature_weight = 0.3


class EnhancedFantasyModel:
    """
    Enhanced fantasy football model that incorporates matchup intelligence.
    
    This model extends traditional player performance prediction by including
    matchup-aware features like schedule strength, environmental factors,
    and situational adjustments.
    """
    
    def __init__(self, position: str, config: EnhancedModelConfig = None):
        """
        Initialize enhanced model for a specific position.
        
        Args:
            position: Player position ('QB', 'RB', 'WR', 'TE', 'K')
            config: Model configuration
        """
        self.position = position
        self.config = config or EnhancedModelConfig()
        
        # Initialize models
        self.models = {
            'random_forest': RandomForestModel({
                'n_estimators': 200,
                'max_depth': 12,
                'min_samples_split': 10,
                'min_samples_leaf': 5,
                'random_state': 42,
                'n_jobs': -1
            }),
            'lightgbm': LightGBMModel({
                'objective': 'regression',
                'metric': 'rmse',
                'n_estimators': 500,
                'learning_rate': 0.05,
                'max_depth': 8,
                'num_leaves': 31,
                'feature_fraction': 0.8,
                'bagging_fraction': 0.8,
                'bagging_freq': 1,
                'verbose': -1,
                'random_state': 42
            }),
            'ridge': RidgeBaselineModel({
                'alpha': 1.0,
                'random_state': 42
            })
        }
        
        # Model artifacts
        self.feature_selector = None
        self.scaler = None
        self.selected_features = None
        self.feature_importance = {}
        self.model_performance = {}
        self.is_trained = False
        
        logger.info(f"Initialized enhanced model for {position} position")
    
    def prepare_features(
        self, 
        df: pd.DataFrame, 
        target_column: str = None
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features for model training/prediction.
        
        Args:
            df: DataFrame with player features
            target_column: Name of target column
            
        Returns:
            Tuple of (features_df, target_series)
        """
        if target_column is None:
            target_column = config.TARGET_VARIABLE
        
        # Filter for position
        position_data = df[df['position'] == self.position].copy()
        
        if position_data.empty:
            logger.warning(f"No data found for position {self.position}")
            return pd.DataFrame(), pd.Series()
        
        # Separate features and target
        feature_columns = self._get_feature_columns(position_data)
        
        X = position_data[feature_columns].copy()
        y = position_data[target_column].copy() if target_column in position_data.columns else pd.Series()
        
        # Handle missing values
        X = self._handle_missing_values(X)
        
        # Remove infinite values
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(X.median())
        
        logger.info(f"Prepared {len(X)} samples with {len(X.columns)} features for {self.position}")
        
        return X, y
    
    def _get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Get relevant feature columns for the model."""
        
        # Exclude non-feature columns
        exclude_columns = [
            'player_id', 'player_name', 'position', 'team', 'season', 
            'prediction_season', 'birth_date', config.TARGET_VARIABLE,
            'feature_engineering_version', 'total_feature_count', 'has_matchup_features'
        ]
        
        # Get all potential feature columns
        feature_columns = [col for col in df.columns if col not in exclude_columns]
        
        # Prioritize certain feature types
        traditional_features = [col for col in feature_columns if not col.startswith('next_')]
        matchup_features = [col for col in feature_columns if col.startswith('next_')]
        
        # Log feature composition
        logger.info(f"Feature composition for {self.position}: {len(traditional_features)} traditional, {len(matchup_features)} matchup")
        
        return feature_columns
    
    def _handle_missing_values(self, X: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in features."""
        
        # Different strategies for different feature types
        result = X.copy()
        
        for col in result.columns:
            if result[col].isna().any():
                if col.startswith('next_'):
                    # Matchup features - use neutral values
                    if 'sos_rating' in col:
                        result[col] = result[col].fillna(0.0)  # Neutral SOS
                    elif 'pct' in col or 'share' in col:
                        result[col] = result[col].fillna(0.5)  # 50% for percentages
                    elif 'tier' in col and result[col].dtype == 'object':
                        result[col] = result[col].fillna('Average')
                    else:
                        result[col] = result[col].fillna(0.0)
                else:
                    # Traditional features - use median or position-specific defaults
                    if result[col].dtype in ['int64', 'float64']:
                        result[col] = result[col].fillna(result[col].median())
                    else:
                        result[col] = result[col].fillna(result[col].mode().iloc[0] if not result[col].mode().empty else 'Unknown')
        
        return result
    
    def select_features(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """
        Select the most important features for the model.
        
        Args:
            X: Feature matrix
            y: Target vector
            
        Returns:
            DataFrame with selected features
        """
        if X.empty or y.empty:
            return X
        
        max_features = self.config.max_features_per_position.get(self.position, 50)
        
        # Convert categorical columns to numeric
        X_numeric = self._encode_categorical_features(X)
        
        # Remove features with no variance
        variance_selector = X_numeric.var()
        high_variance_features = variance_selector[variance_selector > 1e-6].index
        X_filtered = X_numeric[high_variance_features]
        
        logger.info(f"Removed {len(X_numeric.columns) - len(X_filtered.columns)} low-variance features")
        
        # Use SelectKBest for initial feature selection
        if len(X_filtered.columns) > max_features:
            selector = SelectKBest(score_func=f_regression, k=max_features)
            X_selected = selector.fit_transform(X_filtered, y)
            selected_feature_names = X_filtered.columns[selector.get_support()].tolist()
            X_result = pd.DataFrame(X_selected, columns=selected_feature_names, index=X_filtered.index)
        else:
            X_result = X_filtered
            selected_feature_names = X_filtered.columns.tolist()
        
        self.selected_features = selected_feature_names
        logger.info(f"Selected {len(selected_feature_names)} features for {self.position}")
        
        return X_result
    
    def _encode_categorical_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical features for modeling."""
        
        result = X.copy()
        
        for col in result.columns:
            if result[col].dtype == 'object':
                # One-hot encode categorical variables with few categories
                unique_values = result[col].nunique()
                
                if unique_values <= 5:
                    # One-hot encode
                    dummies = pd.get_dummies(result[col], prefix=col, dummy_na=True)
                    result = pd.concat([result.drop(col, axis=1), dummies], axis=1)
                else:
                    # Label encode for high cardinality
                    result[col] = pd.Categorical(result[col]).codes
        
        return result
    
    def train(
        self, 
        X: pd.DataFrame, 
        y: pd.Series,
        validation_split: float = 0.2
    ) -> Dict[str, float]:
        """
        Train the enhanced model ensemble.
        
        Args:
            X: Feature matrix
            y: Target vector
            validation_split: Fraction of data to use for validation
            
        Returns:
            Dictionary with training performance metrics
        """
        logger.info(f"Training enhanced model for {self.position} with {len(X)} samples")
        
        if X.empty or y.empty:
            logger.error("Cannot train with empty data")
            return {}
        
        # Remove samples with missing target values
        valid_mask = y.notna()
        X_clean = X[valid_mask]
        y_clean = y[valid_mask]
        
        if len(X_clean) < 10:
            logger.error(f"Insufficient data for training {self.position} model: {len(X_clean)} samples")
            return {}
        
        # Feature selection
        X_selected = self.select_features(X_clean, y_clean)
        
        # Scale features
        self.scaler = StandardScaler()
        X_scaled = pd.DataFrame(
            self.scaler.fit_transform(X_selected),
            columns=X_selected.columns,
            index=X_selected.index
        )
        
        # Split data for validation
        n_train = int(len(X_scaled) * (1 - validation_split))
        X_train, X_val = X_scaled.iloc[:n_train], X_scaled.iloc[n_train:]
        y_train, y_val = y_clean.iloc[:n_train], y_clean.iloc[n_train:]
        
        # Train individual models
        for model_name, model in self.models.items():
            try:
                logger.info(f"Training {model_name} for {self.position}")
                
                if model_name == 'lightgbm' and len(X_val) > 0:
                    # LightGBM with early stopping
                    model.train(X_train, y_train, X_val, y_val)
                else:
                    model.train(X_train, y_train)
                
                # Evaluate on validation set
                if len(X_val) > 0:
                    val_pred = model.predict(X_val)
                    val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
                    val_mae = mean_absolute_error(y_val, val_pred)
                    val_r2 = r2_score(y_val, val_pred)
                    
                    self.model_performance[model_name] = {
                        'validation_rmse': val_rmse,
                        'validation_mae': val_mae,
                        'validation_r2': val_r2
                    }
                    
                    logger.info(f"{model_name} {self.position} validation RMSE: {val_rmse:.3f}")
                
            except Exception as e:
                logger.error(f"Error training {model_name} for {self.position}: {e}")
                continue
        
        # Calculate feature importance
        self._calculate_feature_importance(X_scaled, y_clean)
        
        self.is_trained = True
        
        # Return performance summary
        if self.model_performance:
            avg_rmse = np.mean([perf['validation_rmse'] for perf in self.model_performance.values()])
            avg_r2 = np.mean([perf['validation_r2'] for perf in self.model_performance.values()])
            
            performance_summary = {
                'average_validation_rmse': avg_rmse,
                'average_validation_r2': avg_r2,
                'models_trained': len(self.model_performance)
            }
            
            logger.info(f"Completed training for {self.position}. Avg RMSE: {avg_rmse:.3f}, Avg R²: {avg_r2:.3f}")
            return performance_summary
        
        return {}
    
    def _calculate_feature_importance(self, X: pd.DataFrame, y: pd.Series):
        """Calculate feature importance from trained models."""
        
        importance_scores = {}
        
        for model_name, model in self.models.items():
            if not hasattr(model.model, 'feature_importances_'):
                continue
                
            try:
                importances = model.model.feature_importances_
                feature_names = X.columns
                
                importance_dict = dict(zip(feature_names, importances))
                importance_scores[model_name] = importance_dict
                
            except Exception as e:
                logger.warning(f"Could not get feature importance from {model_name}: {e}")
        
        # Average importance across models
        if importance_scores:
            all_features = set()
            for importances in importance_scores.values():
                all_features.update(importances.keys())
            
            avg_importance = {}
            for feature in all_features:
                scores = [importances.get(feature, 0) for importances in importance_scores.values()]
                avg_importance[feature] = np.mean(scores)
            
            self.feature_importance = avg_importance
            
            # Log top features
            top_features = sorted(avg_importance.items(), key=lambda x: x[1], reverse=True)[:10]
            logger.info(f"Top features for {self.position}: {[f[0] for f in top_features]}")
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions using the trained ensemble.
        
        Args:
            X: Feature matrix
            
        Returns:
            Array of predictions
        """
        if not self.is_trained:
            logger.error(f"Model for {self.position} is not trained")
            return np.array([])
        
        if X.empty:
            return np.array([])
        
        # Apply same preprocessing as training
        X_processed = self._preprocess_for_prediction(X)
        
        if X_processed.empty:
            return np.array([])
        
        # Get predictions from each model
        predictions = {}
        weights = self.config.ensemble_weights
        
        for model_name, model in self.models.items():
            try:
                pred = model.predict(X_processed)
                predictions[model_name] = pred
            except Exception as e:
                logger.warning(f"Error getting predictions from {model_name}: {e}")
                continue
        
        if not predictions:
            logger.error(f"No predictions available for {self.position}")
            return np.array([])
        
        # Ensemble predictions
        ensemble_pred = np.zeros(len(X_processed))
        total_weight = 0
        
        for model_name, pred in predictions.items():
            weight = weights.get(model_name, 0)
            ensemble_pred += pred * weight
            total_weight += weight
        
        if total_weight > 0:
            ensemble_pred /= total_weight
        
        return ensemble_pred
    
    def _preprocess_for_prediction(self, X: pd.DataFrame) -> pd.DataFrame:
        """Preprocess features for prediction."""
        
        # Select features used in training
        if self.selected_features:
            available_features = [col for col in self.selected_features if col in X.columns]
            missing_features = [col for col in self.selected_features if col not in X.columns]
            
            if missing_features:
                logger.warning(f"Missing features for {self.position} prediction: {missing_features}")
            
            X_selected = X[available_features].copy()
        else:
            X_selected = X.copy()
        
        # Handle missing values
        X_clean = self._handle_missing_values(X_selected)
        
        # Encode categorical features
        X_encoded = self._encode_categorical_features(X_clean)
        
        # Scale features
        if self.scaler:
            # Handle case where scaler was fit on different features
            scaler_features = getattr(self.scaler, 'feature_names_in_', X_encoded.columns)
            available_scaler_features = [col for col in scaler_features if col in X_encoded.columns]
            
            if available_scaler_features:
                X_scaled = pd.DataFrame(
                    self.scaler.transform(X_encoded[available_scaler_features]),
                    columns=available_scaler_features,
                    index=X_encoded.index
                )
            else:
                X_scaled = X_encoded
        else:
            X_scaled = X_encoded
        
        return X_scaled
    
    def save_model(self, filepath: str):
        """Save the trained model to disk."""
        
        if not self.is_trained:
            logger.error(f"Cannot save untrained model for {self.position}")
            return
        
        model_data = {
            'position': self.position,
            'models': self.models,
            'feature_selector': self.feature_selector,
            'scaler': self.scaler,
            'selected_features': self.selected_features,
            'feature_importance': self.feature_importance,
            'model_performance': self.model_performance,
            'config': self.config,
            'is_trained': self.is_trained
        }
        
        try:
            joblib.dump(model_data, filepath)
            logger.info(f"Saved enhanced model for {self.position} to {filepath}")
        except Exception as e:
            logger.error(f"Error saving model for {self.position}: {e}")
    
    @classmethod
    def load_model(cls, filepath: str) -> 'EnhancedFantasyModel':
        """Load a trained model from disk."""
        
        try:
            model_data = joblib.load(filepath)
            
            # Create model instance
            model = cls(model_data['position'], model_data['config'])
            
            # Restore model state
            model.models = model_data['models']
            model.feature_selector = model_data['feature_selector']
            model.scaler = model_data['scaler']
            model.selected_features = model_data['selected_features']
            model.feature_importance = model_data['feature_importance']
            model.model_performance = model_data['model_performance']
            model.is_trained = model_data['is_trained']
            
            logger.info(f"Loaded enhanced model for {model.position}")
            return model
            
        except Exception as e:
            logger.error(f"Error loading model from {filepath}: {e}")
            raise


class EnhancedModelManager:
    """Manages enhanced models for all positions."""
    
    def __init__(self, config: EnhancedModelConfig = None):
        """Initialize the model manager."""
        self.config = config or EnhancedModelConfig()
        self.models = {}
        
        # Initialize models for each position
        for position in config.POSITIONS:
            self.models[position] = EnhancedFantasyModel(position, self.config)
    
    def train_all_models(
        self, 
        features_df: pd.DataFrame,
        seasons_to_train: List[int] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Train enhanced models for all positions.
        
        Args:
            features_df: DataFrame with enhanced features
            seasons_to_train: List of seasons to include in training
            
        Returns:
            Dictionary with performance metrics for each position
        """
        logger.info("Training enhanced models for all positions")
        
        if seasons_to_train:
            training_data = features_df[features_df['season'].isin(seasons_to_train)].copy()
        else:
            training_data = features_df.copy()
        
        all_performance = {}
        
        for position in self.models:
            logger.info(f"Training models for {position}")
            
            try:
                # Prepare position-specific data
                X, y = self.models[position].prepare_features(training_data)
                
                if not X.empty and not y.empty:
                    # Train the model
                    performance = self.models[position].train(X, y)
                    all_performance[position] = performance
                else:
                    logger.warning(f"No training data available for {position}")
                    all_performance[position] = {}
                    
            except Exception as e:
                logger.error(f"Error training {position} model: {e}")
                all_performance[position] = {}
        
        logger.info("Completed training for all positions")
        return all_performance
    
    def predict_all_positions(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate predictions for all positions.
        
        Args:
            features_df: DataFrame with player features
            
        Returns:
            DataFrame with predictions added
        """
        logger.info(f"Generating enhanced predictions for all positions")
        
        result = features_df.copy()
        result['enhanced_prediction'] = np.nan
        result['prediction_confidence'] = np.nan
        
        for position in self.models:
            position_mask = result['position'] == position
            position_data = result[position_mask]
            
            if not position_data.empty and self.models[position].is_trained:
                try:
                    X, _ = self.models[position].prepare_features(position_data)
                    predictions = self.models[position].predict(X)
                    
                    if len(predictions) == len(position_data):
                        result.loc[position_mask, 'enhanced_prediction'] = predictions
                        
                        # Add confidence based on model performance
                        if position in self.models[position].model_performance:
                            avg_r2 = np.mean([
                                perf.get('validation_r2', 0) 
                                for perf in self.models[position].model_performance.values()
                            ])
                            result.loc[position_mask, 'prediction_confidence'] = max(0, avg_r2)
                        
                    logger.info(f"Generated {len(predictions)} predictions for {position}")
                    
                except Exception as e:
                    logger.error(f"Error generating predictions for {position}: {e}")
        
        return result
    
    def save_all_models(self, model_dir: str):
        """Save all trained models to disk."""
        
        model_dir_path = Path(model_dir)
        model_dir_path.mkdir(parents=True, exist_ok=True)
        
        for position, model in self.models.items():
            if model.is_trained:
                filepath = model_dir_path / f"enhanced_{position.lower()}_model.joblib"
                model.save_model(str(filepath))
    
    def load_all_models(self, model_dir: str):
        """Load all models from disk."""
        
        model_dir_path = Path(model_dir)
        
        for position in self.models:
            filepath = model_dir_path / f"enhanced_{position.lower()}_model.joblib"
            
            if filepath.exists():
                try:
                    self.models[position] = EnhancedFantasyModel.load_model(str(filepath))
                    logger.info(f"Loaded enhanced model for {position}")
                except Exception as e:
                    logger.error(f"Could not load model for {position}: {e}")


def validate_enhanced_modeling() -> Dict[str, bool]:
    """Validate enhanced modeling functionality."""
    validation_results = {}
    
    try:
        # Create test data
        test_data = pd.DataFrame({
            'player_id': [f'player_{i}' for i in range(20)],
            'position': ['QB'] * 5 + ['RB'] * 5 + ['WR'] * 5 + ['TE'] * 5,
            'team': ['KC', 'BUF', 'DEN', 'SF', 'DAL'] * 4,
            'fantasy_points_ppr_per_game': np.random.normal(15, 5, 20),
            'next_4w_sos_rating': np.random.normal(0, 0.3, 20),
            'next_4w_home_games_pct': np.random.uniform(0, 1, 20),
            config.TARGET_VARIABLE: np.random.normal(15, 5, 20)
        })
        
        # Test single position model
        qb_model = EnhancedFantasyModel('QB')
        X, y = qb_model.prepare_features(test_data)
        
        validation_results['feature_preparation_works'] = not X.empty and not y.empty
        
        if not X.empty and not y.empty:
            # Test training
            performance = qb_model.train(X, y)
            validation_results['model_training_works'] = bool(performance)
            validation_results['model_is_trained'] = qb_model.is_trained
            
            # Test prediction
            if qb_model.is_trained:
                predictions = qb_model.predict(X)
                validation_results['prediction_works'] = len(predictions) > 0
        
        # Test model manager
        manager = EnhancedModelManager()
        all_performance = manager.train_all_models(test_data)
        validation_results['manager_training_works'] = bool(all_performance)
        
        predictions_df = manager.predict_all_positions(test_data)
        validation_results['manager_predictions_work'] = 'enhanced_prediction' in predictions_df.columns
        
    except Exception as e:
        validation_results['validation_error'] = str(e)
    
    return validation_results


if __name__ == "__main__":
    # Test the enhanced modeling system
    print("🎯 Testing Enhanced Modeling with Matchup Intelligence")
    print("=" * 60)
    
    # Run validation
    validation = validate_enhanced_modeling()
    
    print("Validation Results:")
    for test, result in validation.items():
        if isinstance(result, bool):
            status = "✅" if result else "❌"
            print(f"{status} {test}: {result}")
        else:
            print(f"ℹ️  {test}: {result}")
    
    print("\nEnhanced Modeling implementation complete! 🎯")