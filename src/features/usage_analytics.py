"""
Usage Analytics for Fantasy Football

This module implements advanced usage metrics that complement opportunity metrics:
- Snap Count and Snap Share tracking
- Route Participation Rate for WR/TE  
- Usage trends and efficiency metrics
- High-leverage situation usage

These metrics help evaluate how teams are actually using players beyond just targets/carries.
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


class UsageAnalyticsCalculator:
    """Calculate advanced usage analytics for fantasy football players."""
    
    def __init__(self, season: int = None):
        """
        Initialize the calculator.
        
        Args:
            season: NFL season year. If None, uses config.INFERENCE_DATA_YEAR
        """
        self.season = season or config.INFERENCE_DATA_YEAR
        self.snap_data = None
        self.pbp_data = None
        
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
        
        # Player name column
        player_name_col = None
        for col in available_cols:
            if col.lower() in ['player_name', 'full_name', 'player', 'name']:
                player_name_col = col
                break
        mapping['player_name'] = player_name_col
        
        # Team column
        team_col = None
        for col in available_cols:
            if col.lower() in ['team', 'recent_team', 'posteam', 'current_team']:
                team_col = col
                break
        mapping['team'] = team_col
        
        # Games column
        games_col = None
        for col in available_cols:
            if col.lower() in ['games', 'games_played', 'g']:
                games_col = col
                break
        mapping['games'] = games_col
        
        return mapping
        
    def load_snap_count_data(self) -> pd.DataFrame:
        """
        Load snap count data from nfl_data_py.
        
        Returns:
            DataFrame with snap count data
        """
        logger.info(f"Loading snap count data for {self.season}")
        
        try:
            # Try to load snap counts from nfl_data_py
            snap_counts = nfl.import_snap_counts([self.season])
            
            if snap_counts.empty:
                logger.warning(f"No snap count data available for {self.season}")
                return pd.DataFrame()
            
            logger.info(f"Loaded snap counts for {len(snap_counts)} player-week records")
            self.snap_data = snap_counts
            return snap_counts
            
        except Exception as e:
            logger.error(f"Error loading snap count data: {e}")
            return pd.DataFrame()
    
    def calculate_snap_metrics(self, player_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate snap count and snap share metrics.
        
        Args:
            player_data: DataFrame with player stats
            
        Returns:
            DataFrame with snap metrics added
        """
        logger.info("Calculating snap count metrics")
        
        # Load snap data if not already loaded
        if self.snap_data is None:
            self.load_snap_count_data()
        
        if self.snap_data is None or self.snap_data.empty:
            logger.warning("No snap data available, adding empty snap metrics")
            player_data['total_snaps'] = 0
            player_data['snap_share'] = 0
            player_data['snaps_per_game'] = 0
            return player_data
        
        try:
            # Check what columns are actually available
            available_cols = self.snap_data.columns.tolist()
            logger.info(f"Available snap data columns: {available_cols}")
            
            # Use available columns with fallbacks
            snap_col = None
            pct_col = None
            player_col = None
            team_col = None
            
            # Find the right columns
            for col in available_cols:
                if 'snap' in col.lower() and 'offense' in col.lower():
                    snap_col = col
                elif 'pct' in col.lower() or 'percentage' in col.lower():
                    pct_col = col
                elif col.lower() in ['player', 'player_name', 'full_name']:
                    player_col = col
                elif col.lower() in ['team', 'recent_team', 'posteam']:
                    team_col = col
            
            if not all([player_col, team_col]):
                logger.warning("Missing required columns for snap aggregation")
                # Add empty columns and return
                player_data['total_snaps'] = 0
                player_data['snap_share'] = 0
                player_data['snaps_per_game'] = 0
                return player_data
            
            # Validate player_data has required columns
            required_cols_mapping = self._get_column_mapping(player_data)
            if not required_cols_mapping['player_name'] or not required_cols_mapping['team']:
                logger.warning("Player data missing required columns (player_name, team)")
                # Add empty columns and return
                player_data['total_snaps'] = 0
                player_data['snap_share'] = 0
                player_data['snaps_per_game'] = 0
                return player_data
            
            # Aggregate with available columns
            agg_dict = {}
            if snap_col:
                agg_dict[snap_col] = 'sum'
            if pct_col:
                agg_dict[pct_col] = 'mean'
            
            if not agg_dict:
                logger.warning("No usable snap columns found")
                # Add empty columns and return
                player_data['total_snaps'] = 0
                player_data['snap_share'] = 0  
                player_data['snaps_per_game'] = 0
                return player_data
            
            # Aggregate snap counts by player for the season
            snap_summary = self.snap_data.groupby([player_col, team_col]).agg(agg_dict).reset_index()
            
            # Rename columns to standard names
            new_cols = [player_col, team_col]
            if snap_col:
                new_cols.append('total_snaps')
            if pct_col:
                new_cols.append('avg_snap_share')
            
            snap_summary.columns = new_cols[:len(snap_summary.columns)]
            
            # Convert snap share to decimal (if it's in percentage form)
            if snap_summary['avg_snap_share'].max() > 1:
                snap_summary['avg_snap_share'] = snap_summary['avg_snap_share'] / 100
            
            # Calculate snaps per game using correct column names
            player_name_col = required_cols_mapping['player_name']
            team_col = required_cols_mapping['team']
            games_col = required_cols_mapping['games']
            
            if games_col and games_col in player_data.columns:
                merge_cols = [player_name_col, team_col, games_col]
                snap_summary = snap_summary.merge(
                    player_data[merge_cols].rename(columns={
                        player_name_col: 'player_name',
                        team_col: 'team',
                        games_col: 'games'
                    }), 
                    on=['player_name', 'team'], 
                    how='left'
                )
                
                snap_summary['snaps_per_game'] = np.where(
                    snap_summary['games'] > 0,
                    snap_summary['total_snaps'] / snap_summary['games'],
                    0
                )
            else:
                # No games data available, set snaps per game to 0
                snap_summary['snaps_per_game'] = 0
            
            # Merge with player data using correct column names
            result = player_data.merge(
                snap_summary[['player_name', 'team', 'total_snaps', 'avg_snap_share', 'snaps_per_game']].rename(columns={
                    'player_name': player_name_col,
                    'team': team_col
                }),
                on=[player_name_col, team_col],
                how='left'
            )
            
            # Fill missing values
            snap_columns = ['total_snaps', 'avg_snap_share', 'snaps_per_game']
            for col in snap_columns:
                result[col] = result[col].fillna(0)
            
            logger.info(f"Added snap metrics for {len(result)} players")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating snap metrics: {e}")
            # Add empty columns if calculation fails
            player_data['total_snaps'] = 0
            player_data['avg_snap_share'] = 0
            player_data['snaps_per_game'] = 0
            return player_data
    
    def calculate_usage_efficiency_metrics(self, player_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate usage efficiency metrics.
        
        Args:
            player_data: DataFrame with player stats and snap data
            
        Returns:
            DataFrame with usage efficiency metrics added
        """
        logger.info("Calculating usage efficiency metrics")
        
        result = player_data.copy()
        
        # Targets per snap (for pass catchers)
        if 'targets' in result.columns and 'total_snaps' in result.columns:
            result['targets_per_snap'] = np.where(
                result['total_snaps'] > 0,
                result['targets'] / result['total_snaps'],
                0
            )
        
        # Carries per snap (for RBs)  
        if 'carries' in result.columns and 'total_snaps' in result.columns:
            result['carries_per_snap'] = np.where(
                result['total_snaps'] > 0,
                result['carries'] / result['total_snaps'],
                0
            )
        
        # Fantasy points per snap
        if 'fantasy_points_ppr' in result.columns and 'total_snaps' in result.columns:
            result['fantasy_points_per_snap'] = np.where(
                result['total_snaps'] > 0,
                result['fantasy_points_ppr'] / result['total_snaps'],
                0
            )
        
        # Touch efficiency (touches per snap for skill position players)
        if all(col in result.columns for col in ['targets', 'carries', 'total_snaps']):
            result['total_touches'] = result['targets'] + result['carries']
            result['touches_per_snap'] = np.where(
                result['total_snaps'] > 0,
                result['total_touches'] / result['total_snaps'],
                0
            )
        
        # Snap utilization rate (how often player gets the ball when on field)
        if 'touches_per_snap' in result.columns:
            result['utilization_rate'] = np.clip(result['touches_per_snap'] * 100, 0, 100)
        
        logger.info(f"Calculated usage efficiency metrics for {len(result)} players")
        return result
    
    def calculate_route_participation_advanced(self, player_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate advanced route participation metrics using play-by-play data.
        
        Args:
            player_data: DataFrame with player stats
            
        Returns:
            DataFrame with route participation metrics added
        """
        logger.info("Calculating advanced route participation metrics")
        
        try:
            # Load play-by-play data for route analysis
            if self.pbp_data is None:
                pbp = nfl.import_pbp_data([self.season])
                self.pbp_data = pbp[pbp['play_type'] == 'pass'].copy()
            
            if self.pbp_data.empty:
                logger.warning("No play-by-play data available for route participation")
                player_data['route_participation_advanced'] = 0
                return player_data
            
            # Count total pass plays by team
            team_pass_plays = self.pbp_data.groupby('posteam').size().reset_index(name='team_pass_plays')
            
            # Count targets by player (this gives us routes where they were targeted)
            player_targets = self.pbp_data[self.pbp_data['receiver_player_name'].notna()].groupby([
                'receiver_player_name', 'posteam'
            ]).size().reset_index(name='player_targets_pbp')
            
            # Merge team totals
            route_data = player_targets.merge(
                team_pass_plays, 
                left_on='posteam',
                right_on='posteam',
                how='left'
            )
            
            # Estimate route participation (this is a rough approximation)
            # In reality, we'd need detailed route data to know exact participation
            route_data['estimated_routes'] = route_data['player_targets_pbp'] * 2.5  # Rough multiplier
            route_data['route_participation_rate'] = np.clip(
                route_data['estimated_routes'] / route_data['team_pass_plays'], 
                0, 1
            )
            
            # Merge with player data using correct column names
            cols_mapping = self._get_column_mapping(player_data)
            player_name_col = cols_mapping['player_name']
            team_col = cols_mapping['team']
            
            if player_name_col and team_col:
                result = player_data.merge(
                    route_data[['receiver_player_name', 'posteam', 'route_participation_rate']].rename(
                        columns={'receiver_player_name': player_name_col, 'posteam': team_col}
                    ),
                    on=[player_name_col, team_col],
                    how='left'
                )
                
                result['route_participation_advanced'] = result['route_participation_rate'].fillna(0)
                # Clean up temporary column
                if 'route_participation_rate' in result.columns:
                    result = result.drop(columns=['route_participation_rate'])
            else:
                logger.warning("Cannot merge route participation - missing player_name or team columns")
                player_data['route_participation_advanced'] = 0
                result = player_data
            
            logger.info(f"Calculated advanced route participation for {len(result)} players")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating route participation: {e}")
            player_data['route_participation_advanced'] = 0
            return player_data
    
    def calculate_situational_usage(self, player_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate situational usage metrics (red zone, goal line, 3rd down, etc.).
        
        Args:
            player_data: DataFrame with player stats
            
        Returns:
            DataFrame with situational usage metrics added
        """
        logger.info("Calculating situational usage metrics")
        
        try:
            # Load play-by-play data if not already loaded
            if self.pbp_data is None:
                pbp = nfl.import_pbp_data([self.season])
                self.pbp_data = pbp.copy()
            
            if self.pbp_data.empty:
                logger.warning("No play-by-play data for situational usage")
                # Add empty columns
                sit_columns = ['red_zone_usage', 'goal_line_usage', 'third_down_usage', 'two_minute_usage']
                for col in sit_columns:
                    player_data[col] = 0
                return player_data
            
            result = player_data.copy()
            
            # Red zone usage (already calculated in opportunity_metrics, but add share)
            red_zone_plays = self.pbp_data[self.pbp_data['yardline_100'] <= 20].copy()
            
            # Goal line usage (5 yards and closer)
            goal_line_plays = self.pbp_data[self.pbp_data['yardline_100'] <= 5].copy()
            
            # Third down usage
            third_down_plays = self.pbp_data[self.pbp_data['down'] == 3].copy()
            
            # Two-minute drill usage (last 2 minutes of each half)
            two_min_plays = self.pbp_data[
                ((self.pbp_data['qtr'] == 2) & (self.pbp_data['quarter_seconds_remaining'] <= 120)) |
                ((self.pbp_data['qtr'] == 4) & (self.pbp_data['quarter_seconds_remaining'] <= 120))
            ].copy()
            
            # Calculate usage rates for each situation
            situations = {
                'red_zone_usage': red_zone_plays,
                'goal_line_usage': goal_line_plays, 
                'third_down_usage': third_down_plays,
                'two_minute_usage': two_min_plays
            }
            
            for situation_name, situation_plays in situations.items():
                if not situation_plays.empty:
                    # Count player usage in this situation
                    receiver_usage = situation_plays[
                        (situation_plays['play_type'] == 'pass') & 
                        (situation_plays['receiver_player_name'].notna())
                    ].groupby(['receiver_player_name', 'posteam']).size().reset_index(name=f'{situation_name}_targets')
                    
                    rusher_usage = situation_plays[
                        (situation_plays['play_type'] == 'run') & 
                        (situation_plays['rusher_player_name'].notna())
                    ].groupby(['rusher_player_name', 'posteam']).size().reset_index(name=f'{situation_name}_carries')
                    
                    # Merge both
                    total_usage = receiver_usage.rename(columns={'receiver_player_name': 'player_name'}).merge(
                        rusher_usage.rename(columns={'rusher_player_name': 'player_name'}),
                        on=['player_name', 'posteam'],
                        how='outer'
                    ).fillna(0)
                    
                    total_usage[situation_name] = total_usage[f'{situation_name}_targets'] + total_usage[f'{situation_name}_carries']
                    
                    # Merge with result using correct column names
                    cols_mapping = self._get_column_mapping(result)
                    player_name_col = cols_mapping['player_name']
                    team_col = cols_mapping['team']
                    
                    if player_name_col and team_col:
                        result = result.merge(
                            total_usage[['player_name', 'posteam', situation_name]].rename(columns={
                                'player_name': player_name_col, 
                                'posteam': team_col
                            }),
                            on=[player_name_col, team_col],
                            how='left'
                        )
                        
                        result[situation_name] = result[situation_name].fillna(0)
                    else:
                        logger.warning(f"Cannot merge {situation_name} - missing player_name or team columns")
                        result[situation_name] = 0
                else:
                    result[situation_name] = 0
            
            logger.info(f"Calculated situational usage for {len(result)} players")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating situational usage: {e}")
            # Add empty columns if calculation fails
            sit_columns = ['red_zone_usage', 'goal_line_usage', 'third_down_usage', 'two_minute_usage']
            for col in sit_columns:
                player_data[col] = 0
            return player_data
    
    def calculate_all_usage_metrics(self, player_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all usage analytics for given player data.
        
        Args:
            player_data: DataFrame with basic player stats
            
        Returns:
            DataFrame with all usage analytics added
        """
        logger.info("Calculating all usage analytics")
        
        # Make a copy to avoid modifying original
        result = player_data.copy()
        
        # Calculate each metric set in sequence
        result = self.calculate_snap_metrics(result)
        result = self.calculate_usage_efficiency_metrics(result)
        result = self.calculate_route_participation_advanced(result)
        result = self.calculate_situational_usage(result)
        
        logger.info(f"Completed all usage analytics for {len(result)} players")
        return result


def get_usage_analytics_for_season(season: int, positions: List[str] = None) -> pd.DataFrame:
    """
    Get usage analytics for all players in a given season.
    
    Args:
        season: NFL season year
        positions: List of positions to include. If None, includes skill positions.
        
    Returns:
        DataFrame with player stats and usage analytics
    """
    logger.info(f"Getting usage analytics for {season} season")
    
    try:
        # Use our current data pipeline
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
            # Default to skill positions
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
        
        # Calculate usage analytics
        calculator = UsageAnalyticsCalculator(season)
        result = calculator.calculate_all_usage_metrics(player_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting usage analytics for {season}: {e}")
        return pd.DataFrame()


def validate_usage_metrics(data: pd.DataFrame) -> Dict[str, bool]:
    """
    Validate that usage metrics are within expected ranges.
    
    Args:
        data: DataFrame with usage metrics
        
    Returns:
        Dict with validation results
    """
    validation_results = {}
    
    # Check snap share is between 0 and 1
    if 'avg_snap_share' in data.columns:
        snap_share_valid = data['avg_snap_share'].between(0, 1).all()
        validation_results['snap_share_range'] = snap_share_valid
    
    # Check targets per snap is reasonable (should be < 1)
    if 'targets_per_snap' in data.columns:
        targets_per_snap_valid = data['targets_per_snap'].between(0, 1).all()
        validation_results['targets_per_snap_range'] = targets_per_snap_valid
    
    # Check non-negative snap counts
    if 'total_snaps' in data.columns:
        snaps_non_negative = (data['total_snaps'] >= 0).all()
        validation_results['snaps_non_negative'] = snaps_non_negative
    
    # Check route participation is between 0 and 1
    if 'route_participation_advanced' in data.columns:
        route_participation_valid = data['route_participation_advanced'].between(0, 1).all()
        validation_results['route_participation_range'] = route_participation_valid
    
    return validation_results


if __name__ == "__main__":
    # Test the usage analytics calculator
    print("🏈 Testing Usage Analytics Calculator")
    print("=" * 50)
    
    # Test with current season data
    test_season = config.INFERENCE_DATA_YEAR
    print(f"Testing with {test_season} season data")
    
    # Test with skill positions
    test_positions = ['RB', 'WR', 'TE']
    
    try:
        usage_data = get_usage_analytics_for_season(test_season, test_positions)
        
        if not usage_data.empty:
            print(f"\n✅ Successfully calculated usage analytics for {len(usage_data)} players")
            
            # Show sample of calculated metrics
            usage_cols = ['player_name', 'position', 'team', 'total_snaps', 'avg_snap_share', 
                         'targets_per_snap', 'utilization_rate', 'red_zone_usage']
            available_cols = [col for col in usage_cols if col in usage_data.columns]
            
            print(f"\nSample usage analytics:")
            print(usage_data[available_cols].head(10))
            
            # Show available usage metrics
            usage_metric_cols = [col for col in usage_data.columns if any(word in col.lower() 
                               for word in ['snap', 'usage', 'utilization', 'route', 'efficiency'])]
            print(f"\n📊 Available usage metrics: {len(usage_metric_cols)}")
            print(usage_metric_cols)
            
            # Validate metrics
            validation = validate_usage_metrics(usage_data)
            print(f"\n📊 Validation Results:")
            for metric, valid in validation.items():
                status = "✅" if valid else "❌"
                print(f"{status} {metric}: {valid}")
        else:
            print("❌ No data returned from usage analytics calculation")
            
    except Exception as e:
        print(f"❌ Error testing usage analytics: {e}")
        import traceback
        traceback.print_exc()