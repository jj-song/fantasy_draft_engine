#!/usr/bin/env python3
"""
Microservices Validation Script - Validate the microservices architecture.

This script validates that the microservices refactoring is complete and all
components are properly structured.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

def check_service_structure(service_path: Path, expected_components: List[str]) -> Dict[str, Any]:
    """Check if a service has the expected directory structure."""
    results = {
        "exists": service_path.exists(),
        "components": {},
        "score": 0,
        "total": len(expected_components)
    }
    
    if not results["exists"]:
        return results
    
    for component in expected_components:
        component_path = service_path / component
        exists = component_path.exists()
        results["components"][component] = exists
        if exists:
            results["score"] += 1
    
    return results

def validate_service_apis(service_path: Path) -> Dict[str, Any]:
    """Validate that service has proper API structure."""
    api_components = [
        "src/main.py",
        "src/api/__init__.py", 
        "src/health/__init__.py",
        "Dockerfile",
        "docker-compose.yml",
        "requirements.txt"
    ]
    
    return check_service_structure(service_path, api_components)

def validate_configuration_service(services_root: Path) -> Dict[str, Any]:
    """Validate Configuration Service."""
    service_path = services_root / "configuration"
    
    expected_components = [
        "src/main.py",
        "src/managers/config_manager.py",
        "src/managers/scoring_config.py",
        "src/managers/position_config.py",
        "configs/scoring_systems.yaml",
        "configs/league_settings.yaml"
    ]
    
    result = check_service_structure(service_path, expected_components)
    result["service_name"] = "Configuration Service"
    return result

def validate_data_ingestion_service(services_root: Path) -> Dict[str, Any]:
    """Validate Data Ingestion Service."""
    service_path = services_root / "data-ingestion"
    
    expected_components = [
        "src/main.py",
        "src/acquisition/nfl_data_fetcher.py",
        "src/cleaning/data_cleaning.py", 
        "src/storage/data_storage.py"
    ]
    
    result = check_service_structure(service_path, expected_components)
    result["service_name"] = "Data Ingestion Service"
    return result

def validate_feature_engineering_service(services_root: Path) -> Dict[str, Any]:
    """Validate Feature Engineering Service."""
    service_path = services_root / "feature-engineering"
    
    expected_components = [
        "src/main.py",
        "src/processors/feature_engineering.py",
        "src/position_features/qb_features.py",
        "src/position_features/rb_features.py",
        "src/position_features/wr_features.py",
        "src/position_features/te_features.py",
        "src/quality/data_quality_validator.py"
    ]
    
    result = check_service_structure(service_path, expected_components)
    result["service_name"] = "Feature Engineering Service"
    return result

def validate_ml_models_service(services_root: Path) -> Dict[str, Any]:
    """Validate ML Models Service."""
    service_path = services_root / "ml-models"
    
    expected_components = [
        "src/main.py",
        "src/models/ensemble_model.py",
        "src/serving/model_registry.py",
        "src/serving/prediction_engine.py",
        "src/training/model_trainer.py",
        "src/persistence/model_persistence.py"
    ]
    
    result = check_service_structure(service_path, expected_components)
    result["service_name"] = "ML Models Service"
    return result

def validate_ranking_service(services_root: Path) -> Dict[str, Any]:
    """Validate Ranking Service."""
    service_path = services_root / "ranking"
    
    expected_components = [
        "src/main.py",
        "src/calculation/vor_calculator.py",
        "src/scoring/scoring_engine.py",
        "src/outputs/cheatsheet_generator.py",
        "src/validation/ranking_validator.py"
    ]
    
    result = check_service_structure(service_path, expected_components)
    result["service_name"] = "Ranking Service"
    return result

def validate_orchestration_service(services_root: Path) -> Dict[str, Any]:
    """Validate Orchestration Service."""
    service_path = services_root / "orchestration"
    
    expected_components = [
        "src/main.py",
        "src/coordination/workflow_engine.py",
        "src/workflows/full_pipeline_workflow.py",
        "src/monitoring/health_checker.py",
        "src/scheduling/scheduler.py"
    ]
    
    result = check_service_structure(service_path, expected_components)
    result["service_name"] = "Orchestration Service"
    return result

def check_legacy_code_organization(root_path: Path) -> Dict[str, Any]:
    """Check that legacy code is properly organized."""
    legacy_components = [
        "src/data_acquisition.py",
        "src/data_cleaning.py", 
        "src/feature_engineering.py",
        "src/ensemble_model.py",
        "generate_draft_rankings.py",
        "main.py"
    ]
    
    result = check_service_structure(root_path, legacy_components)
    result["service_name"] = "Legacy Code"
    return result

def validate_data_structure(root_path: Path) -> Dict[str, Any]:
    """Validate data directory structure."""
    data_components = [
        "data/raw",
        "data/processed",
        "data/draft_lists",
        "saved_models"
    ]
    
    result = check_service_structure(root_path, data_components)
    result["service_name"] = "Data Structure"
    return result

def print_service_validation(result: Dict[str, Any]) -> None:
    """Print validation results for a service."""
    name = result["service_name"]
    score = result["score"]
    total = result["total"]
    percentage = (score / total * 100) if total > 0 else 0
    
    status = "✅" if score == total else "⚠️" if score > total // 2 else "❌"
    print(f"  {status} {name}: {score}/{total} ({percentage:.0f}%)")
    
    if score < total:
        missing = [comp for comp, exists in result["components"].items() if not exists]
        if missing:
            print(f"    Missing: {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}")

def main():
    """Run microservices validation."""
    print("🏗️  Fantasy Football Microservices Architecture Validation")
    print("=" * 65)
    
    root_path = Path(__file__).parent
    services_root = root_path / "services"
    
    # Validate each service
    validators = [
        validate_configuration_service,
        validate_data_ingestion_service,
        validate_feature_engineering_service,
        validate_ml_models_service,
        validate_ranking_service,
        validate_orchestration_service
    ]
    
    service_results = []
    for validator in validators:
        result = validator(services_root)
        service_results.append(result)
        print_service_validation(result)
    
    # Validate supporting structure
    print("\\n🗂️  Supporting Structure:")
    legacy_result = check_legacy_code_organization(root_path)
    data_result = validate_data_structure(root_path)
    
    print_service_validation(legacy_result)
    print_service_validation(data_result)
    
    # Overall summary
    total_services = len(service_results)
    fully_complete = sum(1 for r in service_results if r["score"] == r["total"])
    partially_complete = sum(1 for r in service_results if r["score"] > r["total"] // 2 and r["score"] < r["total"])
    incomplete = sum(1 for r in service_results if r["score"] <= r["total"] // 2)
    
    print("\\n📊 Architecture Summary:")
    print(f"  Fully Complete Services: {fully_complete}/{total_services}")
    print(f"  Partially Complete: {partially_complete}/{total_services}")
    print(f"  Incomplete: {incomplete}/{total_services}")
    
    # Overall health score
    total_possible = sum(r["total"] for r in service_results)
    total_achieved = sum(r["score"] for r in service_results)
    overall_percentage = (total_achieved / total_possible * 100) if total_possible > 0 else 0
    
    print(f"\\n🎯 Overall Completion: {total_achieved}/{total_possible} ({overall_percentage:.1f}%)")
    
    # Status assessment
    if overall_percentage >= 90:
        print("\\n🎉 Excellent! Microservices architecture is nearly complete.")
        status = "excellent"
    elif overall_percentage >= 75:
        print("\\n✅ Good! Most microservices are properly structured.")
        status = "good"
    elif overall_percentage >= 50:
        print("\\n⚠️  Fair. Some microservices need additional work.")
        status = "fair"
    else:
        print("\\n❌ Poor. Significant work needed on microservices architecture.")
        status = "poor"
    
    # Recommendations
    print("\\n💡 Next Steps:")
    if fully_complete == total_services:
        print("  - All services are structurally complete!")
        print("  - Ready to test with Docker containers")
        print("  - Consider end-to-end integration testing")
    else:
        print("  - Complete missing components in services")
        print("  - Add missing Docker configurations")  
        print("  - Test service imports and basic functionality")
    
    return status in ["excellent", "good"]

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)