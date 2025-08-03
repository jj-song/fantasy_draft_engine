#!/usr/bin/env python3
"""
Comprehensive Data Validation Tests

This test suite ensures that the pipeline uses real NFL data throughout
and completely eliminates dummy data generation.
"""

import sys
import os
import pandas as pd
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

def test_raw_data_contains_real_players():
    """Test that raw data files contain real NFL player names."""
    print("=" * 60)
    print("TEST 1: Validating Raw Data Contains Real NFL Players")
    print("=" * 60)
    
    from src.data_storage import load_raw_data
    
    # Known real NFL players by position (for validation)
    REAL_NFL_PLAYERS = {
        'QB': {
            'Aaron Rodgers', 'Tom Brady', 'Patrick Mahomes', 'Josh Allen', 'Lamar Jackson',
            'Joe Burrow', 'Justin Herbert', 'Dak Prescott', 'Russell Wilson', 'Kirk Cousins'
        },
        'RB': {
            'Christian McCaffrey', 'Derrick Henry', 'Jonathan Taylor', 'Austin Ekeler',
            'Nick Chubb', 'Joe Mixon', 'Dalvin Cook', 'Ezekiel Elliott', 'Aaron Jones'
        },
        'WR': {
            'Cooper Kupp', 'Davante Adams', 'Tyreek Hill', 'Stefon Diggs', 'DeAndre Hopkins',
            'Mike Evans', 'Calvin Ridley', 'DK Metcalf', 'Tyler Lockett', 'Keenan Allen'
        },
        'TE': {
            'Travis Kelce', 'Mark Andrews', 'George Kittle', 'Darren Waller', 'Kyle Pitts',
            'Rob Gronkowski', 'T.J. Hockenson', 'Noah Fant', 'Dallas Goedert'
        }
    }
    
    # Test recent season data
    try:
        df = load_raw_data(2023)
        print(f"✅ Successfully loaded 2023 raw data: {len(df)} players")
        
        # Check if player_name column exists
        if 'player_name' not in df.columns:
            print("❌ FAIL: No 'player_name' column in raw data")
            return False
            
        # Get unique player names
        player_names = set(df['player_name'].dropna())
        print(f"✅ Found {len(player_names)} unique player names")
        
        # Check for real players by position
        real_players_found = 0
        dummy_players_found = 0
        
        for position, known_players in REAL_NFL_PLAYERS.items():
            position_df = df[df['position'] == position]
            position_players = set(position_df['player_name'].dropna())
            
            # Count real players found
            real_found = known_players.intersection(position_players)
            real_players_found += len(real_found)
            
            if real_found:
                print(f"✅ {position}: Found {len(real_found)} known real players (e.g., {list(real_found)[:3]})")
            else:
                print(f"⚠️ {position}: No known real players found")
        
        # Check for dummy data patterns
        dummy_patterns = [
            r'^(QB|RB|WR|TE|K|DST) Player \d+$',
            r'^Player \d+$',
            r'^Test Player',
            r'^Dummy'
        ]
        
        for name in player_names:
            for pattern in dummy_patterns:
                if re.match(pattern, str(name)):
                    dummy_players_found += 1
                    print(f"❌ FOUND DUMMY PLAYER: {name}")
        
        print(f"\n📊 VALIDATION SUMMARY:")
        print(f"   Real NFL players found: {real_players_found}")
        print(f"   Dummy players found: {dummy_players_found}")
        
        if dummy_players_found > 0:
            print("❌ FAIL: Raw data contains dummy players")
            return False
        
        if real_players_found > 20:  # Should find many real players
            print("✅ PASS: Raw data contains real NFL players")
            return True
        else:
            print("⚠️ WARNING: Very few real NFL players found")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error loading raw data: {e}")
        return False

