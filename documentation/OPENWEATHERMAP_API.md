# OpenWeatherMap API Documentation

## Overview

The OpenWeatherMap API provides weather and environmental data that significantly impacts fantasy football performance. Your Fantasy Draft Engine integrates this API through the `weather_integration.py` module to account for weather conditions that affect player performance and game outcomes.

**Why Weather Matters for Fantasy Football:**
- **Passing Efficiency**: Wind >15mph reduces QB/WR/TE performance by 10-25%
- **Kicking Accuracy**: Wind and precipitation affect field goal success rates
- **Game Flow**: Cold weather and precipitation favor rushing over passing
- **Player Safety**: Extreme conditions increase fumble rates and affect grip
- **Scoring Totals**: Weather directly correlates with under/over performance

## API Configuration

### Base URLs
- **Current Weather**: `http://api.openweathermap.org/data/2.5/weather`
- **5-Day Forecast**: `http://api.openweathermap.org/data/2.5/forecast`
- **Historical Data**: `https://history.openweathermap.org/data/2.5/history/city`

### Authentication
All API calls require an API key via the `appid` parameter:
```
appid=[{API key}]
```

**API Key Setup:**
1. Sign up at https://openweathermap.org/api
2. Generate API key from account dashboard
3. Set environment variable: `WEATHER_API_KEY=your_api_key_here`

## Core API Endpoints Used in Your System

### 1. 5-Day Weather Forecast

**Primary Endpoint:**
```
GET http://api.openweathermap.org/data/2.5/forecast
```

**Parameters:**
- `q` (string): City name, state code, country code (e.g., "Kansas City,MO,US")
- `lat`/`lon` (float): Geographical coordinates (preferred method)
- `appid` (string): Required. Your unique API key
- `units` (string): Optional. 'imperial' (Fahrenheit), 'metric' (Celsius), 'standard' (Kelvin)
- `cnt` (int): Optional. Number of timestamps in response (up to 40)

**Example Request:**
```python
# From your weather_integration.py:186-192
base_url = "http://api.openweathermap.org/data/2.5/forecast"
params = {
    'q': f"{city},{state},US",
    'appid': self.api_key,
    'units': 'imperial',  # Fahrenheit
    'cnt': 40  # 5-day forecast, 3-hour intervals
}
```

### 2. Response Structure

**JSON Response Format:**
```json
{
  "cod": "200",
  "message": 0,
  "cnt": 40,
  "list": [
    {
      "dt": 1647345600,
      "main": {
        "temp": 45.5,
        "feels_like": 41.2,
        "pressure": 1015,
        "humidity": 65
      },
      "weather": [
        {
          "id": 500,
          "main": "Rain",
          "description": "light rain",
          "icon": "10d"
        }
      ],
      "wind": {
        "speed": 15.2,
        "deg": 180,
        "gust": 22.1
      },
      "rain": {
        "3h": 0.25
      },
      "dt_txt": "2022-03-15 12:00:00"
    }
  ],
  "city": {
    "name": "Kansas City",
    "country": "US",
    "timezone": -21600
  }
}
```

**Key Fields for Fantasy Impact:**
- `main.temp`: Temperature in specified units
- `wind.speed`: Wind speed (mph for imperial units)
- `wind.deg`: Wind direction in degrees
- `rain.3h`: Precipitation volume (mm) in last 3 hours
- `snow.3h`: Snow volume (mm) in last 3 hours
- `main.humidity`: Humidity percentage
- `weather[0].description`: Readable weather conditions

## Integration in Your Weather System

### WeatherConditions Data Class

Your system converts API responses into structured data:

```python
@dataclass
class WeatherConditions:
    temperature: float      # Fahrenheit
    wind_speed: float      # mph
    wind_direction: str    # N, NE, E, SE, S, SW, W, NW
    precipitation: float   # inches
    humidity: float        # percentage
    pressure: float        # inHg
    visibility: float      # miles
    conditions: str        # description
```

### API Response Processing

