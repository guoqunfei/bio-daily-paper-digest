#!/usr/bin/env python3
"""
Bio Daily Paper Digest - Main Entry Point
主入口：支持 daily / weekly / cloudflare 三种运行模式
"""

import os
import sys
import argparse
import traceback
from datetime import datetime

from scripts.config import config
from scripts.fetch_papers import fetch_all_sources
from scripts.dedup import deduplicate_papers
from scripts.source_classifier import classify_sources
from scripts.summarize import get_summarizer
from scripts.trend_analyzer import analyze_trends
from scripts.trend_report import generate_weekly_report
from scripts.github_feedback import get_feedback
from scripts.email_sender import get_sender


def run_daily():
    """Run daily digest pipeline"""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[{today}] === Daily Digest Started ===")

    try:
        # 1. Fetch papers
        keywords = config.search_keywords
        max_results = config.max_results
        api_key = config.get("search", "ncbi_api_key", default=None)
        papers = fetch_all_sources(keywords, max_results, api_key)

        if not papers:
            print(f"[{today}] No papers found. Exiting.")
            return

        # 2. Deduplicate
        unique_papers, removed = deduplicate_papers(papers)
        print(f"[{today}] Deduplicated: {len(unique_papers)} unique, {removed} removed")

        # 3. Source classification
        source_stats = classify_sources(unique_papers)
        source_summary = {s: f"{info['count']} ({info['percentage']}%)" for s, info in source_stats['sources'].items()}
        print(f"[{today}] Sources: {source_summary}")

        # 4. Generate digest with LLM
        summarizer = get_summarizer()
        language = config.digest_language

        os.makedirs("output", exist_ok=True)
        digest_path = f"output/{today}_digest.md"

        lines = [
            f"# Daily Literature Digest - {today}",
            "",
            f"> **Total Papers:** {len(unique_papers)} | **Sources:** {', '.join(source_stats['sources'].keys())}",
            "",
            "---",
            "",
        ]

        # LLM overview
        if summarizer.enabled:
            print(f"[{today}] Generating LLM overview...")
            overview = summarizer.generate_overview(unique_papers, language)
            if overview:
                lines.extend(["## Research Trend Overview", "", overview, "", "---", ""])

        # Individual papers
        for i, paper in enumerate(unique_papers, 1):
            if summarizer.enabled and i <= config.get("digest", "llm_max_papers", default=15):
                summary = summarizer.summarize_paper(paper['title'], paper['abstract'], language)
            else:
                summary = paper['abstract'][:300] + "..." if len(paper['abstract']) > 300 else paper['abstract']

            lines.extend([
                f"## {i}. {paper['title']}",
                "",
                f"- **Source:** {paper['source']} | **Published:** {paper['published']}",
                f"- **Authors:** {paper['authors']}",
                f"- **URL:** {paper['url']}",
                "",
                "### Summary",
                "",
                summary if summary else "*No summary available.*",
                "",
                "---",
                "",
            ])

        with open(digest_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"[{today}] Digest saved: {digest_path}")

        # 5. Send email
        sender = get_sender()
        sender.send_digest(digest_path, len(unique_papers))

        # 6. GitHub feedback
        feedback = get_feedback()
        if feedback.enabled:
            source_counts = {s: info['count'] for s, info in source_stats['sources'].items()}
            feedback.report_success(len(unique_papers), source_counts)

        print(f"[{today}] === Daily Digest Completed ===")

    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()
        print(f"[{today}] ERROR: {error_msg}")

        feedback = get_feedback()
        if feedback.enabled:
            feedback.report_error(error_msg, tb)
        raise


def run_weekly():
    """Run weekly trend report"""
    print("=== Weekly Trend Report Started ===")
    try:
        report_path = generate_weekly_report(days=7)

        # Send email
        sender = get_sender()
        today = datetime.now().strftime("%Y-%m-%d")
        subject = f"[Bio-Digest] Weekly Trend Report ({today})"
        sender.send(report_path, subject=subject)

        # GitHub feedback
        feedback = get_feedback()
        if feedback.enabled:
            # Load stats for feedback
            from scripts.trend_analyzer import TrendAnalyzer
            analyzer = TrendAnalyzer()
            # This is a simplified version; real implementation would load papers
            feedback.report_weekly(0, [])

        print("=== Weekly Trend Report Completed ===")
    except Exception as e:
        print(f"Weekly report error: {e}")
        traceback.print_exc()
        raise


def main():
    parser = argparse.ArgumentParser(description="Bio Daily Paper Digest")
    parser.add_argument("--mode", choices=["daily", "weekly", "cloudflare"],
                        default="daily", help="Run mode")
    args = parser.parse_args()

    if args.mode == "daily":
        run_daily()
    elif args.mode == "weekly":
        run_weekly()
    elif args.mode == "cloudflare":
        # Cloudflare mode is handled by cloudflare-worker.js
        print("Cloudflare mode should be triggered via the Worker endpoint.")
        sys.exit(0)


if __name__ == "__main__":
    main()
