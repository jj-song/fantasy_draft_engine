# API Integration Guide - Fantasy Draft Engine

## Overview

This master guide explains how all third-party APIs work together in your Fantasy Draft Engine to create accurate, data-driven fantasy football projections. Understanding these integrations will help you maintain, extend, and optimize your system's performance.

**System Architecture:** Your engine combines NFL statistical data with environmental factors to generate comprehensive player projections that account for both performance history and game-day conditions.

## API Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Fantasy Draft Engine                         │
├─────────────────────────────────────────────────────────────┤
│  Data Acquisition Layer                                     │
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │   NFL Data API  │    │    OpenWeatherMap API           │ │
│  │  (nfl_data_py)  │    │   (weather_integration.py)     │ │
│  │                 │    │                                 │ │
│  │ • Player Stats  │    │ • Game Weather                  │ │
│  │ • Play-by-Play  │    │ • Environmental Factors         │ │
│  │ • Snap Counts   │    │ • Stadium Conditions            │ │
│  │ • Roster Data   │    │ • Historical Averages           │ │
│  └─────────────────┘    └─────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Feature Engineering Layer                                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • Statistical Features  • Environmental Adjustments    │ │
│  │ • Usage Metrics        • Weather Impact Factors        │ │
│  │ • Efficiency Ratios    • Stadium Effects              │ │
│  │ • Advanced Analytics   • Travel Adjustments           │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Machine Learning Layer                                     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • Position-Specific Models                              │ │
│  │ • Ensemble Predictions                                  │ │
│  │ • Environmental Adjustments                             │ │
│  │ • Confidence Intervals                                  │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Draft Optimization Layer                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • VOR Calculations   • Tier Assignments                │ │
│  │ • Draft Rankings     • Auction Values                  │ │
│  │ • Position Scarcity  • Strategy Recommendations        │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Primary API Integrations

### 1. NFL Data Python (nfl_data_py) - Core Statistical Engine

**Role:** Foundation data provider for all fantasy football analysis  
**Implementation:** `src/data_acquisition.py`  
**Data Flow:** Raw NFL statistics → Feature engineering → ML models → Projections

**Key Integration Points:**
- **Historical Analysis**: 15+ years of player performance data
- **Current Season**: Weekly updates during active season
- **Advanced Metrics**: EPA, air yards, target share calculations
- **Usage Analytics**: Snap counts and opportunity metrics

**Why This Integration is Critical:**
Without NFL data, there would be no fantasy football projections. This API provides the statistical foundation that feeds every other system component.

### 2. OpenWeatherMap API - Environmental Intelligence

**Role:** Game-day condition analysis and performance adjustments  
**Implementation:** `src/data/weather_integration.py`  
**Data Flow:** Weather forecasts → Impact calculations → Projection adjustments

**Key Integration Points:**
- **Weather Impact Models**: Position-specific performance multipliers
- **Stadium Intelligence**: Dome vs. outdoor game handling
- **Historical Fallbacks**: When live weather data is unavailable
- **Environmental Factors**: Temperature, wind, precipitation effects

**Why This Integration Matters:**
Weather can swing game outcomes by 20+ points. A QB facing 25mph winds should be projected significantly lower than the same QB in a dome, and your system accounts for this.

## Data Integration Flow

### Phase 1: Raw Data Acquisition

```python
# From src/data_acquisition.py
def fetch_player_season_stats(year, positions=None):
    # 1. Fetch core seasonal statistics
    seasonal_stats = nfl.import_seasonal_data([year])
    
    # 2. Enhance with weekly data for games played
    weekly_stats = nfl.import_weekly_data([year])
    
    # 3. Add advanced play-by-play metrics
    pbp_data = nfl.import_pbp_data([year])
    
    # 4. Include snap count data for usage analysis
    snap_data = nfl.import_snap_counts([year])
    
    # 5. Merge player biographical information
    player_info = nfl.import_players()
    
    # 6. Add team/roster context
    rosters = nfl.import_seasonal_rosters([year])
```

**Designer-Friendly Explanation:**
Think of this like building a comprehensive player database. We start with basic stats (touchdowns, yards), then add context (how many snaps they played), advanced metrics (how efficient they were), and finally personal information (age, experience). Each API call adds another layer of understanding about each player.

### Phase 2: Environmental Data Integration

```python
# From src/data/weather_integration.py
def get_game_environmental_factors(home_team, away_team, game_date):
    # 1. Identify stadium characteristics
    stadium_info = self.get_stadium_data(home_team)
    
    # 2. Fetch weather forecast (if outdoor stadium)
    if not stadium_info['is_dome']:
        weather = self.get_weather_forecast(city, state, game_date)
        
    # 3. Calculate position-specific impact factors
    weather_impacts = self.calculate_weather_impact(weather, position)
    
    # 4. Add altitude and travel adjustments
    altitude_factors = self.calculate_altitude_adjustment(altitude, position)
    travel_impacts = self.calculate_travel_impact(home_team, away_team)
```

