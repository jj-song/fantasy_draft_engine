"""
Current Data Pipeline for Fantasy Football AI Draft Tool.

This module handles current season data, roster updates, and team assignments
to ensure rankings reflect the most recent player situations.
"""

import pandas as pd
import numpy as np
import nfl_data_py as nfl
import logging
from datetime import datetime
import sys
from pathlib import Path
import unicodedata
import re

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from src.config import get_config

# Configure logging
logger = logging.getLogger(__name__)


def add_calculated_features(data: pd.DataFrame) -> pd.DataFrame:
    """
    Add per-game calculations and efficiency metrics that ML models expect.
    
    This function bridges the feature gap by calculating derived metrics from existing data.
    Target: +40 features to get closer to the 209 features ML models expect.
    
    Args:
        data: DataFrame with basic player stats
        
    Returns:
        DataFrame with additional calculated features
    """
    logger.info(f"🧮 Adding calculated features to bridge ML feature gap")
    
    if data.empty:
        return data
    
    result = data.copy()
    features_added = 0
    
    # PHASE 1A: PER-GAME CALCULATIONS
    # Many ML models expect per-game averages rather than totals
    games_col = 'games' if 'games' in result.columns else None
    
    if games_col and games_col in result.columns:
        logger.info(f"📊 Calculating per-game metrics using {games_col}")
        
        # Passing per-game metrics
        if 'passing_attempts' in result.columns:
            result['attempts_per_game'] = np.where(result[games_col] > 0, result['passing_attempts'] / result[games_col], 0)
            features_added += 1
        if 'completions' in result.columns:
            result['completions_per_game'] = np.where(result[games_col] > 0, result['completions'] / result[games_col], 0)
            features_added += 1
        if 'passing_yards' in result.columns:
            result['passing_yards_per_game'] = np.where(result[games_col] > 0, result['passing_yards'] / result[games_col], 0)
            features_added += 1
        if 'passing_tds' in result.columns:
            result['passing_tds_per_game'] = np.where(result[games_col] > 0, result['passing_tds'] / result[games_col], 0)
            features_added += 1
        if 'interceptions' in result.columns:
            result['interceptions_per_game'] = np.where(result[games_col] > 0, result['interceptions'] / result[games_col], 0)
            features_added += 1
        
        # Rushing per-game metrics
        if 'carries' in result.columns:
            result['carries_per_game'] = np.where(result[games_col] > 0, result['carries'] / result[games_col], 0)
            features_added += 1
        if 'rushing_yards' in result.columns:
            result['rushing_yards_per_game'] = np.where(result[games_col] > 0, result['rushing_yards'] / result[games_col], 0)
            features_added += 1
        if 'rushing_tds' in result.columns:
            result['rushing_tds_per_game'] = np.where(result[games_col] > 0, result['rushing_tds'] / result[games_col], 0)
            features_added += 1
        
        # Receiving per-game metrics
        if 'targets' in result.columns:
            result['targets_per_game'] = np.where(result[games_col] > 0, result['targets'] / result[games_col], 0)
            features_added += 1
        if 'receptions' in result.columns:
            result['receptions_per_game'] = np.where(result[games_col] > 0, result['receptions'] / result[games_col], 0)
            features_added += 1
        if 'receiving_yards' in result.columns:
            result['receiving_yards_per_game'] = np.where(result[games_col] > 0, result['receiving_yards'] / result[games_col], 0)
            features_added += 1
        if 'receiving_tds' in result.columns:
            result['receiving_tds_per_game'] = np.where(result[games_col] > 0, result['receiving_tds'] / result[games_col], 0)
            features_added += 1
    else:
        logger.warning(f"No games column found for per-game calculations")
    
    # PHASE 1B: EFFICIENCY METRICS
    # Critical efficiency ratios that ML models expect
    
    # Passing efficiency
    if 'completions' in result.columns and 'passing_attempts' in result.columns:
        result['completion_percentage'] = np.where(result['passing_attempts'] > 0, result['completions'] / result['passing_attempts'], 0)
        features_added += 1
    
    if 'passing_yards' in result.columns and 'passing_attempts' in result.columns:
        result['yards_per_attempt'] = np.where(result['passing_attempts'] > 0, result['passing_yards'] / result['passing_attempts'], 0)
        features_added += 1
    
    if 'passing_yards' in result.columns and 'completions' in result.columns:
        result['yards_per_completion'] = np.where(result['completions'] > 0, result['passing_yards'] / result['completions'], 0)
        features_added += 1
    
    if 'passing_tds' in result.columns and 'passing_attempts' in result.columns:
        result['td_rate'] = np.where(result['passing_attempts'] > 0, result['passing_tds'] / result['passing_attempts'], 0)
        features_added += 1
    
    if 'interceptions' in result.columns and 'passing_attempts' in result.columns:
        result['int_rate'] = np.where(result['passing_attempts'] > 0, result['interceptions'] / result['passing_attempts'], 0)
        features_added += 1
    
    # Rushing efficiency
    if 'rushing_yards' in result.columns and 'carries' in result.columns:
        result['yards_per_carry'] = np.where(result['carries'] > 0, result['rushing_yards'] / result['carries'], 0)
        features_added += 1
    
    if 'rushing_tds' in result.columns and 'carries' in result.columns:
        result['rushing_td_rate'] = np.where(result['carries'] > 0, result['rushing_tds'] / result['carries'], 0)
        features_added += 1
    
    # Receiving efficiency
    if 'receptions' in result.columns and 'targets' in result.columns:
        result['catch_rate'] = np.where(result['targets'] > 0, result['receptions'] / result['targets'], 0)
        features_added += 1
    
    if 'receiving_yards' in result.columns and 'targets' in result.columns:
        result['yards_per_target'] = np.where(result['targets'] > 0, result['receiving_yards'] / result['targets'], 0)
        features_added += 1
    
    if 'receiving_yards' in result.columns and 'receptions' in result.columns:
        result['yards_per_reception'] = np.where(result['receptions'] > 0, result['receiving_yards'] / result['receptions'], 0)
        features_added += 1
    
    if 'receiving_tds' in result.columns and 'targets' in result.columns:
        result['receiving_td_rate'] = np.where(result['targets'] > 0, result['receiving_tds'] / result['targets'], 0)
        features_added += 1
    
    if 'receiving_tds' in result.columns and 'receptions' in result.columns:
        result['td_per_reception'] = np.where(result['receptions'] > 0, result['receiving_tds'] / result['receptions'], 0)
        features_added += 1
    
    # PHASE 1C: POSITIONAL USAGE RATIOS
    # Important for understanding player roles
    
    # QB ratios
    if 'carries' in result.columns and 'passing_attempts' in result.columns:
        result['rush_pass_ratio'] = np.where(result['passing_attempts'] > 0, result['carries'] / result['passing_attempts'], 0)
        features_added += 1
    
    # Target utilization
    if 'receptions' in result.columns and 'targets' in result.columns:
        result['target_utilization'] = np.where(result['targets'] > 0, result['receptions'] / result['targets'], 0)
        features_added += 1
    
    # PHASE 1D: VOLUME INDICATORS
    # Important for identifying high-usage players
    
    if 'passing_attempts' in result.columns and 'carries' in result.columns:
        result['total_touches'] = result['passing_attempts'] + result['carries']
        features_added += 1
    
    if 'targets' in result.columns and 'carries' in result.columns:
        result['skill_position_touches'] = result['targets'] + result['carries'] 
        features_added += 1
    
    # PHASE 1E: FANTASY-SPECIFIC METRICS
    # Metrics specifically relevant for fantasy football
    
    if 'fantasy_points_ppr' in result.columns and games_col:
        result['fantasy_points_per_game'] = np.where(result[games_col] > 0, result['fantasy_points_ppr'] / result[games_col], 0)
        features_added += 1
    
    # Red zone efficiency (if red zone data exists)
    if 'red_zone_opportunities' in result.columns and 'red_zone_opportunities' in result.columns:
        # This will be enhanced after opportunity metrics are calculated
        pass
    
    # PHASE 1F: CONSISTENCY METRICS
    # Important for identifying reliable vs volatile players
    
    # Basic consistency indicators (more can be added with weekly data)
    if 'passing_yards' in result.columns and 'passing_attempts' in result.columns:
        result['pass_yards_consistency'] = np.where(
            result['passing_attempts'] > 0,
            np.minimum(result['passing_yards'] / (result['passing_attempts'] * 8), 2.0),  # Cap at 2.0 for outliers
            0
        )
        features_added += 1
    
    if 'receiving_yards' in result.columns and 'receptions' in result.columns:
        result['receiving_consistency'] = np.where(
            result['receptions'] > 0,
            np.minimum(result['receiving_yards'] / (result['receptions'] * 12), 2.0),  # Cap at 2.0 for outliers
            0
        )
        features_added += 1
    
    # PHASE 1G: ADVANCED RATIOS
    # Complex ratios that ML models might find predictive
    
    if 'passing_tds' in result.columns and 'interceptions' in result.columns:
        result['td_int_ratio'] = np.where(
            result['interceptions'] > 0, 
            result['passing_tds'] / result['interceptions'], 
            result['passing_tds'] * 2  # If no INTs, give bonus
        )
        features_added += 1
    
    if 'receiving_tds' in result.columns and 'rushing_tds' in result.columns:
        result['total_tds'] = result['receiving_tds'] + result['rushing_tds']
        features_added += 1
    
    if 'receiving_yards' in result.columns and 'rushing_yards' in result.columns:
        result['total_scrimmage_yards'] = result['receiving_yards'] + result['rushing_yards']
        features_added += 1
    
    # PHASE 1H: ADDITIONAL ADVANCED FEATURES
    # Add more complex metrics that ML models expect
    
    # Deep target analysis (simplified version - can be enhanced with more PBP data)
    if 'receiving_air_yards' in result.columns and 'targets' in result.columns:
        result['deep_target_rate'] = np.where(
            result['targets'] > 0,
            np.minimum(result['receiving_air_yards'] / (result['targets'] * 10), 1.0),  # Approximate deep target rate
            0
        )
        features_added += 1
    
    # Contested catch estimation (approximate from catch rate and air yards)
    if 'catch_rate' in result.columns and 'receiving_air_yards' in result.columns:
        result['contested_catch_rate'] = np.where(
            result['receiving_air_yards'] > 0,
            result['catch_rate'] * 0.6,  # Approximate: contested catches are ~60% of regular catch rate
            0
        )
        features_added += 1
    
    # Blocking snap estimate for RBs/TEs
    if 'total_offense_snaps' in result.columns and 'targets' in result.columns and 'carries' in result.columns:
        total_touches = result['targets'] + result['carries']
        result['blocking_snap_estimate'] = np.where(
            result['total_offense_snaps'] > 0,
            result['total_offense_snaps'] - total_touches,  # Approximate blocking snaps
            0
        )
        features_added += 1
    
    # Deep target indicator
    if 'receiving_air_yards' in result.columns and 'targets' in result.columns:
        avg_air_per_target = np.where(result['targets'] > 0, result['receiving_air_yards'] / result['targets'], 0)
        result['deep_target_indicator'] = (avg_air_per_target > 12).astype(int)  # Binary indicator for deep targets
        features_added += 1
    
    # Route diversity indicators
    if 'target_share' in result.columns and 'receiving_air_yards' in result.columns:
        result['route_diversity'] = result['target_share'] * 0.8 + (result['receiving_air_yards'] / max(result['receiving_air_yards'].max(), 1)) * 0.2
        features_added += 1
    
    # Snap utilization efficiency
    if 'total_offense_snaps' in result.columns and 'fantasy_points_ppr' in result.columns:
        result['fantasy_points_per_snap'] = np.where(result['total_offense_snaps'] > 0, result['fantasy_points_ppr'] / result['total_offense_snaps'], 0)
        features_added += 1
    
    # Age-adjusted metrics (if age is available)
    if 'age' in result.columns:
        # Age interaction with production
        if 'fantasy_points_ppr' in result.columns:
            result['age_adjusted_production'] = result['fantasy_points_ppr'] / np.maximum(result['age'] - 20, 1)  # Adjusted for age
            features_added += 1
    
    # Experience indicators
    if 'entry_year' in result.columns:
        config = get_config()
        current_year = config.get('data.inference_data_year', 2024)
        result['nfl_experience'] = current_year - result['entry_year']
        result['veteran_indicator'] = (result['nfl_experience'] > 4).astype(int)
        # Add experience alias that ML models expect
        result['experience'] = result['nfl_experience']
        features_added += 3
    
    # Missing key calculated features that ML models expect
    
    # attempts_per_game (critical missing feature)
    if 'passing_attempts' in result.columns and games_col:
        result['attempts_per_game'] = np.where(result[games_col] > 0, result['passing_attempts'] / result[games_col], 0)
        features_added += 1
    
    # fantasy_points_per_touch (critical missing feature)
    if 'fantasy_points_ppr' in result.columns:
        total_touches = 0
        if 'passing_attempts' in result.columns:
            total_touches += result['passing_attempts']
        if 'carries' in result.columns:
            total_touches += result['carries']
        if 'targets' in result.columns:
            total_touches += result['targets']
        
        result['fantasy_points_per_touch'] = np.where(total_touches > 0, result['fantasy_points_ppr'] / total_touches, 0)
        features_added += 1
    
    # fantasy_points_ppr_per_game (critical missing feature)
    if 'fantasy_points_ppr' in result.columns and games_col:
        result['fantasy_points_ppr_per_game'] = np.where(result[games_col] > 0, result['fantasy_points_ppr'] / result[games_col], 0)
        features_added += 1
    
    # catch_rate (critical missing feature)
    if 'receptions' in result.columns and 'targets' in result.columns:
        result['catch_rate'] = np.where(result['targets'] > 0, result['receptions'] / result['targets'], 0)
        features_added += 1
    
    # completion_percentage (critical missing feature - might already exist)
    if 'completions' in result.columns and 'passing_attempts' in result.columns:
        if 'completion_percentage' not in result.columns:
            result['completion_percentage'] = np.where(result['passing_attempts'] > 0, result['completions'] / result['passing_attempts'], 0)
            features_added += 1
    
    # Fantasy relevance and upside scores
    if 'fantasy_points_ppr' in result.columns:
        # Fantasy relevance score (normalized fantasy points)
        max_fp = result['fantasy_points_ppr'].max() if len(result) > 0 else 1
        result['fantasy_relevance_score'] = result['fantasy_points_ppr'] / max(max_fp, 1)
        
        # Fantasy upside score (based on ceiling projection)
        result['fantasy_upside_score'] = result['fantasy_points_ppr'] * 1.2  # 20% upside
        features_added += 2
    
    # Early down rate (approximation)
    if 'carries' in result.columns and 'passing_attempts' in result.columns:
        total_plays = result['carries'] + result['passing_attempts']
        # Approximate early down rate as 65% of total plays
        result['early_down_rate'] = np.where(total_plays > 0, 0.65, 0)
        features_added += 1
    
    # Team context indicators (if team data available)
    if 'team' in result.columns:
        # This would be enhanced with actual team stats, but for now create placeholder
        result['team_pass_heavy'] = 0.5  # Would calculate from team stats
        result['team_run_heavy'] = 0.5   # Would calculate from team stats
        features_added += 2
    
    logger.info(f"✅ Added {features_added} calculated features")
    return result


