#!/usr/bin/env python3
"""
Player Filter - Remove retired, inactive, and irrelevant players from rankings.

This module filters out players who shouldn't appear in current fantasy rankings
based on retirement status, age, recent activity, and known status changes.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Set, Optional
import logging

logger = logging.getLogger(__name__)

class PlayerFilter:
    """Filter players based on activity status, age, and relevance for current fantasy season."""
    
    # Known retired players (as of 2024/2025)
    RETIRED_PLAYERS = {
        'Tom Brady', 'Rob Gronkowski', 'Julian Edelman', 'Marshawn Lynch',
        'Antonio Brown', 'Le\'Veon Bell', 'Todd Gurley', 'Cam Newton',
        'Andrew Luck', 'Jason Witten', 'Eli Manning', 'Philip Rivers',
        'Larry Fitzgerald', 'Frank Gore', 'Adrian Peterson'
    }
    
    # Players with major injury concerns or out for season
    INJURY_CONCERNS_2024 = {
        'Jonathan Taylor': 'ankle',  # Will be filtered based on recent stats instead
        'Aaron Rodgers': 'age_risk'  # Age-based filtering will handle this
    }
    
    # Maximum reasonable age by position
    MAX_AGE_BY_POSITION = {
        'QB': 42,   # QBs can play longer (Brady was 45)
        'RB': 32,   # RBs decline quickly after 30
        'WR': 35,   # WRs can play into mid-30s  
        'TE': 36,   # TEs similar to WRs
        'K': 45,    # Kickers can play very long
        'DST': 99   # Defense/Special Teams not age-dependent
    }
    
    def __init__(self):
        """Initialize player filter."""
        self.current_year = 2025
        logger.info("🔍 PlayerFilter initialized for 2025 season")
    
    def filter_active_players(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter DataFrame to include only active, relevant players.
        
        Args:
            df: DataFrame with player data
            
        Returns:
            Filtered DataFrame with only active players
        """
        logger.info(f"🧹 Filtering players for active status (input: {len(df)} players)")
        
        if df.empty:
            logger.warning("Empty DataFrame provided to player filter")
            return df
        
        original_count = len(df)
        filtered_df = df.copy()
        
        # 1. Remove explicitly retired players
        filtered_df = self._remove_retired_players(filtered_df)
        
        # 2. Remove players based on age
        filtered_df = self._remove_overage_players(filtered_df)
        
        # 3. Remove players with no recent activity
        filtered_df = self._remove_inactive_players(filtered_df)
        
        # 4. Remove players with obvious data quality issues
        filtered_df = self._remove_data_quality_issues(filtered_df)
        
        final_count = len(filtered_df)
        removed_count = original_count - final_count
        
        logger.info(f"✅ Player filtering complete:")
        logger.info(f"   Original players: {original_count}")
        logger.info(f"   Filtered players: {final_count}")
        logger.info(f"   Removed players: {removed_count} ({removed_count/original_count*100:.1f}%)")
        
        if 'position' in filtered_df.columns:
            position_counts = dict(filtered_df['position'].value_counts())
            logger.info(f"   Final position breakdown: {position_counts}")
        
        return filtered_df
    
    def _remove_retired_players(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove known retired players."""
        if 'player_name' not in df.columns:
            return df
        
        initial_count = len(df)
        
        # Remove players in retired list
        mask = ~df['player_name'].isin(self.RETIRED_PLAYERS)
        df_filtered = df[mask]
        
        removed_count = initial_count - len(df_filtered)
        if removed_count > 0:
            removed_players = df[~mask]['player_name'].unique()
            logger.info(f"   Removed {removed_count} retired players: {list(removed_players)[:5]}...")
        
        return df_filtered
    
    def _remove_overage_players(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove players who are too old for their position."""
        if 'birth_date' not in df.columns or 'position' not in df.columns:
            logger.info("   No age filtering (missing birth_date or position columns)")
            return df
        
        initial_count = len(df)
        
        # Calculate age
        current_date = date(self.current_year, 1, 1)  # Use Jan 1 of current season
        
        def calculate_age(birth_date_str):
            try:
                if pd.isna(birth_date_str):
                    return None
                # Handle different date formats
                if isinstance(birth_date_str, str):
                    # Try common formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y']:
                        try:
                            birth_date = datetime.strptime(birth_date_str, fmt).date()
                            return (current_date - birth_date).days // 365
                        except ValueError:
                            continue
                return None
            except:
                return None
        
        df['age'] = df['birth_date'].apply(calculate_age)
        
        # Create age filter mask
        def is_reasonable_age(row):
            if pd.isna(row['age']):
                return True  # Keep players without age data
            
            position = row['position']
            age = row['age']
            max_age = self.MAX_AGE_BY_POSITION.get(position, 35)
            
            return age <= max_age
        
        mask = df.apply(is_reasonable_age, axis=1)
        df_filtered = df[mask]
        
        removed_count = initial_count - len(df_filtered)
        if removed_count > 0:
            removed_players = df[~mask][['player_name', 'position', 'age']].drop_duplicates()
            logger.info(f"   Removed {removed_count} overage players:")
            for _, player in removed_players.head(5).iterrows():
                logger.info(f"     {player['player_name']} ({player['position']}, age {player['age']})")
        
        return df_filtered
    
    def _remove_inactive_players(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove players with no recent fantasy activity."""
        if 'fantasy_points_ppr' not in df.columns:
            logger.info("   No activity filtering (missing fantasy_points_ppr column)")
            return df
        
        initial_count = len(df)
        
        # Remove players with 0 or very low fantasy points (likely inactive)
        # But be careful not to remove rookie or backup players
        min_fantasy_points = {
            'QB': 10,   # QBs should have some passing stats
            'RB': 5,    # RBs might be backups
            'WR': 5,    # WRs might be backups  
            'TE': 5,    # TEs might be backups
            'K': 20,    # Kickers should have decent points if active
            'DST': 50   # Defenses should have decent points
        }
        
        def is_active_player(row):
            position = row.get('position', 'UNKNOWN')
            fantasy_points = row.get('fantasy_points_ppr', 0)
            
            # Handle NaN values
            if pd.isna(fantasy_points):
                fantasy_points = 0
            
            min_points = min_fantasy_points.get(position, 5)
            
            # Special case: if games played is 0, likely inactive
            if 'games' in row and row['games'] == 0:
                return False
            
            return fantasy_points >= min_points
        
        mask = df.apply(is_active_player, axis=1)
        df_filtered = df[mask]
        
        removed_count = initial_count - len(df_filtered)
        if removed_count > 0:
            logger.info(f"   Removed {removed_count} inactive players (low fantasy points)")
        
        return df_filtered
    
    def _remove_data_quality_issues(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove players with obvious data quality problems."""
        initial_count = len(df)
        
        # Remove players without names
        if 'player_name' in df.columns:
            mask = df['player_name'].notna() & (df['player_name'] != '') & (df['player_name'] != 'Unknown Player')
            df = df[mask]
        
        # Remove players without positions
        if 'position' in df.columns:
            valid_positions = {'QB', 'RB', 'WR', 'TE', 'K', 'DST'}
            mask = df['position'].isin(valid_positions)
            df = df[mask]
        
        removed_count = initial_count - len(df)
        if removed_count > 0:
            logger.info(f"   Removed {removed_count} players with data quality issues")
        
        return df
    
    def get_elite_players_by_position(self) -> Dict[str, List[str]]:
        """
        Return known elite players that should appear in rankings.
        Used for validation and sanity checking.
        """
        return {
            'QB': [
                'Josh Allen', 'Patrick Mahomes', 'Lamar Jackson', 'Jalen Hurts',
                'Joe Burrow', 'Dak Prescott', 'Tua Tagovailoa', 'Justin Herbert'
            ],
            'RB': [
                'Christian McCaffrey', 'Saquon Barkley', 'Josh Jacobs', 'Derrick Henry',
                'Austin Ekeler', 'Nick Chubb', 'Jonathan Taylor', 'Alvin Kamara',
                'Kenneth Walker III', 'Bijan Robinson'
            ],
            'WR': [
                'Tyreek Hill', 'Davante Adams', 'Stefon Diggs', 'Cooper Kupp',
                'DeAndre Hopkins', 'A.J. Brown', 'Jaylen Waddle', 'DK Metcalf',  
                'Mike Evans', 'Chris Godwin', 'Calvin Ridley'
            ],
            'TE': [
                'Travis Kelce', 'Mark Andrews', 'George Kittle', 'T.J. Hockenson',
                'Kyle Pitts', 'Evan Engram', 'Dallas Goedert'
            ]
        }
    
    def validate_elite_players_present(self, df: pd.DataFrame) -> bool:
        """
        Check if expected elite players are present in the dataset.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            bool: True if most elite players are present
        """
        if 'player_name' not in df.columns or 'position' not in df.columns:
            logger.warning("Cannot validate elite players - missing required columns")
            return False
        
        elite_players = self.get_elite_players_by_position()
        present_count = 0
        total_count = 0
        missing_players = []
        
        for position, players in elite_players.items():
            position_df = df[df['position'] == position]
            position_players = set(position_df['player_name'].values)
            
            for player in players:
                total_count += 1
                if player in position_players:
                    present_count += 1
                else:
                    missing_players.append(f"{player} ({position})")
        
        presence_rate = present_count / total_count if total_count > 0 else 0
        
        logger.info(f"Elite player validation: {present_count}/{total_count} present ({presence_rate:.1%})")
        
        if missing_players:
            logger.warning(f"Missing elite players: {missing_players[:10]}...")
        
        return presence_rate >= 0.7  # Require at least 70% of elite players present


# Create singleton instance
player_filter = PlayerFilter()