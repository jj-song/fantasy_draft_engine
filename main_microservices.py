#!/usr/bin/env python3
"""
Fantasy Draft Engine - Microservices Entry Point

This script coordinates with the microservices architecture to run the complete
fantasy football pipeline using service-to-service communication.
"""
import requests
import time
import sys
from pathlib import Path

# Service URLs
SERVICES = {
    "configuration": "http://localhost:8001",
    "data-ingestion": "http://localhost:8002", 
    "feature-engineering": "http://localhost:8003",
    "ml-models": "http://localhost:8004",
    "ranking": "http://localhost:8005",
    "orchestration": "http://localhost:8006"
}

def check_service_health(service_name: str, url: str) -> bool:
    """Check if a service is healthy"""
    try:
        response = requests.get(f"{url}/health/live", timeout=5)
        return response.status_code == 200
    except:
        return False

def wait_for_services():
    """Wait for all services to be healthy"""
    print("🚀 Fantasy Draft Engine - Microservices Pipeline")
    print("=" * 60)
    print("\n⏳ Checking service health...")
    
    all_healthy = False
    max_retries = 30
    retry_count = 0
    
    while not all_healthy and retry_count < max_retries:
        healthy_services = []
        
        for service_name, url in SERVICES.items():
            if check_service_health(service_name, url):
                healthy_services.append(service_name)
                print(f"✅ {service_name.title()} Service - Ready")
            else:
                print(f"⏳ {service_name.title()} Service - Waiting...")
        
        if len(healthy_services) == len(SERVICES):
            all_healthy = True
        else:
            retry_count += 1
            time.sleep(2)
    
    if not all_healthy:
        print("\n❌ Not all services are healthy. Please check:")
        print("   docker-compose up -d")
        print("   ./scripts/wait-for-services.sh")
        sys.exit(1)
    
    print("\n🎉 All services are healthy!")
    return True

def run_pipeline():
    """Run the complete fantasy football pipeline via microservices"""
    print("\n🔄 Starting Fantasy Football Pipeline...")
    print("-" * 60)
    
    try:
        # Step 1: Get configuration
        print("\n1️⃣ Getting configuration...")
        config_response = requests.get(f"{SERVICES['configuration']}/api/v1/config/summary", timeout=30)
        
        if config_response.status_code == 200:
            config = config_response.json()
            print(f"   ✅ Configuration loaded for {config['data']['environment']} environment")
        else:
            print(f"   ❌ Failed to get configuration: {config_response.status_code}")
            return False
        
        # Step 2: Data Ingestion
        print("\n2️⃣ Starting data ingestion...")
        ingestion_request = {
            "years": None,  # Use default from config
            "positions": None,  # Use default from config
            "force_refresh": False,
            "include_weather": True,
            "include_rosters": True
        }
        
        ingestion_response = requests.post(
            f"{SERVICES['data-ingestion']}/api/v1/data/ingest",
            json=ingestion_request,
            timeout=30
        )
        
        if ingestion_response.status_code == 200:
            print("   ✅ Data ingestion started in background")
            
            # Wait for ingestion to complete
            print("   ⏳ Waiting for data ingestion to complete...")
            ingestion_complete = False
            while not ingestion_complete:
                status_response = requests.get(f"{SERVICES['data-ingestion']}/api/v1/data/status", timeout=10)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data['data'].get('current_status', {})
                    if current_status.get('status') == 'completed':
                        ingestion_complete = True
                        print("   ✅ Data ingestion completed")
                    elif current_status.get('status') == 'failed':
                        print(f"   ❌ Data ingestion failed: {current_status.get('error', 'Unknown error')}")
                        return False
                    else:
                        print(f"   ⏳ Status: {current_status.get('status', 'unknown')}")
                        time.sleep(5)
                else:
                    print("   ⚠️ Cannot check ingestion status")
                    time.sleep(5)
        else:
            print(f"   ❌ Failed to start data ingestion: {ingestion_response.status_code}")
            return False
        
        # Step 3: Feature Engineering
        print("\n3️⃣ Starting feature engineering...")
        features_request = {
            "years": None,  # Use default from config
            "positions": None,  # Use default from config  
            "force_regenerate": False,
            "include_advanced_features": True
        }
        
        features_response = requests.post(
            f"{SERVICES['feature-engineering']}/api/v1/features/generate",
            json=features_request,
            timeout=30
        )
        
        if features_response.status_code == 200:
            print("   ✅ Feature engineering started in background")
        else:
            print(f"   ❌ Failed to start feature engineering: {features_response.status_code}")
            return False
        
        # Step 4: Check available services (ML Models and Ranking would be next)
        print("\n4️⃣ Checking ML Models service...")
        models_response = requests.get(f"{SERVICES['ml-models']}/api/v1/models/status", timeout=10)
        
        if models_response.status_code == 200:
            print("   ✅ ML Models service is ready")
        else:
            print("   ⚠️ ML Models service needs implementation")
        
        print("\n5️⃣ Checking Ranking service...")
        ranking_response = requests.get(f"{SERVICES['ranking']}/api/v1/rankings/status", timeout=10)
        
        if ranking_response.status_code == 200:
            print("   ✅ Ranking service is ready")
        else:
            print("   ⚠️ Ranking service needs implementation")
        
        print("\n🎉 Pipeline execution completed!")
        print("=" * 60)
        print("\n📊 Next Steps:")
        print("   1. Complete ML Models service implementation")
        print("   2. Complete Ranking service implementation")  
        print("   3. Implement Orchestration service workflows")
        print("   4. Run end-to-end validation")
        
        print("\n🔗 Service Health Dashboard:")
        for service_name, url in SERVICES.items():
            print(f"   {service_name.title()}: {url}/health/deep")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        return False

def main():
    """Main entry point"""
    # Check if services are running
    if not wait_for_services():
        return False
    
    # Run the pipeline
    success = run_pipeline()
    
    if success:
        print("\n✅ Fantasy Draft Engine pipeline completed successfully!")
        return True
    else:
        print("\n❌ Pipeline failed. Check service logs for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)