"""
Data storage utilities for data ingestion service.
Stub implementation for microservices architecture.
"""
import pandas as pd
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def ensure_player_name_column(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure player_name column exists in DataFrame"""
    if 'player_name' not in df.columns:
        # NFL data uses various name columns - check in order of preference
        name_column_mappings = [
            'display_name',        # NFL player info
            'player_display_name', # Some seasonal data
            'football_name',       # Alternative NFL name
            'full_name',          # General name column
            'player',             # Generic player column
            'name'               # Generic name column
        ]
        
        found_name_column = None
        for col in name_column_mappings:
            if col in df.columns:
                found_name_column = col
                break
        
        if found_name_column:
            df = df.rename(columns={found_name_column: 'player_name'})
            logger.info(f"Mapped {found_name_column} to player_name")
        else:
            logger.warning("No player name column found, creating empty player_name column")
            df['player_name'] = ''
    return df

def save_raw_data(df: pd.DataFrame, file_path: str) -> None:
    """Save raw data to parquet file"""
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(file_path, index=False)
        logger.info(f"Saved raw data to {file_path}: {len(df)} records")
    except Exception as e:
        logger.error(f"Failed to save raw data to {file_path}: {e}")
        raise

def load_raw_data(file_path: str) -> pd.DataFrame:
    """Load raw data from parquet file"""
    try:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Raw data file not found: {file_path}")
        return pd.read_parquet(file_path)
    except Exception as e:
        logger.error(f"Failed to load raw data from {file_path}: {e}")
        raise