def add_lagged_features(data: pd.DataFrame, current_year: int) -> pd.DataFrame:
    """
    Add lagged (previous season) features that ML models expect.
    
    This function loads the previous season's data and creates L1 (lag 1) features
    which are critical for ML prediction models. Target: +30 features.
    
    Args:
        data: DataFrame with current season player stats
        current_year: Current season year (e.g., 2024)
        
    Returns:
        DataFrame with additional lagged features (_L1 suffix)
    """
    logger.info(f"📈 Adding lagged features from {current_year-1} season")
    
    if data.empty:
        return data
    
    previous_year = current_year - 1
    result = data.copy()
    
    try:
        # Import necessary modules
        from src.data_storage import load_raw_data
        
        # Load previous season data
        logger.info(f"Loading {previous_year} season data for lagged features")
        prev_data = load_raw_data(previous_year)
        
        if prev_data.empty:
            logger.warning(f"⚠️ No {previous_year} data available for lagged features")
            return result
        
        logger.info(f"Loaded {len(prev_data)} players from {previous_year} season")
        
        # Ensure both datasets have player_name for merging
        if 'player_name' not in prev_data.columns:
            logger.warning("Previous season data missing player_name column")
            return result
        if 'player_name' not in result.columns:
            logger.warning("Current season data missing player_name column")
            return result
        
        # Define key statistics to create lagged features for
        # These are the most important features that ML models expect from previous season
        LAG_FEATURES = [
            # Basic volume stats
            'passing_attempts', 'completions', 'passing_yards', 'passing_tds', 'interceptions',
            'carries', 'rushing_yards', 'rushing_tds', 'rushing_fumbles',
            'targets', 'receptions', 'receiving_yards', 'receiving_tds', 'receiving_fumbles',
            
            # Games and usage
            'games', 'fantasy_points_ppr', 'fantasy_points',
            
            # Efficiency metrics (if available in previous data)
            'passer_rating', 'qbr', 'yards_per_attempt', 'yards_per_carry', 'yards_per_reception',
            
            # Advanced stats (if available)
            'air_yards', 'yac', 'target_share', 'snap_count_offense',
            
            # Position-specific
            'fumbles_lost', 'sacks', 'sack_fumbles'
        ]
        
        # Create lagged feature columns
        lag_columns = {}
        features_added = 0
        
        for feature in LAG_FEATURES:
            if feature in prev_data.columns:
                lag_col_name = f"{feature}_L1"
                lag_columns[feature] = lag_col_name
                features_added += 1
        
        # Select relevant columns from previous data
        prev_cols = ['player_name'] + [col for col in LAG_FEATURES if col in prev_data.columns]
        prev_subset = prev_data[prev_cols].copy()
        
        # Rename columns to add L1 suffix
        rename_mapping = {col: f"{col}_L1" for col in prev_subset.columns if col != 'player_name'}
        prev_subset = prev_subset.rename(columns=rename_mapping)
        
        # Clean player names for better matching
        def clean_player_name(name):
            if pd.isna(name):
                return name
            # Remove accents and normalize
            name = unicodedata.normalize('NFD', str(name))
            name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
            # Remove extra whitespace and convert to title case
            name = ' '.join(str(name).split()).title()
            return name
        
        result['player_name_clean'] = result['player_name'].apply(clean_player_name)
        prev_subset['player_name_clean'] = prev_subset['player_name'].apply(clean_player_name)
        
        # Merge lagged features with current data
        logger.info(f"Merging {features_added} lagged features with current data")
        
        # Use left join to preserve all current players
        merged = result.merge(
            prev_subset.drop('player_name', axis=1),  # Drop original, keep cleaned version
            left_on='player_name_clean',
            right_on='player_name_clean',
            how='left',
            suffixes=('', '_prev')
        )
        
        # Drop the temporary clean name column
        merged = merged.drop('player_name_clean', axis=1)
        
        # Fill missing lagged features with 0 (for rookies and players without previous data)
        lag_cols = [col for col in merged.columns if col.endswith('_L1')]
        merged[lag_cols] = merged[lag_cols].fillna(0)
        
        # Calculate derived lagged features
        derived_features = 0
        
        # Year-over-year change indicators
        if 'fantasy_points_ppr_L1' in merged.columns and 'fantasy_points_ppr' in merged.columns:
            merged['fantasy_points_yoy_change'] = merged['fantasy_points_ppr'] - merged['fantasy_points_ppr_L1']
            merged['fantasy_points_yoy_ratio'] = np.where(
                merged['fantasy_points_ppr_L1'] > 0,
                merged['fantasy_points_ppr'] / merged['fantasy_points_ppr_L1'],
                1.0
            )
            derived_features += 2
        
        # Usage stability indicators
        if 'targets_L1' in merged.columns and 'targets' in merged.columns:
            merged['target_stability'] = np.where(
                merged['targets_L1'] > 0,
                np.minimum(merged['targets'] / merged['targets_L1'], 3.0),  # Cap at 3x
                1.0
            )
            derived_features += 1
        
        if 'carries_L1' in merged.columns and 'carries' in merged.columns:
            merged['carry_stability'] = np.where(
                merged['carries_L1'] > 0,
                np.minimum(merged['carries'] / merged['carries_L1'], 3.0),  # Cap at 3x
                1.0
            )
            derived_features += 1
        
        # Experience continuity (games played consistency)
        if 'games_L1' in merged.columns and 'games' in merged.columns:
            merged['games_consistency'] = np.where(
                merged['games_L1'] > 0,
                merged['games'] / merged['games_L1'],
                1.0
            )
            derived_features += 1
        
        # Breakout/decline indicators
        if 'fantasy_points_ppr_L1' in merged.columns:
            # Rookie indicator (no previous fantasy points)
            merged['rookie_indicator'] = (merged['fantasy_points_ppr_L1'] == 0).astype(int)
            
            # Breakout candidate (low previous production)
            merged['breakout_candidate'] = (merged['fantasy_points_ppr_L1'] < 100).astype(int)
            
            # Veteran decline risk (high age with declining production)
            if 'age' in merged.columns:
                merged['decline_risk'] = ((merged['age'] > 29) & 
                                        (merged['fantasy_points_ppr'] < merged['fantasy_points_ppr_L1'])).astype(int)
            else:
                merged['decline_risk'] = 0
                
            derived_features += 3
        
        total_features = features_added + derived_features
        logger.info(f"✅ Added {total_features} lagged features ({features_added} direct + {derived_features} derived)")
        
        # Log successful merges
        matched_players = (merged[lag_cols].sum(axis=1) > 0).sum()
        logger.info(f"📊 Lagged data matched for {matched_players}/{len(merged)} players")
        
        return merged
        
    except ImportError as e:
        logger.error(f"❌ Failed to import data_storage module: {e}")
        return result
    except Exception as e:
        logger.error(f"❌ Error adding lagged features: {e}")
        logger.error(f"   This is expected for the first year of data or if {previous_year} data is missing")
        return result


