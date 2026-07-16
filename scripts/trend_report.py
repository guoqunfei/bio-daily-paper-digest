#!/usr/bin/env python3
"""
Trend Report Module - Generate weekly trend reports
周趋势报告生成：基于历史数据生成深度趋势分析
"""

import os
import glob
from datetime import datetime, timedelta
from typing import List, Dict

from .trend_analyzer import TrendAnalyzer
from .summarize import get_summarizer


class WeeklyTrendReport:
    """Generate weekly trend reports from historical digests"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.analyzer = TrendAnalyzer()
        self.summarizer = get_summarizer()

    def load_weekly_papers(self, days: int = 7) -> List[Dict]:
        """Load papers from the last N days of digest files"""
        papers = []
        cutoff = datetime.now() - timedelta(days=days)

        # Find all digest files
        pattern = os.path.join(self.output_dir, "*_digest.md")
        for filepath in glob.glob(pattern):
            filename = os.path.basename(filepath)
            try:
                date_str = filename.split("_")[0]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date >= cutoff:
                    # Parse papers from markdown (simplified)
                    papers.extend(self._parse_digest_file(filepath))
            except (ValueError, IndexError):
                continue

        return papers

    def _parse_digest_file(self, filepath: str) -> List[Dict]:
        """Parse papers from a digest markdown file"""
        papers = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Simple parsing: look for paper sections
            lines = content.split("\n")
            current_paper = {}

            for line in lines:
                if line.startswith("## ") and ". " in line[:10]:
                    if current_paper:
                        papers.append(current_paper)
                    current_paper = {"title": line.split(". ", 1)[1] if ". " in line else line}
                elif line.startswith("- **Source:**"):
                    parts = line.replace("- **Source:**", "").split("|")
                    current_paper["source"] = parts[0].strip() if parts else ""
                    if len(parts) > 1:
                        current_paper["published"] = parts[1].replace("**Published:**", "").strip()
                elif line.startswith("- **Authors:**"):
                    current_paper["authors"] = line.replace("- **Authors:**", "").strip()
                elif line.startswith("- **URL:**"):
                    current_paper["url"] = line.replace("- **URL:**", "").strip()
                elif line.startswith("### Summary"):
                    current_paper["has_summary"] = True

            if current_paper:
                papers.append(current_paper)

        except Exception as e:
            print(f"[TrendReport] Error parsing {filepath}: {e}")

        return papers

    def generate(self, days: int = 7) -> str:
        """Generate weekly trend report"""
        papers = self.load_weekly_papers(days)
        if not papers:
            return "# Weekly Trend Report\n\nNo papers found in the last week."

        # Trend analysis
        stats = self.analyzer.analyze(papers)
        trend_md = self.analyzer.generate_report(papers)

        # LLM weekly overview
        llm_overview = ""
        if self.summarizer.enabled:
            print("[TrendReport] Generating LLM weekly overview...")
            llm_overview = self.summarizer.generate_weekly_trend(papers)

        # Build report
        week_start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        week_end = datetime.now().strftime("%Y-%m-%d")

        lines = [
            f"# Weekly Trend Report ({week_start} to {week_end})",
            "",
            f"> **Total Papers:** {len(papers)} | **Period:** Last {days} days",
            "",
            "---",
            "",
        ]

        if llm_overview:
            lines.extend([
                "## LLM Weekly Overview",
                "",
                llm_overview,
                "",
                "---",
                "",
            ])

        lines.extend([
            trend_md,
            "",
            "---",
            "",
            "## Emerging Topics",
            "",
        ])

        emerging = self.analyzer.detect_emerging_topics(papers)
        if emerging:
            for topic in emerging[:5]:
                lines.append(f"- **{topic['topic1']}** + **{topic['topic2']}**: {topic['co_occurrence']} co-occurrences")
        else:
            lines.append("No significant emerging topics detected.")

        lines.append("")
        return "\n".join(lines)

    def save(self, days: int = 7) -> str:
        """Generate and save weekly report"""
        report = self.generate(days)
        today = datetime.now().strftime("%Y-%m-%d")
        filepath = os.path.join(self.output_dir, f"{today}_weekly_trend.md")
        os.makedirs(self.output_dir, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"[TrendReport] Saved to {filepath}")
        return filepath


def generate_weekly_report(output_dir: str = "output", days: int = 7) -> str:
    """Convenience function"""
    reporter = WeeklyTrendReport(output_dir)
    return reporter.save(days)
