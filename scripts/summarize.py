#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 总结模块：强制中文输出 + 结构化 JSON + 用户历史兴趣上下文校准
"""

import os
import sys
import json
import re
import time
import requests
from datetime import datetime
from typing import List, Dict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def log(msg: str):
    print(f"[SUMMARIZER] {msg}")
    sys.stdout.flush()


class PaperSummarizer:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        log(f"Config: model={self.model}, base_url={self.base_url}")
        if not self.api_key:
            log("⚠️ LLM_API_KEY not set! Will use raw abstracts.")

    def summarize_papers(self, papers: List[Dict]) -> List[Dict]:
        if not self.api_key:
            log("No API key, returning raw abstracts")
            for p in papers:
                abstract = p.get("abstract", "")
                p["summary"] = {
                    "one_sentence": abstract[:150] + "..." if len(abstract) > 150 else abstract,
                    "method_innovation": "LLM 未配置，无法生成方法总结",
                    "key_metrics": "",
                    "code_repo": "未提供",
                    "relevance_score": p.get("relevance_score", 5),
                    "action_recommendation": ""
                }
            return papers
        for i, p in enumerate(papers):
            log(f"Processing {i+1}/{len(papers)}: {p.get('title', '')[:50]}...")
            try:
                summary = self._summarize_single(p)
                p["summary"] = summary
                log(f"  → Score: {summary.get('relevance_score', 'N/A')}, "
                    f"Summary: {summary.get('one_sentence', '')[:40]}...")
            except Exception as e:
                log(f"  → ERROR: {e}")
                abstract = p.get("abstract", "")
                p["summary"] = {
                    "one_sentence": abstract[:200] + "..." if len(abstract) > 200 else abstract,
                    "method_innovation": "LLM 总结失败，显示原始摘要",
                    "key_metrics": "",
                    "code_repo": "未提供",
                    "relevance_score": p.get("relevance_score", 5),
                    "action_recommendation": ""
                }
            time.sleep(0.3)
        return papers

    def _summarize_single(self, paper: Dict) -> Dict:
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        source = paper.get("source", "")
        journal = paper.get("journal", "")
        match_reason = paper.get("match_reason", "")
        pre_score = paper.get("relevance_score", 5)

        # 加载用户历史兴趣上下文
        star_context = ""
        try:
            from github_feedback import MultiUserFeedbackStore
            mufb = MultiUserFeedbackStore()
            # 取所有用户的聚合兴趣作为上下文
            all_keywords = {}
            for email in mufb.data.get("users", {}).keys():
                weights = mufb.get_user_weights(email)
                for kw, w in weights.items():
                    all_keywords[kw] = all_keywords.get(kw, 0) + w
            top_kws = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:5]
            if top_kws:
                star_context = "\n\n【系统用户历史兴趣参考】\n用户高频关注的关键词：" + ", ".join([f"{kw}({w:.1f})" for kw, w in top_kws]) + "\n请结合这些兴趣偏好，更精准地评估相关性。"
        except Exception:
            pass

        prompt = f"""你是一位基因组学与生物信息学领域的资深审稿人。请对以下论文进行结构化分析。

【论文信息】
来源：{source}
期刊：{journal}
标题：{title}
摘要：{abstract}
匹配关键词：{match_reason}
初步相关性分数：{pre_score}/10（基于关键词匹配）{star_context}

【输出要求】
1. 所有输出必须用**中文**（专业术语保留英文，如 Sniffles2, hifiasm, BUSCO, QV, N50）
2. 严格按以下 JSON 格式输出，不要添加任何其他文字、解释或 markdown 代码块
3. 如果摘要信息不足，某些字段可以写"信息不足"，但 one_sentence 必须填写

【输出格式】
{{
  "one_sentence": "用一句话概括核心发现或方法创新（中文，50-80字）",
  "method_innovation": "方法创新的关键要点（中文，列出具体工具/算法/实验设计，100字以内）",
  "key_metrics": "核心指标（如 F1 score、contig N50、BUSCO、QV、TH活性、准确率等，中文描述，50字以内）",
  "code_repo": "代码仓库链接或'未提供'或'信息不足'",
  "relevance_score": 0,
  "action_recommendation": "针对该研究者的推荐操作（如'建议用此工具测试猪基因组数据'、'关注其Hi-C挂载方法'、'可迁移至牛蚁属分析'等，中文，30字以内）"
}}

【relevance_score 评分标准】（1-10 整数，请结合初步分数和深度理解重新评估）
- 10分：直接涉及核心研究（猪基因组、Myrmecia/牛蚁属基因组、结构变异检测工具开发、Hi-C组装方法、抗冻蛋白结构/功能）
- 8-9分：基因组组装、节肢动物基因组、长读长测序方法学、三维基因组学，方法可迁移
- 5-7分：一般生物信息学工具、比较基因组学、进化分析，有参考价值
- 1-4分：边缘相关或方法不直接相关

