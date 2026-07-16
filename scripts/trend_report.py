#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""周趋势报告生成：读取最近7天的 output 目录，生成趋势 Markdown"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from summarize import PaperSummarizer


def main():
    print("[TREND] Generating weekly trend report...")
    all_papers = []
    today = datetime.now()
    for i in range(7):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        pj = Path("output") / date_str / "papers.json"
        if pj.exists():
            with open(pj, "r", encoding="utf-8") as f:
                all_papers.extend(json.load(f))
    if not all_papers:
        print("[TREND] No data found for the past 7 days")
        return
    print(f"[TREND] Loaded {len(all_papers)} papers from past 7 days")

    keywords = Counter()
    sources = Counter()
    high_score_papers = []
    for p in all_papers:
        sources[p.get("source", "Unknown")] += 1
        for kw in p.get("match_reason", "").split(", "):
            kw_clean = kw.strip().replace("[HIGH]", "")
            if kw_clean:
                keywords[kw_clean] += 1
        s = p.get("summary", {})
        if isinstance(s, dict) and s.get("relevance_score", 0) >= 8:
            high_score_papers.append(p)

    lines = [
        f"# 📈 本周文献趋势报告 | {datetime.now().strftime('%Y-%m-%d')}",
        "",
        f"本周共监控 **{len(all_papers)}** 篇文献",
        "",
        "## 来源分布",
        ""
    ]
    for src, cnt in sources.most_common():
        lines.append(f"- {src}: {cnt} 篇")
    lines.extend(["", "## 热点关键词 TOP15", ""])
    for kw, cnt in keywords.most_common(15):
        lines.append(f"- {kw}: {cnt} 篇")
    lines.extend(["", f"## 高分文献回顾（≥8分）共 {len(high_score_papers)} 篇", ""])
    for p in sorted(high_score_papers, key=lambda x: x.get("summary", {}).get("relevance_score", 0), reverse=True)[:15]:
        s = p.get("summary", {})
        lines.append(f"- [{p.get('title', '')}]({p.get('url', '#')}) | **{s.get('relevance_score', 0)}/10** | {s.get('one_sentence', '')[:80]}...")
    lines.extend(["", "---", "", "由 GitHub Actions 自动生成"])

    report = "\n".join(lines)
    output_dir = Path("output") / "trend-reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"weekly-{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[TREND] Report saved to {report_path}")


if __name__ == "__main__":
    main()