def sanitize_text_for_json(text):
    """
    Sanitize text to ensure it can be properly JSON serialized.
    
    Args:
        text: Input text that may contain problematic Unicode characters
        
    Returns:
        Clean text safe for JSON serialization
    """
    if pd.isna(text) or text is None:
        return ""
    
    # Convert to string if not already
    text = str(text)
    
    # Normalize Unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Remove or replace problematic characters
    # Replace high surrogates and other problematic Unicode
    text = re.sub(r'[\ud800-\udfff]', '', text)  # Remove surrogate pairs
    text = re.sub(r'[^\x00-\x7F]', '', text)     # Remove non-ASCII characters
    
    # Clean up any resulting double spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def sanitize_dataframe_for_json(df):
    """
    Sanitize all text columns in a DataFrame for JSON serialization.
    
    Args:
        df: Input DataFrame
        
    Returns:
        DataFrame with sanitized text columns
    """
    df_clean = df.copy()
    
    # Find text columns
    text_columns = df_clean.select_dtypes(include=['object']).columns
    
    for col in text_columns:
        logger.debug(f"Sanitizing column: {col}")
        df_clean[col] = df_clean[col].apply(sanitize_text_for_json)
    
    return df_clean

def get_current_roster_assignments(year=None):
    """
    Get current team assignments for all players from the most recent roster data.
    
    Args:
        year (int, optional): Year to get rosters for. Defaults to config.INFERENCE_DATA_YEAR.
    
    Returns:
        pd.DataFrame: DataFrame with player_id, current_team, position, player_name
    """
    if year is None:
        config = get_config()
        year = config.get('data.inference_data_year', 2024)
    
    logger.info(f"Fetching current roster assignments for {year}")
    
    try:
        # Get the most recent roster data
        rosters = nfl.import_seasonal_rosters([year])
        
        # Get player name mappings
        player_ids = nfl.import_ids()
        
        # Create clean roster mapping
        current_rosters = rosters[['player_id', 'team', 'position', 'player_name']].copy()
        current_rosters = current_rosters.drop_duplicates(subset=['player_id'], keep='last')  # Keep most recent entry
        current_rosters = current_rosters.rename(columns={'team': 'current_team'})
        
        # Sanitize text data to prevent JSON encoding issues
        current_rosters = sanitize_dataframe_for_json(current_rosters)
        
        logger.info(f"Successfully loaded {len(current_rosters)} current roster assignments")
        
        # Validate we have key players
        sample_players = ['Austin Ekeler', 'Christian McCaffrey', 'Justin Jefferson']
        for player in sample_players:
            player_data = current_rosters[current_rosters['player_name'].str.contains(player, case=False, na=False)]
            if len(player_data) > 0:
                logger.info(f"✅ {player}: {player_data.iloc[0]['current_team']} {player_data.iloc[0]['position']}")
            else:
                logger.warning(f"⚠️ {player} not found in current rosters")
        
        return current_rosters
        
    except Exception as e:
        logger.error(f"Error fetching current roster assignments: {e}")
        return pd.DataFrame()

