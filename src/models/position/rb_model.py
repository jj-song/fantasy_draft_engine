"""
Running back (RB) position-specific model.

This module contains the RB-specific model class for predicting fantasy points.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
from sklearn.ensemble import RandomForestRegressor
import lightgbm as lgb

from fantasy_football_ai_tool.src.models.base_model import BaseModel


class RBModel(BaseModel):
    """
    RB-specific model for predicting fantasy points per game (FPPG).
    
    This model is specifically tuned for running backs, focusing on 
    features that are most predictive for the RB position.
    """
    
    def __init__(self, model_type: str = 'lightgbm', **kwargs):
        """
        Initialize the RB model.
        
        Args:
            model_type: Type of model to use ('lightgbm' or 'random_forest')
            **kwargs: Additional arguments to pass to the model constructor
        """
        super().__init__(position='RB', model_type=model_type, **kwargs)
        
    def get_position(self) -> str:
        """
        Get the position this model is for.
        
        Returns:
            String representing the position ('RB')
        """
        return 'RB'
    
    def get_feature_importance(self) -> pd.DataFrame:
        """
        Get feature importance from the trained model.
        
        Returns:
            DataFrame with feature names and importance scores
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before getting feature importance")
        
        if self.model_type == 'lightgbm':
            importance = self.model.feature_importances_
            feature_names = self.model.feature_name_
        elif self.model_type == 'random_forest':
            importance = self.model.feature_importances_
            feature_names = self.feature_names
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
        
        feature_importance = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        return feature_importance
    
    def get_rb_specific_features(self) -> List[str]:
        """
        Get a list of RB-specific features that are most important for this position.
        
        Returns:
            List of feature names that are particularly important for RBs
        """
        # These would typically be determined through feature importance analysis
        # and domain knowledge about what drives RB fantasy production
        rb_specific_features = [
            # Usage metrics
            'rushing_attempts_per_game',
            'team_rush_attempt_share',
            'touches_per_game',
            'team_touch_share',
            'targets_per_game',
            'receptions_per_game',
            'red_zone_opportunity_share',
            
            # Efficiency metrics
            'yards_per_carry',
            'yards_per_touch',
            'rushing_td_rate',
            'catch_rate',
            'yards_per_reception',
            'yards_per_target',
            
            # Production metrics
            'rushing_yards_per_game',
            'rushing_tds_per_game',
            'receiving_yards_per_game',
            'receiving_tds_per_game',
            'total_yards_per_game',
            'total_tds_per_game',
            
            # Player attributes
            'age',
            'experience',
            'draft_pick_number'
        ]
        
        return rb_specific_features
    
    def get_default_hyperparameters(self) -> Dict:
        """
        Get default hyperparameters for the RB model.
        
        Returns:
            Dictionary of default hyperparameters
        """
        if self.model_type == 'lightgbm':
            return {
                'learning_rate': 0.05,
                'n_estimators': 200,
                'max_depth': 5,
                'num_leaves': 31,
                'min_child_samples': 20,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'reg_alpha': 0.1,
                'reg_lambda': 0.1
            }
        elif self.model_type == 'random_forest':
            return {
                'n_estimators': 200,
                'max_depth': 15,
                'min_samples_split': 5,
                'min_samples_leaf': 2,
                'max_features': 'sqrt'
            }
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
    
    def preprocess_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess features specifically for the RB model.
        
        Args:
            X: DataFrame of features
            
        Returns:
            Preprocessed DataFrame
        """
        # Make a copy to avoid modifying the original dataframe
        X_processed = X.copy()
        
        # Apply any RB-specific preprocessing here
        # For example, we might want to create interaction terms
        # between usage and efficiency metrics
        
        if 'rushing_attempts_per_game' in X_processed.columns and 'yards_per_carry' in X_processed.columns:
            X_processed['expected_rushing_yards_per_game'] = X_processed['rushing_attempts_per_game'] * X_processed['yards_per_carry']
        
        if 'targets_per_game' in X_processed.columns and 'yards_per_target' in X_processed.columns:
            X_processed['expected_receiving_yards_per_game'] = X_processed['targets_per_game'] * X_processed['yards_per_target']
        
        return X_processed