**Why This Matters:**
Fantasy projections based purely on statistics ignore a huge factor: the environment where games are played. A kicker in Denver (high altitude) has different accuracy than one in Miami (sea level). Your system accounts for these nuances.

### Phase 3: Feature Engineering Integration

```python
# Multiple files combine API data into ML-ready features
def create_model_features(player_data, environmental_data):
    # Base statistical features
    statistical_features = calculate_base_stats(player_data)
    
    # Usage and opportunity metrics
    usage_features = calculate_usage_metrics(snap_data, target_data)
    
    # Efficiency calculations
    efficiency_features = calculate_efficiency_ratios(player_data)
    
    # Environmental adjustments
    adjusted_features = apply_environmental_factors(
        statistical_features, 
        environmental_data
    )
    
    return combined_feature_set
```

## Integration Error Handling

### NFL Data API Resilience

**Common Issues & Solutions:**

1. **Network Connectivity**
```python
try:
    seasonal_stats = nfl.import_seasonal_data([year])
except requests.exceptions.ConnectionError:
    logger.error("NFL API unavailable, using cached data")
    seasonal_stats = load_cached_data(year)
```

2. **Data Completeness**
```python
if seasonal_stats.empty:
    logger.warning(f"No data for {year}, checking alternative sources")
    # Fallback to previous year's data with adjustments
```

3. **Rate Limiting**
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_with_retry(year):
    return nfl.import_seasonal_data([year])
```

### Weather API Resilience

**Fallback Strategy:**

1. **Primary**: Live OpenWeatherMap API
2. **Secondary**: Historical weather averages by location/month
3. **Tertiary**: Assume neutral conditions

```python
def get_weather_with_fallbacks(city, state, game_date):
    try:
        return self.get_weather_forecast(city, state, game_date)
    except WeatherAPIException:
        logger.warning("Weather API failed, using historical averages")
        return self.get_historical_average(city, state, game_date.month)
    except Exception:
        logger.error("All weather sources failed, using neutral conditions")
        return self.get_neutral_weather_conditions()
```

## Performance Optimization Strategies

### Data Caching

**NFL Data Caching:**
```python
# Cache expensive API calls
@lru_cache(maxsize=128)
def get_seasonal_data(year):
    return nfl.import_seasonal_data([year])

# File-based caching for large datasets
def save_processed_data(data, year):
    cache_file = f"data/processed/player_season_{year}.parquet"
    data.to_parquet(cache_file)
```

**Weather Data Caching:**
```python
# Time-based caching
weather_cache = {}
cache_key = f"{city}_{state}_{game_date.strftime('%Y-%m-%d')}"
if cache_key in weather_cache:
    return weather_cache[cache_key]
```

### Memory Management

**Selective Data Loading:**
```python
# Only load necessary columns for large datasets
pbp_data = nfl.import_pbp_data([year], columns=[
    'receiver_player_name', 'air_yards', 'epa', 'cp'
])

# Use efficient data types
pbp_data = pbp_data.astype({
    'air_yards': 'float32',
    'epa': 'float32'
})
```

## Monitoring & Validation

### Data Quality Monitoring

**Statistical Validation:**
```python
def validate_nfl_data(data):
    # Check for reasonable ranges
    assert data['fantasy_points'].max() < 100, "Unrealistic fantasy points detected"
    assert data['games'].min() >= 0, "Negative games played"
    
    # Check for completeness
    missing_positions = set(['QB', 'RB', 'WR', 'TE']) - set(data['position'].unique())
    if missing_positions:
        logger.warning(f"Missing positions: {missing_positions}")
```

**Weather Data Validation:**
```python
def validate_weather_data(weather):
    if weather.temperature < -40 or weather.temperature > 130:
        logger.warning(f"Extreme temperature: {weather.temperature}°F")
    
    if weather.wind_speed > 60:
        logger.warning(f"Extreme wind speed: {weather.wind_speed} mph")
```

### Performance Monitoring

**API Response Time Tracking:**
```python
def monitor_api_performance():
    start_time = time.time()
    data = nfl.import_seasonal_data([2023])
    response_time = time.time() - start_time
    
    # Log performance metrics
    logger.info(f"NFL API response time: {response_time:.2f}s")
    if response_time > 30:
        logger.warning("NFL API response time degraded")
