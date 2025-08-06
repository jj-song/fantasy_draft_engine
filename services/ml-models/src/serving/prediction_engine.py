"""
Prediction Engine - Generate predictions using registered models.

This module provides prediction functionality including:
- Single player predictions
- Batch prediction processing
- Model selection and fallback logic
- Prediction validation and formatting
- Feature compatibility mapping for baseline models
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

# Import feature compatibility mapper
try:
    from ..utils.feature_compatibility import FeatureCompatibilityMapper
except ImportError:
    # Fallback for direct testing
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from utils.feature_compatibility import FeatureCompatibilityMapper

logger = logging.getLogger(__name__)

class PredictionEngine:
    """
    Engine for generating predictions using registered models.
    
    Handles single and batch predictions, model selection, and prediction validation.
    """
    
    def __init__(self, model_registry):
        """
        Initialize prediction engine.
        
        Args:
            model_registry: ModelRegistry instance
        """
        self.model_registry = model_registry
        self.prediction_cache = {}  # Simple cache for repeated predictions
        self.feature_mapper = FeatureCompatibilityMapper()  # Feature mapping for baseline models
        
        logger.info("🎯 Prediction Engine initialized with feature compatibility mapping")
    
    async def predict_single(self, position: str, features: Dict[str, float], 
                           player_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate prediction for a single player.
        
        Args:
            position: Player position (QB, RB, WR, TE)
            features: Feature values for prediction
            player_data: Additional player metadata
            
        Returns:
            Dictionary containing prediction results
        """
        try:
            position = position.upper()
            logger.info(f"🎯 Generating single prediction for {position} player")
            
            # Get the best available model for this position
            model = await self._get_best_model(position)
            if model is None:
                raise ValueError(f"No trained model available for position {position}")
            
            # Prepare features for prediction
            features_df = pd.DataFrame([features])
            
            # Apply feature mapping only for legacy baseline models, not our new ensemble models
            model_type = self._get_model_type(model)
            # Skip feature mapping for our newly trained ensemble models (they expect direct feature names)
            if model_type in ['baseline', 'basic_engineering', 'advanced_engineering'] and model_type != 'ensemble':
                logger.info(f"Applying feature mapping for {model_type} model")
                original_shape = features_df.shape
                features_df = self.feature_mapper.map_features_for_position(features_df, position)
                logger.info(f"Feature mapping: {original_shape} → {features_df.shape}")
                
                # Validate mapped features
                validation = self.feature_mapper.validate_mapped_features(features_df, position)
                if not validation['validation_passed']:
                    logger.error(f"Feature mapping validation failed: {validation}")
                    raise ValueError(f"Feature mapping failed for {position}: {validation['missing_features']}")
            else:
                logger.info(f"Skipping feature mapping for {model_type} model - using features as provided")
            
            # Validate features
            await self._validate_features(features_df, position)
            
            # Generate prediction
            if hasattr(model, 'predict'):
                # Handle custom ensemble models that may need player_data
                if hasattr(model, 'position') and hasattr(model, '__class__') and 'EnsembleFantasyModel' in str(model.__class__):
                    player_df = pd.DataFrame([player_data]) if player_data else None
                    prediction = model.predict(features_df, player_df)
                else:
                    # Handle sklearn-style models (including our RandomForestRegressor ensemble models)
                    prediction = model.predict(features_df)
            else:
                # Fallback for models without predict method
                raise ValueError(f"Model does not have a predict method: {type(model)}")
            
            # Format prediction result
            prediction_value = float(prediction[0]) if isinstance(prediction, (list, np.ndarray)) else float(prediction)
            
            result = {
                "position": position,
                "predicted_fantasy_points": prediction_value,
                "prediction": prediction_value,
                "model_type": self._get_model_type(model),
                "confidence": await self._calculate_confidence(prediction_value, position),
                "prediction_timestamp": datetime.now().isoformat(),
                "features_count": len(features),
                "features_used": list(features_df.columns)
            }
            
            # Add player metadata if provided
            if player_data:
                result["player_info"] = {
                    "player_id": player_data.get("player_id"),
                    "player_name": player_data.get("player_name"),
                    "team": player_data.get("team")
                }
            
            logger.info(f"✅ Single prediction generated: {prediction_value:.2f} points for {position}")
            return result
        
        except Exception as e:
            logger.error(f"Single prediction failed for {position}: {e}")
            raise
    
    async def predict_batch(self, position: str, predictions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate predictions for multiple players.
        
        Args:
            position: Player position
            predictions_data: List of dictionaries containing features and player data
            
        Returns:
            List of prediction results
        """
        try:
            position = position.upper()
            logger.info(f"🎯 Generating batch predictions for {len(predictions_data)} {position} players")
            
            # Get the best available model for this position
            model = await self._get_best_model(position)
            if model is None:
                raise ValueError(f"No trained model available for position {position}")
            
            # Prepare batch features
            features_list = []
            player_data_list = []
            
            for data in predictions_data:
                features = data.get("features", {})
                features_list.append(features)
                player_data_list.append(data.get("player_data", {}))
            
            if not features_list:
                raise ValueError("No features provided for batch prediction")
            
            # Create features DataFrame
            features_df = pd.DataFrame(features_list)
            
            # Apply feature mapping for baseline models
            model_type = self._get_model_type(model)
            # Apply mapping for baseline models (which are typically RandomForest models)
            if model_type in ['baseline', 'basic_engineering', 'advanced_engineering', 'random_forest', 'lightgbm']:
                logger.info(f"Applying feature mapping for {model_type} model (batch)")
                original_shape = features_df.shape
                features_df = self.feature_mapper.map_features_for_position(features_df, position)
                logger.info(f"Batch feature mapping: {original_shape} → {features_df.shape}")
                
                # Validate mapped features
                validation = self.feature_mapper.validate_mapped_features(features_df, position)
                if not validation['validation_passed']:
                    logger.error(f"Batch feature mapping validation failed: {validation}")
                    raise ValueError(f"Batch feature mapping failed for {position}: {validation['missing_features']}")
            
            # Validate features
            await self._validate_features(features_df, position)
            
            # Generate batch predictions
            if hasattr(model, 'predict'):
                # Handle ensemble models
                if hasattr(model, 'position') and player_data_list:
                    player_df = pd.DataFrame(player_data_list)
                    predictions = model.predict(features_df, player_df)
                else:
                    predictions = model.predict(features_df)
            else:
                # Handle sklearn-style models
                predictions = model.predict(features_df)
            
            # Format batch results
            results = []
            for i, (prediction, player_data) in enumerate(zip(predictions, player_data_list)):
                prediction_value = float(prediction) if isinstance(prediction, (list, np.ndarray, int, float)) else float(prediction)
                
                result = {
                    "position": position,
                    "predicted_fantasy_points": prediction_value,
                    "prediction": prediction_value,
                    "model_type": self._get_model_type(model),
                    "confidence": await self._calculate_confidence(prediction_value, position),
                    "prediction_timestamp": datetime.now().isoformat(),
                    "batch_index": i,
                    "features_count": len(features_list[i])
                }
                
                # Add player metadata if provided
                if player_data:
                    result["player_info"] = {
                        "player_id": player_data.get("player_id"),
                        "player_name": player_data.get("player_name"),
                        "team": player_data.get("team")
                    }
                
                results.append(result)
            
            logger.info(f"✅ Batch predictions generated: {len(results)} predictions for {position}")
            logger.info(f"   Average prediction: {np.mean([r['prediction'] for r in results]):.2f} points")
            
            return results
        
        except Exception as e:
            logger.error(f"Batch prediction failed for {position}: {e}")
            raise
    
    async def _get_best_model(self, position: str) -> Optional[Any]:
        """
        Get the best available model for a position.
        
        Args:
            position: Player position
            
        Returns:
            Best available model or None
        """
        # Priority order for model selection
        model_priority = ["ensemble", "advanced", "basic", "baseline"]
        
        for model_type in model_priority:
            model = await self.model_registry.get_model(position, model_type)
            if model is not None:
                logger.info(f"Using {model_type} model for {position}")
                return model
        
        logger.warning(f"No models available for position {position}")
        return None
    
    def _get_model_type(self, model: Any) -> str:
        """Determine the type of a model."""
        if hasattr(model, 'model_type'):
            return model.model_type.lower()
        elif hasattr(model, '__class__'):
            class_name = model.__class__.__name__.lower()
            if 'ensemble' in class_name:
                return 'ensemble'
            elif 'random' in class_name or 'forest' in class_name:
                return 'random_forest'
            elif 'lgb' in class_name or 'lightgbm' in class_name:
                return 'lightgbm'
            elif 'baseline' in class_name:
                return 'baseline'
            else:
                return 'unknown'
        else:
            return 'unknown'
    
    async def _validate_features(self, features_df: pd.DataFrame, position: str):
        """
        Validate feature data for predictions.
        
        Args:
            features_df: Features DataFrame
            position: Player position
        """
        if features_df.empty:
            raise ValueError("Empty features provided for prediction")
        
        # Check for null values
        null_count = features_df.isnull().sum().sum()
        if null_count > 0:
            logger.warning(f"Found {null_count} null values in features, will be handled by model")
        
        # Position-specific validation
        if position == "QB":
            required_features = ["passing_yards", "passing_tds"]
            missing_features = [f for f in required_features if f not in features_df.columns]
            if missing_features:
                logger.warning(f"QB missing expected features: {missing_features}")
        
        elif position in ["RB", "WR", "TE"]:
            if position == "RB":
                expected_features = ["rushing_yards", "rushing_tds"]
            else:  # WR, TE
                expected_features = ["receiving_yards", "receiving_tds"]
            
            missing_features = [f for f in expected_features if f not in features_df.columns]
            if missing_features:
                logger.warning(f"{position} missing expected features: {missing_features}")
    
    async def _calculate_confidence(self, prediction: float, position: str) -> Dict[str, Any]:
        """
        Calculate prediction confidence metrics.
        
        Args:
            prediction: Predicted value
            position: Player position
            
        Returns:
            Confidence metrics
        """
        # Simple confidence calculation based on prediction value and position
        position_ranges = {
            "QB": {"min": 8, "max": 35, "avg": 18},
            "RB": {"min": 3, "max": 25, "avg": 12},
            "WR": {"min": 2, "max": 22, "avg": 10},
            "TE": {"min": 1, "max": 18, "avg": 8}
        }
        
        range_info = position_ranges.get(position, {"min": 0, "max": 30, "avg": 10})
        
        # Calculate confidence based on how reasonable the prediction is
        if range_info["min"] <= prediction <= range_info["max"]:
            confidence_score = 0.8  # High confidence for reasonable predictions
        elif prediction < range_info["min"]:
            confidence_score = max(0.3, 0.8 - (range_info["min"] - prediction) * 0.1)
        else:  # prediction > max
            confidence_score = max(0.3, 0.8 - (prediction - range_info["max"]) * 0.05)
        
        return {
            "score": min(0.95, max(0.1, confidence_score)),  # Clamp between 0.1 and 0.95
            "level": "high" if confidence_score > 0.7 else "medium" if confidence_score > 0.5 else "low",
            "range_check": {
                "within_expected_range": range_info["min"] <= prediction <= range_info["max"],
                "expected_range": f"{range_info['min']}-{range_info['max']}",
                "position_average": range_info["avg"]
            }
        }
    
    async def get_prediction_stats(self) -> Dict[str, Any]:
        """Get prediction engine statistics."""
        return {
            "cache_size": len(self.prediction_cache),
            "engine_status": "ready",
            "supported_positions": ["QB", "RB", "WR", "TE"],
            "prediction_methods": ["single", "batch"],
            "last_updated": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the prediction engine."""
        try:
            # Check if we can access the model registry
            registry_status = await self.model_registry.get_registry_status()
            
            # Check if we have models for all major positions
            major_positions = {"QB", "RB", "WR", "TE"}
            available_positions = set(registry_status.get("available_positions", []))
            missing_positions = major_positions - available_positions
            
            health_status = {
                "status": "healthy" if not missing_positions else "degraded",
                "models_available": registry_status.get("models_loaded", 0),
                "positions_covered": len(available_positions),
                "can_generate_predictions": registry_status.get("models_loaded", 0) > 0,
                "check_timestamp": datetime.now().isoformat()
            }
            
            if missing_positions:
                health_status["missing_positions"] = list(missing_positions)
                health_status["warning"] = f"Cannot generate predictions for: {list(missing_positions)}"
            
            return health_status
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "check_timestamp": datetime.now().isoformat()
            }