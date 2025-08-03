#!/usr/bin/env python3
"""
Value Over Replacement (VOR) Validation Tests

This test suite ensures that the VOR calculations produce realistic
fantasy football rankings that align with actual drafting strategy.
"""

import sys
import os
import pandas as pd
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

def test_vor_configuration():
    """Test that VOR configuration values are reasonable."""
    print("=" * 60)
    print("TEST 1: VOR Configuration Validation")
    print("=" * 60)
    
    import config
    
    # Test replacement levels
    replacement_levels = config.VOR_REPLACEMENT_LEVELS
    scarcity_multipliers = config.VOR_SCARCITY_MULTIPLIERS
    
    print("Replacement Levels:")
    for pos, level in replacement_levels.items():
        print(f"  {pos}: {level}")
    
    print("\nScarcity Multipliers:")
    for pos, multiplier in scarcity_multipliers.items():
        print(f"  {pos}: {multiplier}x")
    
    # Validate replacement levels make sense for 12-team league
    expected_ranges = {
        'QB': (12, 15),   # 12-15 for 12-team league
        'RB': (28, 36),   # 28-36 for multiple starters + FLEX
        'WR': (28, 36),   # 28-36 for multiple starters + FLEX  
        'TE': (12, 15),   # 12-15 for 12-team league
    }
    
    all_valid = True
    for pos, (min_val, max_val) in expected_ranges.items():
        if pos in replacement_levels:
            level = replacement_levels[pos]
            if not (min_val <= level <= max_val):
                print(f"❌ FAIL: {pos} replacement level {level} not in expected range {min_val}-{max_val}")
                all_valid = False
            else:
                print(f"✅ PASS: {pos} replacement level {level} is reasonable")
    
    # Validate scarcity multipliers follow expected hierarchy
    expected_hierarchy = ['RB', 'TE', 'WR', 'QB']  # From highest to lowest scarcity
    prev_multiplier = float('inf')
    
    for pos in expected_hierarchy:
        if pos in scarcity_multipliers:
            current_multiplier = scarcity_multipliers[pos]
            if current_multiplier > prev_multiplier:
                print(f"❌ FAIL: {pos} multiplier {current_multiplier} should be ≤ previous {prev_multiplier}")
                all_valid = False
            prev_multiplier = current_multiplier
    
    if all_valid:
        print("✅ PASS: VOR configuration is valid")
    else:
        print("❌ FAIL: VOR configuration has issues")
    
    return all_valid

def test_ranking_distribution():
    """Test that rankings show appropriate positional distribution in top picks."""
    print("\n" + "=" * 60)
    print("TEST 2: Ranking Distribution Validation")
    print("=" * 60)
    
    try:
        # Find the most recent rankings file
        rankings_dir = project_root / 'data' / 'draft_lists'
        ranking_files = list(rankings_dir.glob('overall_rankings_*.csv'))
        
        if not ranking_files:
            print("❌ FAIL: No ranking files found")
            return False
            
        latest_file = max(ranking_files, key=lambda x: x.stat().st_mtime)
        print(f"Using rankings file: {latest_file.name}")
        
        df = pd.read_csv(latest_file)
        
        # Test top 10 distribution
        top_10 = df.head(10)
        top_10_positions = top_10['position'].value_counts()
        
        print("\nTop 10 Position Distribution:")
        for pos, count in top_10_positions.items():
            print(f"  {pos}: {count}")
        
        # Fantasy football expectations for top 10:
        # - Should have 4-6 RBs (high scarcity)
        # - Should have 2-4 WRs  
        # - Should have 0-2 QBs (not many in top 10)
        # - Should have 0-2 TEs (elite TEs only)
        
        checks_passed = 0
        total_checks = 0
        
        # Check 1: RBs should dominate top 10
        rb_count = top_10_positions.get('RB', 0)
        total_checks += 1
        if 3 <= rb_count <= 7:
            print(f"✅ PASS: {rb_count} RBs in top 10 (expected 3-7)")
            checks_passed += 1
        else:
            print(f"❌ FAIL: {rb_count} RBs in top 10 (expected 3-7)")
        
        # Check 2: QBs should be limited in top 10  
        qb_count = top_10_positions.get('QB', 0)
        total_checks += 1
        if qb_count <= 3:
            print(f"✅ PASS: {qb_count} QBs in top 10 (expected ≤3)")
            checks_passed += 1
        else:
            print(f"❌ FAIL: {qb_count} QBs in top 10 (expected ≤3)")
        
        # Check 3: Top overall should not be a QB
        top_player = df.iloc[0]
        total_checks += 1
        if top_player['position'] != 'QB':
            print(f"✅ PASS: Top player is {top_player['player_name']} ({top_player['position']}), not QB")
            checks_passed += 1
        else:
            print(f"❌ FAIL: Top player is QB ({top_player['player_name']})")
        
        # Check 4: First QB should be outside top 5
        first_qb_rank = None
        for i, row in df.iterrows():
            if row['position'] == 'QB':
                first_qb_rank = row['overall_rank']
                break
        
        total_checks += 1
        if first_qb_rank and first_qb_rank > 5:
            print(f"✅ PASS: First QB ranks #{first_qb_rank} (expected >5)")
            checks_passed += 1
        else:
            print(f"❌ FAIL: First QB ranks #{first_qb_rank} (expected >5)")
        
        success_rate = checks_passed / total_checks
        if success_rate >= 0.75:
            print(f"✅ PASS: Ranking distribution is realistic ({checks_passed}/{total_checks} checks passed)")
            return True
        else:
            print(f"❌ FAIL: Ranking distribution needs improvement ({checks_passed}/{total_checks} checks passed)")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error validating rankings: {e}")
        return False

