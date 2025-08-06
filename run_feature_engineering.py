#!/usr/bin/env python3
"""
Standalone Feature Engineering Runner
Run feature engineering directly on raw data without microservices dependencies.
"""

import os
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def calculate_per_game_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate per-game statistics for key metrics"""
    logger.info("🔄 Calculating per-game statistics...")
    
    df_features = df.copy()
    
    # Ensure games column exists and handle zero games
    if 'games' not in df_features.columns:
        logger.warning("'games' column not found, cannot calculate per-game stats")
        return df_features
    
    games_played = df_features['games'].copy().replace(0, 1)
    
    # Per-game calculations by position
    per_game_metrics = {
        'fantasy_points': 'fantasy_points_per_game',
        'fantasy_points_ppr': 'fantasy_points_ppr_per_game',
        'passing_yards': 'passing_yards_per_game',
        'rushing_yards': 'rushing_yards_per_game',
        'receiving_yards': 'receiving_yards_per_game',
        'targets': 'targets_per_game',
        'receptions': 'receptions_per_game'
    }
    
    for original_col, per_game_col in per_game_metrics.items():
        if original_col in df_features.columns:
            df_features[per_game_col] = df_features[original_col] / games_played
    
    logger.info(f"✅ Added {len([col for col in per_game_metrics.values() if col in df_features.columns])} per-game metrics")
    return df_features

def calculate_efficiency_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate efficiency metrics (yards per attempt, catch rate, etc.)"""
    logger.info("🔄 Calculating efficiency metrics...")
    
    df_features = df.copy()
    added_metrics = []
    
    # QB efficiency metrics
    if 'attempts' in df_features.columns and 'passing_yards' in df_features.columns:
        qb_mask = (df_features['position'] == 'QB') & (df_features['attempts'] > 0)
        df_features.loc[qb_mask, 'yards_per_attempt'] = (
            df_features.loc[qb_mask, 'passing_yards'] / df_features.loc[qb_mask, 'attempts']
        )
        
        df_features.loc[qb_mask, 'completion_percentage'] = (
            df_features.loc[qb_mask, 'completions'] / df_features.loc[qb_mask, 'attempts']
        ) * 100
        added_metrics.extend(['yards_per_attempt', 'completion_percentage'])
    
    # RB efficiency metrics  
    if 'carries' in df_features.columns and 'rushing_yards' in df_features.columns:
        rb_mask = (df_features['position'] == 'RB') & (df_features['carries'] > 0)
        df_features.loc[rb_mask, 'yards_per_carry'] = (
            df_features.loc[rb_mask, 'rushing_yards'] / df_features.loc[rb_mask, 'carries']
        )
        added_metrics.append('yards_per_carry')
    
    # Receiving efficiency metrics (RB, WR, TE)
    if 'targets' in df_features.columns and 'receptions' in df_features.columns:
        skill_mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['targets'] > 0)
        df_features.loc[skill_mask, 'catch_rate'] = (
            df_features.loc[skill_mask, 'receptions'] / df_features.loc[skill_mask, 'targets']
        ) * 100
        added_metrics.append('catch_rate')
    
    if 'targets' in df_features.columns and 'receiving_yards' in df_features.columns:
        skill_mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['targets'] > 0)
        df_features.loc[skill_mask, 'yards_per_target'] = (
            df_features.loc[skill_mask, 'receiving_yards'] / df_features.loc[skill_mask, 'targets']
        )
        added_metrics.append('yards_per_target')
    
    if 'receptions' in df_features.columns and 'receiving_yards' in df_features.columns:
        skill_mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['receptions'] > 0)
        df_features.loc[skill_mask, 'yards_per_reception'] = (
            df_features.loc[skill_mask, 'receiving_yards'] / df_features.loc[skill_mask, 'receptions']
        )
        added_metrics.append('yards_per_reception')
    
    logger.info(f"✅ Added {len(added_metrics)} efficiency metrics: {added_metrics}")
    return df_features

