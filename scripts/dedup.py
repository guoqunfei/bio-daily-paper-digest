#!/usr/bin/env python3
"""
Dedup Module - Multi-dimensional deduplication engine
去重引擎：支持标题哈希、DOI、相似度三种去重策略
"""

import hashlib
import re
from typing import List, Dict, Set, Tuple
from difflib import SequenceMatcher


class DedupEngine:
    """Multi-strategy paper deduplication engine"""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self._seen_hashes: Set[str] = set()
        self._seen_dois: Set[str] = set()
        self._seen_titles: List[str] = []

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison"""
        # Lowercase, remove punctuation, collapse whitespace
        normalized = title.lower().strip()
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def _title_hash(self, title: str) -> str:
        """Generate MD5 hash of normalized title"""
        normalized = self._normalize_title(title)
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles"""
        s1 = self._normalize_title(title1)
        s2 = self._normalize_title(title2)
        if not s1 or not s2:
            return 0.0
        return SequenceMatcher(None, s1, s2).ratio()

    def is_duplicate(self, paper: Dict) -> bool:
        """Check if paper is a duplicate using multiple strategies"""
        title = paper.get("title", "").strip()
        doi = paper.get("doi", "").strip()

        if not title:
            return True  # Skip empty titles

        # Strategy 1: Exact hash match
        title_hash = self._title_hash(title)
        if title_hash in self._seen_hashes:
            return True

        # Strategy 2: DOI exact match
        if doi and doi in self._seen_dois:
            return True

        # Strategy 3: Similarity check against seen titles
        for seen_title in self._seen_titles:
            if self._title_similarity(title, seen_title) >= self.similarity_threshold:
                return True

        return False

    def add(self, paper: Dict) -> None:
        """Add paper to seen set"""
        title = paper.get("title", "").strip()
        doi = paper.get("doi", "").strip()

        if title:
            self._seen_hashes.add(self._title_hash(title))
            self._seen_titles.append(title)
        if doi:
            self._seen_dois.add(doi)

    def deduplicate(self, papers: List[Dict]) -> Tuple[List[Dict], int]:
        """
        Deduplicate a list of papers.
        Returns: (unique_papers, removed_count)
        """
        unique = []
        removed = 0

        for paper in papers:
            if self.is_duplicate(paper):
                removed += 1
                continue
            self.add(paper)
            unique.append(paper)

        return unique, removed


def deduplicate_papers(papers: List[Dict], threshold: float = 0.85) -> Tuple[List[Dict], int]:
    """Convenience function for deduplication"""
    engine = DedupEngine(similarity_threshold=threshold)
    return engine.deduplicate(papers)
