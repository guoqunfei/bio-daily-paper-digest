#!/usr/bin/env python3
"""
Summarize Module - LLM-powered structured paper summarization
结构化摘要：一句话总结 + 方法创新 + 数据集 + 核心指标 + 代码仓库
"""

import os
import re
from typing import List, Dict, Optional


class StructuredSummary:
    """Structured paper summary with key fields"""
    
    def __init__(self):
        self.one_liner: str = ""  # 一句话总结（50-80字）
        self.method_innovation: str = ""  # 方法创新
        self.dataset: str = ""  # 数据集
        self.core_metrics: str = ""  # 核心指标
        self.code_repo: str = ""  # 代码仓库
        self.data_availability: str = ""  # 数据可用性
        self.relevance_score: float = 0.0  # 相关性评分
        self.score_level: str = ""  # 评分等级


class LLMSummarizer:
    """LLM-based structured paper summarization engine"""

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
                    {"role": "system", "content": "You are a bioinformatics research assistant. Summarize academic papers concisely and structurally."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[LLM] API error: {e}")
            return None

    def summarize_paper_structured(self, title: str, abstract: str, language: str = "zh") -> StructuredSummary:
        """Generate structured summary for a single paper"""
        summary = StructuredSummary()
        
        if not self.enabled:
            # Fallback: basic extraction
            summary.one_liner = abstract[:200] + "..." if len(abstract) > 200 else abstract
            summary.method_innovation = "LLM未配置，无法提取"
            summary.dataset = ""
            summary.core_metrics = ""
            summary.code_repo = ""
            summary.data_availability = ""
            return summary

        lang = "用中文" if language == "zh" else "in English"
        
        prompt = f"""请对以下论文进行结构化总结（{lang}），按以下格式输出：

**一句话总结**：（50-80字，格式：利用[工具/方法]完成[目标物种/样本]的[核心发现]，关键指标[数值]）
**方法创新**：（具体工具名、算法改进、实验设计巧思）
**数据集**：（物种、样本量、测序平台如PacBio/ONT/Hi-C）
**核心指标**：（F1 score、N50、BUSCO、QV、活性等，可横向对比的数值）
**代码仓库**：（GitHub链接或"未提供"）
**数据可用性**：（SRA/ENA编号或"未提供"）

Title: {title}
Abstract: {abstract}

请严格按照以下格式输出（每行以对应标签开头）：
ONE_LINER: <一句话总结>
METHOD: <方法创新>
DATASET: <数据集>
METRICS: <核心指标>
CODE: <代码仓库>
DATA: <数据可用性>
"""

        result = self._call(prompt, max_tokens=400)
        
        if result:
            lines = result.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("ONE_LINER:"):
                    summary.one_liner = line.replace("ONE_LINER:", "").strip()
                elif line.startswith("METHOD:"):
                    summary.method_innovation = line.replace("METHOD:", "").strip()
                elif line.startswith("DATASET:"):
                    summary.dataset = line.replace("DATASET:", "").strip()
                elif line.startswith("METRICS:"):
                    summary.core_metrics = line.replace("METRICS:", "").strip()
                elif line.startswith("CODE:"):
                    summary.code_repo = line.replace("CODE:", "").strip()
                elif line.startswith("DATA:"):
                    summary.data_availability = line.replace("DATA:", "").strip()
        
        # Fallback if any field is empty
        if not summary.one_liner:
            summary.one_liner = abstract[:200] + "..." if len(abstract) > 200 else abstract
        if not summary.method_innovation:
            summary.method_innovation = "未提取到方法信息"
        if not summary.dataset:
            summary.dataset = "未提取到数据集信息"
        if not summary.core_metrics:
            summary.core_metrics = "未提取到核心指标"
        if not summary.code_repo:
            summary.code_repo = "未提供"
        if not summary.data_availability:
            summary.data_availability = "未提供"
        
        return summary

    def summarize_paper(self, title: str, abstract: str, language: str = "zh") -> str:
        """Generate one-sentence summary for a single paper (backward compatible)"""
        if not self.enabled:
            return abstract[:200] + "..." if len(abstract) > 200 else abstract

        lang = "用中文" if language == "zh" else "in English"
        prompt = f"""Summarize the following paper in ONE concise sentence ({lang}).
Focus on the main contribution. Format: [工具/方法] + [目标] + [核心发现/指标]

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
