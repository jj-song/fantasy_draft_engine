"""
Debug Analysis Validator - Automated validation of debug session outputs
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DebugValidator:
    """Validates data flow and variables during debug sessions"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.validation_log = []
        self.data_checkpoints = {}
    
    def checkpoint(self, step_name: str, data: Any, expected_type: type = None, 
                   expected_shape: Tuple = None, expected_columns: List[str] = None) -> Dict[str, Any]:
        """
        Create a debug checkpoint to validate data at a specific step
        
        Args:
            step_name: Name of the debug step
            data: The data to validate
            expected_type: Expected data type
            expected_shape: Expected shape for DataFrames/arrays
            expected_columns: Expected columns for DataFrames
            
        Returns:
            Validation results
        """
        validation_result = {
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "service": self.service_name,
            "status": "PASS",
            "issues": [],
            "data_summary": {}
        }
        
        try:
            # Basic type validation
            actual_type = type(data).__name__
            validation_result["data_summary"]["type"] = actual_type
            
            if expected_type and not isinstance(data, expected_type):
                validation_result["status"] = "FAIL"
                validation_result["issues"].append(f"Type mismatch: expected {expected_type.__name__}, got {actual_type}")
            
            # DataFrame-specific validations
            if isinstance(data, pd.DataFrame):
                self._validate_dataframe(data, validation_result, expected_shape, expected_columns)
            
            # Array-specific validations  
            elif isinstance(data, np.ndarray):
                self._validate_array(data, validation_result, expected_shape)
            
            # Dictionary validations
            elif isinstance(data, dict):
                self._validate_dictionary(data, validation_result)
            
            # List validations
            elif isinstance(data, list):
                self._validate_list(data, validation_result)
            
            # Store checkpoint data
            self.data_checkpoints[step_name] = {
                "data": data if self._is_serializable(data) else str(data),
                "validation": validation_result
            }
            
        except Exception as e:
            validation_result["status"] = "ERROR"
            validation_result["issues"].append(f"Validation error: {str(e)}")
        
        self.validation_log.append(validation_result)
        self._log_validation_result(validation_result)
        
        return validation_result
    
    def _validate_dataframe(self, df: pd.DataFrame, result: Dict, expected_shape: Tuple = None, 
                           expected_columns: List[str] = None):
        """Validate DataFrame-specific properties"""
        result["data_summary"].update({
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "null_counts": df.isnull().sum().to_dict(),
            "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2)
        })
        
        # Shape validation
        if expected_shape:
            if len(expected_shape) > 0 and df.shape[0] != expected_shape[0]:
                result["issues"].append(f"Row count mismatch: expected {expected_shape[0]}, got {df.shape[0]}")
            if len(expected_shape) > 1 and df.shape[1] != expected_shape[1]:
                result["issues"].append(f"Column count mismatch: expected {expected_shape[1]}, got {df.shape[1]}")
        
        # Column validation
        if expected_columns:
            missing_cols = set(expected_columns) - set(df.columns)
            if missing_cols:
                result["issues"].append(f"Missing columns: {list(missing_cols)}")
        
        # Data quality checks
        if df.empty:
            result["issues"].append("DataFrame is empty")
        
        # Check for excessive nulls (>50% in any column)
        high_null_cols = [col for col, null_count in df.isnull().sum().items() 
                         if null_count > len(df) * 0.5]
        if high_null_cols:
            result["issues"].append(f"High null percentage columns: {high_null_cols}")
        
        # Sample data for inspection
        if not df.empty:
            result["data_summary"]["sample_data"] = df.head(3).to_dict('records')
    
    def _validate_array(self, arr: np.ndarray, result: Dict, expected_shape: Tuple = None):
        """Validate NumPy array properties"""
        result["data_summary"].update({
            "shape": arr.shape,
            "dtype": str(arr.dtype),
            "min": float(np.min(arr)) if arr.size > 0 else None,
            "max": float(np.max(arr)) if arr.size > 0 else None,
            "mean": float(np.mean(arr)) if arr.size > 0 else None
        })
        
        if expected_shape and arr.shape != expected_shape:
            result["issues"].append(f"Shape mismatch: expected {expected_shape}, got {arr.shape}")
        
        if arr.size == 0:
            result["issues"].append("Array is empty")
    
    def _validate_dictionary(self, data: dict, result: Dict):
        """Validate dictionary properties"""
        result["data_summary"].update({
            "keys": list(data.keys()),
            "key_count": len(data),
            "value_types": {k: type(v).__name__ for k, v in data.items()}
        })
        
        if not data:
            result["issues"].append("Dictionary is empty")
    
    def _validate_list(self, data: list, result: Dict):
        """Validate list properties"""
        result["data_summary"].update({
            "length": len(data),
            "element_types": list(set(type(item).__name__ for item in data)) if data else []
        })
        
        if not data:
            result["issues"].append("List is empty")
    
    def _is_serializable(self, data: Any) -> bool:
        """Check if data can be JSON serialized"""
        try:
            json.dumps(data, default=str)
            return True
        except:
            return False
    
    def _log_validation_result(self, result: Dict):
        """Log validation result"""
        status_emoji = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
        logger.info(f"{status_emoji} {self.service_name} - {result['step']}: {result['status']}")
        
        if result["issues"]:
            for issue in result["issues"]:
                logger.warning(f"   Issue: {issue}")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validations"""
        total_steps = len(self.validation_log)
        passed = sum(1 for v in self.validation_log if v["status"] == "PASS")
        failed = sum(1 for v in self.validation_log if v["status"] == "FAIL")
        errors = sum(1 for v in self.validation_log if v["status"] == "ERROR")
        
        return {
            "service": self.service_name,
            "total_steps": total_steps,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "success_rate": round(passed / total_steps * 100, 2) if total_steps > 0 else 0,
            "validations": self.validation_log
        }
    
    def save_validation_report(self, output_path: Optional[str] = None):
        """Save detailed validation report"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"reports/validation/{self.service_name}/debug_validation_{self.service_name}_{timestamp}.json"
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.get_validation_summary(), f, indent=2, default=str)
        
        logger.info(f"Validation report saved to: {output_path}")
        return output_path


