"""
Feature engineering module for the Fantasy Football AI Draft Tool.

This module contains functions to generate features for predicting player performance
in the upcoming season based on historical data, as described in Section 3.3 of the project plan.

Enhanced with Phase 2 Matchup Intelligence:
- Schedule strength analysis and opponent quality assessment
- Environmental factors (weather, altitude, dome effects)
- Situational adjustments and venue considerations
- Position-specific matchup features and contextual factors

The module supports both traditional feature engineering and enhanced matchup-aware
feature generation through configurable parameters.
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Service Communication
import requests
from typing import Any

# Service URLs for microservices communication
CONFIG_SERVICE_URL = "http://configuration:8000"
DATA_INGESTION_URL = "http://data-ingestion:8000"

def get_config() -> Dict[str, Any]:
    """Get configuration from Configuration Service"""
    try:
        response = requests.get(f"{CONFIG_SERVICE_URL}/api/v1/config/data", timeout=10)
        if response.status_code == 200:
            return response.json().get("data", {})
        else:
            logger.error(f"Failed to get config: {response.status_code}")
            raise Exception(f"Configuration service error: {response.status_code}")
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        # Return default config as fallback - but log the error prominently
        logger.error("USING DEFAULT CONFIG DUE TO SERVICE COMMUNICATION FAILURE")
        return {
            "data_start_year": 2020,
            "data_end_year": 2025,
            "core_positions": ['QB', 'RB', 'WR', 'TE']
        }

def load_raw_data(season_or_path) -> pd.DataFrame:
    """Load raw data - handles both season years and file paths"""
    try:
        # If integer passed, construct file path from season
        if isinstance(season_or_path, int):
            services_root = Path(__file__).parent.parent.parent.parent.parent
            file_path = services_root / "data" / "raw" / f"player_season_{season_or_path}.parquet"
        else:
            file_path = Path(season_or_path)
            
        if not file_path.exists():
            raise FileNotFoundError(f"Raw data file not found: {file_path}")
        return pd.read_parquet(file_path)
    except Exception as e:
        logger.error(f"Failed to load raw data from {season_or_path}: {e}")
        raise

def save_features_data(df: pd.DataFrame, file_path: str) -> None:
    """Save features data to parquet file"""
    try:
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(file_path, index=False)
        logger.info(f"Saved features data to {file_path}: {len(df)} records, {len(df.columns)} features")
    except Exception as e:
        logger.error(f"Failed to save features data to {file_path}: {e}")
        raise

class DataQualityError(Exception):
    """Custom exception for data quality issues"""
    pass

class MockValidator:
    """Mock validator for now - will implement proper validation later"""
    def validate_features(self, df: pd.DataFrame) -> bool:
        if df.empty:
            raise DataQualityError("Empty DataFrame provided")
        if df.isnull().all().any():
            raise DataQualityError("Found columns with all null values")
        return True
    
    def validate_raw_data(self, df: pd.DataFrame, season: int) -> bool:
        """Validate raw data quality"""
        if df.empty:
            raise DataQualityError(f"Empty raw data for season {season}")
        logger.info(f"Raw data validation passed for season {season}: {len(df)} records")
        return True
    
    def validate_feature_engineered_data(self, df: pd.DataFrame, season: int, **kwargs) -> bool:
        """Validate feature engineered data quality"""
        if df.empty:
            raise DataQualityError(f"Empty feature engineered data for season {season}")
        logger.info(f"Feature engineered data validation passed for season {season}: {len(df)} records")
        return True
    
    def log_data_quality_summary(self, df: pd.DataFrame, context: str) -> None:
        """Log data quality summary"""
        logger.info(f"Data Quality Summary - {context}: {len(df)} records, {len(df.columns)} features")

validator = MockValidator()

# Configure logging
logger = logging.getLogger(__name__)


def combine_position_features_safely(position_dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Safely combine position-specific feature DataFrames without cross-contamination.
    
    This function ensures that position-specific features don't leak across positions
    by properly handling column mismatches and filling missing values appropriately.
    
    Args:
        position_dfs: List of DataFrames, each containing features for a specific position
        
    Returns:
        Combined DataFrame with all positions and properly isolated features
    """
    logger.info("🔄 POSITION-AWARE FEATURE COMBINATION START")
    logger.info("=" * 70)
    
    if not position_dfs:
        logger.warning("No position DataFrames to combine")
        return pd.DataFrame()
    
    # Log input data
    total_players = sum(len(df) for df in position_dfs)
    logger.info(f"Combining {len(position_dfs)} position DataFrames with {total_players} total players")
    
    for i, df in enumerate(position_dfs):
        if 'position' in df.columns:
            positions = df['position'].unique()
            logger.info(f"  DataFrame {i+1}: {len(df)} players, {len(df.columns)} features, positions: {positions}")
        else:
            logger.info(f"  DataFrame {i+1}: {len(df)} players, {len(df.columns)} features, no position column")
    
    # Get all unique columns across all position DataFrames
    all_columns = set()
    for df in position_dfs:
        all_columns.update(df.columns)
    
    all_columns = sorted(all_columns)  # Sort for consistent ordering
    logger.info(f"📊 Total unique columns across all positions: {len(all_columns)}")
    
    # Identify position-specific feature categories
    position_specific_features = identify_position_specific_features(all_columns)
    logger.info(f"📋 Position-specific feature categories:")
    for category, features in position_specific_features.items():
        logger.info(f"   {category}: {len(features)} features")
        if len(features) <= 5:  # Show all if 5 or fewer
            logger.info(f"      {features}")
        else:  # Show first 3 for longer lists
            logger.info(f"      {features[:3]}... (+{len(features)-3} more)")
    
    # Normalize each DataFrame to have all columns
    normalized_dfs = []
    
    for i, df in enumerate(position_dfs):
        logger.info(f"🔧 Normalizing DataFrame {i+1}...")
        
        # Get the position(s) in this DataFrame
        positions_in_df = df['position'].unique() if 'position' in df.columns else ['Unknown']
        logger.info(f"   Processing positions: {positions_in_df}")
        
        # Create a copy with all columns
        normalized_df = df.copy()
        
        # Add missing columns with appropriate default values
        missing_columns = set(all_columns) - set(df.columns)
        if missing_columns:
            logger.info(f"   Adding {len(missing_columns)} missing columns...")
            
            for col in missing_columns:
                # Determine appropriate default value based on column type and position relevance
                default_value = get_default_value_for_column(col, positions_in_df, position_specific_features)
                normalized_df[col] = default_value
                
        # Ensure column order is consistent
        normalized_df = normalized_df[all_columns]
        normalized_dfs.append(normalized_df)
        
        logger.info(f"   ✅ Normalized to {len(normalized_df.columns)} columns")
    
    # Now safely concatenate the normalized DataFrames
    logger.info("🔗 Concatenating normalized DataFrames...")
    combined_df = pd.concat(normalized_dfs, ignore_index=True)
    
    # Clean up any remaining null values that shouldn't be there
    logger.info("🧹 Cleaning up null values in position-specific features...")
    initial_nulls = combined_df.isnull().sum().sum()
    
    # Fill remaining nulls with appropriate defaults based on column types
    for col in combined_df.columns:
        if combined_df[col].isnull().any():
            if pd.api.types.is_numeric_dtype(combined_df[col]):
                # Special handling for environmental impact features
                if 'env_impact' in col.lower():
                    # Fill with neutral environmental impact
                    combined_df[col] = combined_df[col].fillna(1.0)
                    logger.info(f"      Filled environmental feature '{col}' with neutral value 1.0")
                else:
                    combined_df[col] = combined_df[col].fillna(0.0)
            else:
                combined_df[col] = combined_df[col].fillna('Unknown')
    
    final_nulls = combined_df.isnull().sum().sum()
    logger.info(f"   Null values: {initial_nulls} → {final_nulls} (cleaned {initial_nulls - final_nulls})")
    
    # Validate the result
    logger.info("✅ POSITION-AWARE COMBINATION COMPLETE")
    logger.info(f"   Final DataFrame: {len(combined_df)} players, {len(combined_df.columns)} features")
    
    if 'position' in combined_df.columns:
        final_position_counts = dict(combined_df['position'].value_counts())
        logger.info(f"   Final position breakdown: {final_position_counts}")
        
        # Verify no players were lost
        input_position_counts = {}
        for df in position_dfs:
            if 'position' in df.columns:
                for pos, count in df['position'].value_counts().items():
                    input_position_counts[pos] = input_position_counts.get(pos, 0) + count
        
        for pos, expected_count in input_position_counts.items():
            actual_count = final_position_counts.get(pos, 0)
            if actual_count != expected_count:
                logger.error(f"❌ PLAYER LOSS DETECTED: {pos} had {expected_count} players, now has {actual_count}")
            else:
                logger.info(f"   ✅ {pos}: {actual_count} players (no loss)")
    
    # Clean feature contamination before checking
    combined_df = clean_position_contamination(combined_df, position_specific_features)
    
    # Log feature contamination check
    check_feature_contamination(combined_df, position_specific_features)
    
    logger.info("=" * 70)
    return combined_df


