"""
Common feature calculation utilities for the Fantasy Draft Engine.

This module contains shared utility functions for calculating common features
across different positions, eliminating code duplication and ensuring consistency.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple, Any
import logging
from .logging_config import get_logger
from .error_handling import FeatureEngineeringError


class FeatureCalculator:
    """
    Utility class for common feature calculations across positions.
    
    This class provides standardized methods for calculating common features
    like per-game stats, efficiency metrics, usage rates, and derived features.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the feature calculator.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or get_logger(self.__class__.__name__)
    
    def calculate_per_game_stats(self, df: pd.DataFrame, 
                                stat_columns: List[str],
                                games_column: str = 'games') -> pd.DataFrame:
        """
        Calculate per-game averages for specified statistics.
        
        Args:
            df: DataFrame containing player statistics
            stat_columns: List of column names to calculate per-game stats for
            games_column: Name of the games played column
            
        Returns:
            DataFrame with per-game statistics added
        """
        df_result = df.copy()
        
        if games_column not in df_result.columns:
            self.logger.warning(f"Games column '{games_column}' not found, skipping per-game calculations")
            return df_result
        
        # Replace 0 games with 1 to avoid division by zero
        games_played = df_result[games_column].replace(0, 1)
        
        for col in stat_columns:
            if col in df_result.columns:
                per_game_col = f"{col}_per_game"
                df_result[per_game_col] = df_result[col] / games_played
                df_result[per_game_col] = df_result[per_game_col].fillna(0)
                self.logger.debug(f"Calculated {per_game_col}")
        
        return df_result
    
    def calculate_efficiency_ratios(self, df: pd.DataFrame,
                                  ratio_definitions: Dict[str, Dict[str, str]]) -> pd.DataFrame:
        """
        Calculate efficiency ratios based on provided definitions.
        
        Args:
            df: DataFrame containing player statistics
            ratio_definitions: Dict mapping ratio names to calculation rules
                             Format: {'ratio_name': {'numerator': 'col1', 'denominator': 'col2'}}
            
        Returns:
            DataFrame with efficiency ratios added
        """
        df_result = df.copy()
        
        for ratio_name, definition in ratio_definitions.items():
            numerator_col = definition.get('numerator')
            denominator_col = definition.get('denominator')
            
            if (numerator_col in df_result.columns and 
                denominator_col in df_result.columns):
                
                # Calculate ratio, avoiding division by zero
                mask = df_result[denominator_col] > 0
                df_result[ratio_name] = 0.0
                df_result.loc[mask, ratio_name] = (
                    df_result.loc[mask, numerator_col] / 
                    df_result.loc[mask, denominator_col]
                )
                
                # Fill any remaining NaN values with 0
                df_result[ratio_name] = df_result[ratio_name].fillna(0)
                
                self.logger.debug(f"Calculated efficiency ratio: {ratio_name}")
            else:
                missing_cols = []
                if numerator_col not in df_result.columns:
                    missing_cols.append(numerator_col)
                if denominator_col not in df_result.columns:
                    missing_cols.append(denominator_col)
                
                self.logger.warning(f"Cannot calculate {ratio_name}: missing columns {missing_cols}")
        
        return df_result
    
    def calculate_usage_shares(self, df: pd.DataFrame,
                             share_definitions: Dict[str, Dict[str, str]]) -> pd.DataFrame:
        """
        Calculate usage share metrics against team totals.
        
        Args:
            df: DataFrame containing player statistics
            share_definitions: Dict mapping share names to calculation rules
                             Format: {'share_name': {'player_stat': 'col1', 'team_stat': 'col2'}}
            
        Returns:
            DataFrame with usage share metrics added
        """
        df_result = df.copy()
        
        for share_name, definition in share_definitions.items():
            player_stat = definition.get('player_stat')
            team_stat = definition.get('team_stat')
            
            if (player_stat in df_result.columns and 
                team_stat in df_result.columns):
                
                # Calculate share, avoiding division by zero
                mask = df_result[team_stat] > 0
                df_result[share_name] = 0.0
                df_result.loc[mask, share_name] = (
                    df_result.loc[mask, player_stat] / 
                    df_result.loc[mask, team_stat]
                )
                
                # Clip shares to reasonable range (0-1 for most shares)
                df_result[share_name] = df_result[share_name].clip(0, 2)  # Allow up to 2 for edge cases
                df_result[share_name] = df_result[share_name].fillna(0)
                
                self.logger.debug(f"Calculated usage share: {share_name}")
            else:
                self.logger.warning(f"Cannot calculate {share_name}: missing required columns")
        
        return df_result
    
    def calculate_consistency_metrics(self, df: pd.DataFrame,
                                    stat_columns: List[str],
                                    games_column: str = 'games') -> pd.DataFrame:
        """
        Calculate consistency metrics (coefficient of variation, etc.).
        
        Args:
            df: DataFrame containing player statistics
            stat_columns: List of statistics to calculate consistency for
            games_column: Column name for games played
            
        Returns:
            DataFrame with consistency metrics added
        """
        df_result = df.copy()
        
        if games_column not in df_result.columns:
            self.logger.warning(f"Games column '{games_column}' not found for consistency calculations")
            return df_result
        
        for stat in stat_columns:
            if stat in df_result.columns:
                per_game_col = f"{stat}_per_game"
                cv_col = f"{stat}_consistency"
                
                # Calculate per-game if not already exists
                if per_game_col not in df_result.columns:
                    games_played = df_result[games_column].replace(0, 1)
                    df_result[per_game_col] = df_result[stat] / games_played
                
                # For now, create a placeholder consistency metric
                # In a real implementation, this would use game-by-game data
                mean_per_game = df_result[per_game_col]
                
                # Estimate consistency based on total production vs games
                # Higher games with lower per-game = more consistent
                mask = (df_result[games_column] > 0) & (mean_per_game > 0)
                df_result[cv_col] = 1.0  # Default consistency
                
                # Simple heuristic: more games = more consistency data
                df_result.loc[mask, cv_col] = np.minimum(
                    1.0, 
                    df_result.loc[mask, games_column] / 16  # Scale by full season
                )
                
                self.logger.debug(f"Calculated consistency metric: {cv_col}")
        
        return df_result
    
    def calculate_opportunity_metrics(self, df: pd.DataFrame,
                                    opportunity_definitions: Dict[str, Any]) -> pd.DataFrame:
        """
        Calculate opportunity-based metrics (targets per snap, touches per game, etc.).
        
        Args:
            df: DataFrame containing player statistics  
            opportunity_definitions: Dictionary defining opportunity calculations
            
        Returns:
            DataFrame with opportunity metrics added
        """
        df_result = df.copy()
        
        for metric_name, definition in opportunity_definitions.items():
            try:
                if definition['type'] == 'ratio':
                    # Simple ratio calculation
                    numerator = definition['numerator']
                    denominator = definition['denominator']
                    
                    if numerator in df_result.columns and denominator in df_result.columns:
                        mask = df_result[denominator] > 0
                        df_result[metric_name] = 0.0
                        df_result.loc[mask, metric_name] = (
                            df_result.loc[mask, numerator] / 
                            df_result.loc[mask, denominator]
                        )
                        df_result[metric_name] = df_result[metric_name].fillna(0)
                
                elif definition['type'] == 'sum':
                    # Sum multiple columns
                    columns = definition['columns']
                    available_columns = [col for col in columns if col in df_result.columns]
                    
                    if available_columns:
                        df_result[metric_name] = df_result[available_columns].sum(axis=1)
                    else:
                        df_result[metric_name] = 0
                
                elif definition['type'] == 'weighted_sum':
                    # Weighted sum of columns
                    total = 0
                    for col, weight in definition['weights'].items():
                        if col in df_result.columns:
                            total += df_result[col] * weight
                    df_result[metric_name] = total
                
                self.logger.debug(f"Calculated opportunity metric: {metric_name}")
                
            except Exception as e:
                self.logger.warning(f"Failed to calculate {metric_name}: {e}")
                df_result[metric_name] = 0
        
        return df_result
    
    def calculate_lag_features(self, df: pd.DataFrame,
                             feature_columns: List[str],
                             lag_periods: List[int] = [1],
                             group_by: Optional[str] = 'player_id') -> pd.DataFrame:
        """
        Calculate lagged versions of features (L1, L2, etc.).
        
        Args:
            df: DataFrame containing features to lag
            feature_columns: List of columns to create lag features for
            lag_periods: List of lag periods (e.g., [1, 2] for L1 and L2)
            group_by: Optional column to group by for lag calculations
            
        Returns:
            DataFrame with lag features added
        """
        df_result = df.copy()
        
        # For now, create placeholder lag features
        # In a real implementation, this would sort by season/year and shift within groups
        for col in feature_columns:
            if col in df_result.columns:
                for lag in lag_periods:
                    lag_col = f"{col}_L{lag}"
                    
                    if group_by and group_by in df_result.columns:
                        # Group-wise lag (proper implementation would sort by time)
                        df_result[lag_col] = df_result.groupby(group_by)[col].shift(lag)
                    else:
                        # Simple lag
                        df_result[lag_col] = df_result[col].shift(lag)
                    
                    # Fill NaN values with 0 or forward fill
                    df_result[lag_col] = df_result[lag_col].fillna(0)
                    
                    self.logger.debug(f"Created lag feature: {lag_col}")
        
        return df_result
    
    def calculate_rolling_features(self, df: pd.DataFrame,
                                 feature_columns: List[str],
                                 window_sizes: List[int] = [3, 5],
                                 group_by: Optional[str] = 'player_id') -> pd.DataFrame:
        """
        Calculate rolling window features (3-game average, 5-game sum, etc.).
        
        Args:
            df: DataFrame containing features
            feature_columns: List of columns to calculate rolling features for
            window_sizes: List of window sizes for rolling calculations
            group_by: Optional column to group by for rolling calculations
            
        Returns:
            DataFrame with rolling features added
        """
        df_result = df.copy()
        
        for col in feature_columns:
            if col in df_result.columns:
                for window in window_sizes:
                    mean_col = f"{col}_rolling_{window}_mean"
                    sum_col = f"{col}_rolling_{window}_sum"
                    
                    if group_by and group_by in df_result.columns:
                        # Group-wise rolling calculations
                        df_result[mean_col] = df_result.groupby(group_by)[col].rolling(
                            window=window, min_periods=1
                        ).mean().reset_index(0, drop=True)
                        
                        df_result[sum_col] = df_result.groupby(group_by)[col].rolling(
                            window=window, min_periods=1
                        ).sum().reset_index(0, drop=True)
                    else:
                        # Simple rolling calculations
                        df_result[mean_col] = df_result[col].rolling(
                            window=window, min_periods=1
                        ).mean()
                        
                        df_result[sum_col] = df_result[col].rolling(
                            window=window, min_periods=1
                        ).sum()
                    
                    # Fill any remaining NaN values
                    df_result[mean_col] = df_result[mean_col].fillna(0)
                    df_result[sum_col] = df_result[sum_col].fillna(0)
                    
                    self.logger.debug(f"Created rolling features: {mean_col}, {sum_col}")
        
        return df_result
    
    def calculate_percentile_features(self, df: pd.DataFrame,
                                    feature_columns: List[str],
                                    percentiles: List[float] = [25, 50, 75, 90],
                                    group_by: Optional[str] = None) -> pd.DataFrame:
        """
        Calculate percentile-based features relative to peer groups.
        
        Args:
            df: DataFrame containing features
            feature_columns: List of columns to calculate percentiles for
            percentiles: List of percentiles to calculate (0-100)
            group_by: Optional column to group by (e.g., 'position', 'season')
            
        Returns:
            DataFrame with percentile features added
        """
        df_result = df.copy()
        
        for col in feature_columns:
            if col in df_result.columns:
                for pct in percentiles:
                    pct_col = f"{col}_pct_{int(pct)}"
                    
                    if group_by and group_by in df_result.columns:
                        # Calculate percentiles within groups
                        df_result[pct_col] = df_result.groupby(group_by)[col].rank(pct=True) * 100
                    else:
                        # Calculate overall percentiles
                        df_result[pct_col] = df_result[col].rank(pct=True) * 100
                    
                    # Fill NaN values with median percentile
                    df_result[pct_col] = df_result[pct_col].fillna(50)
                    
                    self.logger.debug(f"Created percentile feature: {pct_col}")
        
        return df_result
    
    def calculate_categorical_features(self, df: pd.DataFrame,
                                     categorical_definitions: Dict[str, Any]) -> pd.DataFrame:
        """
        Calculate categorical features based on continuous variables.
        
        Args:
            df: DataFrame containing source features
            categorical_definitions: Dictionary defining categorical feature rules
            
        Returns:
            DataFrame with categorical features added
        """
        df_result = df.copy()
        
        for feature_name, definition in categorical_definitions.items():
            try:
                source_col = definition['source_column']
                
                if source_col not in df_result.columns:
                    self.logger.warning(f"Source column {source_col} not found for {feature_name}")
                    continue
                
                if definition['type'] == 'bins':
                    # Bin continuous variable into categories
                    bins = definition['bins']
                    labels = definition.get('labels', None)
                    
                    df_result[feature_name] = pd.cut(
                        df_result[source_col], 
                        bins=bins, 
                        labels=labels,
                        include_lowest=True
                    )
                
                elif definition['type'] == 'quantiles':
                    # Create quantile-based categories
                    n_quantiles = definition['n_quantiles']
                    labels = definition.get('labels', None)
                    
                    df_result[feature_name] = pd.qcut(
                        df_result[source_col],
                        q=n_quantiles,
                        labels=labels,
                        duplicates='drop'
                    )
                
                elif definition['type'] == 'threshold':
                    # Simple threshold-based binary feature
                    threshold = definition['threshold']
                    true_label = definition.get('true_label', 'high')
                    false_label = definition.get('false_label', 'low')
                    
                    df_result[feature_name] = np.where(
                        df_result[source_col] >= threshold,
                        true_label,
                        false_label
                    )
                
                # Convert to string to avoid category issues
                df_result[feature_name] = df_result[feature_name].astype(str).fillna('unknown')
                
                self.logger.debug(f"Created categorical feature: {feature_name}")
                
            except Exception as e:
                self.logger.warning(f"Failed to create categorical feature {feature_name}: {e}")
                df_result[feature_name] = 'unknown'
        
        return df_result
    
    def normalize_features(self, df: pd.DataFrame,
                         feature_columns: List[str],
                         method: str = 'z_score',
                         group_by: Optional[str] = None) -> pd.DataFrame:
        """
        Normalize features using specified method.
        
        Args:
            df: DataFrame containing features to normalize
            feature_columns: List of columns to normalize
            method: Normalization method ('z_score', 'min_max', 'rank')
            group_by: Optional column to group by for normalization
            
        Returns:
            DataFrame with normalized features added
        """
        df_result = df.copy()
        
        for col in feature_columns:
            if col in df_result.columns:
                norm_col = f"{col}_norm"
                
                if method == 'z_score':
                    if group_by and group_by in df_result.columns:
                        # Group-wise z-score normalization
                        df_result[norm_col] = df_result.groupby(group_by)[col].transform(
                            lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0
                        )
                    else:
                        # Overall z-score normalization
                        mean_val = df_result[col].mean()
                        std_val = df_result[col].std()
                        if std_val > 0:
                            df_result[norm_col] = (df_result[col] - mean_val) / std_val
                        else:
                            df_result[norm_col] = 0
                
                elif method == 'min_max':
                    if group_by and group_by in df_result.columns:
                        # Group-wise min-max normalization
                        df_result[norm_col] = df_result.groupby(group_by)[col].transform(
                            lambda x: (x - x.min()) / (x.max() - x.min()) if x.max() > x.min() else 0
                        )
                    else:
                        # Overall min-max normalization
                        min_val = df_result[col].min()
                        max_val = df_result[col].max()
                        if max_val > min_val:
                            df_result[norm_col] = (df_result[col] - min_val) / (max_val - min_val)
                        else:
                            df_result[norm_col] = 0
                
                elif method == 'rank':
                    if group_by and group_by in df_result.columns:
                        # Group-wise rank normalization
                        df_result[norm_col] = df_result.groupby(group_by)[col].rank(pct=True)
                    else:
                        # Overall rank normalization
                        df_result[norm_col] = df_result[col].rank(pct=True)
                
                # Fill NaN values with 0
                df_result[norm_col] = df_result[norm_col].fillna(0)
                
                self.logger.debug(f"Normalized feature: {norm_col} using {method}")
        
        return df_result


