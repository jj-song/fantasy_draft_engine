"""
Opportunity Metrics for Fantasy Football

This module implements industry-standard opportunity metrics used by major fantasy sites:
- Target Share
- Air Yards and Air Yards Share  
- WOPR (Weighted Opportunity Rating)
- aDOT (Average Depth of Target)
- YAC (Yards After Catch) efficiency

These metrics help evaluate player usage and opportunity independent of results.
"""

import pandas as pd
import numpy as np
import nfl_data_py as nfl
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sys

# Import local config
from .. import config

logger = logging.getLogger(__name__)


class OpportunityMetricsCalculator:
    """Calculate advanced opportunity metrics for fantasy football players."""
    
    def __init__(self, season: int = None):
        """
        Initialize the calculator.
        
        Args:
            season: NFL season year. If None, uses config.INFERENCE_DATA_YEAR
        """
        self.season = season or config.INFERENCE_DATA_YEAR
        self.pbp_data = None
        self.target_data = None
        self.team_totals = None
        
    def _get_column_mapping(self, data: pd.DataFrame) -> Dict[str, Optional[str]]:
        """
        Get mapping of standard column names to actual column names in the data.
        
        Args:
            data: DataFrame to examine
            
        Returns:
            Dict mapping standard names to actual column names (None if not found)
        """
        available_cols = data.columns.tolist()
        mapping = {}
        
        # Player name columns
        receiver_col = None
        for col in ['receiver_player_name', 'receiver', 'target_player', 'receiving_player']:
            if col in available_cols:
                receiver_col = col
                break
        mapping['receiver_player_name'] = receiver_col
        
        rusher_col = None
        for col in ['rusher_player_name', 'rusher', 'rushing_player']:
            if col in available_cols:
                rusher_col = col
                break
        mapping['rusher_player_name'] = rusher_col
        
        # Team columns
        team_col = None
        for col in ['posteam', 'team', 'offense_team', 'pos_team']:
            if col in available_cols:
                team_col = col
                break
        mapping['posteam'] = team_col
        
        # Yardage columns
        air_yards_col = None
        for col in ['air_yards', 'intended_air_yards', 'air_distance']:
            if col in available_cols:
                air_yards_col = col
                break
        mapping['air_yards'] = air_yards_col
        
        receiving_yards_col = None
        for col in ['receiving_yards', 'yards_gained', 'yards']:
            if col in available_cols:
                receiving_yards_col = col
                break
        mapping['receiving_yards'] = receiving_yards_col
        
        # Play type column
        play_type_col = None
        for col in ['play_type', 'type', 'play_category']:
            if col in available_cols:
                play_type_col = col
                break
        mapping['play_type'] = play_type_col
        
        return mapping
        
    def load_play_by_play_data(self) -> pd.DataFrame:
        """
        Load play-by-play data for air yards calculations.
        
        Returns:
            DataFrame with play-by-play data
        """
        logger.info(f"Loading play-by-play data for {self.season}")
        
        try:
            # Load play-by-play data from nfl_data_py
            pbp = nfl.import_pbp_data([self.season])
            
            if pbp.empty:
                logger.warning(f"No play-by-play data returned for {self.season}")
                return pd.DataFrame()
            
            # CRITICAL FIX: Ensure player_name column exists for joining
            from src.data_storage import ensure_player_name_column
            pbp = ensure_player_name_column(pbp)
            
            # ROBUST COLUMN MAPPING: Get actual column names
            col_mapping = self._get_column_mapping(pbp)
            play_type_col = col_mapping['play_type']
            air_yards_col = col_mapping['air_yards']
            receiver_col = col_mapping['receiver_player_name']
            
            if not all([play_type_col, air_yards_col, receiver_col]):
                logger.error(f"Missing critical PBP columns - play_type: {play_type_col}, air_yards: {air_yards_col}, receiver: {receiver_col}")
                logger.error(f"Available columns: {pbp.columns.tolist()}")
                return pd.DataFrame()
            
            # Filter to passing plays only using mapped column names
            passing_plays = pbp[
                (pbp[play_type_col] == 'pass') & 
                (pbp[air_yards_col].notna()) &
                (pbp[receiver_col].notna())
            ].copy()
            
            logger.info(f"Loaded {len(passing_plays)} passing plays with column mapping")
            logger.info(f"Using columns - play_type: {play_type_col}, air_yards: {air_yards_col}, receiver: {receiver_col}")
            
            self.pbp_data = passing_plays
            return passing_plays
            
        except Exception as e:
            logger.error(f"Error loading play-by-play data: {e}")
            return pd.DataFrame()
    
    def calculate_target_share(self, player_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Target Share = player targets / team total pass attempts per game.
        
        Args:
            player_data: DataFrame with player stats including targets and team
            
        Returns:
            DataFrame with target_share column added
        """
        logger.info("Calculating target share metrics")
        
        # Calculate team total pass attempts per game
        team_totals = player_data.groupby(['team', 'season']).agg({
            'targets': 'sum',
            'games': 'max'  # Assuming games represents team games played
        }).reset_index()
        
        team_totals['team_targets_per_game'] = team_totals['targets'] / team_totals['games']
        
        # Merge back with player data
        result = player_data.merge(
            team_totals[['team', 'season', 'team_targets_per_game']], 
            on=['team', 'season'], 
            how='left'
        )
        
        # Calculate individual target share
        result['target_share'] = np.where(
            result['team_targets_per_game'] > 0,
            result['targets'] / result['team_targets_per_game'] / result['games'],
            0
        )
        
        # Cap at 100% (shouldn't happen but safety check)
        result['target_share'] = np.clip(result['target_share'], 0, 1.0)
        
        logger.info(f"Calculated target share for {len(result)} players")
        return result
    
    def calculate_air_yards_metrics(self, player_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Air Yards, Air Yards Share, and aDOT from play-by-play data.
        
        Args:
            player_data: DataFrame with player stats
            
        Returns:
            DataFrame with air yards metrics added
        """
        logger.info("Calculating air yards metrics")
        
        if self.pbp_data is None:
            self.load_play_by_play_data()
        
        if self.pbp_data.empty:
            logger.warning("No play-by-play data available, skipping air yards calculations")
            # Add empty columns
            player_data['total_air_yards'] = 0
            player_data['air_yards_share'] = 0
            player_data['adot'] = 0
            player_data['yac_per_target'] = 0
            return player_data
        
        # ROBUST COLUMN MAPPING: Get actual column names from PBP data
        col_mapping = self._get_column_mapping(self.pbp_data)
        receiver_col = col_mapping['receiver_player_name']
        team_col = col_mapping['posteam']
        air_yards_col = col_mapping['air_yards']
        receiving_yards_col = col_mapping['receiving_yards']
        
        if not all([receiver_col, team_col, air_yards_col]):
            logger.error(f"Missing required columns for air yards calculation - receiver: {receiver_col}, team: {team_col}, air_yards: {air_yards_col}")
            # Add empty columns and return
            player_data['total_air_yards'] = 0
            player_data['air_yards_share'] = 0
            player_data['adot'] = 0
            player_data['yac_per_target'] = 0
            return player_data
        
        # Aggregate air yards by player using mapped column names
        agg_dict = {
            air_yards_col: ['sum', 'mean', 'count']
        }
        if receiving_yards_col:
            agg_dict[receiving_yards_col] = 'sum'
        
        air_yards_summary = self.pbp_data.groupby([receiver_col, team_col]).agg(agg_dict).reset_index()
        
        # Flatten column names with fallback for missing receiving yards
        if receiving_yards_col:
            air_yards_summary.columns = [
                'player_name', 'team', 'total_air_yards', 'adot', 'total_targets', 'receiving_yards'
            ]
        else:
            air_yards_summary.columns = [
                'player_name', 'team', 'total_air_yards', 'adot', 'total_targets'
            ]
            air_yards_summary['receiving_yards'] = 0  # Default to 0 if no receiving yards column
        
        # Check if we have any data after aggregation
        if air_yards_summary.empty:
            logger.warning("No air yards data after aggregation, adding empty columns")
            player_data['total_air_yards'] = 0
            player_data['air_yards_share'] = 0
            player_data['adot'] = 0
            player_data['yac_per_target'] = 0
            return player_data
        
        # Calculate team air yards totals using mapped column names
        team_air_yards = self.pbp_data.groupby(team_col)[air_yards_col].sum().reset_index()
        team_air_yards.columns = ['team', 'team_total_air_yards']
        
        # Merge team totals
        air_yards_summary = air_yards_summary.merge(team_air_yards, on='team', how='left')
        
        # Calculate air yards share
        air_yards_summary['air_yards_share'] = np.where(
            air_yards_summary['team_total_air_yards'] > 0,
            air_yards_summary['total_air_yards'] / air_yards_summary['team_total_air_yards'],
            0
        )
        
        # Calculate YAC efficiency
        air_yards_summary['yac'] = air_yards_summary['receiving_yards'] - air_yards_summary['total_air_yards']
        air_yards_summary['yac_per_target'] = np.where(
            air_yards_summary['total_targets'] > 0,
            air_yards_summary['yac'] / air_yards_summary['total_targets'],
            0
        )
        
        # Merge with player data using flexible column matching
        player_data_cols = self._get_column_mapping(player_data)
        player_name_col = player_data_cols.get('player_name', 'player_name')  # Default to 'player_name'
        player_team_col = player_data_cols.get('team', 'team')  # Default to 'team'
        
        # Check if required columns exist in player_data
        if player_name_col not in player_data.columns or player_team_col not in player_data.columns:
            logger.warning(f"Cannot merge air yards data - player_data missing columns: {player_name_col}, {player_team_col}")
            # Add empty columns and return
            player_data['total_air_yards'] = 0
            player_data['air_yards_share'] = 0
            player_data['adot'] = 0
            player_data['yac_per_target'] = 0
            return player_data
        
        # Merge with actual column names
        result = player_data.merge(
            air_yards_summary[['player_name', 'team', 'total_air_yards', 'air_yards_share', 'adot', 'yac_per_target']].rename(columns={
                'player_name': player_name_col,
                'team': player_team_col
            }),
            on=[player_name_col, player_team_col],
            how='left'
        )
        
        # Fill missing values and ensure columns exist
        air_yards_cols = ['total_air_yards', 'air_yards_share', 'adot', 'yac_per_target']
        for col in air_yards_cols:
            if col not in result.columns:
                result[col] = 0  # Add missing column with default values
            else:
                result[col] = result[col].fillna(0)
        
        logger.info(f"Calculated air yards metrics for {len(result)} players")
        return result
    
    def calculate_wopr(self, player_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate WOPR (Weighted Opportunity Rating).
        
        WOPR = (1.5 × target_share + 0.7 × air_yards_share) / 2.2
        
        Args:
            player_data: DataFrame with target_share and air_yards_share columns
            
        Returns:
            DataFrame with wopr column added
        """
        logger.info("Calculating WOPR (Weighted Opportunity Rating)")
        
        # Ensure required columns exist
        if 'target_share' not in player_data.columns:
            logger.warning("target_share not found, calculating first")
            player_data = self.calculate_target_share(player_data)
            
        if 'air_yards_share' not in player_data.columns:
            logger.warning("air_yards_share not found, calculating first")
            player_data = self.calculate_air_yards_metrics(player_data)
        
        # Calculate WOPR
        player_data['wopr'] = (
            (1.5 * player_data['target_share']) + 
            (0.7 * player_data['air_yards_share'])
        ) / 2.2
        
        # Cap at reasonable bounds
        player_data['wopr'] = np.clip(player_data['wopr'], 0, 1.0)
        
        logger.info(f"Calculated WOPR for {len(player_data)} players")
        return player_data
    
    def calculate_red_zone_opportunities(self, player_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate red zone opportunities from play-by-play data.
        
        Args:
            player_data: DataFrame with player stats
            
        Returns:
            DataFrame with red zone metrics added
        """
        logger.info("Calculating red zone opportunities")
        
        if self.pbp_data is None:
            self.load_play_by_play_data()
        
        if self.pbp_data.empty:
            logger.warning("No play-by-play data available, skipping red zone calculations")
            player_data['red_zone_targets'] = 0
            player_data['red_zone_carries'] = 0
            player_data['red_zone_opportunities'] = 0
            return player_data
        
        try:
            # ROBUST COLUMN CHECKING: Find yardline column for red zone calculations
            available_cols = self.pbp_data.columns.tolist()
            yardline_col = None
            for col in ['yardline_100', 'yardline', 'yard_line', 'field_position']:
                if col in available_cols:
                    yardline_col = col
                    break
            
            if yardline_col:
                # Filter to red zone plays (20 yards or less from goal line)
                red_zone_plays = self.pbp_data[self.pbp_data[yardline_col] <= 20].copy()
                
                if not red_zone_plays.empty:
                    # ROBUST COLUMN MAPPING: Get actual column names for red zone calculations
                    rz_col_mapping = self._get_column_mapping(red_zone_plays)
                    play_type_col = rz_col_mapping['play_type']
                    receiver_col = rz_col_mapping['receiver_player_name']
                    rusher_col = rz_col_mapping['rusher_player_name']
                    team_col = rz_col_mapping['posteam']
                    
                    # Red zone targets (passing plays)
                    if play_type_col and receiver_col and team_col:
                        rz_targets = red_zone_plays[
                            (red_zone_plays[play_type_col] == 'pass') &
                            (red_zone_plays[receiver_col].notna())
                        ].groupby([receiver_col, team_col]).size().reset_index(name='red_zone_targets')
                        rz_targets.columns = ['player_name', 'team', 'red_zone_targets']
                    else:
                        logger.warning(f"Missing columns for red zone targets - play_type: {play_type_col}, receiver: {receiver_col}, team: {team_col}")
                        rz_targets = pd.DataFrame()
                    
                    # Red zone carries (rushing plays) 
                    if play_type_col and rusher_col and team_col:
                        rz_carries = red_zone_plays[
                            (red_zone_plays[play_type_col] == 'run') &
                            (red_zone_plays[rusher_col].notna())
                        ].groupby([rusher_col, team_col]).size().reset_index(name='red_zone_carries')
                        rz_carries.columns = ['player_name', 'team', 'red_zone_carries']
                    else:
                        logger.warning(f"Missing columns for red zone carries - play_type: {play_type_col}, rusher: {rusher_col}, team: {team_col}")
                        rz_carries = pd.DataFrame()
                else:
                    logger.info("No red zone plays found in filtered data")
                    rz_targets = pd.DataFrame()
                    rz_carries = pd.DataFrame()
            else:
                logger.warning("No yardline column found for red zone calculations, skipping red zone opportunities")
                red_zone_plays = pd.DataFrame()
                rz_targets = pd.DataFrame()
                rz_carries = pd.DataFrame()
            
            # Get player data column mapping for merging
            player_cols_mapping = self._get_column_mapping(player_data)
            player_name_col = player_cols_mapping.get('player_name', 'player_name')
            player_team_col = player_cols_mapping.get('team', 'team')
            
            # Check if required columns exist in player_data
            if player_name_col not in player_data.columns or player_team_col not in player_data.columns:
                logger.warning(f"Cannot merge red zone data - player_data missing columns: {player_name_col}, {player_team_col}")
                # Add empty columns and return
                player_data['red_zone_targets'] = 0
                player_data['red_zone_carries'] = 0
                player_data['red_zone_opportunities'] = 0
                return player_data
            
            result = player_data.copy()
            
            # Merge red zone targets if available
            if not rz_targets.empty:
                result = result.merge(
                    rz_targets.rename(columns={'player_name': player_name_col, 'team': player_team_col}),
                    on=[player_name_col, player_team_col],
                    how='left'
                )
            else:
                result['red_zone_targets'] = 0
            
            # Merge red zone carries if available
            if not rz_carries.empty:
                result = result.merge(
                    rz_carries.rename(columns={'player_name': player_name_col, 'team': player_team_col}),
                    on=[player_name_col, player_team_col],
                    how='left'
                )
            else:
                result['red_zone_carries'] = 0
            
            # Fill missing values and calculate total opportunities
            result['red_zone_targets'] = result['red_zone_targets'].fillna(0)
            result['red_zone_carries'] = result['red_zone_carries'].fillna(0)
            result['red_zone_opportunities'] = result['red_zone_targets'] + result['red_zone_carries']
            
            logger.info(f"Calculated red zone opportunities for {len(result)} players")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating red zone opportunities: {e}")
            # Return with zero values if calculation fails
            player_data['red_zone_targets'] = 0
            player_data['red_zone_carries'] = 0
            player_data['red_zone_opportunities'] = 0
            return player_data
    
    def calculate_all_opportunity_metrics(self, player_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all opportunity metrics for given player data.
        
        Args:
            player_data: DataFrame with basic player stats
            
        Returns:
            DataFrame with all opportunity metrics added
        """
        logger.info("Calculating all opportunity metrics")
        
        # Make a copy to avoid modifying original
        result = player_data.copy()
        
        # Calculate each metric in sequence
        result = self.calculate_target_share(result)
        result = self.calculate_air_yards_metrics(result)
        result = self.calculate_wopr(result)
        result = self.calculate_red_zone_opportunities(result)
        
        # Add derived efficiency metrics
        result['targets_per_game'] = np.where(
            result['games'] > 0,
            result['targets'] / result['games'],
            0
        )
        
        result['air_yards_per_target'] = np.where(
            result['targets'] > 0,
            result['total_air_yards'] / result['targets'],
            0
        )
        
        logger.info(f"Completed all opportunity metrics for {len(result)} players")
        return result
    
    def enhance_opportunity_metrics(self, player_data: pd.DataFrame) -> pd.DataFrame:
        """
        Enhance existing opportunity metrics data with additional calculations.
        
        This method works with data that already has some opportunity metrics
        (like from nfl_data_py) and adds missing industry-standard metrics.
        
        Args:
            player_data: DataFrame with existing player stats and some opportunity metrics
            
        Returns:
            DataFrame with enhanced opportunity metrics
        """
        logger.info("Enhancing existing opportunity metrics")
        
        # Make a copy to avoid modifying original
        result = player_data.copy()
        
        # Check what opportunity metrics already exist
        existing_metrics = [col for col in result.columns if col in [
            'target_share', 'air_yards_share', 'wopr_x', 'wopr_y', 'receiving_air_yards'
        ]]
        logger.info(f"Found existing opportunity metrics: {existing_metrics}")
        
        # Log available columns for debugging
        air_yards_related = [col for col in result.columns if 'air' in col.lower()]
        logger.info(f"Air yards related columns: {air_yards_related}")
        
        # Calculate missing metrics
        
        # 1. aDOT (Average Depth of Target) if not present
        if 'adot' not in result.columns:
            # Calculate from existing receiving_air_yards if available
            if 'receiving_air_yards' in result.columns and 'targets' in result.columns:
                result['adot'] = np.where(
                    result['targets'] > 0,
                    result['receiving_air_yards'] / result['targets'],
                    0
                )
                logger.info("Calculated aDOT from existing air yards data")
            else:
                logger.info("Calculating aDOT from play-by-play data")
                result = self.calculate_air_yards_metrics(result)
            
        # 2. Enhanced WOPR if we only have basic versions
        if 'wopr_enhanced' not in result.columns:
            # Use existing target_share and air_yards_share if available
            if 'target_share' in result.columns and 'air_yards_share' in result.columns:
                result['wopr_enhanced'] = (
                    (1.5 * result['target_share']) + 
                    (0.7 * result['air_yards_share'])
                ) / 2.2
                logger.info("Calculated enhanced WOPR from existing metrics")
            else:
                # Calculate from scratch
                logger.info("Calculating WOPR from scratch")
                result = self.calculate_wopr(result)
                
        # 3. Red zone opportunities
        if 'red_zone_opportunities' not in result.columns:
            result = self.calculate_red_zone_opportunities(result)
            
        # 4. Additional derived metrics
        result['targets_per_game'] = np.where(
            result['games'] > 0,
            result['targets'] / result['games'],
            0
        )
        
        # 5. YAC efficiency metrics
        if 'yac_per_target' not in result.columns:
            # Calculate YAC from receiving yards and air yards if available
            if 'receiving_air_yards' in result.columns and 'receiving_yards' in result.columns:
                result['yac'] = result['receiving_yards'] - result['receiving_air_yards']
                result['yac_per_target'] = np.where(
                    result['targets'] > 0,
                    result['yac'] / result['targets'],
                    0
                )
            else:
                result['yac_per_target'] = 0
                
        # 6. High-value touches (red zone + 3rd down + 2-minute drill)
        # For now, approximate using red zone opportunities since we'd need play-by-play for full calculation
        if 'high_value_touches' not in result.columns:
            result['high_value_touches'] = result.get('red_zone_opportunities', 0)
            
        # 7. Route participation rate (for WR/TE)
        if 'route_participation' not in result.columns:
            # Approximate using targets and team pass attempts
            # This is a simplified version - full calculation would need route data
            if 'target_share' in result.columns:
                result['route_participation'] = np.clip(result['target_share'] * 3, 0, 1)  # Rough approximation
            else:
                result['route_participation'] = 0
                
        # 8. Air yards per target (aDOT)
        if 'air_yards_per_target' not in result.columns:
            if 'receiving_air_yards' in result.columns:
                result['air_yards_per_target'] = np.where(
                    result['targets'] > 0,
                    result['receiving_air_yards'] / result['targets'],
                    0
                )
            else:
                result['air_yards_per_target'] = result.get('adot', 0)
        
        # 9. Market share metrics (percentage of team's opportunities)
        if 'team_target_market_share' not in result.columns:
            team_targets = result.groupby('team')['targets'].sum().reset_index()
            team_targets.columns = ['team', 'team_total_targets']
            result = result.merge(team_targets, on='team', how='left')
            result['team_target_market_share'] = np.where(
                result['team_total_targets'] > 0,
                result['targets'] / result['team_total_targets'],
                0
            )
            
        logger.info(f"Enhanced opportunity metrics for {len(result)} players")
        return result


def get_opportunity_metrics_for_season(season: int, positions: List[str] = None) -> pd.DataFrame:
    """
    Get opportunity metrics for all players in a given season.
    
    Args:
        season: NFL season year
        positions: List of positions to include (e.g., ['WR', 'TE']). If None, includes all.
        
    Returns:
        DataFrame with player stats and opportunity metrics
    """
    logger.info(f"Getting opportunity metrics for {season} season")
    
    try:
        # Use our current data pipeline which includes position and team data
        from src.current_data_pipeline import create_current_inference_dataset
        
        if positions:
            # Get data for each position and combine
            all_data = []
            for position in positions:
                pos_data = create_current_inference_dataset(position)
                if not pos_data.empty:
                    all_data.append(pos_data)
            
            if all_data:
                player_data = pd.concat(all_data, ignore_index=True)
            else:
                logger.error(f"No data found for positions {positions}")
                return pd.DataFrame()
        else:
            # Get all positions - this would require iterating through all positions
            # For now, default to skill positions
            all_positions = ['QB', 'RB', 'WR', 'TE'] 
            all_data = []
            for position in all_positions:
                pos_data = create_current_inference_dataset(position)
                if not pos_data.empty:
                    all_data.append(pos_data)
            
            if all_data:
                player_data = pd.concat(all_data, ignore_index=True)
            else:
                logger.error(f"No data found for any positions")
                return pd.DataFrame()
        
        # Calculate additional opportunity metrics (enhance what's already there)
        calculator = OpportunityMetricsCalculator(season)
        result = calculator.enhance_opportunity_metrics(player_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting opportunity metrics for {season}: {e}")
        return pd.DataFrame()


def validate_opportunity_metrics(data: pd.DataFrame) -> Dict[str, bool]:
    """
    Validate that opportunity metrics are within expected ranges.
    
    Args:
        data: DataFrame with opportunity metrics
        
    Returns:
        Dict with validation results
    """
    validation_results = {}
    
    # Check target share is between 0 and 1
    if 'target_share' in data.columns:
        target_share_valid = data['target_share'].between(0, 1).all()
        validation_results['target_share_range'] = target_share_valid
        
    # Check air yards share is between 0 and 1
    if 'air_yards_share' in data.columns:
        air_yards_share_valid = data['air_yards_share'].between(0, 1).all()
        validation_results['air_yards_share_range'] = air_yards_share_valid
        
    # Check WOPR is between 0 and 1
    if 'wopr' in data.columns:
        wopr_valid = data['wopr'].between(0, 1).all()
        validation_results['wopr_range'] = wopr_valid
        
    # Check for reasonable aDOT values (typically -5 to 25 yards)
    if 'adot' in data.columns:
        adot_valid = data['adot'].between(-5, 25).all()
        validation_results['adot_range'] = adot_valid
        
    # Check no negative red zone opportunities
    if 'red_zone_opportunities' in data.columns:
        rz_valid = (data['red_zone_opportunities'] >= 0).all()
        validation_results['red_zone_non_negative'] = rz_valid
    
    return validation_results


if __name__ == "__main__":
    # Test the opportunity metrics calculator
    print("🏈 Testing Opportunity Metrics Calculator")
    print("=" * 50)
    
    # Test with current season data
    test_season = config.INFERENCE_DATA_YEAR
    print(f"Testing with {test_season} season data")
    
    # Test with WR/TE positions (most relevant for these metrics)
    test_positions = ['WR', 'TE']
    
    try:
        metrics_data = get_opportunity_metrics_for_season(test_season, test_positions)
        
        if not metrics_data.empty:
            print(f"\n✅ Successfully calculated metrics for {len(metrics_data)} players")
            
            # Show sample of calculated metrics
            metric_cols = ['player_name', 'position', 'team', 'targets', 'target_share', 
                          'air_yards_share', 'wopr', 'adot', 'red_zone_opportunities']
            available_cols = [col for col in metric_cols if col in metrics_data.columns]
            
            print(f"\nSample opportunity metrics:")
            print(metrics_data[available_cols].head(10))
            
            # Validate metrics
            validation = validate_opportunity_metrics(metrics_data)
            print(f"\n📊 Validation Results:")
            for metric, valid in validation.items():
                status = "✅" if valid else "❌"
                print(f"{status} {metric}: {valid}")
        else:
            print("❌ No data returned from opportunity metrics calculation")
            
    except Exception as e:
        print(f"❌ Error testing opportunity metrics: {e}")
        import traceback
        traceback.print_exc()