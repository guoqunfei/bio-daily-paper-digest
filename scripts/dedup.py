#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""去重存储模块：基于 JSON 文件，兼容 GitHub Actions cache"""

import json
import hashlib
from pathlib import Path
from datetime import datetime


class DedupStore:
    def __init__(self, store_path=".paper-digest-cache/seen_papers.json"):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.seen = self._load()

    def _load(self):
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save(self):
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(self.seen, f, ensure_ascii=False, indent=2)

    def get_key(self, paper):
        doi = (paper.get("doi") or "").strip()
        if doi:
            return f"doi:{doi.lower()}"
        arxiv = (paper.get("arxiv_id") or "").strip()
        if arxiv:
            return f"arxiv:{arxiv.lower()}"
        pmid = (paper.get("pmid") or "").strip()
        if pmid:
            return f"pmid:{pmid}"
        title = (paper.get("title") or "").strip()
        if title:
            h = hashlib.md5(title.lower().encode()).hexdigest()[:12]
            return f"title:{h}"
        return None

    def is_seen(self, paper):
        key = self.get_key(paper)
        if not key:
            return False
        return key in self.seen

    def mark_seen(self, paper):
        key = self.get_key(paper)
        if key:
            self.seen[key] = {
                "title": paper.get("title", "")[:120],
                "date": paper.get("date", ""),
                "source": paper.get("source", ""),
                "marked_at": datetime.now().isoformat()
            }

    def stats(self):
        return {"total_seen": len(self.seen)}
