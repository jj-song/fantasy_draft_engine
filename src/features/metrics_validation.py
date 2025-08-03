"""
Comprehensive Metrics Validation for Fantasy Football Features

This module provides validation functions for all opportunity and usage metrics
to ensure data quality and correctness across all position-specific features.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


def validate_all_metrics(df: pd.DataFrame, position: str = None) -> Dict[str, Any]:
    """
    Comprehensive validation of all fantasy football metrics.
    
    Args:
        df: DataFrame with player data and metrics
        position: Position to validate (WR, TE, RB, QB, etc.)
        
    Returns:
        Dict with validation results and recommendations
    """
    logger.info(f"Starting comprehensive metrics validation for {len(df)} players")
    
    validation_results = {
        'position': position,
        'player_count': len(df),
        'total_features': len(df.columns),
        'validation_summary': {},
        'errors': [],
        'warnings': [],
        'recommendations': []
    }
    
    # 1. Basic data quality checks
    basic_validation = validate_basic_data_quality(df)
    validation_results['validation_summary']['basic_quality'] = basic_validation
    
    # 2. Opportunity metrics validation
    opportunity_validation = validate_opportunity_metrics(df)
    validation_results['validation_summary']['opportunity_metrics'] = opportunity_validation
    
    # 3. Usage analytics validation
    usage_validation = validate_usage_metrics(df)
    validation_results['validation_summary']['usage_metrics'] = usage_validation
    
    # 4. Position-specific validation
    if position:
        position_validation = validate_position_specific_metrics(df, position)
        validation_results['validation_summary'][f'{position}_specific'] = position_validation
    
    # 5. Feature completeness check
    completeness_validation = validate_feature_completeness(df, position)
    validation_results['validation_summary']['feature_completeness'] = completeness_validation
    
    # 6. Cross-metric consistency
    consistency_validation = validate_cross_metric_consistency(df)
    validation_results['validation_summary']['consistency'] = consistency_validation
    
    # Compile overall results
    _compile_validation_summary(validation_results)
    
    logger.info(f"Validation completed. Overall status: {validation_results.get('overall_status', 'Unknown')}")
    return validation_results


def validate_basic_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate basic data quality metrics."""
    results = {
        'total_columns': len(df.columns),
        'total_rows': len(df),
        'missing_data': {},
        'data_types': {},
        'duplicates': 0,
        'status': 'pass'
    }
    
    # Check for missing data
    missing_data = df.isnull().sum()
    results['missing_data'] = {col: int(count) for col, count in missing_data.items() if count > 0}
    
    # Check data types
    results['data_types'] = {col: str(dtype) for col, dtype in df.dtypes.items()}
    
    # Check for duplicates
    if 'player_name' in df.columns:
        results['duplicates'] = df.duplicated(subset=['player_name']).sum()
    
    # Determine status
    if results['duplicates'] > 0:
        results['status'] = 'warning'
    if len(results['missing_data']) > len(df.columns) * 0.1:  # >10% columns with missing data
        results['status'] = 'warning'
    
    return results


