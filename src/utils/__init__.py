# Direct import from utils.py to avoid circular imports
import os
import sys
import importlib.util
from pathlib import Path

# Add the src directory to the path
src_dir = Path(__file__).parent.parent
utils_file = src_dir / 'utils.py'

if utils_file.exists():
    # Execute the utils.py file directly
    spec = importlib.util.spec_from_file_location("src_utils", utils_file)
    src_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(src_utils)
    
    # Import the specific function
    calculate_fantasy_points_0_5_ppr = src_utils.calculate_fantasy_points_0_5_ppr
    __all__ = ['calculate_fantasy_points_0_5_ppr']
else:
    __all__ = []