def calculate_usage_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate team-relative usage metrics"""
    logger.info("🔄 Calculating usage metrics...")
    
    df_features = df.copy()
    
    if 'team' not in df_features.columns:
        logger.warning("'team' column not found, cannot calculate team-relative usage metrics")
        return df_features
    
    # Calculate team totals
    team_agg = df_features.groupby('team').agg({
        'attempts': 'sum',
        'targets': 'sum', 
        'carries': 'sum',
        'rushing_yards': 'sum',
        'receiving_yards': 'sum'
    }).reset_index()
    
    # Rename to team totals
    team_agg.columns = ['team'] + [f'team_{col}' for col in team_agg.columns if col != 'team']
    
    # Merge back with player data
    df_features = pd.merge(df_features, team_agg, on='team', how='left')
    
    added_metrics = []
    
    # Calculate usage shares
    if 'team_targets' in df_features.columns:
        skill_mask = (df_features['position'].isin(['RB', 'WR', 'TE'])) & (df_features['team_targets'] > 0)
        df_features.loc[skill_mask, 'target_share'] = (
            df_features.loc[skill_mask, 'targets'] / df_features.loc[skill_mask, 'team_targets']
        )
        added_metrics.append('target_share')
    
    if 'team_carries' in df_features.columns:
        rb_mask = (df_features['position'] == 'RB') & (df_features['team_carries'] > 0)
        df_features.loc[rb_mask, 'rushing_share'] = (
            df_features.loc[rb_mask, 'carries'] / df_features.loc[rb_mask, 'team_carries']
        )
        added_metrics.append('rushing_share')
    
    logger.info(f"✅ Added {len(added_metrics)} usage metrics: {added_metrics}")
    return df_features

def add_age_and_experience(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Add age and experience features"""
    logger.info("🔄 Adding age and experience features...")
    
    df_features = df.copy()
    added_features = []
    
    # Calculate age from birth_date
    if 'birth_date' in df_features.columns:
        reference_date = datetime(year + 1, 9, 1)  # September 1st of prediction season
        df_features['birth_date'] = pd.to_datetime(df_features['birth_date'], errors='coerce')
        df_features['age'] = df_features['birth_date'].apply(
            lambda bd: reference_date.year - bd.year - ((reference_date.month, reference_date.day) < (bd.month, bd.day)) 
            if pd.notna(bd) else np.nan
        )
        added_features.append('age')
    
    # Estimate experience based on entry_year if available
    if 'entry_year' in df_features.columns:
        df_features['experience'] = (year - df_features['entry_year']).clip(lower=0)
        added_features.append('experience')
    else:
        # Default to 2 years experience if no entry year
        df_features['experience'] = 2
        added_features.append('experience')
    
    logger.info(f"✅ Added {len(added_features)} demographic features: {added_features}")
    return df_features

def engineer_position_features(df: pd.DataFrame, position: str, year: int) -> pd.DataFrame:
    """Engineer features for a specific position"""
    logger.info(f"🔧 Engineering features for {position} position ({len(df)} players)")
    
    # Filter to the specific position
    position_df = df[df['position'] == position].copy()
    
    if position_df.empty:
        logger.warning(f"No {position} players found in data")
        return position_df
    
    # Apply all feature engineering steps
    position_df = calculate_per_game_stats(position_df)
    position_df = calculate_efficiency_metrics(position_df)
    position_df = calculate_usage_metrics(position_df)
    position_df = add_age_and_experience(position_df, year)
    
    # Add position-specific derived features
    if position == 'QB':
        # QB-specific features
        if 'passing_tds' in position_df.columns and 'attempts' in position_df.columns:
            position_df['td_rate'] = (position_df['passing_tds'] / position_df['attempts'].replace(0, 1)) * 100
        if 'interceptions' in position_df.columns and 'attempts' in position_df.columns:
            position_df['int_rate'] = (position_df['interceptions'] / position_df['attempts'].replace(0, 1)) * 100
            
    elif position == 'RB':
        # RB-specific features
        if 'rushing_tds' in position_df.columns and 'carries' in position_df.columns:
            position_df['rushing_td_rate'] = (position_df['rushing_tds'] / position_df['carries'].replace(0, 1)) * 100
        # Dual-threat score (rushing + receiving)
        position_df['dual_threat_score'] = (
            position_df.get('rushing_yards', 0) + position_df.get('receiving_yards', 0)
        )
            
    elif position in ['WR', 'TE']:
        # Receiving-focused features
        if 'receiving_tds' in position_df.columns and 'targets' in position_df.columns:
            position_df['td_per_target'] = (position_df['receiving_tds'] / position_df['targets'].replace(0, 1)) * 100
        # Red zone usage (if available)
        if 'red_zone_targets' in position_df.columns:
            position_df['red_zone_share'] = position_df['red_zone_targets'] / position_df['targets'].replace(0, 1)
    
    # Add metadata
    position_df['feature_year'] = year
    position_df['feature_generation_date'] = datetime.now()
    
    logger.info(f"✅ Generated {len(position_df.columns)} features for {len(position_df)} {position} players")
    
    return position_df