```

## Integration Testing

### End-to-End Validation

```python
def test_complete_integration():
    # Test NFL data pipeline
    seasonal_data = fetch_player_season_stats(2023)
    assert not seasonal_data.empty
    
    # Test weather integration
    weather_factors = get_game_environmental_factors('KC', 'BUF', datetime(2023, 12, 15))
    assert 'weather_impacts' in weather_factors
    
    # Test combined feature engineering
    features = create_model_features(seasonal_data, weather_factors)
    assert features.shape[1] > 50  # Sufficient feature count
    
    logger.info("✅ All API integrations validated successfully")
```

### Mock Testing for Development

```python
# Mock NFL API for testing
@patch('nfl_data_py.import_seasonal_data')
def test_with_mock_nfl_data(mock_import):
    mock_import.return_value = create_mock_seasonal_data()
    result = fetch_player_season_stats(2023)
    assert not result.empty

# Mock Weather API for testing
@patch('requests.get')
def test_with_mock_weather(mock_get):
    mock_get.return_value.json.return_value = create_mock_weather_response()
    weather = get_weather_forecast('Kansas City', 'MO', datetime.now())
    assert weather.temperature > 0
```

## Troubleshooting Common Integration Issues

### Issue 1: Player ID Mismatches Between APIs

**Problem:** NFL API uses different player identifiers than internal systems  
**Solution:** Multiple join strategies and name matching

```python
# Primary join on player_id
merged = pd.merge(seasonal_stats, player_info, on='player_id', how='left')

# Fallback to name matching for unmatched players
unmatched = merged[merged['player_name_y'].isna()]
if not unmatched.empty:
    # Fuzzy string matching for name variations
    matched_names = fuzzy_match_players(unmatched, player_info)
    merged = update_with_matched_names(merged, matched_names)
```

### Issue 2: Weather Data for Non-US Games

**Problem:** OpenWeatherMap API optimized for US locations  
**Solution:** International location handling

```python
def get_international_weather(city, country, game_date):
    if country == 'UK':
        return get_uk_weather_forecast(city, game_date)
    elif country == 'DE':
        return get_german_weather_forecast(city, game_date)
    else:
        return get_default_international_weather(city, country, game_date)
```

### Issue 3: Seasonal Data Timing

**Problem:** Current season data incomplete during active season  
**Solution:** Hybrid historical/current season modeling

```python
def handle_incomplete_season(current_year):
    current_data = nfl.import_seasonal_data([current_year])
    
    if current_data['games'].max() < 10:  # Season not complete
        logger.info("Season incomplete, using hybrid approach")
        # Use previous year's full data + current year partial data
        previous_data = nfl.import_seasonal_data([current_year - 1])
        return combine_seasonal_data(previous_data, current_data)
    
    return current_data
```

## Future Integration Opportunities

### Potential API Additions

1. **Vegas Betting Lines**
   - Game totals for scoring environment
   - Player props for market validation
   - Line movements for injury/weather impact

2. **Next Gen Stats**
   - Player tracking data
   - Route running efficiency
   - Speed and acceleration metrics

3. **Injury Reports**
   - Official team injury reports
   - Historical injury impact data
   - Recovery timeline predictions

4. **Social Media Sentiment**
   - Player news and updates
   - Trade rumors and impact
   - Coaching change analysis

### Integration Architecture for New APIs

```python
class APIIntegrationFramework:
    def __init__(self):
        self.registered_apis = {}
        self.data_validators = {}
        self.fallback_strategies = {}
    
    def register_api(self, name, api_client, validator, fallback):
        self.registered_apis[name] = api_client
        self.data_validators[name] = validator
        self.fallback_strategies[name] = fallback
    
    def fetch_with_validation(self, api_name, *args, **kwargs):
        try:
            data = self.registered_apis[api_name].fetch(*args, **kwargs)
            if self.data_validators[api_name](data):
                return data
            else:
                raise ValidationError(f"Data validation failed for {api_name}")
        except Exception as e:
            logger.warning(f"API {api_name} failed: {e}")
            return self.fallback_strategies[api_name](*args, **kwargs)
```

## Best Practices Summary

### Development Guidelines

1. **Always Implement Fallbacks**: Never let a single API failure break your system
2. **Cache Aggressively**: API calls are expensive, cached data is fast
3. **Validate Everything**: Bad data is worse than no data
4. **Monitor Performance**: Track API response times and error rates
5. **Plan for Scale**: Consider rate limits and bulk operations

### Designer-Friendly Integration Tips

1. **Start Simple**: Begin with basic API integration, add complexity gradually
2. **Test Thoroughly**: Use mock data to test edge cases
3. **Document Changes**: Keep API documentation updated as integrations evolve
4. **Monitor Regularly**: Set up alerts for API failures and performance degradation
5. **Plan Ahead**: Consider seasonal patterns and off-season data availability

Your Fantasy Draft Engine's API integration strategy provides a robust foundation for accurate, comprehensive fantasy football analysis. The combination of statistical depth from NFL data and environmental insight from weather data creates projections that account for the full complexity of football performance.