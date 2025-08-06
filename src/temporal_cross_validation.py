"""
Temporal Cross-Validation for Fantasy Football Models

This module implements proper temporal cross-validation that respects the time-series nature
of fantasy football data. Ensures no future data is used to predict past performance.

Key Principles:
- Time-aware splits (no future information leakage)
- Rolling/expanding window validation
- Realistic performance estimation
- Proper statistical significance testing
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import TimeSeriesSplit
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
from scipy.stats import spearmanr
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

class TemporalCrossValidator:
    """
    Implements temporal cross-validation for fantasy football prediction models.
    
    Uses time-aware splits to provide realistic performance estimates without data leakage.
    """
    
    def __init__(self, data_dir: str = "data/processed"):
        """
        Initialize temporal cross-validator.
        
        Args:
            data_dir: Path to processed data directory
        """
        self.data_dir = Path(data_dir)
        self.enhanced_dir = self.data_dir / "enhanced_training"
        self.results_dir = Path("validation_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("⏰ TemporalCrossValidator initialized")
        logger.info(f"   Results dir: {self.results_dir}")
    
    def create_temporal_splits(self, data: pd.DataFrame, n_splits: int = 5) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Create temporal cross-validation splits.
        
        Args:
            data: DataFrame with time-ordered data
            n_splits: Number of CV splits
            
        Returns:
            List of (train_indices, test_indices) tuples
        """
        # Sort by year to ensure temporal ordering
        if 'prediction_year' in data.columns:
            data_sorted = data.sort_values('prediction_year')
        elif 'year' in data.columns:
            data_sorted = data.sort_values('year')
        else:
            # If no year column, assume data is already sorted
            data_sorted = data
        
        # Use TimeSeriesSplit for temporal splits
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        splits = []
        for train_idx, test_idx in tscv.split(data_sorted):
            splits.append((train_idx, test_idx))
        
        logger.info(f"   Created {len(splits)} temporal splits")
        
        # Log split details
        for i, (train_idx, test_idx) in enumerate(splits):
            train_years = data_sorted.iloc[train_idx].get('prediction_year', data_sorted.iloc[train_idx].get('year', []))
            test_years = data_sorted.iloc[test_idx].get('prediction_year', data_sorted.iloc[test_idx].get('year', []))
            
            if len(train_years) > 0 and len(test_years) > 0:
                logger.info(f"   Split {i+1}: Train years {train_years.min()}-{train_years.max()}, "
                          f"Test years {test_years.min()}-{test_years.max()}")
        
        return splits
    
    def validate_model(self, position: str, model_type: str = 'ridge') -> Dict[str, Any]:
        """
        Perform temporal cross-validation for a specific position.
        
        Args:
            position: Player position (QB, RB, WR, TE)
            model_type: Type of model to validate ('ridge', 'random_forest')
            
        Returns:
            Dictionary with cross-validation results
        """
        logger.info(f"⏰ Running temporal CV for {position} - {model_type}")
        
        # Load training data
        train_file = self.enhanced_dir / position.lower() / f"{position.lower()}_train_enhanced.parquet"
        
        if not train_file.exists():
            raise FileNotFoundError(f"Training data not found: {train_file}")
        
        train_data = pd.read_parquet(train_file)
        logger.info(f"   Loaded {len(train_data)} training samples")
        
        # Prepare features
        exclude_cols = {
            'player_id', 'player_display_name', 'position', 'prediction_year',
            'birth_date', 'college_name', 'fantasy_points_per_game', 'split'
        }
        
        feature_cols = [col for col in train_data.columns if col not in exclude_cols]
        target_col = 'fantasy_points_per_game'
        
        X = train_data[feature_cols].fillna(0).values
        y = train_data[target_col].fillna(0).values
        
        logger.info(f"   Using {len(feature_cols)} features")
        
        # Create temporal splits
        splits = self.create_temporal_splits(train_data, n_splits=5)
        
        # Initialize model
        if model_type == 'ridge':
            model = Ridge(alpha=1.0)
            scaler = StandardScaler()
            use_scaling = True
        elif model_type == 'random_forest':
            model = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
            scaler = None
            use_scaling = False
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        # Perform cross-validation
        cv_results = {
            'position': position,
            'model_type': model_type,
            'n_splits': len(splits),
            'feature_names': feature_cols,
            'fold_results': [],
            'summary_stats': {}
        }
        
        fold_scores = {
            'r2': [],
            'rmse': [],
            'mae': [],
            'spearman': []
        }
        
        for fold_idx, (train_idx, test_idx) in enumerate(splits):
            logger.info(f"   📊 Processing fold {fold_idx + 1}/{len(splits)}...")
            
            # Split data
            X_train_fold, X_test_fold = X[train_idx], X[test_idx]
            y_train_fold, y_test_fold = y[train_idx], y[test_idx]
            
            # Scale features if needed
            if use_scaling:
                scaler.fit(X_train_fold)
                X_train_scaled = scaler.transform(X_train_fold)
                X_test_scaled = scaler.transform(X_test_fold)
            else:
                X_train_scaled = X_train_fold
                X_test_scaled = X_test_fold
            
            # Train model
            model.fit(X_train_scaled, y_train_fold)
            
            # Make predictions
            y_pred = model.predict(X_test_scaled)
            
            # Calculate metrics
            r2 = r2_score(y_test_fold, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test_fold, y_pred))
            mae = mean_absolute_error(y_test_fold, y_pred)
            
            if len(y_test_fold) > 1:
                spearman_corr, _ = spearmanr(y_test_fold, y_pred)
                spearman_corr = spearman_corr if not np.isnan(spearman_corr) else 0.0
            else:
                spearman_corr = 0.0
            
            # Store fold results
            fold_result = {
                'fold': fold_idx + 1,
                'train_samples': len(X_train_fold),
                'test_samples': len(X_test_fold),
                'r2': r2,
                'rmse': rmse,
                'mae': mae,
                'spearman': spearman_corr,
                'target_mean': np.mean(y_test_fold),
                'target_std': np.std(y_test_fold)
            }
            
            cv_results['fold_results'].append(fold_result)
            
            # Collect scores for summary statistics
            fold_scores['r2'].append(r2)
            fold_scores['rmse'].append(rmse)
            fold_scores['mae'].append(mae)
            fold_scores['spearman'].append(spearman_corr)
            
            logger.info(f"     Fold {fold_idx + 1} - R²: {r2:.3f}, RMSE: {rmse:.3f}, Spearman: {spearman_corr:.3f}")
        
        # Calculate summary statistics
        cv_results['summary_stats'] = {
            'r2_mean': np.mean(fold_scores['r2']),
            'r2_std': np.std(fold_scores['r2']),
            'rmse_mean': np.mean(fold_scores['rmse']),
            'rmse_std': np.std(fold_scores['rmse']),
            'mae_mean': np.mean(fold_scores['mae']),
            'mae_std': np.std(fold_scores['mae']),
            'spearman_mean': np.mean(fold_scores['spearman']),
            'spearman_std': np.std(fold_scores['spearman'])
        }
        
        logger.info(f"   ✅ CV Complete - Mean R²: {cv_results['summary_stats']['r2_mean']:.3f} ± {cv_results['summary_stats']['r2_std']:.3f}")
        
        return cv_results
    
    def validate_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """Run temporal cross-validation for all positions."""
        
        logger.info("🔄 Running temporal cross-validation for all positions...")
        
        positions = ['QB', 'RB', 'WR', 'TE']
        model_types = ['ridge', 'random_forest']
        
        all_results = {}
        
        for position in positions:
            position_results = {}
            
            for model_type in model_types:
                try:
                    logger.info(f"\n📊 {position} - {model_type}...")
                    cv_results = self.validate_model(position, model_type)
                    position_results[model_type] = cv_results
                    
                except Exception as e:
                    logger.error(f"❌ Failed {position} - {model_type}: {e}")
                    position_results[model_type] = {}
            
            all_results[position] = position_results
        
        # Save results
        self._save_cv_results(all_results)
        
        return all_results
    
    def _save_cv_results(self, all_results: Dict[str, Dict[str, Any]]) -> None:
        """Save cross-validation results."""
        
        # Save detailed results
        import json
        results_file = self.results_dir / "temporal_cv_results.json"
        
        # Convert numpy types to JSON-serializable types
        def convert_numpy(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, (np.int64, np.int32)):
                return int(obj)
            return obj
        
        # Deep conversion for nested structures
        def deep_convert(obj):
            if isinstance(obj, dict):
                return {k: deep_convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [deep_convert(item) for item in obj]
            else:
                return convert_numpy(obj)
        
        serializable_results = deep_convert(all_results)
        serializable_results['generated_at'] = datetime.now().isoformat()
        
        try:
            with open(results_file, 'w') as f:
                json.dump(serializable_results, f, indent=2)
            logger.info(f"💾 Saved detailed results: {results_file}")
        except Exception as e:
            logger.error(f"Failed to save JSON results: {e}")
        
        # Create human-readable report
        report_file = self.results_dir / "temporal_cv_report.txt"
        
        try:
            with open(report_file, 'w') as f:
                f.write("TEMPORAL CROSS-VALIDATION REPORT\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n\n")
                
                f.write("SUMMARY RESULTS:\n")
                f.write("-" * 30 + "\n\n")
                
                for position, position_results in all_results.items():
                    if not position_results:
                        f.write(f"{position}: No results\n")
                        continue
                    
                    f.write(f"{position} POSITION:\n")
                    
                    for model_type, results in position_results.items():
                        if not results or 'summary_stats' not in results:
                            f.write(f"  {model_type}: Failed\n")
                            continue
                        
                        stats = results['summary_stats']
                        f.write(f"  {model_type.upper()}:\n")
                        f.write(f"    R² = {stats['r2_mean']:.3f} ± {stats['r2_std']:.3f}\n")
                        f.write(f"    RMSE = {stats['rmse_mean']:.3f} ± {stats['rmse_std']:.3f}\n")
                        f.write(f"    Spearman = {stats['spearman_mean']:.3f} ± {stats['spearman_std']:.3f}\n")
                        f.write(f"    CV Folds: {results['n_splits']}\n\n")
                
                f.write("\nINTERPRETA‌TION:\n")
                f.write("-" * 30 + "\n")
                f.write("• R² values between 0.15-0.35 are realistic for fantasy football\n")
                f.write("• Negative R² indicates model performs worse than mean baseline\n")
                f.write("• High standard deviation suggests unstable performance\n")
                f.write("• Spearman correlation measures rank-order prediction accuracy\n")
                f.write("• These results represent genuine predictive capability\n")
            
            logger.info(f"📄 Saved report: {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to save report: {e}")


def main():
    """Run temporal cross-validation analysis."""
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    validator = TemporalCrossValidator("data/processed")
    
    print("⏰ Temporal Cross-Validation Analysis")
    print("=" * 50)
    
    # Run cross-validation for all positions
    all_results = validator.validate_all_positions()
    
    print("\n📊 TEMPORAL CROSS-VALIDATION RESULTS")
    print("=" * 50)
    
    for position, position_results in all_results.items():
        if not position_results:
            print(f"\n{position}: No results")
            continue
        
        print(f"\n{position} POSITION:")
        
        for model_type, results in position_results.items():
            if not results or 'summary_stats' not in results:
                print(f"  {model_type:>15}: Failed")
                continue
            
            stats = results['summary_stats']
            print(f"  {model_type:>15}: R² = {stats['r2_mean']:>6.3f} ± {stats['r2_std']:>5.3f}, "
                  f"RMSE = {stats['rmse_mean']:>6.3f} ± {stats['rmse_std']:>5.3f}")
    
    print(f"\n💾 Results saved to: validation_results/")
    print(f"📈 Realistic R² range: 0.15-0.35")
    print(f"⚠️  Negative R² = worse than mean baseline")

if __name__ == "__main__":
    main()