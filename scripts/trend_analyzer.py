#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势分析模块：历史回溯、关键词演化、个人待办
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent))
from github_feedback import MultiUserFeedbackStore


def log(msg: str):
    print(f"[TREND] {msg}")
    sys.stdout.flush()


class TrendAnalyzer:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.mufb = MultiUserFeedbackStore()

    def analyze_last_n_days(self, n: int = 30) -> Dict:
        """分析最近 n 天的所有文献"""
        all_papers = []
        today = datetime.now()
        for i in range(n):
            date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            pj = self.output_dir / date_str / "papers.json"
            if pj.exists():
                with open(pj, "r", encoding="utf-8") as f:
                    all_papers.extend(json.load(f))

        if not all_papers:
            return {}

        log(f"Loaded {len(all_papers)} papers from last {n} days")

        # 1. 关键词趋势
        keywords = Counter()
        tools = Counter()
        species = Counter()

        for p in all_papers:
            # 关键词
            for kw in p.get("match_reason", "").split(", "):
                kw_clean = kw.strip().replace("[HIGH]", "")
                if kw_clean and len(kw_clean) < 50:
                    keywords[kw_clean] += 1

            # 工具探测（从标题和摘要）
            text = f"{p.get('title', '')} {p.get('abstract', '')}".lower()
            tool_list = ["sniffles", "sniffles2", "cutesv", "svim", "pbsv", "truvari",
                        "hifiasm", "canu", "flye", "yahs", "juicer", "3d-dna", "salsa",
                        "nextpolish", "purge_haplotigs", "merqury", "busco", "quast",
                        "getorganelle", "mitos", "alphaFold", "alphaFold3"]
            for t in tool_list:
                if t in text:
                    tools[t] += 1

            # 物种探测
            species_list = ["myrmecia", "bull ant", "pig", "sus scrofa", "porcine",
                           "antifreeze protein", "afp", "arthropod", "insect", "orchid"]
            for s in species_list:
                if s in text:
                    species[s] += 1

        # 2. 高分文献时间线
        high_score_papers = []
        for p in all_papers:
            s = p.get("summary", {})
            if isinstance(s, dict) and s.get("relevance_score", 0) >= 8:
                high_score_papers.append({
                    "date": p.get("date", "未知"),
                    "title": p.get("title", ""),
                    "url": p.get("url", ""),
                    "score": s.get("relevance_score", 0),
                    "one_sentence": s.get("one_sentence", "")[:80]
                })
        high_score_papers.sort(key=lambda x: x["date"], reverse=True)

        return {
            "period_days": n,
            "total_papers": len(all_papers),
            "top_keywords": keywords.most_common(20),
            "emerging_tools": tools.most_common(15),
            "hot_species": species.most_common(10),
            "high_score_timeline": high_score_papers[:20]
        }

    def generate_trend_report(self, n: int = 30) -> str:
        """生成 Markdown 趋势报告"""
        data = self.analyze_last_n_days(n)
        if not data:
            return "# 📈 趋势报告\n\n暂无历史数据。"

        lines = [
            f"# 📈 近{data['period_days']}天文献趋势报告 | {datetime.now().strftime('%Y-%m-%d')}",
            "",
            f"共监控 **{data['total_papers']}** 篇文献",
            "",
            "## 🔥 热点关键词 TOP20",
            ""
        ]
        for kw, cnt in data["top_keywords"]:
            lines.append(f"- **{kw}**: {cnt} 篇")

        lines.extend(["", "## 🛠️ 新兴工具/方法", ""])
        for tool, cnt in data["emerging_tools"]:
            lines.append(f"- **{tool}**: {cnt} 次出现")

        lines.extend(["", "## 🧬 热门物种/领域", ""])
        for sp, cnt in data["hot_species"]:
            lines.append(f"- **{sp}**: {cnt} 篇")

        lines.extend(["", "## ⭐ 高分文献时间线（≥8分）", ""])
        for p in data["high_score_timeline"]:
            lines.append(f"- **{p['date']}** | [{p['title'][:60]}...]({p['url']}) | **{p['score']}/10** | {p['one_sentence']}...")

        lines.extend(["", "---", "", "由 GitHub Actions 自动生成"])
        return "\n".join(lines)

    def get_personal_todo(self, email: str) -> List[Dict]:
        """获取某用户的待办跟进列表"""
        follow_ups = self.mufb.get_due_follow_ups(email)
        # 也包含未到期的
        all_pending = [fu for fu in self.mufb.data.get("follow_ups", []) 
                        if fu.get("status") == "pending" and fu.get("user_email") == email]
        return all_pending

    def generate_personal_digest(self, email: str) -> str:
        """生成个人待办摘要（可嵌入邮件）"""
        todos = self.get_personal_todo(email)
        if not todos:
            return ""

        lines = ["## ⏰ 您的待办跟进", ""]
        for fu in todos[:10]:
            status = "🔴 已到期" if fu.get("due_date", "") <= datetime.now().strftime("%Y-%m-%d") else "🟡 待跟进"
            lines.append(f"- {status} [{fu.get('paper_title', fu['paper_key'])[:50]}...]({fu.get('paper_url', '#')}) "
                        f"(标记于 {fu.get('created_at', '')[:10]})")
        lines.append("")
        return "\n".join(lines)


if __name__ == "__main__":
    analyzer = TrendAnalyzer()
    report = analyzer.generate_trend_report(30)
    print(report[:500])
