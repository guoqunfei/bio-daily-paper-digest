#!/usr/bin/env python3
"""
Daily Literature Digest - Main Entry Point
每日文献综述主程序入口
"""

import os
import sys
from datetime import datetime

from fetch_papers import fetch_all_sources
from generate_digest import generate_daily_digest
from send_email import send_digest_email


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[{today}] Starting daily literature digest...")

    # Step 1: Fetch papers from all sources
    papers = fetch_all_sources()
    if not papers:
        print(f"[{today}] No new papers found today. Skipping.")
        return

    print(f"[{today}] Fetched {len(papers)} papers.")

    # Step 2: Generate digest
    os.makedirs("output", exist_ok=True)
    digest_path = f"output/{today}_digest.md"
    generate_daily_digest(papers, digest_path)
    print(f"[{today}] Digest saved to {digest_path}")

    # Step 3: Send email
    send_digest_email(digest_path, paper_count=len(papers))
    print(f"[{today}] Digest email sent.")

    print(f"[{today}] Task completed. Processed {len(papers)} papers.")


if __name__ == "__main__":
    main()
