#!/usr/bin/env python3
"""
Service Testing Script - Test all microservices for basic functionality.

This script tests that all services can be imported and started without errors.
"""

import sys
import os
from pathlib import Path
import traceback

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "legacy"))

def test_service_imports():
    """Test that all services can be imported."""
    print("🔍 Testing service imports...")
    
    service_tests = {
        "Configuration": "services.configuration.src.main",
        "Data Ingestion": "services.data_ingestion.src.main", 
        "Feature Engineering": "services.feature_engineering.src.main",
        "ML Models": "services.ml_models.src.main",
        "Ranking": "services.ranking.src.main",
        "Orchestration": "services.orchestration.src.main"
    }
    
    results = {}
    
    for service_name, module_path in service_tests.items():
        try:
            print(f"  Testing {service_name}...")
            
            # Fix module path for import
            fixed_path = module_path.replace("-", "_")
            
            # Try to import the module
            __import__(fixed_path)
            
            print(f"    ✅ {service_name} imports successfully")
            results[service_name] = {"success": True, "error": None}
            
        except Exception as e:
            print(f"    ❌ {service_name} import failed: {e}")
            results[service_name] = {"success": False, "error": str(e)}
            
            # Print detailed traceback for debugging
            print(f"    Traceback:")
            traceback.print_exc()
    
    return results

def test_basic_functionality():
    """Test basic functionality of services."""
    print("\n🧪 Testing basic service functionality...")
    
    # Test VOR Calculator
    try:
        print("  Testing VOR Calculator...")
        sys.path.append(str(project_root / "services" / "ranking" / "src"))
        from calculation.vor_calculator import VORCalculator
        
        vor_calc = VORCalculator()
        print("    ✅ VOR Calculator created successfully")
    except Exception as e:
        print(f"    ❌ VOR Calculator failed: {e}")
    
    # Test Model Registry
    try:
        print("  Testing Model Registry...")
        sys.path.append(str(project_root / "services" / "ml-models" / "src"))
        from serving.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        print("    ✅ Model Registry created successfully")
    except Exception as e:
        print(f"    ❌ Model Registry failed: {e}")
    
    # Test Health Checker
    try:
        print("  Testing Health Checker...")
        sys.path.append(str(project_root / "services" / "orchestration" / "src"))
        from monitoring.health_checker import HealthChecker
        
        health_checker = HealthChecker({"test": "http://localhost:8000"})
        print("    ✅ Health Checker created successfully")
    except Exception as e:
        print(f"    ❌ Health Checker failed: {e}")

def test_legacy_imports():
    """Test that legacy imports still work."""
    print("\n📚 Testing legacy imports...")
    
    legacy_tests = [
        ("Ensemble Model", "src.ensemble_model"),
        ("VOR Calculator", "src.ranking.vor_calculator"),
        ("Data Storage", "src.data_storage")
    ]
    
    for name, module in legacy_tests:
        try:
            print(f"  Testing {name}...")
            __import__(module)
            print(f"    ✅ {name} imports successfully")
        except Exception as e:
            print(f"    ❌ {name} import failed: {e}")

def main():
    """Run all tests."""
    print("🚀 Fantasy Football Microservices Test Suite")
    print("=" * 60)
    
    # Test imports
    import_results = test_service_imports()
    
    # Test basic functionality
    test_basic_functionality()
    
    # Test legacy imports
    test_legacy_imports()
    
    # Summary
    print("\n📊 Test Summary")
    print("-" * 40)
    
    successful_imports = sum(1 for result in import_results.values() if result["success"])
    total_services = len(import_results)
    
    print(f"Service Imports: {successful_imports}/{total_services} successful")
    
    for service_name, result in import_results.items():
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {service_name}")
    
    if successful_imports == total_services:
        print("\n🎉 All services are ready!")
        return True
    else:
        print(f"\n⚠️ {total_services - successful_imports} services need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)