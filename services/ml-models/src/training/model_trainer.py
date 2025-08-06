"""
Model Trainer - Orchestrate ensemble model training.

This module provides training orchestration including:
- Data loading and preparation
- Feature engineering integration
- Model training coordination
- Model validation and saving
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import sys
import os
import requests
import asyncio

# Add paths for accessing legacy modules
services_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(services_root))
sys.path.append(str(services_root / "legacy"))

logger = logging.getLogger(__name__)

class ModelTrainer:
    """
    Orchestrates the training of ensemble models for fantasy football predictions.
    
    Handles data loading, feature preparation, model training, and validation.
    """
    
    def __init__(self, config_service_url: str = "http://localhost:8001", 
                 feature_service_url: str = "http://localhost:8003"):
        """
        Initialize model trainer.
        
        Args:
            config_service_url: Configuration service URL
            feature_service_url: Feature engineering service URL
        """
        self.config_service_url = config_service_url
        self.feature_service_url = feature_service_url
        
        # Training state
        self.training_progress = {}
        
        logger.info("🏭 Model Trainer initialized")
    
    async def train_ensemble_models(self, positions: List[str], force_retrain: bool = False, 
                                  save_models: bool = True, validation_split: float = 0.2) -> Dict[str, Any]:
        """
        Train ensemble models for specified positions.
        
        Args:
            positions: List of positions to train models for
            force_retrain: Whether to retrain even if models exist
            save_models: Whether to save trained models
            validation_split: Fraction of data to use for validation
            
        Returns:
            Dictionary of trained models by position
        """
        try:
            logger.info(f"🎯 Starting ensemble model training for positions: {positions}")
            
            # Initialize training progress
            for position in positions:
                self.training_progress[position] = {"status": "starting", "progress": 0}
            
            # Load configuration
            config = await self._get_configuration()
            
            # Load training data for all positions
            training_data = await self._load_training_data(positions)
            
            trained_models = {}
            
            for position in positions:
                try:
                    logger.info(f"\n🎯 Training ensemble model for {position}...")
                    self.training_progress[position] = {"status": "training", "progress": 20}
                    
                    if position not in training_data or training_data[position].empty:
                        logger.error(f"No training data available for {position}")
                        self.training_progress[position] = {"status": "failed", "error": "No training data"}
                        continue
                    
                    # Prepare training data
                    X, y, feature_cols = await self._prepare_training_data(training_data[position], position, config)
                    
                    self.training_progress[position] = {"status": "training", "progress": 40}
                    
                    # Train ensemble model
                    model = await self._train_position_model(position, X, y, feature_cols, validation_split)
                    
                    self.training_progress[position] = {"status": "training", "progress": 80}
                    
                    # Save model if requested
                    if save_models and model is not None:
                        await self._save_model(model, position)
                    
                    trained_models[position] = model
                    self.training_progress[position] = {"status": "completed", "progress": 100}
                    
                    logger.info(f"✅ Ensemble model training completed for {position}")
                
                except Exception as e:
                    logger.error(f"Training failed for {position}: {e}")
                    self.training_progress[position] = {"status": "failed", "error": str(e)}
                    continue
            
            logger.info(f"🎉 Ensemble model training completed. Successfully trained: {list(trained_models.keys())}")
            return trained_models
        
        except Exception as e:
            logger.error(f"Ensemble model training failed: {e}")
            raise
    
    async def _get_configuration(self) -> Dict[str, Any]:
        """Get configuration from configuration service."""
        try:
            response = requests.get(f"{self.config_service_url}/api/v1/config/summary", timeout=10)
            if response.status_code == 200:
                config_data = response.json()
                return config_data.get("data", {})
            else:
                logger.warning(f"Could not get configuration, using defaults: {response.status_code}")
                return self._get_default_config()
        except Exception as e:
            logger.warning(f"Configuration service unavailable, using defaults: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if service is unavailable."""
        return {
            "data": {
                "training_seasons": list(range(2010, 2024)),
                "prediction_season": 2024,
                "min_games_played": 4
            },
            "league": {
                "scoring_system": "0.5_ppr"
            }
        }
    
    async def _load_training_data(self, positions: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Load training data for specified positions.
        
        Args:
            positions: List of positions to load data for
            
        Returns:
            Dictionary mapping positions to their training DataFrames
        """
        logger.info(f"📊 Loading training data for positions: {positions}")
        
        training_data = {}
        
        # Try to get data from feature engineering service
        try:
            # Check if feature engineering service has processed data
            response = requests.get(f"{self.feature_service_url}/api/v1/features/status", timeout=10)
            if response.status_code == 200:
                status_data = response.json()
                if status_data.get("data", {}).get("features_available"):
                    logger.info("✅ Feature engineering service has processed data available")
                    # Load data via service API (this would need to be implemented)
                    # For now, fall back to direct file loading
        except Exception as e:
            logger.warning(f"Could not access feature engineering service: {e}")
        
        # Load data directly from processed files
        # Check if running in Docker container (has /app/data mount)
        if Path("/app/data").exists():
            data_dir = Path("/app/data/processed")
        else:
            data_dir = services_root / "data" / "processed"
        
        for position in positions:
            try:
                # Look for position-specific feature files
                position_data_files = []
                
                # Check for position-specific directory
                position_dir = data_dir / "position_specific" / position.lower()
                if position_dir.exists():
                    position_files = list(position_dir.glob("*.parquet"))
                    position_data_files.extend(position_files)
                
                # Also check for training feature files
                training_files = list(data_dir.glob("training_features_*_with_matchup_intel.parquet"))
                position_data_files.extend(training_files)
                
                if position_data_files:
                    logger.info(f"Found {len(position_data_files)} data files for {position}")
                    
                    # Load and combine data files
                    dfs = []
                    for file_path in position_data_files:
                        try:
                            df = pd.read_parquet(file_path)
                            
                            # Filter for position if position column exists
                            if 'position' in df.columns:
                                df = df[df['position'] == position]
                            
                            if not df.empty:
                                dfs.append(df)
                                logger.info(f"   Loaded {len(df)} records from {file_path.name}")
                        except Exception as e:
                            logger.warning(f"Could not load {file_path}: {e}")
                    
                    if dfs:
                        combined_df = pd.concat(dfs, ignore_index=True)
                        
                        # Remove duplicates if any
                        initial_len = len(combined_df)
                        if 'player_id' in combined_df.columns and 'season' in combined_df.columns:
                            combined_df = combined_df.drop_duplicates(subset=['player_id', 'season'])
                        
                        logger.info(f"✅ Combined training data for {position}: {len(combined_df)} records (removed {initial_len - len(combined_df)} duplicates)")
                        training_data[position] = combined_df
                    else:
                        logger.warning(f"No valid data loaded for {position}")
                else:
                    logger.warning(f"No training data files found for {position}")
            
            except Exception as e:
                logger.error(f"Failed to load training data for {position}: {e}")
        
        return training_data
    
    async def _prepare_training_data(self, data: pd.DataFrame, position: str, config: Dict[str, Any]) -> tuple:
        """
        Prepare training data for model training.
        
        Args:
            data: Raw training data
            position: Player position
            config: Configuration settings
            
        Returns:
            Tuple of (X, y, feature_columns)
        """
        logger.info(f"🔧 Preparing training data for {position}: {len(data)} records")
        
        # Define target column (fantasy points)
        target_candidates = ['fantasy_points_per_game', 'fantasy_points', 'target_points', 'points_per_game']
        target_col = None
        
        for candidate in target_candidates:
            if candidate in data.columns:
                target_col = candidate
                break
        
        if target_col is None:
            raise ValueError(f"No target column found in data for {position}. Available columns: {list(data.columns)}")
        
        logger.info(f"Using target column: {target_col}")
        
        # Filter data based on configuration
        min_games = config.get("data", {}).get("min_games_played", 4)
        if 'games_played' in data.columns:
            initial_len = len(data)
            data = data[data['games_played'] >= min_games]
            logger.info(f"Filtered for min games ({min_games}): {len(data)} records (removed {initial_len - len(data)})")
        
        # Define feature columns (exclude non-feature columns)
        exclude_cols = {
            'player_id', 'player_name', 'team', 'season', 'week', 
            'fantasy_points', 'fantasy_points_per_game', 'target_points', 'points_per_game',
            'position', 'games_played'
        }
        
        feature_cols = [col for col in data.columns if col not in exclude_cols and col != target_col]
        
        # Remove columns with too many nulls
        null_threshold = 0.8
        high_null_cols = []
        for col in feature_cols:
            null_ratio = data[col].isnull().sum() / len(data)
            if null_ratio > null_threshold:
                high_null_cols.append(col)
        
        if high_null_cols:
            logger.info(f"Removing {len(high_null_cols)} columns with >80% null values")
            feature_cols = [col for col in feature_cols if col not in high_null_cols]
        
        # Prepare feature matrix
        X = data[feature_cols].copy()
        y = data[target_col].copy()
        
        # Fill remaining null values
        for col in X.columns:
            if X[col].isnull().any():
                if X[col].dtype in ['int64', 'float64']:
                    X[col] = X[col].fillna(0.0)
                else:
                    X[col] = X[col].fillna('Unknown')
        
        # Remove infinite values
        X = X.replace([np.inf, -np.inf], 0)
        
        # Remove rows with null targets
        valid_indices = ~y.isnull()
        X = X[valid_indices]
        y = y[valid_indices]
        
        logger.info(f"✅ Training data prepared for {position}:")
        logger.info(f"   Features: {len(feature_cols)}")
        logger.info(f"   Samples: {len(X)}")
        logger.info(f"   Target range: {y.min():.2f} - {y.max():.2f}")
        
        return X, y, feature_cols
    
    async def _train_position_model(self, position: str, X: pd.DataFrame, y: pd.Series, 
                                  feature_cols: List[str], validation_split: float) -> Any:
        """
        Train ensemble model for a specific position.
        
        Args:
            position: Player position
            X: Feature matrix
            y: Target values
            feature_cols: List of feature column names
            validation_split: Fraction for validation
            
        Returns:
            Trained ensemble model
        """
        try:
            logger.info(f"🤖 Training ensemble model for {position}...")
            
            # Import the ensemble model class
            from ..models.ensemble_model import EnsembleFantasyModel
            
            # Split data for validation
            split_idx = int(len(X) * (1 - validation_split))
            X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
            
            logger.info(f"   Training split: {len(X_train)} train, {len(X_val)} validation")
            
            # Create and train ensemble model
            ensemble_model = EnsembleFantasyModel(position)
            ensemble_model.train(X_train, y_train, X_val, y_val)
            
            logger.info(f"✅ Ensemble model trained successfully for {position}")
            
            return ensemble_model
        
        except Exception as e:
            logger.error(f"Model training failed for {position}: {e}")
            raise
    
    async def _save_model(self, model: Any, position: str) -> bool:
        """
        Save trained model to disk.
        
        Args:
            model: Trained model
            position: Player position
            
        Returns:
            True if save successful
        """
        try:
            models_dir = services_root / "saved_models"
            models_dir.mkdir(exist_ok=True)
            
            model_filename = f"{position}_ensemble_model.joblib"
            model_path = models_dir / model_filename
            
            model.save(str(model_path))
            
            logger.info(f"💾 Model saved: {model_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save model for {position}: {e}")
            return False
    
    async def get_training_progress(self) -> Dict[str, Any]:
        """Get current training progress for all positions."""
        return {
            "positions": self.training_progress,
            "overall_status": self._get_overall_status(),
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_overall_status(self) -> str:
        """Determine overall training status."""
        if not self.training_progress:
            return "idle"
        
        statuses = [info["status"] for info in self.training_progress.values()]
        
        if any(status == "training" for status in statuses):
            return "training"
        elif any(status == "failed" for status in statuses):
            return "partially_failed"
        elif all(status == "completed" for status in statuses):
            return "completed"
        else:
            return "unknown"