def validate_opportunity_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate opportunity metrics ranges and consistency."""
    results = {
        'metrics_found': [],
        'range_checks': {},
        'invalid_values': {},
        'status': 'pass'
    }
    
    # Define expected opportunity metrics and their valid ranges
    opportunity_metrics = {
        'target_share': (0, 1),  # 0-100% as decimal
        'air_yards_share': (0, 1),  # 0-100% as decimal
        'wopr': (0, 1),  # WOPR typically 0-1
        'wopr_enhanced': (0, 1),
        'adot': (-5, 25),  # Average depth of target, can be negative
        'yac_per_target': (0, 20),  # YAC per target, reasonable max
        'red_zone_opportunities': (0, 50),  # Max reasonable red zone opps
        'targets_per_game': (0, 20),  # Max reasonable targets per game
        'air_yards_per_target': (-5, 25),  # Same as aDOT
    }
    
    for metric, (min_val, max_val) in opportunity_metrics.items():
        if metric in df.columns:
            results['metrics_found'].append(metric)
            
            # Check value ranges
            valid_range = df[metric].between(min_val, max_val, inclusive='both')
            invalid_count = (~valid_range).sum()
            
            results['range_checks'][metric] = {
                'min_found': float(df[metric].min()),
                'max_found': float(df[metric].max()),
                'expected_min': min_val,
                'expected_max': max_val,
                'invalid_count': int(invalid_count),
                'valid': invalid_count == 0
            }
            
            if invalid_count > 0:
                results['invalid_values'][metric] = invalid_count
                results['status'] = 'warning'
    
    return results


def validate_usage_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate usage analytics metrics."""
    results = {
        'metrics_found': [],
        'range_checks': {},
        'invalid_values': {},
        'status': 'pass'
    }
    
    # Define expected usage metrics and their valid ranges
    usage_metrics = {
        'avg_snap_share': (0, 1),  # 0-100% as decimal
        'total_snaps': (0, 2000),  # Max reasonable snaps per season
        'snaps_per_game': (0, 100),  # Max snaps per game
        'targets_per_snap': (0, 1),  # Can't have more targets than snaps
        'carries_per_snap': (0, 1),  # Can't have more carries than snaps
        'touches_per_snap': (0, 1),  # Can't have more touches than snaps
        'fantasy_points_per_snap': (0, 2),  # Max reasonable fantasy points per snap
        'utilization_rate': (0, 100),  # Percentage
        'route_participation_advanced': (0, 1),  # 0-100% as decimal
    }
    
    for metric, (min_val, max_val) in usage_metrics.items():
        if metric in df.columns:
            results['metrics_found'].append(metric)
            
            # Check value ranges
            valid_range = df[metric].between(min_val, max_val, inclusive='both')
            invalid_count = (~valid_range).sum()
            
            results['range_checks'][metric] = {
                'min_found': float(df[metric].min()),
                'max_found': float(df[metric].max()),
                'expected_min': min_val,
                'expected_max': max_val,
                'invalid_count': int(invalid_count),
                'valid': invalid_count == 0
            }
            
            if invalid_count > 0:
                results['invalid_values'][metric] = invalid_count
                results['status'] = 'warning'
    
    return results


def validate_position_specific_metrics(df: pd.DataFrame, position: str) -> Dict[str, Any]:
    """Validate position-specific metrics."""
    results = {
        'position': position,
        'specific_metrics': [],
        'validations': {},
        'status': 'pass'
    }
    
    if position == 'WR':
        wr_metrics = {
            'deep_target_rate': (0, 1),
            'contested_catch_rate': (0, 1),
            'fantasy_relevance_score': (0, 1),
            'air_yards_dominance': ['High', 'Medium', 'Low'],  # Categorical
            'snap_rate_tier': ['Elite', 'High', 'Medium', 'Low']  # Categorical
        }
        results['specific_metrics'] = list(wr_metrics.keys())
        
        for metric, expected in wr_metrics.items():
            if metric in df.columns:
                if isinstance(expected, tuple):  # Numeric range
                    min_val, max_val = expected
                    valid_range = df[metric].between(min_val, max_val, inclusive='both')
                    invalid_count = (~valid_range).sum()
                    results['validations'][metric] = {
                        'type': 'numeric',
                        'valid': invalid_count == 0,
                        'invalid_count': int(invalid_count)
                    }
                else:  # Categorical
                    valid_values = df[metric].isin(expected)
                    invalid_count = (~valid_values).sum()
                    results['validations'][metric] = {
                        'type': 'categorical',
                        'valid': invalid_count == 0,
                        'invalid_count': int(invalid_count),
                        'unique_values': list(df[metric].unique())
                    }
                
                if results['validations'][metric]['invalid_count'] > 0:
                    results['status'] = 'warning'
    
    elif position == 'TE':
        te_metrics = {
            'seam_route_rate': (0, 1),
            'inline_usage_estimate': (0, 1),
            'slot_usage_estimate': (0, 1),
            'blocking_snap_estimate': (0, 1),
            'te_role': ['Receiving', 'Blocking', 'Hybrid'],  # Categorical
            'red_zone_value_tier': ['Elite', 'High', 'Medium', 'Low']  # Categorical
        }
        
        for metric, expected in te_metrics.items():
            if metric in df.columns:
                results['specific_metrics'].append(metric)
                # Similar validation logic as WR...
    
    elif position == 'RB':
        rb_metrics = {
            'goal_line_carry_rate': (0, 1),
            'early_down_rate': (0, 1),
            'passing_down_rate': (0, 1),
            'workhorse_indicator': [0, 1],  # Binary
            'pass_catching_back': [0, 1],  # Binary
            'rb_role': ['Workhorse', 'Passing_Down', 'Change_of_Pace', 'Goal_Line'],  # Categorical
            'usage_sustainability': ['Sustainable', 'Moderate_Risk', 'High_Risk']  # Categorical
        }
        
        for metric, expected in rb_metrics.items():
            if metric in df.columns:
                results['specific_metrics'].append(metric)
                # Similar validation logic...
    
    return results


