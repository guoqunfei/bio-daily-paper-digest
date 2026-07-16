#!/usr/bin/env python3
"""
User Preferences Module - Persistent user preference storage and learning
用户偏好存储：基于反馈动态调整关键词权重、记录已忽略/已读论文
"""

import os
import json
import hashlib
from typing import List, Dict, Set, Optional
from datetime import datetime, timedelta
from pathlib import Path


class UserPreferences:
    """Persistent user preferences with feedback-based learning"""

    def __init__(self, data_dir: str = "output/.preferences"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件路径
        self.prefs_file = self.data_dir / "preferences.json"
        self.ignored_file = self.data_dir / "ignored_papers.json"
        self.read_file = self.data_dir / "read_papers.json"
        self.follow_up_file = self.data_dir / "follow_up.json"
        self.history_file = self.data_dir / "feedback_history.json"
        
        # 加载数据
        self._load()

    def _load(self):
        """Load all preference data"""
        # 关键词权重（正反馈增加权重，负反馈降低）
        self.keyword_weights: Dict[str, float] = self._load_json(self.prefs_file, {})
        
        # 已忽略的论文（黑名单：DOI或标题hash）
        self.ignored_papers: Set[str] = set(self._load_json(self.ignored_file, []))
        
        # 已读的论文
        self.read_papers: Set[str] = set(self._load_json(self.read_file, []))
        
        # 待跟进列表
        self.follow_up: Dict[str, dict] = self._load_json(self.follow_up_file, {})
        
        # 反馈历史
        self.feedback_history: List[dict] = self._load_json(self.history_file, [])

    def _load_json(self, path: Path, default):
        """Load JSON file or return default"""
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default

    def _save_json(self, path: Path, data):
        """Save data to JSON file"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _paper_key(self, paper: dict) -> str:
        """Generate unique key for a paper (DOI or title hash)"""
        doi = paper.get("doi", "").strip()
        if doi:
            return f"doi:{doi}"
        # Use MD5 hash of title as fallback
        title = paper.get("title", "").strip().lower()
        return f"title:{hashlib.md5(title.encode()).hexdigest()[:16]}"

    def mark_useful(self, paper: dict):
        """Mark paper as useful (positive feedback)"""
        key = self._paper_key(paper)
        
        # Boost keyword weights from this paper
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        for word in text.split():
            if len(word) > 3:  # Only meaningful words
                self.keyword_weights[word] = self.keyword_weights.get(word, 1.0) + 0.5
        
        # Record feedback
        self.feedback_history.append({
            "action": "useful",
            "paper_key": key,
            "title": paper.get("title", "")[:100],
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_all()
        print(f"[Preferences] Marked as useful: {paper.get('title', '')[:50]}...")

    def mark_irrelevant(self, paper: dict):
        """Mark paper as irrelevant (negative feedback)"""
        key = self._paper_key(paper)
        self.ignored_papers.add(key)
        
        # Reduce keyword weights
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        for word in text.split():
            if len(word) > 3:
                self.keyword_weights[word] = max(self.keyword_weights.get(word, 1.0) - 0.3, 0.1)
        
        self.feedback_history.append({
            "action": "irrelevant",
            "paper_key": key,
            "title": paper.get("title", "")[:100],
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_all()
        print(f"[Preferences] Marked as irrelevant: {paper.get('title', '')[:50]}...")

    def mark_read(self, paper: dict):
        """Mark paper as read"""
        key = self._paper_key(paper)
        self.read_papers.add(key)
        self._save_json(self.read_file, list(self.read_papers))

    def is_ignored(self, paper: dict) -> bool:
        """Check if paper was previously marked as irrelevant"""
        key = self._paper_key(paper)
        return key in self.ignored_papers

    def is_read(self, paper: dict) -> bool:
        """Check if paper was already read"""
        key = self._paper_key(paper)
        return key in self.read_papers

    def add_follow_up(self, paper: dict, reminder_days: int = 3):
        """Add paper to follow-up list with reminder date"""
        key = self._paper_key(paper)
        reminder_date = (datetime.now() + timedelta(days=reminder_days)).strftime("%Y-%m-%d")
        
        self.follow_up[key] = {
            "title": paper.get("title", ""),
            "url": paper.get("url", ""),
            "reminder_date": reminder_date,
            "added_at": datetime.now().isoformat()
        }
        
        self.feedback_history.append({
            "action": "follow_up",
            "paper_key": key,
            "title": paper.get("title", "")[:100],
            "reminder_date": reminder_date,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_json(self.follow_up_file, self.follow_up)
        print(f"[Preferences] Added to follow-up: {paper.get('title', '')[:50]}... (reminder: {reminder_date})")

    def get_due_follow_ups(self) -> List[dict]:
        """Get follow-up items that are due today"""
        today = datetime.now().strftime("%Y-%m-%d")
        due = []
        for key, item in self.follow_up.items():
            if item.get("reminder_date", "") <= today:
                due.append({
                    "key": key,
                    **item
                })
        return due

    def get_keyword_boost(self, text: str) -> float:
        """Get keyword weight boost based on user preferences"""
        text_lower = text.lower()
        boost = 0.0
        for word, weight in self.keyword_weights.items():
            if word in text_lower:
                boost += (weight - 1.0) * 0.1
        return boost

    def get_stats(self) -> dict:
        """Get preference statistics"""
        return {
            "total_keywords": len(self.keyword_weights),
            "ignored_papers": len(self.ignored_papers),
            "read_papers": len(self.read_papers),
            "follow_up_count": len(self.follow_up),
            "total_feedback": len(self.feedback_history)
        }

    def _save_all(self):
        """Save all preference data"""
        self._save_json(self.prefs_file, self.keyword_weights)
        self._save_json(self.ignored_file, list(self.ignored_papers))
        self._save_json(self.read_file, list(self.read_papers))
        self._save_json(self.follow_up_file, self.follow_up)
        self._save_json(self.history_file, self.feedback_history)


# Singleton instance
_preferences_instance = None

def get_preferences() -> UserPreferences:
    """Get singleton UserPreferences instance"""
    global _preferences_instance
    if _preferences_instance is None:
        _preferences_instance = UserPreferences()
    return _preferences_instance
