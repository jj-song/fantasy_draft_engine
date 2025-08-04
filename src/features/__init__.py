"""
Fantasy Football Feature Engineering Modules

This package contains advanced feature engineering modules for industry-standard
fantasy football metrics including opportunity metrics, usage analytics, and more.
"""

# Import main classes for easier access
from .opportunity_metrics import OpportunityMetricsCalculator
from .usage_analytics import UsageAnalyticsCalculator
from .schedule_strength import ScheduleStrengthCalculator

__all__ = ['OpportunityMetricsCalculator', 'UsageAnalyticsCalculator', 'ScheduleStrengthCalculator']