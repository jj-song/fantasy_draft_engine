"""
Debug Integration Helper - Easily add validation checkpoints to services
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.debug_analysis.debug_validator import (
    DataIngestionValidator,
    FeatureEngineeringValidator, 
    MLModelsValidator,
    RankingValidator
)

# Global validators - can be imported by services
data_validator = DataIngestionValidator()
feature_validator = FeatureEngineeringValidator()
ml_validator = MLModelsValidator()
ranking_validator = RankingValidator()

def add_validation_checkpoint(service_name: str, step_name: str, data, **kwargs):
    """
    Easy function to add validation checkpoints anywhere in your code
    
    Usage in your service:
    ```python
    from utils.debug_analysis.debug_integration import add_validation_checkpoint
    
    # In your function:
    df = fetch_player_season_stats(year)
    add_validation_checkpoint('data-ingestion', 'nfl_data_fetch', df, 
                            expected_columns=['player_name', 'position'])
    ```
    """
    validators = {
        'data-ingestion': data_validator,
        'feature-engineering': feature_validator,
        'ml-models': ml_validator,
        'ranking': ranking_validator
    }
    
    if service_name in validators:
        return validators[service_name].checkpoint(step_name, data, **kwargs)
    else:
        print(f"Unknown service: {service_name}")
        return None

def get_all_validation_summaries():
    """Get validation summaries from all services"""
    return {
        'data-ingestion': data_validator.get_validation_summary(),
        'feature-engineering': feature_validator.get_validation_summary(),
        'ml-models': ml_validator.get_validation_summary(),
        'ranking': ranking_validator.get_validation_summary()
    }

def save_all_validation_reports():
    """Save validation reports for all services"""
    reports = {}
    
    for validator_name, validator in [
        ('data-ingestion', data_validator),
        ('feature-engineering', feature_validator),
        ('ml-models', ml_validator),
        ('ranking', ranking_validator)
    ]:
        if validator.validation_log:  # Only save if there are validations
            report_path = validator.save_validation_report()
            reports[validator_name] = report_path
    
    return reports