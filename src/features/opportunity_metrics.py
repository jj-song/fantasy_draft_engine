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

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))
import config

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
            
            # Filter to passing plays only
            passing_plays = pbp[
                (pbp['play_type'] == 'pass') & 
                (pbp['air_yards'].notna()) &
                (pbp['receiver_player_name'].notna())
            ].copy()
            
            logger.info(f"Loaded {len(passing_plays)} passing plays")
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
            player_data['air_yards'] = 0
            player_data['air_yards_share'] = 0
            player_data['adot'] = 0
            return player_data
        
        # Aggregate air yards by player
        air_yards_summary = self.pbp_data.groupby(['receiver_player_name', 'posteam']).agg({
            'air_yards': ['sum', 'mean', 'count'],
            'receiving_yards': 'sum'
        }).reset_index()
        
        # Flatten column names
        air_yards_summary.columns = [
            'player_name', 'team', 'total_air_yards', 'adot', 'total_targets', 'receiving_yards'
        ]
        
        # Calculate team air yards totals
        team_air_yards = self.pbp_data.groupby('posteam')['air_yards'].sum().reset_index()
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
        
        # Merge with player data
        result = player_data.merge(
            air_yards_summary[['player_name', 'team', 'total_air_yards', 'air_yards_share', 'adot', 'yac_per_target']],
            on=['player_name', 'team'],
            how='left'
        )
        
        # Fill missing values
        air_yards_cols = ['total_air_yards', 'air_yards_share', 'adot', 'yac_per_target']
        for col in air_yards_cols:
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
            # Filter to red zone plays (20 yards or less from goal line)
            red_zone_plays = self.pbp_data[self.pbp_data['yardline_100'] <= 20].copy()
            
            # Red zone targets (passing plays)
            rz_targets = red_zone_plays[
                (red_zone_plays['play_type'] == 'pass') &
                (red_zone_plays['receiver_player_name'].notna())
            ].groupby(['receiver_player_name', 'posteam']).size().reset_index(name='red_zone_targets')
            
            # Red zone carries (rushing plays) 
            rz_carries = red_zone_plays[
                (red_zone_plays['play_type'] == 'run') &
                (red_zone_plays['rusher_player_name'].notna())
            ].groupby(['rusher_player_name', 'posteam']).size().reset_index(name='red_zone_carries')
            
            # Merge red zone targets
            result = player_data.merge(
                rz_targets.rename(columns={'receiver_player_name': 'player_name', 'posteam': 'team'}),
                on=['player_name', 'team'],
                how='left'
            )
            
            # Merge red zone carries  
            result = result.merge(
                rz_carries.rename(columns={'rusher_player_name': 'player_name', 'posteam': 'team'}),
                on=['player_name', 'team'],
                how='left'
            )
            
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
            'target_share', 'air_yards_share', 'wopr_x', 'wopr_y'
        ]]
        logger.info(f"Found existing opportunity metrics: {existing_metrics}")
        
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