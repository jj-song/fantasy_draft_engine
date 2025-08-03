# src/utils.py

def calculate_fantasy_points_0_5_ppr(
    passing_yards: float = 0,
    passing_tds: int = 0,
    interceptions: int = 0,
    rushing_yards: float = 0,
    rushing_tds: int = 0,
    receptions: int = 0,
    receiving_yards: float = 0,
    receiving_tds: int = 0,
    fumbles_lost: int = 0,
    two_pt_conversions: int = 0,
) -> float:
    """
    Calculates fantasy points for a player based on 0.5 PPR scoring rules.

    Args:
        passing_yards (float): Player's passing yards.
        passing_tds (int): Player's passing touchdowns.
        interceptions (int): Player's interceptions thrown.
        rushing_yards (float): Player's rushing yards.
        rushing_tds (int): Player's rushing touchdowns.
        receptions (int): Player's receptions.
        receiving_yards (float): Player's receiving yards.
        receiving_tds (int): Player's receiving touchdowns.
        fumbles_lost (int): Player's fumbles lost.
        two_pt_conversions (int): Player's 2-point conversions scored/thrown.

    Returns:
        float: Total fantasy points calculated.
    """
    points = 0.0

    # Passing
    points += passing_yards * 0.04
    points += passing_tds * 4
    points -= interceptions * 2

    # Rushing
    points += rushing_yards * 0.1
    points += rushing_tds * 6

    # Receiving
    points += receptions * 0.5
    points += receiving_yards * 0.1
    points += receiving_tds * 6

    # Other
    points -= fumbles_lost * 2
    points += two_pt_conversions * 2

    return round(points, 2) # Round to 2 decimal places for consistency
