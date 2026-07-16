#!/usr/bin/env python3
"""
Team Sync Module - Multi-team knowledge base synchronization
团队知识库同步：按研究方向分组推送、差异化推送、团队日报
"""

import os
import yaml
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path


class TeamConfig:
    """Team configuration loaded from config/team.yaml"""
    
    def __init__(self, config_path: str = "config/team.yaml"):
        self.config_path = Path(config_path)
        self.data = self._load()
    
    def _load(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}
    
    @property
    def teams(self) -> List[Dict]:
        return self.data.get("teams", [])
    
    @property
    def locations(self) -> Dict:
        return self.data.get("locations", {})
    
    @property
    def knowledge_base(self) -> Dict:
        return self.data.get("knowledge_base", {})
    
    @property
    def push_strategy(self) -> Dict:
        return self.data.get("push_strategy", {})
    
    @property
    def fatigue_control(self) -> Dict:
        return self.data.get("fatigue_control", {})
    
    def get_team(self, team_id: str) -> Optional[Dict]:
        for team in self.teams:
            if team.get("id") == team_id:
                return team
        return None
    
    def get_teams_for_paper(self, paper: dict) -> List[str]:
        """Determine which team(s) a paper belongs to"""
        matched_teams = []
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        
        for team in self.teams:
            focus = team.get("focus", [])
            for keyword in focus:
                if keyword.lower() in text:
                    matched_teams.append(team["id"])
                    break
        
        return matched_teams
    
    def get_location_bias(self, location: str) -> Dict:
        """Get location-specific bias and extra keywords"""
        return self.locations.get(location, {})


class TeamSyncManager:
    """Manage team knowledge base synchronization"""
    
    def __init__(self):
        self.config = TeamConfig()
        self.data_dir = Path("output/.team")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.team_read_file = self.data_dir / "team_read_papers.json"
        self.team_stats_file = self.data_dir / "team_stats.json"
    
    def group_papers_by_team(self, papers: List[dict]) -> Dict[str, List[dict]]:
        """Group papers by team based on research focus"""
        groups = {team["id"]: [] for team in self.config.teams}
        groups["uncategorized"] = []  # Papers not matching any team
        
        for paper in papers:
            matched = self.config.get_teams_for_paper(paper)
            if matched:
                for team_id in matched:
                    if team_id in groups:
                        groups[team_id].append(paper)
            else:
                groups["uncategorized"].append(paper)
        
        return groups
    
    def apply_team_filter(self, papers: List[dict], team_id: str) -> List[dict]:
        """Filter papers for a specific team with focus keywords"""
        team = self.config.get_team(team_id)
        if not team:
            return papers
        
        filtered = []
        for paper in papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
            for keyword in team.get("focus", []):
                if keyword.lower() in text:
                    filtered.append(paper)
                    break
        
        return filtered
    
    def apply_location_bias(self, papers: List[dict], location: str) -> List[dict]:
        """Apply location-specific bias to paper scoring"""
        location_config = self.config.get_location_bias(location)
        if not location_config:
            return papers
        
        extra_keywords = location_config.get("extra_keywords", [])
        for paper in papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
            bonus = 0
            for kw in extra_keywords:
                if kw.lower() in text:
                    bonus += 0.5
            if bonus > 0 and "relevance_score" in paper:
                paper["relevance_score"] = min(paper["relevance_score"] + bonus, 10.0)
                paper["location_bonus"] = bonus
        
        return papers
    
    def generate_team_digest(self, papers: List[dict], team_id: str) -> str:
        """Generate team-specific digest markdown"""
        team = self.config.get_team(team_id)
        if not team:
            return ""
        
        today = datetime.now().strftime("%Y-%m-%d")
        team_papers = self.apply_team_filter(papers, team_id)
        
        if not team_papers:
            return ""
        
        lines = [
            f"# {team['name']} - 文献日报 ({today})",
            "",
            f"> **匹配文献数:** {len(team_papers)}",
            "> **研究方向:** " + ", ".join(team.get("focus", [])[:5]),
            "",
            "---",
            "",
        ]
        
        for i, paper in enumerate(team_papers[:15], 1):
            score = paper.get("relevance_score", 0)
            lines.extend([
                f"## {i}. {paper['title']}",
                "",
                f"- **来源:** {paper.get('source', 'N/A')} | **评分:** {score}/10",
                f"- **URL:** {paper.get('url', 'N/A')}",
                "",
            ])
        
        return "\n".join(lines)
    
    def generate_team_daily_report(self, all_papers: List[dict]) -> str:
        """Generate daily report for team leader"""
        today = datetime.now().strftime("%Y-%m-%d")
        groups = self.group_papers_by_team(all_papers)
        
        lines = [
            f"# 团队文献日报 - {today}",
            "",
            "> 各组文献推送概览",
            "",
            "---",
            "",
        ]
        
        for team in self.config.teams:
            team_id = team["id"]
            team_papers = groups.get(team_id, [])
            lines.extend([
                f"## {team['name']}",
                "",
                f"- **匹配文献数:** {len(team_papers)}",
                f"- **核心方向:** {', '.join(team.get('focus', [])[:5])}",
                "",
                "### 成员",
                "",
            ])
            
            for member in team.get("members", []):
                location = member.get("location", "")
                loc_name = self.config.locations.get(location, {}).get("name", location)
                lines.append(f"- {member['name']} ({member['role']}) - {loc_name}")
            
            lines.extend(["", "### 今日推荐", ""])
            
            for i, paper in enumerate(team_papers[:5], 1):
                lines.append(f"{i}. {paper['title'][:80]}...")
            
            lines.extend(["", "---", ""])
        
        # Uncategorized papers
        uncategorized = groups.get("uncategorized", [])
        if uncategorized:
            lines.extend([
                "## 未分类文献",
                "",
                f"以下 {len(uncategorized)} 篇文献未匹配到具体研究方向：",
                "",
            ])
            for i, paper in enumerate(uncategorized[:5], 1):
                lines.append(f"{i}. {paper['title'][:80]}...")
            lines.extend(["", "---", ""])
        
        return "\n".join(lines)
    
    def check_weekend_push(self) -> bool:
        """Check if should push on weekend"""
        weekday = datetime.now().weekday()
        is_weekend = weekday >= 5  # Saturday or Sunday
        
        if is_weekend and not self.config.fatigue_control.get("weekend_push", False):
            return False
        
        return True
    
    def check_max_papers(self, paper_count: int) -> bool:
        """Check if paper count exceeds daily limit"""
        max_papers = self.config.fatigue_control.get("max_daily_per_person", 15)
        return paper_count <= max_papers
    
    def get_team_members(self) -> List[Dict]:
        """Get all team members"""
        members = []
        for team in self.config.teams:
            for member in team.get("members", []):
                member_copy = member.copy()
                member_copy["team_id"] = team["id"]
                member_copy["team_name"] = team["name"]
                members.append(member_copy)
        return members
    
    def get_member_by_email(self, email: str) -> Optional[Dict]:
        """Get member info by email"""
        for team in self.config.teams:
            for member in team.get("members", []):
                if member.get("email") == email:
                    member_copy = member.copy()
                    member_copy["team_id"] = team["id"]
                    member_copy["team_name"] = team["name"]
                    return member_copy
        return None


def get_team_sync() -> TeamSyncManager:
    """Factory function"""
    return TeamSyncManager()
