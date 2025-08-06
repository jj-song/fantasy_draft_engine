"""
League-specific configuration for the Fantasy Draft Engine.

This module contains all configuration related to fantasy league settings,
scoring systems, and Value Over Replacement calculations.
"""

from typing import Dict, Any, Union
from .base_config import BaseConfig


class LeagueConfig(BaseConfig):
    """
    Configuration for fantasy league settings and scoring.
    
    This class manages league format, scoring systems, VOR calculations,
    and position-specific adjustments for draft valuations.
    """
    
    def _initialize(self) -> None:
        """Initialize league configuration values."""
        
        # Basic league settings
        self.league_size = 12
        self.ppr_scoring = 0.5  # Half-point PPR
        
        # Roster composition (standard fantasy football)
        self.roster_settings = {
            'qb_starters': 1,          # QBs started per team per week
            'rb_starters': 2,          # RBs started per team per week  
            'wr_starters': 2,          # WRs started per team per week
            'te_starters': 1,          # TEs started per team per week
            'flex_spots': 1,           # FLEX positions (RB/WR/TE)
            'superflex': False,        # Whether league has superflex (QB eligible for FLEX)
            'kicker_spots': 1,         # Kicker spots
            'dst_spots': 1,            # Defense/Special Teams spots
            'bench_spots': 6,          # Bench spots per team
            'ir_spots': 1              # Injured Reserve spots
        }
        
        # VOR (Value Over Replacement) settings
        # Replacement levels based on starter requirements
        self.vor_replacement_levels = {
            'QB': 13,   # QB13 (12 teams × 1 starter + bench depth)
            'RB': 30,   # RB30 (12 teams × 2.5 starters, accounting for FLEX usage)  
            'WR': 30,   # WR30 (12 teams × 2.5 starters, accounting for FLEX usage)
            'TE': 13,   # TE13 (12 teams × 1 starter + minimal FLEX usage)
            'K': 12,    # K12 (12 teams × 1 starter)
            'DST': 12,  # DST12 (12 teams × 1 starter)
        }
        
        # Positional scarcity multipliers based on fantasy football research
        # Account for starter requirements, injury risk, and positional depth
        self.vor_scarcity_multipliers = {
            'RB': 1.5,   # Highest scarcity: injury risk, limited elite tier
            'TE': 1.2,   # Top-heavy position with moderate scarcity premium
            'WR': 1.2,   # Moderate scarcity: need multiple starters, deeper talent pool
            'QB': 0.9,   # Lowest scarcity: deepest position, most predictable
            'K': 0.8,    # Very replaceable position
            'DST': 0.8,  # Very replaceable position
        }
        
        # Draft strategy settings
        self.draft_settings = {
            'total_rounds': 15,        # Total draft rounds
            'draft_time_limit': 90,    # Seconds per pick
            'allow_trades': True,      # Whether trades are allowed
            'trade_deadline_week': 10, # Week after which trades are not allowed
            'waiver_type': 'faab',     # 'waab' or 'priority'
            'faab_budget': 100         # Free Agent Acquisition Budget
        }
        
        # Playoff settings
        self.playoff_settings = {
            'playoff_teams': 6,        # Number of teams that make playoffs
            'playoff_start_week': 15,  # Week playoffs start
            'championship_week': 17,   # Week of championship game
            'playoff_reseeding': False # Whether to reseed after each round
        }
        
        # Auction settings (for auction drafts)
        self.auction_settings = {
            'total_budget': 200,       # Total auction budget per team
            'min_bid': 1,              # Minimum bid amount
            'bid_increment': 1,        # Minimum bid increment
            'starter_budget_pct': 0.88, # ~88% of budget for starters
            'bench_budget_pct': 0.12,   # ~12% of budget for bench
        }
        
        # Environment-specific overrides
        if self.environment == 'test':
            self._apply_test_overrides()
        elif self.environment == 'production':
            self._apply_production_overrides()
    
    def _apply_test_overrides(self) -> None:
        """Apply test-specific configuration overrides."""
        self.league_size = 8  # Smaller league for tests
        self.draft_settings['total_rounds'] = 10
        self.roster_settings['bench_spots'] = 4
        
        # Adjust VOR replacement levels for smaller league
        self.vor_replacement_levels.update({
            'QB': 9,   # 8 teams + 1
            'RB': 20,  # 8 teams × 2.5
            'WR': 20,  # 8 teams × 2.5
            'TE': 9,   # 8 teams + 1
            'K': 8,    # 8 teams
            'DST': 8,  # 8 teams
        })
    
    def _apply_production_overrides(self) -> None:
        """Apply production-specific configuration overrides."""
        # Production might use more conservative settings
        self.draft_settings['draft_time_limit'] = 120  # Longer time limit
        self.auction_settings['total_budget'] = 250    # Higher budget
    
    def _validate(self) -> None:
        """Validate league configuration values."""
        
        # Validate required fields
        required_fields = [
            'league_size', 'ppr_scoring', 'roster_settings', 
            'vor_replacement_levels', 'vor_scarcity_multipliers'
        ]
        self.validate_required_fields(required_fields)
        
        # Validate types
        type_mapping = {
            'league_size': int,
            'ppr_scoring': (int, float),
            'roster_settings': dict,
            'vor_replacement_levels': dict,
            'vor_scarcity_multipliers': dict,
            'draft_settings': dict,
            'playoff_settings': dict,
            'auction_settings': dict
        }
        self.validate_types(type_mapping)
        
        # Validate ranges
        range_mapping = {
            'league_size': (6, 20),          # Reasonable league sizes
            'ppr_scoring': (0.0, 1.0),       # PPR scoring multiplier
            'draft_settings.total_rounds': (10, 25),
            'draft_settings.draft_time_limit': (30, 300),
            'playoff_settings.playoff_teams': (2, 12),
            'playoff_settings.playoff_start_week': (13, 16),
            'playoff_settings.championship_week': (16, 18),
            'auction_settings.total_budget': (100, 1000),
            'auction_settings.min_bid': (1, 10)
        }
        self.validate_ranges(range_mapping)
        
        # Custom validations
        self._validate_roster_settings()
        self._validate_vor_settings()
        self._validate_playoff_settings()
    
    def _validate_roster_settings(self) -> None:
        """Validate roster composition settings."""
        required_roster_keys = [
            'qb_starters', 'rb_starters', 'wr_starters', 'te_starters',
            'flex_spots', 'bench_spots'
        ]
        
        for key in required_roster_keys:
            if key not in self.roster_settings:
                raise ValueError(f"Missing required roster setting: {key}")
            
            value = self.roster_settings[key]
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"Roster setting {key} must be non-negative integer")
        
        # Validate total roster size is reasonable
        total_starters = (
            self.roster_settings['qb_starters'] +
            self.roster_settings['rb_starters'] + 
            self.roster_settings['wr_starters'] +
            self.roster_settings['te_starters'] +
            self.roster_settings['flex_spots'] +
            self.roster_settings.get('kicker_spots', 0) +
            self.roster_settings.get('dst_spots', 0)
        )
        
        total_roster = total_starters + self.roster_settings['bench_spots']
        
        if total_roster < 10 or total_roster > 25:
            raise ValueError(f"Total roster size ({total_roster}) is unreasonable")
    
    def _validate_vor_settings(self) -> None:
        """Validate VOR calculation settings."""
        required_positions = ['QB', 'RB', 'WR', 'TE']
        
        # Check replacement levels
        for pos in required_positions:
            if pos not in self.vor_replacement_levels:
                raise ValueError(f"Missing VOR replacement level for {pos}")
            
            level = self.vor_replacement_levels[pos]
            if not isinstance(level, int) or level < 1:
                raise ValueError(f"VOR replacement level for {pos} must be positive integer")
        
        # Check scarcity multipliers
        for pos in required_positions:
            if pos not in self.vor_scarcity_multipliers:
                raise ValueError(f"Missing VOR scarcity multiplier for {pos}")
            
            multiplier = self.vor_scarcity_multipliers[pos]
            if not isinstance(multiplier, (int, float)) or multiplier <= 0:
                raise ValueError(f"VOR scarcity multiplier for {pos} must be positive number")
    
    def _validate_playoff_settings(self) -> None:
        """Validate playoff settings."""
        playoff_teams = self.playoff_settings['playoff_teams']
        if playoff_teams >= self.league_size:
            raise ValueError("Number of playoff teams must be less than league size")
        
        start_week = self.playoff_settings['playoff_start_week']
        championship_week = self.playoff_settings['championship_week']
        
        if championship_week <= start_week:
            raise ValueError("Championship week must be after playoff start week")
    
    def get_scoring_system(self) -> str:
        """
        Get the scoring system name based on PPR setting.
        
        Returns:
            Scoring system name ('Standard', 'HalfPPR', or 'PPR')
        """
        if self.ppr_scoring == 0:
            return 'Standard'
        elif self.ppr_scoring == 0.5:
            return 'HalfPPR'
        elif self.ppr_scoring == 1.0:
            return 'PPR'
        else:
            return f'Custom_{self.ppr_scoring}PPR'
    
    def get_starter_count(self, position: str) -> int:
        """
        Get number of starters for a position per team.
        
        Args:
            position: Player position
            
        Returns:
            Number of starters for that position
        """
        position_mapping = {
            'QB': 'qb_starters',
            'RB': 'rb_starters', 
            'WR': 'wr_starters',
            'TE': 'te_starters',
            'K': 'kicker_spots',
            'DST': 'dst_spots'
        }
        
        key = position_mapping.get(position.upper())
        if key and key in self.roster_settings:
            return self.roster_settings[key]
        else:
            return 0
    
    def get_total_starters_in_league(self, position: str) -> int:
        """
        Get total number of starters for a position across entire league.
        
        Args:
            position: Player position
            
        Returns:
            Total starters across all teams
        """
        per_team = self.get_starter_count(position)
        
        # Add FLEX consideration for RB/WR/TE
        if position.upper() in ['RB', 'WR', 'TE']:
            # Estimate FLEX usage (roughly split between RB/WR/TE)
            flex_usage = self.roster_settings.get('flex_spots', 0) / 3
            per_team += flex_usage
        
        return int(per_team * self.league_size)
    
    def calculate_replacement_level(self, position: str) -> int:
        """
        Calculate replacement level for a position based on league settings.
        
        Args:
            position: Player position
            
        Returns:
            Replacement level (rank where replacement players start)
        """
        if position.upper() in self.vor_replacement_levels:
            return self.vor_replacement_levels[position.upper()]
        
        # Calculate based on roster requirements if not explicitly set
        total_starters = self.get_total_starters_in_league(position)
        bench_depth = max(1, total_starters * 0.1)  # 10% bench depth
        
        return int(total_starters + bench_depth)
    
    def get_scarcity_multiplier(self, position: str) -> float:
        """
        Get scarcity multiplier for a position.
        
        Args:
            position: Player position
            
        Returns:
            Scarcity multiplier value
        """
        return self.vor_scarcity_multipliers.get(position.upper(), 1.0)
    
    def get_auction_values_config(self) -> Dict[str, Union[int, float]]:
        """
        Get configuration for auction value calculations.
        
        Returns:
            Dictionary with auction value settings
        """
        return {
            'total_budget': self.auction_settings['total_budget'],
            'starter_budget': self.auction_settings['total_budget'] * self.auction_settings['starter_budget_pct'],
            'bench_budget': self.auction_settings['total_budget'] * self.auction_settings['bench_budget_pct'],
            'min_bid': self.auction_settings['min_bid'],
            'league_size': self.league_size
        }
    
    def is_superflex_league(self) -> bool:
        """Check if this is a superflex league."""
        return self.roster_settings.get('superflex', False)
    
    def get_draft_rounds(self) -> int:
        """Get total number of draft rounds."""
        return self.draft_settings.get('total_rounds', 15)
    
    def get_league_summary(self) -> Dict[str, Any]:
        """
        Get a summary of key league settings.
        
        Returns:
            Dictionary with key league configuration
        """
        return {
            'league_size': self.league_size,
            'scoring_system': self.get_scoring_system(),
            'total_roster_spots': sum([
                self.roster_settings.get('qb_starters', 0),
                self.roster_settings.get('rb_starters', 0),
                self.roster_settings.get('wr_starters', 0), 
                self.roster_settings.get('te_starters', 0),
                self.roster_settings.get('flex_spots', 0),
                self.roster_settings.get('kicker_spots', 0),
                self.roster_settings.get('dst_spots', 0),
                self.roster_settings.get('bench_spots', 0)
            ]),
            'superflex': self.is_superflex_league(),
            'draft_rounds': self.get_draft_rounds(),
            'auction_budget': self.auction_settings.get('total_budget', 0)
        }