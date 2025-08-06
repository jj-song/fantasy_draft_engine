#!/usr/bin/env python3
"""
Parquet File Inspector - View the structure and sample data of generated feature files
"""

import pandas as pd
import numpy as np
from pathlib import Path

def inspect_parquet_file(file_path: str):
    """Detailed inspection of a parquet file"""
    print(f"📂 PARQUET FILE INSPECTION")
    print("=" * 80)
    print(f"File: {file_path}")
    
    # Load the file
    df = pd.read_parquet(file_path)
    
    # Basic info
    print(f"\n📊 BASIC INFO:")
    print(f"   Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"   Memory usage: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    print(f"   File size: {Path(file_path).stat().st_size / 1024 / 1024:.2f} MB")
    
    # Data types
    print(f"\n🔢 DATA TYPES:")
    dtype_counts = df.dtypes.value_counts()
    for dtype, count in dtype_counts.items():
        print(f"   {dtype}: {count} columns")
    
    # Column categories
    print(f"\n📋 COLUMN CATEGORIES:")
    
    # Core stats
    core_stats = ['player_id', 'player_name', 'team', 'position', 'season', 'games']
    core_available = [col for col in core_stats if col in df.columns]
    print(f"   Core ID/Meta: {core_available}")
    
    # Fantasy stats
    fantasy_stats = [col for col in df.columns if 'fantasy' in col.lower()]
    print(f"   Fantasy stats: {fantasy_stats[:5]}{'...' if len(fantasy_stats) > 5 else ''}")
    
    # Per-game stats
    per_game_stats = [col for col in df.columns if 'per_game' in col]
    print(f"   Per-game stats: {per_game_stats}")
    
    # Efficiency metrics
    efficiency_stats = [col for col in df.columns if any(x in col.lower() for x in ['rate', 'percentage', 'per_'])]
    efficiency_stats = [col for col in efficiency_stats if 'per_game' not in col]  # Exclude per_game already shown
    print(f"   Efficiency metrics: {efficiency_stats[:5]}{'...' if len(efficiency_stats) > 5 else ''}")
    
    # Advanced features
    advanced_features = [col for col in df.columns if any(x in col.lower() for x in ['share', 'dual_threat', 'usage'])]
    print(f"   Advanced features: {advanced_features}")
    
    # Show sample data
    print(f"\n🎯 SAMPLE DATA (First 3 players):")
    
    # Select key columns for display
    display_cols = ['player_name', 'team', 'position', 'games', 'age']
    
    # Add position-specific columns
    if 'passing_yards' in df.columns and df['passing_yards'].sum() > 0:
        display_cols.extend(['passing_yards', 'passing_tds', 'fantasy_points_per_game'])
    elif 'rushing_yards' in df.columns and df['rushing_yards'].sum() > 0:
        display_cols.extend(['rushing_yards', 'receiving_yards', 'fantasy_points_per_game'])
    elif 'receiving_yards' in df.columns:
        display_cols.extend(['targets', 'receptions', 'receiving_yards', 'fantasy_points_per_game'])
    
    # Filter to available columns
    display_cols = [col for col in display_cols if col in df.columns]
    
    # Show top players by fantasy points
    top_players = df.nlargest(3, 'fantasy_points_per_game') if 'fantasy_points_per_game' in df.columns else df.head(3)
    
    print(top_players[display_cols].to_string(index=False))
    
    # Show all column names for reference
    print(f"\n📝 ALL COLUMNS ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        if i % 4 == 0:
            print(f"{col}")
        else:
            print(f"{col:<25}", end=" ")
    if len(df.columns) % 4 != 0:
        print()  # Final newline if needed

if __name__ == "__main__":
    # Inspect a QB file as example
    inspect_parquet_file("data/processed/position_specific/qb_features_2024.parquet")
    
    print("\n" + "="*80)
    print("\n💡 TO VIEW OTHER PARQUET FILES:")
    print("python inspect_parquet.py")
    print("\nOr in Python:")
    print("import pandas as pd")
    print("df = pd.read_parquet('data/processed/position_specific/rb_features_2024.parquet')")
    print("print(df.head())")
    print("print(df.columns.tolist())")
    print("print(df.describe())")