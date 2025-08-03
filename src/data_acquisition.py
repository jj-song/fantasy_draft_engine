"""
Data acquisition module for the Fantasy Football AI Draft Tool.

This module contains functions to fetch player statistics and information
from nfl_data_py and save them to the raw data directory.
"""

import os
import logging
import pandas as pd
import nfl_data_py as nfl
import sys
from pathlib import Path

# Add the project root to the path so we can import the config
sys.path.append(str(Path(__file__).parent.parent))
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(Path(__file__).parent.parent, 'fantasy_football.log'))
    ]
)
logger = logging.getLogger(__name__)


def fetch_player_season_stats(year, positions=None):
    """
    Fetch player statistics for a specific season.
    
    Args:
        year (int): The NFL season year to fetch data for
        positions (list, optional): List of positions to include. Defaults to config.POSITIONS.
    
    Returns:
        pandas.DataFrame: DataFrame containing player statistics for the specified season
    """
    if positions is None:
        positions = config.POSITIONS
        
    logger.info(f"Fetching player statistics for {year} season for positions: {positions}")
    
    try:
        # Fetch seasonal stats (includes passing, rushing, receiving stats)
        seasonal_stats = nfl.import_seasonal_data([year])
        
        # Fetch weekly stats to get more detailed information
        weekly_stats = nfl.import_weekly_data([year])
        
        # Aggregate weekly stats to get additional metrics not in seasonal data
        if not weekly_stats.empty:
            # Check which columns exist in the weekly data
            agg_dict = {}
            if 'rushing_fumbles' in weekly_stats.columns:
                agg_dict['rushing_fumbles'] = 'sum'
            if 'receiving_yac_yards' in weekly_stats.columns:
                agg_dict['receiving_yac_yards'] = 'sum'
            
            # Always count weeks as a proxy for games played
            agg_dict['week'] = 'count'  # Use 'week' which should always exist
            
            # Only proceed if we have columns to aggregate
            if agg_dict:
                weekly_agg = weekly_stats.groupby('player_id').agg(agg_dict).reset_index()
                # Rename the week count to weeks_played
                if 'week' in weekly_agg.columns:
                    weekly_agg.rename(columns={'week': 'weeks_played'}, inplace=True)
            else:
                weekly_agg = pd.DataFrame()
        else:
            weekly_agg = pd.DataFrame()
        
        # Fetch player information
        player_info = nfl.import_players()
        
        # Get roster information for the year to get accurate team data
        try:
            rosters = nfl.import_seasonal_rosters([year])
        except:
            logger.warning(f"Could not fetch roster data for {year}, using player info only")
            rosters = pd.DataFrame()
        
        logger.info(f"Successfully fetched raw data for {year} season")
        
        # Filter for relevant positions
        player_info = player_info[player_info['position'].isin(positions)]
        
        # Start with seasonal stats
        if not seasonal_stats.empty:
            # Merge with weekly aggregated stats if available
            if not weekly_agg.empty:
                seasonal_stats = pd.merge(
                    seasonal_stats,
                    weekly_agg,
                    on='player_id',
                    how='left'
                )
            
            # Merge with roster data if available to get team information
            if not rosters.empty:
                # Filter rosters for the relevant year
                year_rosters = rosters[rosters['season'] == year]
                
                # Merge with roster data
                seasonal_stats = pd.merge(
                    seasonal_stats,
                    year_rosters[['player_id', 'team', 'position', 'depth_chart_position']],
                    on='player_id',
                    how='left',
                    suffixes=('', '_roster')
                )
            
            # Finally, merge with player info to get biographical data
            # Map player_info columns to the ones we need
            player_columns = [
                'gsis_id', 'first_name', 'last_name', 'position', 'birth_date', 
                'college_name', 'entry_year', 'draftround', 'draft_number'
            ]
            
            # Check which columns exist in player_info
            available_columns = [col for col in player_columns if col in player_info.columns]
            
            # Create a mapping from player_id in seasonal stats to gsis_id in player info
            # First, check if we need to create this mapping
            if 'player_id' not in player_info.columns and 'gsis_id' in player_info.columns:
                # Merge on gsis_id instead of player_id
                merged_stats = pd.merge(
                    seasonal_stats,
                    player_info[available_columns],
                    left_on='player_id',  # player_id in seasonal stats
                    right_on='gsis_id',   # gsis_id in player info
                    how='left',
                    suffixes=('', '_info')
                )
            else:
                # If player_id exists in player_info, use it directly
                merged_stats = pd.merge(
                    seasonal_stats,
                    player_info[available_columns],
                    on='player_id',
                    how='left',
                    suffixes=('', '_info')
                )
            
            # Use position from player_info if not available in seasonal stats
            if 'position' in merged_stats.columns and 'position_info' in merged_stats.columns:
                merged_stats['position'] = merged_stats['position'].fillna(merged_stats['position_info'])
                merged_stats.drop('position_info', axis=1, inplace=True, errors='ignore')
            
            # Filter for players in the specified positions
            merged_stats = merged_stats[merged_stats['position'].isin(positions)]
            
            logger.info(f"Successfully merged stats for {year} season. Total players: {len(merged_stats)}")
            
            return merged_stats
        else:
            logger.warning(f"No seasonal stats found for {year}")
            return pd.DataFrame()
    
    except Exception as e:
        logger.error(f"Error fetching data for {year} season: {str(e)}")
        raise


