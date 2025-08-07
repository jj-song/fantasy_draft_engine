#!/bin/bash

# Fantasy Draft Engine - Service Startup Script
# ==============================================
# This script handles common startup issues and ensures all services start properly.
# It replaces the need to manually run docker-compose commands and troubleshoot issues.

set -e  # Exit on any error

echo "🚀 Fantasy Draft Engine - Starting Services"
echo "============================================="

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        return 1
    fi
    return 0
}

# Function to start Docker Desktop on macOS
start_docker_macos() {
    echo "🐳 Starting Docker Desktop..."
    open -a Docker
    
    # Wait for Docker to start (max 30 seconds)
    for i in {1..30}; do
        if check_docker; then
            echo "✅ Docker is now running!"
            return 0
        fi
        if [ $((i % 5)) -eq 0 ]; then
            echo "   Waiting for Docker to start... (${i}s)"
        fi
        sleep 1
    done
    
    echo "❌ Docker failed to start within 30 seconds"
    return 1
}

# Check if Docker is running, start if needed
echo "🔍 Checking Docker status..."
if ! check_docker; then
    echo "⚠️ Docker is not running"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        start_docker_macos || exit 1
    else
        echo "❌ Please start Docker manually and run this script again"
        exit 1
    fi
else
    echo "✅ Docker is running"
fi

# Verify docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found in current directory"
    echo "   Please run this script from the project root directory"
    exit 1
fi

# Stop any existing services
echo "🧹 Stopping any existing services..."
docker-compose down --remove-orphans 2>/dev/null || true

# Start all services
echo "🚀 Starting all services..."
if docker-compose up -d; then
    echo "✅ All services started successfully"
else
    echo "❌ Failed to start services"
    echo "📋 Showing service logs for debugging..."
    docker-compose logs --tail=20
    exit 1
fi

# Wait for services to initialize
echo "⏳ Waiting for services to initialize..."
sleep 15

# Check service status
echo "📊 Checking service status..."
docker-compose ps

# Test orchestration service
echo "🔍 Testing orchestration service..."
if curl -s http://localhost:8006/api/v1/orchestration/status >/dev/null; then
    echo "✅ Orchestration service is responding"
else
    echo "⚠️ Orchestration service may still be starting up"
    echo "   You can check status with: curl http://localhost:8006/api/v1/orchestration/status"
fi

echo ""
echo "🎉 Fantasy Draft Engine services are running!"
echo ""
echo "📋 Service Endpoints:"
echo "   • Orchestration:      http://localhost:8006"
echo "   • Ranking:           http://localhost:8005" 
echo "   • ML Models:         http://localhost:8004"
echo "   • Feature Engineering: http://localhost:8003"
echo "   • Data Ingestion:    http://localhost:8002"
echo "   • Configuration:     http://localhost:8001"
echo "   • Redis:             localhost:6379"
echo ""
echo "🔧 Useful Commands:"
echo "   • Check status:       docker-compose ps"
echo "   • View logs:         docker-compose logs -f [service-name]"
echo "   • Stop services:     docker-compose down"
echo "   • Full health check: curl http://localhost:8006/api/v1/workflows/health-check"
echo "   • Run full pipeline: curl -X POST http://localhost:8006/api/v1/workflows/full-pipeline \\"
echo "                         -H 'Content-Type: application/json' \\"
echo "                         -d '{\"workflow_type\": \"full-pipeline\", \"parameters\": {\"positions\": [\"QB\", \"RB\", \"WR\", \"TE\"], \"years\": [2024], \"season\": 2024}}'"
echo ""
echo "🏥 For system monitoring: python utils/system_monitor.py --check-all"