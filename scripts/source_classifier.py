#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
来源分类器：区分预印本 / 顶刊 / 专业期刊
"""

from typing import Dict


class SourceClassifier:
    # 顶刊列表（影响因子高、领域里程碑）
    TOP_JOURNALS = {
        "nature", "science", "cell", "nature genetics", "nature methods",
        "nature biotechnology", "nature communications", "pnas",
        "proceedings of the national academy of sciences",
        "molecular ecology resources", "mer",
        "genome research", "genome biology", "nucleic acids research", "nar",
    }

    # 专业方法学期刊
    METHOD_JOURNALS = {
        "gigascience", "bioinformatics", "bmc bioinformatics",
        "briefings in bioinformatics", "plos computational biology",
        "frontiers in genetics", "peerj", "scientific data",
    }

    # 预印本平台
    PREPRINT_SOURCES = {"arxiv", "biorxiv", "medrxiv", "preprint"}

    @classmethod
    def classify(cls, paper: Dict) -> str:
        """返回: 'preprint' | 'top' | 'method' | 'general'"""
        source = paper.get("source", "").lower()
        journal = paper.get("journal", "").lower()

        # 预印本优先
        if any(s in source for s in cls.PREPRINT_SOURCES):
            return "preprint"
        if any(s in journal for s in cls.PREPRINT_SOURCES):
            return "preprint"

        # 顶刊
        if any(t in journal for t in cls.TOP_JOURNALS):
            return "top"

        # 专业方法学期刊
        if any(m in journal for m in cls.METHOD_JOURNALS):
            return "method"

        return "general"

    @classmethod
    def get_display_name(cls, category: str) -> str:
        return {
            "preprint": "📰 预印本（方法学前沿）",
            "top": "🏆 顶刊（领域里程碑）",
            "method": "🔬 专业期刊（方法学细节）",
            "general": "📑 其他期刊"
        }.get(category, "📑 其他")


if __name__ == "__main__":
    test = {"journal": "Nature Genetics", "source": "PubMed"}
    print(SourceClassifier.classify(test))
