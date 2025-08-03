"""
Base model class for fantasy football predictions.

This module contains the base model class that all position-specific models inherit from.
"""

import pandas as pd
import numpy as np
import joblib
import os
from typing import Dict, List, Optional, Union, Tuple
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import lightgbm as lgb
from sklearn.ensemble import RandomForestRegressor


class BaseModel:
    """
    Base model class for fantasy football predictions.
    """
    
    def __init__(self, position: str, model_type: str = 'lightgbm', **kwargs):
        """
        Initialize the base model.
        
        Args:
            position: Player position (QB, RB, WR, TE, K, DST)
            model_type: Type of model to use ('lightgbm' or 'random_forest')
            **kwargs: Additional arguments to pass to the model constructor
        """
        self.position = position
        self.model_type = model_type
        self.model = None
        self.feature_names = None
        self.is_trained = False
        self.model_params = kwargs
        
    def get_position(self) -> str:
        """
        Get the position this model is for.
        
        Returns:
            String representing the position
        """
        return self.position
    
    def get_default_hyperparameters(self) -> Dict:
        """
        Get default hyperparameters for the model.
        
        Returns:
            Dictionary of default hyperparameters
        """
        if self.model_type == 'lightgbm':
            return {
                'learning_rate': 0.05,
                'n_estimators': 100,
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
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 5,
                'min_samples_leaf': 2,
                'max_features': 'sqrt'
            }
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
    
    def preprocess_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess features for the model.
        
        Args:
            X: DataFrame of features
            
        Returns:
            Preprocessed DataFrame
        """
        # Make a copy to avoid modifying the original dataframe
        X_processed = X.copy()
        
        # Handle missing values
        for col in X_processed.columns:
            if X_processed[col].dtype in [np.float64, np.int64]:
                X_processed[col] = X_processed[col].fillna(0)
        
        return X_processed
    
    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> Dict:
        """
        Train the model.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            **kwargs: Additional arguments to pass to the model fit method
            
        Returns:
            Dictionary with training metrics
        """
        # Preprocess features
        X_processed = self.preprocess_features(X)
        self.feature_names = X_processed.columns.tolist()
        
        # Get hyperparameters
        params = self.get_default_hyperparameters()
        params.update(self.model_params)
        
        # Create model
        if self.model_type == 'lightgbm':
            self.model = lgb.LGBMRegressor(**params)
        elif self.model_type == 'random_forest':
            self.model = RandomForestRegressor(**params)
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X_processed, y, test_size=0.2, random_state=42)
        
        # Train model
        self.model.fit(X_train, y_train, **kwargs)
        self.is_trained = True
        
        # Evaluate model
        y_pred = self.model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X_processed, y, cv=5, scoring='r2')
        
        return {
            'rmse': rmse,
            'r2': r2,
            'mae': mae,
            'cv_r2_mean': cv_scores.mean(),
            'cv_r2_std': cv_scores.std()
        }
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions with the trained model.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Array of predictions
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Preprocess features
        X_processed = self.preprocess_features(X)
        
        # Make predictions
        return self.model.predict(X_processed)
    
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
    
    def save(self, filepath: str):
        """
        Save the trained model to disk.
        
        Args:
            filepath: Path to save the model
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save model
        joblib.dump(self.model, filepath)
    
    def load(self, filepath: str):
        """
        Load a trained model from disk.
        
        Args:
            filepath: Path to load the model from
        """
        # Load model
        self.model = joblib.load(filepath)
        self.is_trained = True
