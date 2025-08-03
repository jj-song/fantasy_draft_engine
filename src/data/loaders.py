"""
Data loading utilities for the Fantasy Football AI Draft Tool.

This module provides centralized data loading functionality to avoid
dummy data generation and ensure real player data is used.
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import config

# Real player name pools for fallback data if needed
REAL_PLAYER_NAMES = {
    'QB': [
        'Josh Allen', 'Patrick Mahomes', 'Lamar Jackson', 'Justin Herbert', 
        'Joe Burrow', 'Dak Prescott', 'Russell Wilson', 'Aaron Rodgers',
        'Kirk Cousins', 'Derek Carr', 'Ryan Tannehill', 'Matt Ryan',
        'Jalen Hurts', 'Trevor Lawrence', 'Justin Fields', 'Tua Tagovailoa',
        'Daniel Jones', 'Mac Jones', 'Geno Smith', 'Jameis Winston',
        'Jimmy Garoppolo', 'Jacoby Brissett', 'Marcus Mariota', 'Baker Mayfield',
        'Mitchell Trubisky', 'Sam Darnold', 'Andy Dalton', 'Ryan Fitzpatrick',
        'Mason Rudolph', 'Mike White', 'Davis Mills', 'Drew Lock',
        'Gardner Minshew', 'Tyler Huntley', 'Cooper Rush', 'Teddy Bridgewater'
    ],
    'RB': [
        'Christian McCaffrey', 'Jonathan Taylor', 'Derrick Henry', 'Dalvin Cook',
        'Alvin Kamara', 'Ezekiel Elliott', 'Aaron Jones', 'Nick Chubb',
        'Austin Ekeler', 'Joe Mixon', 'Saquon Barkley', 'Josh Jacobs',
        'Najee Harris', 'D\'Andre Swift', 'James Conner', 'Leonard Fournette',
        'David Montgomery', 'Clyde Edwards-Helaire', 'Miles Sanders', 'Cam Akers',
        'Antonio Gibson', 'Elijah Mitchell', 'Cordarrelle Patterson', 'Javonte Williams',
        'Michael Carter', 'James Robinson', 'Dameon Pierce', 'Breece Hall',
        'Kenneth Walker III', 'Isaiah Pacheco', 'Tony Pollard', 'Alexander Mattison',
        'AJ Dillon', 'Rhamondre Stevenson', 'Rachaad White', 'Tyler Allgeier',
        'Brian Robinson Jr.', 'Damien Harris', 'Melvin Gordon', 'Kareem Hunt'
    ],
    'WR': [
        'Cooper Kupp', 'Davante Adams', 'Tyreek Hill', 'Stefon Diggs',
        'DeAndre Hopkins', 'DK Metcalf', 'CeeDee Lamb', 'Justin Jefferson',
        'A.J. Brown', 'Keenan Allen', 'Mike Evans', 'Chris Godwin',
        'Amari Cooper', 'Tyler Lockett', 'Diontae Johnson', 'Tee Higgins',
        'Ja\'Marr Chase', 'Jaylen Waddle', 'Terry McLaurin', 'Michael Pittman Jr.',
        'Courtland Sutton', 'DJ Moore', 'Amon-Ra St. Brown', 'Gabriel Davis',
        'Brandin Cooks', 'Allen Robinson', 'Robert Woods', 'Jerry Jeudy',
        'Elijah Moore', 'Kadarius Toney', 'DeVonta Smith', 'Rashod Bateman',
        'Jaylen Waddle', 'Drake London', 'Garrett Wilson', 'Chris Olave',
        'Romeo Doubs', 'George Pickens', 'Christian Watson', 'Jahan Dotson'
    ],
    'TE': [
        'Travis Kelce', 'Mark Andrews', 'George Kittle', 'Darren Waller',
        'Kyle Pitts', 'T.J. Hockenson', 'Dallas Goedert', 'Zach Ertz',
        'Hunter Henry', 'Mike Gesicki', 'Noah Fant', 'Tyler Higbee',
        'Pat Freiermuth', 'David Njoku', 'Dawson Knox', 'Robert Tonyan',
        'Gerald Everett', 'Cole Kmet', 'Albert Okwuegbunam', 'Logan Thomas',
        'Austin Hooper', 'C.J. Uzomah', 'Tyler Conklin', 'Irv Smith Jr.',
        'Hayden Hurst', 'O.J. Howard', 'Cameron Brate', 'Jack Doyle',
        'Evan Engram', 'Dan Arnold', 'Blake Jarwin', 'Adam Trautman',
        'Isaiah Likely', 'Trey McBride', 'Greg Dulcich', 'Daniel Bellinger'
    ],
    'K': [
        'Justin Tucker', 'Harrison Butker', 'Tyler Bass', 'Daniel Carlson',
        'Jason Sanders', 'Younghoe Koo', 'Matt Gay', 'Jake Elliott',
        'Brandon McManus', 'Nick Folk', 'Ryan Succop', 'Robbie Gould',
        'Mason Crosby', 'Cairo Santos', 'Graham Gano', 'Dustin Hopkins',
        'Chris Boswell', 'Wil Lutz', 'Jason Myers', 'Brett Maher',
        'Greg Zuerlein', 'Cade York', 'Cameron Dicker', 'Riley Patterson',
        'Evan McPherson', 'Matt Prater', 'Brandon Aubrey', 'Jake Moody'
    ],
    'DST': [
        'San Francisco 49ers', 'Buffalo Bills', 'Philadelphia Eagles', 'Dallas Cowboys',
        'New England Patriots', 'Baltimore Ravens', 'Pittsburgh Steelers', 'Green Bay Packers',
        'Kansas City Chiefs', 'Los Angeles Chargers', 'Tampa Bay Buccaneers', 'Miami Dolphins',
        'Indianapolis Colts', 'New Orleans Saints', 'Minnesota Vikings', 'Denver Broncos',
        'Cleveland Browns', 'Tennessee Titans', 'Las Vegas Raiders', 'Seattle Seahawks',
        'Carolina Panthers', 'New York Jets', 'Washington Commanders', 'Los Angeles Rams',
        'Chicago Bears', 'Atlanta Falcons', 'Detroit Lions', 'Arizona Cardinals',
        'Cincinnati Bengals', 'New York Giants', 'Jacksonville Jaguars', 'Houston Texans'
    ]
}

def load_position_data(position: str, use_real_data_only: bool = True) -> Optional[pd.DataFrame]:
    """
    Load feature-engineered data for a specific position.
    
    Args:
        position: Player position (QB, RB, WR, TE, K, DST)
        use_real_data_only: If True, return None when real data unavailable instead of dummy data
    
    Returns:
        DataFrame with position data or None if not available
    """
    data_path = project_root / f'data/processed/position_specific/{position.lower()}/{position.lower()}_features.parquet'
    
    if data_path.exists():
        try:
            df = pd.read_parquet(data_path)
            print(f"✅ Loaded real data for {position}: {len(df)} players")
            return df
        except Exception as e:
            print(f"❌ Error loading {position} data: {e}")
            if use_real_data_only:
                return None
    else:
        print(f"⚠️ No feature-engineered data found for {position}")
        if use_real_data_only:
            return None
    
    # If we get here and use_real_data_only is False, we could generate fallback data
    # But for now, let's avoid dummy data entirely
    return None

def create_realistic_fallback_data(position: str, n_samples: int = 50) -> pd.DataFrame:
    """
    Create realistic fallback data using real player names and reasonable stats.
    
    Args:
        position: Player position
        n_samples: Number of players to create
    
    Returns:
        DataFrame with realistic player data
    """
    if position not in REAL_PLAYER_NAMES:
        raise ValueError(f"Position {position} not supported")
    
    # Use real player names
    player_names = REAL_PLAYER_NAMES[position][:n_samples]
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # Team assignments
    teams = ['ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL', 'DEN', 
             'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC', 'LV', 'LAC', 'LAR', 'MIA', 
             'MIN', 'NE', 'NO', 'NYG', 'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS']
    
    data = {
        'player_id': [f'{position.lower()}_player_{i}' for i in range(len(player_names))],
        'player_name': player_names,
        'position': [position] * len(player_names),
        'team': np.random.choice(teams, len(player_names)),
        'age': np.random.randint(22, 34, len(player_names)),
        'games_played': np.random.randint(12, 17, len(player_names)),
    }
    
    # Position-specific realistic stats based on 2023 actual ranges
    if position == 'QB':
        data.update({
            'passing_attempts': np.random.randint(250, 650, len(player_names)),
            'passing_completions': np.random.randint(180, 450, len(player_names)),
            'passing_yards': np.random.randint(2000, 5500, len(player_names)),
            'passing_tds': np.random.randint(12, 45, len(player_names)),
            'interceptions': np.random.randint(4, 18, len(player_names)),
            'rushing_attempts': np.random.randint(20, 120, len(player_names)),
            'rushing_yards': np.random.randint(50, 800, len(player_names)),
            'rushing_tds': np.random.randint(1, 12, len(player_names)),
        })
    elif position == 'RB':
        data.update({
            'rushing_attempts': np.random.randint(80, 350, len(player_names)),
            'rushing_yards': np.random.randint(300, 1800, len(player_names)),
            'rushing_tds': np.random.randint(2, 18, len(player_names)),
            'targets': np.random.randint(20, 120, len(player_names)),
            'receptions': np.random.randint(15, 100, len(player_names)),
            'receiving_yards': np.random.randint(100, 1000, len(player_names)),
            'receiving_tds': np.random.randint(0, 8, len(player_names)),
        })
    elif position == 'WR':
        data.update({
            'targets': np.random.randint(40, 180, len(player_names)),
            'receptions': np.random.randint(25, 130, len(player_names)),
            'receiving_yards': np.random.randint(300, 1800, len(player_names)),
            'receiving_tds': np.random.randint(2, 16, len(player_names)),
            'rushing_attempts': np.random.randint(0, 15, len(player_names)),
            'rushing_yards': np.random.randint(0, 150, len(player_names)),
            'rushing_tds': np.random.randint(0, 3, len(player_names)),
        })
    elif position == 'TE':
        data.update({
            'targets': np.random.randint(30, 150, len(player_names)),
            'receptions': np.random.randint(20, 110, len(player_names)),
            'receiving_yards': np.random.randint(200, 1400, len(player_names)),
            'receiving_tds': np.random.randint(1, 15, len(player_names)),
        })
    elif position == 'K':
        data.update({
            'fg_made': np.random.randint(18, 35, len(player_names)),
            'fg_attempted': np.random.randint(22, 42, len(player_names)),
            'extra_points_made': np.random.randint(25, 55, len(player_names)),
            'extra_points_attempted': np.random.randint(26, 58, len(player_names)),
        })
    elif position == 'DST':
        data.update({
            'sacks': np.random.randint(20, 55, len(player_names)),
            'interceptions': np.random.randint(8, 22, len(player_names)),
            'fumbles_recovered': np.random.randint(4, 18, len(player_names)),
            'defensive_tds': np.random.randint(0, 6, len(player_names)),
            'safeties': np.random.randint(0, 2, len(player_names)),
            'points_allowed': np.random.randint(280, 450, len(player_names)),
            'yards_allowed': np.random.randint(4800, 6500, len(player_names)),
        })
    
    df = pd.DataFrame(data)
    
    # Calculate fantasy points using config scoring
    df['fantasy_points'] = calculate_fantasy_points(df, position)
    df['fantasy_points_per_game'] = df['fantasy_points'] / df['games_played']
    
    return df

def calculate_fantasy_points(df: pd.DataFrame, position: str) -> pd.Series:
    """
    Calculate fantasy points based on config scoring system.
    
    Args:
        df: DataFrame with player stats
        position: Player position
    
    Returns:
        Series with fantasy points
    """
    points = pd.Series(0.0, index=df.index)
    
    if position in ['QB', 'RB', 'WR', 'TE']:
        # Standard scoring from config
        if 'passing_yards' in df.columns:
            points += df['passing_yards'] * config.FANTASY_POINTS.get('passing_yards', 0.04)
        if 'passing_tds' in df.columns:
            points += df['passing_tds'] * config.FANTASY_POINTS.get('passing_tds', 4)
        if 'interceptions' in df.columns:
            points += df['interceptions'] * config.FANTASY_POINTS.get('interceptions', -2)
        if 'rushing_yards' in df.columns:
            points += df['rushing_yards'] * config.FANTASY_POINTS.get('rushing_yards', 0.1)
        if 'rushing_tds' in df.columns:
            points += df['rushing_tds'] * config.FANTASY_POINTS.get('rushing_tds', 6)
        if 'receptions' in df.columns:
            points += df['receptions'] * config.FANTASY_POINTS.get('receptions', 0.5)
        if 'receiving_yards' in df.columns:
            points += df['receiving_yards'] * config.FANTASY_POINTS.get('receiving_yards', 0.1)
        if 'receiving_tds' in df.columns:
            points += df['receiving_tds'] * config.FANTASY_POINTS.get('receiving_tds', 6)
    
    elif position == 'K':
        # Kicker scoring (approximate)
        if 'fg_made' in df.columns:
            points += df['fg_made'] * 3  # 3 points per FG
        if 'extra_points_made' in df.columns:
            points += df['extra_points_made'] * 1  # 1 point per XP
    
    elif position == 'DST':
        # Defense scoring (approximate)
        if 'sacks' in df.columns:
            points += df['sacks'] * 1  # 1 point per sack
        if 'interceptions' in df.columns:
            points += df['interceptions'] * 2  # 2 points per INT
        if 'fumbles_recovered' in df.columns:
            points += df['fumbles_recovered'] * 2  # 2 points per fumble recovery
        if 'defensive_tds' in df.columns:
            points += df['defensive_tds'] * 6  # 6 points per defensive TD
        if 'safeties' in df.columns:
            points += df['safeties'] * 2  # 2 points per safety
        # Points allowed penalty would go here but not in this simple version
    
    return points

def get_available_positions() -> List[str]:
    """
    Get list of positions that have available feature-engineered data.
    
    Returns:
        List of position strings
    """
    available = []
    for position in config.POSITIONS:
        if load_position_data(position, use_real_data_only=True) is not None:
            available.append(position)
    return available

def validate_player_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate that player data contains real players, not dummy data.
    
    Args:
        df: DataFrame with player data
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    if 'player_name' in df.columns:
        dummy_patterns = ['Player ', 'QB Player', 'RB Player', 'WR Player', 'TE Player', 'K Player', 'DST Player']
        dummy_names = df['player_name'].str.contains('|'.join(dummy_patterns), na=False)
        
        if dummy_names.any():
            dummy_count = dummy_names.sum()
            issues.append(f"Found {dummy_count} dummy player names")
    
    # Check for unrealistic data patterns
    if 'fantasy_points_per_game' in df.columns:
        if df['fantasy_points_per_game'].min() < 0:
            issues.append("Found negative fantasy points")
        if df['fantasy_points_per_game'].max() > 50:  # Very high but possible
            high_count = (df['fantasy_points_per_game'] > 50).sum()
            if high_count > 2:  # More than 2 players with >50 FPPG is suspicious
                issues.append(f"Found {high_count} players with >50 FPPG (suspicious)")
    
    return len(issues) == 0, issues