def identify_position_specific_features(all_columns: List[str]) -> Dict[str, List[str]]:
    """
    Identify which features are specific to which positions based on naming patterns.
    
    Args:
        all_columns: List of all column names
        
    Returns:
        Dictionary mapping feature categories to lists of column names
    """
    position_features = {
        'QB_specific': [],
        'RB_specific': [],
        'WR_specific': [],
        'TE_specific': [],
        'skill_position_common': [],  # RB, WR, TE common features
        'universal': []  # Features relevant to all positions
    }
    
    # QB-specific patterns (truly QB-only features)
    qb_patterns = [
        'passing_', 'completion_', 'interception_', 'sack', 'quarterback_',
        'qb_', 'air_yards_per_attempt', 'passer_rating', 'passing_td_percentage',
        'dropback', 'pocket_time', 'qb_rating', 'qb_efficiency'
    ]
    
    # RB-specific patterns (truly RB-only features - exclude basic rushing which QBs can have)
    rb_patterns = [
        'workhorse_', 'rb_', 'early_down_rate', 'passing_down_rate', 'rb_age_factor',
        'committee_back', 'goal_line_back', 'third_down_back', 'pass_catching_back',
        'rb_role', 'rb_workload', 'handoff_', 'between_tackles'
    ]
    
    # WR-specific patterns
    wr_patterns = [
        'deep_target', 'contested_catch', 'wr_', 'separation_', 'route_running'
    ]
    
    # TE-specific patterns
    te_patterns = [
        'seam_route', 'inline_usage', 'slot_usage', 'blocking_snap', 'te_', 'versatility_score'
    ]
    
    # Skill position common (RB, WR, TE)
    skill_patterns = [
        'target', 'reception', 'receiving_', 'yards_per_reception', 'yards_per_target',
        'catch_rate', 'red_zone_target', 'air_yards', 'yac', 'wopr', 'adot'
    ]
    
    # Universal patterns (relevant to all positions)
    universal_patterns = [
        'player_', 'season', 'team', 'position', 'games', 'fantasy_points',
        'age', 'experience', 'draft', 'height', 'weight', 'college',
        'next_', 'sos_', 'schedule', 'dome', 'altitude', 'weather', 'matchup',
        # Basic rushing stats that both QBs and RBs can have
        'rushing_', 'carry', 'carries', 'yards_per_carry', 'rushing_attempts',
        'rushing_yards', 'rushing_touchdowns', 'rushing_tds'
    ]
    
    for col in all_columns:
        col_lower = col.lower()
        
        # Check each category
        if any(pattern in col_lower for pattern in qb_patterns):
            position_features['QB_specific'].append(col)
        elif any(pattern in col_lower for pattern in rb_patterns):
            position_features['RB_specific'].append(col)
        elif any(pattern in col_lower for pattern in wr_patterns):
            position_features['WR_specific'].append(col)
        elif any(pattern in col_lower for pattern in te_patterns):
            position_features['TE_specific'].append(col)
        elif any(pattern in col_lower for pattern in skill_patterns):
            position_features['skill_position_common'].append(col)
        elif any(pattern in col_lower for pattern in universal_patterns):
            position_features['universal'].append(col)
        else:
            # Default to universal if we can't categorize
            position_features['universal'].append(col)
    
    return position_features


def get_default_value_for_column(col: str, positions: List[str], position_features: Dict[str, List[str]]) -> Union[float, int, str]:
    """
    Get appropriate default value for a missing column based on position relevance.
    
    Args:
        col: Column name
        positions: List of positions this DataFrame contains
        position_features: Dictionary of position-specific feature categories
        
    Returns:
        Appropriate default value for the column
    """
    col_lower = col.lower()
    
    # For position-specific features that don't apply to current positions, use 0
    if col in position_features['QB_specific'] and not any(pos == 'QB' for pos in positions):
        return 0.0
    elif col in position_features['RB_specific'] and not any(pos == 'RB' for pos in positions):
        return 0.0
    elif col in position_features['WR_specific'] and not any(pos == 'WR' for pos in positions):
        return 0.0
    elif col in position_features['TE_specific'] and not any(pos == 'TE' for pos in positions):
        return 0.0
    
    # For skill position features, use 0 if QB
    elif col in position_features['skill_position_common'] and positions == ['QB']:
        return 0.0
    
    # String columns
    elif any(pattern in col_lower for pattern in ['name', 'team', 'position', 'college', 'role']):
        return 'Unknown'
    
    # Percentage/rate columns (0-100 range)
    elif any(pattern in col_lower for pattern in ['percentage', 'rate', '_pct', 'share']):
        return 0.0
    
    # Binary indicator columns
    elif any(pattern in col_lower for pattern in ['indicator', '_flag', 'is_']):
        return 0
    
    # Default to 0.0 for numeric columns
    else:
        return 0.0


def clean_position_contamination(df: pd.DataFrame, position_features: Dict[str, List[str]]) -> pd.DataFrame:
    """
    Clean position-specific feature contamination by setting irrelevant features to 0.
    
    This ensures that:
    - RBs don't have QB passing stats
    - QBs don't have RB-specific features
    - etc.
    
    Args:
        df: Combined DataFrame to clean
        position_features: Dictionary of position-specific feature categories
        
    Returns:
        Cleaned DataFrame
    """
    logger.info("🧹 CLEANING POSITION-SPECIFIC FEATURE CONTAMINATION")
    
    if 'position' not in df.columns:
        logger.warning("Cannot clean contamination - no position column")
        return df
    
    df_clean = df.copy()
    total_cleaned = 0
    
    for position in df_clean['position'].unique():
        # Get mask for this position
        pos_mask = df_clean['position'] == position
        
        # Determine which features should be zero for this position
        if position == 'QB':
            # QBs shouldn't have RB/WR/TE specific features
            features_to_zero = (position_features.get('RB_specific', []) + 
                              position_features.get('WR_specific', []) + 
                              position_features.get('TE_specific', []))
        elif position == 'RB':
            # RBs shouldn't have QB specific features  
            qb_features = position_features.get('QB_specific', [])
            # Zero out all QB-specific features for RBs
            features_to_zero = qb_features
        elif position == 'WR':
            # WRs shouldn't have QB-specific or RB-specific features
            qb_features = position_features.get('QB_specific', [])
            rb_features = position_features.get('RB_specific', [])
            # Zero out all QB and RB specific features for WRs
            features_to_zero = qb_features + rb_features + position_features.get('TE_specific', [])
        elif position == 'TE':
            # TEs shouldn't have QB/RB/WR specific features
            qb_features = position_features.get('QB_specific', [])
            # Zero out all QB, RB, and WR specific features for TEs
            features_to_zero = (qb_features + 
                              position_features.get('RB_specific', []) + 
                              position_features.get('WR_specific', []))
        else:
            continue
        
        # Zero out irrelevant features for this position
        for feature in features_to_zero:
            if feature in df_clean.columns:
                # Count non-zero values before cleaning
                non_zero_before = (df_clean.loc[pos_mask, feature] != 0).sum()
                if non_zero_before > 0:
                    df_clean.loc[pos_mask, feature] = 0.0
                    total_cleaned += non_zero_before
                    logger.debug(f"   Cleaned {non_zero_before} non-zero values in '{feature}' for {position}")
    
    logger.info(f"✅ Cleaned {total_cleaned} total contaminated values across all positions")
    return df_clean


def check_feature_contamination(df: pd.DataFrame, position_features: Dict[str, List[str]]) -> None:
    """
    Check for feature contamination across positions and log warnings.
    
    Args:
        df: Combined DataFrame to check
        position_features: Dictionary of position-specific feature categories
    """
    logger.info("🔍 FEATURE CONTAMINATION CHECK")
    
    if 'position' not in df.columns:
        logger.warning("Cannot check contamination - no position column")
        return
    
    contamination_found = False
    
    for position in df['position'].unique():
        pos_data = df[df['position'] == position]
        
        # Check for non-zero values in irrelevant position-specific features
        if position == 'QB':
            # QBs shouldn't have non-zero RB/WR/TE specific features
            irrelevant_features = (position_features['RB_specific'] + 
                                 position_features['WR_specific'] + 
                                 position_features['TE_specific'])
        elif position == 'RB':
            # RBs shouldn't have non-zero QB specific features
            irrelevant_features = position_features['QB_specific']
        elif position == 'WR':
            # WRs shouldn't have non-zero QB/RB/TE specific features  
            irrelevant_features = (position_features['QB_specific'] + 
                                 position_features['RB_specific'] + 
                                 position_features['TE_specific'])
        elif position == 'TE':
            # TEs shouldn't have non-zero QB/RB/WR specific features
            irrelevant_features = (position_features['QB_specific'] + 
                                 position_features['RB_specific'] + 
                                 position_features['WR_specific'])
        else:
            continue
        
        # Check for contamination
        contaminated_features = []
        for feature in irrelevant_features:
            if feature in pos_data.columns:
                non_zero_count = (pos_data[feature] != 0).sum()
                if non_zero_count > 0:
                    contaminated_features.append(f"{feature}({non_zero_count} non-zero)")
        
        if contaminated_features:
            contamination_found = True
            logger.warning(f"⚠️ CONTAMINATION in {position}: {len(contaminated_features)} features have non-zero values")
            if len(contaminated_features) <= 3:
                logger.warning(f"   Contaminated features: {contaminated_features}")
            else:
                logger.warning(f"   First 3 contaminated: {contaminated_features[:3]}... (+{len(contaminated_features)-3} more)")
        else:
            logger.info(f"   ✅ {position}: No contamination detected")
    
    if not contamination_found:
        logger.info("🎉 No feature contamination detected across any positions!")
    else:
        logger.warning("❌ Feature contamination detected - review position-specific feature logic")

# Import opportunity metrics and usage analytics (now local)
try:
    from ..advanced_features.opportunity_metrics import OpportunityMetricsCalculator
    from ..advanced_features.usage_analytics import UsageAnalyticsCalculator
    OPPORTUNITY_METRICS_AVAILABLE = True
    logger.info("Opportunity metrics components loaded successfully")
except ImportError as e:
    OPPORTUNITY_METRICS_AVAILABLE = False
    logger.error(f"CRITICAL: Opportunity metrics components not available: {e}")
    logger.error(f"This indicates a critical service structure issue")

# Import position-specific feature engineering (now local)
try:
    from ..position_features.qb_features import engineer_qb_features
    from ..position_features.rb_features import engineer_rb_features
    from ..position_features.wr_features import engineer_wr_features  
    from ..position_features.te_features import engineer_te_features
    POSITION_SPECIFIC_FEATURES_AVAILABLE = True
    logger.info("Position-specific feature engineering loaded successfully")
