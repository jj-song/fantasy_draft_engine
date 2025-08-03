# tests/test_utils.py
import pytest
from src.utils import calculate_fantasy_points_0_5_ppr

def test_calculate_fantasy_points_all_zero():
    """Test with all stats as zero."""
    assert calculate_fantasy_points_0_5_ppr() == 0.0

def test_calculate_fantasy_points_passing_only():
    """Test with only passing stats."""
    # 100 passing yards (100 * 0.04 = 4), 1 TD (4), 1 INT (-2) = 4 + 4 - 2 = 6
    assert calculate_fantasy_points_0_5_ppr(passing_yards=100, passing_tds=1, interceptions=1) == 6.0
    # 250 passing yards (250 * 0.04 = 10), 2 TDs (8) = 18
    assert calculate_fantasy_points_0_5_ppr(passing_yards=250, passing_tds=2) == 18.0

def test_calculate_fantasy_points_rushing_only():
    """Test with only rushing stats."""
    # 50 rushing yards (50 * 0.1 = 5), 1 TD (6) = 5 + 6 = 11
    assert calculate_fantasy_points_0_5_ppr(rushing_yards=50, rushing_tds=1) == 11.0
    # 100 rushing yards (100 * 0.1 = 10)
    assert calculate_fantasy_points_0_5_ppr(rushing_yards=100) == 10.0

def test_calculate_fantasy_points_receiving_only():
    """Test with only receiving stats."""
    # 5 receptions (5 * 0.5 = 2.5), 50 receiving yards (50 * 0.1 = 5), 1 TD (6) = 2.5 + 5 + 6 = 13.5
    assert calculate_fantasy_points_0_5_ppr(receptions=5, receiving_yards=50, receiving_tds=1) == 13.5
    # 10 receptions (10 * 0.5 = 5), 100 receiving yards (100 * 0.1 = 10) = 5 + 10 = 15
    assert calculate_fantasy_points_0_5_ppr(receptions=10, receiving_yards=100) == 15.0

def test_calculate_fantasy_points_fumbles_and_conversions():
    """Test fumbles and 2-point conversions."""
    # 1 fumble lost (-2)
    assert calculate_fantasy_points_0_5_ppr(fumbles_lost=1) == -2.0
    # 1 two-point conversion (2)
    assert calculate_fantasy_points_0_5_ppr(two_pt_conversions=1) == 2.0
    # 2 fumbles lost (-4), 1 two-point conversion (2) = -4 + 2 = -2
    assert calculate_fantasy_points_0_5_ppr(fumbles_lost=2, two_pt_conversions=1) == -2.0

def test_calculate_fantasy_points_mixed_stats_qb():
    """Test with mixed stats typical for a QB."""
    # QB: 300 pass_yds, 2 pass_tds, 1 int, 20 rush_yds, 1 rush_td, 1 two_pt
    # Pass: (300*0.04) + (2*4) - (1*2) = 12 + 8 - 2 = 18
    # Rush: (20*0.1) + (1*6) = 2 + 6 = 8
    # 2pt: 1*2 = 2
    # Total: 18 + 8 + 2 = 28
    points = calculate_fantasy_points_0_5_ppr(
        passing_yards=300,
        passing_tds=2,
        interceptions=1,
        rushing_yards=20,
        rushing_tds=1,
        two_pt_conversions=1
    )
    assert points == 28.0

def test_calculate_fantasy_points_mixed_stats_rb():
    """Test with mixed stats typical for an RB."""
    # RB: 80 rush_yds, 1 rush_td, 3 rec, 25 rec_yds, 1 fumble_lost
    # Rush: (80*0.1) + (1*6) = 8 + 6 = 14
    # Rec: (3*0.5) + (25*0.1) = 1.5 + 2.5 = 4
    # Fumble: -2
    # Total: 14 + 4 - 2 = 16
    points = calculate_fantasy_points_0_5_ppr(
        rushing_yards=80,
        rushing_tds=1,
        receptions=3,
        receiving_yards=25,
        fumbles_lost=1
    )
    assert points == 16.0

def test_calculate_fantasy_points_mixed_stats_wr():
    """Test with mixed stats typical for a WR."""
    # WR: 5 rec, 110 rec_yds, 1 rec_td, 10 rush_yds, 1 two_pt
    # Rec: (5*0.5) + (110*0.1) + (1*6) = 2.5 + 11 + 6 = 19.5
    # Rush: (10*0.1) = 1
    # 2pt: 1*2 = 2
    # Total: 19.5 + 1 + 2 = 22.5
    points = calculate_fantasy_points_0_5_ppr(
        receptions=5,
        receiving_yards=110,
        receiving_tds=1,
        rushing_yards=10, # Some WRs get rushing attempts
        two_pt_conversions=1
    )
    assert points == 22.5

def test_calculate_fantasy_points_rounding():
    """Test rounding to two decimal places."""
    # Passing yards: 1 yard = 0.04 points.
    # Rushing yards: 1 yard = 0.1 points.
    # Receiving yards: 1 yard = 0.1 points.
    # Receptions: 1 reception = 0.5 points.
    # Test case: 1 pass_yd (0.04) + 1 rush_yd (0.1) + 1 rec (0.5) = 0.64
    assert calculate_fantasy_points_0_5_ppr(passing_yards=1, rushing_yards=1, receptions=1) == 0.64
    # Test case: 7 pass_yds (0.28) + 3 rush_yds (0.3) + 1 rec (0.5) = 1.08
    assert calculate_fantasy_points_0_5_ppr(passing_yards=7, rushing_yards=3, receptions=1) == 1.08
    # Test case that might produce more decimals before rounding
    # 33 passing_yards = 33 * 0.04 = 1.32
    # 17 rushing_yards = 17 * 0.1 = 1.7
    # 3 receptions = 3 * 0.5 = 1.5
    # Total = 1.32 + 1.7 + 1.5 = 4.52
    assert calculate_fantasy_points_0_5_ppr(passing_yards=33, rushing_yards=17, receptions=3) == 4.52
