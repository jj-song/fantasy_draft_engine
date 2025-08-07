#!/usr/bin/env python3
"""
System Monitor and Auto-Recovery Script
======================================

This script monitors the fantasy draft engine services and provides automated
recovery for common issues. It's designed to prevent and resolve the types of
issues we encountered during initial setup.

Usage:
    python utils/system_monitor.py --check-all
    python utils/system_monitor.py --auto-recover
    python utils/system_monitor.py --docker-status
"""

import subprocess
import json
import time
import sys
import argparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Import requests with error handling for local logging conflicts
try:
    import requests
except ImportError as e:
    print(f"⚠️ Warning: requests library not available: {e}")
    print("   Run: pip install requests")
    requests = None


class SystemMonitor:
    """Monitor and auto-recover Fantasy Draft Engine services."""
    
    def __init__(self):
        self.services = {
            'orchestration': 8006,
            'ranking': 8005, 
            'ml-models': 8004,
            'feature-engineering': 8003,
            'data-ingestion': 8002,
            'configuration': 8001,
            'redis': 6379
        }
        
        self.docker_compose_file = "docker-compose.yml"
        self.required_volumes = [
            "./data:/app/data",
            "./logs:/app/logs", 
            "./utils:/app/utils"
        ]
    
    def check_docker_running(self) -> bool:
        """Check if Docker daemon is running."""
        try:
            subprocess.run(['docker', 'info'], 
                         capture_output=True, check=True, timeout=10)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def start_docker_if_needed(self) -> bool:
        """Start Docker Desktop if it's not running (macOS)."""
        if self.check_docker_running():
            return True
            
        print("🐳 Docker is not running. Starting Docker Desktop...")
        try:
            subprocess.run(['open', '-a', 'Docker'], check=True)
            # Wait for Docker to start
            for i in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                if self.check_docker_running():
                    print("✅ Docker started successfully!")
                    return True
                if i % 5 == 0:
                    print(f"   Waiting for Docker to start... ({i}s)")
            
            print("⚠️ Docker failed to start within 30 seconds")
            return False
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start Docker: {e}")
            return False
    
    def check_docker_compose_config(self) -> Dict[str, List[str]]:
        """Check docker-compose.yml for common configuration issues."""
        issues = {"errors": [], "warnings": [], "fixed": []}
        
        try:
            with open(self.docker_compose_file, 'r') as f:
                content = f.read()
            
            # Check for obsolete version line
            if content.startswith('version:'):
                issues["warnings"].append("Obsolete 'version' line found in docker-compose.yml")
            
            # Check for missing utils volume mounts
            services_missing_utils = []
            for service in ['configuration', 'data-ingestion', 'feature-engineering', 
                          'ml-models', 'ranking', 'orchestration']:
                service_section = content[content.find(f'{service}:'):content.find(f'\n  ', content.find(f'{service}:'))]
                if './utils:/app/utils' not in service_section and service != 'redis':
                    services_missing_utils.append(service)
            
            if services_missing_utils:
                issues["errors"].append(f"Services missing utils volume mount: {services_missing_utils}")
                
        except FileNotFoundError:
            issues["errors"].append(f"docker-compose.yml not found")
            
        return issues
    
    def get_docker_services_status(self) -> Dict[str, str]:
        """Get status of all Docker Compose services."""
        try:
            result = subprocess.run(['docker-compose', 'ps', '--format', 'json'], 
                                  capture_output=True, text=True, check=True)
            services_data = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    services_data.append(json.loads(line))
            
            status = {}
            for service_data in services_data:
                name = service_data.get('Service', 'unknown')
                state = service_data.get('State', 'unknown')
                health = service_data.get('Health', '')
                status[name] = f"{state}" + (f" ({health})" if health else "")
            
            return status
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            return {"error": str(e)}
    
    def check_service_health(self, service: str, port: int) -> Dict[str, str]:
        """Check health endpoints for a specific service."""
        if service == 'redis':
            # Redis doesn't have HTTP endpoints
            try:
                result = subprocess.run(['docker', 'exec', f'fantasy_draft_engine-redis-1', 
                                       'redis-cli', 'ping'], 
                                      capture_output=True, text=True, timeout=5)
                return {"status": "healthy" if result.stdout.strip() == "PONG" else "unhealthy"}
            except:
                return {"status": "unhealthy"}
    
        base_url = f"http://localhost:{port}"
        health_results = {}
        
        if requests is None:
            return {"error": "requests library not available for health checks"}
            
        for endpoint in ['/health/live', '/health/ready', '/health/deep']:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                health_results[endpoint] = {
                    "status_code": response.status_code,
                    "healthy": response.status_code == 200
                }
            except requests.RequestException as e:
                health_results[endpoint] = {
                    "status_code": None,
                    "healthy": False,
                    "error": str(e)
                }
        
        return health_results
    
    def auto_recover_services(self) -> Dict[str, str]:
        """Attempt to automatically recover services."""
        recovery_log = {"actions": [], "results": []}
        
        # 1. Check and start Docker
        if not self.check_docker_running():
            recovery_log["actions"].append("Starting Docker")
            if self.start_docker_if_needed():
                recovery_log["results"].append("✅ Docker started successfully")
            else:
                recovery_log["results"].append("❌ Failed to start Docker")
                return recovery_log
        
        # 2. Check docker-compose config
        config_issues = self.check_docker_compose_config()
        if config_issues["errors"]:
            recovery_log["actions"].append(f"Config issues found: {config_issues['errors']}")
            recovery_log["results"].append("⚠️ Manual fix required for docker-compose.yml")
        
        # 3. Restart services if needed
        docker_status = self.get_docker_services_status()
        unhealthy_services = [svc for svc, status in docker_status.items() 
                            if 'running' not in status.lower()]
        
        if unhealthy_services or "error" in docker_status:
            recovery_log["actions"].append("Restarting Docker Compose services")
            try:
                subprocess.run(['docker-compose', 'down'], check=True, timeout=30)
                time.sleep(2)
                subprocess.run(['docker-compose', 'up', '-d'], check=True, timeout=120)
                recovery_log["results"].append("✅ Services restarted")
            except subprocess.CalledProcessError as e:
                recovery_log["results"].append(f"❌ Failed to restart services: {e}")
        
        return recovery_log
    
    def generate_status_report(self) -> Dict:
        """Generate comprehensive status report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "docker": {
                "daemon_running": self.check_docker_running(),
                "services": self.get_docker_services_status()
            },
            "config": self.check_docker_compose_config(),
            "health": {}
        }
        
        # Health check each service
        for service, port in self.services.items():
            report["health"][service] = self.check_service_health(service, port)
        
        return report
    
    def print_status_report(self, report: Dict):
        """Print a formatted status report."""
        print("\n" + "="*60)
        print("🏥 FANTASY DRAFT ENGINE - SYSTEM STATUS")
        print("="*60)
        print(f"📅 Report Time: {report['timestamp']}")
        
        # Docker Status
        print(f"\n🐳 Docker Status: {'✅ Running' if report['docker']['daemon_running'] else '❌ Not Running'}")
        
        # Services Status
        print(f"\n📊 Services Status:")
        for service, status in report['docker']['services'].items():
            status_emoji = "✅" if "running" in status.lower() else "❌"
            print(f"   {status_emoji} {service}: {status}")
        
        # Configuration Issues
        config = report['config']
        if config['errors']:
            print(f"\n⚠️ Configuration Issues:")
            for error in config['errors']:
                print(f"   ❌ {error}")
        
        if config['warnings']:
            print(f"\n⚠️ Warnings:")
            for warning in config['warnings']:
                print(f"   ⚠️ {warning}")
        
        # Health Status
        print(f"\n🏥 Health Status:")
        for service, health in report['health'].items():
            if service == 'redis':
                status_emoji = "✅" if health.get('status') == 'healthy' else "❌"
                print(f"   {status_emoji} {service}: {health.get('status', 'unknown')}")
            else:
                live_status = health.get('/health/live', {})
                ready_status = health.get('/health/ready', {})
                
                live_emoji = "✅" if live_status.get('healthy') else "❌"
                ready_emoji = "✅" if ready_status.get('healthy') else "❌"
                
                print(f"   {service}:")
                print(f"     {live_emoji} Live: {live_status.get('status_code', 'N/A')}")
                print(f"     {ready_emoji} Ready: {ready_status.get('status_code', 'N/A')}")
        
        print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description='Fantasy Draft Engine System Monitor')
    parser.add_argument('--check-all', action='store_true', help='Run comprehensive system check')
    parser.add_argument('--auto-recover', action='store_true', help='Attempt automatic recovery')
    parser.add_argument('--docker-status', action='store_true', help='Check Docker status only')
    
    args = parser.parse_args()
    
    monitor = SystemMonitor()
    
    if args.docker_status:
        docker_running = monitor.check_docker_running()
        print(f"🐳 Docker Status: {'✅ Running' if docker_running else '❌ Not Running'}")
        if docker_running:
            services = monitor.get_docker_services_status()
            print("📊 Services:")
            for service, status in services.items():
                print(f"   {service}: {status}")
    
    elif args.auto_recover:
        print("🔧 Starting automatic recovery...")
        recovery_log = monitor.auto_recover_services()
        
        print("\n📋 Recovery Actions:")
        for action in recovery_log["actions"]:
            print(f"   • {action}")
        
        print("\n📊 Recovery Results:")
        for result in recovery_log["results"]:
            print(f"   {result}")
    
    elif args.check_all:
        report = monitor.generate_status_report()
        monitor.print_status_report(report)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()