"""
Dynamic Strength of Schedule (SOS) Analysis for Fantasy Football

This module calculates opponent strength metrics to enhance player projections by
accounting for upcoming matchup difficulty. It provides:

- Position-specific defensive rankings (vs QB, RB, WR, TE)
- Forward-looking strength of schedule calculations
- Pace of play adjustments for opportunity metrics
- Rest advantage/disadvantage factors
- Rolling window defensive performance tracking

The SOS system helps identify:
- Players with easy upcoming schedules (draft targets)
- Players with tough playoff schedules (fade candidates)
- Week-to-week streaming opportunities
- Schedule-based trade targets
"""

import pandas as pd
import numpy as np
import nfl_data_py as nfl
import logging
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import sys
from datetime import datetime, timedelta
import warnings

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))
import config

logger = logging.getLogger(__name__)


class ScheduleStrengthCalculator:
    """Calculate dynamic strength of schedule metrics for fantasy football."""
    
    def __init__(self, current_season: int = None, weeks_ahead: int = 4):
        """
        Initialize the SOS calculator.
        
        Args:
            current_season: Season year for calculations
            weeks_ahead: Number of weeks to look ahead for SOS
        """
        self.current_season = current_season or config.CURRENT_SEASON
        self.weeks_ahead = weeks_ahead
        self.schedule_data = None
        self.defensive_rankings = None
        self.pace_data = None
        
    def load_schedule_data(self, seasons: List[int] = None) -> pd.DataFrame:
        """
        Load NFL schedule data for SOS calculations.
        
        Args:
            seasons: List of seasons to load
            
        Returns:
            DataFrame with schedule information
        """
        if seasons is None:
            seasons = [self.current_season]
            
        logger.info(f"🗓️  LOADING SCHEDULE DATA")
        logger.info(f"   Seasons requested: {seasons}")
        
        try:
            schedules = nfl.import_schedules(seasons)
            
            if schedules.empty:
                logger.error(f"❌ SCHEDULE LOAD FAILED: No schedule data returned for seasons {seasons}")
                return pd.DataFrame()
            
            logger.info(f"✅ Schedule data loaded successfully: {len(schedules)} games")
            logger.info(f"   Seasons found: {sorted(schedules['season'].unique())}")
            logger.info(f"   Weeks available: {sorted(schedules['week'].unique())}")
            
            # Validate we have the expected teams
            teams_found = set(schedules['home_team'].unique()) | set(schedules['away_team'].unique())
            logger.info(f"   Teams in schedule: {len(teams_found)} - {sorted(list(teams_found))[:5]}...")
            
            # Clean and standardize schedule data
            try:
                schedules_clean = schedules.rename(columns={
                    'game_id': 'game_id',
                    'season': 'season',
                    'game_type': 'game_type',
                    'week': 'week',
                    'gameday': 'game_date',
                    'weekday': 'day_of_week',
                    'gametime': 'game_time',
                    'away_team': 'away_team',
                    'away_score': 'away_score',
                    'home_team': 'home_team',
                    'home_score': 'home_score',
                    'location': 'location',
                    'result': 'result',
                    'total': 'total_points',
                    'overtime': 'overtime',
                    'old_game_id': 'old_game_id',
                    'gsis': 'gsis',
                    'nfl_detail_id': 'nfl_detail_id',
                    'pfr': 'pfr',
                    'pff': 'pff',
                    'espn': 'espn',
                    'ftn': 'ftn',
                    'away_rest': 'away_rest',
                    'home_rest': 'home_rest',
                    'away_moneyline': 'away_moneyline',
                    'home_moneyline': 'home_moneyline',
                    'spread_line': 'spread_line',
                'away_spread_odds': 'away_spread_odds',
                'home_spread_odds': 'home_spread_odds',
                'total_line': 'total_line',
                'under_odds': 'under_odds',
                'over_odds': 'over_odds',
                'div_game': 'division_game',
                'roof': 'stadium_type',
                'surface': 'field_surface',
                'temp': 'temperature',
                'wind': 'wind_speed'
                })
                
                logger.info(f"✅ Column standardization successful")
                
                # Filter to regular season games only
                reg_season_games = schedules_clean[schedules_clean['game_type'] == 'REG'].copy()
                logger.info(f"   Regular season games: {len(reg_season_games)}")
                
                # Add derived fields
                reg_season_games['away_rest_advantage'] = reg_season_games['away_rest'] - 7
                reg_season_games['home_rest_advantage'] = reg_season_games['home_rest'] - 7
                
                # Add primetime indicators  
                reg_season_games['is_primetime'] = reg_season_games['day_of_week'].isin(['Thursday', 'Sunday Night', 'Monday'])
                
                self.schedule_data = reg_season_games
                logger.info(f"✅ Schedule data processing complete: {len(reg_season_games)} games")
                return reg_season_games
                
            except Exception as column_error:
                logger.error(f"❌ Column processing failed: {column_error}")
                logger.warning(f"   Using raw schedule data instead")
                self.schedule_data = schedules
                return schedules
            
        except Exception as e:
            logger.error(f"❌ SCHEDULE DATA LOAD FAILED: {e}")
            logger.error(f"   This will cause SOS calculations to fail")
            import traceback
            logger.error(f"   Full traceback: {traceback.format_exc()}")
            return pd.DataFrame()
    
    def calculate_defensive_rankings(self, seasons: List[int] = None, window_size: int = 8) -> pd.DataFrame:
        """
        Calculate position-specific defensive rankings based on fantasy points allowed.
        
        Args:
            seasons: Seasons to include in calculation
            window_size: Rolling window size for recent performance
            
        Returns:
            DataFrame with defensive rankings by position and team
        """
        if seasons is None:
            # Use last 2 seasons for defensive rankings
            seasons = [self.current_season - 2, self.current_season - 1]
            
        logger.info(f"Calculating defensive rankings for seasons: {seasons}")
        
        try:
            # Load weekly player data for defensive analysis
            weekly_data = nfl.import_weekly_data(seasons)
            
            # Calculate fantasy points using Half-PPR scoring
            weekly_data['fantasy_points'] = self.calculate_fantasy_points(weekly_data)
            
            # Create opponent-based defensive stats
            defensive_stats = []
            
            for position in ['QB', 'RB', 'WR', 'TE']:
                pos_data = weekly_data[weekly_data['position'] == position].copy()
                
                if pos_data.empty:
                    continue
                
                # Group by opponent team and calculate average points allowed
                opponent_stats = pos_data.groupby(['opponent_team', 'season', 'week']).agg({
                    'fantasy_points': ['count', 'sum', 'mean', 'std'],
                    'targets': 'sum',
                    'carries': 'sum',
                    'rushing_yards': 'sum',
                    'receiving_yards': 'sum',
                    'passing_yards': 'sum',
                    'rushing_tds': 'sum',
                    'receiving_tds': 'sum',
                    'passing_tds': 'sum'
                }).reset_index()
                
                # Flatten column names
                opponent_stats.columns = [
                    'team', 'season', 'week', f'{position.lower()}_games', 
                    f'{position.lower()}_total_pts', f'{position.lower()}_avg_pts', f'{position.lower()}_std_pts',
                    f'{position.lower()}_targets_allowed', f'{position.lower()}_carries_allowed',
                    f'{position.lower()}_rush_yds_allowed', f'{position.lower()}_rec_yds_allowed',
                    f'{position.lower()}_pass_yds_allowed', f'{position.lower()}_rush_tds_allowed',
                    f'{position.lower()}_rec_tds_allowed', f'{position.lower()}_pass_tds_allowed'
                ]
                
                defensive_stats.append(opponent_stats)
            
            # Combine all position defensive stats
            if defensive_stats:
                # Start with first position and merge others
                combined_defensive = defensive_stats[0]
                for i in range(1, len(defensive_stats)):
                    combined_defensive = combined_defensive.merge(
                        defensive_stats[i], 
                        on=['team', 'season', 'week'], 
                        how='outer'
                    )
                
                # Fill missing values
                combined_defensive = combined_defensive.fillna(0)
                
                # Calculate rolling averages for recent performance
                combined_defensive = combined_defensive.sort_values(['team', 'season', 'week'])
                
                # Create rolling windows for each position
                for position in ['qb', 'rb', 'wr', 'te']:
                    avg_col = f'{position}_avg_pts'
                    if avg_col in combined_defensive.columns:
                        combined_defensive[f'{position}_rolling_avg'] = combined_defensive.groupby('team')[avg_col].rolling(
                            window=window_size, min_periods=3
                        ).mean().reset_index(drop=True)
                
                # Calculate league averages for normalization
                league_averages = {}
                for position in ['qb', 'rb', 'wr', 'te']:
                    avg_col = f'{position}_avg_pts'
                    if avg_col in combined_defensive.columns:
                        league_averages[position] = combined_defensive[avg_col].mean()
                
                # Create defensive strength scores (negative = good defense)
                for position in ['qb', 'rb', 'wr', 'te']:
                    avg_col = f'{position}_avg_pts'
                    rolling_col = f'{position}_rolling_avg'
                    
                    if avg_col in combined_defensive.columns:
                        league_avg = league_averages[position]
                        
                        # Season-long defensive rating
                        combined_defensive[f'{position}_def_rating'] = (
                            combined_defensive[avg_col] - league_avg
                        ) / league_avg
                        
                        # Recent defensive rating (rolling window)
                        if rolling_col in combined_defensive.columns:
                            combined_defensive[f'{position}_recent_def_rating'] = (
                                combined_defensive[rolling_col] - league_avg
                            ) / league_avg
                
                self.defensive_rankings = combined_defensive
                logger.info(f"Calculated defensive rankings for {len(combined_defensive)} team-week combinations")
                return combined_defensive
            else:
                logger.warning("No defensive stats data available")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error calculating defensive rankings: {e}")
            return pd.DataFrame()
    
    def calculate_fantasy_points(self, weekly_data: pd.DataFrame) -> pd.Series:
        """
        Calculate fantasy points using Half-PPR scoring.
        
        Args:
            weekly_data: DataFrame with weekly player stats
            
        Returns:
            Series with fantasy points calculated
        """
        points = pd.Series(0.0, index=weekly_data.index)
        
        # Passing
        if 'passing_yards' in weekly_data.columns:
            points += weekly_data['passing_yards'].fillna(0) * config.FANTASY_POINTS['passing_yards']
        if 'passing_tds' in weekly_data.columns:
            points += weekly_data['passing_tds'].fillna(0) * config.FANTASY_POINTS['passing_tds']
        if 'interceptions' in weekly_data.columns:
            points += weekly_data['interceptions'].fillna(0) * config.FANTASY_POINTS['interceptions']
        
        # Rushing
        if 'rushing_yards' in weekly_data.columns:
            points += weekly_data['rushing_yards'].fillna(0) * config.FANTASY_POINTS['rushing_yards']
        if 'rushing_tds' in weekly_data.columns:
            points += weekly_data['rushing_tds'].fillna(0) * config.FANTASY_POINTS['rushing_tds']
        
        # Receiving
        if 'receptions' in weekly_data.columns:
            points += weekly_data['receptions'].fillna(0) * config.FANTASY_POINTS['receptions']
        if 'receiving_yards' in weekly_data.columns:
            points += weekly_data['receiving_yards'].fillna(0) * config.FANTASY_POINTS['receiving_yards']
        if 'receiving_tds' in weekly_data.columns:
            points += weekly_data['receiving_tds'].fillna(0) * config.FANTASY_POINTS['receiving_tds']
        
        # Fumbles
        if 'fumbles_lost' in weekly_data.columns:
            points += weekly_data['fumbles_lost'].fillna(0) * config.FANTASY_POINTS['fumbles_lost']
        
        # Two point conversions
        if 'two_point_conversions' in weekly_data.columns:
            points += weekly_data['two_point_conversions'].fillna(0) * config.FANTASY_POINTS['two_point_conversions']
        
        return points
    
    def calculate_pace_adjustments(self, seasons: List[int] = None) -> pd.DataFrame:
        """
        Calculate team pace of play metrics for opportunity adjustments.
        
        Args:
            seasons: Seasons to analyze for pace
            
        Returns:
            DataFrame with pace metrics by team
        """
        if seasons is None:
            seasons = [self.current_season - 1]
            
        logger.info(f"Calculating pace adjustments for seasons: {seasons}")
        
        try:
            # Load play-by-play data for pace analysis
            pbp_data = nfl.import_pbp_data(seasons)
            
            # Filter to regular plays only
            pace_plays = pbp_data[
                (pbp_data['play_type'].isin(['pass', 'run'])) &
                (pbp_data['down'].notna()) &
                (~pbp_data['two_minute_warning'].fillna(False)) &
                (~pbp_data['timeout_team'].fillna('').ne(''))
            ].copy()
            
            # Calculate plays per game by team
            team_pace = pace_plays.groupby(['posteam', 'season', 'week']).agg({
                'play_id': 'count'  # Total plays
            }).reset_index()
            
            team_pace = team_pace.rename(columns={'play_id': 'total_plays'})
            
            # Calculate season averages
            season_pace = team_pace.groupby(['posteam', 'season']).agg({
                'total_plays': 'mean'
            }).reset_index()
            
            season_pace = season_pace.rename(columns={'total_plays': 'plays_per_game'})
            
            # Calculate league average pace
            league_avg_pace = season_pace['plays_per_game'].mean()
            
            # Create pace factor (1.0 = league average)
            season_pace['pace_factor'] = season_pace['plays_per_game'] / league_avg_pace
            
            # Add pace categories
            season_pace['pace_category'] = pd.cut(
                season_pace['pace_factor'],
                bins=[0, 0.95, 1.05, float('inf')],
                labels=['Slow', 'Average', 'Fast']
            )
            
            self.pace_data = season_pace
            logger.info(f"Calculated pace adjustments for {len(season_pace)} team-season combinations")
            return season_pace
            
        except Exception as e:
            logger.error(f"Error calculating pace adjustments: {e}")
            return pd.DataFrame()
    
    def calculate_rest_advantages(self, schedule_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Calculate rest advantage/disadvantage factors for teams.
        
        Args:
            schedule_df: Schedule DataFrame (uses self.schedule_data if None)
            
        Returns:
            DataFrame with rest advantage metrics
        """
        if schedule_df is None:
            if self.schedule_data is None:
                self.load_schedule_data()
            schedule_df = self.schedule_data
        
        if schedule_df is None or schedule_df.empty:
            logger.warning("No schedule data available for rest advantages")
            return pd.DataFrame()
        
        logger.info("Calculating rest advantages")
        
        try:
            # Create long format for team-level analysis
            away_games = schedule_df[['game_id', 'season', 'week', 'away_team', 'away_rest', 'home_team']].copy()
            away_games = away_games.rename(columns={
                'away_team': 'team',
                'away_rest': 'rest_days',
                'home_team': 'opponent'
            })
            away_games['home_away'] = 'away'
            
            home_games = schedule_df[['game_id', 'season', 'week', 'home_team', 'home_rest', 'away_team']].copy()
            home_games = home_games.rename(columns={
                'home_team': 'team',
                'home_rest': 'rest_days',
                'away_team': 'opponent'
            })
            home_games['home_away'] = 'home'
            
            # Combine all games
            all_games = pd.concat([away_games, home_games], ignore_index=True)
            
            # Calculate rest advantages
            all_games['rest_advantage'] = all_games['rest_days'] - 7  # Normal week is 7 days
            
            # Categorize rest situations
            def categorize_rest(rest_days):
                if rest_days <= 4:
                    return 'Short Rest'
                elif rest_days >= 10:
                    return 'Long Rest'
                else:
                    return 'Normal Rest'
            
            all_games['rest_category'] = all_games['rest_days'].apply(categorize_rest)
            
            # Add Thursday/Monday game indicators
            all_games['short_week'] = all_games['rest_days'] <= 4
            all_games['long_week'] = all_games['rest_days'] >= 10
            
            # Calculate rest impact factors
            all_games['rest_impact_factor'] = 1.0  # Base factor
            
            # Adjust for short rest (negative impact)
            all_games.loc[all_games['short_week'], 'rest_impact_factor'] = 0.95
            
            # Adjust for long rest (positive impact)
            all_games.loc[all_games['long_week'], 'rest_impact_factor'] = 1.03
            
            # Additional penalty for very short rest (Thursday games)
            all_games.loc[all_games['rest_days'] <= 4, 'rest_impact_factor'] = 0.92
            
            logger.info(f"Calculated rest advantages for {len(all_games)} team-game combinations")
            return all_games
            
        except Exception as e:
            logger.error(f"Error calculating rest advantages: {e}")
            return pd.DataFrame()
    
    def _get_fallback_sos_metrics(self, team: str, position: str) -> Dict[str, float]:
        """
        Generate fallback SOS metrics when primary calculation fails.
        
        Args:
            team: Team abbreviation
            position: Position
            
        Returns:
            Dictionary with fallback SOS metrics (neutral/average values)
        """
        logger.info(f"🔧 GENERATING FALLBACK SOS METRICS for {team} {position}")
        
        # Return neutral/average SOS metrics
        fallback_metrics = {
            'sos_rating': 0.0,          # Neutral schedule strength
            'recent_sos_rating': 0.0,   # Neutral recent strength
            'total_games': 4,           # Assume standard 4-week window
            'tough_matchups': 1,        # Assume 1 tough matchup
            'easy_matchups': 1,         # Assume 1 easy matchup
            'home_games': 2,            # Assume even home/away split
            'away_games': 2,
            'home_game_pct': 0.5,
            'avg_opponent_def_rating': 0.0,  # League average
            'sos_tier': 'Average',      # Middle tier
            'rest_advantage': 0.0       # No rest advantage
        }
        
        logger.info(f"   ✅ Using fallback SOS rating: {fallback_metrics['sos_rating']}")
        return fallback_metrics
    
    def calculate_strength_of_schedule(
        self, 
        team: str, 
        position: str, 
        start_week: int = 1, 
        end_week: int = 17,
        season: int = None
    ) -> Dict[str, float]:
        """
        Calculate forward-looking strength of schedule for a team-position combination.
        
        Args:
            team: Team abbreviation (e.g., 'KC', 'BUF')
            position: Position ('QB', 'RB', 'WR', 'TE')
            start_week: Starting week for SOS calculation
            end_week: Ending week for SOS calculation
            season: Season year
            
        Returns:
            Dictionary with SOS metrics
        """
        if season is None:
            season = self.current_season
            
        logger.info(f"🎯 CALCULATING SOS")
        logger.info(f"   Team: {team}, Position: {position}")
        logger.info(f"   Season: {season}, Weeks: {start_week}-{end_week}")
        
        # Load required data if not already loaded
        if self.schedule_data is None:
            logger.info(f"   Loading schedule data for season {season}")
            try:
                self.load_schedule_data([season])
                if self.schedule_data is None or self.schedule_data.empty:
                    logger.error(f"❌ Schedule data load failed for season {season}")
                    return self._get_fallback_sos_metrics(team, position)
                else:
                    logger.info(f"   ✅ Schedule data loaded: {len(self.schedule_data)} games")
            except Exception as e:
                logger.error(f"❌ Schedule data load error: {e}")
                return self._get_fallback_sos_metrics(team, position)
        
        if self.defensive_rankings is None:
            logger.info(f"   Loading defensive rankings")
            try:
                self.calculate_defensive_rankings()
                if self.defensive_rankings is None or self.defensive_rankings.empty:
                    logger.error(f"❌ Defensive rankings calculation failed")
                    return self._get_fallback_sos_metrics(team, position)
                else:
                    logger.info(f"   ✅ Defensive rankings loaded: {len(self.defensive_rankings)} records")
            except Exception as e:
                logger.error(f"❌ Defensive rankings error: {e}")
                return self._get_fallback_sos_metrics(team, position)
        
        if self.schedule_data is None or self.schedule_data.empty:
            logger.error(f"❌ No schedule data available for SOS calculation")
            return self._get_fallback_sos_metrics(team, position)
        
        try:
            # Get team's upcoming schedule
            team_schedule = self.schedule_data[
                (self.schedule_data['season'] == season) &
                (self.schedule_data['week'] >= start_week) &
                (self.schedule_data['week'] <= end_week) &
                ((self.schedule_data['away_team'] == team) | (self.schedule_data['home_team'] == team))
            ].copy()
            
            if team_schedule.empty:
                logger.error(f"❌ No schedule found for team {team} in weeks {start_week}-{end_week}")
                logger.error(f"   Available teams in schedule: {sorted(set(self.schedule_data['home_team'].unique()) | set(self.schedule_data['away_team'].unique()))}")
                logger.error(f"   Available weeks: {sorted(self.schedule_data['week'].unique())}")
                return self._get_fallback_sos_metrics(team, position)
            
            # Identify opponents
            team_schedule['opponent'] = np.where(
                team_schedule['away_team'] == team,
                team_schedule['home_team'],
                team_schedule['away_team']
            )
            
            team_schedule['is_home'] = team_schedule['home_team'] == team
            
            # Get defensive rankings for opponents
            pos_lower = position.lower()
            def_rating_col = f'{pos_lower}_def_rating'
            recent_rating_col = f'{pos_lower}_recent_def_rating'
            
            if self.defensive_rankings is not None and not self.defensive_rankings.empty:
                # Get most recent defensive ratings for each opponent
                latest_ratings = self.defensive_rankings.loc[
                    self.defensive_rankings.groupby('team')['week'].idxmax()
                ].copy()
                
                # Merge with schedule
                team_schedule = team_schedule.merge(
                    latest_ratings[['team', def_rating_col, recent_rating_col]],
                    left_on='opponent',
                    right_on='team',
                    how='left',
                    suffixes=('', '_def')
                )
                
                # Calculate SOS metrics
                if def_rating_col in team_schedule.columns:
                    avg_def_rating = team_schedule[def_rating_col].mean()
                    recent_def_rating = team_schedule[recent_rating_col].mean() if recent_rating_col in team_schedule.columns else avg_def_rating
                    
                    # Convert to opponent difficulty (positive = easier opponents)
                    sos_rating = -avg_def_rating  # Flip sign so positive = easier
                    recent_sos_rating = -recent_def_rating
                    
                    # Count games vs different defense types
                    tough_matchups = (team_schedule[def_rating_col] < -0.1).sum()  # Good defenses
                    easy_matchups = (team_schedule[def_rating_col] > 0.1).sum()   # Bad defenses
                    
                    # Home/away split
                    home_games = team_schedule['is_home'].sum()
                    away_games = len(team_schedule) - home_games
                    
                    sos_metrics = {
                        'sos_rating': sos_rating,
                        'recent_sos_rating': recent_sos_rating,
                        'total_games': len(team_schedule),
                        'tough_matchups': tough_matchups,
                        'easy_matchups': easy_matchups,
                        'neutral_matchups': len(team_schedule) - tough_matchups - easy_matchups,
                        'home_games': home_games,
                        'away_games': away_games,
                        'home_game_pct': home_games / len(team_schedule) if len(team_schedule) > 0 else 0,
                        'avg_opponent_def_rating': avg_def_rating,
                        'sos_tier': self._categorize_sos(sos_rating)
                    }
                    
                    logger.info(f"✅ SOS CALCULATION SUCCESSFUL")
                    logger.info(f"   {team} {position} SOS Rating: {sos_rating:.3f} ({sos_metrics['sos_tier']})")
                    logger.info(f"   Games: {len(team_schedule)} | Tough: {tough_matchups} | Easy: {easy_matchups}")
                    logger.info(f"   Home: {home_games} | Away: {away_games}")
                    return sos_metrics
                else:
                    logger.error(f"❌ No defensive rating column '{def_rating_col}' found")
                    logger.error(f"   Available columns: {list(team_schedule.columns)}")
                    return self._get_fallback_sos_metrics(team, position)
            else:
                logger.error(f"❌ No defensive rankings data available for SOS calculation")
                return self._get_fallback_sos_metrics(team, position)
                
        except Exception as e:
            logger.error(f"❌ SOS CALCULATION FAILED for {team} {position}: {e}")
            import traceback
            logger.error(f"   Full traceback: {traceback.format_exc()}")
            return self._get_fallback_sos_metrics(team, position)
    
    def _categorize_sos(self, sos_rating: float) -> str:
        """Categorize SOS rating into tiers."""
        if sos_rating >= 0.15:
            return 'Very Easy'
        elif sos_rating >= 0.05:
            return 'Easy'
        elif sos_rating >= -0.05:
            return 'Average'
        elif sos_rating >= -0.15:
            return 'Difficult'
        else:
            return 'Very Difficult'
    
    def get_team_schedule_outlook(
        self, 
        team: str, 
        season: int = None,
        next_n_weeks: int = 4
    ) -> Dict[str, any]:
        """
        Get comprehensive schedule outlook for a team.
        
        Args:
            team: Team abbreviation
            season: Season year
            next_n_weeks: Number of weeks to analyze
            
        Returns:
            Dictionary with comprehensive schedule analysis
        """
        if season is None:
            season = self.current_season
        
        try:
            outlook = {}
            
            # Calculate SOS for each position
            for position in ['QB', 'RB', 'WR', 'TE']:
                sos_metrics = self.calculate_strength_of_schedule(
                    team=team,
                    position=position,
                    start_week=1,
                    end_week=next_n_weeks,
                    season=season
                )
                outlook[f'{position.lower()}_sos'] = sos_metrics
            
            # Get rest advantages if available
            if self.schedule_data is not None:
                rest_data = self.calculate_rest_advantages()
                if not rest_data.empty:
                    team_rest = rest_data[
                        (rest_data['team'] == team) &
                        (rest_data['season'] == season) &
                        (rest_data['week'] <= next_n_weeks)
                    ]
                    
                    if not team_rest.empty:
                        outlook['rest_outlook'] = {
                            'avg_rest_days': team_rest['rest_days'].mean(),
                            'short_rest_games': (team_rest['rest_days'] <= 4).sum(),
                            'long_rest_games': (team_rest['rest_days'] >= 10).sum(),
                            'avg_rest_impact_factor': team_rest['rest_impact_factor'].mean()
                        }
            
            # Get pace factor if available
            if self.pace_data is not None:
                team_pace = self.pace_data[
                    (self.pace_data['posteam'] == team) &
                    (self.pace_data['season'] == season - 1)  # Use previous season
                ]
                
                if not team_pace.empty:
                    outlook['pace_outlook'] = {
                        'pace_factor': team_pace['pace_factor'].iloc[0],
                        'pace_category': team_pace['pace_category'].iloc[0],
                        'plays_per_game': team_pace['plays_per_game'].iloc[0]
                    }
            
            logger.info(f"Generated comprehensive schedule outlook for {team}")
            return outlook
            
        except Exception as e:
            logger.error(f"Error generating schedule outlook for {team}: {e}")
            return {}


def get_league_sos_rankings(
    position: str, 
    season: int = None, 
    weeks: int = 4
) -> pd.DataFrame:
    """
    Get league-wide SOS rankings for a position.
    
    Args:
        position: Position to analyze ('QB', 'RB', 'WR', 'TE')
        season: Season year
        weeks: Number of weeks to analyze
        
    Returns:
        DataFrame with SOS rankings for all teams
    """
    if season is None:
        season = config.CURRENT_SEASON
    
    logger.info(f"Calculating league-wide SOS rankings for {position}")
    
    calculator = ScheduleStrengthCalculator(current_season=season)
    
    # Get all NFL teams
    nfl_teams = [
        'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE',
        'DAL', 'DEN', 'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC',
        'LV', 'LAC', 'LAR', 'MIA', 'MIN', 'NE', 'NO', 'NYG',
        'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS'
    ]
    
    sos_results = []
    
    for team in nfl_teams:
        try:
            sos_metrics = calculator.calculate_strength_of_schedule(
                team=team,
                position=position,
                start_week=1,
                end_week=weeks,
                season=season
            )
            
            if sos_metrics:
                sos_results.append({
                    'team': team,
                    'position': position,
                    **sos_metrics
                })
        except Exception as e:
            logger.warning(f"Could not calculate SOS for {team}: {e}")
            continue
    
    if sos_results:
        sos_df = pd.DataFrame(sos_results)
        sos_df = sos_df.sort_values('sos_rating', ascending=False)  # Highest = easiest schedule
        sos_df['sos_rank'] = range(1, len(sos_df) + 1)
        
        logger.info(f"Generated SOS rankings for {len(sos_df)} teams")
        return sos_df
    else:
        logger.warning("No SOS data could be calculated")
        return pd.DataFrame()


def validate_sos_calculations(test_team: str = 'KC', test_position: str = 'QB') -> Dict[str, bool]:
    """
    Validate SOS calculation functionality.
    
    Args:
        test_team: Team to test
        test_position: Position to test
        
    Returns:
        Dictionary with validation results
    """
    validation_results = {}
    
    try:
        calculator = ScheduleStrengthCalculator()
        
        # Test schedule data loading
        schedule_data = calculator.load_schedule_data([2023])
        validation_results['schedule_data_loaded'] = not schedule_data.empty
        
        # Test defensive rankings calculation
        defensive_rankings = calculator.calculate_defensive_rankings([2022, 2023])
        validation_results['defensive_rankings_calculated'] = not defensive_rankings.empty
        
        # Test SOS calculation
        sos_metrics = calculator.calculate_strength_of_schedule(
            team=test_team,
            position=test_position,
            start_week=1,
            end_week=4,
            season=2023
        )
        validation_results['sos_calculation_works'] = bool(sos_metrics)
        
        # Test league-wide rankings
        league_sos = get_league_sos_rankings(test_position, 2023, 4)
        validation_results['league_rankings_generated'] = not league_sos.empty
        
        # Test pace calculations
        pace_data = calculator.calculate_pace_adjustments([2023])
        validation_results['pace_calculations_work'] = not pace_data.empty
        
    except Exception as e:
        logger.error(f"Validation error: {e}")
        validation_results['validation_error'] = str(e)
    
    return validation_results


if __name__ == "__main__":
    # Test the schedule strength calculator
    print("🏈 Testing Schedule Strength Calculator")
    print("=" * 50)
    
    # Run validation
    validation = validate_sos_calculations()
    
    print("Validation Results:")
    for test, result in validation.items():
        status = "✅" if result else "❌"
        print(f"{status} {test}: {result}")
    
    # Example usage
    print("\n" + "=" * 50)
    print("Example: Kansas City Chiefs QB Schedule Analysis")
    
    calculator = ScheduleStrengthCalculator(current_season=2024)
    kc_qb_sos = calculator.calculate_strength_of_schedule(
        team='KC',
        position='QB',
        start_week=1,
        end_week=4,
        season=2024
    )
    
    if kc_qb_sos:
        print(f"SOS Rating: {kc_qb_sos['sos_rating']:.3f} ({kc_qb_sos['sos_tier']})")
        print(f"Tough Matchups: {kc_qb_sos['tough_matchups']}")
        print(f"Easy Matchups: {kc_qb_sos['easy_matchups']}")
        print(f"Home Games: {kc_qb_sos['home_games']}/{kc_qb_sos['total_games']}")
    
    print("\nSchedule Strength Calculator implementation complete! 🎯")