except ImportError as e:
    POSITION_SPECIFIC_FEATURES_AVAILABLE = False
    logger.error(f"CRITICAL: Position-specific feature engineering not available: {e}")
    logger.error(f"This indicates a critical service structure issue")

# Import matchup intelligence components (Phase 2 enhancements) - now local
try:
    from ..advanced_features.matchup_feature_integrator import (
        MatchupFeatureIntegrator, MatchupFeatureConfig
    )
    MATCHUP_INTELLIGENCE_AVAILABLE = True
    logger.info("Matchup intelligence components loaded successfully")
except ImportError as e:
    MATCHUP_INTELLIGENCE_AVAILABLE = False
    logger.error(f"CRITICAL: Matchup intelligence components not available: {e}")
    logger.error("This indicates a critical service structure issue")


# This function is deprecated, use load_cleaned_data directly
def load_cleaned_season_data(year):
    """
    Load cleaned player statistics for a specific season.
    
    Args:
        year (int): The NFL season year to load data for
    
    Returns:
        pandas.DataFrame: DataFrame containing cleaned player statistics for the specified season
    """
    return load_cleaned_data(year)


def calculate_age(birth_date, reference_date):
    """
    Calculate age as of a reference date.
    
    Args:
        birth_date (datetime): Player's birth date
        reference_date (datetime): Reference date to calculate age against
    
    Returns:
        float: Age in years, or np.nan if birth_date is missing
    """
    if pd.isna(birth_date):
        return np.nan
    
    try:
        # Calculate age in years
        age = reference_date.year - birth_date.year
        
        # Adjust age if birthday hasn't occurred yet in the reference year
        if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
            age -= 1
            
        return age
    except Exception as e:
        logger.warning(f"Error calculating age: {str(e)}")
        return np.nan


def calculate_experience(player_id, current_season, historical_data):
    """
    Calculate years of experience for a player prior to the current season.
    
    Args:
        player_id (str): Player's unique identifier
        current_season (int): The season for which to calculate experience
        historical_data (dict): Dictionary mapping season years to DataFrames with player data
    
    Returns:
        int: Years of experience (0 for rookies)
    """
    # Count seasons where the player appears in the data
    seasons_played = 0
    
    for season, df in historical_data.items():
        if season < current_season and 'player_id' in df.columns and player_id in df['player_id'].values:
            seasons_played += 1
    
    return seasons_played


def calculate_per_game_stats(df):
    """
    Calculate per-game averages for key statistics.
    
    Args:
        df (pandas.DataFrame): DataFrame containing player statistics
    
    Returns:
        pandas.DataFrame: DataFrame with added per-game statistics
    """
    logger.info("Calculating per-game statistics")
    
    # Make a copy to avoid modifying the original DataFrame
    df_features = df.copy()
    
    # Ensure games column exists and is greater than 0 to avoid division by zero
    if 'games' not in df_features.columns:
        logger.warning("'games' column not found, cannot calculate per-game stats")
        return df_features
    
    # Replace 0 games with 1 to avoid division by zero
    games_played = df_features['games'].copy()
    games_played = games_played.replace(0, 1)
    
    # Calculate per-game stats for QB
    qb_per_game_cols = {
        'attempts': 'attempts_per_game',
        'completions': 'completions_per_game',
        'passing_yards': 'passing_yards_per_game',
        'passing_tds': 'passing_tds_per_game',
        'interceptions': 'interceptions_per_game',
        'carries': 'carries_per_game',
        'rushing_yards': 'rushing_yards_per_game',
        'rushing_tds': 'rushing_tds_per_game',
        'fantasy_points': 'fantasy_points_per_game',
        'fantasy_points_ppr': 'fantasy_points_ppr_per_game'
    }
    
    # Calculate per-game stats for RB
    rb_per_game_cols = {
        'carries': 'carries_per_game',
        'rushing_yards': 'rushing_yards_per_game',
        'rushing_tds': 'rushing_tds_per_game',
        'targets': 'targets_per_game',
        'receptions': 'receptions_per_game',
        'receiving_yards': 'receiving_yards_per_game',
        'receiving_tds': 'receiving_tds_per_game',
        'fantasy_points': 'fantasy_points_per_game',
        'fantasy_points_ppr': 'fantasy_points_ppr_per_game'
    }
    
    # Calculate per-game stats for WR/TE
    rec_per_game_cols = {
        'targets': 'targets_per_game',
        'receptions': 'receptions_per_game',
        'receiving_yards': 'receiving_yards_per_game',
        'receiving_tds': 'receiving_tds_per_game',
        'fantasy_points': 'fantasy_points_per_game',
        'fantasy_points_ppr': 'fantasy_points_ppr_per_game'
    }
    
    # Apply calculations based on position
    for position, cols_dict in [('QB', qb_per_game_cols), ('RB', rb_per_game_cols), 
                               ('WR', rec_per_game_cols), ('TE', rec_per_game_cols)]:
        pos_mask = df_features['position'] == position
        
        for col, new_col in cols_dict.items():
            if col in df_features.columns:
                # Only calculate for players of this position
                df_features.loc[pos_mask, new_col] = df_features.loc[pos_mask, col] / games_played[pos_mask]
    
    return df_features


def calculate_efficiency_metrics(df):
    """
    Calculate efficiency metrics such as yards per attempt, catch rate, etc.
    
    Args:
        df (pandas.DataFrame): DataFrame containing player statistics
    
    Returns:
        pandas.DataFrame: DataFrame with added efficiency metrics
    """
    logger.info("Calculating efficiency metrics")
    
    # Make a copy to avoid modifying the original DataFrame
    df_features = df.copy()
    
    # QB efficiency metrics
    if 'attempts' in df_features.columns and 'passing_yards' in df_features.columns:
        # Yards per attempt (passing)
        mask = (df_features['position'] == 'QB') & (df_features['attempts'] > 0)
        df_features.loc[mask, 'yards_per_attempt'] = df_features.loc[mask, 'passing_yards'] / df_features.loc[mask, 'attempts']
        
        # Completion percentage
        mask = (df_features['position'] == 'QB') & (df_features['attempts'] > 0)
        df_features.loc[mask, 'completion_percentage'] = (df_features.loc[mask, 'completions'] / df_features.loc[mask, 'attempts']) * 100
        
        # Touchdown percentage (passing)
        mask = (df_features['position'] == 'QB') & (df_features['attempts'] > 0)
        df_features.loc[mask, 'passing_td_percentage'] = (df_features.loc[mask, 'passing_tds'] / df_features.loc[mask, 'attempts']) * 100
        
        # Interception percentage
        mask = (df_features['position'] == 'QB') & (df_features['attempts'] > 0)
        df_features.loc[mask, 'interception_percentage'] = (df_features.loc[mask, 'interceptions'] / df_features.loc[mask, 'attempts']) * 100
    
    # RB efficiency metrics
    if 'carries' in df_features.columns and 'rushing_yards' in df_features.columns:
        # Yards per carry
        mask = (df_features['position'] == 'RB') & (df_features['carries'] > 0)
        df_features.loc[mask, 'yards_per_carry'] = df_features.loc[mask, 'rushing_yards'] / df_features.loc[mask, 'carries']
        
        # Rushing TD rate
        mask = (df_features['position'] == 'RB') & (df_features['carries'] > 0)
        df_features.loc[mask, 'rushing_td_rate'] = (df_features.loc[mask, 'rushing_tds'] / df_features.loc[mask, 'carries']) * 100
    
    # Receiving efficiency metrics (for RB, WR, TE)
    if 'targets' in df_features.columns and 'receptions' in df_features.columns:
        # Catch rate
        mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['targets'] > 0)
        df_features.loc[mask, 'catch_rate'] = (df_features.loc[mask, 'receptions'] / df_features.loc[mask, 'targets']) * 100
    
    if 'receptions' in df_features.columns and 'receiving_yards' in df_features.columns:
        # Yards per reception
        mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['receptions'] > 0)
        df_features.loc[mask, 'yards_per_reception'] = df_features.loc[mask, 'receiving_yards'] / df_features.loc[mask, 'receptions']
    
    if 'targets' in df_features.columns and 'receiving_yards' in df_features.columns:
        # Yards per target
        mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['targets'] > 0)
        df_features.loc[mask, 'yards_per_target'] = df_features.loc[mask, 'receiving_yards'] / df_features.loc[mask, 'targets']
    
    if 'receptions' in df_features.columns and 'receiving_tds' in df_features.columns:
        # Receiving TD rate (per reception)
        mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['receptions'] > 0)
        df_features.loc[mask, 'receiving_td_per_reception'] = (df_features.loc[mask, 'receiving_tds'] / df_features.loc[mask, 'receptions']) * 100
    
    if 'targets' in df_features.columns and 'receiving_tds' in df_features.columns:
        # Receiving TD rate (per target)
        mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['targets'] > 0)
        df_features.loc[mask, 'receiving_td_per_target'] = (df_features.loc[mask, 'receiving_tds'] / df_features.loc[mask, 'targets']) * 100
    
    # YAC per reception
    if 'receptions' in df_features.columns and 'receiving_yac_yards' in df_features.columns:
        mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['receptions'] > 0)
        df_features.loc[mask, 'yac_per_reception'] = df_features.loc[mask, 'receiving_yac_yards'] / df_features.loc[mask, 'receptions']
    
    return df_features


