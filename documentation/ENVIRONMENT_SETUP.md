# Environment Setup & API Configuration Guide

## Overview

This guide walks you through setting up all required API keys and environment configurations for your Fantasy Draft Engine. Proper API setup is essential for your system to fetch NFL data and weather information needed for accurate fantasy projections.

**What You'll Accomplish:**
- Set up NFL data access (no API key required)
- Configure OpenWeatherMap API for weather data
- Establish secure environment variable management
- Validate your API integrations
- Set up monitoring and error handling

## Prerequisites

Before starting, ensure you have:
- Python 3.8+ installed
- Your Fantasy Draft Engine codebase cloned/downloaded
- Internet connection for API access
- Basic understanding of environment variables

## API Requirements Overview

### 1. NFL Data Python (nfl_data_py)
- **API Key Required**: ❌ No
- **Cost**: 🆓 Free
- **Setup Complexity**: 🟢 Simple
- **Rate Limits**: None specified
- **Data Access**: Historical and current NFL statistics

### 2. OpenWeatherMap API
- **API Key Required**: ✅ Yes
- **Cost**: 🆓 Free tier available (1,000 calls/day)
- **Setup Complexity**: 🟡 Moderate
- **Rate Limits**: 60 calls/minute (free tier)
- **Data Access**: Weather forecasts and historical data

## Step 1: NFL Data Python Setup

### Installation

NFL Data Python is already included in your `requirements.txt`:

```bash
# Install via pip (already handled by requirements.txt)
pip install nfl_data_py>=0.3.0,<0.5.0
```

### Verification

Test that NFL data access is working:

```python
import nfl_data_py as nfl

# Test basic functionality
try:
    # Fetch a small sample of recent data
    test_data = nfl.import_seasonal_data([2023])
    print(f"✅ NFL Data Python working! Loaded {len(test_data)} player records")
except Exception as e:
    print(f"❌ NFL Data Python failed: {e}")
```

### No Configuration Needed

NFL Data Python requires no API keys or special configuration. It fetches data directly from public nflverse repositories. Your system is ready to use this API immediately after installation.

## Step 2: OpenWeatherMap API Setup

### Account Creation

1. **Visit OpenWeatherMap**: Go to https://openweathermap.org/api
2. **Sign Up**: Create a free account
3. **Verify Email**: Check your email and verify your account
4. **Access Dashboard**: Log in to your account dashboard

### API Key Generation

