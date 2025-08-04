"""
Abstract base class for data processing operations.

This module provides a consistent interface for all data processing classes,
ensuring standardized data loading, cleaning, and transformation operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Union, Any
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from .logging_config import get_logger
from .error_handling import DataProcessingError


class BaseDataProcessor(ABC):
    """
    Abstract base class for data processing operations.
    
    This class defines the standard interface for data loading, cleaning,
    and transformation operations throughout the fantasy football system.
    """
    
    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the data processor.
        
        Args:
            name: Name of the data processor
            logger: Optional logger instance
        """
        self.name = name
        self.logger = logger or get_logger(f"{self.__class__.__name__}_{name}")
        self._processing_stats = {}
    
    @abstractmethod
    def process(self, input_data: Union[pd.DataFrame, str, Path]) -> pd.DataFrame:
        """
        Process the input data and return cleaned/transformed output.
        
        Args:
            input_data: Input data (DataFrame, file path, etc.)
            
        Returns:
            Processed DataFrame
            
        Raises:
            DataProcessingError: If processing fails
        """
        pass
    
    @abstractmethod
    def validate_input(self, data: pd.DataFrame) -> bool:
        """
        Validate input data meets processing requirements.
        
        Args:
            data: DataFrame to validate
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            DataProcessingError: If validation fails critically
        """
        pass
    
    @abstractmethod
    def get_expected_columns(self) -> List[str]:
        """
        Get list of columns expected in the input data.
        
        Returns:
            List of expected column names
        """
        pass
    
    def load_data(self, source: Union[str, Path, pd.DataFrame]) -> pd.DataFrame:
        """
        Load data from various sources.
        
        Args:
            source: Data source (file path, DataFrame, etc.)
            
        Returns:
            Loaded DataFrame
            
        Raises:
            DataProcessingError: If loading fails
        """
        try:
            if isinstance(source, pd.DataFrame):
                self.logger.info(f"Using provided DataFrame with {len(source)} rows")
                return source.copy()
            
            source_path = Path(source)
            if not source_path.exists():
                raise DataProcessingError(f"Data source not found: {source_path}")
            
            # Load based on file extension
            if source_path.suffix.lower() == '.parquet':
                df = pd.read_parquet(source_path)
            elif source_path.suffix.lower() == '.csv':
                df = pd.read_csv(source_path)
            else:
                raise DataProcessingError(f"Unsupported file format: {source_path.suffix}")
            
            self.logger.info(f"Loaded {len(df)} rows from {source_path}")
            return df
            
        except Exception as e:
            raise DataProcessingError(f"Failed to load data from {source}: {str(e)}")
    
    def handle_missing_values(self, df: pd.DataFrame,
                            strategy: Dict[str, Union[str, float, int]] = None) -> pd.DataFrame:
        """
        Handle missing values in the DataFrame.
        
        Args:
            df: DataFrame to process
            strategy: Dictionary mapping column names to fill strategies
                     Strategies: 'drop', 'mean', 'median', 'mode', or specific value
            
        Returns:
            DataFrame with missing values handled
        """
        df_result = df.copy()
        
        if strategy is None:
            # Default strategy: fill numeric with 0, categorical with 'Unknown'
            strategy = {}
        
        # Get missing value counts
        missing_counts = df_result.isnull().sum()
        missing_columns = missing_counts[missing_counts > 0].index.tolist()
        
        if not missing_columns:
            self.logger.info("No missing values found")
            return df_result
        
        self.logger.info(f"Handling missing values in {len(missing_columns)} columns")
        
        for col in missing_columns:
            col_strategy = strategy.get(col, 'auto')
            
            if col_strategy == 'drop':
                df_result = df_result.dropna(subset=[col])
                self.logger.debug(f"Dropped rows with missing {col}")
                
            elif col_strategy == 'auto':
                # Auto-detect strategy based on data type
                if pd.api.types.is_numeric_dtype(df_result[col]):
                    df_result[col] = df_result[col].fillna(0)
                    self.logger.debug(f"Filled missing {col} with 0")
                else:
                    df_result[col] = df_result[col].fillna('Unknown')
                    self.logger.debug(f"Filled missing {col} with 'Unknown'")
                    
            elif col_strategy in ['mean', 'median']:
                if pd.api.types.is_numeric_dtype(df_result[col]):
                    fill_value = df_result[col].mean() if col_strategy == 'mean' else df_result[col].median()
                    df_result[col] = df_result[col].fillna(fill_value)
                    self.logger.debug(f"Filled missing {col} with {col_strategy}: {fill_value}")
                else:
                    self.logger.warning(f"Cannot use {col_strategy} for non-numeric column {col}, using 'Unknown'")
                    df_result[col] = df_result[col].fillna('Unknown')
                    
            elif col_strategy == 'mode':
                mode_value = df_result[col].mode()
                if not mode_value.empty:
                    df_result[col] = df_result[col].fillna(mode_value.iloc[0])
                    self.logger.debug(f"Filled missing {col} with mode: {mode_value.iloc[0]}")
                else:
                    df_result[col] = df_result[col].fillna('Unknown')
                    self.logger.debug(f"No mode found for {col}, used 'Unknown'")
                    
            else:
                # Use specific value
                df_result[col] = df_result[col].fillna(col_strategy)
                self.logger.debug(f"Filled missing {col} with: {col_strategy}")
        
        # Update processing stats
        self._processing_stats['missing_values_handled'] = len(missing_columns)
        
        return df_result
    
    def standardize_column_names(self, df: pd.DataFrame,
                                column_mapping: Dict[str, str] = None) -> pd.DataFrame:
        """
        Standardize column names to consistent format.
        
        Args:
            df: DataFrame to process
            column_mapping: Optional mapping of old names to new names
            
        Returns:
            DataFrame with standardized column names
        """
        df_result = df.copy()
        
        if column_mapping:
            # Apply custom mapping
            existing_mappings = {k: v for k, v in column_mapping.items() if k in df_result.columns}
            df_result = df_result.rename(columns=existing_mappings)
            self.logger.info(f"Applied {len(existing_mappings)} column name mappings")
        
        # Standard cleanup: snake_case conversion
        original_columns = df_result.columns.tolist()
        df_result.columns = [
            col.lower().replace(' ', '_').replace('-', '_') 
            for col in df_result.columns
        ]
        
        changed_columns = sum(1 for old, new in zip(original_columns, df_result.columns) if old != new)
        if changed_columns > 0:
            self.logger.debug(f"Standardized {changed_columns} column names to snake_case")
        
        return df_result
    
    def filter_data(self, df: pd.DataFrame,
                   filters: Dict[str, Any] = None) -> pd.DataFrame:
        """
        Apply filters to the DataFrame.
        
        Args:
            df: DataFrame to filter
            filters: Dictionary of column filters
                    Format: {'column': value} or {'column': {'operator': 'value'}}
            
        Returns:
            Filtered DataFrame
        """
        if not filters:
            return df.copy()
        
        df_result = df.copy()
        initial_rows = len(df_result)
        
        for column, condition in filters.items():
            if column not in df_result.columns:
                self.logger.warning(f"Filter column '{column}' not found, skipping")
                continue
            
            if isinstance(condition, dict):
                # Complex condition
                operator = list(condition.keys())[0]
                value = condition[operator]
                
                if operator == 'gt':
                    df_result = df_result[df_result[column] > value]
                elif operator == 'gte':
                    df_result = df_result[df_result[column] >= value]
                elif operator == 'lt':
                    df_result = df_result[df_result[column] < value]
                elif operator == 'lte':
                    df_result = df_result[df_result[column] <= value]
                elif operator == 'eq':
                    df_result = df_result[df_result[column] == value]
                elif operator == 'ne':
                    df_result = df_result[df_result[column] != value]
                elif operator == 'in':
                    df_result = df_result[df_result[column].isin(value)]
                elif operator == 'not_in':
                    df_result = df_result[~df_result[column].isin(value)]
                else:
                    self.logger.warning(f"Unknown operator '{operator}' for column '{column}'")
            else:
                # Simple equality condition
                df_result = df_result[df_result[column] == condition]
        
        final_rows = len(df_result)
        self.logger.info(f"Applied filters: {initial_rows} → {final_rows} rows ({final_rows/initial_rows*100:.1f}% retained)")
        
        # Update processing stats
        self._processing_stats['rows_filtered'] = initial_rows - final_rows
        
        return df_result
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the processing operations performed.
        
        Returns:
            Dictionary of processing statistics
        """
        return self._processing_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self._processing_stats = {}
    
    def get_name(self) -> str:
        """Get the name of this processor."""
        return self.name
    
    def __repr__(self) -> str:
        """String representation of the processor."""
        return f"{self.__class__.__name__}(name='{self.name}')"