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

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data_storage import ensure_player_name_column
from src.config import get_config

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
        positions (list, optional): List of positions to include. Defaults to ['QB', 'RB', 'WR', 'TE', 'K'].
    
    Returns:
        pandas.DataFrame: DataFrame containing player statistics for the specified season
    """
    if positions is None:
        config = get_config()
        positions = config.get('data.positions', ['QB', 'RB', 'WR', 'TE', 'K'])
        
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
        
        # ENHANCED DATA ACQUISITION: Fetch play-by-play data for advanced features
        logger.info(f"Fetching play-by-play data for {year} season...")
        try:
            pbp_data = nfl.import_pbp_data([year])
            
            if not pbp_data.empty:
                # Ensure player_name column exists for joining
                pbp_data = ensure_player_name_column(pbp_data)
                
                logger.info(f"Loaded {len(pbp_data)} play-by-play records for {year}")
                
                # Extract advanced receiving metrics from play-by-play
                pbp_receiving = pbp_data[
                    (pbp_data['play_type'] == 'pass') & 
                    (pbp_data['receiver_player_name'].notna()) &
                    (pbp_data['air_yards'].notna())
                ].copy()
                
                if not pbp_receiving.empty:
                    # Calculate advanced receiving metrics per player
                    pbp_agg = pbp_receiving.groupby('receiver_player_name').agg({
                        'air_yards': ['mean', 'sum', 'count'],
                        'yards_after_catch': ['mean', 'sum'],
                        'epa': 'mean',
                        'cp': 'mean',  # Completion probability (contested catch indicator)
                        'play_id': 'count'  # Total targets
                    }).reset_index()
                    
                    # Flatten column names
                    pbp_agg.columns = [
                        'player_name',
                        'air_yards_per_target', 'total_air_yards', 'total_targets_pbp',
                        'yac_per_reception', 'total_yac',
                        'epa_per_target',
                        'avg_completion_probability',
                        'pbp_target_count'
                    ]
                    
                    logger.info(f"Calculated advanced receiving metrics for {len(pbp_agg)} players")
                else:
                    pbp_agg = pd.DataFrame()
            else:
                pbp_agg = pd.DataFrame()
        except Exception as e:
            logger.warning(f"Could not fetch play-by-play data for {year}: {e}")
            pbp_agg = pd.DataFrame()
        
        # ENHANCED DATA ACQUISITION: Fetch snap count data for usage metrics
        logger.info(f"Fetching snap count data for {year} season...")
        try:
            snap_data = nfl.import_snap_counts([year])
            
            if not snap_data.empty:
                # Ensure player_name column exists for joining
                snap_data = ensure_player_name_column(snap_data)
                
                logger.info(f"Loaded {len(snap_data)} snap count records for {year}")
                
                # Aggregate snap counts by player for the season
                snap_agg = snap_data.groupby('player_name').agg({
                    'offense_snaps': 'sum',
                    'offense_pct': 'mean',
                    'defense_snaps': 'sum', 
                    'defense_pct': 'mean'
                }).reset_index()
                
                snap_agg.columns = [
                    'player_name',
                    'total_offense_snaps', 'avg_offense_snap_pct',
                    'total_defense_snaps', 'avg_defense_snap_pct'
                ]
                
                logger.info(f"Calculated snap metrics for {len(snap_agg)} players")
            else:
                snap_agg = pd.DataFrame()
        except Exception as e:
            logger.warning(f"Could not fetch snap count data for {year}: {e}")
            snap_agg = pd.DataFrame()
        
        # Fetch player information
        player_info = nfl.import_players()
        
        # Get roster information for the year to get accurate team data
        try:
            rosters = nfl.import_seasonal_rosters([year])
        except Exception as e:
            logger.warning(f"Could not fetch roster data for {year}: {str(e)}")
            logger.debug(f"Roster fetch error details: {type(e).__name__}")
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
            
            # ENHANCED MERGING: Add play-by-play data if available
            if not pbp_agg.empty:
                # Ensure player_name exists in merged_stats for joining
                merged_stats = ensure_player_name_column(merged_stats)
                
                logger.info(f"Merging play-by-play data: {len(pbp_agg)} players with advanced metrics")
                merged_stats = pd.merge(
                    merged_stats,
                    pbp_agg,
                    on='player_name',
                    how='left'
                )
                logger.info(f"Successfully merged play-by-play data")
            
            # ENHANCED MERGING: Add snap count data if available  
            if not snap_agg.empty:
                # Ensure player_name exists in merged_stats for joining
                merged_stats = ensure_player_name_column(merged_stats)
                
                logger.info(f"Merging snap count data: {len(snap_agg)} players with snap metrics")
                merged_stats = pd.merge(
                    merged_stats,
                    snap_agg,
                    on='player_name',
                    how='left'
                )
                logger.info(f"Successfully merged snap count data")
            
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
    config = get_config()
    raw_data_dir = os.path.join(Path(__file__).parent.parent, config.get('paths.raw_data_dir', 'data/raw'))
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
        start_year (int, optional): The first season to fetch data for. Defaults to 2010.
        end_year (int, optional): The last season to fetch data for. Defaults to 2024.
        positions (list, optional): List of positions to include. Defaults to ['QB', 'RB', 'WR', 'TE', 'K'].
    
    Returns:
        list: List of paths to the saved files
    """
    config = get_config()
    if start_year is None:
        start_year = config.get('data.data_start_year', 2010)
    if end_year is None:
        end_year = config.get('data.data_end_year', 2024)
    if positions is None:
        positions = config.get('data.positions', ['QB', 'RB', 'WR', 'TE', 'K'])
    
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
