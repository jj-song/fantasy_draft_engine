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

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
import config

# Configure logging
logger = logging.getLogger(__name__)

def get_current_roster_assignments(year=None):
    """
    Get current team assignments for all players from the most recent roster data.
    
    Args:
        year (int, optional): Year to get rosters for. Defaults to config.INFERENCE_DATA_YEAR.
    
    Returns:
        pd.DataFrame: DataFrame with player_id, current_team, position, player_name
    """
    if year is None:
        year = config.INFERENCE_DATA_YEAR
    
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
    Get the most recent season performance data for inference.
    
    Args:
        year (int, optional): Year to get performance for. Defaults to config.INFERENCE_DATA_YEAR.
    
    Returns:
        pd.DataFrame: DataFrame with current season statistics
    """
    if year is None:
        year = config.INFERENCE_DATA_YEAR
        
    logger.info(f"Fetching current season performance data for {year}")
    
    try:
        # Get current season stats
        from src.data_storage import load_raw_data
        
        try:
            # Try to load existing data first
            current_data = load_raw_data(year)
            logger.info(f"✅ Loaded existing {year} data: {len(current_data)} records")
        except FileNotFoundError:
            # Fetch fresh data if not available
            logger.info(f"Fetching fresh {year} data from nfl_data_py")
            current_data = nfl.import_seasonal_data([year])
            
            # Add player names if missing
            if 'player_name' not in current_data.columns and 'first_name' in current_data.columns:
                current_data['player_name'] = current_data['first_name'].astype(str) + ' ' + current_data['last_name'].astype(str)
            
            # Save for future use
            from src.data_storage import save_raw_data
            save_raw_data(current_data, year)
            logger.info(f"✅ Saved fresh {year} data: {len(current_data)} records")
        
        return current_data
        
    except Exception as e:
        logger.error(f"Error fetching current season performance: {e}")
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
        # Merge on player_id (most reliable) - INCLUDE POSITION
        # Use INNER join to only keep players with roster data (position-filtered)
        updated_data = data_df.merge(
            current_rosters_df[['player_id', 'current_team', 'player_name', 'position']],
            on='player_id',
            how='inner',
            suffixes=('_old', '_current')
        )
        
        # Use current team if available, fall back to original team
        if 'team' in updated_data.columns:
            updated_data['team_updated'] = updated_data['current_team'].fillna(updated_data['team'])
            updated_data['team'] = updated_data['team_updated']
            updated_data = updated_data.drop(columns=['team_updated', 'current_team'])
        else:
            updated_data['team'] = updated_data['current_team']
            updated_data = updated_data.drop(columns=['current_team'])
        
        # Update player names if we have better current data
        if 'player_name_current' in updated_data.columns:
            updated_data['player_name'] = updated_data['player_name_current'].fillna(
                updated_data.get('player_name_old', updated_data.get('player_name', ''))
            )
            updated_data = updated_data.drop(columns=[col for col in updated_data.columns 
                                                    if col.endswith('_old') or col.endswith('_current')])
        
        # Count updates
        if 'team' in data_df.columns:
            team_changes = (data_df['team'] != updated_data['team']).sum()
            logger.info(f"Updated {team_changes} player team assignments")
        
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
    results = {
        'current_year': current_year,
        'inference_year': config.INFERENCE_DATA_YEAR,
        'data_available': False,
        'roster_available': False,
        'freshness_status': 'unknown',
        'recommendations': []
    }
    
    try:
        # Check if we can access inference year data
        test_data = nfl.import_seasonal_data([config.INFERENCE_DATA_YEAR])
        if len(test_data) > 0:
            results['data_available'] = True
            logger.info(f"✅ {config.INFERENCE_DATA_YEAR} season data available: {len(test_data)} records")
        
        # Check roster data
        test_rosters = nfl.import_seasonal_rosters([config.INFERENCE_DATA_YEAR])
        if len(test_rosters) > 0:
            results['roster_available'] = True
            logger.info(f"✅ {config.INFERENCE_DATA_YEAR} roster data available: {len(test_rosters)} records")
        
        # Assess freshness
        year_gap = current_year - config.INFERENCE_DATA_YEAR
        if year_gap <= 1:
            results['freshness_status'] = 'current'
            logger.info(f"✅ Data is current (using {config.INFERENCE_DATA_YEAR} in {current_year})")
        elif year_gap == 2:
            results['freshness_status'] = 'slightly_outdated'
            results['recommendations'].append(f"Consider updating INFERENCE_DATA_YEAR to {current_year-1}")
            logger.warning(f"⚠️ Data is slightly outdated (using {config.INFERENCE_DATA_YEAR} in {current_year})")
        else:
            results['freshness_status'] = 'outdated'
            results['recommendations'].append(f"Update INFERENCE_DATA_YEAR to {current_year-1} or {current_year}")
            logger.error(f"❌ Data is outdated (using {config.INFERENCE_DATA_YEAR} in {current_year})")
        
    except Exception as e:
        logger.error(f"Error validating data freshness: {e}")
        results['recommendations'].append("Check nfl_data_py installation and network connectivity")
    
    return results

def create_current_inference_dataset(position=None):
    """
    Create a complete dataset for current inference with updated team assignments.
    
    Args:
        position (str, optional): Filter for specific position
    
    Returns:
        pd.DataFrame: Ready-to-use inference dataset with current teams
    """
    logger.info(f"Creating current inference dataset" + (f" for {position}" if position else ""))
    
    # Get current season performance
    current_performance = get_current_season_performance()
    if current_performance.empty:
        logger.error("No current performance data available")
        return pd.DataFrame()
    
    # Get current roster assignments  
    current_rosters = get_current_roster_assignments()
    if current_rosters.empty:
        logger.error("No current roster data available")
        return current_performance  # Return performance data without team updates
    
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
        logger.info(f"Final filter: {len(updated_data)} {position} players")
    
    # Remove any duplicate player_ids that might still exist
    if 'player_id' in updated_data.columns:
        before_dedup = len(updated_data)
        updated_data = updated_data.drop_duplicates(subset=['player_id'], keep='first')
        after_dedup = len(updated_data)
        if before_dedup != after_dedup:
            logger.warning(f"Removed {before_dedup - after_dedup} duplicate player_ids")
    
    logger.info(f"Created current inference dataset: {len(updated_data)} records")
    return updated_data

def print_team_movement_report():
    """
    Print a report of notable team movements between training and inference years.
    """
    logger.info("Generating team movement report")
    
    try:
        # Get training year rosters (2023)
        training_rosters = nfl.import_seasonal_rosters([config.TRAINING_DATA_END_YEAR])
        training_teams = training_rosters[['player_id', 'team', 'player_name']].drop_duplicates(subset=['player_id'], keep='last')
        
        # Get current rosters (2024)  
        current_rosters = get_current_roster_assignments()
        
        # Find movements
        merged = training_teams.merge(current_rosters, on='player_id', how='inner', suffixes=('_2023', '_2024'))
        movements = merged[merged['team'] != merged['current_team']]
        
        if len(movements) > 0:
            print(f"\n🔄 NOTABLE TEAM MOVEMENTS ({config.TRAINING_DATA_END_YEAR} → {config.INFERENCE_DATA_YEAR})")
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