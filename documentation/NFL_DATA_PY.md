# NFL Data Python (nfl_data_py) API Documentation

## Overview

NFL Data Python (`nfl_data_py`) is the primary data source for your Fantasy Draft Engine. This comprehensive library provides access to NFL player statistics, play-by-play data, roster information, and advanced metrics directly from the nflverse ecosystem.

**Why This API is Critical for Fantasy Football:**
- **Historical Data**: Access to player statistics from 1999 onwards
- **Comprehensive Coverage**: Seasonal stats, weekly data, play-by-play records
- **Fantasy-Relevant Metrics**: Snap counts, target share, red zone usage
- **Real-time Updates**: Current season data with regular updates
- **Advanced Analytics**: EPA, CPOE, air yards, and other modern metrics

## Installation & Setup

```bash
pip install nfl_data_py>=0.3.0,<0.5.0
```

```python
import nfl_data_py as nfl
```

## Core Functions Used in Your Codebase

### 1. `import_seasonal_data()` - Primary Player Statistics

**Function Signature:**
```python
nfl.import_seasonal_data(years, s_type='REG')
```

**Parameters:**
- `years` (List[int]): Required. List of NFL seasons (earliest 1999)
- `s_type` (str): Optional. Season type - 'REG' (regular), 'POST' (playoffs), 'ALL'

**Returns:** DataFrame with seasonal player statistics including:
- Passing stats: attempts, completions, yards, TDs, INTs
- Rushing stats: attempts, yards, TDs, fumbles
- Receiving stats: targets, receptions, yards, TDs
- Fantasy points (PPR and standard scoring)

**Usage in Your Project:**
```python
# From src/data_acquisition.py:52
seasonal_stats = nfl.import_seasonal_data([year])
```

**Why This Matters for Fantasy:** This is your foundation data - it contains the core statistics that drive fantasy point calculations and player projections.

### 2. `import_weekly_data()` - Game-by-Game Performance

**Function Signature:**
```python
nfl.import_weekly_data(years, columns=None, downcast=True)
```

**Parameters:**
- `years` (List[int]): Required. List of NFL seasons
- `columns` (List[str]): Optional. Specific columns to retrieve
- `downcast` (bool): Optional. Convert float64 to float32 (reduces memory ~30%)

**Returns:** DataFrame with weekly player performance data

**Usage in Your Project:**
```python
# From src/data_acquisition.py:56
weekly_stats = nfl.import_weekly_data([year])

# Aggregate to season totals
weekly_agg = weekly_stats.groupby('player_id').agg({
    'rushing_fumbles': 'sum',
    'receiving_yac_yards': 'sum',
    'week': 'count'  # Games played
}).reset_index()
```

**Why This Matters for Fantasy:** Weekly data allows you to calculate:
- Games played (availability/durability)
- Consistency metrics
- Performance trends
- Advanced receiving metrics

### 3. `import_pbp_data()` - Play-by-Play Analysis

**Function Signature:**
```python
nfl.import_pbp_data(years, columns=None, downcast=True, cache=False, alt_path=None)
```

**Parameters:**
- `years` (List[int]): Required. List of NFL seasons (earliest 1999)
- `columns` (List[str]): Optional. Specific columns to retrieve
- `downcast` (bool): Optional. Memory optimization
- `cache` (bool): Optional. Data caching control
- `alt_path` (str): Optional. Alternative cache path

**Returns:** DataFrame with every play from specified seasons

**Advanced Metrics Available:**
- `air_yards`: Distance ball traveled in air
- `yards_after_catch`: YAC for receptions
- `epa`: Expected Points Added per play
- `cp`: Completion Probability
- `receiver_player_name`: Target information

