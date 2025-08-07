"""
ML Models Service - Train, manage, and serve ML models.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import BackgroundTasks, HTTPException
from pydantic import BaseModel
import os
import sys
from pathlib import Path

# Add validation system integration
try:
    from utils.debug_analysis.debug_integration import add_validation_checkpoint, save_all_validation_reports
except ImportError:
    # Fallback for environments without validation system
    def add_validation_checkpoint(*args, **kwargs):
        pass
    def save_all_validation_reports(*args, **kwargs):
        pass

# Add the services directory to the Python path
services_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(services_root))
sys.path.append(str(services_root / "legacy"))

from .api.base_api import BaseService, create_standard_response
from .serving.model_registry import ModelRegistry
from .serving.prediction_engine import PredictionEngine
from .training.model_trainer import ModelTrainer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelTrainingRequest(BaseModel):
    positions: Optional[List[str]] = None  # If None, train all positions
    force_retrain: bool = False
    save_models: bool = True
    validation_split: float = 0.2
    
class PredictionRequest(BaseModel):
    position: str
    player_data: Dict[str, Any]
    features: Dict[str, float]
    
class BatchPredictionRequest(BaseModel):
    position: str
    predictions_data: List[Dict[str, Any]]

class MLModelsService(BaseService):
    def __init__(self):
        super().__init__(
            service_name="ML Models Service",
            version="1.0.0",
            description="Train, manage, and serve ML models"
        )
        
        # Initialize components
        self.model_registry = ModelRegistry()
        self.prediction_engine = PredictionEngine(self.model_registry)
        self.model_trainer = ModelTrainer(
            config_service_url="http://configuration:8000",
            feature_service_url="http://feature-engineering:8000"
        )
        
        # Service state
        self.training_status = {"status": "idle", "message": ""}
        
        self._setup_routes()
    
    async def startup(self):
        """Service startup initialization"""
        logger.info("🤖 ML Models Service starting up...")
        
        # Load existing models
        try:
            models_loaded = await self.model_registry.load_available_models()
            
            # Add validation checkpoint for model loading
            registry_status = await self.model_registry.get_registry_status()
            add_validation_checkpoint('ml-models', 'model_registry_loaded', registry_status,
                expected_type=dict)
            
            logger.info("✅ Existing models loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️ Could not load existing models: {e}")
        
        logger.info("✅ ML Models Service started successfully")
        
        # Save validation report for service startup
        save_all_validation_reports()
    
    def _setup_routes(self):
        
        # Basic status endpoint
        @self.app.get("/api/v1/models/status")
        async def get_status():
            """Get overall service status"""
            registry_status = await self.model_registry.get_registry_status()
            
            return create_standard_response(
                data={
                    "status": "ready", 
                    "service": "ml-models",
                    "models_loaded": registry_status["models_loaded"],
                    "training_status": self.training_status,
                    "available_positions": registry_status["available_positions"]
                },
                metadata={"service": "ml-models"}
            )
        
        # Model registry endpoints
        @self.app.get("/api/v1/models/registry")
        async def get_model_registry():
            """Get complete model registry information"""
            try:
                registry_info = await self.model_registry.get_registry_info()
                return create_standard_response(
                    data=registry_info,
                    metadata={"service": "ml-models", "endpoint": "registry"}
                )
            except Exception as e:
                logger.error(f"Failed to get model registry: {e}")
                raise HTTPException(status_code=500, detail=f"Registry error: {str(e)}")
        
        @self.app.get("/api/v1/models/{position}/status")
        async def get_position_model_status(position: str):
            """Get status for a specific position's models"""
            try:
                position = position.upper()
                if position not in ['QB', 'RB', 'WR', 'TE']:
                    raise HTTPException(status_code=400, detail=f"Invalid position: {position}")
                
                status = await self.model_registry.get_position_status(position)
                return create_standard_response(
                    data=status,
                    metadata={"service": "ml-models", "position": position}
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get position status for {position}: {e}")
                raise HTTPException(status_code=500, detail=f"Status error: {str(e)}")
        
        # Model training endpoints
        @self.app.post("/api/v1/models/train")
        async def train_models(request: ModelTrainingRequest, background_tasks: BackgroundTasks):
            """Start model training in background"""
            try:
                if self.training_status["status"] == "training":
                    return create_standard_response(
                        data={"message": "Training already in progress", "status": self.training_status},
                        metadata={"service": "ml-models", "endpoint": "train"}
                    )
                
                # Start training in background
                background_tasks.add_task(
                    self._run_model_training,
                    request.positions,
                    request.force_retrain,
                    request.save_models,
                    request.validation_split
                )
                
                self.training_status = {"status": "training", "message": "Model training started"}
                
                return create_standard_response(
                    data={
                        "message": "Model training started in background",
                        "positions": request.positions or ["QB", "RB", "WR", "TE"],
                        "training_id": datetime.now().strftime("%Y%m%d_%H%M%S")
                    },
                    metadata={"service": "ml-models", "endpoint": "train"}
                )
            
            except Exception as e:
                logger.error(f"Failed to start model training: {e}")
                raise HTTPException(status_code=500, detail=f"Training error: {str(e)}")
        
        @self.app.get("/api/v1/models/training-status")
        async def get_training_status():
            """Get current training status"""
            return create_standard_response(
                data=self.training_status,
                metadata={"service": "ml-models", "endpoint": "training-status"}
            )
        
        # Prediction endpoints
        @self.app.post("/api/v1/models/predict")
        async def predict_single(request: PredictionRequest):
            """Generate prediction for a single player"""
            try:
                position = request.position.upper()
                if position not in ['QB', 'RB', 'WR', 'TE']:
                    raise HTTPException(status_code=400, detail=f"Invalid position: {position}")
                
                # Add validation checkpoint for prediction input
                add_validation_checkpoint('ml-models', f'prediction_input_{position}', request.features,
                    expected_type=dict)
                
                prediction = await self.prediction_engine.predict_single(
                    position=position,
                    features=request.features,
                    player_data=request.player_data
                )
                
                # Add validation checkpoint for prediction output
                add_validation_checkpoint('ml-models', f'prediction_output_{position}', prediction,
                    expected_type=dict)
                
                return create_standard_response(
                    data=prediction,
                    metadata={"service": "ml-models", "position": position, "endpoint": "predict"}
                )
            
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Prediction failed for {request.position}: {e}")
                raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
        
        @self.app.post("/api/v1/models/predict-batch")
        async def predict_batch(request: BatchPredictionRequest):
            """Generate predictions for multiple players"""
            try:
                position = request.position.upper()
                if position not in ['QB', 'RB', 'WR', 'TE']:
                    raise HTTPException(status_code=400, detail=f"Invalid position: {position}")
                
                # Add validation checkpoint for batch input
                batch_info = {
                    'position': position,
                    'player_count': len(request.predictions_data),
                    'sample_features': request.predictions_data[0].get('features', {}) if request.predictions_data else {}
                }
                add_validation_checkpoint('ml-models', f'batch_input_{position}', batch_info,
                    expected_type=dict)
                
                predictions = await self.prediction_engine.predict_batch(
                    position=position,
                    predictions_data=request.predictions_data
                )
                
                # Add validation checkpoint for batch output
                if predictions:
                    batch_output = {
                        'position': position,
                        'predictions_count': len(predictions),
                        'avg_prediction': sum(p.get('prediction', 0) for p in predictions) / len(predictions),
                        'prediction_range': [min(p.get('prediction', 0) for p in predictions), 
                                            max(p.get('prediction', 0) for p in predictions)]
                    }
                    add_validation_checkpoint('ml-models', f'batch_output_{position}', batch_output,
                        expected_type=dict)
                
                return create_standard_response(
                    data={
                        "predictions": predictions,
                        "count": len(predictions)
                    },
                    metadata={"service": "ml-models", "position": position, "endpoint": "predict-batch"}
                )
            
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Batch prediction failed for {request.position}: {e}")
                raise HTTPException(status_code=500, detail=f"Batch prediction error: {str(e)}")
    
    async def _run_model_training(self, positions: Optional[List[str]], force_retrain: bool, save_models: bool, validation_split: float):
        """Run model training in background"""
        try:
            self.training_status = {"status": "training", "message": "Loading training data..."}
            
            # Use all positions if none specified
            if positions is None:
                positions = ["QB", "RB", "WR", "TE"]
            
            # Start training
            self.training_status = {"status": "training", "message": f"Training models for {positions}..."}
            
            trained_models = await self.model_trainer.train_ensemble_models(
                positions=positions,
                force_retrain=force_retrain,
                save_models=save_models,
                validation_split=validation_split
            )
            
            # Update model registry with newly trained models
            for position, model in trained_models.items():
                await self.model_registry.register_model(position, model)
            
            self.training_status = {
                "status": "completed", 
                "message": f"Successfully trained models for {list(trained_models.keys())}",
                "models_trained": list(trained_models.keys()),
                "completed_at": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Model training completed for positions: {list(trained_models.keys())}")
        
        except Exception as e:
            error_msg = f"Model training failed: {str(e)}"
            self.training_status = {
                "status": "failed", 
                "message": error_msg,
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            }
            logger.error(f"❌ {error_msg}")

service = MLModelsService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