请只输出纯 JSON，不要```json标记，不要任何前言后语。
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 800
        }
        chat_url = f"{self.base_url}/chat/completions"
        if not chat_url.startswith("http"):
            chat_url = f"https://{chat_url}"
        r = requests.post(chat_url, headers=headers, json=payload, timeout=90)
        r.raise_for_status()
        result = r.json()
        content = result["choices"][0]["message"]["content"].strip()
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        content = content.strip()

        try:
            summary = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                summary = json.loads(match.group())
            else:
                raise ValueError(f"LLM output is not valid JSON: {content[:200]}")

        required = ["one_sentence", "method_innovation", "key_metrics", "code_repo", "relevance_score", "action_recommendation"]
        for field in required:
            if field not in summary:
                summary[field] = ""
            if field != "relevance_score" and not isinstance(summary[field], str):
                summary[field] = str(summary[field])
        try:
            summary["relevance_score"] = int(summary["relevance_score"])
        except (ValueError, TypeError):
            summary["relevance_score"] = pre_score

        if not summary.get("one_sentence", "").strip():
            abstract = paper.get("abstract", "")
            summary["one_sentence"] = abstract[:150] + "..." if len(abstract) > 150 else abstract

        if summary.get("code_repo") in ("", "未提供", "信息不足"):
            gh_match = re.search(r'https?://github\.com/[^\s)\]]+', abstract)
            if gh_match:
                summary["code_repo"] = gh_match.group()
        return summary

    def generate_digest(self, papers: List[Dict]) -> str:
        lines = [
            f"# 📚 每日文献综述 | {datetime.now().strftime('%Y-%m-%d')}",
            "",
            f"共 **{len(papers)}** 篇高相关性文献（已过滤低分噪音）",
            "",
            "---",
            ""
        ]
        for i, p in enumerate(papers[:15], 1):
            s = p.get("summary", {}) if isinstance(p.get("summary"), dict) else {}
            one = s.get("one_sentence", "")
            rel = s.get("relevance_score", 0)
            innov = s.get("method_innovation", "")
            metrics = s.get("key_metrics", "")
            code = s.get("code_repo", "")
            action = s.get("action_recommendation", "")
            lines.append(f"## {i}. [{p.get('title', 'Untitled')}]({p.get('url', '#')})")
            lines.append("")
            lines.append(f"- **来源**: {p.get('source', 'N/A')} | **相关性**: {rel}/10 | **匹配**: {p.get('match_reason', 'N/A')}")
            lines.append(f"- **期刊**: {p.get('journal', 'N/A')} | **作者**: {p.get('authors', 'N/A')} | **日期**: {p.get('date', 'N/A')}")
            lines.append("")
            if one:
                lines.append(f"**💡 一句话总结**: {one}")
            if innov:
                lines.append(f"**🔧 方法创新**: {innov}")
            if metrics:
                lines.append(f"**📊 核心指标**: {metrics}")
            if code and code not in ("未提供", "信息不足", ""):
                lines.append(f"**💻 代码仓库**: {code}")
            if action:
                lines.append(f"**🎯 推荐操作**: {action}")
            lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)

    def generate_weekly_trend(self, history_papers: List[Dict]) -> str:
        from collections import Counter
        keywords = Counter()
        for p in history_papers:
            for kw in p.get("match_reason", "").split(", "):
                keywords[kw.strip()] += 1
        top_kw = keywords.most_common(10)
        lines = [
            f"# 📈 本周文献趋势报告 | {datetime.now().strftime('%Y-%m-%d')}",
            "",
            f"本周共监控 **{len(history_papers)}** 篇文献",
            "",
            "## 热点关键词 TOP10",
            ""
        ]
        for kw, cnt in top_kw:
            lines.append(f"- {kw}: {cnt} 篇")
        lines.extend(["", f"## 高分文献回顾（≥8分）", ""])
        for p in sorted(history_papers, key=lambda x: x.get("summary", {}).get("relevance_score", 0), reverse=True)[:10]:
            s = p.get("summary", {})
            if s.get("relevance_score", 0) >= 8:
                lines.append(f"- [{p.get('title', '')}]({p.get('url', '#')}) | **{s.get('relevance_score', 0)}/10** | {s.get('one_sentence', '')[:60]}...")
        lines.append("")
        return "\n".join(lines)


if __name__ == "__main__":
    import glob
    import json as json_lib
    dirs = sorted(Path("output").glob("*"))
    if dirs:
        latest = dirs[-1]
        pj = latest / "papers.json"
        if pj.exists():
            with open(pj, "r", encoding="utf-8") as f:
                papers = json_lib.load(f)
            summarizer = PaperSummarizer()
            papers = summarizer.summarize_papers(papers[:3])
            print(json_lib.dumps([p["summary"] for p in papers], ensure_ascii=False, indent=2))