```python
# From weather_integration.py:214-223
weather = WeatherConditions(
    temperature=closest_forecast['main']['temp'],
    wind_speed=closest_forecast.get('wind', {}).get('speed', 0) * 2.237,  # m/s to mph
    wind_direction=self._degrees_to_direction(closest_forecast.get('wind', {}).get('deg', 0)),
    precipitation=closest_forecast.get('rain', {}).get('3h', 0) + closest_forecast.get('snow', {}).get('3h', 0),
    humidity=closest_forecast['main']['humidity'],
    pressure=closest_forecast['main']['pressure'] * 0.02953,  # hPa to inHg
    visibility=closest_forecast.get('visibility', 10000) / 1609.34,  # meters to miles
    conditions=closest_forecast['weather'][0]['description']
)
```

## Weather Impact Calculations

### Position-Specific Impact Factors

Your system calculates weather impact multipliers for each position:

**Wind Impact:**
- Wind >15 mph: -15% passing efficiency, -10% kicking accuracy
- Wind >25 mph: -25% passing efficiency, -20% kicking accuracy

**Precipitation Impact:**
- Rain/Snow: -10% passing, +5% rushing attempts, +30% fumble risk

**Temperature Impact:**
- <32°F: -5% overall scoring, -10% kicking accuracy
- <20°F: -10% overall, -10% passing, -15% kicking

```python
# From weather_integration.py:354-375
if weather.wind_speed > 15:
    impacts['passing_impact'] *= 0.85  # -15% passing
    impacts['kicking_impact'] *= 0.90  # -10% kicking

if weather.precipitation > 0.1:
    impacts['passing_impact'] *= 0.90  # -10% passing
    impacts['rushing_impact'] *= 1.05  # +5% rushing
    impacts['fumble_risk'] *= 1.3     # +30% fumble risk

if weather.temperature < 32:
    impacts['overall_impact'] *= 0.95  # -5% overall scoring
    impacts['kicking_impact'] *= 0.90  # -10% kicking accuracy
```

## Stadium Integration

### Dome vs. Outdoor Games

Your system automatically accounts for stadium types:

```python
# Dome games are not affected by weather
if is_dome:
    return {
        'overall_impact': 1.0,
        'passing_impact': 1.0,
        'rushing_impact': 1.0,
        'kicking_impact': 1.0,
        'fumble_risk': 1.0
    }
```

**NFL Stadiums by Type (2024):**
- **Domed Stadiums**: 10 teams (weather-independent)
- **Retractable Roof**: 7 teams (situational weather impact)
- **Outdoor Stadiums**: 15 teams (full weather impact)

### Stadium Data Integration

```python
# From weather_integration.py:87-120
stadiums = [
    StadiumInfo("Arrowhead Stadium", "KC", "Kansas City", "MO", False, False, 909, "grass", "CST", 76416),
    StadiumInfo("Lambeau Field", "GB", "Green Bay", "WI", False, False, 640, "grass", "CST", 81441),
    StadiumInfo("Soldier Field", "CHI", "Chicago", "IL", False, False, 597, "grass", "CST", 61500),
    # ... additional stadium data
]
```

## Error Handling & Fallback Systems

### API Failure Handling

When the OpenWeatherMap API is unavailable, your system falls back to historical averages:

```python
# From weather_integration.py:173-175
if not self.api_key:
    logger.warning("❌ No weather API key available. Using historical averages.")
    return self._get_historical_weather_average(city, state, game_date)
```

### Historical Weather Averages

```python
# Regional weather patterns by month
if state in ['FL', 'CA', 'AZ', 'TX', 'LA']:  # Warm weather states
    base_temp = 75 - (abs(month - 7) * 3)  # Peak in July
    wind_speed = 8
    precipitation = 0.1 if month in [6, 7, 8, 9] else 0.0
elif state in ['WI', 'MN', 'NY', 'MA', 'PA', 'OH', 'MI']:  # Cold weather states
    base_temp = 45 - (abs(month - 7) * 8)  # Much colder
    wind_speed = 12
    precipitation = 0.0
```

## Rate Limiting & Best Practices

### API Usage Guidelines

**Free Tier Limits:**
- 60 calls per minute
- 1,000 calls per day
- Current weather data only

**Paid Tier Benefits:**
- Higher rate limits
- Historical data access
- 5-day forecasts
- Professional support

### Optimization Strategies

```python
# Cache weather data to minimize API calls
cache_key = f"{city}_{state}_{game_date.strftime('%Y-%m-%d')}"
if use_cache and cache_key in self.weather_cache:
    return self.weather_cache[cache_key]
```