**Usage in Your Project:**
```python
# From src/data_acquisition.py:84-117
pbp_data = nfl.import_pbp_data([year])

# Calculate advanced receiving metrics
pbp_receiving = pbp_data[
    (pbp_data['play_type'] == 'pass') & 
    (pbp_data['receiver_player_name'].notna()) &
    (pbp_data['air_yards'].notna())
].copy()

pbp_agg = pbp_receiving.groupby('receiver_player_name').agg({
    'air_yards': ['mean', 'sum', 'count'],
    'yards_after_catch': ['mean', 'sum'],
    'epa': 'mean',
    'cp': 'mean',
    'play_id': 'count'
}).reset_index()
```

**Why This Matters for Fantasy:** Play-by-play data enables:
- Advanced receiver metrics (air yards, YAC efficiency)
- Target quality analysis
- Expected Points Added per target
- Red zone efficiency calculations

### 4. `import_snap_counts()` - Usage and Opportunity

**Function Signature:**
```python
nfl.import_snap_counts(years)
```

**Parameters:**
- `years` (List[int]): Optional. List of years to return data

**Returns:** DataFrame with weekly snap count data

**Usage in Your Project:**
```python
# From src/data_acquisition.py:131
snap_data = nfl.import_snap_counts([year])

# Aggregate by player for season totals
snap_agg = snap_data.groupby('player_name').agg({
    'offense_snaps': 'sum',
    'offense_pct': 'mean',
    'defense_snaps': 'sum', 
    'defense_pct': 'mean'
}).reset_index()
```

**Why This Matters for Fantasy:** Snap counts reveal:
- Player usage trends
- Opportunity share within team offense
- Injury impact on playing time
- Backup vs. starter roles

### 5. `import_players()` - Player Information

**Function Signature:**
```python
nfl.import_players()
```

**Returns:** DataFrame with player biographical data:
- `gsis_id`: Unique player identifier
- `first_name`, `last_name`: Player names
- `position`: Player position
- `birth_date`: Birth date (for age calculations)
- `college_name`: College attended
- `entry_year`: NFL entry year
- `draft_round`, `draft_number`: Draft information

**Usage in Your Project:**
```python
# From src/data_acquisition.py:161
player_info = nfl.import_players()

# Filter for fantasy-relevant positions
player_info = player_info[player_info['position'].isin(positions)]
```

### 6. `import_seasonal_rosters()` - Team Information

**Function Signature:**
```python
nfl.import_seasonal_rosters(years, columns=None)
```

**Parameters:**
- `years` (List[int]): Required. List of NFL seasons
- `columns` (List[str]): Optional. Specific columns to retrieve

**Returns:** DataFrame with yearly roster information including team assignments

**Usage in Your Project:**
```python
# From src/data_acquisition.py:165
rosters = nfl.import_seasonal_rosters([year])

# Merge for accurate team data
seasonal_stats = pd.merge(
    seasonal_stats,
    year_rosters[['player_id', 'team', 'position', 'depth_chart_position']],
    on='player_id',
    how='left'
)
```

## Advanced Usage Patterns in Your Codebase

### Data Integration Pipeline

Your `fetch_player_season_stats()` function demonstrates sophisticated API usage:

1. **Multi-source Integration**: Combines seasonal, weekly, play-by-play, and snap data
2. **Advanced Metrics Calculation**: Derives fantasy-relevant metrics from raw data
3. **Data Quality Enhancement**: Fills gaps with multiple data sources
4. **Memory Optimization**: Uses efficient data types and selective columns

### Error Handling Best Practices

```python
try:
    seasonal_stats = nfl.import_seasonal_data([year])
except Exception as e:
    logger.error(f"Error fetching data for {year} season: {str(e)}")
    raise
```

### Performance Optimization

```python
# Only fetch needed columns for large datasets
pbp_data = nfl.import_pbp_data([year], columns=[
    'play_type', 'receiver_player_name', 'air_yards', 
    'yards_after_catch', 'epa', 'cp', 'play_id'
])
```

## Data Quality Considerations

