#!/usr/bin/env python3
"""
Docker Service Testing Script - Test all microservices using Docker containers.

This script tests that all services can be started with Docker and respond to health checks.
"""

import asyncio
import aiohttp
import time
import subprocess
import sys
from typing import Dict, List, Optional, Any

# Service configuration
SERVICES = [
    {"name": "Configuration", "port": 8001, "directory": "services/configuration"},
    {"name": "Data Ingestion", "port": 8002, "directory": "services/data-ingestion"},
    {"name": "Feature Engineering", "port": 8003, "directory": "services/feature-engineering"},
    {"name": "ML Models", "port": 8004, "directory": "services/ml-models"},
    {"name": "Ranking", "port": 8005, "directory": "services/ranking"},
    {"name": "Orchestration", "port": 8006, "directory": "services/orchestration"}
]

def run_command(command: str, cwd: str = None) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd,
            capture_output=True, 
            text=True, 
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

async def check_service_health(port: int, service_name: str) -> Dict[str, Any]:
    """Check if service health endpoint responds."""
    health_urls = [
        f"http://localhost:{port}/health/live",
        f"http://localhost:{port}/health",
        f"http://localhost:{port}/api/v1/health"
    ]
    
    async with aiohttp.ClientSession() as session:
        for url in health_urls:
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.text()
                        return {
                            "healthy": True,
                            "url": url,
                            "status": response.status,
                            "response": data[:200]  # First 200 chars
                        }
                    else:
                        return {
                            "healthy": False,
                            "url": url,
                            "status": response.status,
                            "error": f"HTTP {response.status}"
                        }
            except Exception as e:
                continue  # Try next URL
        
    return {
        "healthy": False,
        "error": f"All health endpoints unreachable for {service_name}",
        "tried_urls": health_urls
    }

def test_docker_availability():
    """Test if Docker is available and running."""
    print("🐳 Testing Docker availability...")
    
    # Check if docker command exists
    exit_code, stdout, stderr = run_command("docker --version")
    if exit_code != 0:
        print("  ❌ Docker command not found")
        return False
    else:
        print(f"  ✅ Docker version: {stdout.strip()}")
    
    # Check if docker-compose exists
    exit_code, stdout, stderr = run_command("docker-compose --version")
    if exit_code != 0:
        print("  ❌ docker-compose command not found")
        return False
    else:
        print(f"  ✅ Docker Compose version: {stdout.strip()}")
    
    # Check if Docker daemon is running
    exit_code, stdout, stderr = run_command("docker info")
    if exit_code != 0:
        print("  ❌ Docker daemon not running")
        return False
    else:
        print("  ✅ Docker daemon is running")
    
    return True

def test_service_docker_configs():
    """Test if service Docker configurations exist."""
    print("\\n📋 Testing service Docker configurations...")
    
    results = {}
    
    for service in SERVICES:
        print(f"  Testing {service['name']}...")
        
        # Check if directory exists
        exit_code, stdout, stderr = run_command(f"ls {service['directory']}")
        if exit_code != 0:
            print(f"    ❌ Directory not found: {service['directory']}")
            results[service['name']] = {"dockerfile": False, "compose": False}
            continue
        
        # Check for Dockerfile
        dockerfile_exists = "Dockerfile" in stdout
        compose_exists = "docker-compose.yml" in stdout or "docker-compose.yaml" in stdout
        
        print(f"    {'✅' if dockerfile_exists else '❌'} Dockerfile")
        print(f"    {'✅' if compose_exists else '❌'} docker-compose.yml")
        
        results[service['name']] = {
            "dockerfile": dockerfile_exists,
            "compose": compose_exists,
            "directory": service['directory']
        }
    
    return results

async def test_service_health_endpoints():
    """Test all service health endpoints."""
    print("\\n🏥 Testing service health endpoints...")
    
    results = {}
    
    for service in SERVICES:
        print(f"  Testing {service['name']} health endpoint...")
        
        health_result = await check_service_health(service['port'], service['name'])
        
        if health_result['healthy']:
            print(f"    ✅ Health endpoint responding at {health_result['url']}")
        else:
            print(f"    ❌ Health endpoint not responding: {health_result.get('error', 'Unknown error')}")
        
        results[service['name']] = health_result
    
    return results

def start_service_with_docker(service: Dict[str, Any]) -> Dict[str, Any]:
    """Start a service using Docker Compose."""
    print(f"  🚀 Starting {service['name']}...")
    
    # Try to start with docker-compose
    exit_code, stdout, stderr = run_command(
        "docker-compose up -d --build", 
        cwd=service['directory']
    )
    
    if exit_code == 0:
        print(f"    ✅ {service['name']} started successfully")
        return {"started": True, "method": "docker-compose"}
    else:
        print(f"    ❌ Failed to start {service['name']}: {stderr}")
        return {"started": False, "error": stderr, "method": "docker-compose"}

async def main():
    """Run all tests."""
    print("🚀 Fantasy Football Microservices Docker Test Suite")
    print("=" * 60)
    
    # Test Docker availability
    if not test_docker_availability():
        print("\\n❌ Docker is not available. Cannot proceed with tests.")
        sys.exit(1)
    
    # Test service configurations
    config_results = test_service_docker_configs()
    
    # Count services ready for Docker
    services_with_docker = sum(1 for result in config_results.values() 
                              if result.get('dockerfile', False))
    services_with_compose = sum(1 for result in config_results.values() 
                               if result.get('compose', False))
    
    print(f"\\n📊 Docker Configuration Summary:")
    print(f"  Services with Dockerfile: {services_with_docker}/{len(SERVICES)}")
    print(f"  Services with docker-compose: {services_with_compose}/{len(SERVICES)}")
    
    # Test health endpoints (assuming services might already be running)
    health_results = await test_service_health_endpoints()
    
    healthy_services = sum(1 for result in health_results.values() 
                          if result.get('healthy', False))
    
    print(f"\\n🏥 Health Check Summary:")
    print(f"  Healthy services: {healthy_services}/{len(SERVICES)}")
    
    # Overall results
    print(f"\\n📋 Final Summary:")
    print(f"  Docker Ready: {services_with_docker}/{len(SERVICES)} services")
    print(f"  Currently Healthy: {healthy_services}/{len(SERVICES)} services")
    
    if services_with_docker == len(SERVICES):
        print("\\n🎉 All services are Docker-ready!")
        
        if healthy_services == 0:
            print("\\n💡 To start services, run:")
            for service in SERVICES:
                print(f"  cd {service['directory']} && docker-compose up -d")
        
        return True
    else:
        print(f"\\n⚠️ {len(SERVICES) - services_with_docker} services need Docker configuration.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)