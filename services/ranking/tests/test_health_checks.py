"""
Tests for standardized health checks.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.health.health_checks import HealthChecker, HealthStatus

@pytest.fixture
def health_checker():
    return HealthChecker("test-service", "1.0.0")

@pytest.mark.asyncio
async def test_liveness_check(health_checker):
    """Test basic liveness check"""
    result = await health_checker.liveness_check()
    
    assert isinstance(result, HealthStatus)
    assert result.status == "healthy"
    assert result.service_name == "test-service"
    assert result.version == "1.0.0"
    assert isinstance(result.timestamp, datetime)

@pytest.mark.asyncio
@patch('psutil.virtual_memory')
@patch('psutil.cpu_percent')
@patch('psutil.disk_usage')
async def test_readiness_check_healthy(mock_disk, mock_cpu, mock_memory, health_checker):
    """Test readiness check when system is healthy"""
    # Mock healthy system resources
    mock_memory.return_value = MagicMock(percent=50.0)
    mock_cpu.return_value = 30.0
    mock_disk.return_value = MagicMock(percent=60.0)
    
    result = await health_checker.readiness_check()
    
    assert result.status == "ready"
    assert result.details["memory_usage_percent"] == 50.0
    assert result.details["cpu_usage_percent"] == 30.0
    assert result.details["disk_usage_percent"] == 60.0

@pytest.mark.asyncio
@patch('psutil.virtual_memory')
@patch('psutil.cpu_percent')
@patch('psutil.disk_usage')
async def test_readiness_check_unhealthy(mock_disk, mock_cpu, mock_memory, health_checker):
    """Test readiness check when system resources are exhausted"""
    # Mock unhealthy system resources
    mock_memory.return_value = MagicMock(percent=95.0)
    mock_cpu.return_value = 98.0
    mock_disk.return_value = MagicMock(percent=97.0)
    
    result = await health_checker.readiness_check()
    
    assert result.status == "not_ready"

@pytest.mark.asyncio
@patch('psutil.virtual_memory')
async def test_deep_health_check(mock_memory, health_checker):
    """Test deep health check"""
    # Mock memory info
    mock_memory_info = MagicMock()
    mock_memory_info.total = 8 * (1024**3)  # 8GB
    mock_memory_info.available = 4 * (1024**3)  # 4GB available
    mock_memory_info.percent = 50.0
    mock_memory.return_value = mock_memory_info
    
    result = await health_checker.deep_health_check()
    
    assert result.status == "healthy"
    assert "memory" in result.details
    assert result.details["memory"]["total_gb"] == 8.0
    assert result.details["memory"]["available_gb"] == 4.0
    assert result.details["memory"]["used_percent"] == 50.0

@pytest.mark.asyncio
async def test_metrics_collection(health_checker):
    """Test metrics collection"""
    result = await health_checker.metrics()
    
    assert "timestamp" in result
    assert result["service_name"] == "test-service"
    assert result["version"] == "1.0.0"
    assert "memory_usage_bytes" in result
    assert "cpu_usage_percent" in result