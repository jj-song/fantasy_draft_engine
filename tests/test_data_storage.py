"""
Test script for the data storage utility module.

This script demonstrates how to use the data_storage module to access
raw, cleaned, and feature-engineered data.
"""

import logging
import pandas as pd
from fantasy_football_ai_tool.src.data_storage import (
    get_available_seasons,
    load_raw_data,
    load_cleaned_data,
    load_features_data,
    verify_data_grain
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Test data storage utility functions."""
    # Check available seasons
    logger.info("Available seasons:")
    seasons = get_available_seasons()
    for season in seasons:
        logger.info(f"- {season}")
    
    # Load raw data for the most recent season
    latest_season = max(seasons) if seasons else None
    if latest_season:
        logger.info(f"Loading raw data for {latest_season}...")
        raw_df = load_raw_data(latest_season)
        logger.info(f"Raw data shape: {raw_df.shape}")
        logger.info(f"Raw data columns: {raw_df.columns.tolist()}")
        
        # Display sample of raw data
        logger.info("Sample of raw data:")
        logger.info(raw_df.head(3))
        
        # Verify data grain
        logger.info("Verifying data grain...")
        is_correct_grain = verify_data_grain(raw_df)
        logger.info(f"Data grain is correct: {is_correct_grain}")
        
        # Load cleaned data
        logger.info(f"Loading cleaned data for {latest_season}...")
        cleaned_df = load_cleaned_data(latest_season)
        logger.info(f"Cleaned data shape: {cleaned_df.shape}")
        
        # Load features data
        logger.info(f"Loading features data for {latest_season}...")
        features_df = load_features_data(latest_season)
        logger.info(f"Features data shape: {features_df.shape}")
        
        # Display sample of features data
        logger.info("Sample of features data:")
        logger.info(features_df.head(3))
    else:
        logger.warning("No seasons available")

if __name__ == "__main__":
    main()
