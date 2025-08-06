#!/usr/bin/env python3
"""
Training Dataset Generation Script with Matchup Intelligence

This script generates comprehensive training datasets for years 2020-2023 with 
matchup intelligence features for ensemble model training.

Key Features:
- Batch process multiple seasons with matchup intelligence
- Data quality validation at each step
- Fail-fast behavior per user requirements
- Consistent feature engineering across all training years
- Comprehensive logging and progress tracking

Usage:
    python scripts/generate_training_datasets.py                    # Generate all years 2020-2023
    python scripts/generate_training_datasets.py --years 2022 2023  # Generate specific years
    python scripts/generate_training_datasets.py --quick            # Quick mode for testing
"""

import os
import sys
import pandas as pd
import numpy as np
import argparse
from typing import List, Dict
from datetime import datetime
import logging

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Import our modules
from src.feature_engineering import engineer_features_for_season
from src.data_quality_validator import validator, DataQualityError
from src.data_storage import save_features_data
from src.config import get_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/training_dataset_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_training_dataset_for_year(year: int, include_matchup_intelligence: bool = True) -> pd.DataFrame:
    """
    Generate training dataset for a specific year with matchup intelligence.
    
    Args:
        year: Year to generate training data for
        include_matchup_intelligence: Whether to include matchup intelligence features
        
    Returns:
        DataFrame with engineered features for training
        
    Raises:
        DataQualityError: If data quality is insufficient
    """
    logger.info(f"🏗️ GENERATING TRAINING DATASET FOR {year}")
    logger.info("=" * 60)
    
    try:
        # Generate features for the year (training mode - predicting next season)
        logger.info(f"📊 Engineering features for {year} → {year+1} prediction")
        logger.info(f"   Matchup Intelligence: {'✅ ENABLED' if include_matchup_intelligence else '❌ DISABLED'}")
        
        # Use training mode (inference_mode=False) to predict future season
        features_df = engineer_features_for_season(
            target_season=year,
            include_matchup_intelligence=include_matchup_intelligence,
            include_position_specific_features=True,  # Use enhanced features for training
            weeks_ahead_sos=4,
            inference_mode=False  # TRAINING MODE: Predict future season
        )
        
        if features_df is None or features_df.empty:
            raise DataQualityError(f"Feature engineering returned empty data for {year}")
        
        logger.info(f"✅ Feature engineering completed: {len(features_df)} players, {len(features_df.columns)} features")
        
        # Apply comprehensive data quality validation with training mode (more lenient)
        validator.validate_feature_engineered_data(
            features_df, 
            year, 
            include_matchup_intelligence=include_matchup_intelligence,
            training_mode=True  # Use more lenient thresholds for historical training data
        )
        
        # Log dataset summary by position
        position_summary = features_df['position'].value_counts()
        logger.info(f"📊 Position Distribution:")
        for position, count in position_summary.items():
            logger.info(f"   {position}: {count} players")
        
        # Validate target variable completeness
        target_col = 'next_season_fppg'  # This should be the target for training
        if target_col in features_df.columns:
            target_valid = features_df[target_col].notna().sum()
            target_total = len(features_df)
            logger.info(f"📈 Target Variable ({target_col}): {target_valid}/{target_total} valid ({target_valid/target_total*100:.1f}%)")
            
            if target_valid < target_total * 0.8:  # Require 80% valid targets
                raise DataQualityError(f"Too many missing target values: {target_total - target_valid}/{target_total}")
        
        # Log feature categories
        matchup_features = [col for col in features_df.columns if any(x in col.lower() for x in ['sos', 'strength_of_schedule', 'weather', 'dome', 'altitude'])]
        opportunity_features = [col for col in features_df.columns if any(x in col.lower() for x in ['target_share', 'air_yards', 'wopr', 'adot'])]
        usage_features = [col for col in features_df.columns if any(x in col.lower() for x in ['snap_share', 'route_participation', 'high_value'])]
        
        logger.info(f"🎯 Feature Categories:")
        logger.info(f"   Matchup Intelligence: {len(matchup_features)} features")
        logger.info(f"   Opportunity Metrics: {len(opportunity_features)} features") 
        logger.info(f"   Usage Analytics: {len(usage_features)} features")
        
        if include_matchup_intelligence and len(matchup_features) < 5:
            logger.warning(f"⚠️ Expected more matchup intelligence features, found only {len(matchup_features)}")
            
        return features_df
        
    except Exception as e:
        logger.error(f"❌ Failed to generate training dataset for {year}: {e}")
        raise