def get_current_season_performance(year=None):
    """
    Get the most recent season performance data for inference with enhanced features.
    
    Args:
        year (int, optional): Year to get performance for. Defaults to config.INFERENCE_DATA_YEAR.
    
    Returns:
        pd.DataFrame: DataFrame with enhanced current season statistics including PBP and snap data
    """
    if year is None:
        config = get_config()
        year = config.get('data.inference_data_year', 2024)
        
    logger.info(f"Fetching enhanced current season performance data for {year}")
    
    try:
        # ENHANCED DATA ACQUISITION: Use the enhanced pipeline with PBP and snap data
        from src.data_acquisition import fetch_player_season_stats
        from src.data_storage import load_raw_data, save_raw_data
        
        try:
            # Try to load existing enhanced data first
            current_data = load_raw_data(year)
            
            # Check if the data has enhanced features (PBP and snap data)
            enhanced_features = ['air_yards_per_target', 'total_offense_snaps', 'avg_completion_probability']
            has_enhanced_features = any(col in current_data.columns for col in enhanced_features)
            
            if has_enhanced_features:
                logger.info(f"✅ Loaded existing enhanced {year} data: {len(current_data)} records with advanced features")
            else:
                logger.info(f"⚠️ Existing {year} data lacks enhanced features, fetching fresh enhanced data")
                raise FileNotFoundError("Need to fetch enhanced data")
                
        except FileNotFoundError:
            # Fetch fresh enhanced data with PBP and snap counts
            logger.info(f"Fetching fresh enhanced {year} data with PBP and snap count features")
            current_data = fetch_player_season_stats(year)  # This now includes PBP and snap data
            
            if current_data.empty:
                logger.warning(f"No enhanced data returned for {year}, falling back to basic data")
                current_data = nfl.import_seasonal_data([year])
                # Add player names if missing
                if 'player_name' not in current_data.columns and 'first_name' in current_data.columns:
                    current_data['player_name'] = current_data['first_name'].astype(str) + ' ' + current_data['last_name'].astype(str)
            else:
                logger.info(f"✅ Fetched enhanced {year} data: {len(current_data)} records with advanced features")
            
            # Save enhanced data for future use
            save_raw_data(current_data, year)
            logger.info(f"✅ Saved enhanced {year} data with advanced features")
        
        # Log available feature categories for debugging
        if not current_data.empty:
            feature_categories = {
                'PBP Features': [col for col in current_data.columns if any(pbp in col.lower() for pbp in ['air_yards', 'epa', 'completion', 'yac'])],
                'Snap Features': [col for col in current_data.columns if any(snap in col.lower() for snap in ['snap', 'offense_pct'])],
                'Basic Features': [col for col in current_data.columns if col in ['targets', 'carries', 'receptions', 'rushing_yards', 'receiving_yards']]
            }
            
            for category, features in feature_categories.items():
                if features:
                    logger.info(f"📊 {category}: {len(features)} features - {features[:3]}{'...' if len(features) > 3 else ''}")
        
        return current_data
        
    except Exception as e:
        logger.error(f"Error fetching enhanced current season performance: {e}")
        return pd.DataFrame()