def calculate_team_aggregates(df):
    """
    Calculate team-level aggregates for usage metrics.
    
    Args:
        df (pandas.DataFrame): DataFrame containing player statistics
    
    Returns:
        pandas.DataFrame: DataFrame with team-level aggregates
    """
    logger.info("Calculating team-level aggregates")
    
    # Check if team column exists
    if 'team' not in df.columns:
        logger.warning("'team' column not found, cannot calculate team aggregates")
        return pd.DataFrame()
    
    # Group by team and aggregate relevant stats
    team_agg = df.groupby('team').agg({
        'attempts': 'sum',  # Total pass attempts
        'targets': 'sum',   # Total targets
        'receptions': 'sum',  # Total receptions
        'carries': 'sum',   # Total rushing attempts
        'rushing_yards': 'sum',  # Total rushing yards
        'receiving_yards': 'sum',  # Total receiving yards
        'passing_yards': 'sum',  # Total passing yards
        'rushing_tds': 'sum',  # Total rushing TDs
        'receiving_tds': 'sum',  # Total receiving TDs
        'passing_tds': 'sum'  # Total passing TDs
    }).reset_index()
    
    # Rename columns to indicate they are team totals
    team_agg.columns = ['team'] + [f'team_{col}' for col in team_agg.columns if col != 'team']
    
    return team_agg


def calculate_usage_metrics(df, team_agg):
    """
    Calculate usage metrics such as target share, reception share, etc.
    
    Args:
        df (pandas.DataFrame): DataFrame containing player statistics
        team_agg (pandas.DataFrame): DataFrame with team-level aggregates
    
    Returns:
        pandas.DataFrame: DataFrame with added usage metrics
    """
    logger.info("Calculating usage metrics")
    
    # Make a copy to avoid modifying the original DataFrame
    df_features = df.copy()
    
    # Merge player data with team aggregates
    if not team_agg.empty and 'team' in df_features.columns:
        df_features = pd.merge(df_features, team_agg, on='team', how='left')
        
        # Calculate target share
        mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['team_attempts'] > 0)
        df_features.loc[mask, 'target_share'] = df_features.loc[mask, 'targets'] / df_features.loc[mask, 'team_attempts']
        
        # Calculate reception share
        mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['team_receptions'] > 0)
        df_features.loc[mask, 'reception_share'] = df_features.loc[mask, 'receptions'] / df_features.loc[mask, 'team_receptions']
        
        # Calculate rushing attempt share (for RBs)
        mask = (df_features['position'] == 'RB') & (df_features['team_carries'] > 0)
        df_features.loc[mask, 'rushing_attempt_share'] = df_features.loc[mask, 'carries'] / df_features.loc[mask, 'team_carries']
        
        # Calculate rushing yards share (for RBs)
        mask = (df_features['position'] == 'RB') & (df_features['team_rushing_yards'] > 0)
        df_features.loc[mask, 'rushing_yards_share'] = df_features.loc[mask, 'rushing_yards'] / df_features.loc[mask, 'team_rushing_yards']
        
        # Calculate receiving yards share
        mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['team_receiving_yards'] > 0)
        df_features.loc[mask, 'receiving_yards_share'] = df_features.loc[mask, 'receiving_yards'] / df_features.loc[mask, 'team_receiving_yards']
        
        # Calculate rushing TD share (for RBs)
        mask = (df_features['position'] == 'RB') & (df_features['team_rushing_tds'] > 0)
        df_features.loc[mask, 'rushing_td_share'] = df_features.loc[mask, 'rushing_tds'] / df_features.loc[mask, 'team_rushing_tds']
        
        # Calculate receiving TD share
        mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['team_receiving_tds'] > 0)
        df_features.loc[mask, 'receiving_td_share'] = df_features.loc[mask, 'receiving_tds'] / df_features.loc[mask, 'team_receiving_tds']
    
    return df_features


def create_lagged_features(current_season_df, previous_season_df):
    """
    Create lagged features from the previous season.
    
    Args:
        current_season_df (pandas.DataFrame): DataFrame for the current season
        previous_season_df (pandas.DataFrame): DataFrame for the previous season
    
    Returns:
        pandas.DataFrame: DataFrame with lagged features added
    """
    logger.info("Creating lagged features from previous season")
    
    # Make a copy to avoid modifying the original DataFrame
    df_features = current_season_df.copy()
    
    # Extract relevant columns from previous season
    if previous_season_df is not None and not previous_season_df.empty:
        # Select columns to lag
        lag_columns = [
            'player_id', 'fantasy_points', 'fantasy_points_ppr', 'games',
            'attempts', 'completions', 'passing_yards', 'passing_tds', 'interceptions',
            'carries', 'rushing_yards', 'rushing_tds',
            'targets', 'receptions', 'receiving_yards', 'receiving_tds'
        ]
        
        # Check which columns exist in the previous season data
        available_lag_columns = [col for col in lag_columns if col in previous_season_df.columns]
        
        if len(available_lag_columns) > 1:  # At least player_id and one other column
            # Create a DataFrame with lagged features
            lagged_df = previous_season_df[available_lag_columns].copy()
            
            # Rename columns to indicate they are lagged
            rename_dict = {col: f'{col}_L1' for col in available_lag_columns if col != 'player_id'}
            lagged_df = lagged_df.rename(columns=rename_dict)
            
            # Merge with current season data
            df_features = pd.merge(df_features, lagged_df, on='player_id', how='left')
            
            # Fill missing lagged values with 0 (for players who didn't play in the previous season)
            for col in rename_dict.values():
                if col in df_features.columns:
                    df_features[col] = df_features[col].fillna(0)
        else:
            logger.warning("Not enough columns available in previous season data for lagging")
    else:
        logger.warning("No previous season data available for lagging")
    
    return df_features


def handle_rookies(df, prediction_season, historical_data):
    """
    Handle rookies by identifying them and applying appropriate projections.
    
    Args:
        df (pandas.DataFrame): DataFrame with player data
        prediction_season (int): The season being predicted
        historical_data (dict): Dictionary mapping season years to DataFrames with player data
    
    Returns:
        pandas.DataFrame: DataFrame with rookie handling applied
    """
    logger.info("Handling rookies for prediction")
    
    # Get config for this function
    config = get_config()
    
    # Make a copy to avoid modifying the original DataFrame
    df_features = df.copy()
    
    # Check if player_id column exists
    if 'player_id' not in df_features.columns:
        logger.warning("'player_id' column not found, cannot calculate experience")
        # Add an experience column with default value 1 (non-rookie)
        df_features['experience'] = 1
        return df_features
    
    # Calculate experience for each player
    df_features['experience'] = df_features['player_id'].apply(
        lambda pid: calculate_experience(pid, prediction_season, historical_data)
    )
    
    # Identify rookies (experience = 0)
    rookies = df_features['experience'] == 0
    logger.info(f"Identified {rookies.sum()} rookies for {prediction_season} season")
    
    # Apply rookie projections based on draft round and position
    if 'draftround' in df_features.columns:
        # For each position and draft round, apply the configured baseline FPPG
        for position in config.get('data.positions', ['QB', 'RB', 'WR', 'TE']):
            pos_mask = (df_features['position'] == position) & rookies
            
            for draft_round in range(1, 8):  # Draft rounds 1-7
                # Get the configured baseline FPPG for this position and draft round
                baseline_fppg = config.get('league.rookie_baseline_fppg', {}).get(position, {}).get(draft_round, 1.0)
                
                # Apply the baseline FPPG to rookies of this position and draft round
                round_mask = pos_mask & (df_features['draftround'] == draft_round)
                df_features.loc[round_mask, 'projected_fppg'] = baseline_fppg
            
            # Handle UDFAs (draft round > 7 or NaN)
            udfa_mask = pos_mask & ((df_features['draftround'] > 7) | df_features['draftround'].isna())
            df_features.loc[udfa_mask, 'projected_fppg'] = config.get('league.rookie_baseline_fppg', {}).get(position, {}).get('UDFA', 1.0)
    else:
        logger.warning("'draftround' column not found, cannot apply rookie projections based on draft capital")
    
    return df_features


def handle_minimal_data_players(df, min_games=4):
    """
    Handle players with minimal recent NFL data.
    
    Args:
        df (pandas.DataFrame): DataFrame with player data
        min_games (int): Minimum number of games played in previous season to be considered sufficient data
    
    Returns:
        pandas.DataFrame: DataFrame with minimal data handling applied
    """
    logger.info(f"Handling players with minimal data (less than {min_games} games)")
    
    # Get config for this function
    config = get_config()
    
    # Make a copy to avoid modifying the original DataFrame
    df_features = df.copy()
    
    # Ensure experience column exists
    if 'experience' not in df_features.columns:
        logger.warning("'experience' column not found, adding default value of 1")
        df_features['experience'] = 1
    
    # Check if we have the necessary columns for games played
    games_col = None
    if 'games_L1' in df_features.columns:
        games_col = 'games_L1'
    elif 'games' in df_features.columns:
        games_col = 'games'
        logger.warning("'games_L1' not found, using current season 'games' column instead")
    
    if games_col is not None:
        # Identify non-rookies with minimal recent data
        minimal_data_mask = (df_features['experience'] > 0) & (df_features[games_col] < min_games)
        
        # Apply baseline FPPG for minimal data players based on position
        for position in config.get('data.positions', ['QB', 'RB', 'WR', 'TE']):
            pos_mask = minimal_data_mask & (df_features['position'] == position)
            baseline_fppg = config.get('league.minimal_data_baseline_fppg', {}).get(position, 1.0)
            
            df_features.loc[pos_mask, 'projected_fppg'] = baseline_fppg
            
            logger.info(f"Applied baseline FPPG of {baseline_fppg} to {pos_mask.sum()} {position} players with minimal data")
    else:
        logger.warning("No games played column found for minimal data handling")
        # Apply baseline FPPG for all players based on position as a fallback
        for position in config.get('data.positions', ['QB', 'RB', 'WR', 'TE']):
            pos_mask = df_features['position'] == position
            baseline_fppg = config.get('league.minimal_data_baseline_fppg', {}).get(position, 1.0)
            
            # Only apply to players without a projected_fppg value
            if 'projected_fppg' in df_features.columns:
                apply_mask = pos_mask & df_features['projected_fppg'].isna()
            else:
                apply_mask = pos_mask
                df_features['projected_fppg'] = np.nan
            
            df_features.loc[apply_mask, 'projected_fppg'] = baseline_fppg
            
            logger.info(f"Applied baseline FPPG of {baseline_fppg} to {apply_mask.sum()} {position} players as fallback")
    
    return df_features


