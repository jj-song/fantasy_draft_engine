#!/usr/bin/env python3
"""
Test script to demonstrate enhanced payload logging middleware.
This script creates a minimal FastAPI service to show request/response body logging.
"""

from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn
import sys
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent))

from utils.logging.config import get_service_logger
from utils.logging.middleware import add_logging_middleware

# Create FastAPI app
app = FastAPI(title="Payload Logging Test Service")

# Initialize logging
logger = get_service_logger("test-service", "1.0.0")

# Add enhanced logging middleware with payload logging enabled
add_logging_middleware(
    app,
    service_name="test-service",
    logger=logger,
    enable_service_discovery=True,
    log_request_body=True,   # ✅ Enable request payload logging
    log_response_body=True   # ✅ Enable response payload logging
)

# Test data model
class PredictionRequest(BaseModel):
    position: str
    features: dict
    player_data: dict

class PredictionResponse(BaseModel):
    status: str
    prediction: float
    confidence: float
    player_name: str

@app.get("/health")
async def health_check():
    """Simple health check"""
    return {"status": "healthy", "service": "test-service"}

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Test prediction endpoint with request/response payloads"""
    logger.info(f"Processing prediction for {request.position} position")
    
    # Simulate ML prediction
    prediction_value = 15.7 if request.position == "QB" else 8.3
    
    return PredictionResponse(
        status="success",
        prediction=prediction_value,
        confidence=0.85,
        player_name=request.player_data.get("player_name", "Unknown")
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Enhanced Payload Logging Test Service",
        "endpoints": {
            "health": "/health",
            "predict": "/predict (POST)",
            "features": ["request_body_logging", "response_body_logging", "correlation_tracking"]
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Enhanced Payload Logging Test Service...")
    print("📋 Features enabled:")
    print("   ✅ Request body logging")
    print("   ✅ Response body logging") 
    print("   ✅ Correlation ID tracking")
    print("   ✅ Performance metrics")
    print("")
    print("🔥 Test with:")
    print("   curl http://localhost:8080/health")
    print('   curl -X POST http://localhost:8080/predict -H "Content-Type: application/json" -d \'{"position":"QB","features":{"games":16,"yards":3500},"player_data":{"player_name":"Test Player"}}\'')
    print("")
    
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")