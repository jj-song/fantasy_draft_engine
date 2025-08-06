#!/usr/bin/env python3
"""
Retrain ensemble models with complete historical NFL data (2010-2024).

This script fetches all historical NFL data and retrains the ensemble models
to provide optimal performance with 15 years of training data.
"""

import logging
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
from pathlib import Path
import sys
from datetime import datetime

# Add paths for accessing modules
services_root = Path(__file__).parent.parent.parent
sys.path.append(str(services_root))
sys.path.append(str(services_root / "services" / "data-ingestion" / "src"))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_historical_data(start_year=2010, end_year=2024):
    """
    Fetch historical NFL data for all years.
    
    Args:
        start_year: First year to fetch
        end_year: Last year to fetch
        
    Returns:
        DataFrame with combined historical data
    """
    logger.info(f"🏈 Fetching NFL data for years {start_year}-{end_year}")
    
    try:
        import nfl_data_py as nfl
        
        # Fetch player stats for all years
        years = list(range(start_year, end_year + 1))
        logger.info(f"📊 Fetching data for {len(years)} seasons: {years}")
        
        # Get regular season stats
        df = nfl.import_weekly_data(years, columns=[
            'season', 'week', 'player_id', 'player_name', 'position',
            'recent_team', 'completions', 'attempts', 'passing_yards', 
            'passing_tds', 'interceptions', 'carries', 'rushing_yards', 
            'rushing_tds', 'targets', 'receptions', 'receiving_yards', 
            'receiving_tds', 'fantasy_points_ppr'
        ])
        
        # Filter to regular season only (weeks 1-17/18)
        df = df[df['week'] <= 18].copy()
        
        logger.info(f"✅ Raw data fetched: {len(df)} player-week records")
        
        # Aggregate to season level
        season_stats = df.groupby(['season', 'player_id', 'player_name', 'position', 'recent_team']).agg({
            'completions': 'sum',
            'attempts': 'sum', 
            'passing_yards': 'sum',
            'passing_tds': 'sum',
            'interceptions': 'sum',
            'carries': 'sum',
            'rushing_yards': 'sum',
            'rushing_tds': 'sum',
            'targets': 'sum',
            'receptions': 'sum',
            'receiving_yards': 'sum',
            'receiving_tds': 'sum',
            'fantasy_points_ppr': 'sum',
            'week': 'count'  # This becomes games_played
        }).reset_index()
        
        # Rename games column
        season_stats = season_stats.rename(columns={'week': 'games'})
        
        # Filter for players with meaningful playing time (4+ games)
        season_stats = season_stats[season_stats['games'] >= 4].copy()
        
        # Calculate fantasy points per game
        season_stats['fantasy_points_per_game'] = season_stats['fantasy_points_ppr'] / season_stats['games']
        
        logger.info(f"✅ Aggregated seasonal data: {len(season_stats)} player-seasons")
        logger.info(f"   Years covered: {season_stats['season'].min()}-{season_stats['season'].max()}")
        logger.info(f"   Total games: {season_stats['games'].sum():,}")
        
        return season_stats
        
    except ImportError:
        logger.error("❌ nfl_data_py not installed. Run: pip install nfl_data_py")
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching historical data: {e}")
        raise

def prepare_position_data(df, position):
    """
    Prepare data for a specific position.
    
    Args:
        df: Combined historical DataFrame
        position: Position to filter for
        
    Returns:
        X (features), y (target), feature_names
    """
    logger.info(f"🎯 Preparing data for {position}")
    
    # Filter for position
    pos_data = df[df['position'] == position].copy()
    
    if len(pos_data) == 0:
        logger.warning(f"⚠️ No data found for {position}")
        return None, None, None
    
    # Define position-specific features
    if position == 'QB':
        feature_cols = ['games', 'attempts', 'completions', 'passing_yards', 
                       'passing_tds', 'interceptions', 'carries', 'rushing_yards', 'rushing_tds']
    elif position == 'RB':
        feature_cols = ['games', 'carries', 'rushing_yards', 'rushing_tds',
                       'targets', 'receptions', 'receiving_yards', 'receiving_tds']
    elif position == 'WR':
        feature_cols = ['games', 'targets', 'receptions', 'receiving_yards', 
                       'receiving_tds', 'carries', 'rushing_yards', 'rushing_tds']
    elif position == 'TE':
        feature_cols = ['games', 'targets', 'receptions', 'receiving_yards', 
                       'receiving_tds', 'carries', 'rushing_yards', 'rushing_tds']
    else:
        logger.warning(f"⚠️ Unknown position: {position}")
        return None, None, None
    
    # Prepare features and target
    X = pos_data[feature_cols].copy()
    y = pos_data['fantasy_points_per_game'].copy()
    
    # Fill missing values with 0
    X = X.fillna(0)
    
    # Remove rows with missing targets
    valid_idx = ~y.isnull()
    X = X[valid_idx]
    y = y[valid_idx]
    
    logger.info(f"✅ {position} data prepared: {len(X)} samples, {len(feature_cols)} features")
    logger.info(f"   Season range: {pos_data['season'].min()}-{pos_data['season'].max()}")
    logger.info(f"   Fantasy points range: {y.min():.2f} - {y.max():.2f}")
    
    return X, y, feature_cols

