"""
Matchup Feature Integrator for Fantasy Football

This module integrates matchup intelligence features with existing position-specific features
to create comprehensive player projections that account for:

- Schedule strength and opponent defensive quality
- Weather and environmental factors  
- Stadium characteristics and venue effects
- Game context and situational factors
- Historical matchup trends

The integrator enhances existing features by adding matchup-derived metrics
that can be used alongside traditional player performance features in ML models.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import sys
from datetime import datetime, timedelta
from dataclasses import dataclass

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from .. import config

# Import our matchup intelligence modules (using local imports)
from .matchup_analysis import MatchupAnalysisEngine
from .schedule_strength import ScheduleStrengthCalculator
# TODO: Implement weather and stadium data in microservices
# from .weather_integration import WeatherIntegrator
# from .stadium_data import StadiumDatabase

logger = logging.getLogger(__name__)


@dataclass 
class MatchupFeatureConfig:
    """Configuration for matchup feature integration."""
    include_schedule_strength: bool = True
    include_environmental_factors: bool = True
    include_situational_adjustments: bool = True
    weeks_ahead_sos: int = 4
    season_for_features: int = 2024
    cache_matchup_data: bool = True


class MatchupFeatureIntegrator:
    """
    Integrates matchup intelligence features with existing player features.
    
    This class enhances traditional player performance features by adding
    matchup-aware metrics that account for opponent strength, environmental
    conditions, and situational factors.
    """
    
    def __init__(self, config: MatchupFeatureConfig = None):
        """
        Initialize the matchup feature integrator.
        
        Args:
            config: Configuration for feature integration
        """
        self.config = config or MatchupFeatureConfig()
        self.season = self.config.season_for_features
        
        # Initialize matchup intelligence components
        self.matchup_engine = MatchupAnalysisEngine(season=self.season)
        self.sos_calculator = ScheduleStrengthCalculator(current_season=self.season)
        self.weather_integrator = WeatherIntegrator()
        self.stadium_database = StadiumDatabase()
        
        # Cache for computed matchup features
        self.feature_cache = {}
        
        logger.info(f"Initialized MatchupFeatureIntegrator for season {self.season}")
    
    def integrate_matchup_features(
        self,
        player_features_df: pd.DataFrame,
        schedule_df: pd.DataFrame = None,
        weeks_to_analyze: List[int] = None
    ) -> pd.DataFrame:
        """
        Integrate matchup features with existing player features.
        
        Args:
            player_features_df: DataFrame with existing player features
            schedule_df: Optional schedule DataFrame
            weeks_to_analyze: List of weeks to analyze (defaults to first 4 weeks)
            
        Returns:
            DataFrame with matchup features added
        """
        logger.info(f"🎯 INTEGRATING MATCHUP FEATURES")
        logger.info(f"   Input data shape: {player_features_df.shape}")
        logger.info(f"   Columns available: {len(player_features_df.columns)}")
        
        if weeks_to_analyze is None:
            weeks_to_analyze = list(range(1, self.config.weeks_ahead_sos + 1))
        
        logger.info(f"   Weeks to analyze: {weeks_to_analyze}")
        logger.info(f"   Season for features: {self.season}")
        
        try:
            # Make a copy to avoid modifying original data
            enhanced_df = player_features_df.copy()
            
            # Ensure required columns exist
            required_cols = ['player_id', 'position', 'team']
            missing_cols = [col for col in required_cols if col not in enhanced_df.columns]
            if missing_cols:
                logger.error(f"❌ Required columns missing: {missing_cols}")
                logger.error(f"   Available columns: {list(enhanced_df.columns[:10])}...")  # Show first 10
                return enhanced_df
            
            logger.info(f"   ✅ Required columns found: {required_cols}")
            
            # Validate data format
            logger.info(f"   Validating data format...")
            teams_found = enhanced_df['team'].dropna().unique()
            positions_found = enhanced_df['position'].dropna().unique()
            logger.info(f"   Teams in data: {len(teams_found)} - {sorted(teams_found)}")
            logger.info(f"   Positions in data: {len(positions_found)} - {sorted(positions_found)}")
            
            if len(teams_found) == 0:
                logger.error(f"❌ No valid teams found in data")
                return enhanced_df
            
            if len(positions_found) == 0:
                logger.error(f"❌ No valid positions found in data")
                return enhanced_df
        
            # Add schedule strength features
            if self.config.include_schedule_strength:
                logger.info(f"   Adding schedule strength features...")
                try:
                    enhanced_df = self._add_schedule_strength_features(enhanced_df, weeks_to_analyze)
                    logger.info(f"   ✅ Schedule strength features added successfully")
                except Exception as e:
                    logger.error(f"   ❌ Schedule strength features failed: {e}")
                    import traceback
                    logger.error(f"   Full traceback: {traceback.format_exc()}")
            else:
                logger.info(f"   Schedule strength features disabled")
            
            # Add environmental features
            if self.config.include_environmental_factors:
                logger.info(f"   Adding environmental features...")
                try:
                    enhanced_df = self._add_environmental_features(enhanced_df, weeks_to_analyze)
                    logger.info(f"   ✅ Environmental features added successfully")
                except Exception as e:
                    logger.error(f"   ❌ Environmental features failed: {e}")
                    import traceback
                    logger.error(f"   Full traceback: {traceback.format_exc()}")
            else:
                logger.info(f"   Environmental features disabled")
            
            # Add situational features
            if self.config.include_situational_adjustments:
                logger.info(f"   Adding situational features...")
                try:
                    enhanced_df = self._add_situational_features(enhanced_df, weeks_to_analyze)
                    logger.info(f"   ✅ Situational features added successfully")
                except Exception as e:
                    logger.error(f"   ❌ Situational features failed: {e}")
                    import traceback
                    logger.error(f"   Full traceback: {traceback.format_exc()}")
            else:
                logger.info(f"   Situational features disabled")
            
            # Add derived matchup metrics
            logger.info(f"   Adding derived matchup metrics...")
            try:
                enhanced_df = self._add_derived_matchup_metrics(enhanced_df)
                logger.info(f"   ✅ Derived matchup metrics added successfully")
            except Exception as e:
                logger.error(f"   ❌ Derived matchup metrics failed: {e}")
                import traceback
                logger.error(f"   Full traceback: {traceback.format_exc()}")
            
            logger.info(f"✅ MATCHUP FEATURES INTEGRATION COMPLETE")
            logger.info(f"   Input columns: {len(player_features_df.columns)}")
            logger.info(f"   Output columns: {len(enhanced_df.columns)}")
            logger.info(f"   Features added: {len(enhanced_df.columns) - len(player_features_df.columns)}")
            return enhanced_df
            
        except Exception as e:
            logger.error(f"❌ MATCHUP FEATURE INTEGRATION FAILED: {e}")
            import traceback
            logger.error(f"   Full traceback: {traceback.format_exc()}")
            return player_features_df  # Return original data if integration fails
    
    def _add_schedule_strength_features(
        self, 
        df: pd.DataFrame, 
        weeks: List[int]
    ) -> pd.DataFrame:
        """Add schedule strength features for each player."""
        logger.info("📊 ADDING SCHEDULE STRENGTH FEATURES")
        logger.info(f"   Weeks to analyze: {weeks}")
        logger.info(f"   Season: {self.season}")
        
        try:
            result = df.copy()
            
            # Initialize SOS columns
            sos_columns = [
                'sos_rating', 'sos_tier', 'tough_matchups', 'easy_matchups',
                'home_game_pct', 'avg_opponent_def_rating'
            ]
            
            logger.info(f"   Initializing {len(sos_columns)} SOS columns...")
            for col in sos_columns:
                result[f'next_{self.config.weeks_ahead_sos}w_{col}'] = np.nan
            
            # Calculate SOS for each team-position combination
            unique_team_positions = result[['team', 'position']].drop_duplicates()
            logger.info(f"   Found {len(unique_team_positions)} unique team-position combinations")
            
            successful_calculations = 0
            failed_calculations = 0
            
            for idx, row in unique_team_positions.iterrows():
                team = row['team']
                position = row['position']
                
                try:
                    logger.info(f"   Calculating SOS for {team} {position}...")
                    # Get SOS metrics for this team-position combination
                    sos_metrics = self.sos_calculator.calculate_strength_of_schedule(
                        team=team,
                        position=position,
                        start_week=min(weeks),
                        end_week=max(weeks),
                        season=self.season
                    )
                    
                    if sos_metrics:
                        # Apply SOS metrics to all players of this team-position
                        mask = (result['team'] == team) & (result['position'] == position)
                        players_affected = mask.sum()
                        
                        logger.info(f"     ✅ SOS calculated: {sos_metrics.get('sos_rating', 0):.3f} ({sos_metrics.get('sos_tier', 'Unknown')})")
                        logger.info(f"     Applying to {players_affected} players...")
                        
                        for metric, value in sos_metrics.items():
                            col_name = f'next_{self.config.weeks_ahead_sos}w_{metric}'
                            if col_name in result.columns:
                                result.loc[mask, col_name] = value
                        
                        successful_calculations += 1
                    else:
                        logger.warning(f"     ⚠️  No SOS metrics returned for {team} {position}")
                        failed_calculations += 1
                    
                except Exception as e:
                    logger.error(f"     ❌ SOS calculation failed for {team} {position}: {e}")
                    failed_calculations += 1
                    continue
            
            logger.info(f"   ✅ Schedule strength features complete")
            logger.info(f"   Successful: {successful_calculations}, Failed: {failed_calculations}")
            
            # Add SOS tier encodings for ML models
            logger.info(f"   Adding SOS tier encodings...")
            if f'next_{self.config.weeks_ahead_sos}w_sos_tier' in result.columns:
                tier_encoding = {
                    'Very Easy': 2,
                    'Easy': 1, 
                    'Average': 0,
                    'Difficult': -1,
                    'Very Difficult': -2
                }
                result[f'next_{self.config.weeks_ahead_sos}w_sos_tier_encoded'] = (
                    result[f'next_{self.config.weeks_ahead_sos}w_sos_tier'].map(tier_encoding).fillna(0)
                )
                logger.info(f"   ✅ SOS tier encodings added")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Schedule strength features failed: {e}")
            import traceback
            logger.error(f"   Full traceback: {traceback.format_exc()}")
            return df
    
    def _add_environmental_features(
        self, 
        df: pd.DataFrame, 
        weeks: List[int]
    ) -> pd.DataFrame:
        """Add environmental and venue features."""
        logger.info("🌍 ADDING ENVIRONMENTAL FEATURES")
        logger.info(f"   Weeks to analyze: {weeks}")
        
        try:
            result = df.copy()
            
            # Initialize environmental columns
            env_columns = [
                'home_games_pct', 'dome_games_pct', 'high_altitude_games_pct',
                'cold_weather_games_pct', 'avg_venue_factor', 'travel_impact_factor'
            ]
            
            logger.info(f"   Initializing {len(env_columns)} environmental columns...")
            for col in env_columns:
                result[f'next_{self.config.weeks_ahead_sos}w_{col}'] = np.nan
            
            # Calculate environmental factors for each team
            unique_teams = result['team'].unique()
            logger.info(f"   Found {len(unique_teams)} unique teams")
            
            successful_teams = 0
            failed_teams = 0
            
            for team in unique_teams:
                try:
                    logger.info(f"   Calculating environmental factors for {team}...")
                    # Get team's upcoming schedule
                    team_env_metrics = self._calculate_team_environmental_metrics(
                        team, weeks
                    )
                    
                    if team_env_metrics:
                        # Apply to all players on this team
                        team_mask = result['team'] == team
                        players_affected = team_mask.sum()
                        
                        logger.info(f"     ✅ Environmental factors calculated for {team}")
                        logger.info(f"     Dome games: {team_env_metrics.get('dome_games_pct', 0):.1%}")
                        logger.info(f"     Home games: {team_env_metrics.get('home_games_pct', 0):.1%}")
                        logger.info(f"     Applying to {players_affected} players...")
                        
                        for metric, value in team_env_metrics.items():
                            col_name = f'next_{self.config.weeks_ahead_sos}w_{metric}'
                            if col_name in result.columns:
                                result.loc[team_mask, col_name] = value
                        
                        successful_teams += 1
                    else:
                        logger.warning(f"     ⚠️  No environmental metrics returned for {team}")
                        failed_teams += 1
                    
                except Exception as e:
                    logger.error(f"     ❌ Environmental calculation failed for {team}: {e}")
                    failed_teams += 1
                    continue
            
            logger.info(f"   Environmental factors complete: {successful_teams} successful, {failed_teams} failed")
            
            # Add position-specific environmental adjustments
            logger.info(f"   Adding position-specific environmental adjustments...")
            try:
                result = self._add_position_specific_environmental_features(result)
                logger.info(f"   ✅ Position-specific environmental features added")
            except Exception as e:
                logger.error(f"   ❌ Position-specific environmental features failed: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Environmental features failed: {e}")
            import traceback
            logger.error(f"   Full traceback: {traceback.format_exc()}")
            return df
    
    def _calculate_team_environmental_metrics(
        self, 
        team: str, 
        weeks: List[int]
    ) -> Dict[str, float]:
        """Calculate environmental metrics for a team's upcoming schedule."""
        logger.info(f"       🌍 Calculating environmental metrics for {team}")
        logger.info(f"       Weeks: {weeks}, Season: {self.season}")
        
        try:
            # Load schedule data if not already loaded
            if self.sos_calculator.schedule_data is None:
                logger.info(f"       Loading schedule data for season {self.season}...")
                self.sos_calculator.load_schedule_data([self.season])
            
            if self.sos_calculator.schedule_data is None or self.sos_calculator.schedule_data.empty:
                logger.error(f"       ❌ No schedule data available")
                return {}
            
            # Get team's schedule for the specified weeks
            schedule = self.sos_calculator.schedule_data
            team_schedule = schedule[
                (schedule['season'] == self.season) &
                (schedule['week'].isin(weeks)) &
                ((schedule['away_team'] == team) | (schedule['home_team'] == team))
            ].copy()
            
            if team_schedule.empty:
                logger.warning(f"       ⚠️  No schedule found for {team} in weeks {weeks}")
                logger.warning(f"       Available teams: {sorted(set(schedule['home_team'].unique()) | set(schedule['away_team'].unique()))}")
                return {}
                
            logger.info(f"       ✅ Found {len(team_schedule)} games for {team}")
        
            # Determine home/away status
            team_schedule['is_home'] = team_schedule['home_team'] == team
            team_schedule['venue_team'] = np.where(
                team_schedule['is_home'],
                team_schedule['home_team'],
                team_schedule['home_team']  # Venue is always home team's stadium
            )
            
            # Get stadium info for each game
            env_metrics = {
                'home_games_pct': team_schedule['is_home'].mean(),
                'dome_games_pct': 0.0,
                'high_altitude_games_pct': 0.0,
                'cold_weather_games_pct': 0.0,
                'avg_venue_factor': 1.0,
                'travel_impact_factor': 1.0
            }
            logger.info(f"       Home games: {env_metrics['home_games_pct']:.1%}")
            
            # Calculate environmental factors for each game
            dome_games = 0
            high_altitude_games = 0
            cold_weather_games = 0
            venue_factors = []
            travel_impacts = []
            
            for _, game in team_schedule.iterrows():
                venue_team = game['venue_team']
                is_home = game['is_home']
                
                # Get stadium info
                stadium_info = self.stadium_database.get_stadium_info(venue_team)
                if stadium_info:
                    # Dome games
                    if stadium_info['is_dome']:
                        dome_games += 1
                    
                    # High altitude (>3000 feet)
                    if stadium_info['altitude'] > 3000:
                        high_altitude_games += 1
                    
                    # Cold weather teams (approximation based on geography)
                    cold_weather_teams = ['BUF', 'GB', 'CHI', 'DET', 'MIN', 'NE', 'NYG', 'NYJ', 'PIT', 'CLE']
                    if venue_team in cold_weather_teams:
                        cold_weather_games += 1
                    
                    # Venue factor (dome advantage, altitude, etc.)
                    venue_factor = 1.0
                    if stadium_info['is_dome']:
                        venue_factor += 0.02  # Slight offensive boost
                    if stadium_info['altitude'] > 3000:
                        venue_factor += 0.01  # Slight boost for some positions
                    
                    venue_factors.append(venue_factor)
                
                # Travel impact (simplified)
                if not is_home:
                    travel_impacts.append(0.98)  # Slight penalty for away games
                else:
                    travel_impacts.append(1.0)
        
            # Calculate averages
            total_games = len(team_schedule)
            if total_games > 0:
                env_metrics.update({
                    'dome_games_pct': dome_games / total_games,
                    'high_altitude_games_pct': high_altitude_games / total_games,
                    'cold_weather_games_pct': cold_weather_games / total_games,
                    'avg_venue_factor': np.mean(venue_factors) if venue_factors else 1.0,
                    'travel_impact_factor': np.mean(travel_impacts) if travel_impacts else 1.0
                })
                
                logger.info(f"       ✅ Environmental metrics calculated:")
                logger.info(f"       Dome games: {env_metrics['dome_games_pct']:.1%}")
                logger.info(f"       High altitude: {env_metrics['high_altitude_games_pct']:.1%}")
                logger.info(f"       Cold weather: {env_metrics['cold_weather_games_pct']:.1%}")
            
            return env_metrics
            
        except Exception as e:
            logger.error(f"       ❌ Environmental metrics calculation failed: {e}")
            import traceback
            logger.error(f"       Full traceback: {traceback.format_exc()}")
            return {}
    
    def _add_position_specific_environmental_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add position-specific environmental adjustments."""
        result = df.copy()
        
        # Position-specific environmental multipliers
        position_env_factors = {
            'QB': {
                'dome_benefit': 1.05,      # +5% in domes
                'altitude_benefit': 1.01,   # +1% at altitude
                'cold_penalty': 0.95       # -5% in cold
            },
            'RB': {
                'dome_benefit': 1.01,      # +1% in domes
                'altitude_benefit': 1.0,    # No altitude effect
                'cold_penalty': 0.98       # -2% in cold
            },
            'WR': {
                'dome_benefit': 1.03,      # +3% in domes
                'altitude_benefit': 1.005,  # +0.5% at altitude
                'cold_penalty': 0.97       # -3% in cold
            },
            'TE': {
                'dome_benefit': 1.02,      # +2% in domes
                'altitude_benefit': 1.0,    # No altitude effect
                'cold_penalty': 0.98       # -2% in cold
            },
            'K': {
                'dome_benefit': 1.08,      # +8% in domes
                'altitude_benefit': 1.03,   # +3% at altitude
                'cold_penalty': 0.90       # -10% in cold
            }
        }
        
        # Apply position-specific environmental factors
        for position in position_env_factors:
            pos_mask = result['position'] == position
            factors = position_env_factors[position]
            
            # Environmental impact score
            weeks_ahead = self.config.weeks_ahead_sos
            
            dome_col = f'next_{weeks_ahead}w_dome_games_pct'
            altitude_col = f'next_{weeks_ahead}w_high_altitude_games_pct'
            cold_col = f'next_{weeks_ahead}w_cold_weather_games_pct'
            
            if all(col in result.columns for col in [dome_col, altitude_col, cold_col]):
                env_impact = (
                    result[dome_col] * (factors['dome_benefit'] - 1) +
                    result[altitude_col] * (factors['altitude_benefit'] - 1) +
                    result[cold_col] * (factors['cold_penalty'] - 1)
                )
                
                result.loc[pos_mask, f'next_{weeks_ahead}w_env_impact_{position.lower()}'] = env_impact
        
        return result
    
    def _add_situational_features(
        self, 
        df: pd.DataFrame, 
        weeks: List[int]
    ) -> pd.DataFrame:
        """Add situational and contextual features."""
        logger.info("Adding situational features")
        
        result = df.copy()
        
        # Initialize situational columns
        situational_columns = [
            'primetime_games_pct', 'division_games_pct', 'rest_advantage_avg',
            'short_week_games', 'long_week_games', 'rivalry_games_pct'
        ]
        
        for col in situational_columns:
            result[f'next_{self.config.weeks_ahead_sos}w_{col}'] = 0.0
        
        # Add player tier classification for primetime adjustments
        result = self._classify_player_tiers(result)
        
        # Calculate situational factors for each team
        unique_teams = result['team'].unique()
        
        for team in unique_teams:
            try:
                situational_metrics = self._calculate_team_situational_metrics(
                    team, weeks
                )
                
                if situational_metrics:
                    team_mask = result['team'] == team
                    
                    for metric, value in situational_metrics.items():
                        col_name = f'next_{self.config.weeks_ahead_sos}w_{metric}'
                        if col_name in result.columns:
                            result.loc[team_mask, col_name] = value
                
            except Exception as e:
                logger.warning(f"Could not calculate situational factors for {team}: {e}")
                continue
        
        return result
    
    def _calculate_team_situational_metrics(
        self, 
        team: str, 
        weeks: List[int]
    ) -> Dict[str, float]:
        """Calculate situational metrics for a team's upcoming schedule."""
        
        # This would typically use NFL schedule data with game times, divisions, etc.
        # For now, we'll provide reasonable defaults and placeholders
        
        # Approximate values based on typical NFL schedule patterns
        situational_metrics = {
            'primetime_games_pct': 0.15,  # ~15% of games are primetime
            'division_games_pct': 0.375,  # 6 of 16 games vs division
            'rest_advantage_avg': 0.0,    # Neutral rest on average
            'short_week_games': 0,        # Number of Thursday games
            'long_week_games': 0,         # Number of games after bye
            'rivalry_games_pct': 0.125    # ~2 rivalry games per season
        }
        
        return situational_metrics
    
    def _classify_player_tiers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Classify players into performance tiers for situational adjustments."""
        result = df.copy()
        
        # Use previous season fantasy points or other performance metrics
        # to classify players into tiers
        
        # Initialize tier column
        result['player_tier'] = 'average'
        
        # Position-specific tier thresholds (based on previous season FPPG)
        tier_thresholds = {
            'QB': {'elite': 20, 'premium': 15},
            'RB': {'elite': 15, 'premium': 10},
            'WR': {'elite': 12, 'premium': 8},
            'TE': {'elite': 8, 'premium': 5},
            'K': {'elite': 8, 'premium': 6}
        }
        
        # Look for fantasy points columns from previous season
        fppg_columns = [col for col in df.columns if 'fantasy_points' in col and ('L1' in col or 'per_game' in col)]
        
        if fppg_columns:
            fppg_col = fppg_columns[0]  # Use first available FPPG column
            
            for position in tier_thresholds:
                pos_mask = result['position'] == position
                thresholds = tier_thresholds[position]
                
                if fppg_col in result.columns:
                    result.loc[
                        pos_mask & (result[fppg_col] >= thresholds['elite']), 
                        'player_tier'
                    ] = 'elite'
                    
                    result.loc[
                        pos_mask & 
                        (result[fppg_col] >= thresholds['premium']) & 
                        (result[fppg_col] < thresholds['elite']), 
                        'player_tier'
                    ] = 'premium'
        
        return result
    
    def _add_derived_matchup_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived metrics that combine multiple matchup factors."""
        logger.info("Adding derived matchup metrics")
        
        result = df.copy()
        weeks_ahead = self.config.weeks_ahead_sos
        
        # Overall matchup favorability score
        sos_col = f'next_{weeks_ahead}w_sos_rating'
        env_impact_cols = [col for col in result.columns if f'next_{weeks_ahead}w_env_impact_' in col]
        
        if sos_col in result.columns:
            matchup_score = result[sos_col].fillna(0) * 0.6  # SOS is most important
            
            # Add environmental impact if available
            for env_col in env_impact_cols:
                matchup_score += result[env_col].fillna(0) * 0.4
            
            result[f'next_{weeks_ahead}w_overall_matchup_score'] = matchup_score
        
        # Matchup volatility (how much matchup quality varies)
        tough_col = f'next_{weeks_ahead}w_tough_matchups'
        easy_col = f'next_{weeks_ahead}w_easy_matchups'
        total_col = f'next_{weeks_ahead}w_total_games'
        
        if all(col in result.columns for col in [tough_col, easy_col, total_col]):
            # High volatility if lots of tough OR easy matchups
            volatility = (result[tough_col] + result[easy_col]) / result[total_col].replace(0, 1)
            result[f'next_{weeks_ahead}w_matchup_volatility'] = volatility
        
        # Schedule difficulty tier
        if sos_col in result.columns:
            result[f'next_{weeks_ahead}w_schedule_tier'] = pd.cut(
                result[sos_col].fillna(0),
                bins=[-np.inf, -0.15, -0.05, 0.05, 0.15, np.inf],
                labels=['Very_Hard', 'Hard', 'Average', 'Easy', 'Very_Easy']
            )
        
        # Home field advantage factor
        home_pct_col = f'next_{weeks_ahead}w_home_games_pct'
        if home_pct_col in result.columns:
            # More home games = advantage
            result[f'next_{weeks_ahead}w_home_field_advantage'] = (
                result[home_pct_col] - 0.5
            ) * 0.05  # Up to +/-2.5% adjustment
        
        return result
    
    def get_matchup_adjusted_projections(
        self,
        base_projections: pd.DataFrame,
        weeks: List[int] = None
    ) -> pd.DataFrame:
        """
        Apply matchup adjustments to base fantasy projections.
        
        Args:
            base_projections: DataFrame with player IDs and base projections
            weeks: Weeks to analyze for matchup adjustments
            
        Returns:
            DataFrame with matchup-adjusted projections
        """
        if weeks is None:
            weeks = list(range(1, self.config.weeks_ahead_sos + 1))
        
        logger.info(f"Applying matchup adjustments to {len(base_projections)} projections")
        
        result = base_projections.copy()
        
        # Ensure we have required columns
        if 'projected_fppg' not in result.columns:
            logger.warning("No 'projected_fppg' column found for matchup adjustments")
            return result
        
        # Get matchup features for these players
        matchup_features = self.integrate_matchup_features(result, weeks_to_analyze=weeks)
        
        # Apply matchup adjustments
        weeks_ahead = self.config.weeks_ahead_sos
        
        # Overall matchup score adjustment
        matchup_score_col = f'next_{weeks_ahead}w_overall_matchup_score'
        if matchup_score_col in matchup_features.columns:
            # Apply up to +/-15% adjustment based on matchup score
            max_adjustment = 0.15
            adjustment_factor = 1 + (matchup_features[matchup_score_col].fillna(0) * max_adjustment)
            adjustment_factor = np.clip(adjustment_factor, 0.85, 1.15)
            
            result['matchup_adjusted_fppg'] = result['projected_fppg'] * adjustment_factor
            result['matchup_adjustment_factor'] = adjustment_factor
        else:
            result['matchup_adjusted_fppg'] = result['projected_fppg']
            result['matchup_adjustment_factor'] = 1.0
        
        # Add confidence intervals based on matchup volatility
        volatility_col = f'next_{weeks_ahead}w_matchup_volatility'
        if volatility_col in matchup_features.columns:
            volatility = matchup_features[volatility_col].fillna(0.2)
            
            # Higher volatility = wider confidence intervals
            result['projection_floor'] = result['matchup_adjusted_fppg'] * (1 - volatility * 0.3)
            result['projection_ceiling'] = result['matchup_adjusted_fppg'] * (1 + volatility * 0.3)
        else:
            result['projection_floor'] = result['matchup_adjusted_fppg'] * 0.8
            result['projection_ceiling'] = result['matchup_adjusted_fppg'] * 1.2
        
        # Merge remaining matchup features
        matchup_cols = [col for col in matchup_features.columns 
                       if col.startswith(f'next_{weeks_ahead}w_') and col not in result.columns]
        
        if matchup_cols:
            merge_cols = ['player_id'] + matchup_cols
            result = result.merge(
                matchup_features[merge_cols],
                on='player_id',
                how='left'
            )
        
        logger.info(f"Applied matchup adjustments. Avg adjustment factor: {result['matchup_adjustment_factor'].mean():.3f}")
        
        return result