def process_season_features(year: int, raw_data_dir: str, output_dir: str) -> Dict[str, str]:
    """Process feature engineering for one season"""
    logger.info(f"🏗️ PROCESSING SEASON {year} FEATURES")
    logger.info("=" * 60)
    
    # Load raw data
    raw_file = Path(raw_data_dir) / f"player_season_{year}.parquet"
    
    if not raw_file.exists():
        logger.error(f"❌ Raw data file not found: {raw_file}")
        return {}
    
    logger.info(f"📂 Loading raw data from: {raw_file}")
    df = pd.read_parquet(raw_file)
    
    logger.info(f"📊 Loaded data: {len(df)} players, {len(df.columns)} columns")
    
    # Show position breakdown
    if 'position' in df.columns:
        position_counts = df['position'].value_counts()
        logger.info(f"📋 Position breakdown: {dict(position_counts)}")
    
    # Process each position
    positions = ['QB', 'RB', 'WR', 'TE']
    output_files = {}
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    for position in positions:
        logger.info(f"\n🎯 Processing {position} position...")
        
        # Engineer features for this position
        position_features = engineer_position_features(df, position, year)
        
        if not position_features.empty:
            # Save position-specific features
            output_file = output_path / f"{position.lower()}_features_{year}.parquet"
            position_features.to_parquet(output_file, index=False)
            
            output_files[position] = str(output_file)
            logger.info(f"💾 Saved {len(position_features)} {position} records to: {output_file}")
            logger.info(f"   Features: {len(position_features.columns)}")
            logger.info(f"   Sample features: {list(position_features.columns[:5])}...")
        else:
            logger.warning(f"❌ No data generated for {position}")
    
    logger.info(f"\n✅ SEASON {year} COMPLETE")
    logger.info(f"   Generated {len(output_files)} position files: {list(output_files.keys())}")
    
    return output_files

def main():
    """Main function to run feature engineering on all available seasons"""
    logger.info("🚀 FANTASY FOOTBALL FEATURE ENGINEERING")
    logger.info("=" * 80)
    
    # Define paths
    project_root = Path(__file__).parent
    raw_data_dir = project_root / "data" / "raw"
    output_dir = project_root / "data" / "processed" / "position_specific"
    
    logger.info(f"📂 Raw data directory: {raw_data_dir}")
    logger.info(f"📂 Output directory: {output_dir}")
    
    # Find all available seasons
    raw_files = list(raw_data_dir.glob("player_season_*.parquet"))
    available_years = sorted([
        int(f.stem.split('_')[-1]) 
        for f in raw_files
        if f.stem.startswith('player_season_')
    ])
    
    logger.info(f"🗂️ Found {len(available_years)} seasons: {available_years}")
    
    if not available_years:
        logger.error("❌ No raw data files found!")
        return
    
    # Process each season
    total_output_files = {}
    
    for year in available_years:
        try:
            season_files = process_season_features(year, raw_data_dir, output_dir)
            total_output_files[year] = season_files
            
        except Exception as e:
            logger.error(f"❌ Error processing {year}: {e}")
            continue
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("🎉 FEATURE ENGINEERING COMPLETE!")
    logger.info("=" * 80)
    
    total_files = sum(len(files) for files in total_output_files.values())
    logger.info(f"📊 Total seasons processed: {len(total_output_files)}")
    logger.info(f"📊 Total output files: {total_files}")
    
    for year, files in total_output_files.items():
        logger.info(f"   {year}: {len(files)} position files ({list(files.keys())})")
    
    logger.info(f"\n💾 All features saved to: {output_dir}")
    logger.info("🎯 Ready for ML model training!")

if __name__ == "__main__":
    main()