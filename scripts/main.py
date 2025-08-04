#!/usr/bin/env python3
"""
Fantasy Draft Engine - Complete Pipeline Runner

This script runs the complete end-to-end pipeline:
1. Fetch NFL data from 2010-2023 (5 min)
2. Engineer 300+ features (3 min)
3. Train position-specific models (10 min)
4. Generate draft rankings (30 sec)

Usage:
    python scripts/main.py
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(project_root / 'logs' / 'pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

def create_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        'data/raw',
        'data/processed',
        'data/processed/position_specific',
        'data/draft_lists',
        'saved_models',
        'plots',
        'logs'
    ]
    
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def step_1_data_acquisition():
    """Step 1: Fetch NFL data from 2010-2023."""
    logger.info("="*80)
    logger.info("STEP 1: Data Acquisition (2010-2023 NFL Data)")
    logger.info("="*80)
    
    start_time = time.time()
    
    try:
        from src.data_acquisition import fetch_and_save_historical_data
        from src.config import get_config
        
        config = get_config()
        data_start_year = config.get('data.data_start_year', 2010)
        data_end_year = config.get('data.data_end_year', 2024)
        positions = config.get('data.positions', ['QB', 'RB', 'WR', 'TE', 'K'])
        
        logger.info(f"Fetching NFL data from {data_start_year} to {data_end_year}...")
        logger.info("This may take 5-8 minutes depending on your internet connection...")
        
        saved_files = fetch_and_save_historical_data(
            start_year=data_start_year,
            end_year=data_end_year,
            positions=positions
        )
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Data acquisition completed in {elapsed:.1f} seconds")
        logger.info(f"✅ Saved {len(saved_files)} season files")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Data acquisition failed: {str(e)}")
        return False

def step_2_data_cleaning():
    """Step 2: Clean and prepare data."""
    logger.info("="*80)
    logger.info("STEP 2: Data Cleaning & Preparation")
    logger.info("="*80)
    
    start_time = time.time()
    
    try:
        from src.data_cleaning import clean_and_save_historical_data
        from src.config import get_config
        
        config = get_config()
        data_start_year = config.get('data.data_start_year', 2010)
        data_end_year = config.get('data.data_end_year', 2024)
        positions = config.get('data.positions', ['QB', 'RB', 'WR', 'TE', 'K'])
        
        logger.info("Cleaning and standardizing player data...")
        
        clean_and_save_historical_data(
            start_year=data_start_year,
            end_year=data_end_year,
            positions=positions
        )
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Data cleaning completed in {elapsed:.1f} seconds")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Data cleaning failed: {str(e)}")
        return False

def step_3_feature_engineering():
    """Step 3: Engineer 300+ features per position."""
    logger.info("="*80)
    logger.info("STEP 3: Feature Engineering (300+ Features)")
    logger.info("="*80)
    
    start_time = time.time()
    
    try:
        from src.feature_engineering import engineer_and_save_features
        from src.config import get_config
        
        config = get_config()
        data_start_year = config.get('data.data_start_year', 2010)
        data_end_year = config.get('data.data_end_year', 2024)
        positions = config.get('data.positions', ['QB', 'RB', 'WR', 'TE', 'K'])
        
        logger.info("Engineering position-specific features...")
        logger.info("Creating efficiency metrics, usage patterns, and advanced stats...")
        
        engineer_and_save_features(
            start_year=data_start_year,
            end_year=data_end_year - 1,  # Don't use final year as features
            positions=positions
        )
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Feature engineering completed in {elapsed:.1f} seconds")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Feature engineering failed: {str(e)}")
        return False

def step_4_model_training():
    """Step 4: Train position-specific ML models."""
    logger.info("="*80)
    logger.info("STEP 4: Model Training (6 Positions)")
    logger.info("="*80)
    
    start_time = time.time()
    
    try:
        # Import and run the model training script
        script_path = project_root / 'scripts' / 'train_models.py'
        
        # Execute the script
        import subprocess
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=True, text=True, cwd=str(project_root))
        
        if result.returncode != 0:
            logger.error(f"Model training failed: {result.stderr}")
            return False
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Model training completed in {elapsed:.1f} seconds")
        logger.info("✅ Trained models for QB, RB, WR, TE, K, DST positions")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Model training failed: {str(e)}")
        return False

def step_5_generate_rankings():
    """Step 5: Generate draft rankings."""
    logger.info("="*80)
    logger.info("STEP 5: Draft Ranking Generation")
    logger.info("="*80)
    
    start_time = time.time()
    
    try:
        # Import and run the draft ranking generator
        script_path = project_root / 'scripts' / 'generate_draft_rankings.py'
        
        # Execute the script
        import subprocess
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=True, text=True, cwd=str(project_root))
        
        if result.returncode != 0:
            logger.error(f"Draft ranking generation failed: {result.stderr}")
            return False
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Draft rankings generated in {elapsed:.1f} seconds")
        
        # List generated files
        draft_lists_dir = project_root / 'data' / 'draft_lists'
        if draft_lists_dir.exists():
            files = list(draft_lists_dir.glob('*'))
            logger.info(f"✅ Generated {len(files)} draft list files")
            
            # Show key files
            for file in files:
                if 'overall_rankings' in file.name or 'cheatsheet' in file.name:
                    logger.info(f"   📄 {file.name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Draft ranking generation failed: {str(e)}")
        return False

def main():
    """Run the complete fantasy draft engine pipeline."""
    overall_start = time.time()
    
    logger.info("🏈 Fantasy Draft Engine - Complete Pipeline")
    logger.info("📊 AI-powered rankings from 14 years of NFL data")
    logger.info("🤖 Training ensemble models for 6 positions")
    logger.info("")
    
    # Create necessary directories
    create_directories()
    
    # Track success of each step
    steps = [
        ("Data Acquisition", step_1_data_acquisition),
        ("Data Cleaning", step_2_data_cleaning),
        ("Feature Engineering", step_3_feature_engineering),
        ("Model Training", step_4_model_training),
        ("Generate Rankings", step_5_generate_rankings)
    ]
    
    completed_steps = 0
    
    for step_name, step_func in steps:
        try:
            if step_func():
                completed_steps += 1
            else:
                logger.error(f"❌ Pipeline failed at step: {step_name}")
                break
        except KeyboardInterrupt:
            logger.warning("⚠️ Pipeline interrupted by user")
            break
        except Exception as e:
            logger.error(f"❌ Unexpected error in {step_name}: {str(e)}")
            break
    
    # Final summary
    total_elapsed = time.time() - overall_start
    logger.info("="*80)
    logger.info("PIPELINE SUMMARY")
    logger.info("="*80)
    logger.info(f"✅ Completed Steps: {completed_steps}/{len(steps)}")
    logger.info(f"⏱️  Total Runtime: {total_elapsed/60:.1f} minutes")
    
    if completed_steps == len(steps):
        logger.info("🎉 SUCCESS: Complete pipeline finished!")
        logger.info("📋 Your draft rankings are ready!")
        logger.info("")
        logger.info("📁 Check these directories:")
        logger.info("   📄 data/draft_lists/ - CSV rankings and text cheatsheet")
        logger.info("   📊 plots/ - Visual draft board and model analysis")
        logger.info("   🤖 saved_models/ - Trained ML models")
        logger.info("")
        logger.info("🚀 Ready to dominate your fantasy draft!")
    else:
        logger.error("❌ Pipeline did not complete successfully")
        logger.error("🔍 Check the logs above for error details")
    
    return completed_steps == len(steps)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)