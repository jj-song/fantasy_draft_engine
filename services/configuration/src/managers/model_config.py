"""
Model-related configuration for the Fantasy Draft Engine.

This module contains all configuration related to machine learning models,
hyperparameters, ensemble settings, and player archetype classifications.
"""

from typing import Dict, Any, List, Union
from .base_config import BaseConfig


class ModelConfig(BaseConfig):
    """
    Configuration for machine learning models and training.
    
    This class manages model hyperparameters, ensemble weights,
    player archetype classifications, and model evaluation settings.
    """
    
    def _initialize(self) -> None:
        """Initialize model configuration values."""
        
        # Default model ensemble weights
        self.model_weights = {
            'lightgbm': 0.5,
            'random_forest': 0.5,
        }
        
        # Position-specific optimized hyperparameters for Random Forest
        self.random_forest_params = {
            'QB': {
                'n_estimators': 400,
                'max_depth': 10,
                'min_samples_split': 5,
                'min_samples_leaf': 4,
                'max_features': 'sqrt',
                'bootstrap': True,
                'oob_score': True,
                'random_state': 42,
                'n_jobs': -1
            },
            'RB': {
                'n_estimators': 300,
                'max_depth': 12,
                'min_samples_split': 8,
                'min_samples_leaf': 2,
                'max_features': 0.8,
                'bootstrap': True,
                'oob_score': True,
                'random_state': 42,
                'n_jobs': -1
            },
            'WR': {
                'n_estimators': 400,
                'max_depth': 12,
                'min_samples_split': 5,
                'min_samples_leaf': 2,
                'max_features': 'sqrt',
                'bootstrap': True,
                'oob_score': True,
                'random_state': 42,
                'n_jobs': -1
            },
            'TE': {
                'n_estimators': 300,
                'max_depth': 8,
                'min_samples_split': 8,
                'min_samples_leaf': 5,
                'max_features': 'sqrt',
                'bootstrap': True,
                'oob_score': True,
                'random_state': 42,
                'n_jobs': -1
            }
        }
        
        # Position-specific optimized hyperparameters for LightGBM
        self.lightgbm_params = {
            'QB': {
                'objective': 'regression_l1',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'n_estimators': 1000,
                'learning_rate': 0.08,
                'num_leaves': 64,
                'max_depth': 8,
                'min_data_in_leaf': 40,
                'feature_fraction': 0.8,
                'bagging_fraction': 0.85,
                'bagging_freq': 1,
                'lambda_l1': 0.1,
                'lambda_l2': 0.2,
                'min_gain_to_split': 0.01,
                'verbose': -1,
                'n_jobs': -1,
                'seed': 42,
                'force_col_wise': True,
            },
            'RB': {
                'objective': 'regression_l1',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'n_estimators': 1000,
                'learning_rate': 0.1,
                'num_leaves': 96,
                'max_depth': 10,
                'min_data_in_leaf': 25,
                'feature_fraction': 0.75,
                'bagging_fraction': 0.8,
                'bagging_freq': 1,
                'lambda_l1': 0.2,
                'lambda_l2': 0.1,
                'min_gain_to_split': 0.02,
                'verbose': -1,
                'n_jobs': -1,
                'seed': 42,
                'force_col_wise': True,
            },
            'WR': {
                'objective': 'regression_l1',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'n_estimators': 1000,
                'learning_rate': 0.08,
                'num_leaves': 96,
                'max_depth': 10,
                'min_data_in_leaf': 30,
                'feature_fraction': 0.7,
                'bagging_fraction': 0.85,
                'bagging_freq': 1,
                'lambda_l1': 0.1,
                'lambda_l2': 0.1,
                'min_gain_to_split': 0.01,
                'verbose': -1,
                'n_jobs': -1,
                'seed': 42,
                'force_col_wise': True,
            },
            'TE': {
                'objective': 'regression_l1',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'n_estimators': 800,
                'learning_rate': 0.08,
                'num_leaves': 64,
                'max_depth': 8,
                'min_data_in_leaf': 50,
                'feature_fraction': 0.8,
                'bagging_fraction': 0.9,
                'bagging_freq': 1,
                'lambda_l1': 0.1,
                'lambda_l2': 0.3,
                'min_gain_to_split': 0.02,
                'verbose': -1,
                'n_jobs': -1,
                'seed': 42,
                'force_col_wise': True,
            }
        }
        
        # Dynamic ensemble weighting based on player context
        self.dynamic_ensemble_weights = {
            'QB': {
                'veteran_stable': {'random_forest': 0.6, 'lightgbm': 0.4},
                'young_developing': {'random_forest': 0.4, 'lightgbm': 0.6},
                'high_volatility': {'random_forest': 0.5, 'lightgbm': 0.5},
                'default': {'random_forest': 0.5, 'lightgbm': 0.5}
            },
            'RB': {
                'workhorse': {'random_forest': 0.6, 'lightgbm': 0.4},
                'committee_back': {'random_forest': 0.4, 'lightgbm': 0.6},
                'pass_catching': {'random_forest': 0.45, 'lightgbm': 0.55},
                'goal_line': {'random_forest': 0.65, 'lightgbm': 0.35},
                'default': {'random_forest': 0.5, 'lightgbm': 0.5}
            },
            'WR': {
                'target_hog': {'random_forest': 0.55, 'lightgbm': 0.45},
                'big_play': {'random_forest': 0.4, 'lightgbm': 0.6},
                'possession': {'random_forest': 0.6, 'lightgbm': 0.4},
                'rookie_developing': {'random_forest': 0.35, 'lightgbm': 0.65},
                'default': {'random_forest': 0.5, 'lightgbm': 0.5}
            },
            'TE': {
                'elite_tier': {'random_forest': 0.55, 'lightgbm': 0.45},
                'receiving_specialist': {'random_forest': 0.45, 'lightgbm': 0.55},
                'blocking_hybrid': {'random_forest': 0.6, 'lightgbm': 0.4},
                'matchup_dependent': {'random_forest': 0.4, 'lightgbm': 0.6},
                'default': {'random_forest': 0.5, 'lightgbm': 0.5}
            }
        }
        
        # Player archetype classification thresholds
        self.player_archetype_thresholds = {
            'QB': {
                'veteran_stable': {'min_experience': 3, 'max_cv_fppg': 0.3},
                'young_developing': {'max_experience': 2, 'min_games': 8},
                'high_volatility': {'min_cv_fppg': 0.4}
            },
            'RB': {
                'workhorse': {'min_carries_per_game': 15, 'min_touch_share': 0.6},
                'committee_back': {'max_carries_per_game': 12, 'max_touch_share': 0.45},
                'pass_catching': {'min_targets_per_game': 4, 'min_target_share': 0.1},
                'goal_line': {'min_red_zone_carries': 3, 'max_carries_per_game': 10}
            },
            'WR': {
                'target_hog': {'min_target_share': 0.25, 'min_targets_per_game': 8},
                'big_play': {'min_adot': 12, 'min_yards_per_target': 8},
                'possession': {'max_adot': 8, 'min_catch_rate': 0.7},
                'rookie_developing': {'max_experience': 1, 'min_draft_round': 1, 'max_draft_round': 3}
            },
            'TE': {
                'elite_tier': {'min_target_share': 0.15, 'min_targets_per_game': 6},
                'receiving_specialist': {'min_routes_per_snap': 0.7, 'max_blocking_snaps': 0.3},
                'blocking_hybrid': {'min_blocking_snaps': 0.4, 'max_targets_per_game': 4},
                'matchup_dependent': {'min_cv_targets': 0.5, 'max_target_share': 0.12}
            }
        }
        
        # Model evaluation thresholds
        self.evaluation_thresholds = {
            'min_rmse': {'QB': 3.5, 'RB': 3.0, 'WR': 3.0, 'TE': 2.5},  # Maximum acceptable RMSE
            'min_r2': {'QB': 0.6, 'RB': 0.65, 'WR': 0.65, 'TE': 0.6},  # Minimum R² score
            'min_rank_correlation': 0.75,  # Minimum Spearman correlation for rankings
            'max_training_time_minutes': 30,  # Maximum training time per model
        }
        
        # Cross-validation settings
        self.cv_settings = {
            'n_splits': 5,              # Number of CV folds
            'shuffle': True,            # Shuffle data before splitting
            'random_state': 42,         # Random state for reproducibility
            'test_size': 0.2,          # Holdout test set size
            'validation_strategy': 'time_series',  # 'time_series' or 'random'
        }
        
        # Feature selection settings
        self.feature_selection = {
            'enable_selection': True,              # Whether to perform feature selection
            'selection_method': 'importance',      # 'importance', 'correlation', 'recursive'
            'max_features': 100,                   # Maximum number of features to use
            'min_importance_threshold': 0.001,     # Minimum feature importance to keep
            'correlation_threshold': 0.95,         # Correlation threshold for redundant features
        }
        
        # Model persistence settings
        self.persistence_settings = {
            'save_models': True,           # Whether to save trained models
            'model_format': 'joblib',      # 'joblib' or 'pickle'
            'save_feature_names': True,    # Save feature names with models
            'save_training_metadata': True, # Save training metadata
            'compression_level': 3,        # Compression level for saved models
        }
        
        # Hyperparameter optimization settings
        self.hyperopt_settings = {
            'enable_optimization': False,  # Whether to run hyperparameter optimization
            'optimization_method': 'bayesian',  # 'grid', 'random', 'bayesian'
            'n_trials': 100,               # Number of optimization trials
            'optimization_metric': 'rmse', # Metric to optimize
            'timeout_minutes': 120,        # Timeout for optimization
        }
        
        # Environment-specific overrides
        if self.environment == 'test':
            self._apply_test_overrides()
        elif self.environment == 'production':
            self._apply_production_overrides()
    
    def _apply_test_overrides(self) -> None:
        """Apply test-specific configuration overrides."""
        # Reduce model complexity for faster tests
        for pos in self.random_forest_params:
            self.random_forest_params[pos]['n_estimators'] = 50
            self.random_forest_params[pos]['n_jobs'] = 1
        
        for pos in self.lightgbm_params:
            self.lightgbm_params[pos]['n_estimators'] = 100
            self.lightgbm_params[pos]['n_jobs'] = 1
        
        # Reduce evaluation requirements for tests
        self.evaluation_thresholds['max_training_time_minutes'] = 5
        self.cv_settings['n_splits'] = 3
        self.hyperopt_settings['n_trials'] = 10
        self.hyperopt_settings['timeout_minutes'] = 5
    
    def _apply_production_overrides(self) -> None:
        """Apply production-specific configuration overrides."""
        # Use more conservative parallel processing
        for pos in self.random_forest_params:
            self.random_forest_params[pos]['n_jobs'] = 8
        
        for pos in self.lightgbm_params:
            self.lightgbm_params[pos]['n_jobs'] = 8
        
        # Enable hyperparameter optimization in production
        self.hyperopt_settings['enable_optimization'] = True
        self.hyperopt_settings['n_trials'] = 200
    
    def _validate(self) -> None:
        """Validate model configuration values."""
        
        # Validate required fields
        required_fields = [
            'model_weights', 'random_forest_params', 'lightgbm_params',
            'evaluation_thresholds', 'cv_settings'
        ]
        self.validate_required_fields(required_fields)
        
        # Validate types
        type_mapping = {
            'model_weights': dict,
            'random_forest_params': dict,
            'lightgbm_params': dict,
            'dynamic_ensemble_weights': dict,
            'player_archetype_thresholds': dict,
            'evaluation_thresholds': dict,
            'cv_settings': dict,
            'feature_selection': dict
        }
        self.validate_types(type_mapping)
        
        # Validate model weights sum to 1
        weight_sum = sum(self.model_weights.values())
        if abs(weight_sum - 1.0) > 0.01:
            raise ValueError(f"Model weights must sum to 1.0, got {weight_sum}")
        
        # Validate position coverage
        required_positions = ['QB', 'RB', 'WR', 'TE']
        for pos in required_positions:
            if pos not in self.random_forest_params:
                raise ValueError(f"Missing Random Forest parameters for {pos}")
            if pos not in self.lightgbm_params:
                raise ValueError(f"Missing LightGBM parameters for {pos}")
        
        # Validate evaluation thresholds
        self._validate_evaluation_thresholds()
    
    def _validate_evaluation_thresholds(self) -> None:
        """Validate model evaluation threshold values."""
        # Check RMSE thresholds
        for pos, rmse in self.evaluation_thresholds['min_rmse'].items():
            if rmse <= 0 or rmse > 10:
                raise ValueError(f"RMSE threshold for {pos} ({rmse}) is unreasonable")
        
        # Check R² thresholds
        for pos, r2 in self.evaluation_thresholds['min_r2'].items():
            if r2 <= 0 or r2 >= 1:
                raise ValueError(f"R² threshold for {pos} ({r2}) must be between 0 and 1")
        
        # Check rank correlation
        rank_corr = self.evaluation_thresholds['min_rank_correlation']
        if rank_corr <= 0 or rank_corr > 1:
            raise ValueError(f"Rank correlation threshold ({rank_corr}) must be between 0 and 1")
    
    def get_model_params(self, model_type: str, position: str) -> Dict[str, Any]:
        """
        Get hyperparameters for a specific model type and position.
        
        Args:
            model_type: 'random_forest' or 'lightgbm'
            position: Player position
            
        Returns:
            Dictionary of hyperparameters
        """
        position = position.upper()
        
        if model_type == 'random_forest':
            params_dict = self.random_forest_params
        elif model_type == 'lightgbm':
            params_dict = self.lightgbm_params
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        if position not in params_dict:
            raise ValueError(f"No parameters defined for {model_type} {position}")
        
        return params_dict[position].copy()
    
    def get_ensemble_weights(self, position: str, archetype: str = None) -> Dict[str, float]:
        """
        Get ensemble weights for a position and optional player archetype.
        
        Args:
            position: Player position
            archetype: Optional player archetype
            
        Returns:
            Dictionary of model weights
        """
        position = position.upper()
        
        if archetype and position in self.dynamic_ensemble_weights:
            pos_weights = self.dynamic_ensemble_weights[position]
            if archetype in pos_weights:
                return pos_weights[archetype].copy()
            else:
                return pos_weights.get('default', self.model_weights.copy())
        
        return self.model_weights.copy()
    
    def classify_player_archetype(self, position: str, player_stats: Dict[str, Any]) -> str:
        """
        Classify a player's archetype based on their statistics.
        
        Args:
            position: Player position
            player_stats: Dictionary of player statistics
            
        Returns:
            Player archetype string
        """
        position = position.upper()
        
        if position not in self.player_archetype_thresholds:
            return 'default'
        
        pos_thresholds = self.player_archetype_thresholds[position]
        
        # Check each archetype's criteria
        for archetype, criteria in pos_thresholds.items():
            if self._meets_archetype_criteria(player_stats, criteria):
                return archetype
        
        return 'default'
    
    def _meets_archetype_criteria(self, player_stats: Dict[str, Any], 
                                 criteria: Dict[str, Union[int, float]]) -> bool:
        """
        Check if player stats meet archetype criteria.
        
        Args:
            player_stats: Player statistics
            criteria: Archetype criteria thresholds
            
        Returns:
            True if player meets all criteria
        """
        for criterion, threshold in criteria.items():
            stat_key = criterion.replace('min_', '').replace('max_', '')
            
            if stat_key not in player_stats:
                return False
            
            player_value = player_stats[stat_key]
            
            if criterion.startswith('min_') and player_value < threshold:
                return False
            elif criterion.startswith('max_') and player_value > threshold:
                return False
        
        return True
    
    def get_evaluation_threshold(self, metric: str, position: str = None) -> Union[float, Dict[str, float]]:
        """
        Get evaluation threshold for a metric.
        
        Args:
            metric: Metric name ('min_rmse', 'min_r2', etc.)
            position: Optional position for position-specific thresholds
            
        Returns:
            Threshold value or dictionary of thresholds by position
        """
        if metric not in self.evaluation_thresholds:
            raise ValueError(f"Unknown evaluation metric: {metric}")
        
        threshold = self.evaluation_thresholds[metric]
        
        if position and isinstance(threshold, dict):
            return threshold.get(position.upper(), 0.0)
        
        return threshold
    
    def should_use_feature_selection(self) -> bool:
        """Check if feature selection should be enabled."""
        return self.feature_selection.get('enable_selection', False)
    
    def get_max_features(self, total_features: int) -> int:
        """
        Get maximum number of features to use after selection.
        
        Args:
            total_features: Total number of available features
            
        Returns:
            Maximum features to use
        """
        max_configured = self.feature_selection.get('max_features', 100)
        return min(max_configured, total_features)
    
    def should_optimize_hyperparameters(self) -> bool:
        """Check if hyperparameter optimization should be run."""
        return (self.hyperopt_settings.get('enable_optimization', False) and 
                not self.is_test())
    
    def get_cv_strategy(self) -> Dict[str, Any]:
        """Get cross-validation strategy configuration."""
        return self.cv_settings.copy()
    
    def get_available_model_types(self) -> List[str]:
        """Get list of available model types."""
        return ['random_forest', 'lightgbm']
    
    def get_supported_positions(self) -> List[str]:
        """Get list of positions with model parameters."""
        return list(self.random_forest_params.keys())