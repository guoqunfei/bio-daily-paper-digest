#!/usr/bin/env python3
"""
Summarize Module - LLM-powered paper summarization
LLM 智能摘要：单篇论文总结 + 领域趋势综述
"""

import os
from typing import List, Dict, Optional


class LLMSummarizer:
    """LLM-based paper summarization engine"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize OpenAI client"""
        if not self.api_key:
            return
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        except ImportError:
            print("[LLM] openai package not installed. LLM features disabled.")
            self.client = None

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def _call(self, prompt: str, max_tokens: int = 800, temperature: float = 0.3) -> Optional[str]:
        """Call LLM API"""
        if not self.client:
            return None
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a bioinformatics research assistant. Summarize academic papers concisely."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[LLM] API error: {e}")
            return None

    def summarize_paper(self, title: str, abstract: str, language: str = "zh") -> str:
        """Generate one-sentence summary for a single paper"""
        if not self.enabled:
            return abstract[:200] + "..." if len(abstract) > 200 else abstract

        lang = "用中文" if language == "zh" else "in English"
        prompt = f"""Summarize the following paper in ONE concise sentence ({lang}).
Focus on the main contribution.

Title: {title}
Abstract: {abstract}

One-sentence summary:"""

        summary = self._call(prompt, max_tokens=150)
        return summary if summary else (abstract[:200] + "..." if len(abstract) > 200 else abstract)

    def generate_overview(self, papers: List[Dict], language: str = "zh") -> str:
        """Generate research trend overview from all papers"""
        if not self.enabled or len(papers) < 2:
            return ""

        lang = "用中文撰写" if language == "zh" else "Write in English"
        paper_list = "\n".join([
            f"{i+1}. {p['title']} ({p['source']})"
            for i, p in enumerate(papers[:10])
        ])

        prompt = f"""Based on these papers, write a brief research trend overview ({lang}).
Highlight main directions and hot topics. Under 200 words.

Papers:
{paper_list}

Overview:"""

        return self._call(prompt, max_tokens=400) or ""

    def generate_weekly_trend(self, papers: List[Dict], language: str = "zh") -> str:
        """Generate weekly deep-dive trend analysis"""
        if not self.enabled:
            return ""

        lang = "用中文撰写" if language == "zh" else "Write in English"
        paper_list = "\n".join([
            f"{i+1}. {p['title']} ({p['source']}, {p['published']})"
            for i, p in enumerate(papers[:20])
        ])

        prompt = f"""Analyze the following weekly paper collection and provide a comprehensive research trend report ({lang}).
Include: 1) Emerging hot topics, 2) Methodological advances, 3) Key findings, 4) Future directions.
Keep it under 500 words.

Weekly Papers:
{paper_list}

Weekly Trend Report:"""

        return self._call(prompt, max_tokens=800) or ""


def get_summarizer() -> LLMSummarizer:
    """Factory function"""
    return LLMSummarizer()
