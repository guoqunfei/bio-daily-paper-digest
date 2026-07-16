#!/usr/bin/env python3
"""
主程序：每日文献综述入口
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from fetch_papers import PaperFetcher
from summarize import PaperSummarizer
from send_email import EmailSender


def main():
    print("=" * 60)
    print("🧬 Bio Daily Paper Digest - 每日文献综述")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 获取文献
    print("\n[Step 1] Fetching papers...")
    fetcher = PaperFetcher()
    papers = fetcher.fetch_all(lookback_days=1)
    print(f"✅ Total papers fetched: {len(papers)}")

    if not papers:
        print("⚠️ No new papers found today.")
        # 发送空邮件通知
        sender = EmailSender()
        sender.send_digest([], "今日无新文献")
        return

    # 2. LLM 总结
    print("\n[Step 2] Summarizing with LLM (gpt-5.5)...")
    summarizer = PaperSummarizer()
    papers = summarizer.summarize_papers(papers)
    print("✅ Summarization complete")

    # 3. 生成综述 Markdown
    print("\n[Step 3] Generating digest...")
    digest_md = summarizer.generate_digest(papers)

    # 保存到 output
    output_dir = Path("output") / datetime.now().strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)

    digest_path = output_dir / "digest.md"
    with open(digest_path, "w", encoding="utf-8") as f:
        f.write(digest_md)
    print(f"✅ Digest saved to {digest_path}")

    # 保存原始数据
    data_path = output_dir / "papers.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    print(f"✅ Data saved to {data_path}")

    # 4. 发送邮件
    print("\n[Step 4] Sending email...")
    sender = EmailSender()
    success = sender.send_digest(papers, digest_md)
    if success:
        print("✅ Email sent successfully")
    else:
        print("❌ Email failed to send")

    print("\n" + "=" * 60)
    print("🎉 Daily digest complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
