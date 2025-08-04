"""
NFL Stadium Data and Venue Analytics

This module provides comprehensive stadium information and venue-based analytics
for fantasy football projections. It includes:

- Complete stadium database with characteristics
- Historical venue scoring environments
- Field surface impact analysis
- Stadium-specific weather patterns
- Altitude and environmental factors

Venue characteristics that impact fantasy performance:
- Dome vs outdoor affects weather dependency
- Altitude impacts kicking range and passing distance  
- Field surface affects injury rates and speed
- Stadium acoustics affect opposing offense
- Historical scoring environments show venue tendencies
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))
import config

logger = logging.getLogger(__name__)


class StadiumDatabase:
    """Complete NFL stadium database and venue analytics."""
    
    def __init__(self):
        """Initialize the stadium database."""
        self.stadium_data = None
        self.venue_scoring_history = None
        self.load_stadium_database()
    
    def load_stadium_database(self) -> pd.DataFrame:
        """Load complete NFL stadium database."""
        
        # Comprehensive stadium data for 2024 season
        stadium_records = [
            {
                'team': 'ARI', 'stadium_name': 'State Farm Stadium', 'city': 'Glendale', 'state': 'AZ',
                'opened': 2006, 'capacity': 63400, 'is_dome': True, 'has_retractable_roof': True,
                'altitude': 1086, 'field_surface': 'grass', 'time_zone': 'MST', 'conference': 'NFC',
                'division': 'West', 'latitude': 33.5276, 'longitude': -112.2626,
                'avg_temperature_sept': 95, 'avg_temperature_oct': 84, 'avg_temperature_nov': 72,
                'avg_temperature_dec': 61, 'avg_temperature_jan': 58, 'avg_wind_speed': 6.2,
                'historical_scoring_environment': 'High', 'noise_factor': 'Average'
            },
            {
                'team': 'ATL', 'stadium_name': 'Mercedes-Benz Stadium', 'city': 'Atlanta', 'state': 'GA',
                'opened': 2017, 'capacity': 71000, 'is_dome': True, 'has_retractable_roof': True,
                'altitude': 1050, 'field_surface': 'turf', 'time_zone': 'EST', 'conference': 'NFC',
                'division': 'South', 'latitude': 33.7553, 'longitude': -84.4006,
                'avg_temperature_sept': 79, 'avg_temperature_oct': 69, 'avg_temperature_nov': 59,
                'avg_temperature_dec': 49, 'avg_temperature_jan': 44, 'avg_wind_speed': 0,  # Dome
                'historical_scoring_environment': 'High', 'noise_factor': 'High'
            },
            {
                'team': 'BAL', 'stadium_name': 'M&T Bank Stadium', 'city': 'Baltimore', 'state': 'MD',
                'opened': 1998, 'capacity': 71008, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 54, 'field_surface': 'grass', 'time_zone': 'EST', 'conference': 'AFC',
                'division': 'North', 'latitude': 39.2780, 'longitude': -76.6227,
                'avg_temperature_sept': 75, 'avg_temperature_oct': 64, 'avg_temperature_nov': 53,
                'avg_temperature_dec': 42, 'avg_temperature_jan': 35, 'avg_wind_speed': 9.1,
                'historical_scoring_environment': 'Average', 'noise_factor': 'High'
            },
            {
                'team': 'BUF', 'stadium_name': 'Highmark Stadium', 'city': 'Orchard Park', 'state': 'NY',
                'opened': 1973, 'capacity': 71608, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 648, 'field_surface': 'turf', 'time_zone': 'EST', 'conference': 'AFC',
                'division': 'East', 'latitude': 42.7738, 'longitude': -78.7870,
                'avg_temperature_sept': 68, 'avg_temperature_oct': 57, 'avg_temperature_nov': 45,
                'avg_temperature_dec': 34, 'avg_temperature_jan': 25, 'avg_wind_speed': 11.8,
                'historical_scoring_environment': 'Low', 'noise_factor': 'Very High'
            },
            {
                'team': 'CAR', 'stadium_name': 'Bank of America Stadium', 'city': 'Charlotte', 'state': 'NC',
                'opened': 1996, 'capacity': 75523, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 750, 'field_surface': 'grass', 'time_zone': 'EST', 'conference': 'NFC',
                'division': 'South', 'latitude': 35.2258, 'longitude': -80.8528,
                'avg_temperature_sept': 77, 'avg_temperature_oct': 66, 'avg_temperature_nov': 56,
                'avg_temperature_dec': 46, 'avg_temperature_jan': 42, 'avg_wind_speed': 7.4,
                'historical_scoring_environment': 'Average', 'noise_factor': 'Average'
            },
            {
                'team': 'CHI', 'stadium_name': 'Soldier Field', 'city': 'Chicago', 'state': 'IL',
                'opened': 1924, 'capacity': 61500, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 597, 'field_surface': 'grass', 'time_zone': 'CST', 'conference': 'NFC',
                'division': 'North', 'latitude': 41.8623, 'longitude': -87.6167,
                'avg_temperature_sept': 70, 'avg_temperature_oct': 58, 'avg_temperature_nov': 45,
                'avg_temperature_dec': 32, 'avg_temperature_jan': 24, 'avg_wind_speed': 13.2,
                'historical_scoring_environment': 'Low', 'noise_factor': 'Average'
            },
            {
                'team': 'CIN', 'stadium_name': 'Paycor Stadium', 'city': 'Cincinnati', 'state': 'OH',
                'opened': 2000, 'capacity': 65515, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 550, 'field_surface': 'turf', 'time_zone': 'EST', 'conference': 'AFC',
                'division': 'North', 'latitude': 39.0955, 'longitude': -84.5160,
                'avg_temperature_sept': 73, 'avg_temperature_oct': 61, 'avg_temperature_nov': 49,
                'avg_temperature_dec': 37, 'avg_temperature_jan': 30, 'avg_wind_speed': 8.7,
                'historical_scoring_environment': 'Average', 'noise_factor': 'Average'
            },
            {
                'team': 'CLE', 'stadium_name': 'Cleveland Browns Stadium', 'city': 'Cleveland', 'state': 'OH',
                'opened': 1999, 'capacity': 67431, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 653, 'field_surface': 'grass', 'time_zone': 'EST', 'conference': 'AFC',
                'division': 'North', 'latitude': 41.5061, 'longitude': -81.6995,
                'avg_temperature_sept': 70, 'avg_temperature_oct': 58, 'avg_temperature_nov': 46,
                'avg_temperature_dec': 35, 'avg_temperature_jan': 27, 'avg_wind_speed': 10.9,
                'historical_scoring_environment': 'Low', 'noise_factor': 'High'
            },
            {
                'team': 'DAL', 'stadium_name': 'AT&T Stadium', 'city': 'Arlington', 'state': 'TX',
                'opened': 2009, 'capacity': 80000, 'is_dome': True, 'has_retractable_roof': True,
                'altitude': 551, 'field_surface': 'turf', 'time_zone': 'CST', 'conference': 'NFC',
                'division': 'East', 'latitude': 32.7473, 'longitude': -97.0945,
                'avg_temperature_sept': 83, 'avg_temperature_oct': 72, 'avg_temperature_nov': 61,
                'avg_temperature_dec': 50, 'avg_temperature_jan': 45, 'avg_wind_speed': 0,  # Dome
                'historical_scoring_environment': 'High', 'noise_factor': 'Average'
            },
            {
                'team': 'DEN', 'stadium_name': 'Empower Field at Mile High', 'city': 'Denver', 'state': 'CO',
                'opened': 2001, 'capacity': 76125, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 5280, 'field_surface': 'grass', 'time_zone': 'MST', 'conference': 'AFC',
                'division': 'West', 'latitude': 39.7439, 'longitude': -105.0201,
                'avg_temperature_sept': 72, 'avg_temperature_oct': 59, 'avg_temperature_nov': 44,
                'avg_temperature_dec': 32, 'avg_temperature_jan': 25, 'avg_wind_speed': 8.5,
                'historical_scoring_environment': 'High', 'noise_factor': 'Very High'
            },
            {
                'team': 'DET', 'stadium_name': 'Ford Field', 'city': 'Detroit', 'state': 'MI',
                'opened': 2002, 'capacity': 65000, 'is_dome': True, 'has_retractable_roof': False,
                'altitude': 585, 'field_surface': 'turf', 'time_zone': 'EST', 'conference': 'NFC',
                'division': 'North', 'latitude': 42.3400, 'longitude': -83.0456,
                'avg_temperature_sept': 69, 'avg_temperature_oct': 57, 'avg_temperature_nov': 45,
                'avg_temperature_dec': 34, 'avg_temperature_jan': 26, 'avg_wind_speed': 0,  # Dome
                'historical_scoring_environment': 'Average', 'noise_factor': 'High'
            },
            {
                'team': 'GB', 'stadium_name': 'Lambeau Field', 'city': 'Green Bay', 'state': 'WI',
                'opened': 1957, 'capacity': 81441, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 640, 'field_surface': 'grass', 'time_zone': 'CST', 'conference': 'NFC',
                'division': 'North', 'latitude': 44.5013, 'longitude': -88.0622,
                'avg_temperature_sept': 66, 'avg_temperature_oct': 54, 'avg_temperature_nov': 40,
                'avg_temperature_dec': 27, 'avg_temperature_jan': 18, 'avg_wind_speed': 10.2,
                'historical_scoring_environment': 'Low', 'noise_factor': 'Very High'
            },
            {
                'team': 'HOU', 'stadium_name': 'NRG Stadium', 'city': 'Houston', 'state': 'TX',
                'opened': 2002, 'capacity': 72220, 'is_dome': True, 'has_retractable_roof': True,
                'altitude': 40, 'field_surface': 'turf', 'time_zone': 'CST', 'conference': 'AFC',
                'division': 'South', 'latitude': 29.6847, 'longitude': -95.4107,
                'avg_temperature_sept': 87, 'avg_temperature_oct': 79, 'avg_temperature_nov': 69,
                'avg_temperature_dec': 59, 'avg_temperature_jan': 54, 'avg_wind_speed': 0,  # Dome
                'historical_scoring_environment': 'High', 'noise_factor': 'Average'
            },
            {
                'team': 'IND', 'stadium_name': 'Lucas Oil Stadium', 'city': 'Indianapolis', 'state': 'IN',
                'opened': 2008, 'capacity': 67000, 'is_dome': True, 'has_retractable_roof': True,
                'altitude': 715, 'field_surface': 'turf', 'time_zone': 'EST', 'conference': 'AFC',
                'division': 'South', 'latitude': 39.7601, 'longitude': -86.1639,
                'avg_temperature_sept': 72, 'avg_temperature_oct': 60, 'avg_temperature_nov': 48,
                'avg_temperature_dec': 36, 'avg_temperature_jan': 29, 'avg_wind_speed': 0,  # Dome
                'historical_scoring_environment': 'High', 'noise_factor': 'High'
            },
            {
                'team': 'JAX', 'stadium_name': 'TIAA Bank Field', 'city': 'Jacksonville', 'state': 'FL',
                'opened': 1995, 'capacity': 67428, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 10, 'field_surface': 'grass', 'time_zone': 'EST', 'conference': 'AFC',
                'division': 'South', 'latitude': 30.3240, 'longitude': -81.6373,
                'avg_temperature_sept': 84, 'avg_temperature_oct': 77, 'avg_temperature_nov': 68,
                'avg_temperature_dec': 59, 'avg_temperature_jan': 54, 'avg_wind_speed': 7.8,
                'historical_scoring_environment': 'Average', 'noise_factor': 'Average'
            },
            {
                'team': 'KC', 'stadium_name': 'Arrowhead Stadium', 'city': 'Kansas City', 'state': 'MO',
                'opened': 1972, 'capacity': 76416, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 909, 'field_surface': 'grass', 'time_zone': 'CST', 'conference': 'AFC',
                'division': 'West', 'latitude': 39.0489, 'longitude': -94.4839,
                'avg_temperature_sept': 76, 'avg_temperature_oct': 64, 'avg_temperature_nov': 50,
                'avg_temperature_dec': 37, 'avg_temperature_jan': 30, 'avg_wind_speed': 10.6,
                'historical_scoring_environment': 'High', 'noise_factor': 'Very High'
            },
            {
                'team': 'LV', 'stadium_name': 'Allegiant Stadium', 'city': 'Las Vegas', 'state': 'NV',
                'opened': 2020, 'capacity': 65000, 'is_dome': True, 'has_retractable_roof': False,
                'altitude': 2001, 'field_surface': 'grass', 'time_zone': 'PST', 'conference': 'AFC',
                'division': 'West', 'latitude': 36.0909, 'longitude': -115.1833,
                'avg_temperature_sept': 94, 'avg_temperature_oct': 81, 'avg_temperature_nov': 67,
                'avg_temperature_dec': 55, 'avg_temperature_jan': 49, 'avg_wind_speed': 0,  # Dome
                'historical_scoring_environment': 'High', 'noise_factor': 'High'
            },
            {
                'team': 'LAC', 'stadium_name': 'SoFi Stadium', 'city': 'Los Angeles', 'state': 'CA',
                'opened': 2020, 'capacity': 70240, 'is_dome': True, 'has_retractable_roof': False,
                'altitude': 86, 'field_surface': 'turf', 'time_zone': 'PST', 'conference': 'AFC',
                'division': 'West', 'latitude': 33.9535, 'longitude': -118.3392,
                'avg_temperature_sept': 79, 'avg_temperature_oct': 75, 'avg_temperature_nov': 69,
                'avg_temperature_dec': 62, 'avg_temperature_jan': 58, 'avg_wind_speed': 0,  # Dome
                'historical_scoring_environment': 'High', 'noise_factor': 'Average'
            },
            {
                'team': 'LAR', 'stadium_name': 'SoFi Stadium', 'city': 'Los Angeles', 'state': 'CA',
                'opened': 2020, 'capacity': 70240, 'is_dome': True, 'has_retractable_roof': False,
                'altitude': 86, 'field_surface': 'turf', 'time_zone': 'PST', 'conference': 'NFC',
                'division': 'West', 'latitude': 33.9535, 'longitude': -118.3392,
                'avg_temperature_sept': 79, 'avg_temperature_oct': 75, 'avg_temperature_nov': 69,
                'avg_temperature_dec': 62, 'avg_temperature_jan': 58, 'avg_wind_speed': 0,  # Dome
                'historical_scoring_environment': 'High', 'noise_factor': 'Average'
            },
            {
                'team': 'MIA', 'stadium_name': 'Hard Rock Stadium', 'city': 'Miami Gardens', 'state': 'FL',
                'opened': 1987, 'capacity': 65326, 'is_dome': False, 'has_retractable_roof': True,
                'altitude': 7, 'field_surface': 'grass', 'time_zone': 'EST', 'conference': 'AFC',
                'division': 'East', 'latitude': 25.9580, 'longitude': -80.2389,
                'avg_temperature_sept': 84, 'avg_temperature_oct': 80, 'avg_temperature_nov': 75,
                'avg_temperature_dec': 70, 'avg_temperature_jan': 66, 'avg_wind_speed': 9.2,
                'historical_scoring_environment': 'High', 'noise_factor': 'Average'
            },
            {
                'team': 'MIN', 'stadium_name': 'U.S. Bank Stadium', 'city': 'Minneapolis', 'state': 'MN',
                'opened': 2016, 'capacity': 66860, 'is_dome': True, 'has_retractable_roof': False,
                'altitude': 840, 'field_surface': 'turf', 'time_zone': 'CST', 'conference': 'NFC',
                'division': 'North', 'latitude': 44.9737, 'longitude': -93.2577,
                'avg_temperature_sept': 66, 'avg_temperature_oct': 53, 'avg_temperature_nov': 38,
                'avg_temperature_dec': 23, 'avg_temperature_jan': 13, 'avg_wind_speed': 0,  # Dome
                'historical_scoring_environment': 'High', 'noise_factor': 'Very High'
            },
            {
                'team': 'NE', 'stadium_name': 'Gillette Stadium', 'city': 'Foxborough', 'state': 'MA',
                'opened': 2002, 'capacity': 65878, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 95, 'field_surface': 'turf', 'time_zone': 'EST', 'conference': 'AFC',
                'division': 'East', 'latitude': 42.0909, 'longitude': -71.2643,
                'avg_temperature_sept': 69, 'avg_temperature_oct': 58, 'avg_temperature_nov': 47,
                'avg_temperature_dec': 36, 'avg_temperature_jan': 29, 'avg_wind_speed': 9.8,
                'historical_scoring_environment': 'Average', 'noise_factor': 'High'
            },
            {
                'team': 'NO', 'stadium_name': 'Caesars Superdome', 'city': 'New Orleans', 'state': 'LA',
                'opened': 1975, 'capacity': 73208, 'is_dome': True, 'has_retractable_roof': False,
                'altitude': 3, 'field_surface': 'turf', 'time_zone': 'CST', 'conference': 'NFC',
                'division': 'South', 'latitude': 29.9511, 'longitude': -90.0812,
                'avg_temperature_sept': 84, 'avg_temperature_oct': 76, 'avg_temperature_nov': 67,
                'avg_temperature_dec': 58, 'avg_temperature_jan': 52, 'avg_wind_speed': 0,  # Dome
                'historical_scoring_environment': 'High', 'noise_factor': 'Very High'
            },
            {
                'team': 'NYG', 'stadium_name': 'MetLife Stadium', 'city': 'East Rutherford', 'state': 'NJ',
                'opened': 2010, 'capacity': 82500, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 7, 'field_surface': 'turf', 'time_zone': 'EST', 'conference': 'NFC',
                'division': 'East', 'latitude': 40.8135, 'longitude': -74.0745,
                'avg_temperature_sept': 71, 'avg_temperature_oct': 60, 'avg_temperature_nov': 49,
                'avg_temperature_dec': 38, 'avg_temperature_jan': 31, 'avg_wind_speed': 10.3,
                'historical_scoring_environment': 'Average', 'noise_factor': 'Average'
            },
            {
                'team': 'NYJ', 'stadium_name': 'MetLife Stadium', 'city': 'East Rutherford', 'state': 'NJ',
                'opened': 2010, 'capacity': 82500, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 7, 'field_surface': 'turf', 'time_zone': 'EST', 'conference': 'AFC',
                'division': 'East', 'latitude': 40.8135, 'longitude': -74.0745,
                'avg_temperature_sept': 71, 'avg_temperature_oct': 60, 'avg_temperature_nov': 49,
                'avg_temperature_dec': 38, 'avg_temperature_jan': 31, 'avg_wind_speed': 10.3,
                'historical_scoring_environment': 'Average', 'noise_factor': 'Average'
            },
            {
                'team': 'PHI', 'stadium_name': 'Lincoln Financial Field', 'city': 'Philadelphia', 'state': 'PA',
                'opened': 2003, 'capacity': 69596, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 56, 'field_surface': 'grass', 'time_zone': 'EST', 'conference': 'NFC',
                'division': 'East', 'latitude': 39.9008, 'longitude': -75.1675,
                'avg_temperature_sept': 73, 'avg_temperature_oct': 62, 'avg_temperature_nov': 51,
                'avg_temperature_dec': 40, 'avg_temperature_jan': 33, 'avg_wind_speed': 9.5,
                'historical_scoring_environment': 'Average', 'noise_factor': 'Very High'
            },
            {
                'team': 'PIT', 'stadium_name': 'Acrisure Stadium', 'city': 'Pittsburgh', 'state': 'PA',
                'opened': 2001, 'capacity': 68400, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 1223, 'field_surface': 'grass', 'time_zone': 'EST', 'conference': 'AFC',
                'division': 'North', 'latitude': 40.4468, 'longitude': -80.0158,
                'avg_temperature_sept': 70, 'avg_temperature_oct': 58, 'avg_temperature_nov': 47,
                'avg_temperature_dec': 36, 'avg_temperature_jan': 28, 'avg_wind_speed': 8.9,
                'historical_scoring_environment': 'Low', 'noise_factor': 'Very High'
            },
            {
                'team': 'SEA', 'stadium_name': 'Lumen Field', 'city': 'Seattle', 'state': 'WA',
                'opened': 2002, 'capacity': 69000, 'is_dome': False, 'has_retractable_roof': True,
                'altitude': 56, 'field_surface': 'turf', 'time_zone': 'PST', 'conference': 'NFC',
                'division': 'West', 'latitude': 47.5952, 'longitude': -122.3316,
                'avg_temperature_sept': 66, 'avg_temperature_oct': 57, 'avg_temperature_nov': 47,
                'avg_temperature_dec': 40, 'avg_temperature_jan': 35, 'avg_wind_speed': 8.1,
                'historical_scoring_environment': 'Average', 'noise_factor': 'Very High'
            },
            {
                'team': 'SF', 'stadium_name': "Levi's Stadium", 'city': 'Santa Clara', 'state': 'CA',
                'opened': 2014, 'capacity': 68500, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 43, 'field_surface': 'grass', 'time_zone': 'PST', 'conference': 'NFC',
                'division': 'West', 'latitude': 37.4030, 'longitude': -121.9696,
                'avg_temperature_sept': 75, 'avg_temperature_oct': 71, 'avg_temperature_nov': 63,
                'avg_temperature_dec': 55, 'avg_temperature_jan': 50, 'avg_wind_speed': 7.6,
                'historical_scoring_environment': 'Average', 'noise_factor': 'High'
            },
            {
                'team': 'TB', 'stadium_name': 'Raymond James Stadium', 'city': 'Tampa', 'state': 'FL',
                'opened': 1998, 'capacity': 65890, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 26, 'field_surface': 'grass', 'time_zone': 'EST', 'conference': 'NFC',
                'division': 'South', 'latitude': 27.9759, 'longitude': -82.5033,
                'avg_temperature_sept': 85, 'avg_temperature_oct': 79, 'avg_temperature_nov': 72,
                'avg_temperature_dec': 64, 'avg_temperature_jan': 59, 'avg_wind_speed': 8.9,
                'historical_scoring_environment': 'High', 'noise_factor': 'Average'
            },
            {
                'team': 'TEN', 'stadium_name': 'Nissan Stadium', 'city': 'Nashville', 'state': 'TN',
                'opened': 1999, 'capacity': 69143, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 597, 'field_surface': 'grass', 'time_zone': 'CST', 'conference': 'AFC',
                'division': 'South', 'latitude': 36.1665, 'longitude': -86.7713,
                'avg_temperature_sept': 78, 'avg_temperature_oct': 67, 'avg_temperature_nov': 55,
                'avg_temperature_dec': 44, 'avg_temperature_jan': 38, 'avg_wind_speed': 7.2,
                'historical_scoring_environment': 'Average', 'noise_factor': 'Average'
            },
            {
                'team': 'WAS', 'stadium_name': 'Commanders Field', 'city': 'Landover', 'state': 'MD',
                'opened': 1997, 'capacity': 82000, 'is_dome': False, 'has_retractable_roof': False,
                'altitude': 79, 'field_surface': 'grass', 'time_zone': 'EST', 'conference': 'NFC',
                'division': 'East', 'latitude': 38.9076, 'longitude': -76.8644,
                'avg_temperature_sept': 74, 'avg_temperature_oct': 63, 'avg_temperature_nov': 52,
                'avg_temperature_dec': 41, 'avg_temperature_jan': 34, 'avg_wind_speed': 8.7,
                'historical_scoring_environment': 'Average', 'noise_factor': 'Low'
            }
        ]
        
        self.stadium_data = pd.DataFrame(stadium_records)
        logger.info(f"Loaded stadium database with {len(self.stadium_data)} venues")
        return self.stadium_data
    
    def get_stadium_info(self, team: str) -> Optional[Dict]:
        """Get complete stadium information for a team."""
        if self.stadium_data is None:
            return None
        
        team_data = self.stadium_data[self.stadium_data['team'] == team]
        if team_data.empty:
            return None
        
        return team_data.iloc[0].to_dict()
    
    def get_venue_scoring_environment(self, team: str) -> str:
        """Get historical scoring environment classification."""
        stadium_info = self.get_stadium_info(team)
        if stadium_info:
            return stadium_info.get('historical_scoring_environment', 'Average')
        return 'Average'
    
    def calculate_dome_advantage(self, position: str) -> float:
        """Calculate dome advantage by position."""
        dome_advantages = {
            'QB': 1.02,   # +2% in controlled environment
            'WR': 1.02,   # +2% better ball flight
            'TE': 1.01,   # +1% slight advantage
            'RB': 1.00,   # No significant advantage
            'K': 1.05    # +5% no wind/weather
        }
        return dome_advantages.get(position, 1.0)
    
    def calculate_altitude_impact(self, altitude: int, position: str) -> float:
        """Calculate altitude impact on performance."""
        if altitude < 3000:
            return 1.0
        
        # Denver effect (5,280 ft)
        altitude_factor = (altitude - 3000) / 2280
        
        altitude_impacts = {
            'K': 1.0 + (altitude_factor * 0.03),    # +3% kicking at Denver
            'QB': 1.0 + (altitude_factor * 0.01),   # +1% passing at Denver
            'WR': 1.0 + (altitude_factor * 0.005),  # +0.5% receiving
            'TE': 1.0 + (altitude_factor * 0.005),  # +0.5% receiving
            'RB': 1.0                               # No impact
        }
        
        return altitude_impacts.get(position, 1.0)
    
    def calculate_surface_impact(self, surface: str, position: str) -> Dict[str, float]:
        """Calculate field surface impact."""
        if surface == 'turf':
            return {
                'speed_boost': 1.02,      # +2% speed on turf
                'injury_risk': 1.1,       # +10% injury risk
                'consistency': 1.01       # +1% more consistent
            }
        else:  # grass
            return {
                'speed_boost': 1.0,       # Natural speed
                'injury_risk': 1.0,       # Natural injury risk
                'consistency': 0.99       # -1% less consistent (weather dependent)
            }
    
    def get_cold_weather_stadiums(self, threshold_temp: int = 35) -> List[str]:
        """Get stadiums with cold weather issues."""
        if self.stadium_data is None:
            return []
        
        # Look at December/January temperatures
        cold_stadiums = self.stadium_data[
            (self.stadium_data['is_dome'] == False) &
            ((self.stadium_data['avg_temperature_dec'] <= threshold_temp) |
             (self.stadium_data['avg_temperature_jan'] <= threshold_temp))
        ]
        
        return cold_stadiums['team'].tolist()
    
    def get_high_wind_stadiums(self, wind_threshold: float = 10.0) -> List[str]:
        """Get stadiums with high wind conditions."""
        if self.stadium_data is None:
            return []
        
        windy_stadiums = self.stadium_data[
            (self.stadium_data['is_dome'] == False) &
            (self.stadium_data['avg_wind_speed'] >= wind_threshold)
        ]
        
        return windy_stadiums['team'].tolist()
    
    def get_scoring_environment_teams(self, environment: str) -> List[str]:
        """Get teams by scoring environment."""
        if self.stadium_data is None:
            return []
        
        env_teams = self.stadium_data[
            self.stadium_data['historical_scoring_environment'] == environment
        ]
        
        return env_teams['team'].tolist()
    
    def calculate_venue_matchup_factor(
        self, 
        home_team: str, 
        position: str, 
        month: int
    ) -> float:
        """Calculate comprehensive venue matchup factor."""
        stadium_info = self.get_stadium_info(home_team)
        if not stadium_info:
            return 1.0
        
        total_factor = 1.0
        
        # Dome advantage
        if stadium_info['is_dome']:
            total_factor *= self.calculate_dome_advantage(position)
        
        # Altitude impact
        total_factor *= self.calculate_altitude_impact(stadium_info['altitude'], position)
        
        # Surface impact (speed boost only for fantasy)
        surface_impact = self.calculate_surface_impact(stadium_info['field_surface'], position)
        total_factor *= surface_impact['speed_boost']
        
        # Scoring environment
        scoring_env = stadium_info['historical_scoring_environment']
        if scoring_env == 'High':
            total_factor *= 1.03  # +3% in high-scoring venues
        elif scoring_env == 'Low':
            total_factor *= 0.97  # -3% in low-scoring venues
        
        # Temperature impact for outdoor stadiums
        if not stadium_info['is_dome']:
            temp_col = f'avg_temperature_{self._month_to_abbr(month)}'
            if temp_col in stadium_info:
                temp = stadium_info[temp_col]
                if temp < 32:  # Freezing
                    total_factor *= 0.95  # -5% for cold weather
                elif temp < 20:  # Extreme cold
                    total_factor *= 0.90  # -10% for extreme cold
        
        return total_factor
    
    def _month_to_abbr(self, month: int) -> str:
        """Convert month number to abbreviation."""
        month_map = {
            9: 'sept', 10: 'oct', 11: 'nov',
            12: 'dec', 1: 'jan', 2: 'feb'
        }
        return month_map.get(month, 'sept')
    
    def get_stadium_analytics_summary(self) -> pd.DataFrame:
        """Get summary analytics of all stadiums."""
        if self.stadium_data is None:
            return pd.DataFrame()
        
        summary = self.stadium_data.groupby(['conference', 'division']).agg({
            'is_dome': 'sum',
            'altitude': 'mean',
            'capacity': 'mean',
            'avg_wind_speed': 'mean',
            'avg_temperature_dec': 'mean'
        }).reset_index()
        
        summary['total_teams'] = self.stadium_data.groupby(['conference', 'division']).size().values
        summary['dome_percentage'] = (summary['is_dome'] / summary['total_teams'] * 100).round(1)
        
        return summary
    
    def get_weather_neutral_venues(self) -> List[str]:
        """Get venues with minimal weather impact."""
        if self.stadium_data is None:
            return []
        
        # Domes and retractable roof stadiums in good weather
        neutral_venues = self.stadium_data[
            (self.stadium_data['is_dome'] == True) |
            (self.stadium_data['has_retractable_roof'] == True) |
            ((self.stadium_data['avg_wind_speed'] < 8) & 
             (self.stadium_data['avg_temperature_dec'] > 45))
        ]
        
        return neutral_venues['team'].tolist()


def validate_stadium_database() -> Dict[str, bool]:
    """Validate stadium database functionality."""
    validation_results = {}
    
    try:
        db = StadiumDatabase()
        
        # Test database loading
        validation_results['database_loaded'] = db.stadium_data is not None and len(db.stadium_data) == 32
        
        # Test stadium info retrieval
        kc_info = db.get_stadium_info('KC')
        validation_results['stadium_info_retrieval'] = kc_info is not None and kc_info['stadium_name'] == 'Arrowhead Stadium'
        
        # Test dome advantage calculation
        dome_advantage = db.calculate_dome_advantage('QB')
        validation_results['dome_advantage_calculation'] = dome_advantage > 1.0
        
        # Test altitude impact
        denver_altitude = db.calculate_altitude_impact(5280, 'K')
        validation_results['altitude_impact_calculation'] = denver_altitude > 1.0
        
        # Test cold weather stadiums
        cold_stadiums = db.get_cold_weather_stadiums()
        validation_results['cold_weather_identification'] = 'BUF' in cold_stadiums and 'GB' in cold_stadiums
        
        # Test high wind stadiums
        windy_stadiums = db.get_high_wind_stadiums()
        validation_results['wind_identification'] = 'CHI' in windy_stadiums
        
        # Test venue matchup factor
        venue_factor = db.calculate_venue_matchup_factor('DEN', 'K', 12)
        validation_results['venue_matchup_calculation'] = venue_factor != 1.0
        
        # Test analytics summary
        summary = db.get_stadium_analytics_summary()
        validation_results['analytics_summary'] = not summary.empty
        
    except Exception as e:
        validation_results['validation_error'] = str(e)
    
    return validation_results


if __name__ == "__main__":
    # Test the stadium database
    print("🏟️  Testing Stadium Database")
    print("=" * 50)
    
    # Run validation
    validation = validate_stadium_database()
    
    print("Validation Results:")
    for test, result in validation.items():
        if isinstance(result, bool):
            status = "✅" if result else "❌"
            print(f"{status} {test}: {result}")
        else:
            print(f"ℹ️  {test}: {result}")
    
    # Example usage
    print("\n" + "=" * 50)
    print("Stadium Database Examples")
    
    db = StadiumDatabase()
    
    # Denver example
    denver_info = db.get_stadium_info('DEN')
    if denver_info:
        print(f"\nDenver Broncos Stadium:")
        print(f"  Name: {denver_info['stadium_name']}")
        print(f"  Altitude: {denver_info['altitude']} ft")
        print(f"  Is Dome: {denver_info['is_dome']}")
        print(f"  Field Surface: {denver_info['field_surface']}")
        print(f"  December Avg Temp: {denver_info['avg_temperature_dec']}°F")
    
    # Cold weather stadiums
    cold_stadiums = db.get_cold_weather_stadiums()
    print(f"\nCold Weather Stadiums ({len(cold_stadiums)}):")
    print(f"  {', '.join(cold_stadiums)}")
    
    # High scoring venues
    high_scoring = db.get_scoring_environment_teams('High')
    print(f"\nHigh Scoring Venues ({len(high_scoring)}):")
    print(f"  {', '.join(high_scoring)}")
    
    # Venue factors
    print(f"\nVenue Impact Examples:")
    print(f"  DEN Kicker (Dec): {db.calculate_venue_matchup_factor('DEN', 'K', 12):.3f}x")
    print(f"  GB QB (Dec): {db.calculate_venue_matchup_factor('GB', 'QB', 12):.3f}x")
    print(f"  NO WR (Dec): {db.calculate_venue_matchup_factor('NO', 'WR', 12):.3f}x")
    
    print("\nStadium Database implementation complete! 🎯")