### Missing Data Handling
- **Rookie Players**: May have limited historical data
- **Position Changes**: Players switching positions mid-career
- **Team Changes**: Free agency and trades affecting team-based metrics
- **Injury Impact**: Games missed affecting sample sizes

### Data Validation
```python
# From your codebase - validate data completeness
if not seasonal_stats.empty:
    logger.info(f"Successfully fetched {len(seasonal_stats)} player records")
else:
    logger.warning(f"No seasonal stats found for {year}")
```

## Common Issues & Troubleshooting

### 1. Network Connectivity
**Error:** `requests.exceptions.ConnectionError`
**Solution:** Check internet connection and nflverse API status

### 2. Memory Issues with Large Datasets
**Error:** `MemoryError` when loading multiple years
**Solution:** Use `downcast=True` and selective column loading

### 3. Data Availability Timing
**Issue:** Current season data may be incomplete during active season
**Solution:** Implement retry logic and data freshness checks

### 4. Player ID Mismatches
**Issue:** Different ID systems across data sources
**Solution:** Use multiple join strategies (player_name, gsis_id)

## Rate Limiting & Best Practices

### API Behavior
- **No explicit rate limits** but be respectful of server resources
- **Bulk downloads preferred** over repeated small requests
- **Cache data locally** to minimize repeated API calls

### Optimization Strategies
```python
# Batch years together rather than individual calls
seasonal_data = nfl.import_seasonal_data([2020, 2021, 2022, 2023])

# Use selective column loading for large datasets
pbp_subset = nfl.import_pbp_data([2023], columns=['epa', 'receiver_player_name'])
```

## Integration with Your Fantasy System

### Fantasy Point Calculations
The library provides pre-calculated fantasy points, but your system customizes:
- **Scoring Systems**: 0.5 PPR vs full PPR vs standard
- **Position Eligibility**: Flexible position assignments
- **Custom Metrics**: VOR calculations, tier assignments

### Model Training Data
nfl_data_py provides the foundation for your ML models:
- **Features**: Statistical performance, usage metrics, efficiency ratios
- **Targets**: Fantasy points in various scoring formats
- **Time Series**: Historical performance for trend analysis

### Draft Rankings Generation
API data flows through your pipeline:
1. **Raw Data**: nfl_data_py imports
2. **Feature Engineering**: Advanced metric calculations
3. **Model Predictions**: ML-based projections
4. **Value Calculations**: VOR and tier assignments
5. **Final Rankings**: Draft-ready player lists

## Monitoring & Maintenance

### Data Freshness Checks
```python
# Monitor when data was last updated
latest_week = weekly_data['week'].max()
logger.info(f"Latest week available: {latest_week}")
```

### Performance Monitoring
```python
import time
start_time = time.time()
seasonal_data = nfl.import_seasonal_data([2023])
load_time = time.time() - start_time
logger.info(f"Data load completed in {load_time:.2f} seconds")
```

## Related Resources

- **Official Repository**: https://github.com/nflverse/nfl_data_py
- **PyPI Package**: https://pypi.org/project/nfl-data-py/
- **nflverse Ecosystem**: https://nflreadr.nflverse.com/
- **Data Dictionary**: Comprehensive field definitions available in repository

## Future Considerations

### Potential Enhancements
- **Real-time Data**: Integration with live game feeds
- **Injury Reports**: Enhanced player availability data
- **Weather Integration**: Game-day environmental factors
- **Vegas Lines**: Betting market intelligence
- **Advanced Metrics**: Next Gen Stats integration

### Version Management
- **Pin Versions**: Use specific version ranges to avoid breaking changes
- **Test Updates**: Validate data schema consistency with new releases
- **Deprecation Monitoring**: Watch for API changes and deprecations

This documentation serves as your comprehensive guide to maximizing the value of nfl_data_py in your Fantasy Draft Engine. The library's rich dataset combined with your sophisticated processing pipeline enables industry-leading fantasy football analysis and projections.