def engineer_features_for_season(
    target_season, 
    historical_seasons=None, 
    include_matchup_intelligence=False,
    include_position_specific_features=False,
    weeks_ahead_sos=4,
    inference_mode=False
):
    """
    Engineer features for a target season using data from historical seasons.
    
    Enhanced with Phase 2 Matchup Intelligence support for comprehensive
    fantasy football projections that account for opponent strength,
    environmental factors, and situational adjustments.

    Args:
        target_season (int): The season to engineer features for (predicting target_season+1)
        historical_seasons (list, optional): List of historical seasons to use. 
                                            Defaults to [target_season-1, target_season].
        include_matchup_intelligence (bool): Include Phase 2 matchup intelligence features
        include_position_specific_features (bool): Include advanced position-specific features
        weeks_ahead_sos (int): Number of weeks ahead to analyze for strength of schedule

    Returns:
        pandas.DataFrame: DataFrame with engineered features (traditional + enhanced if enabled)
    """
    # Initialize config at function start to avoid scope issues
    config = get_config()
    
    logger.info(f"🏗️ FEATURE ENGINEERING START: {target_season} → {target_season+1}")
    logger.info("=" * 80)
    logger.info(f"📊 Configuration:")
    logger.info(f"   Target season: {target_season}")
    logger.info(f"   Prediction season: {target_season+1}")
    logger.info(f"   Matchup intelligence: {include_matchup_intelligence}")
    logger.info(f"   Position-specific features: {include_position_specific_features}")
    logger.info(f"   Weeks ahead SOS: {weeks_ahead_sos}")
    
    if historical_seasons is None:
        historical_seasons = [target_season-1, target_season]
    
    logger.info(f"   Historical seasons: {historical_seasons}")
    logger.info("=" * 80)
    
    # Load data for all required seasons
    historical_data = {}
    prediction_season = target_season + 1
    next_season_actuals_df = None
    
    if inference_mode:
        # INFERENCE MODE: Preserve target season fantasy points for rankings
        logger.info(f"🎯 INFERENCE MODE: Preserving {target_season} fantasy points for draft rankings")
        next_season_actuals_df = None  # Don't try to load future data
    else:
        # TRAINING MODE: Try to load future season for prediction targets
        try:
            # Attempt to load data for the prediction_season to get actual outcomes
            next_season_actuals_df = load_raw_data(prediction_season)
            logger.info(f"Successfully loaded actuals data for {prediction_season} to create target variable.")
        except FileNotFoundError:
            logger.warning(f"Raw data for prediction season {prediction_season} not found. Target variable will be NaN.")
        except Exception as e:
            logger.error(f"Error loading data for prediction season {prediction_season}: {e}. Target variable will be NaN.")

    for season in historical_seasons:
        try:
            historical_data[season] = load_raw_data(season)
        except Exception as e:
            logger.warning(f"Could not load data for {season} season: {str(e)}")
            historical_data[season] = pd.DataFrame()
    
    # Ensure we have the target season data
    if target_season not in historical_data or historical_data[target_season].empty:
        raise DataQualityError(f"No data available for target season {target_season}")
    
    # Apply strict data quality validation at the start
    validator.validate_raw_data(historical_data[target_season], target_season)

    # Convert birth_date to datetime if it exists, before copying to df_features
    if 'birth_date' in historical_data[target_season].columns:
        historical_data[target_season]['birth_date'] = pd.to_datetime(historical_data[target_season]['birth_date'], errors='coerce')
        logger.info(f"Converted 'birth_date' column to datetime for season {target_season} in current_season_df")

    # Get the current season data
    current_season_df = historical_data[target_season]
    
    # Skip comprehensive data enhancement for now - use raw data directly
    logger.info(f"🔧 Using raw data directly for feature engineering (skipping roster enhancement)")
    
    # The current season data should already have the basic columns we need
    if 'position' not in current_season_df.columns:
        logger.error(f"❌ No position column in raw data for {target_season}")
        return pd.DataFrame()
    
    # Filter to fantasy-relevant positions
    fantasy_positions = ['QB', 'RB', 'WR', 'TE']
    current_season_df = current_season_df[current_season_df['position'].isin(fantasy_positions)]
    
    logger.info(f"✅ Raw data loaded for {target_season}")
    logger.info(f"   Data shape: {current_season_df.shape}")
    logger.info(f"   Position breakdown: {dict(current_season_df['position'].value_counts())}")
    
    # Update the historical data dict so downstream processing works
    historical_data[target_season] = current_season_df
    
    # Validate required columns for feature engineering
    required_columns = ['position', 'games', 'player_id']
    missing_columns = [col for col in required_columns if col not in current_season_df.columns]
    
    if missing_columns:
        logger.error(f"❌ FEATURE ENGINEERING FAILED: Missing required columns: {missing_columns}")
        logger.error(f"   Available columns: {list(current_season_df.columns)}")
        logger.error(f"   Data shape: {current_season_df.shape}")
        logger.error(f"   This indicates a data pipeline issue - feature engineering expects historical season data")
        return pd.DataFrame()  # Return empty dataframe to trigger fallback
    
    logger.info(f"✅ Data validation passed - required columns present: {required_columns}")
    logger.info(f"   Data shape: {current_season_df.shape}")
    logger.info(f"   Available positions: {sorted(current_season_df['position'].unique()) if 'position' in current_season_df.columns else 'MISSING'}")
    
    # Get the previous season data (if available)
    previous_season_df = historical_data.get(target_season-1, pd.DataFrame())
    
    # Step 1: Calculate per-game statistics
    df_features = calculate_per_game_stats(current_season_df)
    
    # Step 2: Calculate efficiency metrics
    df_features = calculate_efficiency_metrics(df_features)
    
    # Step 3: Calculate team aggregates
    team_agg = calculate_team_aggregates(df_features)
    
    # Step 4: Calculate usage metrics
    df_features = calculate_usage_metrics(df_features, team_agg)
    
    # Step 5: Create lagged features from previous season
    df_features = create_lagged_features(df_features, previous_season_df)
    
    # Step 6: Calculate age as of September 1st of the prediction season (target_season+1)
    if 'birth_date' in df_features.columns:
        reference_date = datetime(target_season+1, 9, 1)
        df_features['age'] = df_features['birth_date'].apply(
            lambda bd: calculate_age(bd, reference_date)
        )
    
    # Step 7: Handle rookies
    df_features = handle_rookies(df_features, target_season+1, historical_data)
    
    # Step 8: Handle players with minimal recent data
    df_features = handle_minimal_data_players(df_features)
    
    # STEP 9: Add Opportunity Metrics (Industry-Standard Features)
    logger.info("🎯 STEP 9: Adding Opportunity Metrics")
    if OPPORTUNITY_METRICS_AVAILABLE:
        try:
            # Initialize opportunity metrics calculator
            opp_calculator = OpportunityMetricsCalculator(target_season)
            
            # Apply opportunity metrics to skill positions
            skill_positions = ['RB', 'WR', 'TE']
            
            for position in skill_positions:
                pos_mask = df_features['position'] == position
                pos_count = pos_mask.sum()
                
                if pos_count > 0:
                    logger.info(f"   Adding opportunity metrics for {pos_count} {position} players")
                    pos_data = df_features[pos_mask].copy()
                    
                    # Apply opportunity metrics enhancement
                    enhanced_pos_data = opp_calculator.enhance_opportunity_metrics(pos_data)
                    
                    # Update the main dataframe
                    df_features.loc[pos_mask, enhanced_pos_data.columns] = enhanced_pos_data
                    
                    # Log key metrics added
                    opp_metrics = ['target_share', 'air_yards_share', 'wopr', 'adot', 'red_zone_opportunities']
                    added_metrics = [col for col in opp_metrics if col in enhanced_pos_data.columns]
                    logger.info(f"   ✅ Added {len(added_metrics)} opportunity metrics for {position}: {added_metrics}")
            
            logger.info("✅ Opportunity metrics integration complete")
            
        except Exception as e:
            logger.error(f"❌ Error adding opportunity metrics: {e}")
            logger.info("Continuing without opportunity metrics")
    else:
        logger.warning("⚠️ Opportunity metrics not available - skipping industry-standard calculations")
    
    # STEP 10: Add Usage Analytics 
    logger.info("📊 STEP 10: Adding Usage Analytics")
    if OPPORTUNITY_METRICS_AVAILABLE:  # Uses same import check
        try:
            # Initialize usage analytics calculator
            usage_calculator = UsageAnalyticsCalculator()
            
            # Apply usage analytics to all skill positions
            for position in skill_positions:
                pos_mask = df_features['position'] == position
                pos_count = pos_mask.sum()
                
                if pos_count > 0:
                    logger.info(f"   Adding usage analytics for {pos_count} {position} players")
                    pos_data = df_features[pos_mask].copy()
                    
                    # Apply usage analytics
                    enhanced_usage_data = usage_calculator.calculate_all_usage_metrics(pos_data)
                    
                    # Update the main dataframe
                    df_features.loc[pos_mask, enhanced_usage_data.columns] = enhanced_usage_data
                    
                    # Log key usage metrics added
                    usage_metrics = ['snap_share', 'targets_per_snap', 'route_participation', 'high_value_touches']
                    added_usage = [col for col in usage_metrics if col in enhanced_usage_data.columns]
                    logger.info(f"   ✅ Added {len(added_usage)} usage metrics for {position}: {added_usage}")
            
            logger.info("✅ Usage analytics integration complete")
            
        except Exception as e:
            logger.error(f"❌ Error adding usage analytics: {e}")
            logger.info("Continuing without usage analytics")
    else:
        logger.warning("⚠️ Usage analytics not available - skipping advanced usage calculations")
    
    # PHASE 2: Enhanced Position-Specific Features (Standalone)
    if include_position_specific_features and POSITION_SPECIFIC_FEATURES_AVAILABLE:
        logger.info("🔧 PHASE 2: Enhanced Position-Specific Features")
        
        # Apply position-specific feature engineering
        position_dfs = []
        
        for position in ['QB', 'RB', 'WR', 'TE']:
            pos_data = df_features[df_features['position'] == position].copy()
            
            if not pos_data.empty:
                logger.info(f"Applying enhanced {position} feature engineering to {len(pos_data)} players")
                
                try:
                    if position == 'QB':
                        enhanced_pos_data = engineer_qb_features(pos_data)
                    elif position == 'RB':
                        enhanced_pos_data = engineer_rb_features(pos_data)
                    elif position == 'WR':
                        enhanced_pos_data = engineer_wr_features(pos_data)
                    elif position == 'TE':
                        enhanced_pos_data = engineer_te_features(pos_data)
                    
                    position_dfs.append(enhanced_pos_data)
                    logger.info(f"Successfully enhanced {position} features: {len(enhanced_pos_data.columns)} total columns")
                    
                except Exception as e:
                    logger.warning(f"Error in {position} feature engineering: {e}")
                    position_dfs.append(pos_data)  # Use original data if enhancement fails
        
        # Combine position-specific features back together with position isolation
        if position_dfs:
            df_features = combine_position_features_safely(position_dfs)
            logger.info(f"✅ Combined position-specific features: {len(df_features)} players, {len(df_features.columns)} features")
    elif include_position_specific_features and not POSITION_SPECIFIC_FEATURES_AVAILABLE:
        logger.warning("⚠️ Position-specific features requested but not available - skipping enhanced features")
    
    # PHASE 3: Matchup Intelligence Integration (Optional)
    if include_matchup_intelligence and MATCHUP_INTELLIGENCE_AVAILABLE:
        logger.info("Phase 3: Matchup Intelligence Integration")
        
        try:
            logger.info(f"🎯 MATCHUP INTELLIGENCE INTEGRATION START")
            logger.info(f"   Season for features: {target_season}")
            logger.info(f"   Weeks ahead SOS: {weeks_ahead_sos}")
            logger.info(f"   Players to enhance: {len(df_features)}")
            
            # Validate input data for matchup intelligence
            required_cols = ['player_id', 'position', 'team']
            missing_cols = [col for col in required_cols if col not in df_features.columns]
            if missing_cols:
                logger.error(f"❌ MATCHUP INTEGRATION FAILED: Missing required columns: {missing_cols}")
                logger.info("Available columns: " + str(list(df_features.columns)))
                raise ValueError(f"Missing required columns for matchup intelligence: {missing_cols}")
            
            # Configure matchup feature integration
            matchup_config = MatchupFeatureConfig(
                include_schedule_strength=True,
                include_environmental_factors=True,
                include_situational_adjustments=True,
                weeks_ahead_sos=weeks_ahead_sos,
                season_for_features=target_season,  # Use current season, not future season
                cache_matchup_data=True
            )
            
            logger.info(f"✅ Matchup config created successfully")
            
            # Initialize matchup integrator
            try:
                matchup_integrator = MatchupFeatureIntegrator(matchup_config)
                logger.info(f"✅ MatchupFeatureIntegrator initialized successfully")
            except Exception as e:
                logger.error(f"❌ MATCHUP INTEGRATOR INIT FAILED: {e}")
                raise
            
            # Count features before integration
            features_before = len(df_features.columns)
            
            # Integrate matchup features
            try:
                df_features_enhanced = matchup_integrator.integrate_matchup_features(
                    df_features,
                    weeks_to_analyze=list(range(1, weeks_ahead_sos + 1))
                )
                
                features_after = len(df_features_enhanced.columns)
                matchup_features_added = features_after - features_before
                
                logger.info(f"✅ MATCHUP INTEGRATION SUCCESSFUL")
                logger.info(f"   Features before: {features_before}")
                logger.info(f"   Features after: {features_after}")
                logger.info(f"   Matchup features added: {matchup_features_added}")
                
                # Validate that matchup features were actually added
                if matchup_features_added == 0:
                    logger.warning(f"⚠️ WARNING: No matchup features were added despite successful integration")
                
                # Check for specific matchup feature columns
                sos_columns = [col for col in df_features_enhanced.columns if 'sos_rating' in col]
                env_columns = [col for col in df_features_enhanced.columns if any(env in col for env in ['dome', 'altitude', 'weather'])]
                
                logger.info(f"   SOS columns found: {len(sos_columns)} - {sos_columns[:3]}...")
                logger.info(f"   Environmental columns found: {len(env_columns)} - {env_columns[:3]}...")
                
                df_features = df_features_enhanced
                
            except Exception as e:
                logger.error(f"❌ MATCHUP FEATURES INTEGRATION FAILED: {e}")
                logger.error(f"   Input data shape: {df_features.shape}")
                logger.error(f"   Weeks to analyze: {list(range(1, weeks_ahead_sos + 1))}")
                import traceback
                logger.error(f"   Full traceback: {traceback.format_exc()}")
                raise
            
        except Exception as e:
            logger.error(f"❌ MATCHUP INTELLIGENCE INTEGRATION FAILED: {e}")
            logger.error(f"   This means NO matchup features (SOS, weather, environmental) will be available")
            logger.info("   Continuing with traditional features only")
    elif include_matchup_intelligence and not MATCHUP_INTELLIGENCE_AVAILABLE:
        logger.warning("Matchup intelligence requested but components not available. Using traditional features only.")
    
    # --- Add target variable ---
    if next_season_actuals_df is not None and not next_season_actuals_df.empty:
        points_col_name = config.get('scoring.fantasy_points_columns', {}).get(config.get('scoring.default_system', 'ppr'), 'fantasy_points_ppr')
        
        # Ensure required columns exist in next_season_actuals_df
        if points_col_name in next_season_actuals_df.columns and 'games' in next_season_actuals_df.columns and 'player_id' in next_season_actuals_df.columns:
            target_df_prep = next_season_actuals_df[['player_id', points_col_name, 'games']].copy()
            target_df_prep['games_for_fppg'] = target_df_prep['games'].replace(0, np.nan)
            target_df_prep[config.get('data.target_variable', 'fantasy_points_ppr')] = target_df_prep[points_col_name] / target_df_prep['games_for_fppg']
            target_df_to_merge = target_df_prep[['player_id', config.get('data.target_variable', 'fantasy_points_ppr')]]
            df_features = pd.merge(df_features, target_df_to_merge, on='player_id', how='left')
            logger.info(f"Successfully merged target variable '{config.get('data.target_variable', 'fantasy_points_ppr')}' for prediction season {prediction_season}.")
        else:
            missing_cols_actuals = [col for col in ['player_id', points_col_name, 'games'] if col not in next_season_actuals_df.columns]
            logger.warning(f"Required columns ({missing_cols_actuals}) not found in actuals data for {prediction_season}. Target variable '{config.get('data.target_variable', 'fantasy_points_ppr')}' will be NaN.")
            df_features[config.get('data.target_variable', 'fantasy_points_ppr')] = np.nan
    else:
        if inference_mode:
            # INFERENCE MODE: Generate projection features for ranking, don't use historical actuals
            logger.info(f"🎯 INFERENCE MODE: Generating projection features for {prediction_season} rankings")
            logger.info(f"   Features based on {target_season} data → {prediction_season} projections")
            
            # For inference mode, we don't set a target variable since ML models will predict it
            # The features we've generated are designed to predict future performance
            df_features[config.get('data.target_variable', 'fantasy_points_ppr')] = np.nan
            
            logger.info(f"✅ Generated projection features for {len(df_features)} players")
            logger.info(f"   Target variable set to NaN - ML models will generate predictions")
        else:
            # TRAINING MODE: Set to NaN for prediction
            logger.info(f"No actuals data available for {prediction_season}. Target variable '{config.get('data.target_variable', 'fantasy_points_ppr')}' will be NaN.")
            df_features[config.get('data.target_variable', 'fantasy_points_ppr')] = np.nan
    # --- End of target variable addition ---

    # Add metadata columns
    df_features['season'] = target_season
    df_features['prediction_season'] = target_season + 1
    
    # Feature engineering metadata
    df_features['has_matchup_intelligence'] = include_matchup_intelligence and MATCHUP_INTELLIGENCE_AVAILABLE
    df_features['has_position_specific_features'] = include_position_specific_features and MATCHUP_INTELLIGENCE_AVAILABLE
    df_features['feature_engineering_version'] = 'v2_integrated' if (include_matchup_intelligence or include_position_specific_features) else 'v1_traditional'
    
    # COMPREHENSIVE FEATURE ENGINEERING SUMMARY
    logger.info("=" * 80)
    logger.info("🎯 COMPREHENSIVE FEATURE ENGINEERING SUMMARY")
    logger.info("=" * 80)
    
    feature_count = len(df_features.columns)
    matchup_features = len([col for col in df_features.columns if col.startswith('next_')]) if include_matchup_intelligence else 0
    
    # Count key feature categories
    opportunity_features = len([col for col in df_features.columns 
                               if any(keyword in col.lower() for keyword in ['target_share', 'air_yards', 'wopr', 'adot'])])
    usage_features = len([col for col in df_features.columns 
                         if any(keyword in col.lower() for keyword in ['snap_share', 'route_participation', 'high_value'])])
    position_features = len([col for col in df_features.columns 
                            if any(keyword in col.lower() for keyword in ['rb_role', 'te_role', 'wr_tier', 'qb_style'])])
    
    logger.info(f"📊 Total Players: {len(df_features)}")
    logger.info(f"📊 Total Features: {feature_count}")
    logger.info(f"   • Opportunity Metrics: {opportunity_features}")
    logger.info(f"   • Usage Analytics: {usage_features}")
    logger.info(f"   • Position-Specific: {position_features}")
    logger.info(f"   • Matchup Intelligence: {matchup_features}")
    
    # Show sample of key features for validation
    key_feature_samples = {}
    sample_features = ['target_share', 'air_yards_share', 'wopr', 'snap_share', 'red_zone_opportunities']
    
    for feature in sample_features:
        if feature in df_features.columns:
            non_zero_count = (df_features[feature] != 0).sum()
            avg_value = df_features[feature].mean()
            key_feature_samples[feature] = f"{non_zero_count} non-zero (avg: {avg_value:.3f})"
    
    if key_feature_samples:
        logger.info("🔍 Key Feature Validation:")
        for feature, stats in key_feature_samples.items():
            logger.info(f"   • {feature}: {stats}")
    
    # Enhancement flags status
    enhancements = []
    if OPPORTUNITY_METRICS_AVAILABLE and opportunity_features > 0:
        enhancements.append("✅ Opportunity Metrics")
    else:
        enhancements.append("❌ Opportunity Metrics")
        
    if POSITION_SPECIFIC_FEATURES_AVAILABLE and include_position_specific_features:
        enhancements.append("✅ Position-Specific Features")
    else:
        enhancements.append("❌ Position-Specific Features")
        
    if MATCHUP_INTELLIGENCE_AVAILABLE and include_matchup_intelligence:
        enhancements.append("✅ Matchup Intelligence")
    else:
        enhancements.append("❌ Matchup Intelligence")
    
    logger.info("🏗️  Feature Enhancement Status:")
    for enhancement in enhancements:
        logger.info(f"   {enhancement}")
    
    logger.info(f"🔖 Feature Engineering Version: {df_features['feature_engineering_version'].iloc[0] if not df_features.empty else 'unknown'}")
    
    # DETAILED COMPONENT SUCCESS/FAILURE REPORT
    logger.info("")
    logger.info("🔍 DETAILED COMPONENT STATUS REPORT")
    logger.info("-" * 80)
    
    # Core Features Status
    logger.info("📊 Core Features:")
    logger.info(f"   ✅ Per-game statistics: SUCCESSFUL")
    logger.info(f"   ✅ Efficiency metrics: SUCCESSFUL") 
    logger.info(f"   ✅ Team aggregates: SUCCESSFUL")
    logger.info(f"   ✅ Usage metrics: SUCCESSFUL")
    logger.info(f"   ✅ Lagged features: SUCCESSFUL")
    logger.info(f"   ✅ Age calculation: SUCCESSFUL")
    logger.info(f"   ✅ Rookie handling: SUCCESSFUL")
    
    # Enhanced Features Status
    logger.info("🎯 Enhanced Features:")
    
    # Opportunity Metrics
    if OPPORTUNITY_METRICS_AVAILABLE and opportunity_features > 0:
        logger.info(f"   ✅ Opportunity Metrics: SUCCESSFUL ({opportunity_features} features)")
        logger.info(f"      • Target share, WOPR, air yards share calculations")
        logger.info(f"      • Applied to {len(skill_positions)} skill positions")
    else:
        logger.info(f"   ❌ Opportunity Metrics: FAILED OR DISABLED")
        if not OPPORTUNITY_METRICS_AVAILABLE:
            logger.info(f"      • Reason: Import failed - components not available")
        else:
            logger.info(f"      • Reason: No features generated despite successful import")
    
    # Usage Analytics
    if OPPORTUNITY_METRICS_AVAILABLE and usage_features > 0:
        logger.info(f"   ✅ Usage Analytics: SUCCESSFUL ({usage_features} features)")
        logger.info(f"      • Snap share, route participation, high-value touches")
        logger.info(f"      • Applied to {len(skill_positions)} skill positions")
    else:
        logger.info(f"   ❌ Usage Analytics: FAILED OR DISABLED")
        if not OPPORTUNITY_METRICS_AVAILABLE:
            logger.info(f"      • Reason: Import failed - components not available")
        else:
            logger.info(f"      • Reason: No features generated despite successful import")
    
    # Position-Specific Features
    if include_position_specific_features and POSITION_SPECIFIC_FEATURES_AVAILABLE and position_features > 0:
        logger.info(f"   ✅ Position-Specific Features: SUCCESSFUL ({position_features} features)")
        logger.info(f"      • Enhanced position-specific engineering completed")
        logger.info(f"      • Applied to QB, RB, WR, TE positions")
    elif include_position_specific_features and not POSITION_SPECIFIC_FEATURES_AVAILABLE:
        logger.info(f"   ❌ Position-Specific Features: FAILED")
        logger.info(f"      • Reason: Import failed - components not available")
    elif include_position_specific_features:
        logger.info(f"   ❌ Position-Specific Features: FAILED")
        logger.info(f"      • Reason: Requested but no features generated")
    else:
        logger.info(f"   ⚪ Position-Specific Features: DISABLED (not requested)")
    
    # Matchup Intelligence
    if include_matchup_intelligence and MATCHUP_INTELLIGENCE_AVAILABLE and matchup_features > 0:
        logger.info(f"   ✅ Matchup Intelligence: SUCCESSFUL ({matchup_features} features)")
        
        # Detailed matchup component breakdown
        sos_features = len([col for col in df_features.columns if 'sos_rating' in col])
        env_features = len([col for col in df_features.columns if any(env in col for env in ['dome', 'altitude', 'weather'])])
        situational_features = len([col for col in df_features.columns if any(sit in col for sit in ['primetime', 'division', 'rest'])])
        
        logger.info(f"      • Schedule Strength (SOS): {sos_features} features")
        logger.info(f"      • Environmental Factors: {env_features} features") 
        logger.info(f"      • Situational Adjustments: {situational_features} features")
        logger.info(f"      • Analysis window: {weeks_ahead_sos} weeks ahead")
        
    elif include_matchup_intelligence and not MATCHUP_INTELLIGENCE_AVAILABLE:
        logger.info(f"   ❌ Matchup Intelligence: FAILED")
        logger.info(f"      • Reason: Import failed - components not available")
        logger.info(f"      • Missing: SOS Calculator, Weather Integration, Environmental Factors")
    elif include_matchup_intelligence:
        logger.info(f"   ❌ Matchup Intelligence: FAILED")
        logger.info(f"      • Reason: Requested but no matchup features generated")
        logger.info(f"      • Check SOS calculations, schedule data, and environmental factors")
    else:
        logger.info(f"   ⚪ Matchup Intelligence: DISABLED (not requested)")
    
    # Data Quality Report
    logger.info("")
    logger.info("📋 Data Quality Report:")
    logger.info(f"   • Total players processed: {len(df_features)}")
    logger.info(f"   • Players with complete data: {df_features.dropna().shape[0]}")
    logger.info(f"   • Missing data percentage: {(df_features.isnull().sum().sum() / (len(df_features) * len(df_features.columns)) * 100):.1f}%")
    
    # Position breakdown
    if 'position' in df_features.columns:
        position_counts = df_features['position'].value_counts()
        logger.info(f"   • Position breakdown: {dict(position_counts)}")
    
    # Feature Engineering Success Score
    total_components = 4  # Core + 3 enhanced components
    successful_components = 1  # Core features always succeed
    
    if OPPORTUNITY_METRICS_AVAILABLE and opportunity_features > 0:
        successful_components += 1
    if include_position_specific_features and POSITION_SPECIFIC_FEATURES_AVAILABLE and position_features > 0:
        successful_components += 1
    if include_matchup_intelligence and MATCHUP_INTELLIGENCE_AVAILABLE and matchup_features > 0:
        successful_components += 1
    
    success_rate = (successful_components / total_components) * 100
    
    logger.info("")
    logger.info(f"🏆 FEATURE ENGINEERING SUCCESS RATE: {success_rate:.1f}% ({successful_components}/{total_components} components)")
    
    if success_rate == 100:
        logger.info("🎉 PERFECT SCORE! All requested components executed successfully!")
    elif success_rate >= 75:
        logger.info("✅ EXCELLENT! Most components executed successfully.")
    elif success_rate >= 50:
        logger.info("⚠️  PARTIAL SUCCESS. Some components failed - check logs above.")
    else:
        logger.info("❌ POOR PERFORMANCE. Multiple components failed - review configuration.")
    
    logger.info("=" * 80)
    
    # Apply final data quality validation before returning
    # Use training mode for historical data (more lenient thresholds)
    is_training_mode = not inference_mode
    validator.validate_feature_engineered_data(
        df_features, 
        target_season, 
        include_matchup_intelligence=include_matchup_intelligence,
        training_mode=is_training_mode
    )
    validator.log_data_quality_summary(df_features, f"Feature Engineering Complete ({target_season})")
    
    # CRITICAL: Add missing calculated features before production filter
    if inference_mode:
        # Calculate dual_threat_score for RBs (rushing + receiving yards per game)
        rb_mask = df_features['position'] == 'RB'
        games_played = df_features['games'].replace(0, 1)  # Avoid division by zero
        
        if rb_mask.any():
            dual_threat = (df_features['rushing_yards'].fillna(0) + df_features['receiving_yards'].fillna(0)) / games_played
            df_features.loc[rb_mask, 'dual_threat_score'] = dual_threat[rb_mask]
            logger.info(f"✅ Calculated dual_threat_score for {rb_mask.sum()} RBs")
        
        # Calculate rushing_share (player rushing yards / team total rushing yards)
        if 'team' in df_features.columns and 'rushing_yards' in df_features.columns:
            try:
                # Calculate team totals for rushing yards
                team_rushing = df_features.groupby(['team', 'season'])['rushing_yards'].sum().reset_index()
                team_rushing = team_rushing.rename(columns={'rushing_yards': 'team_rushing_yards'})
                
                # Merge team totals back
                df_features = df_features.merge(
                    team_rushing, 
                    on=['team', 'season'], 
                    how='left'
                )
                
                # Calculate rushing share only where we have team data
                if 'team_rushing_yards' in df_features.columns:
                    mask = (df_features['team_rushing_yards'] > 0) & (df_features['rushing_yards'] > 0)
                    df_features.loc[mask, 'rushing_share'] = (
                        df_features.loc[mask, 'rushing_yards'] / df_features.loc[mask, 'team_rushing_yards']
                    )
                    
                    # Clean up temporary column
                    df_features = df_features.drop(columns=['team_rushing_yards'], errors='ignore')
                    logger.info(f"✅ Calculated rushing_share for {mask.sum()} players")
                else:
                    logger.warning("⚠️ Could not merge team rushing data, setting rushing_share to 0")
                    df_features['rushing_share'] = 0.0
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to calculate rushing_share: {e}, setting to 0")
                df_features['rushing_share'] = 0.0
        
        # Fill NaN values for these calculated features
        df_features['dual_threat_score'] = df_features['dual_threat_score'].fillna(0.0)
        df_features['rushing_share'] = df_features['rushing_share'].fillna(0.0)
    
    # PRODUCTION FILTER: Return only core features that models expect
    if inference_mode:
        core_features = [
            # Model features (23 unique across all positions)
            'games', 'age', 'attempts', 'completions', 'passing_yards', 'passing_tds', 'interceptions',
            'carries', 'rushing_yards', 'rushing_tds', 'targets', 'receptions', 'receiving_yards', 
            'receiving_tds', 'yards_per_attempt', 'completion_percentage', 'yards_per_carry', 
            'catch_rate', 'dual_threat_score', 'rushing_share', 'target_share', 'yards_per_target',
            'yards_per_reception',
            # Essential metadata 
            'player_id', 'player_name', 'team', 'position', 'fantasy_points_ppr'
        ]
        
        # Filter to only available core features
        available_core_features = [col for col in core_features if col in df_features.columns]
        missing_core_features = [col for col in core_features if col not in df_features.columns]
        
        if missing_core_features:
            logger.warning(f"⚠️ Missing core features: {missing_core_features}")
        
        df_features = df_features[available_core_features]
        logger.info(f"🎯 PRODUCTION MODE: Filtered to {len(available_core_features)} core features")
        logger.info(f"   Core features: {available_core_features}")
    
    return df_features


