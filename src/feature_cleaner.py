"""
Feature Cleaner Module for Fantasy Football ML Models

This module removes data leakage by identifying and removing same-season features
that would not be available when making real predictions about future performance.

Key Principles:
- Remove all same-season statistical features
- Keep only historical and predictive features
- Maintain only features available at prediction time
- Prevent target leakage
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Set, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class FeatureCleaner:
    """
    Removes data leakage by filtering out same-season and target-leaking features.
    
    Ensures models only use information that would be available when making
    real predictions about future player performance.
    """
    
    def __init__(self):
        """Initialize feature cleaner with predefined feature categories."""
        
        # Features that directly leak the target (fantasy points)
        self.direct_leakage_features = {
            'fantasy_points', 'fantasy_points_ppr', 'target_points', 'points_per_game'
        }
        
        # Same-season statistics that wouldn't be available for future prediction
        self.same_season_stats = {
            # Passing stats
            'completions', 'attempts', 'passing_yards', 'passing_tds', 'interceptions',
            'sacks', 'sack_yards', 'sack_fumbles', 'sack_fumbles_lost', 
            'passing_air_yards', 'passing_yards_after_catch', 'passing_first_downs',
            'passing_epa', 'passing_2pt_conversions', 'pacr', 'dakota',
            
            # Rushing stats  
            'carries', 'rushing_yards', 'rushing_tds', 'rushing_fumbles_x', 'rushing_fumbles_y',
            'rushing_fumbles_lost', 'rushing_first_downs', 'rushing_epa', 'rushing_2pt_conversions',
            
            # Receiving stats
            'targets', 'receptions', 'receiving_yards', 'receiving_tds',
            'receiving_fumbles', 'receiving_fumbles_lost', 'receiving_air_yards',
            'receiving_yards_after_catch', 'receiving_first_downs', 'receiving_epa',
            'receiving_2pt_conversions', 'racr', 'target_share', 'air_yards_share',
            'wopr_x', 'wopr_y', 'tgt_sh', 'ay_sh', 'yac_sh', 'ry_sh', 'rfd_sh',
            'rtdfd_sh', 'yptmpa', 'ppr_sh',
            
            # Game-level stats
            'yards_per_reception', 'passing_yards_per_game', 'games', 'weeks_played',
            'special_teams_tds'
        }
        
        # Non-predictive metadata that shouldn't be used for prediction
        self.non_predictive_metadata = {
            'recent_team', 'opponent_team', 'headshot_url', 'gsis_id',
            'season_type'  # Regular season vs playoffs
        }
        
        # Features that are acceptable to use (available before season starts)
        self.acceptable_features = {
            # Player identifiers (for tracking, not prediction)
            'player_id', 'player_display_name', 'first_name', 'last_name',
            
            # Static player attributes
            'birth_date', 'college_name', 'position_group',
            
            # Temporal information
            'year',
            
            # Historical averages and trends (these would need to be computed from past seasons)
            # Note: Current implementation may still have these as same-season, needs verification
        }
        
        logger.info("🧹 FeatureCleaner initialized")
        logger.info(f"   Direct leakage features: {len(self.direct_leakage_features)}")
        logger.info(f"   Same-season stats: {len(self.same_season_stats)}")
        logger.info(f"   Non-predictive metadata: {len(self.non_predictive_metadata)}")
        logger.info(f"   Acceptable features: {len(self.acceptable_features)}")
    
    def identify_problematic_features(self, columns: List[str]) -> Dict[str, Set[str]]:
        """
        Identify problematic features in a dataset.
        
        Args:
            columns: List of column names from dataset
            
        Returns:
            Dictionary categorizing problematic features
        """
        columns_set = set(columns)
        
        found_issues = {
            'direct_leakage': columns_set.intersection(self.direct_leakage_features),
            'same_season_stats': columns_set.intersection(self.same_season_stats),
            'non_predictive': columns_set.intersection(self.non_predictive_metadata),
            'acceptable': columns_set.intersection(self.acceptable_features),
            'unknown': columns_set - (
                self.direct_leakage_features | 
                self.same_season_stats | 
                self.non_predictive_metadata | 
                self.acceptable_features
            )
        }
        
        return found_issues
    
    def clean_features(self, df: pd.DataFrame, position: str) -> pd.DataFrame:
        """
        Remove problematic features from dataset.
        
        Args:
            df: Input DataFrame
            position: Player position for logging context
            
        Returns:
            Cleaned DataFrame with problematic features removed
        """
        if df.empty:
            return df
            
        logger.info(f"🧹 Cleaning features for {position}...")
        logger.info(f"   Input shape: {df.shape}")
        
        # Analyze current features
        issues = self.identify_problematic_features(df.columns.tolist())
        
        # Log findings
        for issue_type, features in issues.items():
            if features:
                logger.info(f"   {issue_type.replace('_', ' ').title()}: {len(features)} features")
                if issue_type in ['direct_leakage', 'same_season_stats']:
                    # Show specific problematic features
                    feature_list = sorted(list(features))[:10]  # Show first 10
                    more_count = len(features) - 10
                    logger.warning(f"     Removing: {feature_list}{f' + {more_count} more' if more_count > 0 else ''}")
        
        # Define features to remove
        features_to_remove = (
            issues['direct_leakage'] | 
            issues['same_season_stats'] | 
            issues['non_predictive']
        )
        
        # Features to keep
        features_to_keep = [col for col in df.columns if col not in features_to_remove]
        
        # Create cleaned dataset
        df_cleaned = df[features_to_keep].copy()
        
        logger.info(f"   ✂️  Removed {len(features_to_remove)} problematic features")
        logger.info(f"   ✅ Output shape: {df_cleaned.shape}")
        logger.info(f"   📉 Features remaining: {len(features_to_keep)}")
        
        # Handle remaining features
        if issues['unknown']:
            logger.warning(f"   ⚠️  Unknown features kept: {sorted(list(issues['unknown']))}")
            logger.warning(f"      These need manual review for data leakage")
        
        return df_cleaned
    
    def validate_cleaned_features(self, df: pd.DataFrame, position: str) -> Dict[str, any]:
        """
        Validate that cleaned features don't contain obvious data leakage.
        
        Args:
            df: Cleaned DataFrame
            position: Player position
            
        Returns:
            Validation report
        """
        logger.info(f"🔍 Validating cleaned features for {position}...")
        
        validation_report = {
            'position': position,
            'total_features': len(df.columns),
            'sample_size': len(df),
            'features_per_sample_ratio': len(df.columns) / max(len(df), 1),
            'issues_found': [],
            'validation_passed': True
        }
        
        # Check for remaining problematic features
        remaining_issues = self.identify_problematic_features(df.columns.tolist())
        
        if remaining_issues['direct_leakage']:
            validation_report['issues_found'].append(
                f"Direct target leakage still present: {remaining_issues['direct_leakage']}"
            )
            validation_report['validation_passed'] = False
        
        if remaining_issues['same_season_stats']:
            validation_report['issues_found'].append(
                f"Same-season stats still present: {len(remaining_issues['same_season_stats'])} features"
            )
            validation_report['validation_passed'] = False
        
        # Check feature-to-sample ratio (should be reasonable for ML)
        if validation_report['features_per_sample_ratio'] > 0.5:
            validation_report['issues_found'].append(
                f"Too many features per sample: {validation_report['features_per_sample_ratio']:.2f} (should be < 0.1)"
            )
            validation_report['validation_passed'] = False
        
        # Log results
        if validation_report['validation_passed']:
            logger.info(f"   ✅ Validation PASSED for {position}")
            logger.info(f"   📊 {validation_report['total_features']} features for {validation_report['sample_size']} samples")
            logger.info(f"   📈 Feature/sample ratio: {validation_report['features_per_sample_ratio']:.3f}")
        else:
            logger.error(f"   ❌ Validation FAILED for {position}")
            for issue in validation_report['issues_found']:
                logger.error(f"     • {issue}")
        
        return validation_report
    
    def create_historical_features(self, splits: Dict[str, pd.DataFrame], position: str) -> Dict[str, pd.DataFrame]:
        """
        Create proper historical features for each split.
        
        This is a placeholder for the more complex task of creating features
        from historical data only (e.g., previous season averages, career trends).
        
        Args:
            splits: Dictionary of temporal splits
            position: Player position
            
        Returns:
            Dictionary of splits with proper historical features
        """
        logger.info(f"🏗️  Creating historical features for {position}...")
        
        cleaned_splits = {}
        
        for split_name, split_df in splits.items():
            if split_df.empty:
                cleaned_splits[split_name] = split_df
                continue
            
            # Clean current features
            cleaned_df = self.clean_features(split_df, f"{position}_{split_name}")
            
            # Validate cleaned features  
            validation = self.validate_cleaned_features(cleaned_df, f"{position}_{split_name}")
            
            cleaned_splits[split_name] = cleaned_df
        
        return cleaned_splits


def main():
    """Test the feature cleaning functionality."""
    import sys
    sys.path.append('.')
    from src.temporal_validation import TemporalDataSplitter
    
    logging.basicConfig(level=logging.INFO)
    
    cleaner = FeatureCleaner()
    splitter = TemporalDataSplitter("data/processed")
    
    print("🧹 Feature Cleaning Analysis")
    print("=" * 50)
    
    positions = ['QB', 'RB', 'WR', 'TE']
    
    for position in positions:
        try:
            print(f"\n{position} Position Feature Analysis:")
            
            # Get temporal splits
            splits = splitter.get_temporal_splits(position)
            
            # Clean features
            cleaned_splits = cleaner.create_historical_features(splits, position)
            
            # Summary
            for split_name, split_df in cleaned_splits.items():
                if not split_df.empty:
                    print(f"  {split_name:>10}: {len(split_df):>3} samples, {len(split_df.columns):>2} features")
                else:
                    print(f"  {split_name:>10}: No data")
        
        except Exception as e:
            print(f"\n{position} Position: ❌ Error - {e}")

if __name__ == "__main__":
    main()