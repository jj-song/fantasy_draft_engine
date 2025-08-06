"""
Simple configuration stub for feature engineering service.
This replaces the complex config system with service-to-service communication.
"""
import requests
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def get_config() -> Dict[str, Any]:
    """Get configuration - stub implementation"""
    return {
        "data_start_year": 2020,
        "data_end_year": 2025,
        "core_positions": ['QB', 'RB', 'WR', 'TE'],
        "feature_engineering": {
            "include_advanced_features": True,
            "include_matchup_features": True
        }
    }

def get_data_paths() -> Dict[str, str]:
    """Get data paths for current environment (local vs container)"""
    # Check if we're running in a container
    is_container = os.path.exists('/app') and os.getcwd().startswith('/app')
    
    if is_container:
        base_path = "/app/data"
    else:
        # Local development - use centralized data directory
        # Navigate from service directory to project root data
        base_path = "../../data"
    
    return {
        "base": base_path,
        "raw": f"{base_path}/raw",
        "processed": f"{base_path}/processed",
        "features": f"{base_path}/processed/position_specific"
    }