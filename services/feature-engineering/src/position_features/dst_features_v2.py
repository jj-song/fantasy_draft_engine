"""
DST Feature Engineering - Refactored Version

This module contains the DSTFeatureEngineer class that inherits from BaseFeatureEngineer
and implements DST-specific feature engineering using centralized utilities.

This replaces the legacy dst_features.py with a cleaner, more maintainable architecture.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union

from ..core.base_feature_engineer import BaseFeatureEngineer
from ..core.column_mapper import ColumnMapper
from ..core.feature_utils import FeatureCalculator


class DSTFeatureEngineer(BaseFeatureEngineer):
    """
    Feature engineer for defense/special teams (DST) position.
    
    Inherits from BaseFeatureEngineer to provide standardized feature engineering
    with DST-specific calculations and defensive metrics.
    """
    
    def __init__(self):
        """Initialize DST feature engineer with position-specific settings."""
        super().__init__(position='DST')
        self.column_mapper = ColumnMapper()
        self.feature_calculator = FeatureCalculator()
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate that DataFrame contains required DST data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            bool: True if data is valid for DST feature engineering
        """
        if df.empty:
            self.logger.warning("Empty DataFrame provided for DST feature engineering")
            return False
            
        # Check for DST position data
        if 'position' not in df.columns:
            self.logger.error("Missing 'position' column in DataFrame")
            return False
            
        dst_players = df[df['position'].isin(['DST', 'DEF', 'D/ST'])]
        if dst_players.empty:
            self.logger.warning("No DST players found in DataFrame")
            return False
            
        self.logger.info(f"Found {len(dst_players)} DST players for feature engineering")
        return True
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer DST-specific features from player data.
        
        Args:
            df: DataFrame containing player data for this position
            
        Returns:
            DataFrame with engineered features added
        """
        self.logger.info(f"Engineering features for {len(df)} DST records")
        
        if not self.validate_data(df):
            return df
        
        # Filter to DST players only
        dst_df = df[df['position'].isin(['DST', 'DEF', 'D/ST'])].copy()
        
        if dst_df.empty:
            self.logger.warning("No DST players to process")
            return df
        
        try:
            # Step 1: Calculate defensive efficiency metrics
            dst_df = self._calculate_defensive_efficiency(dst_df)
            
            # Step 2: Calculate per-game metrics
            dst_df = self._calculate_per_game_metrics(dst_df)
            
            # Step 3: Calculate turnover metrics
            dst_df = self._calculate_turnover_metrics(dst_df)
            
            # Step 4: Calculate special teams metrics
            dst_df = self._calculate_special_teams_metrics(dst_df)
            
            # Step 5: Calculate strength indicators
            dst_df = self._calculate_strength_indicators(dst_df)
            
            # Replace DST records in original dataframe, preserving new columns
            result_df = df.copy()
            dst_mask = result_df['position'].isin(['DST', 'DEF', 'D/ST'])
            
            # Add new columns from dst_df to result_df
            for col in dst_df.columns:
                if col not in result_df.columns:
                    result_df[col] = np.nan
            
            # Now update the DST rows with all the features
            result_df.loc[dst_mask] = dst_df
            
            self.logger.info(f"DST feature engineering completed successfully")
            return result_df
            
        except Exception as e:
            self.logger.error(f"Error in DST feature engineering: {str(e)}")
            return df
    
    def _get_column_name(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find the first matching column name from a list of possibilities."""
        for name in possible_names:
            if name in df.columns:
                return name
        return None
    
    def _calculate_defensive_efficiency(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate DST defensive efficiency metrics."""
        result = df.copy()
        
        # Map defensive stat columns
        sacks = self._get_column_name(result, ['sacks', 'sacks_total', 'sk'])
        points_allowed = self._get_column_name(result, ['points_allowed', 'pa', 'pts_allowed'])
        yards_allowed = self._get_column_name(result, ['yards_allowed', 'ya', 'total_yards_allowed'])
        pass_yards_allowed = self._get_column_name(result, ['pass_yards_allowed', 'passing_yards_allowed', 'pya'])
        rush_yards_allowed = self._get_column_name(result, ['rush_yards_allowed', 'rushing_yards_allowed', 'rya'])
        
        # Points allowed per game
        games_col = self._get_column_name(result, ['games', 'games_played', 'g'])
        if points_allowed and games_col:
            games = result[games_col].replace(0, 1)
            result['points_allowed_per_game'] = result[points_allowed] / games
        
        # Yards allowed per game
        if yards_allowed and games_col:
            games = result[games_col].replace(0, 1)
            result['yards_allowed_per_game'] = result[yards_allowed] / games
        
        # Pass defense efficiency
        if pass_yards_allowed and games_col:
            games = result[games_col].replace(0, 1)
            result['pass_yards_allowed_per_game'] = result[pass_yards_allowed] / games
        
        # Run defense efficiency
        if rush_yards_allowed and games_col:
            games = result[games_col].replace(0, 1)
            result['rush_yards_allowed_per_game'] = result[rush_yards_allowed] / games
        
        # Sack rate (approximate - would need opponent pass attempts for true rate)
        if sacks and games_col:
            games = result[games_col].replace(0, 1)
            result['sacks_per_game'] = result[sacks] / games
        
        return result
    
    def _calculate_per_game_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate DST per-game metrics."""
        result = df.copy()
        
        # Get games column
        games_col = self._get_column_name(result, ['games', 'games_played', 'g'])
        if not games_col:
            self.logger.warning("No games column found for per-game calculations")
            return result
        
        games = result[games_col].replace(0, 1)
        
        # Map stat columns
        interceptions = self._get_column_name(result, ['interceptions', 'int', 'ints'])
        fumbles_recovered = self._get_column_name(result, ['fumbles_recovered', 'fumbles_rec', 'fr'])
        defensive_tds = self._get_column_name(result, ['defensive_tds', 'def_td', 'dtd'])
        
        # Per-game defensive stats
        if interceptions:
            result['interceptions_per_game'] = result[interceptions] / games
        if fumbles_recovered:
            result['fumbles_recovered_per_game'] = result[fumbles_recovered] / games
        if defensive_tds:
            result['defensive_tds_per_game'] = result[defensive_tds] / games
        
        return result
    
    def _calculate_turnover_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate DST turnover-related metrics."""
        result = df.copy()
        
        # Map turnover columns
        interceptions = self._get_column_name(result, ['interceptions', 'int', 'ints'])
        fumbles_recovered = self._get_column_name(result, ['fumbles_recovered', 'fumbles_rec', 'fr'])
        fumbles_forced = self._get_column_name(result, ['fumbles_forced', 'fumbles_force', 'ff'])
        
        # Total turnovers
        if interceptions and fumbles_recovered:
            result['total_turnovers'] = result[interceptions] + result[fumbles_recovered]
        elif interceptions:
            result['total_turnovers'] = result[interceptions]
        elif fumbles_recovered:
            result['total_turnovers'] = result[fumbles_recovered]
        else:
            result['total_turnovers'] = 0
        
        # Turnover differential (turnovers gained - turnovers lost)
        # Note: For DST, we only track turnovers gained, so this is just total turnovers
        result['turnover_differential'] = result['total_turnovers']
        
        # Turnover rate per game
        games_col = self._get_column_name(result, ['games', 'games_played', 'g'])
        if games_col:
            games = result[games_col].replace(0, 1)
            result['turnovers_per_game'] = result['total_turnovers'] / games
        
        # Ball hawking ability (combination of INTs and FRs)
        if interceptions and fumbles_recovered:
            result['ball_hawking_score'] = (
                result[interceptions] * 1.2 +  # INTs slightly more valuable
                result[fumbles_recovered] * 1.0
            )
        
        return result
    
    def _calculate_special_teams_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate DST special teams metrics."""
        result = df.copy()
        
        # Map special teams columns
        st_tds = self._get_column_name(result, ['special_teams_tds', 'st_td', 'return_tds'])
        kick_return_tds = self._get_column_name(result, ['kick_return_tds', 'kr_td'])
        punt_return_tds = self._get_column_name(result, ['punt_return_tds', 'pr_td'])
        blocked_kicks = self._get_column_name(result, ['blocked_kicks', 'blocks', 'blocked'])
        safeties = self._get_column_name(result, ['safeties', 'safety'])
        
        # Special teams touchdowns
        if st_tds:
            games_col = self._get_column_name(result, ['games', 'games_played', 'g'])
            if games_col:
                games = result[games_col].replace(0, 1)
                result['st_tds_per_game'] = result[st_tds] / games
        
        # Return game impact
        return_tds = 0
        if kick_return_tds:
            return_tds += result[kick_return_tds]
        if punt_return_tds:
            return_tds += result[punt_return_tds]
        result['return_td_total'] = return_tds
        
        # Special plays (blocks, safeties)
        special_plays = 0
        if blocked_kicks:
            special_plays += result[blocked_kicks]
        if safeties:
            special_plays += result[safeties] * 2  # Safeties worth more
        result['special_plays_total'] = special_plays
        
        return result
    
    def _calculate_strength_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate DST strength and reliability indicators."""
        result = df.copy()
        
        # Elite defense indicator (low points allowed)
        if 'points_allowed_per_game' in result.columns:
            result['elite_defense'] = (result['points_allowed_per_game'] <= 18.0).astype(int)
            result['bend_dont_break'] = (
                (result['points_allowed_per_game'] <= 21.0) & 
                (result['points_allowed_per_game'] > 18.0)
            ).astype(int)
        
        # Big play defense (high turnovers + sacks)
        big_play_score = 0
        if 'total_turnovers' in result.columns:
            big_play_score += result['total_turnovers']
        if 'sacks_per_game' in result.columns:
            big_play_score += result['sacks_per_game'] * 16  # Approximate season total
        result['big_play_defense_score'] = big_play_score
        
        # Touchdown upside (defensive + special teams TDs)
        td_upside = 0
        if 'defensive_tds_per_game' in result.columns:
            td_upside += result['defensive_tds_per_game'] * 16  # Season projection
        if 'st_tds_per_game' in result.columns:
            td_upside += result['st_tds_per_game'] * 16  # Season projection
        result['td_upside_score'] = td_upside
        
        # Consistency score (inverse of points allowed variance - placeholder)
        if 'points_allowed_per_game' in result.columns:
            # Favor defenses that allow 18-22 points consistently over boom/bust
            consistency_sweet_spot = 20.0
            result['consistency_score'] = 1.0 / (1.0 + abs(result['points_allowed_per_game'] - consistency_sweet_spot))
        
        # Home field advantage (placeholder - would need home/away splits)
        result['home_field_advantage'] = 0.1  # Neutral default
        
        return result
    
    def get_required_columns(self) -> List[str]:
        """
        Get list of columns required for DST feature engineering.
        
        Returns:
            List of column names that must be present in input data
        """
        return [
            'position',
            'games', 'games_played',  # Alternative names
            'sacks', 'sacks_total',  # Alternative names
            'interceptions', 'int', 'ints',  # Alternative names
            'fumbles_recovered', 'fumbles_rec',  # Alternative names
            'points_allowed', 'pa', 'pts_allowed',  # Alternative names
            'yards_allowed', 'ya', 'total_yards_allowed',  # Alternative names
            'defensive_tds', 'def_td'  # Alternative names
        ]
    
    def get_generated_features(self) -> List[str]:
        """
        Get list of features that will be generated by this engineer.
        
        Returns:
            List of feature names that will be added to the DataFrame
        """
        return [
            # Defensive efficiency
            'points_allowed_per_game',
            'yards_allowed_per_game', 
            'pass_yards_allowed_per_game',
            'rush_yards_allowed_per_game',
            'sacks_per_game',
            
            # Per-game stats
            'interceptions_per_game',
            'fumbles_recovered_per_game',
            'defensive_tds_per_game',
            
            # Turnover metrics
            'total_turnovers',
            'turnover_differential',
            'turnovers_per_game',
            'ball_hawking_score',
            
            # Special teams
            'st_tds_per_game',
            'return_td_total',
            'special_plays_total',
            
            # Strength indicators
            'elite_defense',
            'bend_dont_break',
            'big_play_defense_score',
            'td_upside_score',
            'consistency_score',
            'home_field_advantage'
        ]