def save_engineered_features(df, season, prediction_season):
    """
    Save engineered features to a parquet file.
    
    Args:
        df (pd.DataFrame): DataFrame containing engineered features
        season (int): NFL season year used for feature engineering
        prediction_season (int): Season to predict
        
    Returns:
        bool: True if the features were saved successfully, False otherwise
    """
    try:
        logger.info(f"Saving engineered features for {season} season")
        return save_features_data(df, season, prediction_season)
    except Exception as e:
        logger.error(f"Error saving engineered features for {season} season: {e}")
        return False


def engineer_and_save_features(
    start_year=None, 
    end_year=None, 
    positions=None,
    include_matchup_intelligence=False,
    include_position_specific_features=False,
    weeks_ahead_sos=4
):
    """
    Engineer and save features for a range of seasons with optional enhancements.
    
    Args:
        start_year (int, optional): The first season to engineer features for. Defaults to config.get('data.data_start_year', 2010).
        end_year (int, optional): The last season to engineer features for. Defaults to config.get('data.data_end_year', 2024)-1.
        positions (list, optional): List of positions to include. Defaults to config.get('data.positions', ['QB', 'RB', 'WR', 'TE']).
        include_matchup_intelligence (bool): Include Phase 2 matchup intelligence features
        include_position_specific_features (bool): Include advanced position-specific features  
        weeks_ahead_sos (int): Number of weeks ahead to analyze for strength of schedule
    
    Returns:
        list: List of paths to the saved files
    """
    config = get_config()
    if start_year is None:
        start_year = config.get('data.data_start_year', 2010)
    if end_year is None:
        # End one year before the last available year since we need the next year for prediction
        end_year = config.get('data.data_end_year', 2024) - 1
    if positions is None:
        positions = config.get('data.positions', ['QB', 'RB', 'WR', 'TE'])
    
    logger.info(f"Engineering and saving features for seasons {start_year} to {end_year}")
    logger.info(f"Matchup intelligence: {include_matchup_intelligence}, Position-specific: {include_position_specific_features}")
    
    saved_files = []
    
    for year in range(start_year, end_year + 1):
        try:
            logger.info(f"Processing season {year}...")
            logger.info(f"Engineering features for {year} season to predict {year+1}")
            df = engineer_features_for_season(
                year,
                include_matchup_intelligence=include_matchup_intelligence,
                include_position_specific_features=include_position_specific_features,
                weeks_ahead_sos=weeks_ahead_sos
            )
            
            # Filter for relevant positions
            if positions and 'position' in df.columns:
                df = df[df['position'].isin(positions)]
            
            # Only save if we have data
            if not df.empty:
                success = save_engineered_features(df, year, year+1)
                if success:
                    from .data_storage import get_features_data_path
                    file_path = get_features_data_path(year, year+1)
                    saved_files.append(str(file_path))
                    logger.info(f"Completed feature engineering for season {year}")
                else:
                    logger.error(f"Failed to save engineered features for season {year}")
            else:
                logger.warning(f"No data to save for season {year}")
        except Exception as e:
            logger.error(f"Failed to process season {year}: {str(e)}")
            # Continue with the next season even if this one fails
            continue
    
    logger.info(f"Completed engineering and saving features for all seasons. Saved {len(saved_files)} files.")
    return saved_files


