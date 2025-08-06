#!/bin/bash
# Wait for all microservices to be healthy

echo "🚀 Waiting for Fantasy Draft Engine microservices to start..."

services=(
    "Configuration Service:8001"
    "Data Ingestion Service:8002" 
    "Feature Engineering Service:8003"
    "ML Models Service:8004"
    "Ranking Service:8005"
    "Orchestration Service:8006"
)

wait_for_service() {
    local service_name="$1"
    local port="$2"
    local url="http://localhost:$port/health/live"
    
    echo "⏳ Waiting for $service_name (port $port)..."
    
    for i in {1..30}; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo "✅ $service_name is ready"
            return 0
        fi
        sleep 2
    done
    
    echo "❌ $service_name failed to start within 60 seconds"
    return 1
}

# Wait for all services
all_ready=true
for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if ! wait_for_service "$name" "$port"; then
        all_ready=false
    fi
done

if $all_ready; then
    echo ""
    echo "🎉 All services are ready!"
    echo ""
    echo "Service Health Check URLs:"
    echo "  Configuration:       http://localhost:8001/health/deep"
    echo "  Data Ingestion:      http://localhost:8002/health/deep"
    echo "  Feature Engineering: http://localhost:8003/health/deep"
    echo "  ML Models:           http://localhost:8004/health/deep"
    echo "  Ranking:             http://localhost:8005/health/deep"
    echo "  Orchestration:       http://localhost:8006/health/deep"
    echo ""
    echo "Run the pipeline:"
    echo "  curl -X POST http://localhost:8006/api/v1/workflows/full-pipeline"
    echo ""
else
    echo ""
    echo "❌ Some services failed to start. Check the logs:"
    echo "  docker-compose logs"
    exit 1
fi