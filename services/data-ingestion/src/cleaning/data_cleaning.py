"""
Data cleaning module for the Fantasy Football AI Draft Tool.

This module contains functions to clean and preprocess the raw player statistics
data according to the requirements in Section 3.2 of the project plan.
"""

import os
import logging
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add the project root to the path so we can import the config
sys.path.append(str(Path(__file__).parent.parent))
from src.config import get_config

# Get configuration instance
config_manager = get_config()

# Configure logging
logger = logging.getLogger(__name__)


def load_raw_season_data(year):
    """
    Load raw player statistics for a specific season.
    
    Args:
        year (int): The NFL season year to load data for
    
    Returns:
        pandas.DataFrame: DataFrame containing raw player statistics for the specified season
    """
    raw_data_dir = os.path.join(Path(__file__).parent.parent, config_manager.get('data.raw_data_dir', '../../data/raw'))
    file_path = os.path.join(raw_data_dir, f"player_season_{year}.parquet")
    
    try:
        df = pd.read_parquet(file_path)
        logger.info(f"Successfully loaded raw player statistics for {year} season. Total players: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"Error loading raw player statistics for {year} season: {str(e)}")
        raise


def handle_missing_values(df, position):
    """
    Handle missing values in the player statistics DataFrame.
    
    Args:
        df (pandas.DataFrame): DataFrame containing player statistics
        position (str): Player position ('QB', 'RB', 'WR', 'TE')
    
    Returns:
        pandas.DataFrame: DataFrame with missing values handled
    """
    logger.info(f"Handling missing values for {position} players")
    
    # Make a copy to avoid modifying the original DataFrame
    df_clean = df.copy()
    
    # List of numerical stats columns to impute with 0
    numerical_stats = [
        # Passing stats
        'completions', 'attempts', 'passing_yards', 'passing_tds', 'interceptions',
        'sacks', 'sack_yards', 'sack_fumbles', 'sack_fumbles_lost', 'passing_air_yards',
        'passing_yards_after_catch', 'passing_first_downs', 'passing_epa', 'passing_2pt_conversions',
        
        # Rushing stats
        'carries', 'rushing_yards', 'rushing_tds', 'rushing_fumbles_x', 'rushing_fumbles_lost',
        'rushing_first_downs', 'rushing_epa', 'rushing_2pt_conversions',
        
        # Receiving stats
        'receptions', 'targets', 'receiving_yards', 'receiving_tds', 'receiving_fumbles',
        'receiving_fumbles_lost', 'receiving_air_yards', 'receiving_yards_after_catch',
        'receiving_first_downs', 'receiving_epa', 'receiving_2pt_conversions',
        
        # Special teams
        'special_teams_tds',
        
        # Fantasy points
        'fantasy_points', 'fantasy_points_ppr'
    ]
    
    # Fill missing numerical stats with 0
    for col in numerical_stats:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna(0)
    
    # Handle missing games played
    if 'games' in df_clean.columns:
        # If games is missing but weeks_played exists, use weeks_played
        if 'weeks_played' in df_clean.columns:
            df_clean['games'] = df_clean['games'].fillna(df_clean['weeks_played'])
        
        # If still missing, impute with median for that position
        median_games = df_clean[df_clean['games'] > 0]['games'].median()
        df_clean['games'] = df_clean['games'].fillna(median_games)
    
    # Handle missing draft information
    if 'draft_number' in df_clean.columns:
        # For UDFAs (undrafted free agents), set a high value
        udfa_value = 300  # Configurable value higher than any draft pick
        df_clean['draft_number'] = df_clean['draft_number'].fillna(udfa_value)
    
    if 'draftround' in df_clean.columns:
        # For UDFAs, set to 8 (higher than any actual draft round)
        df_clean['draftround'] = df_clean['draftround'].fillna(8)
    
    # Handle missing team information
    if 'team' in df_clean.columns:
        df_clean['team'] = df_clean['team'].fillna('UNKNOWN')
    
    # Handle missing college information
    if 'college_name' in df_clean.columns:
        df_clean['college_name'] = df_clean['college_name'].fillna('UNKNOWN')
    
    # Handle missing entry year
    if 'entry_year' in df_clean.columns:
        # Use the season year as a fallback for rookies
        season_year = df_clean['season'].iloc[0]
        df_clean['entry_year'] = df_clean['entry_year'].fillna(season_year)
    
    # Log missing value counts after handling
    missing_counts = df_clean.isna().sum()
    if missing_counts.sum() > 0:
        logger.warning(f"Remaining missing values after handling for {position}: {missing_counts[missing_counts > 0]}")
    else:
        logger.info(f"All missing values handled for {position}")
    
    return df_clean


def standardize_formats(df):
    """
    Standardize formats in the player statistics DataFrame.
    
    Args:
        df (pandas.DataFrame): DataFrame containing player statistics
    
    Returns:
        pandas.DataFrame: DataFrame with standardized formats
    """
    logger.info("Standardizing formats")
    
    # Make a copy to avoid modifying the original DataFrame
    df_std = df.copy()
    
    # Ensure consistent team naming abbreviations
    if 'team' in df_std.columns:
        # Map old team abbreviations to new ones if needed
        team_mapping = {
            'OAK': 'LV',  # Oakland Raiders -> Las Vegas Raiders
            'SD': 'LAC',  # San Diego Chargers -> Los Angeles Chargers
            'STL': 'LA',  # St. Louis Rams -> Los Angeles Rams
            'WSH': 'WAS'  # Washington Redskins -> Washington Football Team/Commanders
        }
        df_std['team'] = df_std['team'].replace(team_mapping)
    
    # Convert birth_date to datetime if it's not already
    if 'birth_date' in df_std.columns:
        df_std['birth_date'] = pd.to_datetime(df_std['birth_date'], errors='coerce')
    
    # Ensure position is uppercase
    if 'position' in df_std.columns:
        df_std['position'] = df_std['position'].str.upper()
    
    return df_std


def detect_outliers(df, position):
    """
    Detect and handle outliers in the player statistics DataFrame.
    
    Args:
        df (pandas.DataFrame): DataFrame containing player statistics
        position (str): Player position ('QB', 'RB', 'WR', 'TE')
    
    Returns:
        pandas.DataFrame: DataFrame with outliers handled
        dict: Dictionary of detected outliers for reporting
    """
    logger.info(f"Detecting outliers for {position} players")
    
    # Make a copy to avoid modifying the original DataFrame
    df_clean = df.copy()
    
    # Define position-specific columns to check for outliers
    outlier_columns = {
        'QB': ['attempts', 'passing_yards', 'passing_tds', 'interceptions'],
        'RB': ['carries', 'rushing_yards', 'rushing_tds', 'receptions', 'receiving_yards'],
        'WR': ['targets', 'receptions', 'receiving_yards', 'receiving_tds'],
        'TE': ['targets', 'receptions', 'receiving_yards', 'receiving_tds']
    }
    
    # Only check columns that exist in the DataFrame
    columns_to_check = [col for col in outlier_columns.get(position, []) if col in df_clean.columns]
    
    # Dictionary to store outliers for reporting
    outliers = {}
    
    # For MVP, we'll just log outliers but not modify them
    for col in columns_to_check:
        # Calculate IQR (Interquartile Range)
        Q1 = df_clean[col].quantile(0.25)
        Q3 = df_clean[col].quantile(0.75)
        IQR = Q3 - Q1
        
        # Define outlier bounds
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Find outliers
        outlier_mask = (df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)
        outlier_rows = df_clean[outlier_mask]
        
        if not outlier_rows.empty:
            # Store outliers for reporting
            outliers[col] = outlier_rows[['player_id', 'first_name', 'last_name', col]].to_dict('records')
            
            # Log outliers
            logger.info(f"Detected {len(outlier_rows)} outliers in {col} for {position} players")
            
            # For extreme outliers, we might cap values
            extreme_upper = Q3 + 3 * IQR
            extreme_lower = Q1 - 3 * IQR
            
            # Cap extreme outliers
            df_clean.loc[df_clean[col] > extreme_upper, col] = extreme_upper
            df_clean.loc[df_clean[col] < extreme_lower, col] = extreme_lower
    
    return df_clean, outliers


def check_games_played(df):
    """
    Check for players with games_played > 0 but zero relevant offensive stats.
    
    Args:
        df (pandas.DataFrame): DataFrame containing player statistics
    
    Returns:
        pandas.DataFrame: DataFrame of players with potential data issues
    """
    logger.info("Checking for players with games played but no offensive stats")
    
    # Define relevant offensive stats columns by position
    offensive_stats = {
        'QB': ['attempts', 'completions', 'passing_yards'],
        'RB': ['carries', 'rushing_yards', 'receptions'],
        'WR': ['targets', 'receptions', 'receiving_yards'],
        'TE': ['targets', 'receptions', 'receiving_yards']
    }
    
    # Players with games played but no offensive stats
    potential_issues = []
    
    for position, stats in offensive_stats.items():
        # Filter for position
        pos_df = df[df['position'] == position]
        
        # Check which stats columns exist in the DataFrame
        available_stats = [col for col in stats if col in pos_df.columns]
        
        if available_stats and 'games' in pos_df.columns:
            # Players with games played > 0
            active_players = pos_df[pos_df['games'] > 0]
            
            # Players with all offensive stats = 0
            zero_stats = active_players[(active_players[available_stats] == 0).all(axis=1)]
            
            if not zero_stats.empty:
                logger.warning(f"Found {len(zero_stats)} {position} players with games played but no offensive stats")
                potential_issues.append(zero_stats)
    
    if potential_issues:
        return pd.concat(potential_issues)
    else:
        return pd.DataFrame()


def clean_season_data(year, positions=None):
    """
    Clean player statistics for a specific season.
    
    Args:
        year (int): The NFL season year to clean data for
        positions (list, optional): List of positions to include. Defaults to config.POSITIONS.
    
    Returns:
        pandas.DataFrame: DataFrame containing cleaned player statistics for the specified season
    """
    if positions is None:
        positions = config_manager.get('data.positions', ['QB', 'RB', 'WR', 'TE', 'K'])
    
    logger.info(f"Cleaning player statistics for {year} season for positions: {positions}")
    
    try:
        # Load raw data
        df = load_raw_season_data(year)
        
        # Filter for relevant positions
        df = df[df['position'].isin(positions)]
        
        # Standardize formats
        df = standardize_formats(df)
        
        # Process each position separately for position-specific cleaning
        cleaned_dfs = []
        for position in positions:
            pos_df = df[df['position'] == position]
            
            if not pos_df.empty:
                # Handle missing values
                pos_df = handle_missing_values(pos_df, position)
                
                # Detect and handle outliers
                pos_df, outliers = detect_outliers(pos_df, position)
                
                cleaned_dfs.append(pos_df)
        
        # Combine all cleaned position DataFrames
        cleaned_df = pd.concat(cleaned_dfs)
        
        # Check for players with games played but no offensive stats
        potential_issues = check_games_played(cleaned_df)
        if not potential_issues.empty:
            logger.warning(f"Potential data issues detected for {len(potential_issues)} players")
        
        logger.info(f"Successfully cleaned player statistics for {year} season. Total players: {len(cleaned_df)}")
        
        return cleaned_df
    
    except Exception as e:
        logger.error(f"Error cleaning player statistics for {year} season: {str(e)}")
        raise


def save_cleaned_data(df, year):
    """
    Save cleaned player statistics to a parquet file in the processed data directory.
    
    Args:
        df (pandas.DataFrame): DataFrame containing cleaned player statistics
        year (int): The NFL season year
    
    Returns:
        str: Path to the saved file
    """
    # Create the processed data directory if it doesn't exist
    processed_data_dir = os.path.join(Path(__file__).parent.parent, config_manager.get('data.processed_data_dir', '../../data/processed'))
    os.makedirs(processed_data_dir, exist_ok=True)
    
    # Define the output file path
    output_file = os.path.join(processed_data_dir, f"player_season_cleaned_{year}.parquet")
    
    try:
        # Save the DataFrame to a parquet file
        df.to_parquet(output_file, index=False)
        logger.info(f"Successfully saved cleaned player statistics for {year} season to {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Error saving cleaned player statistics for {year} season: {str(e)}")
        raise


def clean_and_save_historical_data(start_year=None, end_year=None, positions=None):
    """
    Clean and save player statistics for a range of seasons.
    
    Args:
        start_year (int, optional): The first season to clean data for. Defaults to config.DATA_START_YEAR.
        end_year (int, optional): The last season to clean data for. Defaults to config.DATA_END_YEAR.
        positions (list, optional): List of positions to include. Defaults to config.POSITIONS.
    
    Returns:
        list: List of paths to the saved files
    """
    if start_year is None:
        start_year = config_manager.get('data.data_start_year', 2010)
    if end_year is None:
        end_year = config.DATA_END_YEAR
    if positions is None:
        positions = config_manager.get('data.positions', ['QB', 'RB', 'WR', 'TE', 'K'])
    
    logger.info(f"Cleaning and saving player statistics for seasons {start_year} to {end_year}")
    
    saved_files = []
    
    for year in range(start_year, end_year + 1):
        try:
            logger.info(f"Processing season {year}...")
            df = clean_season_data(year, positions)
            
            # Only save if we have data
            if not df.empty:
                file_path = save_cleaned_data(df, year)
                saved_files.append(file_path)
                logger.info(f"Completed cleaning for season {year}")
            else:
                logger.warning(f"No data to save for season {year}")
        except Exception as e:
            logger.error(f"Failed to process season {year}: {str(e)}")
            # Continue with the next season even if this one fails
            continue
    
    logger.info(f"Completed cleaning and saving player statistics for all seasons. Saved {len(saved_files)} files.")
    return saved_files


if __name__ == "__main__":
    # Example usage
    clean_and_save_historical_data()