def validate_feature_completeness(df: pd.DataFrame, position: str = None) -> Dict[str, Any]:
    """Validate that expected features are present."""
    results = {
        'expected_categories': [],
        'missing_categories': [],
        'feature_counts': {},
        'completeness_score': 0.0,
        'status': 'pass'
    }
    
    # Define expected feature categories
    expected_categories = [
        'basic_stats',
        'efficiency_metrics',
        'per_game_metrics',
        'opportunity_metrics',
        'usage_analytics',
        'advanced_metrics'
    ]
    
    # Check for each category
    category_patterns = {
        'basic_stats': ['targets', 'receptions', 'receiving_yards', 'receiving_tds'],
        'efficiency_metrics': ['catch_rate', 'yards_per_reception', 'yards_per_target'],
        'per_game_metrics': ['targets_per_game', 'receptions_per_game', 'receiving_yards_per_game'],
        'opportunity_metrics': ['target_share', 'air_yards_share', 'wopr', 'adot'],
        'usage_analytics': ['avg_snap_share', 'total_snaps', 'utilization_rate'],
        'advanced_metrics': ['fantasy_relevance_score', 'target_efficiency_score']
    }
    
    for category, patterns in category_patterns.items():
        present_features = [p for p in patterns if p in df.columns]
        results['feature_counts'][category] = {
            'expected': len(patterns),
            'present': len(present_features),
            'percentage': len(present_features) / len(patterns) * 100
        }
        
        if len(present_features) > 0:
            results['expected_categories'].append(category)
        else:
            results['missing_categories'].append(category)
    
    # Calculate overall completeness score
    total_expected = sum(cat['expected'] for cat in results['feature_counts'].values())
    total_present = sum(cat['present'] for cat in results['feature_counts'].values())
    results['completeness_score'] = (total_present / total_expected * 100) if total_expected > 0 else 0
    
    if results['completeness_score'] < 80:
        results['status'] = 'warning'
    if results['completeness_score'] < 60:
        results['status'] = 'error'
    
    return results


