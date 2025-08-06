"""
Simplified Ensemble Fantasy Football Model for Microservices

This module provides a streamlined ensemble model optimized for the microservices
architecture with complete 2010-2024 historical data training.
"""

import pandas as pd
import numpy as np
import joblib
import logging
from typing import Dict, Any, Tuple, Optional, List
import os
from datetime import datetime

# Use sklearn directly for the ensemble model
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnsembleFantasyModel:
    """
    Simplified ensemble model using RandomForest for fantasy football predictions.
    
    This version is streamlined for the microservices architecture and focuses
    on reliable training with the complete 2010-2024 historical dataset.
    """
    
    def __init__(self, position: str):
        """
        Initialize ensemble model for a specific position.
        
        Args:
            position: Player position (QB, RB, WR, TE)
        """
        self.position = position
        self.model = RandomForestRegressor(
            n_estimators=50,          # Reduced to prevent overfitting
            max_depth=6,              # Shallower trees to reduce complexity
            min_samples_split=20,     # Higher threshold to prevent overspecialization
            min_samples_leaf=10,      # Larger leaf sizes to smooth predictions
            max_features=0.7,         # Use subset of features to reduce overfitting
            random_state=42,
            n_jobs=-1
        )
        self.is_trained = False
        self.feature_names = []
        self.preprocessor = None
        
        logger.info(f"🤖 ENSEMBLE MODEL INITIALIZATION: {position}")
        logger.info("Using RandomForest with optimized hyperparameters")
    
    def train(self, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, Any]:
        """
        Train the ensemble model.
        
        Args:
            X_train: Training feature matrix
            y_train: Training target values
            X_val: Validation feature matrix
            y_val: Validation target values
            
        Returns:
            Training metrics
        """
        logger.info(f"🎯 Starting training for {self.position}")
        logger.info(f"Training data shape: {X_train.shape}")
        logger.info(f"Validation data shape: {X_val.shape}")
        logger.info(f"Target range: {y_train.min():.2f} - {y_train.max():.2f}")
        
        # Store feature names
        self.feature_names = list(X_train.columns)
        
        # Identify categorical columns (object dtype or contains string values)
        categorical_cols = []
        numerical_cols = []
        
        for col in X_train.columns:
            if X_train[col].dtype == 'object' or X_train[col].dtype.name == 'string':
                categorical_cols.append(col)
                logger.info(f"Found categorical column: {col} (sample values: {X_train[col].dropna().head(3).tolist()})")
            else:
                # Check if numeric column actually contains strings
                sample_vals = X_train[col].dropna().head(100)
                if any(isinstance(val, str) for val in sample_vals):
                    categorical_cols.append(col)
                    logger.info(f"Found string values in numeric column: {col} (sample values: {sample_vals.head(3).tolist()})")
                else:
                    numerical_cols.append(col)
        
        logger.info(f"Identified {len(categorical_cols)} categorical columns and {len(numerical_cols)} numerical columns")
        
        # Set up preprocessing pipeline
        if categorical_cols:
            from sklearn.preprocessing import OneHotEncoder
            from sklearn.compose import ColumnTransformer
            
            preprocessor = ColumnTransformer([
                ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_cols),
                ('num', 'passthrough', numerical_cols)
            ])
            
            # Fit and transform training data
            logger.info("Applying categorical encoding...")
            X_train_processed = preprocessor.fit_transform(X_train)
            X_val_processed = preprocessor.transform(X_val)
            
            # Convert back to DataFrame for consistency
            feature_names = (preprocessor.named_transformers_['cat'].get_feature_names_out(categorical_cols).tolist() + 
                           numerical_cols)
            X_train_processed = pd.DataFrame(X_train_processed, columns=feature_names)
            X_val_processed = pd.DataFrame(X_val_processed, columns=feature_names)
            
            self.preprocessor = preprocessor
            logger.info(f"After preprocessing: {X_train_processed.shape[1]} features")
        else:
            X_train_processed = X_train
            X_val_processed = X_val
        
        # Train the model
        logger.info(f"Training on {len(X_train_processed)} samples, validating on {len(X_val_processed)} samples")
        self.model.fit(X_train_processed, y_train)
        self.is_trained = True
        
        # Calculate metrics
        train_pred = self.model.predict(X_train_processed)
        val_pred = self.model.predict(X_val_processed)
        
        train_rmse = np.sqrt(mean_squared_error(y_train, train_pred))
        val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
        train_r2 = r2_score(y_train, train_pred)
        val_r2 = r2_score(y_val, val_pred)
        
        # Calculate overfitting indicators
        rmse_ratio = val_rmse / train_rmse if train_rmse > 0 else float('inf')
        r2_diff = train_r2 - val_r2
        
        metrics = {
            'train_rmse': train_rmse,
            'val_rmse': val_rmse,
            'train_r2': train_r2,
            'val_r2': val_r2,
            'rmse_ratio': rmse_ratio,
            'r2_difference': r2_diff,
            'feature_count': len(self.feature_names),
            'sample_count': len(X_train) + len(X_val),
            'overfitting_detected': rmse_ratio > 1.3 or r2_diff > 0.1 or val_r2 > 0.85
        }
        
        logger.info(f"✅ Training completed for {self.position}")
        logger.info(f"Training RMSE: {metrics['train_rmse']:.3f}")
        logger.info(f"Validation RMSE: {metrics['val_rmse']:.3f}")
        logger.info(f"Validation R²: {metrics['val_r2']:.3f}")
        logger.info(f"RMSE Ratio (val/train): {metrics['rmse_ratio']:.3f}")
        logger.info(f"R² Difference (train-val): {metrics['r2_difference']:.3f}")
        
        # Issue overfitting warning
        if metrics['overfitting_detected']:
            logger.warning("⚠️ OVERFITTING DETECTED!")
            logger.warning(f"   - RMSE Ratio: {metrics['rmse_ratio']:.3f} (should be < 1.3)")
            logger.warning(f"   - R² Difference: {metrics['r2_difference']:.3f} (should be < 0.1)")
            logger.warning(f"   - Validation R²: {metrics['val_r2']:.3f} (should be < 0.85 for realistic models)")
        else:
            logger.info("✅ Model validation passed - no overfitting detected")
        
        return metrics
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Generate predictions.
        
        Args:
            X: Feature matrix
            
        Returns:
            Predictions
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Apply preprocessing if it was used during training
        if self.preprocessor is not None:
            X_processed = self.preprocessor.transform(X)
        else:
            X_processed = X
            
        return self.model.predict(X_processed)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before getting feature importance")
        
        importance_dict = dict(zip(self.feature_names, self.model.feature_importances_))
        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
    
    def save(self, filepath: str):
        """
        Save the trained model.
        
        Args:
            filepath: Path to save the model
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")
        
        model_data = {
            'model': self.model,
            'position': self.position,
            'feature_names': self.feature_names,
            'is_trained': self.is_trained,
            'preprocessor': self.preprocessor
        }
        
        joblib.dump(model_data, filepath)
        logger.info(f"✅ Model saved to {filepath}")
    
    def load(self, filepath: str):
        """
        Load a trained model.
        
        Args:
            filepath: Path to load the model from
        """
        model_data = joblib.load(filepath)
        
        self.model = model_data['model']
        self.position = model_data['position']
        self.feature_names = model_data['feature_names']
        self.is_trained = model_data['is_trained']
        self.preprocessor = model_data.get('preprocessor', None)
        
        logger.info(f"✅ Model loaded from {filepath}")