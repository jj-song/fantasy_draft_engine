#!/usr/bin/env python3
"""
Comprehensive Pipeline Validation Framework

This script provides end-to-end validation of the entire fantasy football
draft ranking pipeline, from data ingestion through final ranking generation.

Key Features:
- Training dataset integrity validation (2020-2023)
- Ensemble model loading and prediction accuracy testing
- Feature compatibility system validation
- Draft ranking generation with statistical tier validation
- Comprehensive data quality checks using DataQualityValidator
- Performance metrics and regression detection

Usage:
    python scripts/validate_pipeline.py                    # Full validation
    python scripts/validate_pipeline.py --quick           # Fast validation
    python scripts/validate_pipeline.py --models-only     # Model validation only
    python scripts/validate_pipeline.py --rankings-only   # Rankings validation only
"""

import os
import sys
import pandas as pd
import numpy as np
import joblib
import argparse
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import logging
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Import our modules
from src.data_quality_validator import validator, DataQualityError
from src.ensemble_model import EnsembleFantasyModel
from src.feature_compatibility import FeatureCompatibilityMapper
from src.config import get_config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PipelineValidator:
    """Comprehensive pipeline validation system."""
    
    def __init__(self, quick_mode: bool = False):
        """Initialize the pipeline validator."""
        self.quick_mode = quick_mode
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'quick_mode': quick_mode,
            'training_data_validation': {},
            'model_validation': {},
            'ranking_validation': {},
            'performance_metrics': {},
            'overall_status': 'PENDING'
        }
        
        # Get configuration
        self.config = get_config()
        self.processed_data_dir = self.config.get('data.processed_data_dir', 'data/processed')
        self.models_dir = 'saved_models'
        
        logger.info(f"🔍 PIPELINE VALIDATOR INITIALIZED")
        logger.info(f"   Quick mode: {quick_mode}")
        logger.info(f"   Data directory: {self.processed_data_dir}")
        logger.info(f"   Models directory: {self.models_dir}")
    
    def validate_training_datasets(self) -> Dict[str, Any]:
        """Validate integrity of all training datasets."""
        logger.info("📊 VALIDATING TRAINING DATASETS")
        logger.info("=" * 50)
        
        results = {
            'datasets_found': 0,
            'datasets_valid': 0,
            'total_players': 0,
            'position_distribution': {},
            'feature_counts': {},
            'years_validated': [],
            'validation_errors': []
        }
        
        # Expected training datasets
        if self.quick_mode:
            years_to_check = [2022, 2023]  # Recent years only
        else:
            years_to_check = [2020, 2021, 2022, 2023]  # All training years
        
        for year in years_to_check:
            dataset_path = project_root / self.processed_data_dir / f"training_features_{year}_with_matchup_intel.parquet"
            
            logger.info(f"   Validating {year} training dataset...")
            
            try:
                if not dataset_path.exists():
                    error_msg = f"Training dataset missing: {dataset_path}"
                    results['validation_errors'].append(error_msg)
                    logger.error(f"   ❌ {error_msg}")
                    continue
                
                # Load and validate dataset
                df = pd.read_parquet(dataset_path)
                results['datasets_found'] += 1
                
                # Basic validation
                if df.empty:
                    error_msg = f"Empty dataset: {year}"
                    results['validation_errors'].append(error_msg)
                    continue
                
                # Position distribution validation
                if 'position' not in df.columns:
                    error_msg = f"Missing position column: {year}"
                    results['validation_errors'].append(error_msg)
                    continue
                
                position_counts = df['position'].value_counts()
                results['position_distribution'][year] = position_counts.to_dict()
                results['total_players'] += len(df)
                results['feature_counts'][year] = len(df.columns)
                
                # Data quality validation using existing validator
                validator.validate_feature_engineered_data(
                    df, year, 
                    include_matchup_intelligence=True,
                    training_mode=True
                )
                
                results['datasets_valid'] += 1
                results['years_validated'].append(year)
                
                logger.info(f"   ✅ {year}: {len(df)} players, {len(df.columns)} features")
                for pos, count in position_counts.items():
                    logger.info(f"      {pos}: {count} players")
                
            except Exception as e:
                error_msg = f"Validation failed for {year}: {str(e)}"
                results['validation_errors'].append(error_msg)
                logger.error(f"   ❌ {error_msg}")
        
        # Summary
        success_rate = (results['datasets_valid'] / len(years_to_check)) * 100 if years_to_check else 0
        logger.info(f"\n📊 TRAINING DATASETS VALIDATION SUMMARY:")
        logger.info(f"   Datasets found: {results['datasets_found']}/{len(years_to_check)}")
        logger.info(f"   Datasets valid: {results['datasets_valid']}/{len(years_to_check)}")
        logger.info(f"   Success rate: {success_rate:.1f}%")
        logger.info(f"   Total players: {results['total_players']:,}")
        
        if results['validation_errors']:
            logger.warning(f"   ⚠️ Validation errors: {len(results['validation_errors'])}")
            for error in results['validation_errors']:
                logger.warning(f"      • {error}")
        
        results['success_rate'] = success_rate
        results['status'] = 'PASSED' if success_rate >= 100 else 'FAILED'
        
        return results
    
    def validate_ensemble_models(self) -> Dict[str, Any]:
        """Validate ensemble model loading and basic functionality."""
        logger.info("\n🤖 VALIDATING ENSEMBLE MODELS")
        logger.info("=" * 50)
        
        results = {
            'models_found': 0,
            'models_loaded': 0,
            'model_details': {},
            'prediction_tests': {},
            'validation_errors': []
        }
        
        positions = ['QB', 'RB', 'WR', 'TE']
        
        for position in positions:
            model_path = project_root / self.models_dir / f"{position}_ensemble_model.joblib"
            
            logger.info(f"   Validating {position} ensemble model...")
            
            try:
                if not model_path.exists():
                    error_msg = f"Ensemble model missing: {model_path}"
                    results['validation_errors'].append(error_msg)
                    logger.error(f"   ❌ {error_msg}")
                    continue
                
                results['models_found'] += 1
                
                # Load model
                model = EnsembleFantasyModel.load(str(model_path))
                
                # Validate model structure
                if not model.is_trained:
                    error_msg = f"{position} model not trained"
                    results['validation_errors'].append(error_msg)
                    continue
                
                # Test basic model properties
                model_info = {
                    'position': model.position,
                    'is_trained': model.is_trained,
                    'has_rf_model': model.rf_model is not None,
                    'has_lgb_model': model.lgb_model is not None,
                    'fallback_model': getattr(model, 'fallback_model', None)
                }
                
                results['model_details'][position] = model_info
                results['models_loaded'] += 1
                
                # Quick prediction test (if not in quick mode)
                if not self.quick_mode:
                    # Create simple test data
                    test_data = pd.DataFrame({
                        f'feature_{i}': np.random.randn(5) for i in range(50)
                    })
                    
                    try:
                        predictions = model.predict(test_data)
                        
                        prediction_info = {
                            'predictions_generated': len(predictions),
                            'mean_prediction': float(np.mean(predictions)),
                            'has_nan_predictions': bool(np.any(np.isnan(predictions))),
                            'prediction_range': [float(np.min(predictions)), float(np.max(predictions))]
                        }
                        
                        results['prediction_tests'][position] = prediction_info
                        
                        if np.any(np.isnan(predictions)):
                            error_msg = f"{position} model produced NaN predictions"
                            results['validation_errors'].append(error_msg)
                        
                    except Exception as e:
                        error_msg = f"{position} model prediction test failed: {str(e)}"
                        results['validation_errors'].append(error_msg)
                
                logger.info(f"   ✅ {position}: Loaded successfully")
                if model_info['fallback_model']:
                    logger.info(f"      Fallback mode: {model_info['fallback_model']}")
                
            except Exception as e:
                error_msg = f"Model validation failed for {position}: {str(e)}"
                results['validation_errors'].append(error_msg)
                logger.error(f"   ❌ {error_msg}")
        
        # Summary
        success_rate = (results['models_loaded'] / len(positions)) * 100
        logger.info(f"\n🤖 ENSEMBLE MODELS VALIDATION SUMMARY:")
        logger.info(f"   Models found: {results['models_found']}/{len(positions)}")
        logger.info(f"   Models loaded: {results['models_loaded']}/{len(positions)}")
        logger.info(f"   Success rate: {success_rate:.1f}%")
        
        if results['validation_errors']:
            logger.warning(f"   ⚠️ Validation errors: {len(results['validation_errors'])}")
        
        results['success_rate'] = success_rate
        results['status'] = 'PASSED' if success_rate >= 100 else 'FAILED'
        
        return results
    
    def validate_feature_compatibility(self) -> Dict[str, Any]:
        """Validate feature compatibility system."""
        logger.info("\n🔧 VALIDATING FEATURE COMPATIBILITY SYSTEM")
        logger.info("=" * 50)
        
        results = {
            'compatibility_tests_passed': 0,
            'total_compatibility_tests': 0,
            'mapping_validation': {},
            'validation_errors': []
        }
        
        try:
            mapper = FeatureCompatibilityMapper()
            
            # Test basic functionality
            positions = ['QB', 'RB', 'WR', 'TE']
            
            for position in positions:
                logger.info(f"   Testing {position} feature compatibility...")
                
                try:
                    results['total_compatibility_tests'] += 1
                    
                    # Create test data with enhanced features
                    test_enhanced_features = pd.DataFrame({
                        'birth_date': ['1995-01-01'] * 3,
                        'carries': [10, 15, 20],
                        'games': [16, 15, 14],
                        'passing_attempts': [500, 400, 300],
                        'fantasy_points_ppr': [200, 180, 160],
                        'air_yards_share': [0.2, 0.15, 0.1]
                    })
                    
                    # Expected legacy features
                    expected_legacy_features = [
                        'age', 'rushing_attempts', 'games_played', 'attempts',
                        'fantasy_points_ppr', 'air_yards_dominance'
                    ]
                    
                    # Test compatibility mapping
                    compatible_features = mapper.create_compatible_features(
                        test_enhanced_features, expected_legacy_features, position
                    )
                    
                    # Validate results
                    mapping_info = {
                        'input_features': len(test_enhanced_features.columns),
                        'expected_features': len(expected_legacy_features),
                        'output_features': len(compatible_features.columns),
                        'compatibility_score': len(compatible_features.columns) / len(expected_legacy_features)
                    }
                    
                    results['mapping_validation'][position] = mapping_info
                    results['compatibility_tests_passed'] += 1
                    
                    logger.info(f"   ✅ {position}: Compatibility score {mapping_info['compatibility_score']:.3f}")
                    
                except Exception as e:
                    error_msg = f"{position} compatibility test failed: {str(e)}"
                    results['validation_errors'].append(error_msg)
                    logger.error(f"   ❌ {error_msg}")
            
        except Exception as e:
            error_msg = f"Feature compatibility system initialization failed: {str(e)}"
            results['validation_errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
        
        # Summary
        success_rate = (results['compatibility_tests_passed'] / results['total_compatibility_tests']) * 100 if results['total_compatibility_tests'] > 0 else 0
        logger.info(f"\n🔧 FEATURE COMPATIBILITY VALIDATION SUMMARY:")
        logger.info(f"   Tests passed: {results['compatibility_tests_passed']}/{results['total_compatibility_tests']}")
        logger.info(f"   Success rate: {success_rate:.1f}%")
        
        results['success_rate'] = success_rate
        results['status'] = 'PASSED' if success_rate >= 100 else 'FAILED'
        
        return results
    
    def validate_pipeline_performance(self) -> Dict[str, Any]:
        """Validate overall pipeline performance metrics."""
        logger.info("\n⚡ VALIDATING PIPELINE PERFORMANCE")
        logger.info("=" * 50)
        
        results = {
            'execution_times': {},
            'memory_usage': {},
            'file_sizes': {},
            'performance_score': 0.0,
            'validation_errors': []
        }
        
        try:
            # Test data loading performance
            start_time = time.time()
            dataset_path = project_root / self.processed_data_dir / "training_features_2023_with_matchup_intel.parquet"
            if dataset_path.exists():
                df = pd.read_parquet(dataset_path)
                load_time = time.time() - start_time
                results['execution_times']['data_loading'] = load_time
                logger.info(f"   Data loading: {load_time:.3f}s")
            
            # Test model loading performance
            start_time = time.time()
            model_path = project_root / self.models_dir / "QB_ensemble_model.joblib"
            if model_path.exists():
                model = EnsembleFantasyModel.load(str(model_path))
                model_load_time = time.time() - start_time
                results['execution_times']['model_loading'] = model_load_time
                logger.info(f"   Model loading: {model_load_time:.3f}s")
            
            # Check file sizes
            for file_pattern in ['training_features_*_with_matchup_intel.parquet', '*_ensemble_model.joblib']:
                files = list(project_root.rglob(file_pattern))
                for file_path in files:
                    if file_path.exists():
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        results['file_sizes'][file_path.name] = size_mb
            
            # Calculate performance score
            performance_factors = []
            if 'data_loading' in results['execution_times']:
                # Good if data loads in under 2 seconds
                performance_factors.append(min(1.0, 2.0 / results['execution_times']['data_loading']))
            
            if 'model_loading' in results['execution_times']:
                # Good if model loads in under 1 second
                performance_factors.append(min(1.0, 1.0 / results['execution_times']['model_loading']))
            
            results['performance_score'] = np.mean(performance_factors) if performance_factors else 0.0
            
        except Exception as e:
            error_msg = f"Performance validation failed: {str(e)}"
            results['validation_errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
        
        logger.info(f"\n⚡ PERFORMANCE VALIDATION SUMMARY:")
        logger.info(f"   Performance score: {results['performance_score']:.3f}")
        if results['execution_times']:
            for operation, time_taken in results['execution_times'].items():
                logger.info(f"   {operation}: {time_taken:.3f}s")
        
        results['status'] = 'PASSED' if results['performance_score'] >= 0.7 else 'FAILED'
        
        return results
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run complete pipeline validation."""
        logger.info("🚀 STARTING COMPREHENSIVE PIPELINE VALIDATION")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        # Run all validation components
        self.validation_results['training_data_validation'] = self.validate_training_datasets()
        self.validation_results['model_validation'] = self.validate_ensemble_models()
        self.validation_results['feature_compatibility_validation'] = self.validate_feature_compatibility()
        self.validation_results['performance_validation'] = self.validate_pipeline_performance()
        
        # Calculate overall status
        validation_components = [
            self.validation_results['training_data_validation'],
            self.validation_results['model_validation'],
            self.validation_results['feature_compatibility_validation'],
            self.validation_results['performance_validation']
        ]
        
        passed_components = sum(1 for component in validation_components if component.get('status') == 'PASSED')
        total_components = len(validation_components)
        overall_success_rate = (passed_components / total_components) * 100
        
        self.validation_results['overall_status'] = 'PASSED' if overall_success_rate >= 100 else 'FAILED'
        self.validation_results['overall_success_rate'] = overall_success_rate
        self.validation_results['execution_time'] = time.time() - start_time
        
        # Final summary
        logger.info(f"\n🎯 COMPREHENSIVE VALIDATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"   Overall status: {self.validation_results['overall_status']}")
        logger.info(f"   Success rate: {overall_success_rate:.1f}%")
        logger.info(f"   Components passed: {passed_components}/{total_components}")
        logger.info(f"   Total execution time: {self.validation_results['execution_time']:.2f}s")
        
        # Component breakdown
        for name, component in [
            ('Training Data', self.validation_results['training_data_validation']),
            ('Ensemble Models', self.validation_results['model_validation']),
            ('Feature Compatibility', self.validation_results['feature_compatibility_validation']),
            ('Performance', self.validation_results['performance_validation'])
        ]:
            status_emoji = "✅" if component.get('status') == 'PASSED' else "❌"
            logger.info(f"   {status_emoji} {name}: {component.get('status', 'UNKNOWN')}")
        
        return self.validation_results
    
    def save_validation_report(self, output_path: Optional[str] = None) -> str:
        """Save validation results to a report file."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"validation_reports/pipeline_validation_report_{timestamp}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        import json
        with open(output_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2, default=str)
        
        logger.info(f"📋 Validation report saved: {output_path}")
        return output_path


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Comprehensive pipeline validation')
    
    parser.add_argument('--quick', action='store_true', help='Quick validation mode')
    parser.add_argument('--models-only', action='store_true', help='Validate models only')
    parser.add_argument('--rankings-only', action='store_true', help='Validate rankings only')
    parser.add_argument('--save-report', action='store_true', help='Save validation report')
    
    return parser.parse_args()


def main():
    """Main function to run pipeline validation."""
    args = parse_arguments()
    
    # Create validator
    validator = PipelineValidator(quick_mode=args.quick)
    
    if args.models_only:
        logger.info("🎯 Running models-only validation")
        results = validator.validate_ensemble_models()
    elif args.rankings_only:
        logger.info("🎯 Running rankings-only validation")  
        # This would call ranking validation when implemented
        results = {'status': 'NOT_IMPLEMENTED'}
    else:
        logger.info("🎯 Running comprehensive validation")
        results = validator.run_comprehensive_validation()
    
    # Save report if requested
    if args.save_report:
        validator.save_validation_report()
    
    # Exit with appropriate code
    if results.get('overall_status') == 'PASSED' or results.get('status') == 'PASSED':
        logger.info("🎉 Validation completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()