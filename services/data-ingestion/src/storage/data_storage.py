"""
Data Storage and Retrieval Module

This module handles data storage and retrieval operations for the Fantasy Football AI Draft Tool.
It provides functions to:
1. Get paths to raw, cleaned, and feature-engineered data files
2. Load data from these files
3. Save data to these files
4. Manage data grain and format consistency
"""

import os
import logging
import pandas as pd
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

def ensure_player_name_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure player_name column exists in DataFrame, creating it from first_name + last_name if needed.
    
    This is a critical function for data consistency throughout the pipeline.
    Many downstream components expect a 'player_name' column for joining and analysis.
    
    Args:
        df: DataFrame to check and potentially modify
        
    Returns:
        DataFrame with guaranteed player_name column
    """
    if df.empty:
        return df
        
    # If player_name already exists, ensure it's properly formatted
    if 'player_name' in df.columns:
        # Clean up any NaN or empty values
        df['player_name'] = df['player_name'].fillna('Unknown Player').astype(str)
        df['player_name'] = df['player_name'].str.strip()
        # Replace any empty strings with 'Unknown Player'
        df.loc[df['player_name'] == '', 'player_name'] = 'Unknown Player'
        return df
    
    # Create player_name from first_name and last_name
    if 'first_name' in df.columns and 'last_name' in df.columns:
        first_name = df['first_name'].fillna('').astype(str).str.strip()
        last_name = df['last_name'].fillna('').astype(str).str.strip()
        
        # Combine names with proper spacing
        df['player_name'] = (first_name + ' ' + last_name).str.strip()
        
        # Handle cases where both names are empty
        df.loc[df['player_name'] == '', 'player_name'] = 'Unknown Player'
        
        logger.info(f"Created player_name column for {len(df)} players")
        return df
    
    # Fallback: look for alternative name columns
    name_candidates = ['player', 'full_name', 'name', 'display_name']
    for candidate in name_candidates:
        if candidate in df.columns:
            df['player_name'] = df[candidate].fillna('Unknown Player').astype(str).str.strip()
            df.loc[df['player_name'] == '', 'player_name'] = 'Unknown Player'
            logger.info(f"Created player_name column from '{candidate}' for {len(df)} players")
            return df
    
    # Last resort: create generic player names
    df['player_name'] = [f'Player_{i+1}' for i in range(len(df))]
    logger.warning(f"No name columns found, created generic player_name for {len(df)} players")
    return df

def get_data_directory(data_type="raw"):
    """
    Get the path to a specific data directory.
    
    Args:
        data_type (str): Type of data directory ('raw' or 'processed')
        
    Returns:
        Path: Path object pointing to the requested directory
    """
    # Get the project root directory
    project_dir = Path(__file__).resolve().parent.parent
    
    if data_type.lower() == "raw":
        return project_dir / "data" / "raw"
    elif data_type.lower() == "processed":
        return project_dir / "data" / "processed"
    else:
        raise ValueError(f"Invalid data_type: {data_type}. Must be 'raw' or 'processed'.")

def get_raw_data_path(season, file_prefix="player_season"):
    """
    Get the path to a raw data file for a specific season.
    
    Args:
        season (int): NFL season year
        file_prefix (str): Prefix for the file name
        
    Returns:
        Path: Path object pointing to the raw data file
    """
    raw_dir = get_data_directory("raw")
    return raw_dir / f"{file_prefix}_{season}.parquet"

def get_cleaned_data_path(season, file_prefix="player_season_cleaned"):
    """
    Get the path to a cleaned data file for a specific season.
    
    Args:
        season (int): NFL season year
        file_prefix (str): Prefix for the file name
        
    Returns:
        Path: Path object pointing to the cleaned data file
    """
    processed_dir = get_data_directory("processed")
    return processed_dir / f"{file_prefix}_{season}.parquet"

def get_features_data_path(season, prediction_season=None, file_prefix="features_for"):
    """
    Get the path to a feature-engineered data file for a specific season.
    
    Args:
        season (int): NFL season year used for feature engineering
        prediction_season (int, optional): Season to predict. If None, defaults to season + 1
        file_prefix (str): Prefix for the file name
        
    Returns:
        Path: Path object pointing to the feature-engineered data file
    """
    if prediction_season is None:
        prediction_season = season + 1
        
    processed_dir = get_data_directory("processed")
    return processed_dir / f"{file_prefix}_{season}_predicting_{prediction_season}.parquet"

def load_raw_data(season, file_prefix="player_season"):
    """
    Load raw data for a specific season.
    
    Args:
        season (int): NFL season year
        file_prefix (str): Prefix for the file name
        
    Returns:
        pd.DataFrame: DataFrame containing the raw data
        
    Raises:
        FileNotFoundError: If the raw data file does not exist
    """
    file_path = get_raw_data_path(season, file_prefix)
    
    try:
        logger.info(f"Loading raw data for {season} season from {file_path}")
        df = pd.read_parquet(file_path)
        
        # Create player_name column from first_name and last_name if it doesn't exist
        df = ensure_player_name_column(df)
        
        
        return df
    except FileNotFoundError:
        logger.error(f"Raw data file not found: {file_path}")
        raise

def load_cleaned_data(season, file_prefix="player_season_cleaned"):
    """
    Load cleaned data for a specific season.
    
    Args:
        season (int): NFL season year
        file_prefix (str): Prefix for the file name
        
    Returns:
        pd.DataFrame: DataFrame containing the cleaned data
        
    Raises:
        FileNotFoundError: If the cleaned data file does not exist
    """
    file_path = get_cleaned_data_path(season, file_prefix)
    
    try:
        logger.info(f"Loading cleaned data for {season} season from {file_path}")
        return pd.read_parquet(file_path)
    except FileNotFoundError:
        logger.error(f"Cleaned data file not found: {file_path}")
        raise

def load_features_data(season, prediction_season=None, file_prefix="features_for"):
    """
    Load feature-engineered data for a specific season.
    
    Args:
        season (int): NFL season year used for feature engineering
        prediction_season (int, optional): Season to predict. If None, defaults to season + 1
        file_prefix (str): Prefix for the file name
        
    Returns:
        pd.DataFrame: DataFrame containing the feature-engineered data
        
    Raises:
        FileNotFoundError: If the feature-engineered data file does not exist
    """
    file_path = get_features_data_path(season, prediction_season, file_prefix)
    
    try:
        logger.info(f"Loading features for {season} season (predicting {prediction_season if prediction_season else season + 1}) from {file_path}")
        return pd.read_parquet(file_path)
    except FileNotFoundError:
        logger.error(f"Features data file not found: {file_path}")
        raise

def save_raw_data(df, season, file_prefix="player_season"):
    """
    Save raw data for a specific season.
    
    Args:
        df (pd.DataFrame): DataFrame containing the raw data
        season (int): NFL season year
        file_prefix (str): Prefix for the file name
        
    Returns:
        bool: True if the data was saved successfully, False otherwise
    """
    file_path = get_raw_data_path(season, file_prefix)
    
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        logger.info(f"Saving raw data for {season} season to {file_path}")
        df.to_parquet(file_path)
        return True
    except Exception as e:
        logger.error(f"Error saving raw data for {season} season: {e}")
        return False

def save_cleaned_data(df, season, file_prefix="player_season_cleaned"):
    """
    Save cleaned data for a specific season.
    
    Args:
        df (pd.DataFrame): DataFrame containing the cleaned data
        season (int): NFL season year
        file_prefix (str): Prefix for the file name
        
    Returns:
        bool: True if the data was saved successfully, False otherwise
    """
    file_path = get_cleaned_data_path(season, file_prefix)
    
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        logger.info(f"Saving cleaned data for {season} season to {file_path}")
        df.to_parquet(file_path)
        return True
    except Exception as e:
        logger.error(f"Error saving cleaned data for {season} season: {e}")
        return False

def save_features_data(df, season, prediction_season=None, file_prefix="features_for"):
    """
    Save feature-engineered data for a specific season.
    
    Args:
        df (pd.DataFrame): DataFrame containing the feature-engineered data
        season (int): NFL season year used for feature engineering
        prediction_season (int, optional): Season to predict. If None, defaults to season + 1
        file_prefix (str): Prefix for the file name
        
    Returns:
        bool: True if the data was saved successfully, False otherwise
    """
    file_path = get_features_data_path(season, prediction_season, file_prefix)
    
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        logger.info(f"Saving features for {season} season (predicting {prediction_season if prediction_season else season + 1}) to {file_path}")
        df.to_parquet(file_path)
        return True
    except Exception as e:
        logger.error(f"Error saving features for {season} season: {e}")
        return False

def get_available_seasons(data_type="raw", file_prefix=None):
    """
    Get a list of available seasons for a specific data type.
    
    Args:
        data_type (str): Type of data ('raw', 'cleaned', or 'features')
        file_prefix (str, optional): Prefix for the file name. If None, uses default prefix for the data type
        
    Returns:
        list: List of available seasons
    """
    if data_type.lower() == "raw":
        data_dir = get_data_directory("raw")
        if file_prefix is None:
            file_prefix = "player_season"
        pattern = f"{file_prefix}_*.parquet"
    elif data_type.lower() == "cleaned":
        data_dir = get_data_directory("processed")
        if file_prefix is None:
            file_prefix = "player_season_cleaned"
        pattern = f"{file_prefix}_*.parquet"
    elif data_type.lower() == "features":
        data_dir = get_data_directory("processed")
        if file_prefix is None:
            file_prefix = "features_for"
        pattern = f"{file_prefix}_*_predicting_*.parquet"
    else:
        raise ValueError(f"Invalid data_type: {data_type}. Must be 'raw', 'cleaned', or 'features'.")
    
    # Get all matching files
    files = list(data_dir.glob(pattern))
    
    if data_type.lower() in ["raw", "cleaned"]:
        # Extract seasons from file names
        seasons = []
        for file in files:
            try:
                season = int(file.stem.split("_")[-1])
                seasons.append(season)
            except (ValueError, IndexError):
                continue
    else:  # features
        # Extract seasons from file names
        seasons = []
        for file in files:
            try:
                parts = file.stem.split("_")
                season = int(parts[-3])  # Extract season from "features_for_YYYY_predicting_ZZZZ"
                seasons.append(season)
            except (ValueError, IndexError):
                continue
    
    return sorted(seasons)

def verify_data_grain(df, expected_grain_columns=None):
    """
    Verify that a DataFrame follows the expected data grain.
    
    Args:
        df (pd.DataFrame): DataFrame to verify
        expected_grain_columns (list, optional): List of columns that should uniquely identify each row.
            If None, defaults to ['player_id', 'season']
            
    Returns:
        bool: True if the DataFrame follows the expected grain, False otherwise
    """
    if expected_grain_columns is None:
        expected_grain_columns = ['player_id', 'season']
    
    # Check if all expected grain columns are in the DataFrame
    missing_columns = [col for col in expected_grain_columns if col not in df.columns]
    if missing_columns:
        logger.warning(f"Missing grain columns: {missing_columns}")
        return False
    
    # Check if the grain columns uniquely identify each row
    n_rows = len(df)
    n_unique_combinations = df[expected_grain_columns].drop_duplicates().shape[0]
    
    if n_rows != n_unique_combinations:
        logger.warning(f"Data grain violation: {n_rows} rows but only {n_unique_combinations} unique combinations of {expected_grain_columns}")
        return False
    
    return True
