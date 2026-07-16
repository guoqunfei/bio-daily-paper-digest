#!/usr/bin/env python3
"""
Trend Analyzer Module - Keyword frequency and research hotspot tracking
趋势分析器：关键词频率统计、研究热点追踪、时间序列分析
"""

import re
from typing import List, Dict, Counter as CounterType
from collections import Counter, defaultdict
from datetime import datetime


class TrendAnalyzer:
    """Analyze research trends from paper collections"""

    def __init__(self):
        self.keyword_counter = Counter()
        self.date_counter = defaultdict(int)
        self.source_counter = Counter()
        self.author_counter = Counter()

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract potential keywords from text"""
        # Common bioinformatics keywords
        bio_keywords = [
            "genome", "assembly", "structural variation", "sv", "snp",
            "long-read", "pacbio", "ont", "nanopore", "hifi",
            "hi-c", "chromatin", "epigenome", "methylation",
            "transcriptome", "rna-seq", "single-cell", "scRNA",
            "proteome", "metabolome", "microbiome",
            "crispr", "gene editing", "synthetic biology",
            "machine learning", "deep learning", "ai",
            "phylogeny", "evolution", "population genetics",
            "comparative genomics", "functional genomics"
        ]

        text_lower = text.lower()
        found = []
        for kw in bio_keywords:
            if kw in text_lower:
                found.append(kw)
        return found

    def analyze(self, papers: List[Dict]) -> Dict:
        """Analyze trends from a list of papers"""
        for paper in papers:
            # Keyword frequency from title + abstract
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            keywords = self._extract_keywords(text)
            self.keyword_counter.update(keywords)

            # Date distribution
            pub_date = paper.get("published", "")
            if pub_date:
                try:
                    dt = datetime.strptime(pub_date[:7], "%Y-%m")
                    self.date_counter[dt.strftime("%Y-%m")] += 1
                except ValueError:
                    pass

            # Source distribution
            self.source_counter[paper.get("source", "Unknown")] += 1

            # Author frequency
            authors = paper.get("authors", "")
            for author in authors.split(","):
                name = author.strip().split()[-1] if author.strip() else ""
                if name:
                    self.author_counter[name] += 1

        return {
            "top_keywords": self.keyword_counter.most_common(20),
            "date_distribution": dict(sorted(self.date_counter.items())),
            "source_distribution": dict(self.source_counter),
            "top_authors": self.author_counter.most_common(10),
            "total_papers": len(papers)
        }

    def generate_report(self, papers: List[Dict]) -> str:
        """Generate a markdown trend report"""
        stats = self.analyze(papers)
        lines = [
            "## Trend Analysis Report",
            "",
            f"**Total Papers Analyzed:** {stats['total_papers']}",
            "",
            "### Top Keywords",
            "",
        ]

        for keyword, count in stats["top_keywords"][:10]:
            lines.append(f"- {keyword}: {count} occurrences")

        lines.extend(["", "### Source Distribution", ""])
        for source, count in stats["source_distribution"].items():
            lines.append(f"- {source}: {count} papers")

        lines.extend(["", "### Monthly Distribution", ""])
        for month, count in stats["date_distribution"].items():
            lines.append(f"- {month}: {count} papers")

        if stats["top_authors"]:
            lines.extend(["", "### Most Active Authors", ""])
            for author, count in stats["top_authors"][:5]:
                lines.append(f"- {author}: {count} papers")

        return "\n".join(lines)

    def detect_emerging_topics(self, papers: List[Dict]) -> List[Dict]:
        """Detect emerging topics based on keyword co-occurrence"""
        topic_pairs = defaultdict(int)

        for paper in papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            keywords = self._extract_keywords(text)
            for i, kw1 in enumerate(keywords):
                for kw2 in keywords[i+1:]:
                    pair = tuple(sorted([kw1, kw2]))
                    topic_pairs[pair] += 1

        emerging = []
        for (kw1, kw2), count in topic_pairs.most_common(10):
            if count >= 2:
                emerging.append({
                    "topic1": kw1,
                    "topic2": kw2,
                    "co_occurrence": count
                })

        return emerging


def analyze_trends(papers: List[Dict]) -> Dict:
    """Convenience function"""
    analyzer = TrendAnalyzer()
    return analyzer.analyze(papers)
