"""
Draft Ranking Generator

Generates comprehensive fantasy football draft rankings.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import os
from pathlib import Path
from datetime import datetime

from .vor_calculator import VORCalculator


class RankingGenerator:
    """Generate fantasy football draft rankings with VOR calculations."""
    
    def __init__(self, scoring_system: str = 'half_ppr'):
        """
        Initialize ranking generator.
        
        Args:
            scoring_system: Fantasy scoring system (ppr, half_ppr, standard)
        """
        self.scoring_system = scoring_system
        self.vor_calc = VORCalculator()
        self.rankings = None
        
    def generate_rankings(self, player_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Generate overall draft rankings from position-specific data.
        
        Args:
            player_data: Dictionary mapping positions to DataFrames with predictions
            
        Returns:
            DataFrame with overall rankings
        """
        all_players = []
        
        # Combine all position data
        for position, df in player_data.items():
            if df is not None and len(df) > 0:
                pos_df = df.copy()
                pos_df['position'] = position
                
                # Ensure required columns exist
                if 'predicted_points' not in pos_df.columns:
                    if 'fantasy_points_per_game' in pos_df.columns:
                        pos_df['predicted_points'] = pos_df['fantasy_points_per_game']
                    else:
                        print(f"Warning: No predicted points for {position}")
                        continue
                
                all_players.append(pos_df)
        
        if not all_players:
            print("No player data to rank")
            return pd.DataFrame()
        
        # Combine all data
        combined_df = pd.concat(all_players, ignore_index=True)
        
        # Calculate VOR scores
        combined_df = self.vor_calc.calculate_vor_scores(combined_df)
        
        # Sort by VOR descending
        combined_df = combined_df.sort_values('vor', ascending=False)
        
        # Add overall ranking
        combined_df = combined_df.reset_index(drop=True)
        combined_df['overall_rank'] = range(1, len(combined_df) + 1)
        
        # Add position rankings
        combined_df['position_rank'] = combined_df.groupby('position').cumcount() + 1
        
        self.rankings = combined_df
        return combined_df
    
    def create_position_rankings(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Create position-specific rankings.
        
        Args:
            df: DataFrame with overall rankings
            
        Returns:
            Dictionary mapping positions to ranked DataFrames
        """
        position_rankings = {}
        
        for position in df['position'].unique():
            pos_df = df[df['position'] == position].copy()
            pos_df = pos_df.sort_values('predicted_points', ascending=False)
            pos_df = pos_df.reset_index(drop=True)
            pos_df['position_rank'] = range(1, len(pos_df) + 1)
            
            position_rankings[position] = pos_df
        
        return position_rankings
    
    def create_tier_groupings(self, df: pd.DataFrame, tier_gap_threshold: float = 3.0) -> pd.DataFrame:
        """
        Create tier groupings based on VOR score gaps.
        
        Args:
            df: DataFrame with rankings
            tier_gap_threshold: Minimum VOR gap to create new tier
            
        Returns:
            DataFrame with tier assignments
        """
        df = df.copy()
        df['tier'] = 1
        
        for position in df['position'].unique():
            pos_mask = df['position'] == position
            pos_data = df[pos_mask].sort_values('vor', ascending=False)
            
            current_tier = 1
            tier_assignments = [current_tier]
            
            for i in range(1, len(pos_data)):
                vor_gap = pos_data.iloc[i-1]['vor'] - pos_data.iloc[i]['vor']
                
                if vor_gap > tier_gap_threshold:
                    current_tier += 1
                
                tier_assignments.append(current_tier)
            
            # Assign tiers back to original dataframe
            df.loc[pos_mask, 'tier'] = [tier_assignments[list(pos_data.index).index(idx)] for idx in df[pos_mask].index]
        
        return df
    
    def export_rankings(self, df: pd.DataFrame, output_dir: str) -> Dict[str, str]:
        """
        Export rankings to various formats.
        
        Args:
            df: DataFrame with rankings
            output_dir: Directory to save files
            
        Returns:
            Dictionary mapping export types to file paths
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        exported_files = {}
        
        # Overall rankings CSV
        overall_file = os.path.join(output_dir, f'overall_rankings_{timestamp}.csv')
        ranking_cols = ['overall_rank', 'player_name', 'position', 'team', 'predicted_points', 'vor']
        export_cols = [col for col in ranking_cols if col in df.columns]
        df[export_cols].head(100).to_csv(overall_file, index=False)
        exported_files['overall_csv'] = overall_file
        
        # Position-specific rankings
        position_rankings = self.create_position_rankings(df)
        for position, pos_df in position_rankings.items():
            pos_file = os.path.join(output_dir, f'{position.lower()}_rankings_{timestamp}.csv')
            pos_df[export_cols].head(30).to_csv(pos_file, index=False)
            exported_files[f'{position.lower()}_csv'] = pos_file
        
        # Text cheatsheet
        cheatsheet_file = os.path.join(output_dir, f'draft_cheatsheet_{timestamp}.txt')
        self.create_text_cheatsheet(df, cheatsheet_file)
        exported_files['cheatsheet_txt'] = cheatsheet_file
        
        return exported_files
    
    def create_text_cheatsheet(self, df: pd.DataFrame, output_file: str):
        """
        Create a text-based draft cheatsheet.
        
        Args:
            df: DataFrame with rankings
            output_file: Path to output file
        """
        with open(output_file, 'w') as f:
            f.write("=" * 80 + "\\n")
            f.write("FANTASY FOOTBALL DRAFT CHEATSHEET\\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write("=" * 80 + "\\n\\n")
            
            # Top 50 overall
            f.write("TOP 50 OVERALL PLAYERS\\n")
            f.write("-" * 80 + "\\n")
            
            top_50 = df.head(50)
            for _, player in top_50.iterrows():
                name = player.get('player_name', 'Unknown Player')
                position = player.get('position', 'XX')
                team = player.get('team', 'XXX')
                points = player.get('predicted_points', 0)
                rank = player.get('overall_rank', 0)
                
                f.write(f"{rank:3d}. {name:25} {position:3} {team:4} {points:6.2f} pts\\n")
            
            # Position breakdowns
            for position in ['QB', 'RB', 'WR', 'TE', 'K']:
                if position in df['position'].values:
                    f.write(f"\\n\\n{position} RANKINGS\\n")
                    f.write("-" * 40 + "\\n")
                    
                    pos_players = df[df['position'] == position].head(15)
                    for _, player in pos_players.iterrows():
                        name = player.get('player_name', 'Unknown Player')
                        team = player.get('team', 'XXX')
                        points = player.get('predicted_points', 0)
                        pos_rank = player.get('position_rank', 0)
                        
                        f.write(f"{pos_rank:2d}. {name:20} {team:4} {points:6.2f} pts\\n")
    
    def get_ranking_summary(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Get summary statistics for the rankings.
        
        Args:
            df: DataFrame with rankings
            
        Returns:
            Dictionary with summary stats
        """
        summary = {
            'total_players': len(df),
            'positions': list(df['position'].unique()),
            'top_player': df.iloc[0]['player_name'] if len(df) > 0 else None,
            'avg_predicted_points': df['predicted_points'].mean(),
            'vor_range': {
                'max': df['vor'].max(),
                'min': df['vor'].min(),
                'std': df['vor'].std()
            }
        }
        
        # Position counts
        summary['position_counts'] = df['position'].value_counts().to_dict()
        
        return summary