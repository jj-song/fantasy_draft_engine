#!/usr/bin/env python3
"""
End-to-End Pipeline Validation Script

This script validates the complete fantasy football prediction pipeline
from data ingestion through rankings generation using the microservices architecture.

Usage:
    python validate_end_to_end.py
"""

import os
import sys
import time
import requests
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

def check_service_health(service_name: str, port: int, timeout: int = 30) -> bool:
    """Check if a service is healthy and ready."""
    print(f"🔍 Checking {service_name} service health...")
    
    url = f"http://localhost:{port}/health/live"
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get('status', 'unknown')
                print(f"   ✅ {service_name} is {status}")
                return True
            else:
                print(f"   ⚠️ {service_name} returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ⏳ {service_name} not ready, waiting...")
            time.sleep(2)
        except Exception as e:
            print(f"   ❌ Error checking {service_name}: {e}")
            time.sleep(2)
    
    print(f"   ❌ {service_name} not ready after {timeout} seconds")
    return False

def wait_for_all_services() -> Dict[str, bool]:
    """Wait for all required services to be healthy."""
    print("🚀 WAITING FOR ALL MICROSERVICES TO BE READY")
    print("=" * 60)
    
    services = {
        "Configuration": 8001,
        "Data Ingestion": 8002,
        "Feature Engineering": 8003,
        "ML Models": 8004,
        "Ranking": 8005,
        "Orchestration": 8006
    }
    
    service_status = {}
    
    for service_name, port in services.items():
        service_status[service_name] = check_service_health(service_name, port, timeout=60)
    
    return service_status

def test_configuration_service() -> bool:
    """Test configuration service endpoints."""
    print(f"\n🔧 Testing Configuration Service...")
    
    try:
        # Test config retrieval
        response = requests.get("http://localhost:8001/api/v1/config", timeout=10)
        if response.status_code == 200:
            config = response.json()
            print(f"   ✅ Configuration retrieved")
            print(f"   Environment: {config.get('environment', 'unknown')}")
            return True
        else:
            print(f"   ❌ Config retrieval failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Configuration service error: {e}")
        return False

def test_data_ingestion_service() -> bool:
    """Test data ingestion service endpoints."""
    print(f"\n📊 Testing Data Ingestion Service...")
    
    try:
        # Test data ingestion status
        response = requests.get("http://localhost:8002/api/v1/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ Data Ingestion status retrieved")
            print(f"   Data sources: {status.get('data_sources', 0)}")
            return True
        else:
            print(f"   ❌ Data Ingestion status failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Data Ingestion service error: {e}")
        return False

def test_feature_engineering_service() -> bool:
    """Test feature engineering service endpoints."""
    print(f"\n🔧 Testing Feature Engineering Service...")
    
    try:
        # Test feature engineering status
        response = requests.get("http://localhost:8003/api/v1/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ Feature Engineering status retrieved")
            print(f"   Processors loaded: {status.get('processors_loaded', 0)}")
            return True
        else:
            print(f"   ❌ Feature Engineering status failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Feature Engineering service error: {e}")
        return False

def test_ml_models_service() -> bool:
    """Test ML models service endpoints."""
    print(f"\n🤖 Testing ML Models Service...")
    
    try:
        # Test model registry status
        response = requests.get("http://localhost:8004/api/v1/models/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ ML Models status retrieved")
            print(f"   Models loaded: {status.get('models_loaded', 0)}")
            
            # Test prediction endpoint with sample data
            sample_prediction = {
                "position": "RB",
                "features": {
                    "age": 25,
                    "games": 16,
                    "carries": 200,
                    "rushing_yards": 1000,
                    "rushing_tds": 8,
                    "targets": 50,
                    "receptions": 40,
                    "receiving_yards": 400,
                    "receiving_tds": 2
                },
                "player_data": {
                    "player_id": "test_rb",
                    "player_name": "Test RB",
                    "team": "KC"
                }
            }
            
            pred_response = requests.post(
                "http://localhost:8004/api/v1/predict/single",
                json=sample_prediction,
                timeout=15
            )
            
            if pred_response.status_code == 200:
                prediction = pred_response.json()
                print(f"   ✅ Sample RB prediction: {prediction.get('prediction', 0):.2f} points")
                return True
            else:
                print(f"   ⚠️ Prediction test failed: {pred_response.status_code}")
                return False
            
        else:
            print(f"   ❌ ML Models status failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ ML Models service error: {e}")
        return False

def test_ranking_service() -> bool:
    """Test ranking service endpoints."""
    print(f"\n🏆 Testing Ranking Service...")
    
    try:
        # Test ranking status
        response = requests.get("http://localhost:8005/api/v1/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ Ranking service status retrieved")
            print(f"   Ranking engines: {status.get('ranking_engines', 0)}")
            return True
        else:
            print(f"   ❌ Ranking status failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Ranking service error: {e}")
        return False