def test_vor_values():
    """Test that VOR values follow expected patterns."""
    print("\n" + "=" * 60)
    print("TEST 3: VOR Values Validation")
    print("=" * 60)
    
    try:
        # Find the most recent rankings file
        rankings_dir = project_root / 'data' / 'draft_lists'
        ranking_files = list(rankings_dir.glob('overall_rankings_*.csv'))
        
        if not ranking_files:
            print("❌ FAIL: No ranking files found")
            return False
            
        latest_file = max(ranking_files, key=lambda x: x.stat().st_mtime)
        df = pd.read_csv(latest_file)
        
        # Test VOR patterns by position
        positions = ['QB', 'RB', 'WR', 'TE']
        all_valid = True
        
        print("VOR Analysis by Position:")
        for pos in positions:
            pos_df = df[df['position'] == pos].head(5)  # Top 5 per position
            if len(pos_df) > 0:
                vor_values = pos_df['vor'].tolist()
                avg_vor = pos_df['vor'].mean()
                max_vor = pos_df['vor'].max()
                
                print(f"{pos}:")
                print(f"  Top 5 VOR values: {[f'{v:.1f}' for v in vor_values]}")
                print(f"  Average: {avg_vor:.1f}, Max: {max_vor:.1f}")
        
        # Check that top RBs have higher VOR than top QBs
        top_rb_vor = df[df['position'] == 'RB'].iloc[0]['vor'] if len(df[df['position'] == 'RB']) > 0 else 0
        top_qb_vor = df[df['position'] == 'QB'].iloc[0]['vor'] if len(df[df['position'] == 'QB']) > 0 else 0
        
        if top_rb_vor > top_qb_vor:
            print(f"✅ PASS: Top RB VOR ({top_rb_vor:.1f}) > Top QB VOR ({top_qb_vor:.1f})")
        else:
            print(f"❌ FAIL: Top RB VOR ({top_rb_vor:.1f}) ≤ Top QB VOR ({top_qb_vor:.1f})")
            all_valid = False
        
        # Check that VOR values are reasonable (not negative for top players)
        top_50 = df.head(50)
        negative_vor_count = (top_50['vor'] < 0).sum()
        
        if negative_vor_count == 0:
            print(f"✅ PASS: No negative VOR values in top 50")
        else:
            print(f"⚠️ WARNING: {negative_vor_count} negative VOR values in top 50")
        
        return all_valid
        
    except Exception as e:
        print(f"❌ FAIL: Error validating VOR values: {e}")
        return False

def main():
    """Run all VOR validation tests."""
    print("🏈 Fantasy Draft Engine - VOR Validation Tests")
    print("🔍 Ensuring realistic fantasy football rankings")
    print("")
    
    tests = [
        ("VOR Configuration", test_vor_configuration),
        ("Ranking Distribution", test_ranking_distribution),
        ("VOR Values", test_vor_values)
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
    print("VOR VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ SUCCESS: All VOR validation tests passed!")
        print("✅ Rankings reflect realistic fantasy football strategy")
        return True
    else:
        print("❌ FAILURE: Some VOR validation tests failed")
        print("❌ Rankings may not reflect optimal fantasy strategy")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)