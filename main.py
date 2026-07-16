#!/usr/bin/env python3
"""
Bio Daily Paper Digest - Main Entry Point
主入口：支持 daily / weekly / cloudflare 三种运行模式
整合：信息筛选 → 相关性评分 → 去重 → 结构化摘要 → 邮件推送 → GitHub反馈
"""

import os
import sys
import argparse
import traceback
import json
from datetime import datetime
from typing import List, Dict

from scripts.config import config
from scripts.fetch_papers import fetch_all_sources
from scripts.scoring import get_default_config, filter_and_score_papers, get_score_level, get_score_badge
from scripts.dedup import deduplicate_papers
from scripts.source_classifier import classify_sources
from scripts.summarize import get_summarizer
from scripts.trend_analyzer import analyze_trends
from scripts.trend_report import generate_weekly_report
from scripts.github_feedback import get_feedback
from scripts.email_sender import get_sender
from scripts.user_preferences import get_preferences
from scripts.follow_up import get_follow_up_manager


# 配置常量
MAX_DAILY_PAPERS = 15  # 每日推送上限
MIN_RELEVANCE_SCORE = 4.0  # 最低相关性阈值


def run_daily():
    """Run daily digest pipeline"""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[{today}] === Daily Digest Started ===")

    try:
        # Initialize feedback loop components
        preferences = get_preferences()
        follow_up_manager = get_follow_up_manager()
        
        # Print preference stats
        stats = preferences.get_stats()
        print(f"[{today}] User preferences loaded: {stats['ignored_papers']} ignored, {stats['read_papers']} read, {stats['follow_up_count']} follow-ups")

        # 1. Fetch papers
        keywords = config.search_keywords
        max_results = config.max_results
        api_key = config.get("search", "ncbi_api_key", default=None)
        papers = fetch_all_sources(keywords, max_results, api_key)

        if not papers:
            print(f"[{today}] No papers found. Exiting.")
            return

        # 2. Relevance scoring and filtering
        print(f"[{today}] Scoring {len(papers)} papers...")
        scoring_config = get_default_config()
        scored_papers = filter_and_score_papers(papers, scoring_config)
        
        # Filter out low-relevance papers
        relevant_papers = [p for p in scored_papers if p["relevance_score"] >= MIN_RELEVANCE_SCORE]
        
        if not relevant_papers:
            print(f"[{today}] No relevant papers found after scoring. Exiting.")
            return
        
        print(f"[{today}] Scored: {len(relevant_papers)} relevant (score >= {MIN_RELEVANCE_SCORE}), {len(scored_papers) - len(relevant_papers)} filtered")

        # 3. Deduplicate
        unique_papers, removed = deduplicate_papers(relevant_papers)
        print(f"[{today}] Deduplicated: {len(unique_papers)} unique, {removed} removed")

        # 4. Apply user preference filtering (ignore already read/ignored papers)
        print(f"[{today}] Applying user preference filters...")
        filtered_by_prefs = []
        ignored_count = 0
        read_count = 0
        for p in unique_papers:
            if preferences.is_ignored(p):
                ignored_count += 1
                continue
            if preferences.is_read(p):
                read_count += 1
                continue
            filtered_by_prefs.append(p)
        
        print(f"[{today}] Preference filter: {ignored_count} ignored, {read_count} already read, {len(filtered_by_prefs)} remaining")
        
        # 5. Apply daily limit
        limited_papers = filtered_by_prefs[:MAX_DAILY_PAPERS]
        if len(filtered_by_prefs) > MAX_DAILY_PAPERS:
            print(f"[{today}] Limited to top {MAX_DAILY_PAPERS} papers (from {len(filtered_by_prefs)})")

        # 5. Source classification
        source_stats = classify_sources(limited_papers)
        source_summary = {s: f"{info['count']} ({info['percentage']}%)" for s, info in source_stats['sources'].items()}
        print(f"[{today}] Sources: {source_summary}")
        
        # Show score distribution
        score_distribution = {}
        for p in limited_papers:
            level = get_score_level(p["relevance_score"])
            score_distribution[level] = score_distribution.get(level, 0) + 1
        print(f"[{today}] Score distribution: {score_distribution}")

        # 6. Generate digest with LLM
        summarizer = get_summarizer()
        language = config.digest_language

        os.makedirs("output", exist_ok=True)
        digest_path = f"output/{today}_digest.md"

        lines = [
            f"# Daily Literature Digest - {today}",
            "",
            f"> **Total Papers:** {len(limited_papers)} | **Sources:** {', '.join(source_stats['sources'].keys())}",
            f"> **Score Distribution:** {score_distribution}",
            "",
            "---",
            "",
        ]

        # LLM overview
        # Add follow-up reminders section first
        follow_up_reminder_md = follow_up_manager.generate_reminder_section()
        if follow_up_reminder_md:
            lines.extend([follow_up_reminder_md, ""])

        if summarizer.enabled:
            print(f"[{today}] Generating LLM overview...")
            overview = summarizer.generate_overview(limited_papers, language)
            if overview:
                lines.extend(["## Research Trend Overview", "", overview, "", "---", ""])

        # Individual papers
        for i, paper in enumerate(limited_papers, 1):
            score = paper.get("relevance_score", 0)
            level = get_score_level(score)
            badge = get_score_badge(score)
            
            # Generate structured summary if LLM enabled
            if summarizer.enabled and i <= config.get("digest", "llm_max_papers", default=15):
                print(f"[{today}] Summarizing paper {i}/{len(limited_papers)}: {paper['title'][:50]}...")
                structured = summarizer.summarize_paper_structured(paper['title'], paper['abstract'], language)
                summary = structured.one_liner
                method = structured.method_innovation
                dataset = structured.dataset
                metrics = structured.core_metrics
                code_repo = structured.code_repo
                data_avail = structured.data_availability
            else:
                summary = paper['abstract'][:300] + "..." if len(paper['abstract']) > 300 else paper['abstract']
                method = dataset = metrics = code_repo = data_avail = ""

            lines.extend([
                f"## {i}. {paper['title']}",
                "",
                f"- **Source:** {paper['source']} | **Published:** {paper['published']}",
                f"- **Authors:** {paper['authors']}",
                f"- **URL:** {paper['url']}",
                f"- **Relevance Score:** {badge} {score}/10 ({level})",
                f"- **Score Reason:** {paper.get('relevance_reason', 'N/A')}",
                "",
                "### Summary",
                "",
                summary if summary else "*No summary available.*",
                "",
            ])
            
            # Add structured details if available
            if method or dataset or metrics:
                lines.extend([
                    "**方法创新:** " + (method if method else "N/A"),
                    "**数据集:** " + (dataset if dataset else "N/A"),
                    "**核心指标:** " + (metrics if metrics else "N/A"),
                    "**代码仓库:** " + (code_repo if code_repo else "N/A"),
                    "**数据可用性:** " + (data_avail if data_avail else "N/A"),
                    "",
                ])
            
            lines.extend(["---", ""])

        with open(digest_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"[{today}] Digest saved: {digest_path}")

        # Save raw data
        data_path = f"output/{today}_papers.json"
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(limited_papers, f, ensure_ascii=False, indent=2)
        print(f"[{today}] Paper data saved: {data_path}")

        # 7. Send email
        sender = get_sender()
        sender.send_digest(digest_path, len(limited_papers))

        # 8. GitHub feedback
        feedback = get_feedback()
        if feedback.enabled:
            source_counts = {s: info['count'] for s, info in source_stats['sources'].items()}
            due_follow_ups = follow_up_manager.get_due_reminders()
            feedback.report_success(len(limited_papers), source_counts, papers=limited_papers, follow_ups=due_follow_ups)

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