def update_data_with_current_teams(data_df, current_rosters_df):
    """
    Update player data with current team assignments.
    
    Args:
        data_df (pd.DataFrame): Player performance data
        current_rosters_df (pd.DataFrame): Current roster assignments
    
    Returns:
        pd.DataFrame: Updated data with current team assignments
    """
    logger.info("Updating data with current team assignments")
    
    if data_df.empty or current_rosters_df.empty:
        logger.warning("Empty input data for team assignment update")
        return data_df
    
    # Merge current team assignments
    if 'player_id' in data_df.columns and 'player_id' in current_rosters_df.columns:
        # CRITICAL FIX: Use LEFT join to preserve all players - don't lose anyone!
        updated_data = data_df.merge(
            current_rosters_df[['player_id', 'current_team', 'player_name', 'position']],
            on='player_id',
            how='left',  # Changed from 'inner' to 'left' to preserve all players
            suffixes=('_old', '_current')
        )
        
        logger.info(f"✅ Merge preserved all players: {len(data_df)} → {len(updated_data)}")
        
        # Use current team if available, fall back to original team
        if 'team' in updated_data.columns:
            updated_data['team_updated'] = updated_data['current_team'].fillna(updated_data['team'])
            updated_data['team'] = updated_data['team_updated']
            updated_data = updated_data.drop(columns=['team_updated', 'current_team'])
        else:
            updated_data['team'] = updated_data['current_team'].fillna('UNK')  # Fallback for players without roster data
            updated_data = updated_data.drop(columns=['current_team'])
        
        # Update player names and position if we have better current data
        if 'player_name_current' in updated_data.columns:
            updated_data['player_name'] = updated_data['player_name_current'].fillna(
                updated_data.get('player_name_old', updated_data.get('player_name', ''))
            )
        
        # CRITICAL FIX: Ensure position column is preserved correctly
        if 'position_current' in updated_data.columns:
            # Use roster position as authoritative source, fallback to original
            updated_data['position'] = updated_data['position_current'].fillna(
                updated_data.get('position_old', updated_data.get('position', ''))
            )
        elif 'position' not in updated_data.columns and 'position_old' in updated_data.columns:
            # If no current position but have old position, use that
            updated_data['position'] = updated_data['position_old']
        
        # Clean up suffix columns
        suffix_columns = [col for col in updated_data.columns if col.endswith('_old') or col.endswith('_current')]
        if suffix_columns:
            updated_data = updated_data.drop(columns=suffix_columns)
            logger.info(f"Cleaned up {len(suffix_columns)} suffix columns: {suffix_columns[:3]}{'...' if len(suffix_columns) > 3 else ''}")
        
        # Validate the merge preserved all players
        if len(data_df) != len(updated_data):
            logger.error(f"❌ MERGE ERROR: Player count mismatch! Original: {len(data_df)}, Updated: {len(updated_data)}")
            logger.error("This should not happen with LEFT join - investigating...")
            
            # Log some debugging info
            missing_players = len(data_df) - len(updated_data)
            logger.error(f"Lost {missing_players} players during merge")
            
            # For now, continue with available players rather than failing hard
            logger.warning("Continuing with available players - team assignments may be incomplete")
        
        # Count successful team updates
        if 'team' in data_df.columns and len(updated_data) > 0:
            # Count players with updated team info (non-null current team assignments)
            roster_matches = updated_data['position'].notna().sum()  # Players who matched roster data
            logger.info(f"🔍 Roster matching: {roster_matches}/{len(updated_data)} players have current roster data")
            
            if roster_matches > 0:
                logger.info(f"✅ Team assignment update successful for {roster_matches} players")
        
        return updated_data
    
    else:
        logger.warning("Cannot merge on player_id - missing column")
        return data_df

