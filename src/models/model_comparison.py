"""
Clean Model Comparison Class for Fantasy Football ML Pipeline

This replaces the corrupted model_comparison.py with a clean, working implementation.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import lightgbm as lgb
import joblib
import os
from typing import Dict, Any, Optional
import matplotlib.pyplot as plt


class ModelComparison:
    """Clean model comparison class for position-specific fantasy football predictions."""
    
    def __init__(self, position: str):
        """
        Initialize the model comparison.
        
        Args:
            position: Player position (QB, RB, WR, TE, K)
        """
        self.position = position
        self.models = {}
        self.results = {}
        self.best_model = None
        self.data = None
        
    def load_data(self, data_path: str):
        """Load position data from file."""
        if os.path.exists(data_path):
            self.data = pd.read_parquet(data_path)
            print(f"Loaded data for {self.position}: {len(self.data)} samples")
        else:
            raise FileNotFoundError(f"Data file not found: {data_path}")
    
    def set_data(self, data: pd.DataFrame):
        """Set data directly from DataFrame."""
        self.data = data.copy()
        print(f"Set data for {self.position}: {len(self.data)} samples")
    
    def prepare_features(self, target_col: str = 'fantasy_points_per_game'):
        """Prepare features for model training."""
        if self.data is None:
            raise ValueError("No data loaded. Call load_data() or set_data() first.")
        
        # Define features to exclude from training
        exclude_cols = [
            'player_id', 'player_name', 'position', 'team', 'season',
            'fantasy_points', target_col, 'next_season_fppg'
        ]
        
        # Get feature columns
        feature_cols = [col for col in self.data.columns if col not in exclude_cols]
        
        # Prepare X and y
        X = self.data[feature_cols].fillna(0)
        y = self.data[target_col]
        
        # Remove any infinite values
        X = X.replace([np.inf, -np.inf], 0)
        y = y.replace([np.inf, -np.inf], y.median())
        
        return X, y, feature_cols
    
    def baseline_model(self) -> Dict[str, Any]:
        """Train a baseline RandomForest model."""
        print(f"Training baseline model for {self.position}...")
        
        X, y, feature_cols = self.prepare_features()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train model
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        
        # Cross-validation
        cv = KFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring='r2')
        
        result = {
            'model': model,
            'scaler': None,  # No scaling for RF
            'feature_names': feature_cols,
            'X_test': X_test.values,
            'y_test': y_test.values,
            'y_pred': y_pred,
            'metrics': {
                'rmse': rmse,
                'r2': r2,
                'mae': mae,
                'cv_r2_mean': cv_scores.mean(),
                'cv_r2_std': cv_scores.std(),
            }
        }
        
        self.models['baseline'] = result
        return result
    
    def basic_engineering_model(self) -> Dict[str, Any]:
        """Train a basic feature engineering model (LightGBM with feature selection)."""
        print(f"Training basic engineering model for {self.position}...")
        
        X, y, feature_cols = self.prepare_features()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train initial LightGBM to get feature importance
        initial_model = lgb.LGBMRegressor(
            n_estimators=100,
            learning_rate=0.1,
            num_leaves=31,
            random_state=42,
            verbosity=-1
        )
        initial_model.fit(X_train, y_train)
        
        # Select top features
        feature_importance = initial_model.feature_importances_
        n_features = min(15, len(feature_cols))  # Top 15 features or all if less
        top_indices = np.argsort(feature_importance)[-n_features:]
        top_features = [feature_cols[i] for i in top_indices]
        
        # Train final model with selected features
        X_train_selected = X_train.iloc[:, top_indices]
        X_test_selected = X_test.iloc[:, top_indices]
        
        model = lgb.LGBMRegressor(
            n_estimators=150,
            learning_rate=0.05,
            num_leaves=31,
            max_depth=6,
            min_child_samples=20,
            random_state=42,
            verbosity=-1
        )
        
        model.fit(X_train_selected, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test_selected)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        
        # Cross-validation on selected features
        X_selected = X.iloc[:, top_indices]
        cv = KFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X_selected, y, cv=cv, scoring='r2')
        
        result = {
            'model': model,
            'scaler': None,
            'feature_names': top_features,
            'X_test': X_test_selected.values,
            'y_test': y_test.values,
            'y_pred': y_pred,
            'metrics': {
                'rmse': rmse,
                'r2': r2,
                'mae': mae,
                'cv_r2_mean': cv_scores.mean(),
                'cv_r2_std': cv_scores.std(),
            }
        }
        
        self.models['basic_engineering'] = result
        return result
    
    def advanced_engineering_model(self) -> Dict[str, Any]:
        """Train an advanced feature engineering model (LightGBM with scaling and tuning)."""
        print(f"Training advanced engineering model for {self.position}...")
        
        X, y, feature_cols = self.prepare_features()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Convert back to DataFrame for LightGBM
        X_train_scaled = pd.DataFrame(X_train_scaled, columns=feature_cols)
        X_test_scaled = pd.DataFrame(X_test_scaled, columns=feature_cols)
        
        # Train advanced LightGBM model
        model = lgb.LGBMRegressor(
            n_estimators=200,
            learning_rate=0.03,
            num_leaves=31,
            max_depth=6,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1
        )
        
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test_scaled)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        
        # Cross-validation
        X_scaled = scaler.fit_transform(X)
        X_scaled = pd.DataFrame(X_scaled, columns=feature_cols)
        cv = KFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='r2')
        
        result = {
            'model': model,
            'scaler': scaler,
            'feature_names': feature_cols,
            'X_test': X_test_scaled.values,
            'y_test': y_test.values,
            'y_pred': y_pred,
            'metrics': {
                'rmse': rmse,
                'r2': r2,
                'mae': mae,
                'cv_r2_mean': cv_scores.mean(),
                'cv_r2_std': cv_scores.std(),
            }
        }
        
        self.models['advanced_engineering'] = result
        return result
    
    def run_comparison(self) -> Dict[str, Dict[str, Any]]:
        """Run all model comparisons."""
        print(f"Running model comparison for {self.position}...")
        
        results = {}
        
        # Train all models
        results['baseline'] = self.baseline_model()
        results['basic_engineering'] = self.basic_engineering_model()
        results['advanced_engineering'] = self.advanced_engineering_model()
        
        # Find best model based on R²
        best_r2 = -np.inf
        best_model_name = None
        
        for name, result in results.items():
            r2 = result['metrics']['r2']
            print(f"{name:20} R²: {r2:.3f} RMSE: {result['metrics']['rmse']:.3f}")
            
            if r2 > best_r2:
                best_r2 = r2
                best_model_name = name
        
        self.best_model = best_model_name
        self.results = results
        
        print(f"Best model for {self.position}: {best_model_name} (R² = {best_r2:.3f})")
        
        return results
    
    def plot_feature_importance(self, model_name: str = None, top_n: int = 15):
        """Plot feature importance for a specific model."""
        if not self.results:
            print("No models trained yet. Run run_comparison() first.")
            return
        
        if model_name is None:
            model_name = self.best_model
        
        if model_name not in self.results:
            print(f"Model '{model_name}' not found.")
            return
        
        result = self.results[model_name]
        model = result['model']
        feature_names = result['feature_names']
        
        # Get feature importance
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
        else:
            print("Model doesn't have feature importance.")
            return
        
        # Sort and get top features
        indices = np.argsort(importance)[-top_n:]
        top_features = [feature_names[i] for i in indices]
        top_importance = importance[indices]
        
        # Plot
        plt.figure(figsize=(10, 6))
        plt.barh(range(len(top_features)), top_importance)
        plt.yticks(range(len(top_features)), top_features)
        plt.xlabel('Feature Importance')
        plt.title(f'{self.position} - {model_name} - Top {top_n} Features')
        plt.tight_layout()
        
        return plt.gcf()
    
    def save_models(self, output_dir: str = 'saved_models'):
        """Save all trained models."""
        if not self.results:
            print("No models to save. Run run_comparison() first.")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        for model_name, result in self.results.items():
            model_path = os.path.join(output_dir, f'{self.position}_{model_name}_model.joblib')
            joblib.dump(result['model'], model_path)
            
            # Also save scaler if it exists
            if result['scaler'] is not None:
                scaler_path = os.path.join(output_dir, f'{self.position}_{model_name}_scaler.joblib')
                joblib.dump(result['scaler'], scaler_path)
            
            print(f"Saved {self.position} {model_name} model")
    
    def get_best_model(self):
        """Get the best performing model."""
        if self.best_model and self.best_model in self.results:
            return self.results[self.best_model]
        return None