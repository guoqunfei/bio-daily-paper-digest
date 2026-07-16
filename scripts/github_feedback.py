#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Issues 反馈处理模块 + 多用户画像存储
"""

import os
import re
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
import requests


def log(msg: str):
    print(f"[FEEDBACK] {msg}")
    sys.stdout.flush()


class GitHubFeedbackProcessor:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.owner = os.getenv("REPO_OWNER", "guoqunfei")
        self.repo = os.getenv("REPO_NAME", "bio-daily-paper-digest")
        self.api_base = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        if not self.token:
            log("⚠️ GITHUB_TOKEN not set, skipping issue processing")

    def process_all(self) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        if not self.token:
            return [], [], []
        issues = self._list_open_issues()
        stars, follow_ups, ignores = [], [], []
        for issue in issues:
            title = issue.get("title", "")
            body = issue.get("body", "")
            number = issue.get("number")
            match = re.match(r'^\[(STAR|FOLLOW_UP|IGNORE)\]\s*(.+)$', title, re.IGNORECASE)
            if not match:
                continue
            action = match.group(1).upper()
            paper_key = match.group(2).strip()
            user_email = self._extract_user(body)
            entry = {"paper_key": paper_key, "user_email": user_email, "created_at": issue.get("created_at", ""), "note": body, "issue_number": number}
            if action == "STAR": stars.append(entry)
            elif action == "FOLLOW_UP": follow_ups.append(entry)
            elif action == "IGNORE": ignores.append(entry)
            self._close_issue(number)
            log(f"Processed [{action}] {paper_key} from {user_email}")
        return stars, follow_ups, ignores

    def _list_open_issues(self) -> List[Dict]:
        url = f"{self.api_base}/issues"
        headers = {"Authorization": f"token {self.token}", "Accept": "application/vnd.github.v3+json"}
        params = {"state": "open", "labels": "feedback", "per_page": 100}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            r.raise_for_status()
            issues = [i for i in r.json() if "pull_request" not in i]
            log(f"Found {len(issues)} open feedback issues")
            return issues
        except Exception as e:
            log(f"Error listing issues: {e}")
            return []

    def _close_issue(self, number: int):
        url = f"{self.api_base}/issues/{number}"
        headers = {"Authorization": f"token {self.token}", "Accept": "application/vnd.github.v3+json"}
        try:
            requests.patch(url, headers=headers, json={"state": "closed"}, timeout=30)
        except Exception as e:
            log(f"Error closing issue #{number}: {e}")

    def _extract_user(self, body: str) -> str:
        match = re.search(r'用户[:\s]+(\S+@\S+)', body)
        if match:
            return match.group(1)
        return os.getenv("EMAIL_TO", "unknown").split(",")[0].strip()


class MultiUserFeedbackStore:
    def __init__(self, path=".paper-digest-cache/multi_user_feedback.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"version": 3, "users": {}, "follow_ups": [], "processed_issues": []}

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_or_create_user(self, email: str):
        if email not in self.data["users"]:
            self.data["users"][email] = {"starred_keywords": {}, "starred_count": 0, "ignored_papers": [], "created_at": datetime.now().isoformat()}
        return self.data["users"][email]

    def add_star(self, email: str, paper_key: str, paper_meta: Dict):
        user = self.get_or_create_user(email)
        user["starred_count"] = user.get("starred_count", 0) + 1
        text = f"{paper_meta.get('title', '')} {paper_meta.get('abstract', '')}".lower()
        core_terms = ["hifiasm", "yahs", "sniffles", "sniffles2", "bcftools", "truvari", "myrmecia", "bull ant", "pig genome", "sus scrofa", "antifreeze protein", "hi-c", "long-read", "pacbio", "nanopore", "chromosome-level", "busco", "merqury", "purge_haplotigs", "nextpolish", "alphaFold", "gromacs", "cutesv", "svim", "pbsv", "canu", "flye", "juicer", "3d-dna", "salsa", "getorganelle", "mitos", "pore-c", "micro-c", "tad", "promoter-enhancer", "haplotype-resolved", "de novo assembly", "benchmark", "comparative genomics"]
        for term in core_terms:
            if term.lower() in text:
                user["starred_keywords"][term] = user["starred_keywords"].get(term, 0) + 1

    def add_follow_up(self, email: str, paper_key: str, paper_meta: Dict, days: int = 3):
        due_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        self.data["follow_ups"].append({"paper_key": paper_key, "user_email": email, "created_at": datetime.now().isoformat(), "due_date": due_date, "paper_title": paper_meta.get("title", paper_key), "paper_url": paper_meta.get("url", ""), "status": "pending"})

    def add_ignore(self, email: str, paper_key: str):
        user = self.get_or_create_user(email)
        if paper_key not in user.get("ignored_papers", []):
            user.setdefault("ignored_papers", []).append(paper_key)

    def get_due_follow_ups(self, email: str = None) -> List[Dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        return [fu for fu in self.data.get("follow_ups", []) if fu.get("status") == "pending" and fu.get("due_date", "") <= today and (email is None or fu.get("user_email") == email)]

    def get_all_pending_follow_ups(self, email: str = None) -> List[Dict]:
        return [fu for fu in self.data.get("follow_ups", []) if fu.get("status") == "pending" and (email is None or fu.get("user_email") == email)]

    def mark_follow_up_done(self, paper_key: str, email: str):
        for fu in self.data.get("follow_ups", []):
            if fu.get("paper_key") == paper_key and fu.get("user_email") == email:
                fu["status"] = "done"

    def get_user_weights(self, email: str) -> Dict[str, float]:
        user = self.data["users"].get(email)
        if not user:
            return {}
        keywords = user.get("starred_keywords", {})
        total = user.get("starred_count", 0)
        if not keywords or total == 0:
            return {}
        return {kw: min(count / total * 5, 3.0) for kw, count in keywords.items()}

    def is_ignored_by_user(self, paper_key: str, email: str) -> bool:
        user = self.data["users"].get(email)
        if not user:
            return False
        return paper_key in user.get("ignored_papers", [])

    def get_recent_starred_context(self, email: str, n: int = 5) -> List[Dict]:
        starred = []
        for k, v in self.data.get("users", {}).get(email, {}).get("starred_keywords", {}).items():
            starred.append((v, k))
        starred.sort(reverse=True)
        return [{"keyword": k, "count": c} for c, k in starred[:n]]


if __name__ == "__main__":
    processor = GitHubFeedbackProcessor()
    stars, follow_ups, ignores = processor.process_all()
    print(f"Stars: {len(stars)}, Follow-ups: {len(follow_ups)}, Ignores: {len(ignores)}")