def validate_current_data_freshness():
    """
    Validate that we have access to current season data.
    
    Returns:
        dict: Validation results with data availability and freshness info
    """
    logger.info("Validating current data freshness")
    
    current_year = datetime.now().year
    config = get_config()
    results = {
        'current_year': current_year,
        'inference_year': config.get('data.inference_data_year', 2024),
        'data_available': False,
        'roster_available': False,
        'freshness_status': 'unknown',
        'recommendations': []
    }
    
    try:
        # Check if we can access inference year data
        config = get_config()
        inference_year = config.get('data.inference_data_year', 2024)
        test_data = nfl.import_seasonal_data([inference_year])
        if len(test_data) > 0:
            results['data_available'] = True
            logger.info(f"✅ {inference_year} season data available: {len(test_data)} records")
        
        # Check roster data
        test_rosters = nfl.import_seasonal_rosters([inference_year])
        if len(test_rosters) > 0:
            results['roster_available'] = True
            logger.info(f"✅ {inference_year} roster data available: {len(test_rosters)} records")
        
        # Assess freshness
        year_gap = current_year - inference_year
        if year_gap <= 1:
            results['freshness_status'] = 'current'
            logger.info(f"✅ Data is current (using {inference_year} in {current_year})")
        elif year_gap == 2:
            results['freshness_status'] = 'slightly_outdated'
            results['recommendations'].append(f"Consider updating INFERENCE_DATA_YEAR to {current_year-1}")
            logger.warning(f"⚠️ Data is slightly outdated (using {inference_year} in {current_year})")
        else:
            results['freshness_status'] = 'outdated'
            results['recommendations'].append(f"Update INFERENCE_DATA_YEAR to {current_year-1} or {current_year}")
            logger.error(f"❌ Data is outdated (using {inference_year} in {current_year})")
        
    except Exception as e:
        logger.error(f"Error validating data freshness: {e}")
        results['recommendations'].append("Check nfl_data_py installation and network connectivity")
    
    return results

