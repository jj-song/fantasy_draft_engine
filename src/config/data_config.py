"""
Data-related configuration for the Fantasy Draft Engine.

This module contains all configuration related to data acquisition,
processing, file paths, and data validation settings.
"""

from typing import List, Dict, Any
from pathlib import Path
from .base_config import BaseConfig


class DataConfig(BaseConfig):
    """
    Configuration for data acquisition and processing.
    
    This class manages settings related to data sources, file paths,
    processing parameters, and data validation thresholds.
    """
    
    def _initialize(self) -> None:
        """Initialize data configuration values."""
        
        # Data acquisition settings
        self.data_start_year = 2010
        self.data_end_year = 2024
        
        # Training vs inference data split
        self.training_data_end_year = 2023  # Complete seasons for training
        self.inference_data_year = 2024     # Current season for predictions
        self.current_season = 2025          # Season being projected
        
        # Player positions to include
        self.positions = ['QB', 'RB', 'WR', 'TE', 'K']  # DST handled separately
        self.core_positions = ['QB', 'RB', 'WR', 'TE']  # Positions with full feature engineering
        
        # File and directory paths
        self.raw_data_dir = 'data/raw'
        self.processed_data_dir = 'data/processed'
        self.feature_data_dir = 'data/processed/position_specific'
        self.model_dir = 'saved_models'
        self.draft_lists_dir = 'data/draft_lists'
        self.logs_dir = 'logs'
        
        # Data quality thresholds
        self.min_games_threshold = 4  # Minimum games for sufficient data
        self.max_missing_data_ratio = 0.3  # Maximum allowed missing data ratio
        self.outlier_std_threshold = 3.0  # Standard deviations for outlier detection
        
        # Data processing settings
        self.chunk_size = 10000  # For processing large datasets
        self.parallel_workers = -1  # Number of parallel workers (-1 = all cores)
        
        # File formats
        self.default_data_format = 'parquet'  # Default file format for processed data
        self.supported_formats = ['parquet', 'csv', 'json']
        
        # Caching settings
        self.enable_data_cache = True
        self.cache_expiry_hours = 24
        self.max_cache_size_mb = 500
        
        # Data validation settings
        self.required_player_columns = [
            'player_id', 'player_name', 'position', 'team', 'season'
        ]
        
        self.required_stat_columns_by_position = {
            'QB': ['passing_attempts', 'passing_yards', 'passing_touchdowns'],
            'RB': ['rushing_attempts', 'rushing_yards', 'rushing_touchdowns'],
            'WR': ['targets', 'receptions', 'receiving_yards'],
            'TE': ['targets', 'receptions', 'receiving_yards'],
            'K': ['field_goal_attempts', 'field_goals_made'],
            'DST': ['points_allowed', 'yards_allowed']
        }
        
        # Data source settings
        self.primary_data_source = 'nfl_data_py'
        self.backup_data_sources = ['local_cache', 'manual_files']
        
        # NFL data specific settings
        self.nfl_data_columns_to_fetch = [
            'player_id', 'player_name', 'position', 'team', 'season', 'games',
            'passing_attempts', 'passing_completions', 'passing_yards', 'passing_touchdowns', 'interceptions',
            'rushing_attempts', 'rushing_yards', 'rushing_touchdowns',
            'targets', 'receptions', 'receiving_yards', 'receiving_touchdowns',
            'fantasy_points', 'fantasy_points_ppr'
        ]
        
        # Environment-specific overrides
        if self.environment == 'test':
            self._apply_test_overrides()
        elif self.environment == 'production':
            self._apply_production_overrides()
    
    def _apply_test_overrides(self) -> None:
        """Apply test-specific configuration overrides."""
        self.data_start_year = 2020  # Use smaller data range for tests
        self.data_end_year = 2022
        self.chunk_size = 1000
        self.enable_data_cache = False
        self.max_cache_size_mb = 50
        
    def _apply_production_overrides(self) -> None:
        """Apply production-specific configuration overrides."""
        self.chunk_size = 50000  # Larger chunks for production
        self.parallel_workers = 8  # Fixed number of workers for stability
        self.max_cache_size_mb = 2000  # Larger cache for production
        
    def _validate(self) -> None:
        """Validate data configuration values."""
        
        # Validate required fields
        required_fields = [
            'data_start_year', 'data_end_year', 'positions', 'raw_data_dir',
            'processed_data_dir', 'min_games_threshold'
        ]
        self.validate_required_fields(required_fields)
        
        # Validate types
        type_mapping = {
            'data_start_year': int,
            'data_end_year': int,
            'training_data_end_year': int,
            'inference_data_year': int,
            'current_season': int,
            'positions': list,
            'core_positions': list,
            'min_games_threshold': int,
            'chunk_size': int,
            'enable_data_cache': bool
        }
        self.validate_types(type_mapping)
        
        # Validate ranges
        range_mapping = {
            'data_start_year': (2009, 2030),  # Reasonable NFL data range
            'data_end_year': (2009, 2030),
            'min_games_threshold': (1, 17),  # NFL season has max 17 games
            'chunk_size': (100, 1000000),
            'max_missing_data_ratio': (0.0, 1.0),
            'outlier_std_threshold': (1.0, 10.0),
            'cache_expiry_hours': (1, 168),  # 1 hour to 1 week
            'max_cache_size_mb': (10, 10000)
        }
        self.validate_ranges(range_mapping)
        
        # Custom validations
        if self.data_start_year >= self.data_end_year:
            raise ValueError("data_start_year must be less than data_end_year")
        
        if self.training_data_end_year >= self.current_season:
            raise ValueError("training_data_end_year must be less than current_season")
        
        if not all(pos in ['QB', 'RB', 'WR', 'TE', 'K', 'DST'] for pos in self.positions):
            raise ValueError("Invalid positions specified")
        
        if not all(pos in self.positions for pos in self.core_positions):
            raise ValueError("All core_positions must be in positions list")
    
    def get_data_path(self, data_type: str, filename: str = None) -> Path:
        """
        Get path for a specific data type.
        
        Args:
            data_type: Type of data ('raw', 'processed', 'features', 'models', 'draft_lists', 'logs')
            filename: Optional filename to append
            
        Returns:
            Path object for the requested data
        """
        path_mapping = {
            'raw': self.raw_data_dir,
            'processed': self.processed_data_dir,
            'features': self.feature_data_dir,
            'models': self.model_dir,
            'draft_lists': self.draft_lists_dir,
            'logs': self.logs_dir
        }
        
        if data_type not in path_mapping:
            raise ValueError(f"Unknown data type: {data_type}")
        
        base_path = Path(path_mapping[data_type])
        
        if filename:
            return base_path / filename
        else:
            return base_path
    
    def get_season_file_path(self, data_type: str, season: int, 
                           position: str = None, format: str = None) -> Path:
        """
        Get standardized file path for season data.
        
        Args:
            data_type: Type of data ('raw', 'processed', 'features')
            season: NFL season year
            position: Optional position for position-specific files
            format: File format (defaults to default_data_format)
            
        Returns:
            Path object for the season data file
        """
        if format is None:
            format = self.default_data_format
        
        base_path = self.get_data_path(data_type)
        
        if position:
            filename = f"{position.lower()}_season_{season}.{format}"
        else:
            filename = f"player_season_{season}.{format}"
        
        return base_path / filename
    
    def get_years_range(self, include_current: bool = False) -> List[int]:
        """
        Get list of years for data processing.
        
        Args:
            include_current: Whether to include the current inference year
            
        Returns:
            List of year integers
        """
        end_year = self.training_data_end_year
        if include_current:
            end_year = max(self.training_data_end_year, self.inference_data_year)
        
        return list(range(self.data_start_year, end_year + 1))
    
    def get_training_years(self) -> List[int]:
        """Get years used for model training."""
        return list(range(self.data_start_year, self.training_data_end_year + 1))
    
    def get_inference_years(self) -> List[int]:
        """Get years used for inference/prediction."""
        return [self.inference_data_year]
    
    def is_valid_position(self, position: str) -> bool:
        """Check if a position is valid and supported."""
        return position.upper() in [pos.upper() for pos in self.positions]
    
    def is_core_position(self, position: str) -> bool:
        """Check if a position is a core position with full feature engineering."""
        return position.upper() in [pos.upper() for pos in self.core_positions]
    
    def get_required_columns_for_position(self, position: str) -> List[str]:
        """
        Get required columns for a specific position.
        
        Args:
            position: Player position
            
        Returns:
            List of required column names
        """
        required_cols = self.required_player_columns.copy()
        
        position_upper = position.upper()
        if position_upper in self.required_stat_columns_by_position:
            required_cols.extend(self.required_stat_columns_by_position[position_upper])
        
        return required_cols
    
    def should_cache_data(self) -> bool:
        """Check if data caching is enabled for current environment."""
        return self.enable_data_cache and not self.is_test()
    
    def get_cache_settings(self) -> Dict[str, Any]:
        """Get caching configuration as dictionary."""
        return {
            'enabled': self.enable_data_cache,
            'expiry_hours': self.cache_expiry_hours,
            'max_size_mb': self.max_cache_size_mb
        }