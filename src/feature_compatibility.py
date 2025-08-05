"""
Feature Compatibility System for Matchup Intelligence Integration

This module bridges the gap between legacy ensemble models (trained on older features)
and the current enhanced feature engineering pipeline with matchup intelligence.

Key functions:
1. Maps new feature names to legacy model expectations
2. Creates missing legacy features from available enhanced features  
3. Handles position-specific feature compatibility
4. Provides fallback values for unavailable features
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Set, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class FeatureCompatibilityMapper:
    """Maps enhanced features to legacy model expectations."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Core feature mappings: enhanced name → legacy name
        self.core_mappings = {
            # Basic stats (reverse mapping from new to legacy)
            'passing_attempts': 'attempts',
            'passing_completions': 'completions',
            'rushing_attempts': 'carries', 
            'games_played': 'games',
            'rec_yards': 'receiving_yards',
            'rush_yards': 'rushing_yards',
            'pass_yards': 'passing_yards',
            'rec_tds': 'receiving_touchdowns',
            'rush_tds': 'rushing_touchdowns', 
            'pass_tds': 'passing_touchdowns',
            
            # Efficiency metrics
            'yards_per_attempt': 'ya_per_att',
            'passer_rating': 'qb_rating',
            'touchdown_percentage': 'passing_td_percentage',
            'interception_percentage': 'int_percentage',
            
            # Receiving metrics
            'catch_rate': 'reception_rate',
            'yards_per_reception': 'ypr',
            'yards_per_target': 'ypt',
            'touchdowns_per_reception': 'td_per_reception',
            'touchdowns_per_target': 'td_per_target',
            
            # Team context
            'team_passing_attempts': 'team_attempts',
            'team_rushing_attempts': 'team_carries',
            'team_passing_touchdowns': 'team_passing_tds',
            'team_rushing_touchdowns': 'team_rushing_tds',
        }
        
        # Features that need to be created from enhanced features
        self.synthetic_features = {
            # Air yards features
            'air_yards_dominance': self._calculate_air_yards_dominance,
            'air_yards_efficiency': self._calculate_air_yards_efficiency,
            
            # Snap share features
            'avg_snap_share': self._calculate_avg_snap_share,
            'fantasy_points_per_snap': self._calculate_fantasy_points_per_snap,
            
            # Target/catch features
            'contested_catch_rate': self._calculate_contested_catch_rate,
            'deep_target_indicator': self._calculate_deep_target_indicator,
            'deep_target_rate': self._calculate_deep_target_rate,
            
            # Usage features
            'early_down_rate': self._calculate_early_down_rate,
            'carries_per_snap': self._calculate_carries_per_snap,
            'blocking_snap_estimate': self._calculate_blocking_snap_estimate,
            
            # Efficiency derived features
            'target_quality': self._calculate_target_quality,
            'usage_sustainability': self._calculate_usage_sustainability,
            'snap_share_tier': self._calculate_snap_share_tier,
            'player_tier': self._calculate_player_tier,
        }
        
        # Default fallback values for missing features
        self.fallback_values = {
            'air_yards_dominance': 0.1,
            'air_yards_efficiency': 1.0,
            'avg_snap_share': 0.5,
            'fantasy_points_per_snap': 0.1,
            'contested_catch_rate': 0.6,
            'deep_target_indicator': 0.0,
            'deep_target_rate': 0.1,
            'early_down_rate': 0.6,
            'carries_per_snap': 0.0,
            'blocking_snap_estimate': 0.1,
            'target_quality': 1.0,
            'usage_sustainability': 0.5,
            'snap_share_tier': 0.3,
            'player_tier': 0.5,
        }
    
    def create_compatible_features(
        self, 
        df: pd.DataFrame, 
        expected_features: List[str], 
        position: str
    ) -> pd.DataFrame:
        """
        Create a feature set compatible with legacy ensemble models.
        
        Args:
            df: DataFrame with enhanced features
            expected_features: List of features the model expects
            position: Player position for position-specific handling
        
        Returns:
            DataFrame with compatible features for model prediction
        """
        self.logger.info(f"🔧 Creating compatible features for {position}")
        self.logger.info(f"   Input features: {len(df.columns)}")
        self.logger.info(f"   Expected features: {len(expected_features)}")
        
        # Start with copy of input data
        compatible_df = df.copy()
        
        # Step 1: Apply core mappings (rename columns)
        mapped_count = 0
        for enhanced_name, legacy_name in self.core_mappings.items():
            if enhanced_name in compatible_df.columns and legacy_name in expected_features:
                compatible_df = compatible_df.rename(columns={enhanced_name: legacy_name})
                mapped_count += 1
        
        self.logger.info(f"   ✅ Applied {mapped_count} core mappings")
        
        # Step 2: Handle special conversions (birth_date → age)
        if 'birth_date' in compatible_df.columns and 'age' in expected_features:
            compatible_df['age'] = self._convert_birth_date_to_age(compatible_df['birth_date'])
            compatible_df = compatible_df.drop(columns=['birth_date'])
            self.logger.info(f"   ✅ Converted birth_date to age")
        
        # Step 3: Create synthetic features
        synthetic_count = 0
        for feature_name, creation_func in self.synthetic_features.items():
            if feature_name in expected_features and feature_name not in compatible_df.columns:
                try:
                    compatible_df[feature_name] = creation_func(compatible_df, position)
                    synthetic_count += 1
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Could not create {feature_name}: {e}")
                    compatible_df[feature_name] = self.fallback_values.get(feature_name, 0.0)
        
        self.logger.info(f"   ✅ Created {synthetic_count} synthetic features")
        
        # Step 4: Add missing features with fallback values
        missing_features = set(expected_features) - set(compatible_df.columns)
        for feature in missing_features:
            compatible_df[feature] = self.fallback_values.get(feature, 0.0)
        
        self.logger.info(f"   ✅ Added {len(missing_features)} missing features with fallbacks")
        
        # Step 5: Select only expected features in correct order
        final_features = [f for f in expected_features if f in compatible_df.columns]
        result_df = compatible_df[final_features].copy()
        
        # Step 6: Clean data types and handle nulls
        result_df = result_df.fillna(0).astype(float)
        
        self.logger.info(f"   📊 Final compatible features: {len(result_df.columns)}")
        self.logger.info(f"   🎯 Compatibility achieved: {len(final_features)}/{len(expected_features)} features")
        
        return result_df
    
    # Synthetic feature creation methods
    def _convert_birth_date_to_age(self, birth_date_series: pd.Series) -> pd.Series:
        """Convert birth_date to age."""
        try:
            current_year = 2025  # Prediction year
            birth_dates = pd.to_datetime(birth_date_series, errors='coerce')
            ages = current_year - birth_dates.dt.year
            return ages.fillna(25)  # Default age for missing birth dates
        except:
            return pd.Series([25] * len(birth_date_series), index=birth_date_series.index)
    
    def _calculate_air_yards_dominance(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Calculate air yards dominance from available air yards data."""
        if 'air_yards_share' in df.columns:
            return df['air_yards_share'].fillna(0.1)
        elif 'receiving_air_yards' in df.columns and 'targets' in df.columns:
            return (df['receiving_air_yards'] / (df['targets'] + 1)).fillna(0.1)
        else:
            return pd.Series([0.1] * len(df), index=df.index)
    
    def _calculate_air_yards_efficiency(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Calculate air yards efficiency."""
        if 'receiving_air_yards' in df.columns and 'receiving_yards' in df.columns:
            efficiency = df['receiving_yards'] / (df['receiving_air_yards'] + 1)
            return efficiency.fillna(1.0)
        else:
            return pd.Series([1.0] * len(df), index=df.index)
    
    def _calculate_avg_snap_share(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Calculate average snap share."""
        if 'avg_offense_snap_pct' in df.columns:
            return (df['avg_offense_snap_pct'] / 100).fillna(0.5)
        elif 'total_offense_snaps' in df.columns and 'games' in df.columns:
            snaps_per_game = df['total_offense_snaps'] / df['games'].clip(1, 17)
            # Estimate snap share (assuming ~65 snaps per game average)
            return (snaps_per_game / 65).clip(0, 1).fillna(0.5)
        else:
            # Position-specific defaults
            defaults = {'QB': 0.9, 'RB': 0.4, 'WR': 0.6, 'TE': 0.5}
            return pd.Series([defaults.get(position, 0.5)] * len(df), index=df.index)
    
    def _calculate_fantasy_points_per_snap(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Calculate fantasy points per snap."""
        if 'fantasy_points_ppr' in df.columns and 'total_offense_snaps' in df.columns:
            points_per_snap = df['fantasy_points_ppr'] / (df['total_offense_snaps'] + 1)
            return points_per_snap.fillna(0.1)
        else:
            # Position-specific defaults based on efficiency
            defaults = {'QB': 0.2, 'RB': 0.15, 'WR': 0.12, 'TE': 0.1}
            return pd.Series([defaults.get(position, 0.1)] * len(df), index=df.index)
    
    def _calculate_contested_catch_rate(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Estimate contested catch rate."""
        # Use catch rate as proxy if available
        if 'receptions' in df.columns and 'targets' in df.columns:
            catch_rate = df['receptions'] / (df['targets'] + 1)
            # Contested catches are typically 60-70% of overall catch rate
            return (catch_rate * 0.65).fillna(0.6)
        else:
            return pd.Series([0.6] * len(df), index=df.index)
    
    def _calculate_deep_target_indicator(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Calculate deep target indicator."""
        if 'adot' in df.columns:
            # Players with aDOT > 12 yards get deep target indicator
            return (df['adot'] > 12).astype(float)
        else:
            return pd.Series([0.0] * len(df), index=df.index)
    
    def _calculate_deep_target_rate(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Calculate deep target rate."""
        if 'adot' in df.columns:
            # Normalize aDOT to 0-1 scale for deep target rate
            normalized_adot = (df['adot'] / 20).clip(0, 1)
            return normalized_adot.fillna(0.1)
        else:
            return pd.Series([0.1] * len(df), index=df.index)
    
    def _calculate_early_down_rate(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Estimate early down usage rate."""
        # Use carries/targets as proxy for early down involvement
        if position == 'RB' and 'carries' in df.columns:
            # RBs with more carries likely used on early downs more
            normalized_carries = (df['carries'] / df['carries'].max()).fillna(0.6)
            return normalized_carries
        else:
            return pd.Series([0.6] * len(df), index=df.index)
    
    def _calculate_carries_per_snap(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Calculate carries per snap for RBs."""
        if position == 'RB' and 'carries' in df.columns and 'total_offense_snaps' in df.columns:
            carries_per_snap = df['carries'] / (df['total_offense_snaps'] + 1)
            return carries_per_snap.fillna(0.0)
        else:
            return pd.Series([0.0] * len(df), index=df.index)
    
    def _calculate_blocking_snap_estimate(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Estimate blocking snap involvement."""
        if position in ['RB', 'TE']:
            # Use snap share as proxy - higher snap players likely block more
            if 'avg_offense_snap_pct' in df.columns:
                blocking_rate = (df['avg_offense_snap_pct'] / 100) * 0.2  # 20% of snaps
                return blocking_rate.fillna(0.1)
        return pd.Series([0.1] * len(df), index=df.index)
    
    def _calculate_target_quality(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Calculate target quality score."""
        if 'receiving_yards' in df.columns and 'targets' in df.columns:
            yards_per_target = df['receiving_yards'] / (df['targets'] + 1)
            # Normalize to reasonable range
            return (yards_per_target / 10).clip(0.5, 2.0).fillna(1.0)
        else:
            return pd.Series([1.0] * len(df), index=df.index)
    
    def _calculate_usage_sustainability(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Calculate usage sustainability score."""
        if 'games' in df.columns:
            # Players who played more games have more sustainable usage
            games_played = df['games'].clip(1, 17)
            sustainability = games_played / 17
            return sustainability.fillna(0.5)
        else:
            return pd.Series([0.5] * len(df), index=df.index)
    
    def _calculate_snap_share_tier(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Calculate snap share tier."""
        return self._calculate_avg_snap_share(df, position)
    
    def _calculate_player_tier(self, df: pd.DataFrame, position: str) -> pd.Series:
        """Calculate overall player tier."""
        if 'fantasy_points_ppr' in df.columns:
            # Normalize fantasy points to 0-1 scale
            max_points = df['fantasy_points_ppr'].max()
            if max_points > 0:
                tier = df['fantasy_points_ppr'] / max_points
                return tier.fillna(0.5)
        return pd.Series([0.5] * len(df), index=df.index)


def create_model_compatible_features(
    df: pd.DataFrame, 
    expected_features: List[str], 
    position: str
) -> pd.DataFrame:
    """
    Main function to create model-compatible features.
    
    Args:
        df: DataFrame with enhanced features
        expected_features: Features expected by the model
        position: Player position
    
    Returns:
        DataFrame with compatible features
    """
    mapper = FeatureCompatibilityMapper()
    return mapper.create_compatible_features(df, expected_features, position)