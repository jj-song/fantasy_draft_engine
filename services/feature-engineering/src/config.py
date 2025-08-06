"""
Simple configuration stub for feature engineering service.
This replaces the complex config system with service-to-service communication.
"""
import requests
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