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


class ConfigurationValidator(DebugValidator):
    """Specialized validator for configuration service debug sessions"""
    
    def __init__(self):
        super().__init__("configuration")
        self.expected_domains = ["data", "league", "model", "position", "scoring"]
        self.expected_positions = ["QB", "RB", "WR", "TE"]
        self.expected_ppr_values = [0.0, 0.5, 1.0]  # Standard, Half PPR, Full PPR
    
    def validate_config_manager_initialization(self, config_manager, environment: str = None):
        """Validate that configuration manager initializes correctly"""
        return self.checkpoint(
            "config_manager_initialization",
            config_manager,
            expected_type=object,
            environment=environment,
            config_manager=config_manager
        )
    
    def validate_domain_access(self, domain_configs: Dict[str, Any]):
        """Validate access to all configuration domains"""
        return self.checkpoint(
            "domain_access", 
            domain_configs,
            expected_type=dict,
            expected_domains=self.expected_domains
        )
    
    def validate_positions_config(self, positions_data: Dict[str, Any]):
        """Validate positions configuration"""
        return self.checkpoint(
            "positions_config",
            positions_data,
            expected_type=dict,
            expected_core_positions=self.expected_positions
        )
    
    def validate_scoring_system(self, scoring_data: Dict[str, Any]):
        """Validate scoring system configuration"""
        return self.checkpoint(
            "scoring_system",
            scoring_data,
            expected_type=dict,
            expected_ppr_values=self.expected_ppr_values
        )
    
    def validate_api_endpoints(self, endpoint_results: Dict[str, Any]):
        """Validate API endpoint functionality"""
        return self.checkpoint(
            "api_endpoints",
            endpoint_results,
            expected_type=dict,
            expected_endpoints=['summary', 'positions', 'scoring/system', 'config/data']
        )
    
    def validate_health_checks(self, health_data: Dict[str, Any]):
        """Validate health check functionality"""
        return self.checkpoint(
            "health_checks",
            health_data,
            expected_type=dict,
            expected_status='healthy'
        )
    
    def checkpoint(self, step_name: str, data: Any, **kwargs) -> Dict[str, Any]:
        """Enhanced checkpoint for configuration-specific validations"""
        result = super().checkpoint(step_name, data)
        
        # Configuration-specific validations
        if step_name == "config_manager_initialization":
            self._validate_config_manager(data, result, **kwargs)
        elif step_name == "domain_access":
            self._validate_domain_configs(data, result, **kwargs)
        elif step_name == "positions_config":
            self._validate_positions_data(data, result, **kwargs)
        elif step_name == "scoring_system":
            self._validate_scoring_data(data, result, **kwargs)
        elif step_name == "api_endpoints":
            self._validate_api_results(data, result, **kwargs)
        elif step_name == "health_checks":
            self._validate_health_data(data, result, **kwargs)
        
        return result
    
    def _validate_config_manager(self, config_manager, result: Dict, **kwargs):
        """Validate configuration manager object"""
        try:
            # Check if config manager has essential methods
            essential_methods = ['get_config', 'get_environment', 'get_all_positions', 'get_core_positions']
            missing_methods = []
            
            for method in essential_methods:
                if not hasattr(config_manager, method):
                    missing_methods.append(method)
            
            if missing_methods:
                result["status"] = "FAIL"
                result["issues"].append(f"Missing essential methods: {missing_methods}")
            
            # Check environment
            environment = kwargs.get('environment')
            if environment and hasattr(config_manager, 'get_environment'):
                actual_env = config_manager.get_environment()
                if actual_env != environment:
                    result["issues"].append(f"Environment mismatch: expected {environment}, got {actual_env}")
                    result["status"] = "FAIL"
                result["data_summary"]["environment"] = actual_env
            
            # Test basic functionality
            if hasattr(config_manager, 'get_all_positions'):
                try:
                    positions = config_manager.get_all_positions()
                    result["data_summary"]["positions_count"] = len(positions)
                    if not positions:
                        result["issues"].append("No positions returned")
                        result["status"] = "FAIL"
                except Exception as e:
                    result["issues"].append(f"Error getting positions: {str(e)}")
                    result["status"] = "FAIL"
        
        except Exception as e:
            result["status"] = "ERROR"
            result["issues"].append(f"Config manager validation error: {str(e)}")
    
    def _validate_domain_configs(self, domain_configs: Dict, result: Dict, **kwargs):
        """Validate domain configuration access"""
        expected_domains = kwargs.get('expected_domains', self.expected_domains)
        
        missing_domains = []
        for domain in expected_domains:
            if domain not in domain_configs:
                missing_domains.append(domain)
        
        if missing_domains:
            result["status"] = "FAIL"
            result["issues"].append(f"Missing domains: {missing_domains}")
        
        result["data_summary"]["available_domains"] = list(domain_configs.keys())
        result["data_summary"]["domain_count"] = len(domain_configs)
        
        # Check each domain has data
        for domain, config in domain_configs.items():
            if not config or (isinstance(config, dict) and not config):
                result["issues"].append(f"Empty configuration for domain: {domain}")
                if result["status"] != "FAIL":
                    result["status"] = "WARNING"
    
    def _validate_positions_data(self, positions_data: Dict, result: Dict, **kwargs):
        """Validate positions configuration data"""
        expected_core = kwargs.get('expected_core_positions', self.expected_positions)
        
        if 'all_positions' not in positions_data:
            result["status"] = "FAIL"
            result["issues"].append("Missing 'all_positions' field")
        
        if 'core_positions' not in positions_data:
            result["status"] = "FAIL"
            result["issues"].append("Missing 'core_positions' field")
        
        core_positions = positions_data.get('core_positions', [])
        missing_core = [pos for pos in expected_core if pos not in core_positions]
        
        if missing_core:
            result["status"] = "FAIL"
            result["issues"].append(f"Missing core positions: {missing_core}")
        
        result["data_summary"]["core_positions"] = core_positions
        result["data_summary"]["all_positions"] = positions_data.get('all_positions', [])
    
    def _validate_scoring_data(self, scoring_data: Dict, result: Dict, **kwargs):
        """Validate scoring system data"""
        if 'scoring_system' not in scoring_data:
            result["status"] = "FAIL"
            result["issues"].append("Missing 'scoring_system' field")
            return
        
        scoring_system = scoring_data['scoring_system']
        required_scoring_keys = ['passing_yards', 'passing_tds', 'rushing_yards', 'rushing_tds', 
                                'receptions', 'receiving_yards', 'receiving_tds']
        
        missing_keys = [key for key in required_scoring_keys if key not in scoring_system]
        if missing_keys:
            result["status"] = "FAIL"
            result["issues"].append(f"Missing scoring keys: {missing_keys}")
        
        # Validate PPR value
        ppr_value = scoring_data.get('ppr_value', None)
        expected_ppr = kwargs.get('expected_ppr_values', self.expected_ppr_values)
        
        if ppr_value is not None and ppr_value not in expected_ppr:
            result["issues"].append(f"Unusual PPR value: {ppr_value} (expected one of {expected_ppr})")
            if result["status"] != "FAIL":
                result["status"] = "WARNING"
        
        result["data_summary"]["ppr_value"] = ppr_value
        result["data_summary"]["scoring_keys"] = list(scoring_system.keys()) if scoring_system else []
    
    def _validate_api_results(self, api_results: Dict, result: Dict, **kwargs):
        """Validate API endpoint results"""
        expected_endpoints = kwargs.get('expected_endpoints', [])
        
        for endpoint in expected_endpoints:
            if endpoint not in api_results:
                result["issues"].append(f"Missing API endpoint result: {endpoint}")
                result["status"] = "FAIL"
                continue
            
            endpoint_result = api_results[endpoint]
            if isinstance(endpoint_result, dict) and 'status' in endpoint_result:
                if endpoint_result['status'] != 'success':
                    result["issues"].append(f"API endpoint {endpoint} failed: {endpoint_result.get('error', 'Unknown error')}")
                    result["status"] = "FAIL"
        
        result["data_summary"]["tested_endpoints"] = list(api_results.keys())
        result["data_summary"]["successful_endpoints"] = [
            ep for ep, res in api_results.items() 
            if isinstance(res, dict) and res.get('status') == 'success'
        ]
    
    def _validate_health_data(self, health_data: Dict, result: Dict, **kwargs):
        """Validate health check data"""
        expected_status = kwargs.get('expected_status', 'healthy')
        
        if 'status' not in health_data:
            result["status"] = "FAIL"
            result["issues"].append("Missing 'status' field in health data")
        elif health_data['status'] != expected_status:
            result["status"] = "FAIL"
            result["issues"].append(f"Health status is {health_data['status']}, expected {expected_status}")
        
        result["data_summary"]["health_status"] = health_data.get('status')
        result["data_summary"]["health_details"] = health_data.get('details', {})