# Fantasy Football specific validators
class DataIngestionValidator(DebugValidator):
    """Specialized validator for Data Ingestion Service"""
    
    def __init__(self):
        super().__init__("data-ingestion")
    
    def validate_nfl_data_fetch(self, raw_data: pd.DataFrame, year: int) -> Dict[str, Any]:
        """Validate NFL data fetching results"""
        expected_columns = ['player_name', 'position', 'games', 'passing_yards', 'rushing_yards']
        
        return self.checkpoint(
            step_name=f"nfl_data_fetch_{year}",
            data=raw_data,
            expected_type=pd.DataFrame,
            expected_columns=expected_columns
        )
    
    def validate_data_cleaning(self, cleaned_data: pd.DataFrame, original_count: int) -> Dict[str, Any]:
        """Validate data cleaning results"""
        result = self.checkpoint(
            step_name="data_cleaning",
            data=cleaned_data,
            expected_type=pd.DataFrame
        )
        
        # Additional cleaning-specific checks
        if len(cleaned_data) > original_count:
            result["issues"].append(f"Data cleaning increased row count: {original_count} → {len(cleaned_data)}")
        
        # Check for reasonable data loss (shouldn't lose more than 10% of data)
        data_loss_pct = ((original_count - len(cleaned_data)) / original_count) * 100
        if data_loss_pct > 10:
            result["issues"].append(f"High data loss during cleaning: {data_loss_pct:.1f}%")
        
        return result


class FeatureEngineeringValidator(DebugValidator):
    """Specialized validator for Feature Engineering Service"""
    
    def __init__(self):
        super().__init__("feature-engineering")
    
    def validate_feature_generation(self, features: pd.DataFrame, position: str) -> Dict[str, Any]:
        """Validate feature generation results"""
        # Expected 28 core features based on developer notes
        expected_feature_count = 28
        
        result = self.checkpoint(
            step_name=f"feature_generation_{position}",
            data=features,
            expected_type=pd.DataFrame
        )
        
        # Feature-specific validations
        if features.shape[1] != expected_feature_count:
            result["issues"].append(f"Feature count mismatch: expected {expected_feature_count}, got {features.shape[1]}")
        
        # Check for NaN values in features (shouldn't have any)
        nan_features = features.columns[features.isnull().any()].tolist()
        if nan_features:
            result["issues"].append(f"Features with NaN values: {nan_features}")
        
        return result


class MLModelsValidator(DebugValidator):
    """Specialized validator for ML Models Service"""
    
    def __init__(self):
        super().__init__("ml-models")
    
    def validate_model_prediction(self, predictions: np.ndarray, position: str, 
                                 player_count: int) -> Dict[str, Any]:
        """Validate ML model prediction results"""
        result = self.checkpoint(
            step_name=f"model_prediction_{position}",
            data=predictions,
            expected_type=np.ndarray,
            expected_shape=(player_count,)
        )
        
        # Position-specific prediction range validation based on developer notes
        expected_ranges = {
            'QB': (5, 25),   # QB ~17 FPPG ± reasonable range
            'RB': (2, 20),   # RB ~11 FPPG ± reasonable range  
            'WR': (1, 18),   # WR ~8 FPPG ± reasonable range
            'TE': (1, 15)    # TE ~7 FPPG ± reasonable range
        }
        
        if position in expected_ranges:
            min_exp, max_exp = expected_ranges[position]
            actual_min, actual_max = float(np.min(predictions)), float(np.max(predictions))
            
            if actual_min < min_exp or actual_max > max_exp:
                result["issues"].append(f"Predictions outside expected range for {position}: "
                                      f"got [{actual_min:.2f}, {actual_max:.2f}], "
                                      f"expected [{min_exp}, {max_exp}]")
        
        return result


class RankingValidator(DebugValidator):
    """Specialized validator for Ranking Service"""
    
    def __init__(self):
        super().__init__("ranking")
    
    def validate_vor_calculation(self, vor_data: pd.DataFrame) -> Dict[str, Any]:
        """Validate VOR calculation results"""
        expected_columns = ['player_name', 'position', 'projected_points', 'vor_value', 'rank']
        
        result = self.checkpoint(
            step_name="vor_calculation",
            data=vor_data,
            expected_type=pd.DataFrame,
            expected_columns=expected_columns
        )
        
        # VOR-specific validations
        if 'vor_value' in vor_data.columns:
            # Check that top players have positive VOR
            top_10_vor = vor_data.nlargest(10, 'vor_value')['vor_value']
            if any(vor <= 0 for vor in top_10_vor):
                result["issues"].append("Top 10 players should have positive VOR values")
        
        # Check expected player count (should be ~569 based on developer notes)
        expected_player_range = (500, 650)
        actual_count = len(vor_data)
        if not (expected_player_range[0] <= actual_count <= expected_player_range[1]):
            result["issues"].append(f"Player count outside expected range: "
                                  f"got {actual_count}, expected {expected_player_range}")
        
        return result