def create_matchup_adjusted_projections(
    base_projections_df: pd.DataFrame,
    weeks_to_analyze: List[int] = None
) -> pd.DataFrame:
    """
    Create matchup-adjusted projections from base projections using Phase 3 matchup intelligence.
    
    Args:
        base_projections_df: DataFrame with player IDs and base projections
        weeks_to_analyze: List of weeks to analyze for matchup adjustments
        
    Returns:
        DataFrame with matchup-adjusted projections
    """
    logger.info(f"Creating matchup-adjusted projections for {len(base_projections_df)} players")
    
    if weeks_to_analyze is None:
        weeks_to_analyze = list(range(1, 5))  # First 4 weeks by default
    
    if not MATCHUP_INTELLIGENCE_AVAILABLE:
        logger.warning("Matchup intelligence components not available. Returning original projections.")
        result = base_projections_df.copy()
        result['matchup_adjusted_fppg'] = result.get('projected_fppg', result.get('fantasy_points_ppr', 0))
        result['matchup_adjustment_factor'] = 1.0
        return result
    
    try:
        # Configure matchup integrator
        config = get_config()
        matchup_config = MatchupFeatureConfig(
            include_schedule_strength=True,
            include_environmental_factors=True,
            include_situational_adjustments=True,
            weeks_ahead_sos=len(weeks_to_analyze),
            season_for_features=config.get('data.current_season', 2025),
            cache_matchup_data=True
        )
        
        # Initialize matchup integrator
        matchup_integrator = MatchupFeatureIntegrator(matchup_config)
        
        # Get matchup-adjusted projections
        adjusted_projections = matchup_integrator.get_matchup_adjusted_projections(
            base_projections_df,
            weeks=weeks_to_analyze
        )
        
        logger.info(f"Successfully created matchup-adjusted projections")
        logger.info(f"Average adjustment factor: {adjusted_projections['matchup_adjustment_factor'].mean():.3f}")
        
        return adjusted_projections
        
    except Exception as e:
        logger.error(f"Error creating matchup-adjusted projections: {e}")
        # Return original projections if adjustment fails
        result = base_projections_df.copy()
        result['matchup_adjusted_fppg'] = result.get('projected_fppg', result.get('fantasy_points_ppr', 0))
        result['matchup_adjustment_factor'] = 1.0
        return result


