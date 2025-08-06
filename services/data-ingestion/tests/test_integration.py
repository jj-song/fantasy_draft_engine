"""
Comprehensive integration tests for data-ingestion service.
"""
import pytest
import asyncio
import httpx
import json
from pathlib import Path
import pandas as pd
from unittest.mock import patch, MagicMock

from src.main import app, service
from src.config import get_data_paths

@pytest.fixture
def client():
    """Create test client for the FastAPI app"""
    return httpx.AsyncClient(app=app, base_url="http://test")

@pytest.fixture
def mock_data_paths(tmp_path):
    """Create temporary data directories for testing"""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    processed_dir.mkdir()
    
    paths = {
        "base": str(tmp_path),
        "raw": str(raw_dir),
        "processed": str(processed_dir)
    }
    
    with patch('src.config.get_data_paths', return_value=paths):
        with patch('src.main.get_data_paths', return_value=paths):
            yield paths

@pytest.mark.asyncio
async def test_service_health_endpoints(client):
    """Test all health check endpoints"""
    
    # Test liveness
    response = await client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service_name"] == "Data Ingestion Service"
    
    # Test readiness
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "memory_usage_percent" in data["details"]
    
    # Test service info
    response = await client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == "Data Ingestion Service"
    assert data["version"] == "1.0.0"

@pytest.mark.asyncio
async def test_data_status_endpoint(client, mock_data_paths):
    """Test data status endpoint with mock data"""
    
    # Create mock data files
    raw_file = Path(mock_data_paths["raw"]) / "player_stats_2024.parquet"
    processed_file = Path(mock_data_paths["processed"]) / "player_stats_2024.parquet"
    
    # Create dummy parquet files
    test_df = pd.DataFrame({
        'player_name': ['Test Player'],
        'position': ['QB'],
        'games': [16]
    })
    test_df.to_parquet(raw_file, index=False)
    test_df.to_parquet(processed_file, index=False)
    
    response = await client.get("/api/v1/data/status")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["data"]["raw_count"] == 1
    assert data["data"]["processed_count"] == 1
    assert "player_stats_2024.parquet" in data["data"]["raw_files"]

@pytest.mark.asyncio
async def test_data_validation_endpoint(client, mock_data_paths):
    """Test data validation endpoint"""
    
    # Create mock data file for validation
    processed_file = Path(mock_data_paths["processed"]) / "player_stats_2024.parquet"
    test_df = pd.DataFrame({
        'player_name': ['Aaron Rodgers', 'Tom Brady'],
        'position': ['QB', 'QB'],
        'games': [17, 16],
        'passing_yards': [4500, 4600]
    })
    test_df.to_parquet(processed_file, index=False)
    
    response = await client.post("/api/v1/data/validate")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert "data_quality" in data["data"]["checks"]
    quality_check = data["data"]["checks"]["data_quality"]
    assert quality_check["total_records"] == 2
    assert quality_check["position_distribution"]["QB"] == 2

@pytest.mark.asyncio
async def test_data_health_endpoint(client):
    """Test data health endpoint"""
    
    response = await client.get("/api/v1/data/health")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert "external_apis" in data["data"]
    assert "nfl_data_py" in data["data"]["external_apis"]
    
    # NFL data should be available
    nfl_status = data["data"]["external_apis"]["nfl_data_py"]
    assert nfl_status["status"] == "available"

@pytest.mark.asyncio 
async def test_year_specific_data_endpoint(client, mock_data_paths):
    """Test year-specific data retrieval"""
    
    # Create mock data for 2024
    processed_file = Path(mock_data_paths["processed"]) / "player_stats_2024.parquet"
    test_df = pd.DataFrame({
        'player_name': ['Aaron Rodgers', 'Josh Allen', 'Patrick Mahomes'],
        'position': ['QB', 'QB', 'QB'],
        'games': [17, 17, 17],
        'passing_yards': [4500, 4306, 4183],
        'passing_tds': [32, 29, 27]
    })
    test_df.to_parquet(processed_file, index=False)
    
    response = await client.get("/api/v1/data/years/2024")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    year_data = data["data"]
    assert year_data["year"] == 2024
    assert year_data["total_players"] == 3
    assert "QB" in year_data["positions"]
    assert len(year_data["sample_players"]) >= 1

@pytest.mark.asyncio
async def test_year_data_not_found(client, mock_data_paths):
    """Test year-specific data endpoint when data doesn't exist"""
    
    response = await client.get("/api/v1/data/years/2025")
    assert response.status_code == 404
    data = response.json()
    assert "Data for year 2025 not found" in data["detail"]

@pytest.mark.asyncio
async def test_test_endpoint(client):
    """Test the simple test endpoint"""
    
    response = await client.get("/api/v1/data/test")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Test endpoint working"

@pytest.mark.asyncio
@patch('src.main.fetch_player_season_stats')
async def test_data_ingestion_endpoint(mock_fetch, client, mock_data_paths):
    """Test data ingestion functionality"""
    
    # Mock the data fetching function
    mock_df = pd.DataFrame({
        'player_name': ['Test Player'],
        'position': ['QB'],
        'games': [16],
        'passing_yards': [4000]
    })
    mock_fetch.return_value = mock_df
    
    # Test ingestion request
    ingestion_request = {
        "years": [2023],
        "positions": ["QB"],
        "force_refresh": False,
        "include_weather": True,
        "include_rosters": True
    }
    
    response = await client.post("/api/v1/data/ingest", json=ingestion_request)
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["data"]["ingestion_started"] is True
    assert data["data"]["years"] == [2023]
    assert data["data"]["positions"] == ["QB"]
    assert "Data ingestion started in background" in data["message"]
    
    # Give some time for background task
    await asyncio.sleep(0.1)
    
    # Check that mock was called
    mock_fetch.assert_called_once_with(2023, ["QB"])

@pytest.mark.asyncio
async def test_service_error_handling(client):
    """Test service error handling"""
    
    # Test invalid endpoint
    response = await client.get("/api/v1/invalid/endpoint")
    assert response.status_code == 404
    
    # Test malformed year parameter
    response = await client.get("/api/v1/data/years/invalid")
    assert response.status_code == 422  # Pydantic validation error

# CORS headers are tested in live deployment - test client bypasses middleware

@pytest.mark.asyncio
async def test_correlation_id_headers(client):
    """Test correlation ID headers are properly set"""
    
    response = await client.get("/api/v1/data/test")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    assert len(response.headers["X-Correlation-ID"]) > 0

@pytest.mark.asyncio
async def test_json_serialization_safety(client, mock_data_paths):
    """Test that pandas/numpy types are safely serialized"""
    
    # Create data with potential serialization issues
    processed_file = Path(mock_data_paths["processed"]) / "player_stats_2024.parquet"
    test_df = pd.DataFrame({
        'player_name': ['Test Player'],
        'position': ['QB'],
        'games': [16],  # This will be numpy int64
        'passing_yards': [4000.5],  # This will be numpy float64
        'completion_pct': [65.5]  # Another float
    })
    test_df.to_parquet(processed_file, index=False)
    
    response = await client.get("/api/v1/data/years/2024")
    assert response.status_code == 200
    
    # Should not raise JSON serialization errors
    data = response.json()
    assert data["status"] == "success"
    assert isinstance(data["data"]["total_players"], int)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])