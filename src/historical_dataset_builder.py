"""
Historical Dataset Builder for Fantasy Football ML Models

This module creates proper historical training datasets by:
1. Using only data available before prediction time
2. Building historical features from past seasons
3. Creating proper train/validation/test splits
4. Ensuring no data leakage
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging
from datetime import datetime
import joblib

from temporal_validation import TemporalDataSplitter
from feature_cleaner import FeatureCleaner

logger = logging.getLogger(__name__)

class HistoricalDatasetBuilder:
    """
    Builds proper historical datasets for fantasy football prediction.
    
    Creates features using only historical data and ensures proper temporal splits.
    """
    
    def __init__(self, data_dir: str = "data/processed"):
        """
        Initialize historical dataset builder.
        
        Args:
            data_dir: Path to processed data directory
        """
        self.data_dir = Path(data_dir)
        self.output_dir = self.data_dir / "historical_training"
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.splitter = TemporalDataSplitter(data_dir)
        self.cleaner = FeatureCleaner()
        
        # Define minimum viable feature set
        self.minimal_features = {
            'year', 'data_year', 'position', 
            'player_id', 'player_display_name', 'player_name',
            'birth_date', 'college_name'
        }
        
        logger.info("🏗️ HistoricalDatasetBuilder initialized")
        logger.info(f"   Output directory: {self.output_dir}")
    
    def build_position_datasets(self, position: str, save: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Build historical datasets for a specific position.
        
        Args:
            position: Player position (QB, RB, WR, TE)
            save: Whether to save datasets to disk
            
        Returns:
            Dictionary with train, validation, and test DataFrames
        """
        logger.info(f"🔨 Building historical datasets for {position}...")
        
        # Get temporal splits
        splits = self.splitter.get_temporal_splits(position)
        
        # Clean features (remove same-season data leakage)
        cleaned_splits = self.cleaner.create_historical_features(splits, position)
        
        # Build proper historical features
        final_datasets = {}
        
        for split_name, split_df in cleaned_splits.items():
            if split_df.empty:
                final_datasets[split_name] = split_df
                continue
            
            logger.info(f"   Processing {split_name} split for {position}...")
            
            # Create historical feature set
            processed_df = self._create_minimal_feature_set(split_df, position, split_name)
            
            final_datasets[split_name] = processed_df
            
            logger.info(f"   ✅ {split_name} processed: {len(processed_df)} samples, {len(processed_df.columns)} features")
        
        # Validate final datasets
        validation_report = self._validate_datasets(final_datasets, position)
        
        if save and validation_report['validation_passed']:
            self._save_datasets(final_datasets, position)
        
        return final_datasets
    
    def _create_minimal_feature_set(self, df: pd.DataFrame, position: str, split_name: str) -> pd.DataFrame:
        """
        Create a minimal, safe feature set for initial modeling.
        
        Args:
            df: Input DataFrame
            position: Player position
            split_name: Split name (train/validation/test)
            
        Returns:
            DataFrame with minimal feature set
        """
        if df.empty:
            return df
        
        # Start with essential columns
        essential_cols = list(self.minimal_features.intersection(set(df.columns)))
        
        # Add target variable if available (only for train split)
        target_candidates = ['fantasy_points_per_game']
        target_col = None
        
        for candidate in target_candidates:
            if candidate in df.columns:
                target_col = candidate
                essential_cols.append(candidate)
                break
        
        # Add a few safe derived features that should be available historically
        safe_features = []
        
        # Player age (can be calculated from birth_date)
        if 'birth_date' in df.columns and 'year' in df.columns:
            try:
                df_copy = df.copy()
                df_copy['birth_date'] = pd.to_datetime(df_copy['birth_date'], errors='coerce')
                df_copy['age'] = df_copy['year'] - df_copy['birth_date'].dt.year
                safe_features.append('age')
                df = df_copy
            except Exception as e:
                logger.warning(f"Could not calculate age: {e}")
        
        # Experience level (years since first appearance)
        # This would need to be calculated properly from historical data
        
        # Add safe features to essential columns
        for feature in safe_features:
            if feature in df.columns:
                essential_cols.append(feature)
        
        # Select only available columns
        final_cols = [col for col in essential_cols if col in df.columns]
        
        # Create final dataset
        result_df = df[final_cols].copy()
        
        # Add metadata about the dataset
        result_df['split'] = split_name
        result_df['dataset_created'] = datetime.now().isoformat()
        
        logger.info(f"      Created minimal feature set: {len(final_cols)} features")
        if target_col:
            logger.info(f"      Target variable: {target_col}")
        else:
            logger.warning(f"      No target variable found for {split_name}")
        
        return result_df
    
    def _validate_datasets(self, datasets: Dict[str, pd.DataFrame], position: str) -> Dict[str, any]:
        """
        Validate the final datasets for machine learning readiness.
        
        Args:
            datasets: Dictionary of datasets
            position: Player position
            
        Returns:
            Validation report
        """
        logger.info(f"🔍 Validating final datasets for {position}...")
        
        validation_report = {
            'position': position,
            'validation_passed': True,
            'issues': [],
            'dataset_stats': {}
        }
        
        for split_name, df in datasets.items():
            if df.empty:
                validation_report['dataset_stats'][split_name] = {
                    'samples': 0,
                    'features': 0,
                    'has_target': False
                }
                continue
            
            # Check dataset stats
            has_target = 'fantasy_points_per_game' in df.columns
            stats = {
                'samples': len(df),
                'features': len(df.columns),
                'has_target': has_target,
                'feature_to_sample_ratio': len(df.columns) / len(df) if len(df) > 0 else 0
            }
            
            validation_report['dataset_stats'][split_name] = stats
            
            # Validation checks
            if split_name in ['validation', 'test'] and stats['feature_to_sample_ratio'] > 1.0:
                validation_report['issues'].append(
                    f"{split_name} split has too many features per sample: {stats['feature_to_sample_ratio']:.2f}"
                )
                # Don't fail validation for this since we're building minimal datasets
            
            if split_name == 'train' and not has_target:
                validation_report['issues'].append(f"Training data missing target variable")
                validation_report['validation_passed'] = False
            
            if stats['samples'] == 0:
                validation_report['issues'].append(f"{split_name} split is empty")
                if split_name == 'train':
                    validation_report['validation_passed'] = False
        
        # Log validation results
        if validation_report['validation_passed']:
            logger.info(f"   ✅ Dataset validation PASSED for {position}")
        else:
            logger.error(f"   ❌ Dataset validation FAILED for {position}")
        
        for issue in validation_report['issues']:
            logger.warning(f"     • {issue}")
        
        # Log dataset summary
        logger.info(f"   📊 Dataset Summary for {position}:")
        for split_name, stats in validation_report['dataset_stats'].items():
            if stats['samples'] > 0:
                logger.info(f"     {split_name:>10}: {stats['samples']:>3} samples, {stats['features']:>2} features, target: {'✅' if stats['has_target'] else '❌'}")
            else:
                logger.info(f"     {split_name:>10}: No data")
        
        return validation_report
    
    def _save_datasets(self, datasets: Dict[str, pd.DataFrame], position: str) -> None:
        """
        Save datasets to disk.
        
        Args:
            datasets: Dictionary of datasets to save
            position: Player position
        """
        logger.info(f"💾 Saving datasets for {position}...")
        
        position_dir = self.output_dir / position.lower()
        position_dir.mkdir(exist_ok=True)
        
        saved_files = []
        
        for split_name, df in datasets.items():
            if df.empty:
                continue
            
            filename = f"{position.lower()}_{split_name}_historical.parquet"
            filepath = position_dir / filename
            
            try:
                df.to_parquet(filepath, index=False)
                saved_files.append(filepath)
                logger.info(f"   ✅ Saved {split_name}: {filepath}")
            except Exception as e:
                logger.error(f"   ❌ Failed to save {split_name}: {e}")
        
        # Save metadata
        metadata = {
            'position': position,
            'created_at': datetime.now().isoformat(),
            'datasets': {name: len(df) for name, df in datasets.items()},
            'files': [str(f) for f in saved_files]
        }
        
        metadata_file = position_dir / f"{position.lower()}_metadata.json"
        import json
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"   📄 Saved metadata: {metadata_file}")
    
    def build_all_positions(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Build historical datasets for all positions.
        
        Returns:
            Dictionary mapping positions to their datasets
        """
        logger.info("🏭 Building historical datasets for all positions...")
        
        positions = ['QB', 'RB', 'WR', 'TE']
        all_datasets = {}
        
        for position in positions:
            try:
                datasets = self.build_position_datasets(position)
                all_datasets[position] = datasets
                logger.info(f"✅ Completed {position}")
            except Exception as e:
                logger.error(f"❌ Failed to build {position} datasets: {e}")
                all_datasets[position] = {}
        
        # Create summary report
        self._create_summary_report(all_datasets)
        
        return all_datasets
    
    def _create_summary_report(self, all_datasets: Dict[str, Dict[str, pd.DataFrame]]) -> None:
        """Create a summary report of all generated datasets."""
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'positions': {},
            'total_samples': 0,
            'validation_summary': {}
        }
        
        for position, datasets in all_datasets.items():
            position_stats = {
                'splits': {},
                'total_samples': 0
            }
            
            for split_name, df in datasets.items():
                split_stats = {
                    'samples': len(df) if not df.empty else 0,
                    'features': len(df.columns) if not df.empty else 0,
                    'has_target': 'fantasy_points_per_game' in df.columns if not df.empty else False
                }
                position_stats['splits'][split_name] = split_stats
                position_stats['total_samples'] += split_stats['samples']
            
            report['positions'][position] = position_stats
            report['total_samples'] += position_stats['total_samples']
        
        # Save report
        report_file = self.output_dir / 'dataset_summary.json'
        import json
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📋 Summary report saved: {report_file}")
        logger.info(f"🎯 Total samples across all positions: {report['total_samples']}")


def main():
    """Test the historical dataset building functionality."""
    logging.basicConfig(level=logging.INFO)
    
    builder = HistoricalDatasetBuilder("data/processed")
    
    print("🏗️ Historical Dataset Building")
    print("=" * 50)
    
    # Build datasets for all positions
    all_datasets = builder.build_all_positions()
    
    print("\n📊 Final Summary:")
    print("-" * 30)
    
    for position, datasets in all_datasets.items():
        total_samples = sum(len(df) for df in datasets.values() if not df.empty)
        print(f"{position}: {total_samples} total samples")
        
        for split_name, df in datasets.items():
            if not df.empty:
                target_status = "✅" if 'fantasy_points_per_game' in df.columns else "❌"
                print(f"  {split_name:>10}: {len(df):>3} samples, {len(df.columns):>2} features, target: {target_status}")

if __name__ == "__main__":
    main()