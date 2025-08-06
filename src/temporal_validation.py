"""
Temporal Data Splitting Module for Fantasy Football ML Models

This module implements proper temporal validation to prevent data leakage
by ensuring models only use historical data to predict future performance.

Key Principles:
- Training data: Historical seasons (2010-2022)  
- Validation data: Recent season (2023)
- Test data: Future season (2024)
- No same-season features allowed
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TemporalDataSplitter:
    """
    Implements proper temporal validation splits for fantasy football prediction.
    
    Ensures no data leakage by using only historical seasons to predict future performance.
    """
    
    def __init__(self, data_dir: str = "data/processed"):
        """
        Initialize temporal data splitter.
        
        Args:
            data_dir: Path to processed data directory
        """
        self.data_dir = Path(data_dir)
        self.position_dir = self.data_dir / "position_specific"
        
        # Define temporal splits
        self.train_years = list(range(2010, 2023))  # 2010-2022 for training
        self.validation_year = 2023                  # 2023 for validation  
        self.test_year = 2024                        # 2024 for test
        
        logger.info("🕐 TemporalDataSplitter initialized")
        logger.info(f"   Training years: {self.train_years[0]}-{self.train_years[-1]} ({len(self.train_years)} years)")
        logger.info(f"   Validation year: {self.validation_year}")
        logger.info(f"   Test year: {self.test_year}")
    
    def get_temporal_splits(self, position: str) -> Dict[str, pd.DataFrame]:
        """
        Get temporal data splits for a position.
        
        Args:
            position: Player position (QB, RB, WR, TE)
            
        Returns:
            Dictionary with train, validation, and test DataFrames
        """
        position = position.upper()
        logger.info(f"📊 Loading temporal splits for {position}...")
        
        # Load all available data for position
        position_path = self.position_dir / position.lower()
        
        if not position_path.exists():
            raise FileNotFoundError(f"Position data not found: {position_path}")
        
        # Collect data by year
        train_dfs = []
        validation_df = None
        test_df = None
        
        # Load training data (2010-2022)
        for year in self.train_years:
            file_path = position_path / f"{position.lower()}_features_{year}.parquet"
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    df['data_year'] = year
                    df['split'] = 'train'
                    train_dfs.append(df)
                    logger.info(f"   ✅ Loaded {year} training data: {len(df)} samples")
                except Exception as e:
                    logger.warning(f"   ⚠️ Could not load {year} data: {e}")
        
        # Load validation data (2023)
        val_file = position_path / f"{position.lower()}_features_{self.validation_year}.parquet"
        if val_file.exists():
            try:
                validation_df = pd.read_parquet(val_file)
                validation_df['data_year'] = self.validation_year
                validation_df['split'] = 'validation'
                logger.info(f"   ✅ Loaded {self.validation_year} validation data: {len(validation_df)} samples")
            except Exception as e:
                logger.warning(f"   ⚠️ Could not load validation data: {e}")
        
        # Load test data (2024)
        test_file = position_path / f"{position.lower()}_features_{self.test_year}.parquet"
        if test_file.exists():
            try:
                test_df = pd.read_parquet(test_file)
                test_df['data_year'] = self.test_year
                test_df['split'] = 'test'
                logger.info(f"   ✅ Loaded {self.test_year} test data: {len(test_df)} samples")
            except Exception as e:
                logger.warning(f"   ⚠️ Could not load test data: {e}")
        
        # Combine training data
        if train_dfs:
            train_combined = pd.concat(train_dfs, ignore_index=True)
            logger.info(f"   📈 Combined training data: {len(train_combined)} samples from {len(train_dfs)} years")
        else:
            train_combined = pd.DataFrame()
            logger.error(f"   ❌ No training data found for {position}")
        
        # Prepare results
        splits = {
            'train': train_combined,
            'validation': validation_df if validation_df is not None else pd.DataFrame(),
            'test': test_df if test_df is not None else pd.DataFrame()
        }
        
        # Log split summary
        logger.info(f"📋 Temporal splits summary for {position}:")
        for split_name, split_df in splits.items():
            if not split_df.empty:
                years = split_df['data_year'].unique() if 'data_year' in split_df.columns else ['unknown']
                logger.info(f"   {split_name:>10}: {len(split_df):>4} samples from {sorted(years)}")
            else:
                logger.warning(f"   {split_name:>10}: No data available")
        
        return splits
    
    def validate_temporal_integrity(self, splits: Dict[str, pd.DataFrame]) -> bool:
        """
        Validate that temporal splits maintain proper time ordering.
        
        Args:
            splits: Dictionary of split DataFrames
            
        Returns:
            True if temporal integrity is maintained
        """
        logger.info("🔍 Validating temporal integrity...")
        
        issues = []
        
        for split_name, split_df in splits.items():
            if split_df.empty:
                continue
                
            if 'data_year' not in split_df.columns:
                issues.append(f"{split_name} split missing data_year column")
                continue
            
            years = sorted(split_df['data_year'].unique())
            
            # Check year ranges
            if split_name == 'train':
                invalid_years = [y for y in years if y not in self.train_years]
                if invalid_years:
                    issues.append(f"Training data contains invalid years: {invalid_years}")
            
            elif split_name == 'validation':
                if len(years) != 1 or years[0] != self.validation_year:
                    issues.append(f"Validation data should only contain {self.validation_year}, found: {years}")
            
            elif split_name == 'test':
                if len(years) != 1 or years[0] != self.test_year:
                    issues.append(f"Test data should only contain {self.test_year}, found: {years}")
        
        if issues:
            logger.error("❌ Temporal integrity validation FAILED:")
            for issue in issues:
                logger.error(f"   • {issue}")
            return False
        else:
            logger.info("✅ Temporal integrity validation PASSED")
            return True
    
    def get_data_summary(self, position: str) -> Dict:
        """
        Get comprehensive data summary for a position.
        
        Args:
            position: Player position
            
        Returns:
            Dictionary with data summary statistics
        """
        splits = self.get_temporal_splits(position)
        
        summary = {
            'position': position.upper(),
            'total_samples': sum(len(df) for df in splits.values()),
            'splits': {},
            'temporal_integrity': self.validate_temporal_integrity(splits),
            'generated_at': datetime.now().isoformat()
        }
        
        for split_name, split_df in splits.items():
            if not split_df.empty:
                years = sorted(split_df['data_year'].unique()) if 'data_year' in split_df.columns else []
                summary['splits'][split_name] = {
                    'samples': len(split_df),
                    'years': years,
                    'year_range': f"{min(years)}-{max(years)}" if years else "No data"
                }
            else:
                summary['splits'][split_name] = {
                    'samples': 0,
                    'years': [],
                    'year_range': "No data"
                }
        
        return summary

def main():
    """Test the temporal data splitting functionality."""
    logging.basicConfig(level=logging.INFO)
    
    splitter = TemporalDataSplitter("data/processed")
    
    positions = ['QB', 'RB', 'WR', 'TE']
    
    print("🕐 Temporal Data Splitting Analysis")
    print("=" * 50)
    
    for position in positions:
        try:
            summary = splitter.get_data_summary(position)
            print(f"\n{position} Position Summary:")
            print(f"  Total samples: {summary['total_samples']}")
            print(f"  Temporal integrity: {'✅ PASS' if summary['temporal_integrity'] else '❌ FAIL'}")
            
            for split_name, split_info in summary['splits'].items():
                print(f"  {split_name:>10}: {split_info['samples']:>3} samples ({split_info['year_range']})")
        
        except Exception as e:
            print(f"\n{position} Position: ❌ Error - {e}")

if __name__ == "__main__":
    main()