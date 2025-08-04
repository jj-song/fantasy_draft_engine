"""
Comprehensive Matchup Analysis System for Fantasy Football

This module provides advanced matchup analysis by combining:
- Defensive strength analysis by position
- Environmental factor integration
- Schedule strength calculations  
- Situational adjustments (primetime, division games, etc.)
- Historical matchup trends

The system generates matchup-adjusted projections that account for:
- Opponent defensive quality
- Weather and venue conditions
- Rest advantages/disadvantages
- Game script implications
- Situational factors

Output includes matchup grades (-3 to +3 scale) and adjusted projections
for more accurate weekly and seasonal fantasy forecasts.
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
import config

# Import our other modules
from src.features.schedule_strength import ScheduleStrengthCalculator
from src.data.weather_integration import WeatherIntegrator
from src.data.stadium_data import StadiumDatabase

logger = logging.getLogger(__name__)


@dataclass
class MatchupGrade:
    """Data class for matchup grades."""
    overall_grade: float      # -3 to +3 scale
    defensive_grade: float    # Opponent defense quality
    environmental_grade: float # Weather/venue factors
    situational_grade: float  # Game situation factors
    confidence: float         # Prediction confidence 0-1
    explanation: str          # Human-readable explanation


@dataclass
class MatchupProjection:
    """Data class for matchup-adjusted projections."""
    base_projection: float
    matchup_adjustment: float
    final_projection: float
    adjustment_factor: float
    matchup_grade: MatchupGrade
    factors_breakdown: Dict[str, float]


class MatchupAnalysisEngine:
    """Comprehensive matchup analysis engine."""
    
    def __init__(self, season: int = None):
        """
        Initialize the matchup analysis engine.
        
        Args:
            season: Current season for analysis
        """
        self.season = season or config.CURRENT_SEASON
        self.schedule_calculator = ScheduleStrengthCalculator(current_season=self.season)
        self.weather_integrator = WeatherIntegrator()
        self.stadium_database = StadiumDatabase()
        
        # Load cached defensive rankings
        self.defensive_rankings = None
        self.pace_adjustments = None
        self._load_cached_data()
    
    def _load_cached_data(self) -> None:
        """Load and cache frequently used data."""
        try:
            # Load defensive rankings
            self.defensive_rankings = self.schedule_calculator.calculate_defensive_rankings(
                seasons=[self.season - 2, self.season - 1]
            )
            
            # Load pace adjustments
            self.pace_adjustments = self.schedule_calculator.calculate_pace_adjustments(
                seasons=[self.season - 1]
            )
            
            logger.info("Cached defensive rankings and pace adjustments")
            
        except Exception as e:
            logger.warning(f"Could not load cached data: {e}")
    
    def analyze_matchup(
        self,
        player_team: str,
        opponent_team: str,
        position: str,
        game_date: datetime = None,
        is_home_game: bool = True,
        game_context: Dict[str, any] = None
    ) -> MatchupGrade:
        """
        Perform comprehensive matchup analysis.
        
        Args:
            player_team: Player's team
            opponent_team: Opponent team
            position: Player position
            game_date: Game date (optional)
            is_home_game: Whether player's team is home
            game_context: Additional game context
            
        Returns:
            MatchupGrade with comprehensive analysis
        """
        game_context = game_context or {}
        
        try:
            # Initialize grades
            defensive_grade = 0.0
            environmental_grade = 0.0
            situational_grade = 0.0
            confidence = 0.8  # Base confidence
            
            # 1. Defensive matchup analysis
            defensive_grade = self._analyze_defensive_matchup(opponent_team, position)
            
            # 2. Environmental factors
            if game_date:
                environmental_grade = self._analyze_environmental_factors(
                    player_team if is_home_game else opponent_team,
                    player_team if not is_home_game else opponent_team,
                    position,
                    game_date
                )
            
            # 3. Situational factors
            situational_grade = self._analyze_situational_factors(
                player_team, opponent_team, game_context
            )
            
            # 4. Calculate overall grade (weighted average)
            overall_grade = (
                defensive_grade * 0.6 +        # Defense is most important
                environmental_grade * 0.25 +    # Environmental factors
                situational_grade * 0.15        # Situational factors
            )
            
            # Ensure grade is within bounds
            overall_grade = np.clip(overall_grade, -3.0, 3.0)
            
            # 5. Generate explanation
            explanation = self._generate_matchup_explanation(
                overall_grade, defensive_grade, environmental_grade, 
                situational_grade, opponent_team, position
            )
            
            # 6. Adjust confidence based on data quality
            confidence = self._calculate_confidence(
                opponent_team, position, game_date
            )
            
            return MatchupGrade(
                overall_grade=overall_grade,
                defensive_grade=defensive_grade,
                environmental_grade=environmental_grade,
                situational_grade=situational_grade,
                confidence=confidence,
                explanation=explanation
            )
            
        except Exception as e:
            logger.error(f"Error analyzing matchup: {e}")
            return MatchupGrade(
                overall_grade=0.0,
                defensive_grade=0.0, 
                environmental_grade=0.0,
                situational_grade=0.0,
                confidence=0.5,
                explanation="Error in matchup analysis"
            )
    
    def _analyze_defensive_matchup(self, opponent_team: str, position: str) -> float:
        """Analyze defensive matchup grade."""
        if self.defensive_rankings is None or self.defensive_rankings.empty:
            return 0.0
        
        try:
            pos_lower = position.lower()
            rating_col = f'{pos_lower}_def_rating'
            recent_rating_col = f'{pos_lower}_recent_def_rating'
            
            # Get most recent defensive rating for opponent
            opponent_def = self.defensive_rankings[
                self.defensive_rankings['team'] == opponent_team
            ].sort_values('week').tail(1)
            
            if opponent_def.empty:
                return 0.0
            
            opponent_def = opponent_def.iloc[0]
            
            # Use recent rating if available, otherwise season rating
            if recent_rating_col in opponent_def and not np.isnan(opponent_def[recent_rating_col]):
                def_rating = opponent_def[recent_rating_col]
            elif rating_col in opponent_def and not np.isnan(opponent_def[rating_col]):
                def_rating = opponent_def[rating_col]
            else:
                return 0.0
            
            # Convert defensive rating to matchup grade
            # Negative def_rating = good defense = bad matchup (negative grade)
            # Positive def_rating = bad defense = good matchup (positive grade)
            matchup_grade = -def_rating * 3  # Scale to -3 to +3 range
            
            return np.clip(matchup_grade, -3.0, 3.0)
            
        except Exception as e:
            logger.warning(f"Error analyzing defensive matchup: {e}")
            return 0.0
    
    def _analyze_environmental_factors(
        self, 
        home_team: str, 
        away_team: str, 
        position: str,
        game_date: datetime
    ) -> float:
        """Analyze environmental factors impact."""
        try:
            # Get environmental factors
            env_factors = self.weather_integrator.get_game_environmental_factors(
                home_team=home_team,
                away_team=away_team,
                game_date=game_date,
                get_weather=False  # Skip weather API for now
            )
            
            if not env_factors:
                return 0.0
            
            environmental_grade = 0.0
            
            # Stadium factors
            stadium_info = env_factors.get('stadium_info', {})
            
            # Dome advantage
            if stadium_info.get('is_dome', False):
                if position in ['QB', 'WR', 'TE']:
                    environmental_grade += 0.3  # Positive for passing positions
                elif position == 'K':
                    environmental_grade += 0.5  # Major advantage for kickers
            
            # Altitude advantage
            altitude = stadium_info.get('altitude', 0)
            if altitude > 3000:
                altitude_factor = (altitude - 3000) / 2280  # Denver factor
                if position == 'K':
                    environmental_grade += altitude_factor * 0.8  # Up to +0.8 for kickers
                elif position == 'QB':
                    environmental_grade += altitude_factor * 0.2  # Up to +0.2 for QBs
            
            # Surface impact (minimal for fantasy)
            if stadium_info.get('field_surface') == 'turf':
                if position in ['RB', 'WR', 'TE']:
                    environmental_grade += 0.1  # Slight speed advantage
            
            # Weather impact (if available)
            if 'weather_impacts' in env_factors and position in env_factors['weather_impacts']:
                weather_impact = env_factors['weather_impacts'][position]
                position_impact = weather_impact.get('position_impact', 1.0)
                
                # Convert impact factor to grade
                if position_impact < 0.95:
                    environmental_grade -= 0.5  # Bad weather penalty
                elif position_impact < 0.98:
                    environmental_grade -= 0.2  # Slight weather penalty
            
            # Travel impact
            travel_impacts = env_factors.get('travel_impacts', {})
            away_impact = travel_impacts.get('away_team_impact', 1.0)
            if away_impact < 0.99:
                environmental_grade -= 0.3  # Travel fatigue penalty
            
            return np.clip(environmental_grade, -2.0, 2.0)
            
        except Exception as e:
            logger.warning(f"Error analyzing environmental factors: {e}")
            return 0.0
    
    def _analyze_situational_factors(
        self, 
        player_team: str, 
        opponent_team: str,
        game_context: Dict[str, any]
    ) -> float:
        """Analyze situational factors."""
        situational_grade = 0.0
        
        try:
            # Division game
            if game_context.get('is_division_game', False):
                situational_grade += 0.1  # Slight variance increase
            
            # Primetime game
            if game_context.get('is_primetime', False):
                # Elite players get boost, others get penalty
                player_tier = game_context.get('player_tier', 'average')
                if player_tier in ['elite', 'premium']:
                    situational_grade += 0.2
                else:
                    situational_grade -= 0.1
            
            # Playoff implications
            if game_context.get('playoff_implications', False):
                situational_grade += 0.1  # All players get slight boost
            
            # Rest advantage
            rest_advantage = game_context.get('rest_advantage', 0)
            if rest_advantage > 0:
                situational_grade += min(rest_advantage / 7 * 0.3, 0.3)  # Up to +0.3
            elif rest_advantage < 0:
                situational_grade += max(rest_advantage / 7 * 0.3, -0.3)  # Up to -0.3
            
            # Rivalry game
            if game_context.get('is_rivalry', False):
                situational_grade += 0.05  # Slight intensity boost
            
            # Weather delay risk
            if game_context.get('weather_delay_risk', False):
                situational_grade -= 0.2  # Potential game disruption
            
            # Coaching changes
            if game_context.get('new_coaching_staff', False):
                situational_grade -= 0.1  # Uncertainty penalty
            
            return np.clip(situational_grade, -1.0, 1.0)
            
        except Exception as e:
            logger.warning(f"Error analyzing situational factors: {e}")
            return 0.0
    
    def _generate_matchup_explanation(
        self,
        overall_grade: float,
        defensive_grade: float,
        environmental_grade: float,
        situational_grade: float,
        opponent_team: str,
        position: str
    ) -> str:
        """Generate human-readable matchup explanation."""
        
        # Overall assessment
        if overall_grade >= 1.5:
            overall_desc = "Excellent"
        elif overall_grade >= 0.5:
            overall_desc = "Good"
        elif overall_grade >= -0.5:
            overall_desc = "Average"
        elif overall_grade >= -1.5:
            overall_desc = "Difficult"
        else:
            overall_desc = "Very Difficult"
        
        explanation = f"{overall_desc} matchup vs {opponent_team}. "
        
        # Defensive component
        if defensive_grade >= 1.0:
            explanation += f"{opponent_team} allows above-average fantasy points to {position}s. "
        elif defensive_grade <= -1.0:
            explanation += f"{opponent_team} has a strong defense against {position}s. "
        
        # Environmental component
        if environmental_grade >= 0.5:
            explanation += "Favorable venue conditions. "
        elif environmental_grade <= -0.5:
            explanation += "Challenging environmental factors. "
        
        # Situational component
        if situational_grade >= 0.3:
            explanation += "Positive situational factors. "
        elif situational_grade <= -0.3:
            explanation += "Some situational concerns. "
        
        return explanation.strip()
    
    def _calculate_confidence(
        self, 
        opponent_team: str, 
        position: str,
        game_date: datetime = None
    ) -> float:
        """Calculate prediction confidence."""
        confidence = 0.8  # Base confidence
        
        try:
            # Reduce confidence if no defensive data
            if self.defensive_rankings is None or self.defensive_rankings.empty:
                confidence -= 0.2
            else:
                # Check if we have recent data for opponent
                pos_lower = position.lower()
                rating_col = f'{pos_lower}_def_rating'
                
                opponent_data = self.defensive_rankings[
                    self.defensive_rankings['team'] == opponent_team
                ]
                
                if opponent_data.empty:
                    confidence -= 0.15
                elif rating_col not in opponent_data.columns:
                    confidence -= 0.1
            
            # Reduce confidence for future games (less data available)
            if game_date and game_date > datetime.now():
                days_ahead = (game_date - datetime.now()).days
                confidence -= min(days_ahead / 30 * 0.1, 0.1)  # Up to -0.1 for 30+ days
            
            # Position-specific confidence adjustments
            position_confidence = {
                'QB': 0.85,   # Most predictable
                'RB': 0.75,   # Injury risk, committee concerns
                'WR': 0.80,   # Target volatility
                'TE': 0.70,   # Most volatile position
                'K': 0.60     # Highly game-dependent
            }
            
            confidence *= position_confidence.get(position, 0.75)
            
            return np.clip(confidence, 0.3, 0.95)
            
        except Exception as e:
            logger.warning(f"Error calculating confidence: {e}")
            return 0.6
    
    def calculate_matchup_adjusted_projection(
        self,
        base_projection: float,
        player_team: str,
        opponent_team: str,
        position: str,
        game_date: datetime = None,
        is_home_game: bool = True,
        game_context: Dict[str, any] = None
    ) -> MatchupProjection:
        """
        Calculate matchup-adjusted fantasy projection.
        
        Args:
            base_projection: Base fantasy point projection
            player_team: Player's team
            opponent_team: Opponent team  
            position: Player position
            game_date: Game date
            is_home_game: Whether player's team is home
            game_context: Additional game context
            
        Returns:
            MatchupProjection with adjusted values
        """
        try:
            # Get matchup grade
            matchup_grade = self.analyze_matchup(
                player_team=player_team,
                opponent_team=opponent_team,
                position=position,
                game_date=game_date,
                is_home_game=is_home_game,
                game_context=game_context
            )
            
            # Convert grade to adjustment factor
            # Grade of +3 = +30% projection, Grade of -3 = -30% projection
            max_adjustment = 0.30  # 30% max adjustment
            adjustment_pct = (matchup_grade.overall_grade / 3.0) * max_adjustment
            adjustment_factor = 1.0 + adjustment_pct
            
            # Apply matchup adjustment
            matchup_adjustment = base_projection * adjustment_pct
            final_projection = base_projection * adjustment_factor
            
            # Create factors breakdown
            factors_breakdown = {
                'base_projection': base_projection,
                'defensive_adjustment': base_projection * (matchup_grade.defensive_grade / 3.0 * max_adjustment * 0.6),
                'environmental_adjustment': base_projection * (matchup_grade.environmental_grade / 3.0 * max_adjustment * 0.25),
                'situational_adjustment': base_projection * (matchup_grade.situational_grade / 3.0 * max_adjustment * 0.15),
                'total_adjustment': matchup_adjustment,
                'adjustment_factor': adjustment_factor
            }
            
            return MatchupProjection(
                base_projection=base_projection,
                matchup_adjustment=matchup_adjustment,
                final_projection=final_projection,
                adjustment_factor=adjustment_factor,
                matchup_grade=matchup_grade,
                factors_breakdown=factors_breakdown
            )
            
        except Exception as e:
            logger.error(f"Error calculating matchup-adjusted projection: {e}")
            return MatchupProjection(
                base_projection=base_projection,
                matchup_adjustment=0.0,
                final_projection=base_projection,
                adjustment_factor=1.0,
                matchup_grade=MatchupGrade(0, 0, 0, 0, 0.5, "Error in calculation"),
                factors_breakdown={'error': str(e)}
            )
    
    def analyze_weekly_matchups(
        self,
        week: int,
        season: int = None,
        positions: List[str] = None
    ) -> pd.DataFrame:
        """
        Analyze all matchups for a given week.
        
        Args:
            week: Week number
            season: Season year
            positions: Positions to analyze
            
        Returns:
            DataFrame with matchup analysis for all games
        """
        if season is None:
            season = self.season
        
        if positions is None:
            positions = ['QB', 'RB', 'WR', 'TE']
        
        try:
            # Load schedule for the week
            if self.schedule_calculator.schedule_data is None:
                self.schedule_calculator.load_schedule_data([season])
            
            schedule = self.schedule_calculator.schedule_data
            if schedule is None or schedule.empty:
                return pd.DataFrame()
            
            week_games = schedule[
                (schedule['season'] == season) &
                (schedule['week'] == week)
            ]
            
            if week_games.empty:
                return pd.DataFrame()
            
            matchup_results = []
            
            for _, game in week_games.iterrows():
                home_team = game['home_team']
                away_team = game['away_team']
                game_date = pd.to_datetime(game.get('game_date', datetime.now()))
                
                # Analyze for each position and team
                for position in positions:
                    # Home team players vs away team defense
                    home_matchup = self.analyze_matchup(
                        player_team=home_team,
                        opponent_team=away_team,
                        position=position,
                        game_date=game_date,
                        is_home_game=True
                    )
                    
                    matchup_results.append({
                        'week': week,
                        'season': season,
                        'game_id': game.get('game_id', f"{away_team}@{home_team}"),
                        'team': home_team,
                        'opponent': away_team,
                        'position': position,
                        'is_home': True,
                        'matchup_grade': home_matchup.overall_grade,
                        'defensive_grade': home_matchup.defensive_grade,
                        'environmental_grade': home_matchup.environmental_grade,
                        'situational_grade': home_matchup.situational_grade,
                        'confidence': home_matchup.confidence,
                        'explanation': home_matchup.explanation
                    })
                    
                    # Away team players vs home team defense
                    away_matchup = self.analyze_matchup(
                        player_team=away_team,
                        opponent_team=home_team,
                        position=position,
                        game_date=game_date,
                        is_home_game=False
                    )
                    
                    matchup_results.append({
                        'week': week,
                        'season': season,
                        'game_id': game.get('game_id', f"{away_team}@{home_team}"),
                        'team': away_team,
                        'opponent': home_team,
                        'position': position,
                        'is_home': False,
                        'matchup_grade': away_matchup.overall_grade,
                        'defensive_grade': away_matchup.defensive_grade,
                        'environmental_grade': away_matchup.environmental_grade,
                        'situational_grade': away_matchup.situational_grade,
                        'confidence': away_matchup.confidence,
                        'explanation': away_matchup.explanation
                    })
            
            return pd.DataFrame(matchup_results)
            
        except Exception as e:
            logger.error(f"Error analyzing weekly matchups: {e}")
            return pd.DataFrame()
    
    def get_best_matchups(
        self,
        week: int,
        position: str,
        season: int = None,
        min_grade: float = 1.0,
        top_n: int = 10
    ) -> pd.DataFrame:
        """Get best matchups for a position in a given week."""
        
        weekly_matchups = self.analyze_weekly_matchups(week, season, [position])
        
        if weekly_matchups.empty:
            return pd.DataFrame()
        
        # Filter and sort
        good_matchups = weekly_matchups[
            (weekly_matchups['position'] == position) &
            (weekly_matchups['matchup_grade'] >= min_grade)
        ].sort_values('matchup_grade', ascending=False).head(top_n)
        
        return good_matchups
    
    def get_worst_matchups(
        self,
        week: int,
        position: str,
        season: int = None,
        max_grade: float = -1.0,
        top_n: int = 10
    ) -> pd.DataFrame:
        """Get worst matchups for a position in a given week."""
        
        weekly_matchups = self.analyze_weekly_matchups(week, season, [position])
        
        if weekly_matchups.empty:
            return pd.DataFrame()
        
        # Filter and sort
        bad_matchups = weekly_matchups[
            (weekly_matchups['position'] == position) &
            (weekly_matchups['matchup_grade'] <= max_grade)
        ].sort_values('matchup_grade', ascending=True).head(top_n)
        
        return bad_matchups


def validate_matchup_analysis() -> Dict[str, bool]:
    """Validate matchup analysis functionality."""
    validation_results = {}
    
    try:
        engine = MatchupAnalysisEngine(season=2024)
        
        # Test matchup analysis
        test_date = datetime(2024, 9, 15, 13, 0)
        
        matchup_grade = engine.analyze_matchup(
            player_team='KC',
            opponent_team='BUF',
            position='QB',
            game_date=test_date,
            is_home_game=True
        )
        
        validation_results['matchup_analysis_works'] = isinstance(matchup_grade, MatchupGrade)
        validation_results['grade_in_range'] = -3 <= matchup_grade.overall_grade <= 3
        validation_results['confidence_valid'] = 0 <= matchup_grade.confidence <= 1
        
        # Test projection adjustment
        test_projection = 22.5
        adjusted_projection = engine.calculate_matchup_adjusted_projection(
            base_projection=test_projection,
            player_team='KC',
            opponent_team='BUF',
            position='QB',
            game_date=test_date,
            is_home_game=True
        )
        
        validation_results['projection_adjustment_works'] = isinstance(adjusted_projection, MatchupProjection)
        validation_results['adjustment_factor_valid'] = adjusted_projection.adjustment_factor > 0
        
        # Test weekly analysis
        weekly_matchups = engine.analyze_weekly_matchups(week=1, season=2024, positions=['QB'])
        validation_results['weekly_analysis_works'] = isinstance(weekly_matchups, pd.DataFrame)
        
        # Test best/worst matchups
        best_matchups = engine.get_best_matchups(week=1, position='QB', season=2024)
        validation_results['best_matchups_works'] = isinstance(best_matchups, pd.DataFrame)
        
    except Exception as e:
        validation_results['validation_error'] = str(e)
    
    return validation_results


if __name__ == "__main__":
    # Test the matchup analysis system
    print("🎯 Testing Matchup Analysis System")
    print("=" * 50)
    
    # Run validation
    validation = validate_matchup_analysis()
    
    print("Validation Results:")
    for test, result in validation.items():
        if isinstance(result, bool):
            status = "✅" if result else "❌"
            print(f"{status} {test}: {result}")
        else:
            print(f"ℹ️  {test}: {result}")
    
    # Example usage
    print("\n" + "=" * 50)
    print("Example: Chiefs QB vs Bills Defense Matchup")
    
    engine = MatchupAnalysisEngine(season=2024)
    
    test_date = datetime(2024, 10, 15, 20, 0)  # Sunday Night Football
    game_context = {
        'is_primetime': True,
        'is_division_game': False,
        'player_tier': 'elite',
        'playoff_implications': True
    }
    
    # Analyze matchup
    matchup = engine.analyze_matchup(
        player_team='KC',
        opponent_team='BUF',
        position='QB',
        game_date=test_date,
        is_home_game=True,
        game_context=game_context
    )
    
    print(f"Overall Grade: {matchup.overall_grade:.2f}")
    print(f"Defensive Grade: {matchup.defensive_grade:.2f}")
    print(f"Environmental Grade: {matchup.environmental_grade:.2f}")
    print(f"Situational Grade: {matchup.situational_grade:.2f}")
    print(f"Confidence: {matchup.confidence:.2f}")
    print(f"Explanation: {matchup.explanation}")
    
    # Test projection adjustment
    base_projection = 24.8
    adjusted = engine.calculate_matchup_adjusted_projection(
        base_projection=base_projection,
        player_team='KC',
        opponent_team='BUF',
        position='QB',
        game_date=test_date,
        is_home_game=True,
        game_context=game_context
    )
    
    print(f"\nProjection Adjustment:")
    print(f"Base: {adjusted.base_projection:.1f}")
    print(f"Adjusted: {adjusted.final_projection:.1f}")
    print(f"Factor: {adjusted.adjustment_factor:.3f}x")
    print(f"Change: {adjusted.matchup_adjustment:+.1f}")
    
    print("\nMatchup Analysis System implementation complete! 🎯")