def validate_matchup_feature_integration() -> Dict[str, bool]:
    """Validate matchup feature integration functionality."""
    validation_results = {}
    
    try:
        # Create test data
        test_data = pd.DataFrame({
            'player_id': ['player_1', 'player_2', 'player_3'],
            'position': ['QB', 'RB', 'WR'],  
            'team': ['KC', 'BUF', 'DEN'],
            'projected_fppg': [20.0, 15.0, 12.0]
        })
        
        # Initialize integrator
        config = MatchupFeatureConfig(season_for_features=2024)
        integrator = MatchupFeatureIntegrator(config)
        
        # Test feature integration
        enhanced_df = integrator.integrate_matchup_features(test_data)
        validation_results['feature_integration_works'] = len(enhanced_df) == len(test_data)
        validation_results['features_added'] = len(enhanced_df.columns) > len(test_data.columns)
        
        # Test projection adjustments
        adjusted_projections = integrator.get_matchup_adjusted_projections(test_data)
        validation_results['projection_adjustments_work'] = 'matchup_adjusted_fppg' in adjusted_projections.columns
        validation_results['adjustment_factors_valid'] = (
            adjusted_projections['matchup_adjustment_factor'].between(0.5, 1.5).all()
        )
        
    except Exception as e:
        validation_results['validation_error'] = str(e)
    
    return validation_results


