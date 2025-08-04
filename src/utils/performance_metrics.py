"""
Performance Metrics Module for Fantasy Football Models

This module provides comprehensive performance tracking for ML models including
R², RMSE, MAE, and other relevant metrics for fantasy football predictions.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from typing import Dict, List, Tuple, Optional, Any
import json
import logging
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """
    Calculate and track performance metrics for fantasy football models.
    """
    
    def __init__(self, position: str = None):
        """
        Initialize performance metrics tracker.
        
        Args:
            position: Player position (QB, RB, WR, TE, etc.)
        """
        self.position = position
        self.metrics_history = []
        
    def calculate_regression_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """
        Calculate comprehensive regression metrics.
        
        Args:
            y_true: Actual values
            y_pred: Predicted values
            
        Returns:
            Dictionary of metrics
        """
        metrics = {}
        
        # Basic regression metrics
        metrics['r2_score'] = r2_score(y_true, y_pred)
        metrics['rmse'] = np.sqrt(mean_squared_error(y_true, y_pred))
        metrics['mae'] = mean_absolute_error(y_true, y_pred)
        metrics['mse'] = mean_squared_error(y_true, y_pred)
        
        # Fantasy-specific metrics
        metrics['mean_actual'] = np.mean(y_true)
        metrics['mean_predicted'] = np.mean(y_pred)
        metrics['std_actual'] = np.std(y_true)
        metrics['std_predicted'] = np.std(y_pred)
        
        # Percentage error metrics
        mape = np.mean(np.abs((y_true - y_pred) / np.where(y_true == 0, 1, y_true))) * 100
        metrics['mape'] = mape
        
        # Correlation
        correlation = np.corrcoef(y_true, y_pred)[0, 1]
        metrics['correlation'] = correlation if not np.isnan(correlation) else 0.0
        
        # Fantasy-specific: Top player accuracy
        # How well do we predict the top 10% of players?
        top_10_pct = int(len(y_true) * 0.1)
        if top_10_pct > 0:
            top_actual_idx = np.argsort(y_true)[-top_10_pct:]
            top_pred_idx = np.argsort(y_pred)[-top_10_pct:]
            top_overlap = len(set(top_actual_idx) & set(top_pred_idx))
            metrics['top_10_overlap'] = top_overlap / top_10_pct
        else:
            metrics['top_10_overlap'] = 0.0
            
        return metrics
    
    def evaluate_model_performance(self, model: Any, X_test: pd.DataFrame, 
                                 y_test: pd.Series, model_name: str = "model") -> Dict[str, Any]:
        """
        Evaluate model performance with comprehensive metrics.
        
        Args:
            model: Trained model
            X_test: Test features
            y_test: Test targets
            model_name: Name of the model for logging
            
        Returns:
            Dictionary with performance results
        """
        logger.info(f"🔍 Evaluating {model_name} performance for {self.position or 'Unknown'}")
        
        # Make predictions
        try:
            y_pred = model.predict(X_test)
        except Exception as e:
            logger.error(f"Prediction failed for {model_name}: {e}")
            return {"error": str(e)}
        
        # Calculate metrics
        metrics = self.calculate_regression_metrics(y_test.values, y_pred)
        
        # Add metadata
        evaluation_result = {
            "model_name": model_name,
            "position": self.position,
            "test_samples": len(y_test),
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        }
        
        # Log key metrics
        logger.info(f"📊 {model_name} Performance:")
        logger.info(f"   R² Score: {metrics['r2_score']:.4f}")
        logger.info(f"   RMSE: {metrics['rmse']:.3f}")
        logger.info(f"   MAE: {metrics['mae']:.3f}")
        logger.info(f"   Correlation: {metrics['correlation']:.4f}")
        logger.info(f"   Top 10% Overlap: {metrics['top_10_overlap']:.2%}")
        
        # Store in history
        self.metrics_history.append(evaluation_result)
        
        return evaluation_result
    
    def compare_models(self, results: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Compare performance across multiple models.
        
        Args:
            results: List of evaluation results from evaluate_model_performance
            
        Returns:
            DataFrame with model comparison
        """
        if not results:
            return pd.DataFrame()
        
        comparison_data = []
        
        for result in results:
            if "error" in result:
                continue
                
            row = {
                "Model": result["model_name"],
                "Position": result["position"],
                "R²": result["metrics"]["r2_score"],
                "RMSE": result["metrics"]["rmse"],
                "MAE": result["metrics"]["mae"],
                "Correlation": result["metrics"]["correlation"],
                "Top 10% Overlap": result["metrics"]["top_10_overlap"],
                "Test Samples": result["test_samples"]
            }
            comparison_data.append(row)
        
        df = pd.DataFrame(comparison_data)
        
        if not df.empty:
            # Sort by R² score descending
            df = df.sort_values("R²", ascending=False)
            logger.info(f"📈 Model Comparison for {self.position}:")
            logger.info(f"\n{df.to_string(index=False, float_format='%.3f')}")
        
        return df
    
    def save_metrics(self, filepath: str) -> None:
        """
        Save metrics history to JSON file.
        
        Args:
            filepath: Path to save metrics
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.metrics_history, f, indent=2, default=str)
            logger.info(f"💾 Saved metrics to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def load_metrics(self, filepath: str) -> None:
        """
        Load metrics history from JSON file.
        
        Args:
            filepath: Path to load metrics from
        """
        try:
            with open(filepath, 'r') as f:
                self.metrics_history = json.load(f)
            logger.info(f"📂 Loaded metrics from {filepath}")
        except Exception as e:
            logger.warning(f"Could not load metrics: {e}")
    
    def create_performance_report(self, output_dir: str = "logs") -> str:
        """
        Create a comprehensive performance report.
        
        Args:
            output_dir: Directory to save report
            
        Returns:
            Path to generated report
        """
        if not self.metrics_history:
            logger.warning("No metrics history to report")
            return ""
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"{output_dir}/performance_report_{self.position}_{timestamp}.md"
        
        with open(report_path, 'w') as f:
            f.write(f"# Performance Report: {self.position}\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Summary table
            f.write("## Model Performance Summary\n\n")
            
            # Create comparison DataFrame
            comparison_df = self.compare_models(self.metrics_history)
            if not comparison_df.empty:
                f.write(comparison_df.to_markdown(index=False, floatfmt=".3f"))
                f.write("\n\n")
            
            # Detailed metrics for each model
            f.write("## Detailed Metrics\n\n")
            for result in self.metrics_history:
                if "error" in result:
                    continue
                    
                f.write(f"### {result['model_name']}\n\n")
                metrics = result['metrics']
                
                f.write(f"- **R² Score**: {metrics['r2_score']:.4f}\n")
                f.write(f"- **RMSE**: {metrics['rmse']:.3f}\n")
                f.write(f"- **MAE**: {metrics['mae']:.3f}\n")
                f.write(f"- **Correlation**: {metrics['correlation']:.4f}\n")
                f.write(f"- **Top 10% Overlap**: {metrics['top_10_overlap']:.2%}\n")
                f.write(f"- **Mean Actual**: {metrics['mean_actual']:.1f}\n")
                f.write(f"- **Mean Predicted**: {metrics['mean_predicted']:.1f}\n")
                f.write(f"- **Test Samples**: {result['test_samples']}\n\n")
        
        logger.info(f"📄 Performance report saved to {report_path}")
        return report_path


def evaluate_position_models(position: str, models: Dict[str, Any], 
                           X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
    """
    Evaluate all models for a specific position.
    
    Args:
        position: Player position
        models: Dictionary of model_name -> model_object
        X_test: Test features
        y_test: Test targets
        
    Returns:
        Dictionary with evaluation results
    """
    logger.info(f"🎯 Evaluating all models for {position}")
    
    metrics_tracker = PerformanceMetrics(position)
    results = []
    
    for model_name, model in models.items():
        if model is None:
            logger.warning(f"Model {model_name} is None, skipping")
            continue
            
        result = metrics_tracker.evaluate_model_performance(
            model, X_test, y_test, model_name
        )
        results.append(result)
    
    # Create comparison
    comparison_df = metrics_tracker.compare_models(results)
    
    # Save metrics
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    metrics_file = logs_dir / f"model_metrics_{position}.json"
    metrics_tracker.save_metrics(str(metrics_file))
    
    # Create report
    report_path = metrics_tracker.create_performance_report(str(logs_dir))
    
    return {
        "position": position,
        "results": results,
        "comparison": comparison_df,
        "metrics_file": str(metrics_file),
        "report_path": report_path,
        "best_model": comparison_df.iloc[0]["Model"] if not comparison_df.empty else None
    }


def create_overall_performance_summary(position_results: Dict[str, Dict[str, Any]]) -> str:
    """
    Create an overall performance summary across all positions.
    
    Args:
        position_results: Dictionary of position -> evaluation results
        
    Returns:
        Path to summary report
    """
    logger.info("📋 Creating overall performance summary")
    
    # Create summary data
    summary_data = []
    
    for position, results in position_results.items():
        if not results.get("comparison") or results["comparison"].empty:
            continue
            
        best_model_row = results["comparison"].iloc[0]
        
        summary_data.append({
            "Position": position,
            "Best Model": best_model_row["Model"],
            "R²": best_model_row["R²"],
            "RMSE": best_model_row["RMSE"],
            "MAE": best_model_row["MAE"],
            "Correlation": best_model_row["Correlation"],
            "Top 10% Overlap": best_model_row["Top 10% Overlap"],
            "Test Samples": best_model_row["Test Samples"]
        })
    
    # Create summary DataFrame
    summary_df = pd.DataFrame(summary_data)
    
    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"logs/overall_performance_summary_{timestamp}.md"
    
    with open(report_path, 'w') as f:
        f.write("# Overall Model Performance Summary\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        if not summary_df.empty:
            f.write("## Best Model by Position\n\n")
            f.write(summary_df.to_markdown(index=False, floatfmt=".3f"))
            f.write("\n\n")
            
            # Calculate averages
            avg_r2 = summary_df["R²"].mean()
            avg_rmse = summary_df["RMSE"].mean()
            avg_mae = summary_df["MAE"].mean()
            
            f.write("## Overall Statistics\n\n")
            f.write(f"- **Average R²**: {avg_r2:.3f}\n")
            f.write(f"- **Average RMSE**: {avg_rmse:.3f}\n")
            f.write(f"- **Average MAE**: {avg_mae:.3f}\n")
            f.write(f"- **Total Positions**: {len(summary_df)}\n")
            f.write(f"- **Total Test Samples**: {summary_df['Test Samples'].sum()}\n\n")
            
            # Model type summary
            model_counts = summary_df["Best Model"].value_counts()
            f.write("## Best Model Types\n\n")
            for model, count in model_counts.items():
                f.write(f"- **{model}**: {count} positions\n")
        
        else:
            f.write("No performance data available.\n")
    
    logger.info(f"📊 Overall performance summary saved to {report_path}")
    return report_path