# Global feature calculator instance
_global_feature_calculator: Optional[FeatureCalculator] = None


def get_feature_calculator() -> FeatureCalculator:
    """
    Get the global feature calculator instance.
    
    Returns:
        FeatureCalculator instance
    """
    global _global_feature_calculator
    
    if _global_feature_calculator is None:
        _global_feature_calculator = FeatureCalculator()
    
    return _global_feature_calculator


# Convenience functions that use the global calculator
def calculate_per_game_stats(df: pd.DataFrame, stat_columns: List[str], 
                           games_column: str = 'games') -> pd.DataFrame:
    """Convenience function for calculating per-game stats."""
    return get_feature_calculator().calculate_per_game_stats(df, stat_columns, games_column)


def calculate_efficiency_ratios(df: pd.DataFrame, 
                              ratio_definitions: Dict[str, Dict[str, str]]) -> pd.DataFrame:
    """Convenience function for calculating efficiency ratios."""
    return get_feature_calculator().calculate_efficiency_ratios(df, ratio_definitions)


def calculate_usage_shares(df: pd.DataFrame,
                         share_definitions: Dict[str, Dict[str, str]]) -> pd.DataFrame:
    """Convenience function for calculating usage shares."""
    return get_feature_calculator().calculate_usage_shares(df, share_definitions)