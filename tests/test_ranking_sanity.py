#!/usr/bin/env python3
"""
Ranking Sanity Tests - Comprehensive tests for fantasy football ranking quality.

These tests ensure that generated rankings pass basic sanity checks and 
align with fantasy football common sense and expert expectations.
"""

import sys
import os
import pandas as pd
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.ranking_validator import ranking_validator
from src.player_filter import player_filter

class TestRankingSanity:
    """Test suite for fantasy football ranking sanity checks."""
    
    @pytest.fixture
    def sample_rankings(self):
        """Create sample rankings data for testing."""
        return pd.DataFrame({
            'overall_rank': range(1, 21),
            'player_name': [
                'Christian McCaffrey', 'Saquon Barkley', 'Josh Allen', 'Justin Jefferson',
                'Tyreek Hill', 'Travis Kelce', 'Josh Jacobs', 'Patrick Mahomes',
                'Stefon Diggs', 'Davante Adams', 'Lamar Jackson', 'Cooper Kupp',
                'Derrick Henry', 'Mark Andrews', 'A.J. Brown', 'Austin Ekeler',
                'Joe Burrow', 'George Kittle', 'Kenneth Walker III', 'DK Metcalf'
            ],
            'position': [
                'RB', 'RB', 'QB', 'WR', 'WR', 'TE', 'RB', 'QB',
                'WR', 'WR', 'QB', 'WR', 'RB', 'TE', 'WR', 'RB',
                'QB', 'TE', 'RB', 'WR'
            ],
            'team': [
                'SF', 'PHI', 'BUF', 'MIN', 'MIA', 'KC', 'LV', 'KC',
                'BUF', 'LV', 'BAL', 'LA', 'TEN', 'BAL', 'PHI', 'WAS',
                'CIN', 'SF', 'SEA', 'SEA'
            ],
            'predicted_points': [
                350, 320, 380, 310, 300, 180, 300, 370,
                290, 285, 365, 280, 290, 170, 275, 280,
                360, 165, 260, 270
            ],
            'vor': [
                200, 170, 120, 156, 146, 100, 150, 110,
                136, 131, 105, 126, 140, 90, 121, 130,
                100, 85, 110, 116
            ]
        })
    
    @pytest.fixture  
    def bad_rankings(self):
        """Create obviously bad rankings for testing."""
        return pd.DataFrame({
            'overall_rank': range(1, 11),
            'player_name': [
                'Tom Brady', 'Zach Ertz', 'Sam Darnold', 'Baker Mayfield',
                'Drake London', 'Brian Thomas Jr.', 'Ray-Ray McCloud', 'Foster Moreau',
                'Jordan Love', 'Bo Nix'
            ],
            'position': ['QB', 'TE', 'QB', 'QB', 'WR', 'WR', 'WR', 'TE', 'QB', 'QB'],
            'team': ['TB', 'WAS', 'MIN', 'TB', 'ATL', 'JAX', 'ATL', 'NO', 'GB', 'DEN'],
            'predicted_points': [50, 80, 250, 220, 180, 160, 120, 90, 200, 180],
            'vor': [10, 20, 80, 60, 30, 10, -10, 10, 40, 20]
        })
    
    def test_elite_rbs_in_top_rankings(self, sample_rankings):
        """Test that elite RBs appear in top rankings."""
        top_20 = sample_rankings.head(20)
        top_20_players = set(top_20['player_name'].values)
        
        elite_rbs = {'Christian McCaffrey', 'Saquon Barkley', 'Josh Jacobs', 'Derrick Henry'}
        rbs_in_top_20 = elite_rbs.intersection(top_20_players)
        
        assert len(rbs_in_top_20) >= 3, f"Expected at least 3 elite RBs in top 20, found: {rbs_in_top_20}"
    
    def test_elite_qbs_properly_ranked(self, sample_rankings):
        """Test that elite QBs are ranked appropriately."""
        elite_qbs = {'Josh Allen', 'Patrick Mahomes', 'Lamar Jackson'}
        
        for qb in elite_qbs:
            qb_data = sample_rankings[sample_rankings['player_name'] == qb]
            assert not qb_data.empty, f"Elite QB {qb} missing from rankings"
            
            qb_rank = qb_data['overall_rank'].iloc[0]
            assert qb_rank <= 15, f"Elite QB {qb} ranked too low: #{qb_rank}"
    
    def test_no_retired_players_in_top_50(self, bad_rankings):
        """Test that retired players don't appear in top rankings."""
        validation_results = ranking_validator.validate_rankings(bad_rankings)
        
        # Should have warnings about excluded players
        warnings = validation_results['warnings']
        excluded_warnings = [w for w in warnings if 'Problematic players' in w]
        
        assert len(excluded_warnings) > 0, "Should warn about retired/problematic players in rankings"
    
    def test_position_distribution_reasonable(self, sample_rankings):
        """Test that position distribution in top rankings is reasonable."""
        top_20_positions = sample_rankings.head(20)['position'].value_counts()
        
        # Should have reasonable position distribution
        assert top_20_positions.get('RB', 0) >= 4, f"Too few RBs in top 20: {top_20_positions.get('RB', 0)}"
        assert top_20_positions.get('WR', 0) >= 5, f"Too few WRs in top 20: {top_20_positions.get('WR', 0)}"
        assert top_20_positions.get('QB', 0) >= 2, f"Too few QBs in top 20: {top_20_positions.get('QB', 0)}"
        assert top_20_positions.get('TE', 0) >= 2, f"Too few TEs in top 20: {top_20_positions.get('TE', 0)}"
        
        # Should not be dominated by one position
        assert top_20_positions.get('WR', 0) <= 10, f"Too many WRs in top 20: {top_20_positions.get('WR', 0)}"
        assert top_20_positions.get('QB', 0) <= 6, f"Too many QBs in top 20: {top_20_positions.get('QB', 0)}"
    
    def test_fantasy_points_realistic(self, sample_rankings):
        """Test that fantasy point predictions are realistic."""
        validation_results = ranking_validator.validate_rankings(sample_rankings)
        
        # Should pass basic fantasy point validation
        point_warnings = [w for w in validation_results['warnings'] if 'unrealistic' in w.lower()]
        assert len(point_warnings) == 0, f"Fantasy points should be realistic: {point_warnings}"
    
    def test_vor_calculations_make_sense(self, sample_rankings):
        """Test that VOR calculations are sensible."""
        # Top players should have positive VOR
        top_10 = sample_rankings.head(10)
        negative_vor = (top_10['vor'] <= 0).sum()
        assert negative_vor == 0, f"Top 10 players should have positive VOR, {negative_vor} don't"
        
        # VOR should generally decrease with rank
        vor_values = sample_rankings['vor'].values
        decreasing_trend = sum(vor_values[i] >= vor_values[i+1] for i in range(len(vor_values)-1))
        total_comparisons = len(vor_values) - 1
        
        # Allow some flexibility but expect general decreasing trend
        assert decreasing_trend / total_comparisons >= 0.7, "VOR should generally decrease with rank"
    
    def test_ranking_validator_catches_bad_rankings(self, bad_rankings):
        """Test that the ranking validator catches obviously bad rankings."""
        validation_results = ranking_validator.validate_rankings(bad_rankings)
        
        # Should have errors or warnings for bad rankings
        total_issues = len(validation_results['errors']) + len(validation_results['warnings'])
        assert total_issues > 0, "Validator should catch issues with bad rankings"
        
        # Should not pass overall validation
        assert validation_results['overall_status'] != 'PASS', "Bad rankings should not pass validation"
    
    def test_player_filter_removes_inactive_players(self):
        """Test that player filter removes inactive/retired players."""
        # Create test data with inactive players
        test_data = pd.DataFrame({
            'player_name': ['Josh Allen', 'Tom Brady', 'Christian McCaffrey', 'Rob Gronkowski'],
            'position': ['QB', 'QB', 'RB', 'TE'],
            'birth_date': ['1996-05-21', '1977-08-03', '1996-06-07', '1989-05-14'],
            'fantasy_points_ppr': [350, 0, 300, 0],
            'games': [16, 0, 14, 0]
        })
        
        filtered_data = player_filter.filter_active_players(test_data)
        
        # Should keep active players
        active_players = set(filtered_data['player_name'].values)
        assert 'Josh Allen' in active_players, "Should keep active star QB"
        assert 'Christian McCaffrey' in active_players, "Should keep active star RB"
        
        # Should remove inactive/retired players
        assert 'Tom Brady' not in active_players, "Should remove retired QB"
        assert 'Rob Gronkowski' not in active_players, "Should remove retired TE"
    
    def test_elite_player_validation(self):
        """Test elite player validation functionality."""
        # Create data missing elite players
        test_data = pd.DataFrame({
            'player_name': ['Random Player 1', 'Random Player 2', 'Christian McCaffrey'],
            'position': ['WR', 'QB', 'RB'],
            'fantasy_points_ppr': [100, 200, 300]
        })
        
        validation_passed = player_filter.validate_elite_players_present(test_data)
        assert not validation_passed, "Should fail validation when most elite players missing"
        
        # Create data with most elite players
        elite_data = pd.DataFrame({
            'player_name': [
                'Josh Allen', 'Patrick Mahomes', 'Lamar Jackson',
                'Christian McCaffrey', 'Saquon Barkley', 'Josh Jacobs', 
                'Tyreek Hill', 'Stefon Diggs', 'Cooper Kupp',
                'Travis Kelce', 'Mark Andrews', 'George Kittle'
            ],
            'position': ['QB', 'QB', 'QB', 'RB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'TE', 'TE'],
            'fantasy_points_ppr': [380, 370, 365, 350, 320, 300, 300, 290, 280, 180, 170, 165]
        })
        
        validation_passed = player_filter.validate_elite_players_present(elite_data)
        assert validation_passed, "Should pass validation when elite players present"
    
    def test_ranking_fixes_improve_quality(self, bad_rankings):
        """Test that ranking fixes improve ranking quality."""
        # Get initial validation
        initial_validation = ranking_validator.validate_rankings(bad_rankings)
        initial_issues = len(initial_validation['errors']) + len(initial_validation['warnings'])
        
        # Apply fixes
        fixed_rankings = ranking_validator.generate_ranking_fixes(bad_rankings, initial_validation)
        
        # Validate fixed rankings
        fixed_validation = ranking_validator.validate_rankings(fixed_rankings)
        fixed_issues = len(fixed_validation['errors']) + len(fixed_validation['warnings'])
        
        # Should have fewer issues after fixes
        assert fixed_issues < initial_issues, f"Fixes should reduce issues: {initial_issues} -> {fixed_issues}"
    
    def test_comprehensive_ranking_workflow(self):
        """Test the complete ranking validation and fixing workflow."""
        # Create problematic rankings that represent real issues
        problematic_rankings = pd.DataFrame({
            'overall_rank': range(1, 21),
            'player_name': [
                # Missing major RBs, has retired players, wrong QB order
                'Justin Jefferson', 'Drake London', 'Brian Thomas Jr.', 'Terry McLaurin',
                'Zach Ertz', 'Sam Darnold', 'Baker Mayfield', 'Tom Brady',
                'Aaron Rodgers', 'Bo Nix', 'Ray-Ray McCloud', 'Foster Moreau',
                'Josh Downs', 'Nelson Agholor', 'George Pickens', 'Theo Johnson',
                'Patrick Mahomes', 'C.J. Stroud', 'Jordan Love', 'Kenneth Walker III'
            ],
            'position': [
                'WR', 'WR', 'WR', 'WR', 'TE', 'QB', 'QB', 'QB',
                'QB', 'QB', 'WR', 'TE', 'WR', 'WR', 'WR', 'TE', 
                'QB', 'QB', 'QB', 'RB'
            ],
            'team': [
                'MIN', 'ATL', 'JAX', 'WAS', 'WAS', 'MIN', 'TB', 'TB',
                'NYJ', 'DEN', 'ATL', 'NO', 'IND', 'BAL', 'PIT', 'NYG',
                'KC', 'HOU', 'GB', 'SEA'
            ],
            'predicted_points': [
                337.6, 314.1, 315.7, 268.4, 140.2, 414.4, 424.6, 50.0,
                376.6, 403.6, 172.4, 101.0, 156.8, 153.7, 153.0, 79.2,
                324.7, 315.9, 275.4, 95.7
            ],
            'vor': [
                220.7, 192.5, 194.4, 137.6, 72.0, 78.8, 87.9, 10.0,
                44.7, 69.0, 22.4, 25.0, 3.7, 0.0, -0.8, -1.2,
                -2.0, -9.9, -46.4, 22.4
            ]
        })
        
        # Step 1: Validate problematic rankings
        validation_results = ranking_validator.validate_rankings(problematic_rankings)
        
        # Should identify major issues
        assert validation_results['overall_status'] != 'PASS', "Should identify ranking problems"
        assert len(validation_results['errors']) + len(validation_results['warnings']) > 5, "Should find multiple issues"
        
        # Step 2: Apply player filtering
        filtered_rankings = player_filter.filter_active_players(problematic_rankings)
        
        # Should remove some problematic players
        assert len(filtered_rankings) < len(problematic_rankings), "Should remove some players"
        assert 'Tom Brady' not in filtered_rankings['player_name'].values, "Should remove retired players"
        
        # Step 3: Apply ranking fixes
        fixed_rankings = ranking_validator.generate_ranking_fixes(filtered_rankings, validation_results)
        
        # Step 4: Validate fixed rankings
        final_validation = ranking_validator.validate_rankings(fixed_rankings)
        
        # Should have improvement
        initial_issues = len(validation_results['errors']) + len(validation_results['warnings'])
        final_issues = len(final_validation['errors']) + len(final_validation['warnings'])
        
        assert final_issues < initial_issues, f"Should improve ranking quality: {initial_issues} -> {final_issues}"
        
        # Should have more reasonable position distribution
        top_20_positions = fixed_rankings.head(20)['position'].value_counts()
        assert top_20_positions.get('RB', 0) >= 3, "Should have more RBs after fixes"


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])