**Best Practices:**
1. **Cache Results**: Store weather data for repeated access
2. **Batch Requests**: Group multiple game forecasts when possible
3. **Error Handling**: Always have fallback data available
4. **Time Matching**: Find closest forecast to actual game time

## Common Issues & Solutions

### 1. API Key Authentication Errors

**Error 401 - Unauthorized:**
```json
{
  "cod": 401,
  "message": "Invalid API key. Please see http://openweathermap.org/faq#error401 for more info."
}
```

**Solutions:**
- Verify API key is correctly set in environment variables
- Check if API key has necessary permissions
- Ensure API key is not expired

### 2. Rate Limit Exceeded

**Error 429 - Too Many Requests:**
- Implement exponential backoff
- Use caching to reduce API calls
- Consider upgrading API plan

### 3. Location Not Found

**Error 404 - City Not Found:**
```python
# Use coordinates instead of city names for better accuracy
params = {
    'lat': 39.0458,
    'lon': -94.4845,  # Kansas City coordinates
    'appid': api_key
}
```

### 4. Network Connectivity Issues

**Timeout Handling:**
```python
try:
    response = requests.get(base_url, params=params, timeout=10)
    response.raise_for_status()
except requests.exceptions.Timeout:
    logger.error("Weather API request timed out")
    return self._get_historical_weather_average(city, state, game_date)
```

## Advanced Features

### Unit Conversions

Your system handles multiple unit systems:

```python
# Wind speed: m/s to mph
wind_speed_mph = wind_speed_ms * 2.237

# Pressure: hPa to inHg
pressure_inhg = pressure_hpa * 0.02953

# Visibility: meters to miles
visibility_miles = visibility_meters / 1609.34
```

### Wind Direction Conversion

```python
def _degrees_to_direction(self, degrees: float) -> str:
    directions = [
        'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
        'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'
    ]
    index = int((degrees + 11.25) / 22.5) % 16
    return directions[index]
```

### Time Zone Handling

```python
# Find forecast closest to game time
game_timestamp = int(game_date.timestamp())
for forecast in data['list']:
    forecast_timestamp = forecast['dt']
    time_diff = abs(game_timestamp - forecast_timestamp)
    # Select closest match
```

## Fantasy Football Applications

### Lineup Decisions

Weather impact helps with:
- **Start/Sit Decisions**: Downgrade players in severe weather
- **Streaming Options**: Target QBs in dome games
- **Kicker Selection**: Avoid kickers in windy conditions
- **Stack Strategies**: Favor ground games in bad weather

### DFS Optimization

- **GPP Leverage**: Fade popular players in bad weather
- **Cash Game Safety**: Stick to dome games for consistent scoring
- **Correlation Plays**: Stack RBs with their offensive lines in cold weather

### Season-Long Strategy

- **Playoff Considerations**: Account for December/January weather patterns
- **Handcuff Values**: Cold-weather teams' backup RBs gain value
- **Trade Timing**: Move outdoor players before winter months

## Monitoring & Validation

### Data Quality Checks

```python
# Validate weather data reasonableness
if weather.temperature < -20 or weather.temperature > 120:
    logger.warning(f"Extreme temperature detected: {weather.temperature}°F")

if weather.wind_speed > 50:
    logger.warning(f"Extreme wind speed detected: {weather.wind_speed} mph")
```

### Performance Monitoring

```python
# Track API response times
start_time = time.time()
weather_data = self.get_weather_forecast(city, state, game_date)
response_time = time.time() - start_time
logger.info(f"Weather API response time: {response_time:.2f}s")
```

## Future Enhancements

### Radar Integration
- **Real-time Updates**: Doppler radar for live precipitation tracking
- **Storm Tracking**: Movement patterns for game-time predictions

### Advanced Metrics
- **Heat Index**: Apparent temperature for player fatigue
- **UV Index**: Outdoor game conditions for player comfort
- **Air Quality**: Pollution levels affecting performance

### Machine Learning Integration
- **Weather Impact Models**: Position-specific performance adjustments
- **Historical Correlations**: Weather pattern impact on specific player types
- **Game Script Predictions**: How weather affects play-calling tendencies

This comprehensive weather integration gives your Fantasy Draft Engine a significant competitive advantage by accounting for environmental factors that many systems ignore. The detailed weather impact calculations help create more accurate projections and better draft recommendations.