if __name__ == "__main__":
    # Test the matchup feature integrator
    print("🎯 Testing Matchup Feature Integrator")
    print("=" * 50)
    
    # Run validation
    validation = validate_matchup_feature_integration()
    
    print("Validation Results:")
    for test, result in validation.items():
        if isinstance(result, bool):
            status = "✅" if result else "❌"
            print(f"{status} {test}: {result}")
        else:
            print(f"ℹ️  {test}: {result}")
    
    # Example usage
    print("\n" + "=" * 50)
    print("Example: Integrating Matchup Features")
    
    # Create sample player data
    sample_data = pd.DataFrame({
        'player_id': ['mahomes', 'henry', 'hill'],
        'position': ['QB', 'RB', 'WR'],
        'team': ['KC', 'TEN', 'MIA'],
        'projected_fppg': [24.5, 16.2, 13.8],
        'fantasy_points_ppr_L1': [25.1, 15.8, 12.9]  # Previous season data
    })
    
    # Initialize integrator
    config = MatchupFeatureConfig(
        season_for_features=2024,
        weeks_ahead_sos=4,
        include_schedule_strength=True,
        include_environmental_factors=True
    )
    
    integrator = MatchupFeatureIntegrator(config)
    
    # Integrate matchup features
    enhanced_data = integrator.integrate_matchup_features(sample_data)
    
    print(f"Original features: {len(sample_data.columns)}")
    print(f"Enhanced features: {len(enhanced_data.columns)}")
    
    # Get matchup-adjusted projections
    adjusted_projections = integrator.get_matchup_adjusted_projections(sample_data)
    
    print("\nMatchup-Adjusted Projections:")
    for _, row in adjusted_projections.iterrows():
        print(f"{row['player_id']}: {row['projected_fppg']:.1f} → {row['matchup_adjusted_fppg']:.1f} "
              f"(factor: {row['matchup_adjustment_factor']:.3f})")
    
    print("\nMatchup Feature Integrator implementation complete! 🎯")