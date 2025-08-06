"""
Cheatsheet Generator - Export rankings in various formats.

This module provides export functionality including:
- CSV export for spreadsheet analysis
- PDF cheatsheet generation
- JSON export for API consumption
- Printable cheatsheet formatting
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json
import sys

# Add paths for accessing services
services_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(services_root))

logger = logging.getLogger(__name__)

class CheatsheetGenerator:
    """
    Generate and export fantasy football cheatsheets in various formats.
    
    Supports CSV, JSON, PDF, and printable text formats for draft preparation.
    """
    
    def __init__(self):
        """Initialize cheatsheet generator."""
        # Simple solution: always use /app/data/draft_lists in Docker
        self.output_dir = Path("/app/data/draft_lists")
        
        # Create directory with full path creation
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Format templates
        self.format_handlers = {
            "csv": self._export_csv,
            "json": self._export_json,
            "pdf": self._export_pdf,
            "cheatsheet": self._export_cheatsheet,
            "txt": self._export_text
        }
        
        logger.info("📋 Cheatsheet Generator initialized")
    
    async def export_rankings(self, format: str = "csv", positions: Optional[List[str]] = None,
                            top_n: Optional[int] = None, include_tiers: bool = True) -> Dict[str, Any]:
        """
        Export rankings in specified format.
        
        Args:
            format: Export format (csv, json, pdf, cheatsheet, txt)
            positions: Positions to include (None for all)
            top_n: Number of top players to include (None for all)
            include_tiers: Whether to include tier information
            
        Returns:
            Dictionary containing export results
        """
        try:
            logger.info(f"📤 Exporting rankings in {format} format...")
            
            # Get ranking data
            ranking_data = await self._get_ranking_data(positions, top_n, include_tiers)
            
            if not ranking_data or len(ranking_data) == 0:
                return {
                    "success": False,
                    "error": "No ranking data available for export",
                    "format": format
                }
            
            # Get format handler
            handler = self.format_handlers.get(format.lower())
            if not handler:
                return {
                    "success": False,
                    "error": f"Unsupported format: {format}. Supported formats: {list(self.format_handlers.keys())}",
                    "format": format
                }
            
            # Export using appropriate handler
            export_result = await handler(ranking_data, positions, top_n, include_tiers)
            
            logger.info(f"✅ Rankings exported successfully in {format} format")
            return export_result
        
        except Exception as e:
            logger.error(f"Failed to export rankings in {format} format: {e}")
            return {
                "success": False,
                "error": str(e),
                "format": format
            }
    
    async def _get_ranking_data(self, positions: Optional[List[str]], top_n: Optional[int], 
                              include_tiers: bool) -> List[Dict[str, Any]]:
        """Get ranking data for export."""
        try:
            # This would typically get data from cached rankings or VOR calculator
            # For now, we'll generate sample ranking data
            logger.info("📊 Loading ranking data for export...")
            
            # Generate sample data (in production this would come from actual rankings)
            ranking_data = await self._generate_sample_rankings(positions or ["QB", "RB", "WR", "TE"])
            
            # Apply filters
            if top_n:
                ranking_data = ranking_data[:top_n]
            
            # Add tier information if requested
            if include_tiers:
                ranking_data = self._add_tier_information(ranking_data)
            
            logger.info(f"✅ Loaded {len(ranking_data)} players for export")
            return ranking_data
        
        except Exception as e:
            logger.error(f"Failed to get ranking data: {e}")
            return []
    
    async def _generate_sample_rankings(self, positions: List[str]) -> List[Dict[str, Any]]:
        """Generate sample ranking data."""
        all_players = []
        
        # Point ranges by position
        point_ranges = {
            "QB": (8, 35, 24),   # (min, max, count)
            "RB": (3, 25, 60),
            "WR": (2, 22, 72),
            "TE": (1, 18, 20)
        }
        
        overall_rank = 1
        
        for position in positions:
            min_pts, max_pts, count = point_ranges.get(position, (5, 20, 30))
            
            for i in range(count):
                # Create decreasing point values
                predicted_points = max_pts - (i * (max_pts - min_pts) / count)
                predicted_points += np.random.normal(0, 0.5)  # Add slight variation
                predicted_points = max(min_pts, predicted_points)
                
                # Calculate VOR (simplified)
                replacement_levels = {"QB": 12, "RB": 8, "WR": 6, "TE": 4}
                replacement_points = replacement_levels.get(position, 8)
                vor_value = predicted_points - replacement_points
                
                player = {
                    "overall_rank": overall_rank,
                    "position_rank": i + 1,
                    "player_name": f"{position} Player {i+1}",
                    "team": f"TEAM{(i % 32) + 1}",
                    "position": position,
                    "predicted_points": round(predicted_points, 1),
                    "vor_value": round(vor_value, 1),
                    "adp": overall_rank + np.random.randint(-5, 6),  # Mock ADP
                    "bye_week": (i % 14) + 4  # Weeks 4-17
                }
                
                all_players.append(player)
                overall_rank += 1
        
        # Sort by VOR value (descending)
        all_players.sort(key=lambda x: x["vor_value"], reverse=True)
        
        # Update overall ranks after sorting
        for i, player in enumerate(all_players):
            player["overall_rank"] = i + 1
        
        return all_players
    
    def _add_tier_information(self, ranking_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add tier information to ranking data."""
        try:
            # Group by position and assign tiers
            for position in ["QB", "RB", "WR", "TE"]:
                position_players = [p for p in ranking_data if p["position"] == position]
                
                if not position_players:
                    continue
                
                # Sort by VOR for tier assignment
                position_players.sort(key=lambda x: x["vor_value"], reverse=True)
                
                # Assign tiers based on VOR gaps
                tiers = self._calculate_tiers_by_vor_gaps(position_players)
                
                # Update original data with tier information
                for player, tier in zip(position_players, tiers):
                    player["tier"] = tier
            
            return ranking_data
        
        except Exception as e:
            logger.error(f"Failed to add tier information: {e}")
            return ranking_data
    
    def _calculate_tiers_by_vor_gaps(self, players: List[Dict[str, Any]]) -> List[int]:
        """Calculate tiers based on VOR value gaps."""
        if len(players) <= 1:
            return [1] * len(players)
        
        vor_values = [p["vor_value"] for p in players]
        gaps = [vor_values[i] - vor_values[i+1] for i in range(len(vor_values)-1)]
        
        # Find significant gaps (above mean + std)
        mean_gap = np.mean(gaps)
        std_gap = np.std(gaps)
        threshold = mean_gap + std_gap
        
        tiers = [1]  # First player is always tier 1
        current_tier = 1
        
        for i, gap in enumerate(gaps):
            if gap > threshold:
                current_tier += 1
            tiers.append(current_tier)
        
        return tiers
    
    async def _export_csv(self, data: List[Dict[str, Any]], positions: Optional[List[str]], 
                        top_n: Optional[int], include_tiers: bool) -> Dict[str, Any]:
        """Export rankings to CSV format."""
        try:
            df = pd.DataFrame(data)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fantasy_rankings_{timestamp}.csv"
            filepath = self.output_dir / filename
            
            # Export to CSV
            df.to_csv(filepath, index=False)
            
            return {
                "success": True,
                "format": "csv",
                "filepath": str(filepath),
                "filename": filename,
                "total_players": len(data),
                "file_size": filepath.stat().st_size
            }
        
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _export_json(self, data: List[Dict[str, Any]], positions: Optional[List[str]],
                         top_n: Optional[int], include_tiers: bool) -> Dict[str, Any]:
        """Export rankings to JSON format."""
        try:
            # Create export structure
            export_data = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_players": len(data),
                    "positions": positions,
                    "top_n": top_n,
                    "includes_tiers": include_tiers
                },
                "rankings": data
            }
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fantasy_rankings_{timestamp}.json"
            filepath = self.output_dir / filename
            
            # Export to JSON
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return {
                "success": True,
                "format": "json",
                "filepath": str(filepath),
                "filename": filename,
                "total_players": len(data),
                "file_size": filepath.stat().st_size
            }
        
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _export_pdf(self, data: List[Dict[str, Any]], positions: Optional[List[str]],
                        top_n: Optional[int], include_tiers: bool) -> Dict[str, Any]:
        """Export rankings to PDF format."""
        try:
            # For now, create a text-based "PDF" (would need reportlab for real PDF)
            logger.info("📄 Creating PDF export (text-based)...")
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fantasy_cheatsheet_{timestamp}.txt"
            filepath = self.output_dir / filename
            
            # Create formatted content
            content = self._generate_cheatsheet_content(data, include_tiers)
            
            # Write to file
            with open(filepath, 'w') as f:
                f.write(content)
            
            return {
                "success": True,
                "format": "pdf",
                "filepath": str(filepath),
                "filename": filename,
                "total_players": len(data),
                "file_size": filepath.stat().st_size,
                "note": "Text-based format (PDF generation requires additional dependencies)"
            }
        
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _export_cheatsheet(self, data: List[Dict[str, Any]], positions: Optional[List[str]],
                               top_n: Optional[int], include_tiers: bool) -> Dict[str, Any]:
        """Export rankings as printable cheatsheet."""
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"draft_cheatsheet_{timestamp}.txt"
            filepath = self.output_dir / filename
            
            # Create formatted cheatsheet content
            content = self._generate_cheatsheet_content(data, include_tiers, printable=True)
            
            # Write to file
            with open(filepath, 'w') as f:
                f.write(content)
            
            return {
                "success": True,
                "format": "cheatsheet",
                "filepath": str(filepath),
                "filename": filename,
                "total_players": len(data),
                "file_size": filepath.stat().st_size,
                "description": "Printable draft cheatsheet"
            }
        
        except Exception as e:
            logger.error(f"Cheatsheet export failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _export_text(self, data: List[Dict[str, Any]], positions: Optional[List[str]],
                         top_n: Optional[int], include_tiers: bool) -> Dict[str, Any]:
        """Export rankings as plain text."""
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fantasy_rankings_{timestamp}.txt"
            filepath = self.output_dir / filename
            
            # Create simple text format
            lines = []
            lines.append(f"Fantasy Football Rankings - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            lines.append("=" * 80)
            lines.append("")
            
            for player in data:
                tier_info = f" (Tier {player['tier']})" if include_tiers and 'tier' in player else ""
                line = f"{player['overall_rank']:3d}. {player['player_name']:<25} ({player['position']}) - {player['predicted_points']:5.1f} pts, VOR: {player['vor_value']:5.1f}{tier_info}"
                lines.append(line)
            
            content = "\n".join(lines)
            
            # Write to file
            with open(filepath, 'w') as f:
                f.write(content)
            
            return {
                "success": True,
                "format": "text",
                "filepath": str(filepath),
                "filename": filename,
                "total_players": len(data),
                "file_size": filepath.stat().st_size
            }
        
        except Exception as e:
            logger.error(f"Text export failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_cheatsheet_content(self, data: List[Dict[str, Any]], include_tiers: bool, 
                                   printable: bool = False) -> str:
        """Generate formatted cheatsheet content."""
        lines = []
        
        # Header
        header = "🏈 FANTASY FOOTBALL DRAFT CHEATSHEET 🏈"
        lines.append(header)
        lines.append("=" * len(header))
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        
        # Instructions
        if printable:
            lines.append("DRAFT STRATEGY:")
            lines.append("- Focus on RB/WR early rounds (rounds 1-6)")
            lines.append("- Wait on QB unless elite option available")
            lines.append("- Target TE in middle rounds or stream")
            lines.append("- Pay attention to bye weeks for key players")
            lines.append("")
        
        # Overall rankings
        lines.append("OVERALL RANKINGS (by VOR):")
        lines.append("-" * 80)
        
        # Position-specific sections
        for position in ["QB", "RB", "WR", "TE"]:
            position_players = [p for p in data if p["position"] == position]
            if not position_players:
                continue
            
            lines.append(f"\n{position} RANKINGS:")
            lines.append("-" * 40)
            
            for player in position_players[:20]:  # Top 20 per position
                tier_info = f" T{player['tier']}" if include_tiers and 'tier' in player else ""
                bye_info = f" (Bye: {player['bye_week']})" if 'bye_week' in player else ""
                
                line = f"{player['position_rank']:2d}. {player['player_name']:<20} {player['team']:<4} - {player['predicted_points']:5.1f} pts{tier_info}{bye_info}"
                lines.append(line)
        
        return "\n".join(lines)
    
    async def get_export_history(self) -> Dict[str, Any]:
        """Get history of exported files."""
        try:
            export_files = []
            
            # Scan output directory for exported files
            for file_path in self.output_dir.glob("*"):
                if file_path.is_file():
                    file_info = {
                        "filename": file_path.name,
                        "filepath": str(file_path),
                        "size": file_path.stat().st_size,
                        "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                    export_files.append(file_info)
            
            # Sort by creation time (newest first)
            export_files.sort(key=lambda x: x["created"], reverse=True)
            
            return {
                "total_files": len(export_files),
                "files": export_files,
                "output_directory": str(self.output_dir)
            }
        
        except Exception as e:
            logger.error(f"Failed to get export history: {e}")
            return {"error": str(e)}