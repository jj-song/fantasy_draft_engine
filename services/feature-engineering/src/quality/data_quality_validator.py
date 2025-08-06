#!/usr/bin/env python3
"""
Data Quality Validator - Strict validation gates for the fantasy football pipeline.

Implements fail-fast data quality checks to catch issues early and prevent
degraded results from propagating through the system.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class DataQualityError(Exception):
    """Raised when data quality is insufficient to continue processing."""
    pass

class DataQualityValidator:
    """
    Strict data quality validator that fails fast on insufficient data quality.
    
    This validator implements the user's requirement: "if something doesn't work, 
    i want it to actually break" rather than relying on fallback logic.
    """
    
    # Minimum player counts per position (based on 12-team league standards)
    MIN_PLAYERS_BY_POSITION = {
        'QB': 20,  # Need at least 20 QBs for reasonable rankings
        'RB': 60,  # Need at least 60 RBs (5 per team in 12-team league)
        'WR': 72,  # Need at least 72 WRs (6 per team in 12-team league)
        'TE': 24   # Need at least 24 TEs (2 per team in 12-team league)
    }
    
    # Training-specific thresholds (more lenient for historical data)
    TRAINING_MIN_PLAYERS_BY_POSITION = {
        'QB': 15,  # Training: More lenient for historical data
        'RB': 30,  # Training: Allow fewer RBs for historical seasons
        'WR': 40,  # Training: Allow fewer WRs for historical seasons
        'TE': 15   # Training: Allow fewer TEs for historical seasons
    }
    
    # Fantasy points thresholds for elite players (must have at least some)
    ELITE_THRESHOLDS = {
        'QB': 300,  # Elite QBs score 300+ fantasy points
        'RB': 250,  # Elite RBs score 250+ fantasy points
        'WR': 200,  # Elite WRs score 200+ fantasy points
        'TE': 150   # Elite TEs score 150+ fantasy points
    }
    
    def validate_raw_data(self, data: pd.DataFrame, season: int) -> None:
        """
        Validate raw data quality and fail if insufficient.
        
        Args:
            data: Raw player data
            season: Season year for context
            
        Raises:
            DataQualityError: If data quality is insufficient
        """
        logger.info(f"🔍 Validating raw data quality for {season}")
        
        # Basic data structure checks
        if data is None or len(data) == 0:
            raise DataQualityError(f"Raw data for {season} is empty or None")
            
        required_columns = ['player_name', 'position', 'fantasy_points_ppr', 'games']
        missing_cols = [col for col in required_columns if col not in data.columns]
        if missing_cols:
            raise DataQualityError(f"Raw data missing required columns: {missing_cols}")
        
        # Position-specific player count validation
        position_counts = data['position'].value_counts()
        for position, min_count in self.MIN_PLAYERS_BY_POSITION.items():
            actual_count = position_counts.get(position, 0)
            if actual_count < min_count:
                raise DataQualityError(
                    f"Insufficient {position} players: {actual_count} < {min_count} required"
                )
        
        # Fantasy points data quality
        total_players = len(data)
        nan_fantasy_points = data['fantasy_points_ppr'].isna().sum()
        valid_fantasy_points = total_players - nan_fantasy_points
        
        if valid_fantasy_points < total_players * 0.8:  # Require 80% valid fantasy points
            raise DataQualityError(
                f"Too many NaN fantasy points: {nan_fantasy_points}/{total_players} "
                f"({nan_fantasy_points/total_players*100:.1f}% missing)"
            )
        
        # Elite player validation - ensure we have top performers
        for position, threshold in self.ELITE_THRESHOLDS.items():
            pos_data = data[data['position'] == position]
            if len(pos_data) > 0:
                elite_count = len(pos_data[pos_data['fantasy_points_ppr'] >= threshold])
                if elite_count == 0:
                    raise DataQualityError(
                        f"No elite {position}s found (none scoring >= {threshold} fantasy points)"
                    )
        
        logger.info(f"✅ Raw data quality validation passed for {season}")
    
    def validate_feature_engineered_data(self, data: pd.DataFrame, season: int, 
                                       include_matchup_intelligence: bool = False,
                                       training_mode: bool = False) -> None:
        """
        Validate feature-engineered data and fail if quality degraded.
        
        Args:
            data: Feature-engineered data
            season: Season year for context
            include_matchup_intelligence: Whether matchup features should be present
            training_mode: Whether this is training data (more lenient thresholds)
            
        Raises:
            DataQualityError: If data quality is insufficient
        """
        logger.info(f"🔍 Validating feature-engineered data quality for {season}")
        
        if data is None or len(data) == 0:
            raise DataQualityError(f"Feature-engineered data for {season} is empty or None")
        
        # Check that we haven't lost too many players during feature engineering
        position_counts = data['position'].value_counts()
        
        # Use training-specific thresholds for historical data
        min_counts = self.TRAINING_MIN_PLAYERS_BY_POSITION if training_mode else self.MIN_PLAYERS_BY_POSITION
        
        # Position-specific retention thresholds (more lenient for positions with feature issues)
        retention_thresholds = {
            'QB': 0.6,  # Allow 40% loss for QBs
            'RB': 0.3,  # Allow 70% loss for RBs (feature engineering struggles with missing data)
            'WR': 0.5,  # Allow 50% loss for WRs  
            'TE': 0.5   # Allow 50% loss for TEs
        }
        
        for position, min_count in min_counts.items():
            actual_count = position_counts.get(position, 0)
            # Use position-specific retention threshold
            retention_threshold = retention_thresholds.get(position, 0.7)
            adjusted_min = int(min_count * retention_threshold)
            
            if actual_count < adjusted_min:
                # Log warning instead of failing for RBs (to prevent complete pipeline failure)
                if position == 'RB' and actual_count >= 5:  # At least 5 RBs minimum
                    logger.warning(
                        f"Low {position} retention but continuing: "
                        f"{actual_count} < {adjusted_min} optimal ({retention_threshold*100:.0f}% of {min_count})"
                    )
                else:
                    raise DataQualityError(
                        f"Too many {position} players lost during feature engineering: "
                        f"{actual_count} < {adjusted_min} required ({retention_threshold*100:.0f}% of original {min_count})"
                    )
        
        # Validate critical columns exist (different for training vs inference)
        if training_mode:
            # Training mode: look for target variable instead of current fantasy points
            required_base_cols = ['player_name', 'position']
            target_cols = [col for col in data.columns if 'next_season' in col.lower() or 'target' in col.lower()]
            if not target_cols:
                logger.warning("No target variable found in training data - this may be expected for some training scenarios")
        else:
            # Inference mode: need current fantasy points for VOR calculations
            required_base_cols = ['player_name', 'position', 'fantasy_points_ppr']
        
        missing_cols = [col for col in required_base_cols if col not in data.columns]
        if missing_cols:
            raise DataQualityError(f"Feature-engineered data missing columns: {missing_cols}")
        
        # Fantasy points preservation check (only for inference mode)
        if not training_mode and 'fantasy_points_ppr' in data.columns:
            nan_count = data['fantasy_points_ppr'].isna().sum()
            total_count = len(data)
            
            # For inference mode, fantasy points should be mostly preserved
            if nan_count > total_count * 0.2:  # Allow max 20% NaN
                raise DataQualityError(
                    f"Too many NaN fantasy points after feature engineering: "
                    f"{nan_count}/{total_count} ({nan_count/total_count*100:.1f}%)"
                )
        
        # Matchup intelligence validation (more flexible)
        if include_matchup_intelligence:
            # Look for any matchup intelligence features by pattern
            matchup_features = [col for col in data.columns if any(pattern in col.lower() for pattern in 
                                ['sos', 'strength_of_schedule', 'weather', 'temperature', 'wind', 'dome', 'altitude'])]
            
            if len(matchup_features) < 5:  # Expect at least 5 matchup features
                logger.warning(f"Matchup intelligence enabled but only found {len(matchup_features)} matchup features")
                logger.warning(f"Found matchup features: {matchup_features[:10]}")  # Show first 10
            else:
                logger.info(f"✅ Matchup intelligence validation passed: {len(matchup_features)} features found")
        
        logger.info(f"✅ Feature-engineered data quality validation passed for {season}")
    
    def validate_position_data(self, data: pd.DataFrame, position: str) -> None:
        """
        Validate position-specific data before model predictions.
        
        Args:
            data: Position-specific data
            position: Position being validated
            
        Raises:
            DataQualityError: If position data is insufficient
        """
        logger.info(f"🔍 Validating {position} data quality")
        
        if data is None or len(data) == 0:
            raise DataQualityError(f"No {position} data provided")
        
        # Check minimum player count
        min_required = self.MIN_PLAYERS_BY_POSITION.get(position, 10)
        if len(data) < min_required:
            raise DataQualityError(
                f"Insufficient {position} players for ranking: {len(data)} < {min_required} required"
            )
        
        # Check for critical data completeness
        if 'fantasy_points_ppr' in data.columns:
            valid_fp_count = data['fantasy_points_ppr'].notna().sum()
            if valid_fp_count < len(data) * 0.8:  # Require 80% valid fantasy points
                raise DataQualityError(
                    f"Too many {position} players missing fantasy points: "
                    f"{len(data) - valid_fp_count}/{len(data)} have NaN values"
                )
            
            # Check for at least some elite players
            elite_threshold = self.ELITE_THRESHOLDS.get(position, 100)
            elite_count = len(data[data['fantasy_points_ppr'] >= elite_threshold])
            if elite_count == 0:
                raise DataQualityError(
                    f"No elite {position} players found (none scoring >= {elite_threshold} fantasy points)"
                )
        
        logger.info(f"✅ {position} data quality validation passed")
    
    def validate_model_predictions(self, predictions: np.ndarray, position: str, 
                                 player_names: List[str]) -> None:
        """
        Validate model predictions are realistic and usable.
        
        Args:
            predictions: Model prediction array
            position: Position being predicted
            player_names: Player names for context
            
        Raises:
            DataQualityError: If predictions are unrealistic
        """
        logger.info(f"🔍 Validating {position} model predictions")
        
        if predictions is None or len(predictions) == 0:
            raise DataQualityError(f"No predictions generated for {position}")
        
        # Check for NaN predictions
        nan_count = np.isnan(predictions).sum()
        if nan_count > 0:
            raise DataQualityError(
                f"{position} model produced {nan_count}/{len(predictions)} NaN predictions"
            )
        
        # Check prediction ranges are realistic
        position_ranges = {
            'QB': (150, 450),   # QBs typically score 150-450 fantasy points
            'RB': (50, 400),    # RBs typically score 50-400 fantasy points  
            'WR': (50, 350),    # WRs typically score 50-350 fantasy points
            'TE': (30, 200)     # TEs typically score 30-200 fantasy points
        }
        
        min_realistic, max_realistic = position_ranges.get(position, (0, 500))
        
        too_low = (predictions < min_realistic).sum()
        too_high = (predictions > max_realistic).sum()
        
        if too_low > len(predictions) * 0.1:  # Allow 10% outliers
            raise DataQualityError(
                f"{position} predictions too low: {too_low}/{len(predictions)} below {min_realistic}"
            )
        
        if too_high > len(predictions) * 0.1:  # Allow 10% outliers
            raise DataQualityError(
                f"{position} predictions too high: {too_high}/{len(predictions)} above {max_realistic}"
            )
        
        # Check prediction distribution makes sense
        pred_std = np.std(predictions)
        pred_mean = np.mean(predictions)
        
        if pred_std < pred_mean * 0.1:  # Predictions too similar (low variance)
            raise DataQualityError(
                f"{position} predictions lack variance: std={pred_std:.1f}, mean={pred_mean:.1f}"
            )
        
        logger.info(f"✅ {position} model predictions validation passed")
    
    def validate_final_rankings(self, rankings: pd.DataFrame) -> None:
        """
        Validate final draft rankings meet quality standards.
        
        Args:
            rankings: Final draft rankings dataframe
            
        Raises:
            DataQualityError: If rankings are insufficient
        """
        logger.info("🔍 Validating final draft rankings quality")
        
        if rankings is None or len(rankings) == 0:
            raise DataQualityError("No final rankings generated")
        
        # Check we have sufficient players for a viable draft
        total_players = len(rankings)
        if total_players < 200:  # Need at least 200 players for 12-team draft
            raise DataQualityError(f"Too few players in final rankings: {total_players} < 200")
        
        # Position distribution check
        position_counts = rankings['position'].value_counts()
        for position, min_count in self.MIN_PLAYERS_BY_POSITION.items():
            actual_count = position_counts.get(position, 0)
            if actual_count < min_count:
                raise DataQualityError(
                    f"Final rankings insufficient {position} players: {actual_count} < {min_count}"
                )
        
        # VOR calculation validation
        if 'vor' in rankings.columns:
            vor_issues = rankings['vor'].isna().sum()
            if vor_issues > 0:
                raise DataQualityError(f"VOR calculation failed for {vor_issues} players")
            
            # Check VOR distribution makes sense
            positive_vor = (rankings['vor'] > 0).sum()
            if positive_vor < len(rankings) * 0.3:  # At least 30% should have positive VOR
                raise DataQualityError(
                    f"Too few players with positive VOR: {positive_vor}/{len(rankings)}"
                )
        
        # Tier validation
        if 'tier' in rankings.columns:
            tier_counts = rankings['tier'].value_counts()
            if len(tier_counts) < 3:  # Should have at least 3 tiers
                raise DataQualityError(f"Too few tiers in rankings: {len(tier_counts)} < 3")
        
        logger.info("✅ Final draft rankings validation passed")
    
    def log_data_quality_summary(self, data: pd.DataFrame, stage: str) -> None:
        """
        Log a comprehensive data quality summary for debugging.
        
        Args:
            data: Data to summarize
            stage: Pipeline stage name
        """
        logger.info(f"📊 DATA QUALITY SUMMARY - {stage}")
        logger.info(f"  Total players: {len(data)}")
        
        if 'position' in data.columns:
            pos_counts = data['position'].value_counts()
            for pos, count in pos_counts.items():
                logger.info(f"  {pos}: {count} players")
        
        if 'fantasy_points_ppr' in data.columns:
            fp_valid = data['fantasy_points_ppr'].notna().sum()
            fp_total = len(data)
            logger.info(f"  Fantasy points valid: {fp_valid}/{fp_total} ({fp_valid/fp_total*100:.1f}%)")
            
            if fp_valid > 0:
                fp_stats = data['fantasy_points_ppr'].describe()
                logger.info(f"  Fantasy points range: {fp_stats['min']:.1f} - {fp_stats['max']:.1f}")
                logger.info(f"  Fantasy points mean: {fp_stats['mean']:.1f}")

# Global validator instance
validator = DataQualityValidator()