def save_training_dataset(features_df: pd.DataFrame, year: int, include_matchup_intelligence: bool = True):
    """
    Save training dataset to standardized location.
    
    Args:
        features_df: DataFrame with engineered features
        year: Year the dataset was generated for
        include_matchup_intelligence: Whether matchup intelligence was included
    """
    logger.info(f"💾 SAVING TRAINING DATASET FOR {year}")
    
    # Create standardized filename
    if include_matchup_intelligence:
        filename = f"training_features_{year}_with_matchup_intel.parquet"
    else:
        filename = f"training_features_{year}_basic.parquet"
    
    # Save to processed data directory
    config = get_config()
    processed_data_dir = config.get('data.processed_data_dir', 'data/processed')
    output_path = os.path.join(project_root, processed_data_dir, filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Clean data before saving (convert string columns to numeric where possible)
    logger.info(f"🧹 Cleaning data types before saving...")
    
    # Identify and clean problematic columns
    object_columns = features_df.select_dtypes(include=['object']).columns
    for col in object_columns:
        if col not in ['player_name', 'position', 'team']:  # Keep these as strings
            try:
                # Try to convert to numeric, setting errors='coerce' to handle strings
                features_df[col] = pd.to_numeric(features_df[col], errors='coerce')
                logger.debug(f"   Converted {col} to numeric")
            except:
                logger.warning(f"   Could not convert {col} to numeric, keeping as object")
    
    # Save with compression
    features_df.to_parquet(output_path, compression='snappy', index=False)
    
    # Log save details
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    logger.info(f"✅ Saved training dataset:")
    logger.info(f"   File: {filename}")
    logger.info(f"   Size: {file_size_mb:.2f} MB")
    logger.info(f"   Players: {len(features_df):,}")
    logger.info(f"   Features: {len(features_df.columns):,}")
    
    return output_path

def generate_all_training_datasets(years: List[int], include_matchup_intelligence: bool = True, 
                                 quick_mode: bool = False) -> Dict[int, str]:
    """
    Generate training datasets for all specified years.
    
    Args:
        years: List of years to generate datasets for
        include_matchup_intelligence: Whether to include matchup intelligence
        quick_mode: If True, use quick processing (for testing)
        
    Returns:
        Dictionary mapping years to output file paths
    """
    logger.info(f"🚀 GENERATING TRAINING DATASETS FOR ALL YEARS")
    logger.info("=" * 80)
    logger.info(f"📅 Years: {years}")
    logger.info(f"🎯 Matchup Intelligence: {'✅ ENABLED' if include_matchup_intelligence else '❌ DISABLED'}")
    logger.info(f"⚡ Quick Mode: {'✅ ENABLED' if quick_mode else '❌ DISABLED'}")
    logger.info("=" * 80)
    
    generated_files = {}
    total_players = 0
    total_features = 0
    
    for i, year in enumerate(years, 1):
        logger.info(f"\n📊 PROCESSING YEAR {year} ({i}/{len(years)})")
        logger.info("-" * 40)
        
        try:
            # Generate dataset for this year
            features_df = generate_training_dataset_for_year(
                year=year,
                include_matchup_intelligence=include_matchup_intelligence
            )
            
            # Save dataset
            output_path = save_training_dataset(
                features_df=features_df, 
                year=year,
                include_matchup_intelligence=include_matchup_intelligence
            )
            
            generated_files[year] = output_path
            total_players += len(features_df) 
            total_features = len(features_df.columns)  # Same for all years
            
            logger.info(f"✅ Year {year} completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to process year {year}: {e}")
            # Fail fast - don't continue if one year fails
            raise DataQualityError(f"Training dataset generation failed for {year}: {e}")
    
    # Summary report
    logger.info(f"\n" + "=" * 80)
    logger.info(f"🎯 TRAINING DATASET GENERATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"✅ Successfully generated {len(generated_files)} datasets")
    logger.info(f"📊 Total players across all years: {total_players:,}")
    logger.info(f"🔧 Features per dataset: {total_features:,}")
    logger.info(f"💾 Files generated:")
    
    for year, path in generated_files.items():
        filename = os.path.basename(path)
        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        logger.info(f"   {year}: {filename} ({file_size_mb:.2f} MB)")
    
    return generated_files

def validate_training_datasets(generated_files: Dict[int, str]):
    """
    Validate that all generated training datasets meet quality standards.
    
    Args:
        generated_files: Dictionary mapping years to file paths
    """
    logger.info(f"\n🔍 VALIDATING TRAINING DATASETS")
    logger.info("-" * 40)
    
    for year, file_path in generated_files.items():
        logger.info(f"📊 Validating {year} dataset...")
        
        try:
            # Load and validate dataset
            df = pd.read_parquet(file_path)
            
            # Basic validation
            if df.empty:
                raise DataQualityError(f"Dataset for {year} is empty")
            
            # Position validation
            position_counts = df['position'].value_counts()
            config = get_config()
            required_positions = config.get('data.core_positions', ['QB', 'RB', 'WR', 'TE'])
            
            for position in required_positions:
                if position not in position_counts:
                    raise DataQualityError(f"Missing {position} players in {year} dataset")
                
                min_required = validator.TRAINING_MIN_PLAYERS_BY_POSITION.get(position, 10)
                actual_count = position_counts[position]
                
                if actual_count < min_required:
                    raise DataQualityError(f"Insufficient {position} players in {year}: {actual_count} < {min_required}")
            
            # Feature validation
            expected_min_features = 100  # Expect substantial feature set
            if len(df.columns) < expected_min_features:
                raise DataQualityError(f"Too few features in {year} dataset: {len(df.columns)} < {expected_min_features}")
            
            logger.info(f"   ✅ {year}: {len(df)} players, {len(df.columns)} features")
            
        except Exception as e:
            logger.error(f"   ❌ {year}: Validation failed - {e}")
            raise DataQualityError(f"Training dataset validation failed for {year}: {e}")
    
    logger.info(f"✅ All training datasets passed validation")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate training datasets with matchup intelligence')
    
    parser.add_argument(
        '--years', 
        nargs='+', 
        type=int, 
        default=[2020, 2021, 2022, 2023],
        help='Years to generate training datasets for'
    )
    
    parser.add_argument(
        '--no-matchup-intelligence',
        action='store_true',
        help='Disable matchup intelligence features'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true', 
        help='Quick mode for testing (faster processing)'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate existing datasets without regenerating'
    )
    
    return parser.parse_args()

def main():
    """Main function to generate training datasets."""
    args = parse_arguments()
    
    # Configuration
    years = sorted(args.years)
    include_matchup_intelligence = not args.no_matchup_intelligence
    quick_mode = args.quick
    validate_only = args.validate_only
    
    logger.info(f"🏈 TRAINING DATASET GENERATION STARTED")
    logger.info(f"🕐 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        if validate_only:
            # Just validate existing files
            logger.info("📋 Validation-only mode - checking existing datasets")
            
            # Build expected file paths
            generated_files = {}
            for year in years:
                if include_matchup_intelligence:
                    filename = f"training_features_{year}_with_matchup_intel.parquet"
                else:
                    filename = f"training_features_{year}_basic.parquet"
                
                config = get_config()
                processed_data_dir = config.get('data.processed_data_dir', 'data/processed')
                file_path = os.path.join(project_root, processed_data_dir, filename)
                
                if os.path.exists(file_path):
                    generated_files[year] = file_path
                else:
                    logger.error(f"❌ Missing dataset file: {filename}")
                    raise FileNotFoundError(f"Expected dataset file not found: {file_path}")
            
            validate_training_datasets(generated_files)
            
        else:
            # Generate new datasets
            generated_files = generate_all_training_datasets(
                years=years,
                include_matchup_intelligence=include_matchup_intelligence,
                quick_mode=quick_mode
            )
            
            # Validate generated datasets
            validate_training_datasets(generated_files)
        
        logger.info(f"\n🎯 SUCCESS: Training dataset generation completed successfully!")
        logger.info(f"🕐 End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        logger.error(f"❌ FAILED: Training dataset generation failed: {e}")
        logger.error(f"🕐 Failed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sys.exit(1)

if __name__ == "__main__":
    main()