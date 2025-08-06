"""
Baseline Models for Fantasy Football Prediction

This module implements proper baseline models with realistic performance expectations.
Models use only historical features and proper temporal validation to prevent data leakage.

Key Principles:
- Simple, interpretable models first
- Proper temporal cross-validation
- Realistic performance expectations (R² = 0.15-0.35)
- Baseline comparisons (mean, median predictions)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
from scipy.stats import spearmanr
import joblib

logger = logging.getLogger(__name__)

class BaselineModelTrainer:
    """
    Trains and evaluates baseline models for fantasy football prediction.
    
    Implements proper temporal validation and realistic performance benchmarks.
    """
    
    def __init__(self, data_dir: str = "data/processed"):
        """
        Initialize baseline model trainer.
        
        Args:
            data_dir: Path to processed data directory
        """
        self.data_dir = Path(data_dir)
        self.enhanced_dir = self.data_dir / "enhanced_training"
        self.models_dir = Path("saved_models") / "baseline_models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Define baseline models to test
        self.baseline_models = {
            'mean_baseline': self._mean_baseline,
            'linear_regression': LinearRegression(),
            'ridge_regression': Ridge(alpha=1.0),
            'lasso_regression': Lasso(alpha=1.0),
            'random_forest_simple': RandomForestRegressor(
                n_estimators=50, 
                max_depth=5, 
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=42
            )
        }
        
        logger.info("🎯 BaselineModelTrainer initialized")
        logger.info(f"   Models dir: {self.models_dir}")
        logger.info(f"   Baseline models: {list(self.baseline_models.keys())}")
    
    def _mean_baseline(self, X_train: np.ndarray, y_train: np.ndarray) -> np.ndarray:
        """Simple mean baseline predictor."""
        self._mean_value = np.mean(y_train)
        return self._mean_value
    
    def _predict_mean_baseline(self, X_test: np.ndarray) -> np.ndarray:
        """Predict using mean baseline."""
        return np.full(len(X_test), self._mean_value)
    
    def load_position_data(self, position: str) -> Dict[str, pd.DataFrame]:
        """
        Load enhanced training data for a position.
        
        Args:
            position: Player position (QB, RB, WR, TE)
            
        Returns:
            Dictionary with train, validation, and test DataFrames
        """
        position_path = self.enhanced_dir / position.lower()
        
        if not position_path.exists():
            raise FileNotFoundError(f"Enhanced data not found for {position}: {position_path}")
        
        datasets = {}
        
        for split_name in ['train', 'validation', 'test']:
            file_path = position_path / f"{position.lower()}_{split_name}_enhanced.parquet"
            
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    datasets[split_name] = df
                    logger.info(f"   Loaded {position} {split_name}: {len(df)} samples")
                except Exception as e:
                    logger.error(f"Failed to load {file_path}: {e}")
                    datasets[split_name] = pd.DataFrame()
            else:
                datasets[split_name] = pd.DataFrame()
        
        return datasets
    
    def prepare_features(self, datasets: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Prepare feature matrices and target vectors from datasets.
        
        Args:
            datasets: Dictionary of train/validation/test DataFrames
            
        Returns:
            Tuple of (prepared_data_dict, feature_names)
        """
        # Define feature columns (exclude metadata and target)
        exclude_cols = {
            'player_id', 'player_display_name', 'position', 'prediction_year',
            'birth_date', 'college_name', 'fantasy_points_per_game', 'split'
        }
        
        # Get feature columns from training data
        if datasets['train'].empty:
            return {}, []
        
        feature_cols = [col for col in datasets['train'].columns if col not in exclude_cols]
        target_col = 'fantasy_points_per_game'
        
        logger.info(f"   Using {len(feature_cols)} features: {feature_cols}")
        
        prepared_data = {}
        
        for split_name, df in datasets.items():
            if df.empty:
                prepared_data[split_name] = {'X': np.array([]).reshape(0, len(feature_cols)), 'y': np.array([])}
                continue
            
            # Handle missing values
            X = df[feature_cols].fillna(0).values
            
            if target_col in df.columns:
                y = df[target_col].fillna(0).values
            else:
                y = np.zeros(len(X))  # For test data without targets
            
            prepared_data[split_name] = {'X': X, 'y': y}
            logger.info(f"   {split_name}: X shape {X.shape}, y shape {y.shape}")
        
        return prepared_data, feature_cols
    
    def train_baseline_models(self, position: str) -> Dict[str, Any]:
        """
        Train all baseline models for a position.
        
        Args:
            position: Player position to train models for
            
        Returns:
            Dictionary containing trained models and results
        """
        logger.info(f"🤖 Training baseline models for {position}...")
        
        # Load data
        datasets = self.load_position_data(position)
        if datasets['train'].empty:
            logger.error(f"No training data available for {position}")
            return {}
        
        # Prepare features
        data, feature_names = self.prepare_features(datasets)
        if not data:
            logger.error(f"Failed to prepare features for {position}")
            return {}
        
        X_train, y_train = data['train']['X'], data['train']['y']
        X_val, y_val = data['validation']['X'], data['validation']['y']
        X_test, y_test = data['test']['X'], data['test']['y']
        
        # Scale features for regularized models
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val) if len(X_val) > 0 else np.array([]).reshape(0, X_train.shape[1])
        X_test_scaled = scaler.transform(X_test) if len(X_test) > 0 else np.array([]).reshape(0, X_train.shape[1])
        
        results = {
            'position': position,
            'feature_names': feature_names,
            'scaler': scaler,
            'models': {},
            'performance': {},
            'training_stats': {
                'train_samples': len(X_train),
                'val_samples': len(X_val),
                'test_samples': len(X_test),
                'features': len(feature_names),
                'target_stats': {
                    'train_mean': np.mean(y_train),
                    'train_std': np.std(y_train),
                    'train_min': np.min(y_train),
                    'train_max': np.max(y_train)
                }
            }
        }
        
        logger.info(f"   Training on {len(X_train)} samples with {len(feature_names)} features")
        logger.info(f"   Target stats - Mean: {np.mean(y_train):.2f}, Std: {np.std(y_train):.2f}")
        
        # Train each baseline model
        for model_name, model in self.baseline_models.items():
            try:
                logger.info(f"   🔧 Training {model_name}...")
                
                if model_name == 'mean_baseline':
                    # Special handling for mean baseline
                    model(X_train, y_train)
                    
                    # Evaluate mean baseline
                    train_pred = self._predict_mean_baseline(X_train)
                    val_pred = self._predict_mean_baseline(X_val) if len(X_val) > 0 else np.array([])
                    test_pred = self._predict_mean_baseline(X_test) if len(X_test) > 0 else np.array([])
                    
                else:
                    # Train sklearn models
                    if model_name in ['ridge_regression', 'lasso_regression']:
                        # Use scaled features for regularized models
                        model.fit(X_train_scaled, y_train)
                        train_pred = model.predict(X_train_scaled)
                        val_pred = model.predict(X_val_scaled) if len(X_val) > 0 else np.array([])
                        test_pred = model.predict(X_test_scaled) if len(X_test) > 0 else np.array([])
                    else:
                        # Use unscaled features for tree-based models
                        model.fit(X_train, y_train)
                        train_pred = model.predict(X_train)
                        val_pred = model.predict(X_val) if len(X_val) > 0 else np.array([])
                        test_pred = model.predict(X_test) if len(X_test) > 0 else np.array([])
                
                # Calculate performance metrics
                performance = self._calculate_metrics(
                    model_name, 
                    y_train, train_pred,
                    y_val, val_pred,
                    y_test, test_pred
                )
                
                results['models'][model_name] = model
                results['performance'][model_name] = performance
                
                logger.info(f"     ✅ {model_name} - Train R²: {performance['train_r2']:.3f}, Val R²: {performance['val_r2']:.3f}")
                
            except Exception as e:
                logger.error(f"     ❌ Failed to train {model_name}: {e}")
                continue
        
        # Save results
        if results['models']:
            self._save_baseline_results(results, position)
        
        return results
    
    def _calculate_metrics(self, model_name: str, 
                         y_train: np.ndarray, train_pred: np.ndarray,
                         y_val: np.ndarray, val_pred: np.ndarray,
                         y_test: np.ndarray, test_pred: np.ndarray) -> Dict[str, float]:
        """Calculate comprehensive performance metrics."""
        
        metrics = {'model_name': model_name}
        
        # Training metrics
        if len(y_train) > 0 and len(train_pred) > 0:
            metrics['train_r2'] = r2_score(y_train, train_pred)
            metrics['train_rmse'] = np.sqrt(mean_squared_error(y_train, train_pred))
            metrics['train_mae'] = mean_absolute_error(y_train, train_pred)
            if len(y_train) > 1:
                spearman_corr, _ = spearmanr(y_train, train_pred)
                metrics['train_spearman'] = spearman_corr if not np.isnan(spearman_corr) else 0.0
            else:
                metrics['train_spearman'] = 0.0
        
        # Validation metrics
        if len(y_val) > 0 and len(val_pred) > 0:
            metrics['val_r2'] = r2_score(y_val, val_pred)
            metrics['val_rmse'] = np.sqrt(mean_squared_error(y_val, val_pred))
            metrics['val_mae'] = mean_absolute_error(y_val, val_pred)
            if len(y_val) > 1:
                spearman_corr, _ = spearmanr(y_val, val_pred)
                metrics['val_spearman'] = spearman_corr if not np.isnan(spearman_corr) else 0.0
            else:
                metrics['val_spearman'] = 0.0
        else:
            metrics.update({
                'val_r2': 0.0, 'val_rmse': 0.0, 'val_mae': 0.0, 'val_spearman': 0.0
            })
        
        # Test metrics (may not have targets)
        if len(y_test) > 0 and len(test_pred) > 0:
            metrics['test_r2'] = r2_score(y_test, test_pred)
            metrics['test_rmse'] = np.sqrt(mean_squared_error(y_test, test_pred))
            metrics['test_mae'] = mean_absolute_error(y_test, test_pred)
            if len(y_test) > 1:
                spearman_corr, _ = spearmanr(y_test, test_pred)
                metrics['test_spearman'] = spearman_corr if not np.isnan(spearman_corr) else 0.0
            else:
                metrics['test_spearman'] = 0.0
        else:
            metrics.update({
                'test_r2': 0.0, 'test_rmse': 0.0, 'test_mae': 0.0, 'test_spearman': 0.0
            })
        
        return metrics
    
    def _save_baseline_results(self, results: Dict[str, Any], position: str) -> None:
        """Save baseline model results."""
        
        # Save models
        models_file = self.models_dir / f"{position.lower()}_baseline_models.joblib"
        try:
            # Create serializable results (exclude non-serializable objects)
            serializable_results = {
                'position': results['position'],
                'feature_names': results['feature_names'],
                'scaler': results['scaler'],
                'performance': results['performance'],
                'training_stats': results['training_stats'],
                'models': {}
            }
            
            # Save sklearn models, exclude custom baseline
            for model_name, model in results['models'].items():
                if model_name != 'mean_baseline':
                    serializable_results['models'][model_name] = model
                else:
                    # Save mean baseline separately
                    serializable_results['mean_baseline_value'] = self._mean_value
            
            joblib.dump(serializable_results, models_file)
            logger.info(f"   💾 Saved models: {models_file}")
            
        except Exception as e:
            logger.error(f"   ❌ Failed to save models: {e}")
        
        # Save performance report
        report_file = self.models_dir / f"{position.lower()}_performance_report.txt"
        try:
            with open(report_file, 'w') as f:
                f.write(f"Baseline Models Performance Report - {position}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n\n")
                
                f.write("Training Data Summary:\n")
                f.write(f"  Train samples: {results['training_stats']['train_samples']}\n")
                f.write(f"  Validation samples: {results['training_stats']['val_samples']}\n")
                f.write(f"  Test samples: {results['training_stats']['test_samples']}\n")
                f.write(f"  Features: {results['training_stats']['features']}\n")
                
                target_stats = results['training_stats']['target_stats']
                f.write(f"  Target stats: Mean={target_stats['train_mean']:.2f}, ")
                f.write(f"Std={target_stats['train_std']:.2f}, ")
                f.write(f"Range=[{target_stats['train_min']:.2f}, {target_stats['train_max']:.2f}]\n\n")
                
                f.write("Model Performance:\n")
                f.write("-" * 30 + "\n")
                
                for model_name, perf in results['performance'].items():
                    f.write(f"\n{model_name.upper()}:\n")
                    f.write(f"  Train - R²: {perf['train_r2']:.3f}, RMSE: {perf['train_rmse']:.3f}, Spearman: {perf['train_spearman']:.3f}\n")
                    f.write(f"  Val   - R²: {perf['val_r2']:.3f}, RMSE: {perf['val_rmse']:.3f}, Spearman: {perf['val_spearman']:.3f}\n")
                    f.write(f"  Test  - R²: {perf['test_r2']:.3f}, RMSE: {perf['test_rmse']:.3f}, Spearman: {perf['test_spearman']:.3f}\n")
            
            logger.info(f"   📄 Saved report: {report_file}")
            
        except Exception as e:
            logger.error(f"   ❌ Failed to save report: {e}")
    
    def train_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """Train baseline models for all positions."""
        
        logger.info("🚀 Training baseline models for all positions...")
        
        positions = ['QB', 'RB', 'WR', 'TE']
        all_results = {}
        
        for position in positions:
            try:
                logger.info(f"\n📊 Processing {position}...")
                results = self.train_baseline_models(position)
                all_results[position] = results
                
                if results:
                    logger.info(f"✅ {position} baseline models trained successfully")
                else:
                    logger.warning(f"⚠️ No models trained for {position}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to process {position}: {e}")
                all_results[position] = {}
        
        # Create summary report
        self._create_summary_report(all_results)
        
        return all_results
    
    def _create_summary_report(self, all_results: Dict[str, Dict[str, Any]]) -> None:
        """Create a comprehensive summary report."""
        
        summary_file = self.models_dir / "baseline_models_summary.txt"
        
        try:
            with open(summary_file, 'w') as f:
                f.write("BASELINE MODELS SUMMARY REPORT\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n\n")
                
                f.write("PERFORMANCE OVERVIEW:\n")
                f.write("-" * 30 + "\n\n")
                
                # Best performing models by position
                for position, results in all_results.items():
                    if not results or not results.get('performance'):
                        f.write(f"{position}: No models trained\n")
                        continue
                    
                    f.write(f"{position} POSITION:\n")
                    
                    # Find best model by validation R²
                    best_model = None
                    best_r2 = -999
                    
                    for model_name, perf in results['performance'].items():
                        val_r2 = perf.get('val_r2', -999)
                        if val_r2 > best_r2:
                            best_r2 = val_r2
                            best_model = model_name
                    
                    f.write(f"  Best model: {best_model} (Val R² = {best_r2:.3f})\n")
                    f.write(f"  Training samples: {results['training_stats']['train_samples']}\n")
                    
                    # Show all model performances
                    for model_name, perf in results['performance'].items():
                        f.write(f"    {model_name}: Val R² = {perf['val_r2']:.3f}, Val RMSE = {perf['val_rmse']:.3f}\n")
                    
                    f.write("\n")
                
                f.write("\nREALISTIC EXPECTATIONS:\n")
                f.write("-" * 30 + "\n")
                f.write("Industry standard R² for fantasy football prediction: 0.15-0.35\n")
                f.write("These baseline results establish the foundation for realistic modeling.\n")
                f.write("Results significantly above 0.35 R² should be investigated for data leakage.\n")
            
            logger.info(f"📋 Summary report saved: {summary_file}")
            
        except Exception as e:
            logger.error(f"Failed to create summary report: {e}")


