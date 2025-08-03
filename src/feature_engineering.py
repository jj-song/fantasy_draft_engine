"""
Feature engineering module for the Fantasy Football AI Draft Tool.

This module contains functions to generate features for predicting player performance
in the upcoming season based on historical data, as described in Section 3.3 of the project plan.
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path
from data_storage import load_raw_data, save_features_data

# Add the project root to the path so we can import the config
sys.path.append(str(Path(__file__).parent.parent))
import config

# Configure logging
logger = logging.getLogger(__name__)


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
        for position in config.POSITIONS:
            pos_mask = (df_features['position'] == position) & rookies
            
            for draft_round in range(1, 8):  # Draft rounds 1-7
                # Get the configured baseline FPPG for this position and draft round
                baseline_fppg = config.ROOKIE_BASELINE_FPPG.get(position, {}).get(draft_round, 1.0)
                
                # Apply the baseline FPPG to rookies of this position and draft round
                round_mask = pos_mask & (df_features['draftround'] == draft_round)
                df_features.loc[round_mask, 'projected_fppg'] = baseline_fppg
            
            # Handle UDFAs (draft round > 7 or NaN)
            udfa_mask = pos_mask & ((df_features['draftround'] > 7) | df_features['draftround'].isna())
            df_features.loc[udfa_mask, 'projected_fppg'] = config.ROOKIE_BASELINE_FPPG.get(position, {}).get('UDFA', 1.0)
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
        for position in config.POSITIONS:
            pos_mask = minimal_data_mask & (df_features['position'] == position)
            baseline_fppg = config.MINIMAL_DATA_BASELINE_FPPG.get(position, 1.0)
            
            df_features.loc[pos_mask, 'projected_fppg'] = baseline_fppg
            
            logger.info(f"Applied baseline FPPG of {baseline_fppg} to {pos_mask.sum()} {position} players with minimal data")
    else:
        logger.warning("No games played column found for minimal data handling")
        # Apply baseline FPPG for all players based on position as a fallback
        for position in config.POSITIONS:
            pos_mask = df_features['position'] == position
            baseline_fppg = config.MINIMAL_DATA_BASELINE_FPPG.get(position, 1.0)
            
            # Only apply to players without a projected_fppg value
            if 'projected_fppg' in df_features.columns:
                apply_mask = pos_mask & df_features['projected_fppg'].isna()
            else:
                apply_mask = pos_mask
                df_features['projected_fppg'] = np.nan
            
            df_features.loc[apply_mask, 'projected_fppg'] = baseline_fppg
            
            logger.info(f"Applied baseline FPPG of {baseline_fppg} to {apply_mask.sum()} {position} players as fallback")
    
    return df_features


def engineer_features_for_season(target_season, historical_seasons=None):
    """
    Engineer features for a target season using data from historical seasons.
    
    Args:
        target_season (int): The season to engineer features for (predicting target_season+1)
        historical_seasons (list, optional): List of historical seasons to use. 
                                            Defaults to [target_season-1, target_season].
    
    Returns:
        pandas.DataFrame: DataFrame with engineered features
    """
    logger.info(f"Engineering features for {target_season} season to predict {target_season+1}")
    
    if historical_seasons is None:
        historical_seasons = [target_season-1, target_season]
    
    # Load data for all required seasons
    historical_data = {}
    prediction_season = target_season + 1
    next_season_actuals_df = None
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
        logger.warning(f"No data available for target season {target_season}. Skipping feature engineering.")
        return pd.DataFrame()

    # Convert birth_date to datetime if it exists, before copying to df_features
    if 'birth_date' in historical_data[target_season].columns:
        historical_data[target_season]['birth_date'] = pd.to_datetime(historical_data[target_season]['birth_date'], errors='coerce')
        logger.info(f"Converted 'birth_date' column to datetime for season {target_season} in current_season_df")

    # Get the current season data
    current_season_df = historical_data[target_season]
    
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
    
    # --- Add target variable ---
    if next_season_actuals_df is not None and not next_season_actuals_df.empty:
        points_col_name = config.FANTASY_POINTS_COLUMNS.get(config.DEFAULT_SCORING_SYSTEM, 'fantasy_points_ppr')
        
        # Ensure required columns exist in next_season_actuals_df
        if points_col_name in next_season_actuals_df.columns and 'games' in next_season_actuals_df.columns and 'player_id' in next_season_actuals_df.columns:
            target_df_prep = next_season_actuals_df[['player_id', points_col_name, 'games']].copy()
            target_df_prep['games_for_fppg'] = target_df_prep['games'].replace(0, np.nan)
            target_df_prep[config.TARGET_VARIABLE] = target_df_prep[points_col_name] / target_df_prep['games_for_fppg']
            target_df_to_merge = target_df_prep[['player_id', config.TARGET_VARIABLE]]
            df_features = pd.merge(df_features, target_df_to_merge, on='player_id', how='left')
            logger.info(f"Successfully merged target variable '{config.TARGET_VARIABLE}' for prediction season {prediction_season}.")
        else:
            missing_cols_actuals = [col for col in ['player_id', points_col_name, 'games'] if col not in next_season_actuals_df.columns]
            logger.warning(f"Required columns ({missing_cols_actuals}) not found in actuals data for {prediction_season}. Target variable '{config.TARGET_VARIABLE}' will be NaN.")
            df_features[config.TARGET_VARIABLE] = np.nan
    else:
        logger.info(f"No actuals data available for {prediction_season}. Target variable '{config.TARGET_VARIABLE}' will be NaN.")
        df_features[config.TARGET_VARIABLE] = np.nan
    # --- End of target variable addition ---

    # Add metadata columns
    df_features['season'] = target_season
    df_features['prediction_season'] = target_season + 1
    
    logger.info(f"Successfully engineered features for {len(df_features)} players")
    
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


def engineer_and_save_features(start_year=None, end_year=None, positions=None):
    """
    Engineer and save features for a range of seasons.
    
    Args:
        start_year (int, optional): The first season to engineer features for. Defaults to config.DATA_START_YEAR.
        end_year (int, optional): The last season to engineer features for. Defaults to config.DATA_END_YEAR-1.
        positions (list, optional): List of positions to include. Defaults to config.POSITIONS.
    
    Returns:
        list: List of paths to the saved files
    """
    if start_year is None:
        start_year = config.DATA_START_YEAR
    if end_year is None:
        # End one year before the last available year since we need the next year for prediction
        end_year = config.DATA_END_YEAR - 1
    if positions is None:
        positions = config.POSITIONS
    
    logger.info(f"Engineering and saving features for seasons {start_year} to {end_year}")
    
    saved_files = []
    
    for year in range(start_year, end_year + 1):
        try:
            logger.info(f"Processing season {year}...")
            logger.info(f"Engineering features for {year} season to predict {year+1}")
            df = engineer_features_for_season(year)
            
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


if __name__ == "__main__":
    # Example usage
    engineer_and_save_features()