def test_end_to_end_pipeline() -> bool:
    """Test the complete end-to-end pipeline."""
    print(f"\n🚀 Testing End-to-End Pipeline...")
    
    try:
        # Test orchestration service to run full pipeline
        pipeline_request = {
            "pipeline_type": "full_rankings",
            "positions": ["QB", "RB", "WR", "TE"],
            "season": 2024,
            "league_settings": {
                "scoring": "half_ppr",
                "teams": 12,
                "roster_size": 16
            }
        }
        
        print("   🔄 Starting full pipeline execution...")
        response = requests.post(
            "http://localhost:8006/api/v1/pipeline/execute",
            json=pipeline_request,
            timeout=120  # Extended timeout for full pipeline
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Pipeline executed successfully")
            
            # Check if rankings were generated
            if result.get('rankings_generated'):
                print(f"   ✅ Rankings generated for {len(result.get('rankings', []))} players")
                
                # Show sample rankings
                rankings = result.get('rankings', [])[:5]  # Top 5
                print(f"   📊 Top 5 Players:")
                for i, player in enumerate(rankings, 1):
                    name = player.get('player_name', 'Unknown')
                    pos = player.get('position', 'Unknown')
                    proj = player.get('projected_points', 0)
                    vor = player.get('vor', 0)
                    print(f"      {i}. {name} ({pos}): {proj:.1f} pts, VOR: {vor:.1f}")
                
                return True
            else:
                print(f"   ⚠️ Pipeline ran but no rankings generated")
                return False
                
        else:
            print(f"   ❌ Pipeline execution failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ End-to-end pipeline error: {e}")
        return False

def generate_validation_report(results: Dict[str, bool]) -> None:
    """Generate a comprehensive validation report."""
    print(f"\n📋 END-TO-END VALIDATION REPORT")
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"System: Fantasy Football Draft Engine - Microservices Architecture")
    
    # Service Health Summary
    print(f"\n🏥 Service Health Summary:")
    service_results = {k: v for k, v in results.items() if 'Service' in k}
    healthy_services = sum(1 for v in service_results.values() if v)
    total_services = len(service_results)
    
    for service, status in service_results.items():
        emoji = "✅" if status else "❌"
        print(f"   {emoji} {service}: {'Healthy' if status else 'Unhealthy'}")
    
    print(f"\n   Overall: {healthy_services}/{total_services} services healthy")
    
    # Functionality Tests Summary
    print(f"\n🧪 Functionality Tests Summary:")
    func_results = {k: v for k, v in results.items() if 'Test' in k}
    passed_tests = sum(1 for v in func_results.values() if v)
    total_tests = len(func_results)
    
    for test, status in func_results.items():
        emoji = "✅" if status else "❌"
        print(f"   {emoji} {test}: {'Passed' if status else 'Failed'}")
    
    print(f"\n   Overall: {passed_tests}/{total_tests} tests passed")
    
    # Overall System Status
    print(f"\n🎯 Overall System Status:")
    all_passed = all(results.values())
    
    if all_passed:
        print(f"   🎉 SYSTEM FULLY OPERATIONAL")
        print(f"   ✅ All services healthy and functional")
        print(f"   ✅ End-to-end pipeline validated")
        print(f"   🚀 Ready for production deployment!")
    else:
        print(f"   ⚠️ SYSTEM PARTIALLY OPERATIONAL")
        failed_components = [k for k, v in results.items() if not v]
        print(f"   ❌ Failed components: {len(failed_components)}")
        for component in failed_components:
            print(f"      - {component}")
        print(f"   🔧 Address failed components before production")
    
    # Next Steps
    print(f"\n🚀 Next Steps:")
    if all_passed:
        print(f"   1. Performance testing under load")
        print(f"   2. Security audit and hardening")
        print(f"   3. Production deployment")
        print(f"   4. Monitoring and alerting setup")
    else:
        print(f"   1. Fix failed components listed above")
        print(f"   2. Re-run validation once fixes are applied")
        print(f"   3. Proceed with production preparation")

def main():
    """Main validation function."""
    print("🚀 FANTASY FOOTBALL DRAFT ENGINE - END-TO-END VALIDATION")
    print("=" * 80)
    print("This script validates the complete microservices pipeline")
    print("from data ingestion through final rankings generation.")
    print("=" * 80)
    
    # Wait for all services to be ready
    service_status = wait_for_all_services()
    
    # If not all services are ready, provide guidance
    ready_services = sum(1 for v in service_status.values() if v)
    total_services = len(service_status)
    
    if ready_services < total_services:
        print(f"\n⚠️ NOT ALL SERVICES ARE READY")
        print(f"   Ready: {ready_services}/{total_services} services")
        print(f"   This validation will test available services only.")
        print(f"   For full validation, ensure all services are running.")
    
    # Run validation tests
    results = {}
    results.update(service_status)
    
    # Test individual service functionality
    if service_status.get("Configuration", False):
        results["Configuration Test"] = test_configuration_service()
    
    if service_status.get("Data Ingestion", False):
        results["Data Ingestion Test"] = test_data_ingestion_service()
    
    if service_status.get("Feature Engineering", False):
        results["Feature Engineering Test"] = test_feature_engineering_service()
    
    if service_status.get("ML Models", False):
        results["ML Models Test"] = test_ml_models_service()
    
    if service_status.get("Ranking", False):
        results["Ranking Test"] = test_ranking_service()
    
    # Test end-to-end pipeline (only if all critical services are ready)
    critical_services = ["Configuration", "Feature Engineering", "ML Models", "Ranking", "Orchestration"]
    if all(service_status.get(svc, False) for svc in critical_services):
        results["End-to-End Pipeline Test"] = test_end_to_end_pipeline()
    else:
        print(f"\n⏳ Skipping end-to-end test - waiting for critical services to be ready")
        results["End-to-End Pipeline Test"] = False
    
    # Generate comprehensive report
    generate_validation_report(results)
    
    # Return overall success
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)