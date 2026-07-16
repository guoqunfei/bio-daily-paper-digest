#!/usr/bin/env python3
"""
Source Classifier Module - Classify and analyze paper sources
来源分类器：统计各数据源占比、识别交叉文献
"""

from typing import List, Dict
from collections import Counter, defaultdict


class SourceClassifier:
    """Analyze and classify paper sources"""

    def __init__(self):
        self.source_counts = Counter()
        self.source_papers = defaultdict(list)

    def classify(self, papers: List[Dict]) -> Dict:
        """Classify papers by source and return statistics"""
        for paper in papers:
            source = paper.get("source", "Unknown")
            self.source_counts[source] += 1
            self.source_papers[source].append(paper)

        total = len(papers)
        stats = {
            "total": total,
            "sources": {},
            "dominant_source": None,
        }

        for source, count in self.source_counts.items():
            percentage = (count / total * 100) if total > 0 else 0
            stats["sources"][source] = {
                "count": count,
                "percentage": round(percentage, 1),
                "papers": self.source_papers[source]
            }

        if self.source_counts:
            stats["dominant_source"] = self.source_counts.most_common(1)[0][0]

        return stats

    def get_cross_source_duplicates(self, papers: List[Dict]) -> List[Dict]:
        """Identify papers that appear in multiple sources (by title)"""
        title_map = defaultdict(list)
        for paper in papers:
            title = paper.get("title", "").lower().strip()
            if title:
                title_map[title].append(paper["source"])

        cross_source = []
        for title, sources in title_map.items():
            if len(set(sources)) > 1:
                cross_source.append({
                    "title": title,
                    "sources": list(set(sources))
                })

        return cross_source

    def generate_summary(self, papers: List[Dict]) -> str:
        """Generate a human-readable source summary"""
        stats = self.classify(papers)
        lines = ["### Source Distribution", ""]

        for source, info in stats["sources"].items():
            lines.append(f"- **{source}**: {info['count']} papers ({info['percentage']}%)")

        lines.append("")
        lines.append(f"**Dominant Source:** {stats['dominant_source']}")
        lines.append("")

        cross = self.get_cross_source_duplicates(papers)
        if cross:
            lines.append(f"**Cross-source duplicates:** {len(cross)} papers found in multiple sources")
            lines.append("")

        return "\n".join(lines)


def classify_sources(papers: List[Dict]) -> Dict:
    """Convenience function"""
    classifier = SourceClassifier()
    return classifier.classify(papers)