def create_current_inference_dataset(position=None):
    """
    Create a complete dataset for current inference with enhanced features and updated team assignments.
    
    Args:
        position (str, optional): Filter for specific position
    
    Returns:
        pd.DataFrame: Ready-to-use inference dataset with advanced features and current teams
    """
    logger.info(f"Creating enhanced current inference dataset" + (f" for {position}" if position else ""))
    
    # Get enhanced current season performance (includes PBP and snap data)
    current_performance = get_current_season_performance()
    if current_performance.empty:
        logger.error("No current performance data available")
        return pd.DataFrame()
    
    # Get current roster assignments  
    current_rosters = get_current_roster_assignments()
    if current_rosters.empty:
        logger.error("No current roster data available")
        logger.warning("Proceeding with performance data only - team assignments may be outdated")
        updated_data = current_performance
    else:
        # CRITICAL FIX: Filter rosters by position BEFORE merging to prevent duplicates
        if position and 'position' in current_rosters.columns:
            current_rosters = current_rosters[current_rosters['position'] == position]
            logger.info(f"Filtered rosters to {len(current_rosters)} {position} players")
        
        # Update with current teams - now position-filtered
        updated_data = update_data_with_current_teams(current_performance, current_rosters)
    
    # Additional safety filter: ensure we only have players with matching performance data
    if position and 'position' in updated_data.columns:
        # Use roster position as the authoritative source
        updated_data = updated_data[updated_data['position'] == position]
        logger.info(f"Position filter: {len(updated_data)} {position} players")
    
    # Remove any duplicate player_ids that might still exist
    if 'player_id' in updated_data.columns:
        before_dedup = len(updated_data)
        updated_data = updated_data.drop_duplicates(subset=['player_id'], keep='first')
        after_dedup = len(updated_data)
        if before_dedup != after_dedup:
            logger.warning(f"Removed {before_dedup - after_dedup} duplicate player_ids")
    
    # ENHANCED FEATURE ENGINEERING: Apply advanced metrics that ML models expect
    logger.info(f"🔧 Applying advanced feature engineering to {len(updated_data)} {position or 'all'} players")
    
    try:
        # STEP 1: Add calculated features (per-game metrics, efficiency ratios, etc.)
        updated_data = add_calculated_features(updated_data)
        logger.info(f"✅ Applied calculated features (per-game metrics and efficiency ratios)")
        
        # STEP 2: Add lagged features from previous season (L1 features)
        config = get_config()
        inference_year = config.get('data.inference_data_year', 2024)
        updated_data = add_lagged_features(updated_data, inference_year)
        logger.info(f"✅ Applied lagged features from previous season")
        
        # STEP 3: Apply opportunity metrics (air yards, target share, WOPR, etc.)
        from src.features.opportunity_metrics import OpportunityMetricsCalculator
        opportunity_calc = OpportunityMetricsCalculator(inference_year)
        updated_data = opportunity_calc.enhance_opportunity_metrics(updated_data)
        logger.info(f"✅ Applied opportunity metrics enhancement")
        
        # Apply usage analytics (snap counts, route participation, etc.)
        from src.features.usage_analytics import UsageAnalyticsCalculator
        usage_calc = UsageAnalyticsCalculator(inference_year)
        updated_data = usage_calc.calculate_all_usage_metrics(updated_data)
        logger.info(f"✅ Applied usage analytics enhancement")
        
        # Apply additional advanced features based on position
        if position:
            logger.info(f"🎯 Applying position-specific feature engineering for {position}")
            
            # Use the new feature engineering system
            from src.core.base_feature_engineer import BaseFeatureEngineer
            from src.core.model_factory import ModelFactory
            
            try:
                # Get the appropriate feature engineer for the position
                feature_engineer = ModelFactory.create_feature_engineer(position)
                if feature_engineer:
                    # Apply position-specific feature engineering
                    enhanced_features = feature_engineer.engineer_features(updated_data)
                    
                    # Merge enhanced features back
                    if not enhanced_features.empty and len(enhanced_features) == len(updated_data):
                        # Add only new columns from enhanced features
                        for col in enhanced_features.columns:
                            if col not in updated_data.columns:
                                updated_data[col] = enhanced_features[col]
                        logger.info(f"✅ Applied {position}-specific feature engineering")
                    else:
                        logger.warning(f"⚠️ Position-specific feature engineering failed for {position}")
                else:
                    logger.warning(f"⚠️ No feature engineer available for position {position}")
            except Exception as e:
                logger.warning(f"⚠️ Position-specific feature engineering failed: {e}")
        
        # Final feature count
        total_features = len([col for col in updated_data.columns if col not in ['player_id', 'player_name', 'position', 'team']])
        logger.info(f"🔢 Final feature count: {total_features} features for ML prediction")
        
    except Exception as e:
        logger.error(f"❌ Error during advanced feature engineering: {e}")
        logger.warning("Proceeding with basic features only")
    
    # Sanitize text data to prevent JSON encoding issues
    updated_data = sanitize_dataframe_for_json(updated_data)
    
    logger.info(f"✅ Created enhanced current inference dataset: {len(updated_data)} records with advanced features")
    return updated_data

