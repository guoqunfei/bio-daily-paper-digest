#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序：每日文献综述入口
整合：Issue反馈处理 → 抓取 → 去重 → 过滤评分 → LLM总结 → 邮件推送 → 归档
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from dedup import DedupStore
from github_feedback import GitHubFeedbackProcessor, MultiUserFeedbackStore
from fetch_papers import PaperFetcher
from summarize import PaperSummarizer
from email_sender import EmailSender


def log(msg: str):
    print(f"[MAIN] {msg}")
    sys.stdout.flush()


def main():
    log("=" * 60)
    log("🧬 Bio Daily Paper Digest - 每日文献综述")
    log(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    cfg = Config()
    dedup = DedupStore()
    mufb = MultiUserFeedbackStore()

    # 0. 处理用户反馈 Issues
    log("\n[Step 0] Processing user feedback from GitHub Issues...")
    processor = GitHubFeedbackProcessor()
    stars, follow_ups, ignores = processor.process_all()

    # 加载已归档的 papers.json 获取 paper_meta
    latest_dirs = sorted(Path("output").glob("*"))
    paper_meta_cache = {}
    if latest_dirs:
        pj = latest_dirs[-1] / "papers.json"
        if pj.exists():
            with open(pj, "r", encoding="utf-8") as f:
                for p in json.load(f):
                    key = p.get("doi", "") or p.get("arxiv_id", "") or p.get("title", "")[:50]
                    paper_meta_cache[key] = p

    for star in stars:
        meta = paper_meta_cache.get(star["paper_key"], {"title": star["paper_key"]})
        mufb.add_star(star["user_email"], star["paper_key"], meta)
        log(f"  → Starred by {star['user_email']}: {star['paper_key'][:50]}...")

    for fu in follow_ups:
        meta = paper_meta_cache.get(fu["paper_key"], {"title": fu["paper_key"]})
        mufb.add_follow_up(fu["user_email"], fu["paper_key"], meta, days=3)
        log(f"  → Follow-up by {fu['user_email']}: {fu['paper_key'][:50]}...")

    for ign in ignores:
        mufb.add_ignore(ign["user_email"], ign["paper_key"])
        log(f"  → Ignored by {ign['user_email']}: {ign['paper_key'][:50]}...")

    mufb.save()
    log(f"✅ Feedback processed: {len(stars)} stars, {len(follow_ups)} follow-ups, {len(ignores)} ignores")

    # 获取今日到期的 follow_ups
    due_reminders = mufb.get_due_follow_ups()
    log(f"  → {len(due_reminders)} follow-up reminders due today")

    # 1. 获取文献
    log("\n[Step 1] Fetching papers from all sources...")
    fetcher = PaperFetcher()
    raw_papers = fetcher.fetch_all(lookback_days=cfg.lookback_days)
    log(f"✅ Raw papers fetched: {len(raw_papers)}")

    # 2. 去重
    log("\n[Step 2] Deduplicating...")
    unique_papers = []
    for p in raw_papers:
        if not dedup.is_seen(p):
            unique_papers.append(p)
    log(f"✅ Unique papers: {len(unique_papers)} (dedup removed {len(raw_papers) - len(unique_papers)})")

    # 3. 评分过滤
    log("\n[Step 3] Scoring and filtering...")
    filtered = fetcher.score_and_filter(unique_papers)
    log(f"✅ After strict filtering: {len(filtered)}")

    # 4. 反馈过滤（忽略已标记的）
    log("\n[Step 4] Applying feedback filters...")
    final_candidates = []
    for p in filtered:
        if p.get("ignored_by"):
            log(f"  → Skipped (ignored by users): {p.get('title', '')[:50]}... | {p['ignored_by']}")
            continue
        final_candidates.append(p)
    log(f"✅ After feedback filter: {len(final_candidates)}")

    if not final_candidates:
        log("⚠️ No new papers found today after all filters.")
        sender = EmailSender()
        sender.send_digest([], "今日无匹配的新文献（所有文献被过滤或已推送过）", due_reminders)
        dedup.save()
        mufb.save()
        return

    # 5. LLM 总结
    log("\n[Step 5] Summarizing with LLM...")
    summarizer = PaperSummarizer()
    papers = summarizer.summarize_papers(final_candidates)
    log("✅ Summarization complete")

    # 6. 按 LLM 评分二次排序，取前 N 篇发邮件
    log("\n[Step 6] Selecting top papers for email...")
    papers.sort(key=lambda x: x.get("summary", {}).get("relevance_score", 0), reverse=True)
    email_papers = [p for p in papers if p.get("summary", {}).get("relevance_score", 0) >= cfg.min_relevance_score]
    if len(email_papers) < 3 and papers:
        email_papers = papers[:10]
    email_papers = email_papers[:cfg.max_email_papers]
    log(f"✅ Selected {len(email_papers)} papers for email (score >= {cfg.min_relevance_score}, max {cfg.max_email_papers})")

    # 7. 生成 Markdown 归档
    log("\n[Step 7] Generating digest archive...")
    output_dir = Path("output") / datetime.now().strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_digest = summarizer.generate_digest(papers)
    all_path = output_dir / "digest_all.md"
    with open(all_path, "w", encoding="utf-8") as f:
        f.write(all_digest)
    log(f"✅ Full digest saved to {all_path} ({len(papers)} papers)")

    email_digest = summarizer.generate_digest(email_papers)
    email_path = output_dir / "digest.md"
    with open(email_path, "w", encoding="utf-8") as f:
        f.write(email_digest)
    log(f"✅ Email digest saved to {email_path} ({len(email_papers)} papers)")

    data_path = output_dir / "papers.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    log(f"✅ Data saved to {data_path}")

    # 8. 标记已见
    log("\n[Step 8] Marking papers as seen...")
    for p in papers:
        dedup.mark_seen(p)
    dedup.save()
    mufb.save()
    log("✅ Dedup and feedback state saved")

    # 9. 发送邮件（包含待跟进提醒）
    log("\n[Step 9] Sending email...")
    sender = EmailSender()
    success = sender.send_digest(email_papers, email_digest, due_reminders)
    if success:
        log("✅ Email sent successfully")
    else:
        log("❌ Email failed to send (check SMTP settings)")

    log("\n" + "=" * 60)
    log(f"🎉 Daily digest complete! {len(email_papers)} papers emailed, {len(papers)} archived, {len(due_reminders)} reminders.")
    log("=" * 60)


if __name__ == "__main__":
    main()