def train_ensemble_model(X, y, position):
    """
    Train RandomForest ensemble model for a position.
    
    Args:
        X: Feature matrix
        y: Target values  
        position: Player position
        
    Returns:
        Trained model
    """
    logger.info(f"🤖 Training ensemble model for {position}")
    
    # Split data for validation
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train RandomForest model
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Validate model
    val_pred = model.predict(X_val)
    r2 = r2_score(y_val, val_pred)
    rmse = np.sqrt(mean_squared_error(y_val, val_pred))
    
    logger.info(f"✅ {position} model trained successfully:")
    logger.info(f"   Training samples: {len(X_train)}")
    logger.info(f"   Validation samples: {len(X_val)}")
    logger.info(f"   R² score: {r2:.3f}")
    logger.info(f"   RMSE: {rmse:.2f} fantasy points")
    
    return model

def save_model(model, position):
    """
    Save trained model to disk.
    
    Args:
        model: Trained model
        position: Player position
    """
    models_dir = Path("/Users/jihoonsong/Documents/projects/fantasy_draft_engine/saved_models")
    models_dir.mkdir(exist_ok=True)
    
    model_path = models_dir / f"{position}_ensemble_model.joblib"
    
    # Save model with metadata
    model_data = {
        'model': model,
        'position': position,
        'trained_at': datetime.now().isoformat(),
        'model_type': 'RandomForestRegressor',
        'training_years': '2010-2024',
        'feature_names': list(model.feature_names_in_),
        'n_features': model.n_features_in_
    }
    
    joblib.dump(model, model_path)
    logger.info(f"💾 {position} model saved to: {model_path}")

def main():
    """Main function to retrain all models with historical data."""
    logger.info("🚀 Starting complete historical model retraining (2010-2024)")
    
    try:
        # Fetch historical data
        historical_data = fetch_historical_data(2010, 2024)
        
        # Save historical data for future use
        data_dir = Path("/Users/jihoonsong/Documents/projects/fantasy_draft_engine/data/processed")
        data_dir.mkdir(parents=True, exist_ok=True)
        historical_data.to_parquet(data_dir / "historical_player_stats_2010_2024.parquet")
        logger.info(f"💾 Historical data saved for future use")
        
        # Train models for each position
        positions = ['QB', 'RB', 'WR', 'TE']
        trained_models = {}
        
        for position in positions:
            logger.info(f"\n{'='*50}")
            logger.info(f"🎯 TRAINING {position} MODEL")
            logger.info(f"{'='*50}")
            
            # Prepare position-specific data
            X, y, feature_cols = prepare_position_data(historical_data, position)
            
            if X is not None and len(X) > 10:  # Need minimum samples
                # Train model
                model = train_ensemble_model(X, y, position)
                trained_models[position] = model
                
                # Save model
                save_model(model, position)
                
                logger.info(f"✅ {position} model training completed successfully")
            else:
                logger.warning(f"⚠️ Insufficient data for {position} model training")
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info(f"🎉 HISTORICAL MODEL RETRAINING COMPLETE")
        logger.info(f"{'='*50}")
        logger.info(f"Models trained: {list(trained_models.keys())}")
        logger.info(f"Historical years: 2010-2024")
        logger.info(f"Total player-seasons: {len(historical_data):,}")
        
        # Show position breakdown
        for position in positions:
            pos_count = len(historical_data[historical_data['position'] == position])
            logger.info(f"  {position}: {pos_count:,} player-seasons")
        
        logger.info("🚀 Models are now ready for production use with 15 years of training data!")
        
    except Exception as e:
        logger.error(f"❌ Historical model retraining failed: {e}")
        raise

if __name__ == "__main__":
    main()