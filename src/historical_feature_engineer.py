"""
Historical Feature Engineer for Fantasy Football ML Models

This module creates proper historical features using only past data to predict future performance.
Features are constructed from historical player statistics and trends available before the prediction season.

Key Principles:
- Use only historical data available before prediction time
- Create meaningful statistical aggregations and trends
- No same-season information leakage
- Focus on career patterns and recent performance trends
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class HistoricalFeatureEngineer:
    """
    Creates historical features for fantasy football prediction using only past data.
    
    Builds features that would realistically be available when making predictions
    about future player performance.
    """
    
    def __init__(self, data_dir: str = "data/processed"):
        """
        Initialize historical feature engineer.
        
        Args:
            data_dir: Path to processed data directory
        """
        self.data_dir = Path(data_dir)
        self.position_dir = self.data_dir / "position_specific"
        
        logger.info("🏗️ HistoricalFeatureEngineer initialized")
    
    def create_career_features(self, player_data: pd.DataFrame, target_year: int) -> Dict[str, float]:
        """
        Create career-based features for a player using only data before target year.
        
        Args:
            player_data: Historical data for a single player
            target_year: Year we're predicting (exclude this year's data)
            
        Returns:
            Dictionary of career features
        """
        # Only use data before target year
        historical_data = player_data[player_data['year'] < target_year].copy()
        
        if historical_data.empty:
            return self._get_rookie_features()
        
        features = {}
        
        # Career length and experience
        features['career_years'] = len(historical_data['year'].unique())
        features['years_since_rookie'] = target_year - historical_data['year'].min()
        
        # Fantasy points career statistics
        if 'fantasy_points_per_game' in historical_data.columns:
            fp_data = historical_data['fantasy_points_per_game'].dropna()
            if not fp_data.empty:
                features['career_fp_mean'] = fp_data.mean()
                features['career_fp_std'] = fp_data.std() if len(fp_data) > 1 else 0.0
                features['career_fp_max'] = fp_data.max()
                features['best_season_fp'] = fp_data.max()
                features['worst_season_fp'] = fp_data.min()
                
                # Recent performance (last 3 years)
                recent_years = historical_data[historical_data['year'] >= target_year - 3]
                if not recent_years.empty:
                    recent_fp = recent_years['fantasy_points_per_game'].dropna()
                    if not recent_fp.empty:
                        features['recent_3yr_fp_mean'] = recent_fp.mean()
                        features['recent_vs_career_ratio'] = recent_fp.mean() / fp_data.mean() if fp_data.mean() > 0 else 1.0
                
                # Trend analysis (last 2 years vs previous)
                if features['career_years'] >= 2:
                    last_2_years = historical_data[historical_data['year'] >= target_year - 2]
                    earlier_years = historical_data[historical_data['year'] < target_year - 2]
                    
                    if not last_2_years.empty and not earlier_years.empty:
                        last_2_fp = last_2_years['fantasy_points_per_game'].dropna().mean()
                        earlier_fp = earlier_years['fantasy_points_per_game'].dropna().mean()
                        if earlier_fp > 0:
                            features['performance_trend'] = (last_2_fp - earlier_fp) / earlier_fp
                        else:
                            features['performance_trend'] = 0.0
        
        # Age-related features (if birth_date available)
        if 'birth_date' in historical_data.columns and 'age' in historical_data.columns:
            ages = historical_data['age'].dropna()
            if not ages.empty:
                features['peak_age'] = ages[historical_data['fantasy_points_per_game'].idxmax()] if not historical_data['fantasy_points_per_game'].isna().all() else ages.mean()
                features['current_age'] = target_year - 1990  # Approximation, will be updated with real age
        
        # Consistency metrics
        if 'fantasy_points_per_game' in historical_data.columns:
            fp_data = historical_data['fantasy_points_per_game'].dropna()
            if len(fp_data) > 1:
                features['consistency'] = 1.0 / (1.0 + fp_data.std())  # Higher value = more consistent
                features['boom_bust_ratio'] = len(fp_data[fp_data > fp_data.mean() + fp_data.std()]) / len(fp_data)
        
        return features
    
    def _get_rookie_features(self) -> Dict[str, float]:
        """Get default features for rookie players with no historical data."""
        return {
            'career_years': 0,
            'years_since_rookie': 0,
            'career_fp_mean': 0.0,
            'career_fp_std': 0.0,
            'career_fp_max': 0.0,
            'best_season_fp': 0.0,
            'worst_season_fp': 0.0,
            'recent_3yr_fp_mean': 0.0,
            'recent_vs_career_ratio': 1.0,
            'performance_trend': 0.0,
            'peak_age': 25.0,
            'current_age': 22.0,
            'consistency': 0.0,
            'boom_bust_ratio': 0.0
        }
    
    def engineer_position_features(self, position: str, prediction_year: int) -> pd.DataFrame:
        """
        Engineer historical features for all players of a position for a given prediction year.
        
        Args:
            position: Player position (QB, RB, WR, TE)
            prediction_year: Year we're making predictions for
            
        Returns:
            DataFrame with engineered features
        """
        logger.info(f"🔧 Engineering historical features for {position} - {prediction_year}")
        
        position_path = self.position_dir / position.lower()
        if not position_path.exists():
            raise FileNotFoundError(f"Position data not found: {position_path}")
        
        # Load all available historical data for the position
        all_data = []
        for year in range(2010, 2025):  # Load all available years
            file_path = position_path / f"{position.lower()}_features_{year}.parquet"
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    df['year'] = year
                    all_data.append(df)
                except Exception as e:
                    logger.warning(f"Could not load {file_path}: {e}")
        
        if not all_data:
            raise ValueError(f"No historical data found for {position}")
        
        # Combine all historical data
        combined_data = pd.concat(all_data, ignore_index=True)
        logger.info(f"   Loaded {len(combined_data)} historical records from {len(all_data)} years")
        
        # Get players who played in the prediction year
        prediction_data = combined_data[combined_data['year'] == prediction_year].copy()
        if prediction_data.empty:
            logger.warning(f"No data found for {position} in {prediction_year}")
            return pd.DataFrame()
        
        logger.info(f"   Found {len(prediction_data)} {position} players in {prediction_year}")
        
        # Engineer features for each player
        engineered_features = []
        
        for _, player_row in prediction_data.iterrows():
            # Get all historical data for this player
            player_id = player_row.get('player_id', player_row.get('player_display_name', ''))
            if not player_id:
                continue
                
            player_history = combined_data[
                (combined_data['player_id'] == player_id) | 
                (combined_data['player_display_name'] == player_id)
            ].copy()
            
            # Create career features using only pre-prediction data
            career_features = self.create_career_features(player_history, prediction_year)
            
            # Combine with basic player info
            feature_row = {
                'player_id': player_id,
                'player_display_name': player_row.get('player_display_name', player_id),
                'position': position,
                'prediction_year': prediction_year,
                'birth_date': player_row.get('birth_date'),
                'college_name': player_row.get('college_name'),
            }
            
            # Add current age (calculated properly)
            if 'birth_date' in player_row and pd.notna(player_row['birth_date']):
                try:
                    birth_year = pd.to_datetime(player_row['birth_date']).year
                    feature_row['age'] = prediction_year - birth_year
                    career_features['current_age'] = prediction_year - birth_year
                except:
                    feature_row['age'] = career_features.get('current_age', 25.0)
            else:
                feature_row['age'] = career_features.get('current_age', 25.0)
            
            # Add target variable
            target_col = 'fantasy_points_per_game'
            if target_col in player_row:
                feature_row[target_col] = player_row[target_col]
            
            # Add career features
            feature_row.update(career_features)
            engineered_features.append(feature_row)
        
        # Convert to DataFrame
        result_df = pd.DataFrame(engineered_features)
        
        logger.info(f"   ✅ Engineered features for {len(result_df)} {position} players")
        logger.info(f"   📊 Features created: {len([col for col in result_df.columns if col not in ['player_id', 'player_display_name', 'position', 'prediction_year', 'birth_date', 'college_name', 'fantasy_points_per_game']])} historical features")
        
        return result_df
    
    def create_enhanced_datasets(self, save: bool = True) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Create enhanced historical datasets with proper feature engineering for all positions.
        
        Args:
            save: Whether to save enhanced datasets
            
        Returns:
            Dictionary mapping positions to their enhanced datasets
        """
        logger.info("🚀 Creating enhanced historical datasets...")
        
        positions = ['QB', 'RB', 'WR', 'TE']
        enhanced_datasets = {}
        
        for position in positions:
            try:
                logger.info(f"\n📊 Processing {position} position...")
                
                position_datasets = {
                    'train': pd.DataFrame(),
                    'validation': pd.DataFrame(), 
                    'test': pd.DataFrame()
                }
                
                # Create features for training data (2010-2022)
                train_data_list = []
                for year in range(2010, 2023):  # 2010-2022 for training
                    year_features = self.engineer_position_features(position, year)
                    if not year_features.empty:
                        year_features['split'] = 'train'
                        train_data_list.append(year_features)
                
                if train_data_list:
                    position_datasets['train'] = pd.concat(train_data_list, ignore_index=True)
                
                # Create features for validation data (2023)
                val_features = self.engineer_position_features(position, 2023)
                if not val_features.empty:
                    val_features['split'] = 'validation'
                    position_datasets['validation'] = val_features
                
                # Create features for test data (2024)
                test_features = self.engineer_position_features(position, 2024)
                if not test_features.empty:
                    test_features['split'] = 'test'
                    position_datasets['test'] = test_features
                
                enhanced_datasets[position] = position_datasets
                
                # Log summary
                total_samples = sum(len(df) for df in position_datasets.values())
                logger.info(f"✅ {position} enhanced datasets created:")
                for split_name, df in position_datasets.items():
                    if not df.empty:
                        logger.info(f"   {split_name:>10}: {len(df):>3} samples, {len(df.columns):>2} features")
                logger.info(f"   Total: {total_samples} samples")
                
                # Save datasets if requested
                if save:
                    self._save_enhanced_datasets(position_datasets, position)
                
            except Exception as e:
                logger.error(f"❌ Failed to process {position}: {e}")
                enhanced_datasets[position] = {'train': pd.DataFrame(), 'validation': pd.DataFrame(), 'test': pd.DataFrame()}
        
        return enhanced_datasets
    
    def _save_enhanced_datasets(self, datasets: Dict[str, pd.DataFrame], position: str) -> None:
        """Save enhanced datasets for a position."""
        enhanced_dir = self.data_dir / "enhanced_training"
        enhanced_dir.mkdir(exist_ok=True)
        
        position_dir = enhanced_dir / position.lower()
        position_dir.mkdir(exist_ok=True)
        
        for split_name, df in datasets.items():
            if df.empty:
                continue
                
            filename = f"{position.lower()}_{split_name}_enhanced.parquet"
            filepath = position_dir / filename
            
            try:
                df.to_parquet(filepath, index=False)
                logger.info(f"   💾 Saved {split_name}: {filepath}")
            except Exception as e:
                logger.error(f"   ❌ Failed to save {split_name}: {e}")
        
        # Save metadata
        metadata = {
            'position': position,
            'created_at': datetime.now().isoformat(),
            'datasets': {name: len(df) for name, df in datasets.items()},
            'feature_engineering': 'historical_career_based'
        }
        
        metadata_file = position_dir / f"{position.lower()}_enhanced_metadata.json"
        import json
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)


def main():
    """Test the historical feature engineering."""
    logging.basicConfig(level=logging.INFO)
    
    engineer = HistoricalFeatureEngineer("data/processed")
    
    print("🔧 Historical Feature Engineering")
    print("=" * 50)
    
    # Create enhanced datasets
    enhanced_datasets = engineer.create_enhanced_datasets()
    
    print("\n📊 Enhanced Datasets Summary:")
    print("-" * 40)
    
    total_samples = 0
    for position, datasets in enhanced_datasets.items():
        position_total = sum(len(df) for df in datasets.values() if not df.empty)
        total_samples += position_total
        
        print(f"\n{position} Position: {position_total} total samples")
        for split_name, df in datasets.items():
            if not df.empty:
                feature_count = len([col for col in df.columns if col not in ['player_id', 'player_display_name', 'position', 'prediction_year', 'birth_date', 'college_name', 'fantasy_points_per_game', 'split']])
                target_status = "✅" if 'fantasy_points_per_game' in df.columns else "❌"
                print(f"  {split_name:>10}: {len(df):>3} samples, {feature_count:>2} historical features, target: {target_status}")
    
    print(f"\n🎯 Total enhanced samples: {total_samples}")

if __name__ == "__main__":
    main()