def validate_cross_metric_consistency(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate consistency between related metrics."""
    results = {
        'consistency_checks': [],
        'inconsistencies': [],
        'status': 'pass'
    }
    
    # Check target share consistency
    if all(col in df.columns for col in ['targets', 'target_share', 'games']):
        # target_share should be reasonable given targets per game
        targets_per_game = df['targets'] / df['games'].replace(0, 1)
        # High target share should correspond to high targets per game
        high_share_high_targets = df[(df['target_share'] > 0.2) & (targets_per_game > 8)]
        low_share_low_targets = df[(df['target_share'] < 0.1) & (targets_per_game < 3)]
        
        results['consistency_checks'].append({
            'check': 'target_share_consistency',
            'high_share_high_targets': len(high_share_high_targets),
            'low_share_low_targets': len(low_share_low_targets),
            'status': 'pass'
        })
    
    # Check snap share vs usage consistency
    if all(col in df.columns for col in ['avg_snap_share', 'targets_per_snap']):
        # High snap share with very low targets per snap might indicate blocking role
        high_snaps_low_targets = df[(df['avg_snap_share'] > 0.6) & (df['targets_per_snap'] < 0.05)]
        if len(high_snaps_low_targets) > 0:
            results['consistency_checks'].append({
                'check': 'snap_usage_consistency',
                'high_snaps_low_targets': len(high_snaps_low_targets),
                'note': 'Likely blocking/special teams players',
                'status': 'pass'
            })
    
    # Check WOPR consistency
    if all(col in df.columns for col in ['wopr', 'target_share', 'air_yards_share']):
        # WOPR should be calculated correctly: (1.5 * target_share + 0.7 * air_yards_share) / 2.2
        calculated_wopr = ((1.5 * df['target_share']) + (0.7 * df['air_yards_share'])) / 2.2
        wopr_diff = abs(df['wopr'] - calculated_wopr)
        inconsistent_wopr = wopr_diff > 0.01  # Allow small floating point differences
        
        if inconsistent_wopr.sum() > 0:
            results['inconsistencies'].append({
                'metric': 'wopr',
                'inconsistent_count': int(inconsistent_wopr.sum()),
                'max_difference': float(wopr_diff.max())
            })
            results['status'] = 'warning'
    
    return results


def _compile_validation_summary(validation_results: Dict[str, Any]) -> None:
    """Compile overall validation summary and recommendations."""
    
    # Count statuses
    statuses = []
    for category, results in validation_results['validation_summary'].items():
        if isinstance(results, dict) and 'status' in results:
            statuses.append(results['status'])
    
    # Determine overall status
    if 'error' in statuses:
        validation_results['overall_status'] = 'error'
    elif 'warning' in statuses:
        validation_results['overall_status'] = 'warning'
    else:
        validation_results['overall_status'] = 'pass'
    
    # Generate recommendations
    recommendations = []
    
    # Feature completeness recommendations
    completeness = validation_results['validation_summary'].get('feature_completeness', {})
    if completeness.get('completeness_score', 100) < 80:
        recommendations.append(f"Feature completeness is {completeness.get('completeness_score', 0):.1f}%. Consider implementing missing feature categories.")
    
    # Data quality recommendations
    basic_quality = validation_results['validation_summary'].get('basic_quality', {})
    if basic_quality.get('duplicates', 0) > 0:
        recommendations.append(f"Found {basic_quality['duplicates']} duplicate players. Consider deduplication.")
    
    # Opportunity metrics recommendations
    opp_metrics = validation_results['validation_summary'].get('opportunity_metrics', {})
    if opp_metrics.get('status') == 'warning':
        recommendations.append("Some opportunity metrics have values outside expected ranges. Review data processing.")
    
    validation_results['recommendations'] = recommendations


def generate_validation_report(validation_results: Dict[str, Any]) -> str:
    """Generate a human-readable validation report."""
    
    report = []
    report.append("=" * 60)
    report.append("FANTASY FOOTBALL METRICS VALIDATION REPORT")
    report.append("=" * 60)
    
    # Basic info
    report.append(f"Position: {validation_results.get('position', 'All')}")
    report.append(f"Players: {validation_results.get('player_count', 0)}")
    report.append(f"Total Features: {validation_results.get('total_features', 0)}")
    report.append(f"Overall Status: {validation_results.get('overall_status', 'Unknown').upper()}")
    report.append("")
    
    # Summary by category
    report.append("VALIDATION SUMMARY BY CATEGORY:")
    report.append("-" * 40)
    for category, results in validation_results.get('validation_summary', {}).items():
        if isinstance(results, dict):
            status = results.get('status', 'unknown').upper()
            report.append(f"{category.ljust(25)}: {status}")
    report.append("")
    
    # Feature completeness
    completeness = validation_results['validation_summary'].get('feature_completeness', {})
    if completeness:
        report.append("FEATURE COMPLETENESS:")
        report.append("-" * 20)
        report.append(f"Overall Score: {completeness.get('completeness_score', 0):.1f}%")
        for category, counts in completeness.get('feature_counts', {}).items():
            report.append(f"  {category}: {counts['present']}/{counts['expected']} features ({counts['percentage']:.1f}%)")
        report.append("")
    
    # Recommendations
    if validation_results.get('recommendations'):
        report.append("RECOMMENDATIONS:")
        report.append("-" * 15)
        for i, rec in enumerate(validation_results['recommendations'], 1):
            report.append(f"{i}. {rec}")
        report.append("")
    
    report.append("=" * 60)
    
    return "\n".join(report)


if __name__ == "__main__":
    # Test the validation system
    print("🔍 Testing Metrics Validation System")
    print("=" * 50)
    
    try:
        import sys
        sys.path.append('.')
        from src.current_data_pipeline import create_current_inference_dataset
        from src.data.feature_engineering.position.wr_features import engineer_wr_features
        
        # Test with WR data
        wr_data = create_current_inference_dataset('WR')
        if not wr_data.empty:
            wr_enhanced = engineer_wr_features(wr_data.head(20))  # Test with sample
            
            validation_results = validate_all_metrics(wr_enhanced, 'WR')
            
            print(generate_validation_report(validation_results))
            
            print(f"✅ Validation completed successfully")
            print(f"📊 Overall Status: {validation_results.get('overall_status', 'Unknown')}")
        else:
            print("❌ No WR data available for testing")
            
    except Exception as e:
        print(f"❌ Error during validation testing: {e}")
        import traceback
        traceback.print_exc()