1. **Navigate to API Keys**: In dashboard, click "API keys" tab
2. **Generate Key**: Click "Generate" or use the default key provided
3. **Copy Key**: Save your API key securely (looks like: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`)
4. **Activation Wait**: New keys may take up to 2 hours to activate

### Free Tier Limitations

**What's Included:**
- 1,000 API calls per day
- 60 calls per minute
- Current weather data
- 5-day/3-hour forecast
- Basic weather parameters

**What Requires Paid Plan:**
- Historical weather data (1+ days old)
- Higher rate limits
- Advanced weather parameters
- Professional support

### Environment Variable Configuration

#### Method 1: .env File (Recommended for Development)

Create a `.env` file in your project root:

```bash
# Create .env file
touch .env

# Add to .env file (replace with your actual API key)
WEATHER_API_KEY=your_actual_api_key_here
```

**Important**: Add `.env` to your `.gitignore` to prevent committing API keys:

```bash
# Add to .gitignore
echo ".env" >> .gitignore
```

#### Method 2: System Environment Variables

**On macOS/Linux:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export WEATHER_API_KEY="your_actual_api_key_here"

# Reload your shell
source ~/.bashrc  # or source ~/.zshrc
```

**On Windows:**
```cmd
# Command Prompt
setx WEATHER_API_KEY "your_actual_api_key_here"

# PowerShell
$env:WEATHER_API_KEY = "your_actual_api_key_here"
```

#### Method 3: Python-dotenv Integration

Your project can use python-dotenv to load environment variables:

```python
# Install python-dotenv
pip install python-dotenv

# Add to your Python code
from dotenv import load_dotenv
import os

load_dotenv()  # Load .env file
api_key = os.getenv('WEATHER_API_KEY')
```

## Step 3: Validate Your API Setup

### Complete Integration Test

Run this test script to validate both APIs:

```python
#!/usr/bin/env python3
"""
API Integration Validation Script
Run this to verify all APIs are working correctly.
"""

import os
import sys
from datetime import datetime
import nfl_data_py as nfl
import requests

def test_nfl_data_py():
    """Test NFL Data Python integration."""
    print("🏈 Testing NFL Data Python...")
    
    try:
        # Test seasonal data
        seasonal_data = nfl.import_seasonal_data([2023])
        print(f"✅ Seasonal data: {len(seasonal_data)} player records")
        
        # Test weekly data
        weekly_data = nfl.import_weekly_data([2023])
        print(f"✅ Weekly data: {len(weekly_data)} game records")
        
        # Test player info
        players = nfl.import_players()
        print(f"✅ Player info: {len(players)} players")
        
        return True
        
    except Exception as e:
        print(f"❌ NFL Data Python failed: {e}")
        return False

def test_openweathermap_api():
    """Test OpenWeatherMap API integration."""
    print("\n🌤️  Testing OpenWeatherMap API...")
    
    api_key = os.getenv('WEATHER_API_KEY')
    
    if not api_key:
        print("❌ WEATHER_API_KEY environment variable not set")
        print("   Please set your OpenWeatherMap API key:")
        print("   export WEATHER_API_KEY='your_api_key_here'")
        return False
    
    try:
        # Test current weather API
        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': 'Kansas City,MO,US',
            'appid': api_key,
            'units': 'imperial'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 401:
            print("❌ API key is invalid or not activated")
            print("   Check your API key and wait up to 2 hours for activation")
            return False
        elif response.status_code == 429:
            print("❌ Rate limit exceeded")
            print("   Wait a few minutes and try again")
            return False
        elif response.status_code != 200:
            print(f"❌ API error: {response.status_code} - {response.text}")
            return False
        
        data = response.json()
        temp = data['main']['temp']
        conditions = data['weather'][0]['description']
        
        print(f"✅ Current weather for Kansas City: {temp}°F, {conditions}")
        
        # Test forecast API
        forecast_url = "http://api.openweathermap.org/data/2.5/forecast"
        forecast_params = {
            'q': 'Kansas City,MO,US',
            'appid': api_key,
            'units': 'imperial',
            'cnt': 8  # 24 hours of forecasts
        }
        
        forecast_response = requests.get(forecast_url, params=forecast_params, timeout=10)
        
        if forecast_response.status_code == 200:
            forecast_data = forecast_response.json()
            forecast_count = forecast_data['cnt']
            print(f"✅ 5-day forecast: {forecast_count} data points retrieved")
        else:
            print(f"⚠️  Forecast API warning: {forecast_response.status_code}")
        
        return True
        
    except requests.exceptions.Timeout:
        print("❌ API request timed out - check your internet connection")
        return False
    except Exception as e:
        print(f"❌ OpenWeatherMap API failed: {e}")
        return False

def test_your_weather_integration():
    """Test your custom weather integration."""
    print("\n🏟️  Testing Your Weather Integration...")
    
    try:
        # Import your weather integration
        sys.path.append('src')
        from data.weather_integration import WeatherIntegrator
        
        integrator = WeatherIntegrator()
        
        # Test stadium data loading
        if integrator.stadium_data is not None and not integrator.stadium_data.empty:
            stadium_count = len(integrator.stadium_data)
            print(f"✅ Stadium data loaded: {stadium_count} stadiums")
        else:
            print("❌ Stadium data failed to load")
            return False
        
        # Test environmental factors (without weather API call)
        test_date = datetime(2024, 12, 15, 13, 0)
        factors = integrator.get_game_environmental_factors(
            'KC', 'BUF', test_date, get_weather=False
        )
        
        if factors:
            print("✅ Environmental factors calculation working")
            print(f"   Stadium: {factors['stadium_info']['name']}")
            print(f"   Dome: {factors['stadium_info']['is_dome']}")
            print(f"   Altitude: {factors['stadium_info']['altitude']} ft")
        else:
            print("❌ Environmental factors calculation failed")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ Could not import weather integration: {e}")
        return False
    except Exception as e:
        print(f"❌ Weather integration test failed: {e}")
        return False

def main():
    """Run all API validation tests."""
    print("🚀 Fantasy Draft Engine - API Validation")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    # Test NFL Data Python
    if test_nfl_data_py():
        tests_passed += 1
    
    # Test OpenWeatherMap API
    if test_openweathermap_api():
        tests_passed += 1
    
    # Test Your Weather Integration
    if test_your_weather_integration():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All APIs are working correctly!")
        print("Your Fantasy Draft Engine is ready to run.")
    else:
        print("⚠️  Some APIs need attention before proceeding.")
        print("Review the error messages above and fix any issues.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

### Running the Validation Script

Save the script as `validate_apis.py` and run:

```bash
python validate_apis.py
```

## Step 4: Configuration File Integration

### Update Your Configuration

Your project likely has configuration files that need API key references. Here's how to integrate them:

#### config.py Updates

```python
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_CONFIG = {
    'weather': {
        'api_key': os.getenv('WEATHER_API_KEY'),
        'base_url': 'http://api.openweathermap.org/data/2.5',
        'timeout': 10,
        'rate_limit': 60,  # calls per minute
        'retry_attempts': 3
    },
    'nfl_data': {
        'cache_enabled': True,
        'cache_duration': 3600,  # 1 hour
        'download_timeout': 30
    }
}

# Validation
def validate_api_config():
    """Validate API configuration on startup."""
    issues = []
    
    if not API_CONFIG['weather']['api_key']:
        issues.append("WEATHER_API_KEY environment variable not set")
    
    if issues:
        for issue in issues:
            print(f"⚠️  Configuration issue: {issue}")
        return False
    
    return True
```

#### Weather Integration Updates

Ensure your weather integration uses the environment variable:

```python
# In src/data/weather_integration.py
class WeatherIntegrator:
    def __init__(self, api_key: Optional[str] = None):
        # Use environment variable if no key provided
        self.api_key = api_key or os.getenv('WEATHER_API_KEY')
        
        if not self.api_key:
            logger.warning("No weather API key available - weather features disabled")
```

## Step 5: Security Best Practices

### API Key Security

1. **Never Commit API Keys**: Always use environment variables or secure vaults
2. **Rotate Keys Regularly**: Generate new API keys periodically
3. **Monitor Usage**: Watch for unexpected API usage spikes
4. **Restrict Access**: Use API key restrictions when available

### Environment Variable Security

```python
# Good: Use environment variables
api_key = os.getenv('WEATHER_API_KEY')

# Bad: Hardcode in source code
api_key = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"  # DON'T DO THIS!
```

### Production Deployment

For production environments:

1. **Use Secret Management**: AWS Secrets Manager, Azure Key Vault, etc.
2. **Environment Isolation**: Separate keys for dev/staging/production
3. **Access Logging**: Monitor who accesses API keys
4. **Backup Keys**: Keep backup API keys for emergency failover

## Step 6: Monitoring & Alerting

### API Usage Monitoring

```python
import logging
from datetime import datetime

# Set up API usage logging
api_logger = logging.getLogger('api_usage')
handler = logging.FileHandler('logs/api_usage.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
handler.setFormatter(formatter)
api_logger.addHandler(handler)

def log_api_call(api_name, endpoint, response_time, status_code):
    """Log API usage for monitoring."""
    api_logger.info(f"{api_name} | {endpoint} | {response_time:.2f}s | {status_code}")

# Usage in your API calls
start_time = time.time()
response = requests.get(url, params=params)
response_time = time.time() - start_time
log_api_call('OpenWeatherMap', 'forecast', response_time, response.status_code)
```

### Error Alerting

```python
def check_api_health():
    """Check API health and send alerts if needed."""
    errors = []
    
    # Check NFL data availability
    try:
        test_data = nfl.import_seasonal_data([2023])
        if test_data.empty:
            errors.append("NFL data returned empty dataset")
    except Exception as e:
        errors.append(f"NFL data API error: {e}")
    
    # Check weather API
    weather_key = os.getenv('WEATHER_API_KEY')
    if not weather_key:
        errors.append("Weather API key not configured")
    
    # Send alerts if errors found
    if errors:
        send_alert(f"API Health Issues: {'; '.join(errors)}")
    
    return len(errors) == 0
```

## Troubleshooting Common Issues

### Issue 1: "WEATHER_API_KEY not found"

**Cause**: Environment variable not set correctly  
**Solution**:
```bash
# Verify environment variable is set
echo $WEATHER_API_KEY

# If empty, set it:
export WEATHER_API_KEY="your_api_key_here"

# For permanent solution, add to ~/.bashrc or ~/.zshrc
```

### Issue 2: "OpenWeatherMap API returns 401 Unauthorized"

**Cause**: Invalid or inactive API key  
**Solution**:
1. Check API key is correct (no extra spaces/characters)
2. Wait up to 2 hours for new API keys to activate
3. Verify account is in good standing
4. Generate a new API key if needed

### Issue 3: "NFL data download very slow"

**Cause**: Large dataset downloads  
**Solution**:
```python
# Use selective column loading
data = nfl.import_pbp_data([2023], columns=['epa', 'receiver_player_name'])

# Enable memory optimization
data = nfl.import_weekly_data([2023], downcast=True)

# Cache data locally
data.to_parquet('cache/weekly_2023.parquet')
```

### Issue 4: "Weather API rate limit exceeded"

**Cause**: Too many API calls in short time  
**Solution**:
```python
import time
from functools import wraps

def rate_limit(calls_per_minute=60):
    """Rate limiting decorator."""
    def decorator(func):
        last_called = [0.0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = 60.0 / calls_per_minute - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator

@rate_limit(calls_per_minute=50)  # Stay under 60/minute limit
def get_weather_with_rate_limit(city, state, date):
    return get_weather_forecast(city, state, date)
```

## Next Steps

After completing this setup:

1. **Run Your Pipeline**: Test the complete data acquisition pipeline
2. **Validate Projections**: Ensure weather adjustments are working
3. **Monitor Performance**: Watch API response times and error rates  
4. **Scale Gradually**: Start with small data sets, expand as needed
5. **Document Changes**: Keep this guide updated as you modify integrations

Your Fantasy Draft Engine is now properly configured with secure, monitored API access. The combination of NFL statistical data and weather intelligence provides a comprehensive foundation for accurate fantasy football projections.

## Quick Reference

### Essential Commands

```bash
# Test API setup
python validate_apis.py

# Check environment variables
echo $WEATHER_API_KEY

# View API usage logs
tail -f logs/api_usage.log

# Run full data pipeline
python src/data_acquisition.py
```

### Emergency Contacts

- **OpenWeatherMap Support**: https://openweathermap.org/faq
- **NFL Data Python Issues**: https://github.com/nflverse/nfl_data_py/issues
- **Project Documentation**: /documentation/ folder

Your APIs are now ready to power your Fantasy Draft Engine!