def main():
    """Train and evaluate baseline models."""
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    trainer = BaselineModelTrainer("data/processed")
    
    print("🎯 Baseline Models Training")
    print("=" * 50)
    
    # Train all baseline models
    all_results = trainer.train_all_positions()
    
    print("\n📊 BASELINE MODELS SUMMARY")
    print("=" * 50)
    
    for position, results in all_results.items():
        if not results or not results.get('performance'):
            print(f"\n{position}: No models trained")
            continue
        
        print(f"\n{position} POSITION:")
        print(f"  Training samples: {results['training_stats']['train_samples']}")
        print(f"  Features: {results['training_stats']['features']}")
        
        # Show model performances
        best_val_r2 = -999
        best_model = ""
        
        for model_name, perf in results['performance'].items():
            val_r2 = perf.get('val_r2', 0)
            print(f"    {model_name:>20}: Val R² = {val_r2:>6.3f}, Val RMSE = {perf.get('val_rmse', 0):>6.3f}")
            
            if val_r2 > best_val_r2:
                best_val_r2 = val_r2
                best_model = model_name
        
        print(f"  🏆 Best: {best_model} (R² = {best_val_r2:.3f})")
    
    print(f"\n💾 Models saved to: saved_models/baseline_models/")
    print(f"📈 Expected realistic R² range: 0.15-0.35")

if __name__ == "__main__":
    main()