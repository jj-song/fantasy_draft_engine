"""
Centralized column mapping utility for fantasy football data.

This module provides a unified way to handle column mapping and standardization
across different data sources and formats, eliminating code duplication.
"""

from typing import Dict, List, Optional, Set, Union
import pandas as pd
import logging
from .logging_config import get_logger


class ColumnMapper:
    """
    Utility class for standardizing and mapping column names across different data sources.
    
    This class centralizes all the column mapping logic that was previously
    duplicated across position-specific feature engineering modules.
    """
    
    # Standard column mappings for different statistical categories
    PASSING_COLUMNS = {
        'standard_names': {
            'passing_attempts': ['passing_attempts', 'attempts', 'att', 'pass_att', 'completions_attempts'],
            'passing_completions': ['passing_completions', 'completions', 'comp', 'pass_comp'],
            'passing_yards': ['passing_yards', 'pass_yards', 'passing_yds', 'pass_yds'],
            'passing_touchdowns': ['passing_touchdowns', 'passing_tds', 'pass_tds', 'pass_td'],
            'passing_interceptions': ['passing_interceptions', 'interceptions', 'ints', 'pass_int'],
            'sacks': ['sacks', 'sacked', 'sack_count'],
            'sack_yards': ['sack_yards', 'sacked_yards', 'sack_yds'],
            'passer_rating': ['passer_rating', 'qb_rating', 'rating'],
            'air_yards': ['air_yards', 'passing_air_yards', 'air_yds'],
            'yac': ['yards_after_catch', 'yac', 'passing_yac']
        }
    }
    
    RUSHING_COLUMNS = {
        'standard_names': {
            'rushing_attempts': ['rushing_attempts', 'carries', 'rush_att', 'attempts'],
            'rushing_yards': ['rushing_yards', 'rush_yards', 'rushing_yds', 'rush_yds'],
            'rushing_touchdowns': ['rushing_touchdowns', 'rushing_tds', 'rush_tds', 'rush_td'],
            'rushing_fumbles': ['rushing_fumbles', 'fumbles', 'rush_fumbles'],
            'rushing_fumbles_lost': ['rushing_fumbles_lost', 'fumbles_lost', 'rush_fumbles_lost'],
            'yards_per_carry': ['yards_per_carry', 'ypc', 'avg_rush']
        }
    }
    
    RECEIVING_COLUMNS = {
        'standard_names': {
            'targets': ['targets', 'tgts', 'receiving_targets'],
            'receptions': ['receptions', 'rec', 'catches'],
            'receiving_yards': ['receiving_yards', 'rec_yards', 'receiving_yds', 'rec_yds'],
            'receiving_touchdowns': ['receiving_touchdowns', 'receiving_tds', 'rec_tds', 'rec_td'],
            'receiving_fumbles': ['receiving_fumbles', 'rec_fumbles'],
            'receiving_fumbles_lost': ['receiving_fumbles_lost', 'rec_fumbles_lost'],
            'yards_per_reception': ['yards_per_reception', 'ypr', 'avg_rec'],
            'yards_per_target': ['yards_per_target', 'ypt', 'yac_per_target'],
            'catch_rate': ['catch_rate', 'catch_percentage', 'catch_pct'],
            'air_yards_share': ['air_yards_share', 'target_air_yards_share', 'air_yds_share'],
            'wopr': ['wopr', 'weighted_opportunity_rating']
        }
    }
    
    GENERAL_COLUMNS = {
        'standard_names': {
            'player_id': ['player_id', 'gsis_id', 'id', 'player_gsis_id'],
            'player_name': ['player_name', 'name', 'full_name', 'player_display_name'],
            'first_name': ['first_name', 'fname'],
            'last_name': ['last_name', 'lname'],
            'position': ['position', 'pos'],
            'team': ['team', 'tm', 'recent_team', 'current_team'],
            'season': ['season', 'year'],
            'games': ['games', 'games_played', 'g', 'gp'],
            'games_started': ['games_started', 'gs'],
            'age': ['age', 'player_age'],
            'experience': ['experience', 'years_pro', 'seasons'],
            'height': ['height', 'ht'],
            'weight': ['weight', 'wt'],
            'college': ['college', 'college_name'],
            'draft_round': ['draft_round', 'draftround', 'round'],
            'draft_number': ['draft_number', 'draft_position', 'draft_pick'],
            'fantasy_points': ['fantasy_points', 'fpts', 'standard_fantasy_points'],
            'fantasy_points_ppr': ['fantasy_points_ppr', 'ppr_points', 'fpts_ppr']
        }
    }
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the column mapper.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or get_logger(self.__class__.__name__)
        self._custom_mappings = {}
        
    def add_custom_mapping(self, standard_name: str, variations: List[str]) -> None:
        """
        Add a custom column mapping.
        
        Args:
            standard_name: The standardized column name
            variations: List of possible variations of this column name
        """
        self._custom_mappings[standard_name] = variations
        self.logger.debug(f"Added custom mapping: {standard_name} -> {variations}")
    
    def get_column_mapping(self, df: pd.DataFrame, 
                          categories: List[str] = None) -> Dict[str, Optional[str]]:
        """
        Get mapping of standard column names to actual column names in the DataFrame.
        
        Args:
            df: DataFrame to examine
            categories: List of column categories to include ('passing', 'rushing', 'receiving', 'general')
                       If None, includes all categories
        
        Returns:
            Dictionary mapping standard names to actual column names (None if not found)
        """
        available_cols = [col.lower() for col in df.columns]
        mapping = {}
        
        # Define which column sets to use
        if categories is None:
            categories = ['passing', 'rushing', 'receiving', 'general']
        
        column_sets = {}
        if 'passing' in categories:
            column_sets.update(self.PASSING_COLUMNS['standard_names'])
        if 'rushing' in categories:
            column_sets.update(self.RUSHING_COLUMNS['standard_names'])
        if 'receiving' in categories:
            column_sets.update(self.RECEIVING_COLUMNS['standard_names'])
        if 'general' in categories:
            column_sets.update(self.GENERAL_COLUMNS['standard_names'])
        
        # Add custom mappings
        column_sets.update(self._custom_mappings)
        
        # Find matches
        for standard_name, variations in column_sets.items():
            found_col = None
            for variation in variations:
                if variation.lower() in available_cols:
                    # Get the original case column name
                    original_idx = available_cols.index(variation.lower())
                    found_col = df.columns[original_idx]
                    break
            
            mapping[standard_name] = found_col
        
        # Log mapping results
        found_mappings = {k: v for k, v in mapping.items() if v is not None}
        missing_mappings = [k for k, v in mapping.items() if v is None]
        
        self.logger.info(f"Column mapping: {len(found_mappings)} found, {len(missing_mappings)} missing")
        if missing_mappings:
            self.logger.debug(f"Missing columns: {missing_mappings}")
        
        return mapping
    
    def get_position_specific_mapping(self, df: pd.DataFrame, position: str) -> Dict[str, Optional[str]]:
        """
        Get column mapping specific to a player position.
        
        Args:
            df: DataFrame to examine
            position: Player position (QB, RB, WR, TE, K, DST)
        
        Returns:
            Dictionary mapping standard names to actual column names
        """
        position = position.upper()
        
        # Base categories for all positions
        categories = ['general']
        
        # Add position-specific categories
        if position == 'QB':
            categories.extend(['passing', 'rushing'])  # QBs can rush too
        elif position == 'RB':
            categories.extend(['rushing', 'receiving'])  # RBs can catch passes
        elif position in ['WR', 'TE']:
            categories.extend(['receiving'])
        
        return self.get_column_mapping(df, categories)
    
    def standardize_columns(self, df: pd.DataFrame, 
                           categories: List[str] = None,
                           inplace: bool = False) -> pd.DataFrame:
        """
        Rename columns in DataFrame to standard names.
        
        Args:
            df: DataFrame to standardize
            categories: List of column categories to standardize
            inplace: Whether to modify the DataFrame in place
        
        Returns:
            DataFrame with standardized column names
        """
        mapping = self.get_column_mapping(df, categories)
        
        # Create reverse mapping (actual -> standard names)
        rename_mapping = {v: k for k, v in mapping.items() if v is not None}
        
        if inplace:
            df.rename(columns=rename_mapping, inplace=True)
            result_df = df
        else:
            result_df = df.rename(columns=rename_mapping)
        
        if rename_mapping:
            self.logger.info(f"Standardized {len(rename_mapping)} column names")
            self.logger.debug(f"Renamed columns: {list(rename_mapping.keys())}")
        
        return result_df
    
    def get_missing_columns(self, df: pd.DataFrame, 
                           required_columns: List[str]) -> List[str]:
        """
        Get list of required columns that are missing from the DataFrame.
        
        Args:
            df: DataFrame to check
            required_columns: List of required standard column names
        
        Returns:
            List of missing column names
        """
        mapping = self.get_column_mapping(df)
        missing = [col for col in required_columns if mapping.get(col) is None]
        
        if missing:
            self.logger.warning(f"Missing required columns: {missing}")
        
        return missing
    
    def validate_required_columns(self, df: pd.DataFrame, 
                                 required_columns: List[str],
                                 raise_on_missing: bool = True) -> bool:
        """
        Validate that all required columns are present in the DataFrame.
        
        Args:
            df: DataFrame to validate
            required_columns: List of required standard column names
            raise_on_missing: Whether to raise exception if columns are missing
        
        Returns:
            True if all required columns are present
        
        Raises:
            ValueError: If required columns are missing and raise_on_missing is True
        """
        missing = self.get_missing_columns(df, required_columns)
        
        if missing:
            error_msg = f"Missing required columns: {missing}"
            if raise_on_missing:
                raise ValueError(error_msg)
            else:
                self.logger.error(error_msg)
                return False
        
        self.logger.info(f"All {len(required_columns)} required columns found")
        return True
    
    def get_available_categories(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Get which column categories are available in the DataFrame.
        
        Args:
            df: DataFrame to examine
        
        Returns:
            Dictionary mapping categories to lists of available columns
        """
        result = {}
        
        for category in ['passing', 'rushing', 'receiving', 'general']:
            mapping = self.get_column_mapping(df, [category])
            available = [k for k, v in mapping.items() if v is not None]
            if available:
                result[category] = available
        
        return result
    
    def suggest_mappings(self, df: pd.DataFrame, 
                        unknown_columns: List[str] = None) -> Dict[str, List[str]]:
        """
        Suggest possible mappings for unknown columns based on similarity.
        
        Args:
            df: DataFrame containing the columns
            unknown_columns: List of column names to find suggestions for
                           If None, suggests for all unmapped columns
        
        Returns:
            Dictionary mapping unknown columns to lists of suggested standard names
        """
        if unknown_columns is None:
            # Find columns that don't have standard mappings
            mapping = self.get_column_mapping(df)
            mapped_cols = set(v for v in mapping.values() if v is not None)
            unknown_columns = [col for col in df.columns if col not in mapped_cols]
        
        suggestions = {}
        all_standard_names = set()
        
        # Collect all standard names
        for category_dict in [self.PASSING_COLUMNS, self.RUSHING_COLUMNS, 
                             self.RECEIVING_COLUMNS, self.GENERAL_COLUMNS]:
            all_standard_names.update(category_dict['standard_names'].keys())
        
        for col in unknown_columns:
            col_lower = col.lower()
            possible_matches = []
            
            # Look for partial matches
            for standard_name in all_standard_names:
                if (col_lower in standard_name or standard_name in col_lower or
                    any(word in col_lower for word in standard_name.split('_'))):
                    possible_matches.append(standard_name)
            
            if possible_matches:
                suggestions[col] = possible_matches[:3]  # Top 3 suggestions
        
        return suggestions