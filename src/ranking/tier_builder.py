"""
Tier Builder for Fantasy Football Rankings

Creates player tiers based on various clustering and gap analysis methods.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt


class TierBuilder:
    """Build player tiers for fantasy football draft strategy."""
    
    def __init__(self):
        """Initialize tier builder."""
        self.tier_assignments = {}
        
    def create_value_gap_tiers(self, df: pd.DataFrame, gap_threshold: float = 2.0) -> pd.DataFrame:
        """
        Create tiers based on value gaps between players.
        
        Args:
            df: DataFrame with player rankings and VOR scores
            gap_threshold: Minimum gap in VOR to create new tier
            
        Returns:
            DataFrame with tier assignments
        """
        df = df.copy()
        
        for position in df['position'].unique():
            pos_mask = df['position'] == position
            pos_data = df[pos_mask].sort_values('vor', ascending=False).copy()
            
            if len(pos_data) < 2:
                df.loc[pos_mask, 'tier'] = 1
                continue
            
            # Calculate gaps between consecutive players
            vor_values = pos_data['vor'].values
            gaps = np.diff(vor_values)
            
            # Find tier breaks where gap exceeds threshold
            tier_breaks = np.where(np.abs(gaps) > gap_threshold)[0] + 1
            
            # Assign tier numbers
            tiers = np.ones(len(pos_data), dtype=int)
            current_tier = 1
            
            for i, break_point in enumerate(tier_breaks):
                current_tier += 1
                if i == 0:
                    start_idx = break_point
                else:
                    start_idx = tier_breaks[i-1]
                
                if i == len(tier_breaks) - 1:
                    # Last tier goes to end
                    tiers[break_point:] = current_tier
                else:
                    # Tier up to next break
                    tiers[start_idx:break_point] = current_tier
            
            # Assign back to original dataframe
            df.loc[pos_data.index, 'tier'] = tiers
        
        return df
    
    def create_kmeans_tiers(self, df: pd.DataFrame, n_tiers_per_position: int = 5) -> pd.DataFrame:
        """
        Create tiers using K-means clustering on player stats.
        
        Args:
            df: DataFrame with player stats
            n_tiers_per_position: Number of tiers to create per position
            
        Returns:
            DataFrame with tier assignments
        """
        df = df.copy()
        
        for position in df['position'].unique():
            pos_mask = df['position'] == position
            pos_data = df[pos_mask].copy()
            
            if len(pos_data) < n_tiers_per_position:
                # Not enough players for clustering
                df.loc[pos_mask, 'tier'] = 1
                continue
            
            # Use VOR and predicted points for clustering
            features = pos_data[['vor', 'predicted_points']].fillna(0)
            
            # Fit K-means
            kmeans = KMeans(n_clusters=min(n_tiers_per_position, len(pos_data)), 
                          random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(features)
            
            # Order clusters by average VOR (highest = tier 1)
            cluster_avg_vor = []
            for cluster_id in range(kmeans.n_clusters):
                cluster_mask = cluster_labels == cluster_id
                avg_vor = pos_data.loc[pos_data.index[cluster_mask], 'vor'].mean()
                cluster_avg_vor.append((cluster_id, avg_vor))
            
            # Sort by average VOR descending
            cluster_avg_vor.sort(key=lambda x: x[1], reverse=True)
            
            # Create tier mapping
            tier_mapping = {}
            for tier, (cluster_id, _) in enumerate(cluster_avg_vor, 1):
                tier_mapping[cluster_id] = tier
            
            # Assign tiers
            tiers = [tier_mapping[label] for label in cluster_labels]
            df.loc[pos_data.index, 'tier'] = tiers
        
        return df
    
    def create_percentile_tiers(self, df: pd.DataFrame, 
                               tier_percentiles: List[float] = [90, 75, 50, 25]) -> pd.DataFrame:
        """
        Create tiers based on percentile breaks.
        
        Args:
            df: DataFrame with player rankings
            tier_percentiles: Percentile breaks for tiers (descending order)
            
        Returns:
            DataFrame with tier assignments
        """
        df = df.copy()
        
        for position in df['position'].unique():
            pos_mask = df['position'] == position
            pos_data = df[pos_mask].copy()
            
            if len(pos_data) == 0:
                continue
            
            # Calculate percentile thresholds for this position
            vor_values = pos_data['vor']
            thresholds = [np.percentile(vor_values, p) for p in tier_percentiles]
            
            # Assign tiers
            tiers = np.ones(len(pos_data), dtype=int)
            
            for i, threshold in enumerate(thresholds):
                tier_num = i + 1
                mask = vor_values >= threshold
                tiers[mask] = tier_num
            
            # Assign back to dataframe
            df.loc[pos_data.index, 'tier'] = tiers
        
        return df
    
    def get_tier_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get summary of tier assignments.
        
        Args:
            df: DataFrame with tier assignments
            
        Returns:
            DataFrame summarizing tiers by position
        """
        summary_data = []
        
        for position in df['position'].unique():
            pos_data = df[df['position'] == position]
            
            for tier in sorted(pos_data['tier'].unique()):
                tier_data = pos_data[pos_data['tier'] == tier]
                
                summary_data.append({
                    'position': position,
                    'tier': tier,
                    'player_count': len(tier_data),
                    'avg_vor': tier_data['vor'].mean(),
                    'avg_predicted_points': tier_data['predicted_points'].mean(),
                    'top_player': tier_data.loc[tier_data['vor'].idxmax(), 'player_name']
                })
        
        return pd.DataFrame(summary_data)
    
    def plot_tier_distribution(self, df: pd.DataFrame, position: str = None) -> plt.Figure:
        """
        Plot tier distribution for visualization.
        
        Args:
            df: DataFrame with tier assignments
            position: Specific position to plot (None for all)
            
        Returns:
            matplotlib Figure
        """
        if position:
            plot_data = df[df['position'] == position]
            title = f'{position} Player Tiers'
        else:
            plot_data = df
            title = 'All Position Player Tiers'
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Tier count by position
        tier_counts = plot_data.groupby(['position', 'tier']).size().unstack(fill_value=0)
        tier_counts.plot(kind='bar', ax=ax1, stacked=True)
        ax1.set_title('Players per Tier by Position')
        ax1.set_xlabel('Position')
        ax1.set_ylabel('Number of Players')
        ax1.legend(title='Tier', bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # VOR distribution by tier
        for tier in sorted(plot_data['tier'].unique()):
            tier_data = plot_data[plot_data['tier'] == tier]
            ax2.scatter(tier_data['tier'], tier_data['vor'], 
                       alpha=0.6, label=f'Tier {tier}', s=50)
        
        ax2.set_title('VOR Score by Tier')
        ax2.set_xlabel('Tier')
        ax2.set_ylabel('VOR Score')
        ax2.legend()
        
        plt.suptitle(title)
        plt.tight_layout()
        
        return fig
    
    def compare_tier_methods(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Compare different tier creation methods.
        
        Args:
            df: DataFrame with player data
            
        Returns:
            Dictionary mapping method names to DataFrames with tier assignments
        """
        methods = {}
        
        # Value gap method
        methods['value_gap'] = self.create_value_gap_tiers(df.copy(), gap_threshold=2.0)
        
        # K-means method
        methods['kmeans'] = self.create_kmeans_tiers(df.copy(), n_tiers_per_position=4)
        
        # Percentile method
        methods['percentile'] = self.create_percentile_tiers(df.copy())
        
        return methods
    
    def get_tier_recommendations(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Get tier-based draft recommendations.
        
        Args:
            df: DataFrame with tier assignments
            
        Returns:
            Dictionary with draft strategy recommendations
        """
        recommendations = {}
        
        for position in df['position'].unique():
            pos_data = df[df['position'] == position]
            tier_summary = pos_data['tier'].value_counts().sort_index()
            
            # Identify tier cliff (big drop in player count)
            if len(tier_summary) > 1:
                tier_sizes = tier_summary.values
                biggest_drop_idx = np.argmax(np.diff(tier_sizes))
                cliff_tier = tier_summary.index[biggest_drop_idx + 1]
                
                recommendations[position] = f"Target {position} before Tier {cliff_tier} cliff"
            else:
                recommendations[position] = f"{position} has consistent depth"
        
        return recommendations