if __name__ == "__main__":
    # Example usage - Traditional feature engineering
    print("🎯 Fantasy Football Feature Engineering")
    print("=" * 50)
    
    # Traditional feature engineering
    print("Running traditional feature engineering...")
    traditional_features = engineer_features_for_season(2022)
    print(f"Traditional features: {len(traditional_features.columns)} columns for {len(traditional_features)} players")
    
    # Enhanced feature engineering (if available)
    if MATCHUP_INTELLIGENCE_AVAILABLE:
        print("\nRunning enhanced feature engineering with matchup intelligence...")
        enhanced_features = engineer_features_for_season(
            2022,
            include_matchup_intelligence=True,
            include_position_specific_features=True,
            weeks_ahead_sos=4
        )
        print(f"Enhanced features: {len(enhanced_features.columns)} columns for {len(enhanced_features)} players")
        
        # Demo matchup-adjusted projections
        if not enhanced_features.empty:
            sample_projections = enhanced_features[['player_id', 'position', 'team']].head(5).copy()
            sample_projections['projected_fppg'] = [20.0, 15.0, 12.0, 10.0, 8.0]
            
            adjusted = create_matchup_adjusted_projections(sample_projections)
            
            print("\nSample Matchup-Adjusted Projections:")
            for _, row in adjusted.iterrows():
                print(f"  {row['position']}: {row['projected_fppg']:.1f} → {row['matchup_adjusted_fppg']:.1f} "
                      f"({row['matchup_adjustment_factor']:.3f}x)")
    else:
        print("\nMatchup intelligence components not available - using traditional features only")
        
    print("\nFeature engineering complete! 🎯")