def save_player_season_stats(df, year):
    """
    Save player statistics to a parquet file in the raw data directory.
    
    Args:
        df (pandas.DataFrame): DataFrame containing player statistics
        year (int): The NFL season year
    
    Returns:
        str: Path to the saved file
    """
    # Create the raw data directory if it doesn't exist
    raw_data_dir = os.path.join(Path(__file__).parent.parent, config.RAW_DATA_DIR)
    os.makedirs(raw_data_dir, exist_ok=True)
    
    # Define the output file path
    output_file = os.path.join(raw_data_dir, f"player_season_{year}.parquet")
    
    try:
        # Save the DataFrame to a parquet file
        df.to_parquet(output_file, index=False)
        logger.info(f"Successfully saved player statistics for {year} season to {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Error saving player statistics for {year} season: {str(e)}")
        raise


def fetch_and_save_historical_data(start_year=None, end_year=None, positions=None):
    """
    Fetch and save player statistics for a range of seasons.
    
    Args:
        start_year (int, optional): The first season to fetch data for. Defaults to config.DATA_START_YEAR.
        end_year (int, optional): The last season to fetch data for. Defaults to config.DATA_END_YEAR.
        positions (list, optional): List of positions to include. Defaults to config.POSITIONS.
    
    Returns:
        list: List of paths to the saved files
    """
    if start_year is None:
        start_year = config.DATA_START_YEAR
    if end_year is None:
        end_year = config.DATA_END_YEAR
    if positions is None:
        positions = config.POSITIONS
    
    logger.info(f"Fetching and saving player statistics for seasons {start_year} to {end_year}")
    
    saved_files = []
    
    for year in range(start_year, end_year + 1):
        try:
            logger.info(f"Processing season {year}...")
            df = fetch_player_season_stats(year, positions)
            
            # Only save if we have data
            if not df.empty:
                file_path = save_player_season_stats(df, year)
                saved_files.append(file_path)
                logger.info(f"Completed processing for season {year}")
            else:
                logger.warning(f"No data to save for season {year}")
        except Exception as e:
            logger.error(f"Failed to process season {year}: {str(e)}")
            # Continue with the next season even if this one fails
            continue
    
    logger.info(f"Completed fetching and saving player statistics for all seasons. Saved {len(saved_files)} files.")
    return saved_files


if __name__ == "__main__":
    # Example usage
    fetch_and_save_historical_data()