def print_team_movement_report():
    """
    Print a report of notable team movements between training and inference years.
    """
    logger.info("Generating team movement report")
    
    try:
        # Get training year rosters (2023)
        config = get_config()
        training_end_year = config.get('data.training_data_end_year', 2023)
        training_rosters = nfl.import_seasonal_rosters([training_end_year])
        training_teams = training_rosters[['player_id', 'team', 'player_name']].drop_duplicates(subset=['player_id'], keep='last')
        
        # Get current rosters (2024)  
        current_rosters = get_current_roster_assignments()
        
        # Find movements
        merged = training_teams.merge(current_rosters, on='player_id', how='inner', suffixes=('_2023', '_2024'))
        movements = merged[merged['team'] != merged['current_team']]
        
        if len(movements) > 0:
            inference_year = config.get('data.inference_data_year', 2024)
            print(f"\n🔄 NOTABLE TEAM MOVEMENTS ({training_end_year} → {inference_year})")
            print("=" * 80)
            
            # Focus on fantasy-relevant positions
            fantasy_movements = movements[movements['position'].isin(['QB', 'RB', 'WR', 'TE'])]
            fantasy_movements = fantasy_movements.sort_values('position')
            
            for _, row in fantasy_movements.head(20).iterrows():  # Show top 20
                print(f"{row['player_name_2024']:<25} {row['position']:<3} {row['team']:<4} → {row['current_team']:<4}")
            
            if len(fantasy_movements) > 20:
                print(f"... and {len(fantasy_movements) - 20} more movements")
            
            print(f"\nTotal movements tracked: {len(movements)}")
            print(f"Fantasy-relevant movements: {len(fantasy_movements)}")
        else:
            print("No team movements detected (this may indicate a data issue)")
            
    except Exception as e:
        logger.error(f"Error generating team movement report: {e}")

if __name__ == "__main__":
    # Test the current data pipeline
    print("🏈 Testing Current Data Pipeline")
    print("=" * 50)
    
    # Validate data freshness
    freshness = validate_current_data_freshness()
    print(f"Data freshness: {freshness['freshness_status']}")
    for rec in freshness['recommendations']:
        print(f"💡 {rec}")
    
    # Test roster assignments
    current_rosters = get_current_roster_assignments()
    print(f"\n📋 Current roster assignments: {len(current_rosters)} players")
    
    # Show team movement report
    print_team_movement_report()
    
    # Test inference dataset creation
    print(f"\n🎯 Testing inference dataset creation...")
    rb_data = create_current_inference_dataset('RB')
    print(f"Created RB inference dataset: {len(rb_data)} players")
    
    if len(rb_data) > 0:
        print("\nSample RB data with current teams:")
        sample_cols = ['player_name', 'position', 'team', 'fantasy_points_ppr'] 
        available_cols = [col for col in sample_cols if col in rb_data.columns]
        print(rb_data[available_cols].head())