#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 总结模块：强制中文 + 评分截断 + 重试 + 代码预提取
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
                p["summary"] = self._fallback_summary(abstract, p.get("relevance_score", 5))
            return papers

        for i, p in enumerate(papers):
            log(f"Processing {i+1}/{len(papers)}: {p.get('title', '')[:50]}...")
            summary = None
            for attempt in range(2):
                try:
                    summary = self._summarize_single(p)
                    if summary.get("one_sentence") and summary["one_sentence"] != "信息不足":
                        break
                except Exception as e:
                    log(f"  → Attempt {attempt+1} failed: {e}")
                    time.sleep(1)

            if not summary or not summary.get("one_sentence"):
                abstract = p.get("abstract", "")
                summary = self._fallback_summary(abstract, p.get("relevance_score", 5))
                log(f"  → Fallback after retries")

            # 强制截断到 1-10
            try:
                raw_score = int(summary.get("relevance_score", 5))
                summary["relevance_score"] = max(1, min(raw_score, 10))
            except (ValueError, TypeError):
                summary["relevance_score"] = min(p.get("relevance_score", 5), 10)

            p["summary"] = summary
            log(f"  → Final Score: {summary['relevance_score']}/10, Summary: {summary.get('one_sentence', '')[:40]}...")
            time.sleep(0.3)
        return papers

    def _fallback_summary(self, abstract: str, pre_score: int) -> Dict:
        first_sentence = abstract.split(".")[0] if abstract else "信息不足"
        if len(first_sentence) > 120:
            first_sentence = first_sentence[:120] + "..."
        return {
            "one_sentence": f"【LLM总结失败，显示摘要首句】{first_sentence}",
            "method_innovation": "LLM 解析失败，请查看原文摘要。",
            "key_metrics": "信息不足",
            "code_repo": self._extract_code_from_text(abstract),
            "relevance_score": min(pre_score, 10),
            "action_recommendation": "建议阅读原文获取详细信息"
        }

    def _summarize_single(self, paper: Dict) -> Dict:
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        source = paper.get("source", "")
        journal = paper.get("journal", "")
        match_reason = paper.get("match_reason", "")
        pre_score = paper.get("relevance_score", 5)
        pre_extracted_code = self._extract_code_from_text(abstract)

        # 用户兴趣上下文
        star_context = ""
        try:
            from github_feedback import MultiUserFeedbackStore
            mufb = MultiUserFeedbackStore()
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

        prompt = f"""你是一位基因组学与生物信息学领域的资深审稿人。请对以下论文进行**精准中文提炼**。

【论文信息】
来源：{source}
期刊：{journal}
标题：{title}
摘要：{abstract[:2000]}
匹配关键词：{match_reason}
初步相关性分数：{pre_score}/10{star_context}

【绝对要求 - 违反则输出无效】
1. **所有输出必须是中文**（专业术语保留英文，如 Sniffles2, hifiasm, BUSCO）
2. **禁止直接复制摘要原文**，必须用自己的语言重新组织
3. **relevance_score 必须是 1-10 的整数**，严禁超出此范围
4. **必须输出纯 JSON**，不要```json 标记，不要任何前言、后语、解释

【输出格式 - 严格 JSON】
{{
  "one_sentence": "用一句话精准概括核心发现（中文，40-60字，禁止复制摘要原文）",
  "method_innovation": "方法学核心创新点（中文，80字以内，具体到工具名、技术路线、实验设计）",
  "key_metrics": "核心指标（中文，40字以内，如 QV=72.3, BUSCO=98.4%, F1=0.94）",
  "code_repo": "代码仓库链接，或'未提供'，或'信息不足'",
  "relevance_score": 0,
  "action_recommendation": "推荐操作（中文，25字以内，如'建议测试该工具在猪数据上的效果'）"
}}

【relevance_score 评分标准】（1-10 整数，必须严格遵守）
- 10分：直接涉及猪基因组/Myrmecia/牛蚁属/结构变异工具开发/Hi-C组装/抗冻蛋白结构功能
- 8-9分：基因组组装、节肢动物基因组、长读长测序方法学、三维基因组学，方法可迁移
- 5-7分：一般生物信息学工具、比较基因组学、进化分析，有参考价值
- 1-4分：边缘相关或方法不直接相关
- **当前文献初步分{pre_score}，请结合内容深度判断，最终分必须1-10整数**

【one_sentence 写作要求】
- 必须说明"做了什么" + "核心发现/意义"
- 示例："利用hifiasm+trio-binning完成牛蚁属染色体级组装，揭示n=1极端单倍型演化机制"
- 反例（禁止）："Cremastra appendiculata是一种濒危兰科植物..."（这是复制摘要背景）

【method_innovation 写作要求】
- 列出具体工具/算法/实验设计创新
- 示例："采用hifiasm trio模式解析单倍型；yahs+Juicer挂载率98.7%；merqury评估QV=72.3"
- 反例（禁止）："该研究对兰花基因组进行了组装..."（太笼统）

如果摘要信息确实无法提取某字段，该字段写"信息不足"，但one_sentence必须填写。
"""

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 800}
        chat_url = f"{self.base_url}/chat/completions"
        if not chat_url.startswith("http"):
            chat_url = f"https://{chat_url}"

        r = requests.post(chat_url, headers=headers, json=payload, timeout=90)
        r.raise_for_status()
        result = r.json()
        content = result["choices"][0]["message"]["content"].strip()

        content = re.sub(r'^```json\s*', '', content, flags=re.IGNORECASE)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        content = content.strip()

        think_match = re.search(r'\s*think\s*>(.*)', content, re.DOTALL)
        if think_match:
            content = think_match.group(1).strip()

        summary = self._robust_json_parse(content)

        required = ["one_sentence", "method_innovation", "key_metrics", "code_repo", "relevance_score", "action_recommendation"]
        for field in required:
            if field not in summary or not summary[field]:
                if field == "relevance_score":
                    summary[field] = pre_score
                elif field == "code_repo":
                    summary[field] = pre_extracted_code or "未提供"
                else:
                    summary[field] = "信息不足"

        one = summary.get("one_sentence", "")
        if len(one) > 150 or (abstract and one.lower().startswith(abstract[:30].lower())):
            summary["one_sentence"] = f"【可能未提炼】{one[:100]}..."

        return summary

    def _robust_json_parse(self, text: str) -> Dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        fixed = text.replace("'", '"')
        fixed = re.sub(r',\s*}', '}', fixed)
        fixed = re.sub(r',\s*]', ']', fixed)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
        result = {}
        for key in ["one_sentence", "method_innovation", "key_metrics", "code_repo", "relevance_score", "action_recommendation"]:
            m = re.search(rf'"{key}"\s*:\s*"([^"]*)"', text, re.IGNORECASE)
            if m:
                result[key] = m.group(1)
            else:
                m = re.search(rf'"{key}"\s*:\s*(\d+)', text, re.IGNORECASE)
                if m:
                    result[key] = int(m.group(1))
        return result

    def _extract_code_from_text(self, text: str) -> str:
        if not text:
            return ""
        for pattern in [r'https?://github\.com/[\w\-]+/[\w\-]+/?[\w\-]*', r'https?://gitlab\.com/[\w\-]+/[\w\-]+', r'https?://zenodo\.org/record/\d+', r'https?://figshare\.com/articles/[^)\s]+']:
            m = re.search(pattern, text)
            if m:
                return m.group()
        return ""

    def generate_digest(self, papers: List[Dict]) -> str:
        lines = [f"# 📚 每日文献综述 | {datetime.now().strftime('%Y-%m-%d')}", "", f"共 **{len(papers)}** 篇高相关性文献", "", "---", ""]
        for i, p in enumerate(papers[:15], 1):
            s = p.get("summary", {}) if isinstance(p.get("summary"), dict) else {}
            one, rel, innov, metrics, code, action = s.get("one_sentence", ""), s.get("relevance_score", 0), s.get("method_innovation", ""), s.get("key_metrics", ""), s.get("code_repo", ""), s.get("action_recommendation", "")
            lines.append(f"## {i}. [{p.get('title', 'Untitled')}]({p.get('url', '#')})")
            lines.append("")
            lines.append(f"- **来源**: {p.get('source', 'N/A')} | **相关性**: {rel}/10 | **匹配**: {p.get('match_reason', 'N/A')}")
            lines.append(f"- **期刊**: {p.get('journal', 'N/A')} | **作者**: {p.get('authors', 'N/A')} | **日期**: {p.get('date', 'N/A')}")
            lines.append("")
            if one: lines.append(f"**💡 一句话总结**: {one}")
            if innov and innov != "信息不足": lines.append(f"**🔧 方法创新**: {innov}")
            if metrics and metrics != "信息不足": lines.append(f"**📊 核心指标**: {metrics}")
            if code and code not in ("未提供", "信息不足", ""): lines.append(f"**💻 代码仓库**: {code}")
            if action and action != "信息不足": lines.append(f"**🎯 推荐操作**: {action}")
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
        lines = [f"# 📈 本周文献趋势报告 | {datetime.now().strftime('%Y-%m-%d')}", "", f"本周共监控 **{len(history_papers)}** 篇文献", "", "## 热点关键词 TOP10", ""]
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
    import glob, json as json_lib
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
