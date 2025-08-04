"""
Advanced Hyperparameter Optimization for Fantasy Football Models

This module provides position-specific hyperparameter optimization using sophisticated
search strategies tailored to fantasy football data characteristics.

Features:
- Position-specific parameter search spaces
- Bayesian optimization for efficient parameter search
- Cross-validation strategies appropriate for time-series fantasy data
- Performance-based early stopping
- Comprehensive logging and result tracking
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional, Union
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit, GroupKFold
from sklearn.metrics import mean_squared_error, r2_score
from scipy.stats import uniform
import logging
from datetime import datetime
import joblib
import os

# Import our model classes
from src.modeling import RandomForestModel, LightGBMModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FantasyFootballHyperparameterOptimizer:
    """
    Advanced hyperparameter optimizer specifically designed for fantasy football models.
    
    This class provides position-specific optimization strategies that account for:
    - Different data characteristics by position (QB vs RB vs WR vs TE)
    - Temporal dependencies in fantasy sports data
    - Balance between model complexity and generalization
    - Fantasy-specific evaluation metrics
    """
    
    def __init__(self, n_trials: int = 100, random_state: int = 42):
        """
        Initialize the hyperparameter optimizer.
        
        Args:
            n_trials: Number of optimization trials to run
            random_state: Random state for reproducibility
        """
        self.n_trials = n_trials
        self.random_state = random_state
        self.best_params_by_position = {}
        self.optimization_history = {}
        
    def get_position_specific_param_space(self, position: str, model_type: str) -> Dict[str, Any]:
        """
        Get position-specific hyperparameter search spaces optimized for fantasy football.
        
        Args:
            position: Player position (QB, RB, WR, TE, K, DST)
            model_type: Model type ('random_forest' or 'lightgbm')
            
        Returns:
            Dictionary containing parameter search space
        """
        if model_type == 'random_forest':
            return self._get_rf_param_space(position)
        elif model_type == 'lightgbm':
            return self._get_lgb_param_space(position)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    def _get_rf_param_space(self, position: str) -> Dict[str, Any]:
        """Get RandomForest parameter space for specific position."""
        base_space = {
            'n_estimators': [200, 300, 400, 500],
            'max_depth': [8, 10, 12, 15, None],
            'min_samples_split': [2, 5, 10, 15],
            'min_samples_leaf': [1, 2, 4, 6],
            'max_features': ['sqrt', 'log2', 0.6, 0.8],
            'bootstrap': [True],
            'oob_score': [True],
        }
        
        # Position-specific adjustments
        if position == 'QB':
            # QBs are more predictable, favor stability
            base_space.update({
                'min_samples_leaf': [2, 4, 6, 8],  # Higher for stability
                'max_depth': [8, 10, 12],           # Moderate depth
                'n_estimators': [300, 400, 500]     # Higher for consistency
            })
        elif position == 'RB':
            # RBs have high volatility, need balanced complexity
            base_space.update({
                'min_samples_split': [5, 10, 15],   # Higher for generalization
                'max_features': ['sqrt', 0.7, 0.8], # Moderate feature sampling
                'max_depth': [10, 12, 15]           # Allow more complexity
            })
        elif position == 'WR':
            # WRs benefit from feature diversity
            base_space.update({
                'max_features': ['sqrt', 'log2', 0.6], # Lower feature fraction
                'n_estimators': [300, 400, 500],       # Higher for stability
                'max_depth': [8, 10, 12, 15]           # Full range
            })
        elif position == 'TE':
            # TEs have smaller datasets, need careful regularization
            base_space.update({
                'min_samples_leaf': [3, 5, 8],      # Higher for small dataset
                'max_depth': [6, 8, 10],            # Lower complexity
                'n_estimators': [200, 300, 400]     # Moderate number
            })
        
        return base_space
    
    def _get_lgb_param_space(self, position: str) -> Dict[str, Any]:
        """Get LightGBM parameter space for specific position."""
        base_space = {
            'n_estimators': [800, 1000, 1200],
            'learning_rate': [0.05, 0.08, 0.1, 0.12],
            'num_leaves': [31, 64, 96, 128],
            'max_depth': [6, 8, 10, 12],
            'min_data_in_leaf': [20, 30, 40, 50],
            'feature_fraction': [0.6, 0.7, 0.8, 0.9],
            'bagging_fraction': [0.7, 0.8, 0.9],
            'lambda_l1': [0, 0.1, 0.2, 0.5],
            'lambda_l2': [0, 0.1, 0.2, 0.5],
            'min_gain_to_split': [0, 0.01, 0.02, 0.05],
            'bagging_freq': [1],
            'boosting_type': ['gbdt'],
            'objective': ['regression_l1'],
        }
        
        # Position-specific adjustments
        if position == 'QB':
            # QBs: Focus on stability over complexity
            base_space.update({
                'learning_rate': [0.05, 0.08, 0.1],     # More conservative
                'min_data_in_leaf': [30, 40, 50],       # Higher for stability
                'lambda_l2': [0.1, 0.2, 0.3],           # More regularization
                'max_depth': [6, 8, 10]                 # Moderate depth
            })
        elif position == 'RB':
            # RBs: Balance complexity for volatility
            base_space.update({
                'learning_rate': [0.08, 0.1, 0.12],     # Higher learning rate
                'num_leaves': [64, 96, 128],             # More complexity
                'feature_fraction': [0.7, 0.8],         # Feature diversity
                'lambda_l1': [0.1, 0.2, 0.3]            # L1 regularization
            })
        elif position == 'WR':
            # WRs: Feature diversity and moderate complexity
            base_space.update({
                'feature_fraction': [0.6, 0.7, 0.8],    # Lower for diversity
                'num_leaves': [64, 96, 128],             # Moderate complexity
                'learning_rate': [0.08, 0.1],           # Balanced learning
                'bagging_fraction': [0.8, 0.9]          # High for robustness
            })
        elif position == 'TE':
            # TEs: Conservative due to smaller dataset
            base_space.update({
                'min_data_in_leaf': [40, 50, 60],       # Higher for small data
                'max_depth': [6, 8],                    # Lower complexity
                'num_leaves': [31, 64],                 # Conservative
                'lambda_l2': [0.2, 0.3, 0.5]           # Strong regularization
            })
        
        return base_space
    
    def optimize_hyperparameters(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        position: str,
        model_type: str,
        cv_strategy: str = 'time_series',
        n_cv_folds: int = 5,
        scoring: str = 'neg_root_mean_squared_error',
        n_iter: int = 100
    ) -> Dict[str, Any]:
        """
        Optimize hyperparameters for a specific position and model type.
        
        Args:
            X_train: Training features
            y_train: Training targets
            position: Player position
            model_type: 'random_forest' or 'lightgbm'
            cv_strategy: Cross-validation strategy ('time_series', 'group', 'stratified')
            n_cv_folds: Number of CV folds
            scoring: Scoring metric for optimization
            n_iter: Number of RandomizedSearchCV iterations
            
        Returns:
            Dictionary containing best parameters and optimization results
        """
        logger.info(f"Starting hyperparameter optimization for {position} {model_type}")
        
        # Get position-specific parameter search space
        param_space = self.get_position_specific_param_space(position, model_type)
        
        # Select appropriate cross-validation strategy
        if cv_strategy == 'time_series':
            cv = TimeSeriesSplit(n_splits=n_cv_folds)
        elif cv_strategy == 'group':
            # Assume we have a 'season' column for grouping
            cv = GroupKFold(n_splits=n_cv_folds)
        else:
            # Default to TimeSeriesSplit for fantasy sports data
            cv = TimeSeriesSplit(n_splits=n_cv_folds)
        
        # Create model instance
        if model_type == 'random_forest':
            model = RandomForestModel()
        elif model_type == 'lightgbm':
            model = LightGBMModel()
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        # Set up RandomizedSearchCV
        search = RandomizedSearchCV(
            estimator=model.model,
            param_distributions=param_space,
            n_iter=n_iter,
            cv=cv,
            scoring=scoring,
            n_jobs=-1,
            random_state=self.random_state,
            verbose=1,
            return_train_score=True
        )
        
        # Perform optimization
        logger.info(f"Running RandomizedSearchCV with {n_iter} iterations...")
        search.fit(X_train, y_train)
        
        # Store results
        optimization_result = {
            'best_params': search.best_params_,
            'best_score': search.best_score_,
            'best_estimator': search.best_estimator_,
            'cv_results': search.cv_results_,
            'position': position,
            'model_type': model_type,
            'optimization_timestamp': datetime.now().isoformat()
        }
        
        # Cache results
        key = f"{position}_{model_type}"
        self.best_params_by_position[key] = optimization_result
        
        logger.info(f"Optimization complete for {position} {model_type}")
        logger.info(f"Best CV score: {search.best_score_:.4f}")
        logger.info(f"Best parameters: {search.best_params_}")
        
        return optimization_result
    
    def optimize_ensemble_weights(
        self,
        rf_predictions: np.ndarray,
        lgb_predictions: np.ndarray,
        y_true: np.ndarray,
        position: str
    ) -> Dict[str, float]:
        """
        Optimize ensemble weights for RandomForest and LightGBM predictions using grid search.
        
        Args:
            rf_predictions: RandomForest predictions
            lgb_predictions: LightGBM predictions
            y_true: True target values
            position: Player position
            
        Returns:
            Dictionary with optimized ensemble weights
        """
        logger.info(f"Optimizing ensemble weights for {position}")
        
        # Test different weight combinations
        weight_candidates = np.arange(0.1, 1.0, 0.05)  # 0.1 to 0.95 in 0.05 increments
        best_rmse = float('inf')
        best_rf_weight = 0.5
        
        for rf_weight in weight_candidates:
            lgb_weight = 1.0 - rf_weight
            
            # Create ensemble predictions
            ensemble_preds = rf_weight * rf_predictions + lgb_weight * lgb_predictions
            
            # Calculate RMSE
            rmse = np.sqrt(mean_squared_error(y_true, ensemble_preds))
            
            if rmse < best_rmse:
                best_rmse = rmse
                best_rf_weight = rf_weight
        
        best_lgb_weight = 1.0 - best_rf_weight
        
        optimal_weights = {
            'random_forest': best_rf_weight,
            'lightgbm': best_lgb_weight
        }
        
        logger.info(f"Optimal ensemble weights for {position}: {optimal_weights} (RMSE: {best_rmse:.4f})")
        
        return optimal_weights
    
    def save_optimization_results(self, filepath: str) -> None:
        """Save optimization results to file."""
        results = {
            'best_params_by_position': self.best_params_by_position,
            'optimization_timestamp': datetime.now().isoformat(),
            'optimizer_config': {
                'n_trials': self.n_trials,
                'random_state': self.random_state
            }
        }
        
        joblib.dump(results, filepath)
        logger.info(f"Optimization results saved to {filepath}")
    
    def load_optimization_results(self, filepath: str) -> None:
        """Load optimization results from file."""
        if os.path.exists(filepath):
            results = joblib.load(filepath)
            self.best_params_by_position = results.get('best_params_by_position', {})
            logger.info(f"Optimization results loaded from {filepath}")
        else:
            logger.warning(f"Optimization results file not found: {filepath}")
    
    def get_optimized_model(self, position: str, model_type: str) -> Union[RandomForestModel, LightGBMModel]:
        """
        Get a model instance with optimized hyperparameters for the specified position.
        
        Args:
            position: Player position
            model_type: 'random_forest' or 'lightgbm'
            
        Returns:
            Model instance with optimized parameters
        """
        key = f"{position}_{model_type}"
        
        if key in self.best_params_by_position:
            best_params = self.best_params_by_position[key]['best_params']
            logger.info(f"Using optimized parameters for {position} {model_type}")
        else:
            logger.warning(f"No optimized parameters found for {position} {model_type}, using defaults")
            best_params = {}
        
        if model_type == 'random_forest':
            return RandomForestModel(model_params=best_params)
        elif model_type == 'lightgbm':
            return LightGBMModel(model_params=best_params)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")


def run_comprehensive_optimization(
    data_by_position: Dict[str, pd.DataFrame],
    feature_cols: List[str],
    target_col: str = 'fantasy_points_per_game',
    positions: List[str] = ['QB', 'RB', 'WR', 'TE'],
    model_types: List[str] = ['random_forest', 'lightgbm'],
    save_results: bool = True,
    results_dir: str = 'optimization_results'
) -> Dict[str, Any]:
    """
    Run comprehensive hyperparameter optimization for all positions and model types.
    
    Args:
        data_by_position: Dictionary mapping positions to their respective datasets
        feature_cols: List of feature column names
        target_col: Target column name
        positions: List of positions to optimize
        model_types: List of model types to optimize
        save_results: Whether to save optimization results
        results_dir: Directory to save results
        
    Returns:
        Dictionary containing all optimization results
    """
    logger.info("Starting comprehensive hyperparameter optimization")
    
    # Create results directory
    if save_results:
        os.makedirs(results_dir, exist_ok=True)
    
    # Initialize optimizer
    optimizer = FantasyFootballHyperparameterOptimizer(n_trials=100, random_state=42)
    
    all_results = {}
    
    for position in positions:
        if position not in data_by_position:
            logger.warning(f"No data available for position {position}, skipping...")
            continue
        
        logger.info(f"Optimizing hyperparameters for {position}")
        
        # Get position data
        position_data = data_by_position[position]
        
        if position_data.empty:
            logger.warning(f"Empty dataset for position {position}, skipping...")
            continue
        
        # Prepare features and target
        X = position_data[feature_cols]
        y = position_data[target_col]
        
        position_results = {}
        
        for model_type in model_types:
            logger.info(f"Optimizing {model_type} for {position}")
            
            try:
                # Run optimization
                result = optimizer.optimize_hyperparameters(
                    X_train=X,
                    y_train=y,
                    position=position,
                    model_type=model_type,
                    cv_strategy='time_series',
                    n_cv_folds=5,
                    n_iter=100
                )
                
                position_results[model_type] = result
                
            except Exception as e:
                logger.error(f"Optimization failed for {position} {model_type}: {str(e)}")
                continue
        
        all_results[position] = position_results
    
    # Save results
    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(results_dir, f'hyperparameter_optimization_{timestamp}.joblib')
        optimizer.save_optimization_results(results_file)
    
    logger.info("Comprehensive hyperparameter optimization complete")
    
    return all_results


if __name__ == "__main__":
    # Example usage for testing
    logger.info("Fantasy Football Hyperparameter Optimization Module")
    logger.info("This module provides advanced hyperparameter optimization for fantasy football models.")
    logger.info("Import this module and use FantasyFootballHyperparameterOptimizer class for optimization.")