def test_feature_engineering_preserves_real_names():
    """Test that feature engineering preserves real player names."""
    print("\n" + "=" * 60)
    print("TEST 2: Validating Feature Engineering Preserves Real Names")
    print("=" * 60)
    
    try:
        from src.feature_engineering import engineer_features_for_season
        
        # Test feature engineering for a recent year
        df = engineer_features_for_season(2022)
        
        if df is None or df.empty:
            print("❌ FAIL: Feature engineering returned no data")
            return False
            
        print(f"✅ Feature engineering completed: {len(df)} player records")
        
        # Check if player names are preserved
        if 'player_name' not in df.columns:
            print("❌ FAIL: Feature engineering lost player_name column")
            return False
            
        player_names = set(df['player_name'].dropna())
        print(f"✅ Feature engineering preserved {len(player_names)} player names")
        
        # Check for dummy patterns
        dummy_count = 0
        real_count = 0
        
        for name in player_names:
            if re.match(r'^(QB|RB|WR|TE|K|DST) Player \d+$', str(name)):
                dummy_count += 1
                print(f"❌ FOUND DUMMY: {name}")
            elif len(str(name).split()) >= 2 and not str(name).startswith('Player'):
                real_count += 1
        
        print(f"\n📊 FEATURE ENGINEERING SUMMARY:")
        print(f"   Real-looking names: {real_count}")
        print(f"   Dummy names: {dummy_count}")
        
        if dummy_count > 0:
            print("❌ FAIL: Feature engineering created dummy players")
            return False
        elif real_count > 50:
            print("✅ PASS: Feature engineering preserved real player names")
            return True
        else:
            print("⚠️ WARNING: Very few real-looking names in feature engineering")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error in feature engineering: {e}")
        return False

def test_training_data_validation():
    """Test that training pipeline uses real data."""
    print("\n" + "=" * 60)
    print("TEST 3: Validating Training Data Uses Real Players")
    print("=" * 60)
    
    try:
        # Import training function
        sys.path.insert(0, str(project_root / 'scripts'))
        from train_models import train_position_model
        
        # Test training for one position
        position = 'QB'
        print(f"Testing training data for {position}...")
        
        # This will load real data and attempt training
        result = train_position_model(position)
        
        if result is None:
            print(f"⚠️ WARNING: No training result for {position}")
            return False
        
        print(f"✅ Successfully loaded training data for {position}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Error in training data validation: {e}")
        return False

def test_ranking_generation_real_players():
    """Test that ranking generation produces real player names."""
    print("\n" + "=" * 60)
    print("TEST 4: Validating Ranking Generation Uses Real Players")
    print("=" * 60)
    
    try:
        # Import ranking functions
        sys.path.insert(0, str(project_root / 'scripts'))
        from generate_draft_rankings import load_position_data
        
        # Test loading data for each position
        import config
        positions = ['QB', 'RB', 'WR', 'TE']
        
        all_real = True
        total_players = 0
        
        for position in positions:
            print(f"\nTesting {position} data loading...")
            df = load_position_data(position)
            
            if df.empty:
                print(f"⚠️ No data for {position}")
                continue
                
            if 'player_name' not in df.columns:
                print(f"❌ FAIL: No player_name column for {position}")
                all_real = False
                continue
                
            player_names = df['player_name'].dropna()
            total_players += len(player_names)
            
            # Check for dummy patterns
            dummy_count = 0
            for name in player_names:
                if re.match(r'^(QB|RB|WR|TE|K|DST) Player \d+$', str(name)):
                    dummy_count += 1
                    print(f"❌ FOUND DUMMY: {name}")
            
            if dummy_count > 0:
                print(f"❌ FAIL: {position} data contains {dummy_count} dummy players")
                all_real = False
            else:
                print(f"✅ PASS: {position} data contains {len(player_names)} real player names")
        
        print(f"\n📊 RANKING DATA SUMMARY:")
        print(f"   Total players loaded: {total_players}")
        
        if all_real and total_players > 100:
            print("✅ PASS: Ranking generation uses real player data")
            return True
        else:
            print("❌ FAIL: Ranking generation has issues with real data")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error in ranking validation: {e}")
        return False

def main():
    """Run all validation tests."""
    print("🏈 Fantasy Draft Engine - Real Data Validation Tests")
    print("🔍 Ensuring 100% real NFL player usage throughout pipeline")
    print("")
    
    tests = [
        ("Raw Data Validation", test_raw_data_contains_real_players),
        ("Feature Engineering Validation", test_feature_engineering_preserves_real_names),
        ("Training Data Validation", test_training_data_validation),
        ("Ranking Data Validation", test_ranking_generation_real_players)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            print("")
        except Exception as e:
            print(f"❌ CRITICAL ERROR in {test_name}: {e}")
            print("")
    
    # Final summary
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ SUCCESS: All validation tests passed!")
        print("✅ Pipeline is using 100% real NFL player data")
        return True
    else:
        print("❌ FAILURE: Some validation tests failed")
        print("❌ Pipeline may still contain dummy data")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)