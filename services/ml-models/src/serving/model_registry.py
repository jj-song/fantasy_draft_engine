"""
Model Registry - Manage and track trained ML models.

This module provides centralized model management including:
- Model loading and registration
- Model metadata tracking
- Model version management
- Model health checking
"""

import logging
import os
import joblib
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

class ModelRegistry:
    """
    Central registry for managing trained ML models.
    
    Provides model loading, registration, status tracking, and metadata management.
    """
    
    def __init__(self, models_dir: Optional[str] = None):
        """
        Initialize model registry.
        
        Args:
            models_dir: Directory containing saved models (defaults to project saved_models/)
        """
        if models_dir is None:
            # Default to project's saved_models directory
            services_root = Path(__file__).parent.parent.parent.parent.parent
            models_dir = services_root / "saved_models"
        
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        
        # Registry state
        self.registered_models: Dict[str, Any] = {}
        self.model_metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"🏛️ Model Registry initialized with models directory: {self.models_dir}")
    
    async def load_available_models(self) -> Dict[str, List[str]]:
        """
        Load all available models from the models directory.
        
        Returns:
            Dictionary mapping positions to available model types
        """
        logger.info("📂 Loading available models from registry...")
        
        available_models = {"ensemble": [], "baseline": [], "advanced": [], "basic": []}
        
        try:
            if not self.models_dir.exists():
                logger.warning(f"Models directory does not exist: {self.models_dir}")
                return available_models
            
            model_files = list(self.models_dir.glob("*.joblib"))
            logger.info(f"Found {len(model_files)} model files")
            
            for model_file in model_files:
                try:
                    # Parse model filename to determine position and type
                    filename = model_file.stem
                    
                    if "_ensemble_model" in filename:
                        position = filename.replace("_ensemble_model", "")
                        model_type = "ensemble"
                    elif "_baseline_model" in filename:
                        position = filename.replace("_baseline_model", "")
                        model_type = "baseline"
                    elif "_advanced_engineering_model" in filename:
                        position = filename.replace("_advanced_engineering_model", "")
                        model_type = "advanced"
                    elif "_basic_engineering_model" in filename:
                        position = filename.replace("_basic_engineering_model", "")
                        model_type = "basic"
                    else:
                        logger.warning(f"Unknown model file format: {filename}")
                        continue
                    
                    # Load model to get metadata
                    model_data = joblib.load(model_file)
                    
                    # Register the model
                    await self._register_model_from_file(position.upper(), model_type, model_file, model_data)
                    
                    available_models[model_type].append(position.upper())
                    logger.info(f"✅ Loaded {model_type} model for {position.upper()}")
                
                except Exception as e:
                    logger.error(f"Failed to load model from {model_file}: {e}")
                    continue
            
            # Log summary
            total_models = sum(len(models) for models in available_models.values())
            logger.info(f"📊 Model loading summary: {total_models} models loaded")
            for model_type, positions in available_models.items():
                if positions:
                    logger.info(f"   {model_type.title()}: {positions}")
            
            return available_models
        
        except Exception as e:
            logger.error(f"Failed to load available models: {e}")
            return available_models
    
    async def _register_model_from_file(self, position: str, model_type: str, model_file: Path, model_data: Any):
        """Register a model loaded from file."""
        model_key = f"{position}_{model_type}"
        
        # Store model reference
        self.registered_models[model_key] = model_data
        
        # Store metadata
        self.model_metadata[model_key] = {
            "position": position,
            "model_type": model_type,
            "file_path": str(model_file),
            "file_size": model_file.stat().st_size,
            "loaded_at": datetime.now().isoformat(),
            "last_modified": datetime.fromtimestamp(model_file.stat().st_mtime).isoformat(),
            "is_trained": getattr(model_data, 'is_trained', True),
            "model_class": type(model_data).__name__ if hasattr(model_data, '__class__') else "Unknown"
        }
        
        # Add model-specific metadata if available
        if hasattr(model_data, 'creation_timestamp'):
            self.model_metadata[model_key]["creation_timestamp"] = model_data.creation_timestamp
        
        if hasattr(model_data, 'model_type'):
            self.model_metadata[model_key]["internal_model_type"] = model_data.model_type
    
    async def register_model(self, position: str, model: Any, model_type: str = "ensemble") -> bool:
        """
        Register a newly trained model.
        
        Args:
            position: Player position (QB, RB, WR, TE)
            model: Trained model object
            model_type: Type of model (ensemble, baseline, etc.)
            
        Returns:
            True if registration successful
        """
        try:
            position = position.upper()
            model_key = f"{position}_{model_type}"
            
            logger.info(f"📝 Registering {model_type} model for {position}...")
            
            # Store model
            self.registered_models[model_key] = model
            
            # Store metadata
            self.model_metadata[model_key] = {
                "position": position,
                "model_type": model_type,
                "registered_at": datetime.now().isoformat(),
                "is_trained": getattr(model, 'is_trained', True),
                "model_class": type(model).__name__,
                "in_memory": True
            }
            
            # Add model-specific metadata
            if hasattr(model, 'creation_timestamp'):
                self.model_metadata[model_key]["creation_timestamp"] = model.creation_timestamp
            
            logger.info(f"✅ Model registered successfully: {model_key}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to register model {position}_{model_type}: {e}")
            return False
    
    async def get_model(self, position: str, model_type: str = "ensemble") -> Optional[Any]:
        """
        Get a registered model.
        
        Args:
            position: Player position
            model_type: Type of model to retrieve
            
        Returns:
            Model object if found, None otherwise
        """
        position = position.upper()
        model_key = f"{position}_{model_type}"
        
        model = self.registered_models.get(model_key)
        if model is None:
            logger.warning(f"Model not found: {model_key}")
            
            # Try to find alternative model types for this position
            available_types = [key.split('_', 1)[1] for key in self.registered_models.keys() 
                             if key.startswith(f"{position}_")]
            
            if available_types:
                logger.info(f"Available model types for {position}: {available_types}")
        
        return model
    
    async def get_registry_status(self) -> Dict[str, Any]:
        """Get overall registry status."""
        positions_with_models = set()
        model_types = set()
        
        for model_key in self.registered_models.keys():
            position, model_type = model_key.split('_', 1)
            positions_with_models.add(position)
            model_types.add(model_type)
        
        return {
            "models_loaded": len(self.registered_models),
            "available_positions": sorted(list(positions_with_models)),
            "available_model_types": sorted(list(model_types)),
            "registry_initialized": True
        }
    
    async def get_registry_info(self) -> Dict[str, Any]:
        """Get complete registry information."""
        registry_status = await self.get_registry_status()
        
        # Count models by type
        model_types = {}
        positions = {}
        
        for model_key, metadata in self.model_metadata.items():
            position = metadata["position"]
            model_type = metadata["model_type"]
            
            # Count by type
            if model_type not in model_types:
                model_types[model_type] = 0
            model_types[model_type] += 1
            
            # Count by position
            if position not in positions:
                positions[position] = {"model_count": 0, "model_types": []}
            positions[position]["model_count"] += 1
            if model_type not in positions[position]["model_types"]:
                positions[position]["model_types"].append(model_type)
        
        registry_info = {
            "total_models": registry_status["models_loaded"],
            "model_types": model_types,
            "positions": positions,
            "models_directory": str(self.models_dir),
            "models": {}
        }
        
        # Add detailed model information
        for model_key, metadata in self.model_metadata.items():
            position = metadata["position"]
            if position not in registry_info["models"]:
                registry_info["models"][position] = {}
            
            registry_info["models"][position][metadata["model_type"]] = {
                "metadata": metadata,
                "available": model_key in self.registered_models,
                "model_loaded": model_key in self.registered_models
            }
        
        return registry_info
    
    async def get_position_status(self, position: str) -> Dict[str, Any]:
        """
        Get status for all models of a specific position.
        
        Args:
            position: Player position
            
        Returns:
            Status information for the position
        """
        position = position.upper()
        
        position_models = {}
        for model_key, metadata in self.model_metadata.items():
            if metadata["position"] == position:
                model_type = metadata["model_type"]
                position_models[model_type] = {
                    "metadata": metadata,
                    "available": model_key in self.registered_models,
                    "model_key": model_key
                }
        
        return {
            "position": position,
            "models": position_models,
            "models_available": len(position_models),
            "model_count": len(position_models),
            "model_types": list(position_models.keys()),
            "has_ensemble": "ensemble" in position_models,
            "recommended_model": self._get_recommended_model_type(position_models)
        }
    
    def _get_recommended_model_type(self, position_models: Dict[str, Any]) -> str:
        """Determine the recommended model type for a position."""
        # Priority order for model types
        priority_order = ["ensemble", "advanced", "basic", "baseline"]
        
        for model_type in priority_order:
            if model_type in position_models and position_models[model_type]["available"]:
                return model_type
        
        return "none"
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the model registry."""
        try:
            registry_status = await self.get_registry_status()
            
            health_status = {
                "status": "healthy",
                "models_loaded": registry_status["models_loaded"],
                "positions_covered": len(registry_status["available_positions"]),
                "models_directory_exists": self.models_dir.exists(),
                "models_directory_writable": os.access(self.models_dir, os.W_OK),
                "check_timestamp": datetime.now().isoformat()
            }
            
            # Check if we have at least one model per major position
            major_positions = {"QB", "RB", "WR", "TE"}
            covered_positions = set(registry_status["available_positions"])
            missing_positions = major_positions - covered_positions
            
            if missing_positions:
                health_status["status"] = "degraded"
                health_status["missing_positions"] = list(missing_positions)
                health_status["warning"] = f"Missing models for positions: {list(missing_positions)}"
            
            return health_status
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "check_timestamp": datetime.now().isoformat()
            }