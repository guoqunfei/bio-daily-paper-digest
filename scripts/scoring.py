#!/usr/bin/env python3
"""
Scoring Module - Relevance scoring engine for papers
相关性评分引擎：基于关键词、方法学语境、物种/工具匹配的分层评分
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ScoringConfig:
    """Scoring configuration"""
    # 白名单关键词（出现在标题/摘要中加分）
    whitelist: List[str]
    # 黑名单关键词（出现则直接排除）
    blacklist: List[str]
    # 高优先级关键词（直接涉及用户研究领域）
    high_priority: List[str]
    # 监控的物种
    species: List[str]
    # 监控的工具
    tools: List[str]
    # 监控的课题组/作者
    labs: List[str]
    # 相关性阈值（低于此分数的论文被过滤）
    min_score: float = 5.0
    # 每日推送上限
    max_daily_papers: int = 15


def get_default_config() -> ScoringConfig:
    """Get default scoring configuration"""
    return ScoringConfig(
        whitelist=[
            # 核心技术
            "structural variation", "genome assembly", "genome annotation",
            "comparative genomics", "functional genomics",
            # 测序技术
            "long-read sequencing", "pacbio", "oxford nanopore", "hifi reads",
            "nanopore", "third-generation sequencing",
            # 三维基因组
            "hi-c", "chromatin conformation", "tad", "3d genome",
            "scaffolding", "chromosome-level",
            # 变异检测
            "snp calling", "indel", "sv calling", "structural variant",
            "copy number variation", "population genomics",
            # 节肢动物/抗冻蛋白
            "antifreeze protein", "arthropod", "insect", "myrmecia",
            "bull ant", "ant genome", "invertebrate",
            # 猪基因组
            "pig genome", "sus scrofa", "porcine", "swine",
            # 方法学
            "benchmark", "pipeline", "workflow", "snakemake", "nextflow",
            "docker", "container", "singularity",
        ],
        blacklist=[
            # 临床/医学
            "clinical trial", "patient", "cancer therapy", "oncology",
            "disease", "drug", "treatment", "therapeutic",
            "hospital", "medical", "diagnosis", "prognosis",
            "covid-19", "sars-cov", "pandemic",
            # 纯植物（非基因组组装）
            "crop yield", "agronomy", "fertilizer",
            # 纯人类医学
            "human genome", "patient cohort", "clinical",
        ],
        high_priority=[
            # 直接相关的物种
            "myrmecia", "bull ant", "ant genome",
            "sus scrofa", "pig genome", "porcine genome",
            # 直接相关的技术
            "structural variation", "genome assembly", "scaffolding",
            "hi-c scaffolding", "yahs", "hifiasm",
            "antifreeze protein", "afp", "ice-binding",
            # 直接相关的工具
            "sniffles", "svim", "pbsv", "cuteSV",
            "purge_haplotigs", "merqury", "busco",
        ],
        species=[
            "myrmecia", "bull ant", "ant", "arthropod", "insect",
            "sus scrofa", "pig", "porcine", "swine",
        ],
        tools=[
            "hifiasm", "yahs", "sniffles", "svim", "pbsv", "cutesv",
            "purge_haplotigs", "merqury", "busco", "quast",
            "lra", "minimap2", "ngmlr",
        ],
        labs=[
            "t2t consortium", "telomere-to-telomere",
        ],
        min_score=5.0,
        max_daily_papers=15,
    )


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.lower().strip()


def _contains_any(text: str, keywords: List[str]) -> Tuple[bool, List[str]]:
    """Check if text contains any of the keywords, return matched keywords"""
    text_lower = _normalize_text(text)
    matched = []
    for kw in keywords:
        if kw.lower() in text_lower:
            matched.append(kw)
    return len(matched) > 0, matched


def check_blacklist(paper: Dict, blacklist: List[str]) -> bool:
    """Check if paper should be excluded based on blacklist
    
    Returns: True if paper should be excluded
    """
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
    excluded, _ = _contains_any(text, blacklist)
    return excluded


def calculate_relevance_score(paper: Dict, config: ScoringConfig) -> Tuple[float, str]:
    """Calculate relevance score for a paper (0-10 scale)
    
    Returns: (score, reason)
    """
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    text = f"{title} {abstract}"
    text_lower = _normalize_text(text)
    
    score = 0.0
    reasons = []
    
    # 1. 黑名单检查（如果命中直接返回 0 分）
    excluded, matched_blacklist = _contains_any(text, config.blacklist)
    if excluded:
        # 但如果同时命中高优先级关键词，给予豁免
        has_high_priority, _ = _contains_any(text, config.high_priority)
        if not has_high_priority:
            return 0.0, f"黑名单匹配: {', '.join(matched_blacklist[:3])}"
    
    # 2. 高优先级关键词匹配（必读级，+3~5分）
    _, matched_high = _contains_any(text, config.high_priority)
    if matched_high:
        score += min(3.0 + len(matched_high) * 0.5, 5.0)
        reasons.append(f"高优先级关键词: {', '.join(matched_high[:3])}")
    
    # 3. 白名单关键词匹配（+1~2分）
    _, matched_white = _contains_any(text, config.whitelist)
    if matched_white:
        score += min(1.0 + len(matched_white) * 0.3, 2.0)
        reasons.append(f"白名单关键词: {', '.join(matched_white[:3])}")
    
    # 4. 物种匹配（+2分）
    _, matched_species = _contains_any(text, config.species)
    if matched_species:
        score += 2.0
        reasons.append(f"目标物种: {', '.join(matched_species[:2])}")
    
    # 5. 工具匹配（+1.5分）
    _, matched_tools = _contains_any(text, config.tools)
    if matched_tools:
        score += 1.5
        reasons.append(f"工具匹配: {', '.join(matched_tools[:2])}")
    
    # 6. 来源加分
    source = paper.get("source", "").lower()
    if "arxiv" in source or "biorxiv" in source:
        # 预印本中方法学论文比例更高
        score += 0.5
    
    # 7. 标题加权（标题匹配比摘要匹配更重要）
    _, title_matched = _contains_any(title, config.whitelist + config.high_priority)
    if title_matched:
        score += 1.0
    
    # 8. 封顶和保底
    score = min(score, 10.0)
    
    # 如果没有命中任何关键词，保底给 3 分（避免误杀）
    if score == 0.0 and not reasons:
        score = 3.0
        reasons.append("基础相关")
    
    reason_str = "; ".join(reasons) if reasons else "基础相关"
    return round(score, 1), reason_str


def filter_and_score_papers(papers: List[Dict], config: ScoringConfig = None) -> List[Dict]:
    """Filter and score papers, return sorted by relevance
    
    Returns: List of papers with added 'relevance_score' and 'relevance_reason' fields
    """
    if config is None:
        config = get_default_config()
    
    scored_papers = []
    
    for paper in papers:
        # 黑名单过滤
        if check_blacklist(paper, config.blacklist):
            score, reason = 0.0, "黑名单过滤"
        else:
            score, reason = calculate_relevance_score(paper, config)
        
        paper_copy = paper.copy()
        paper_copy["relevance_score"] = score
        paper_copy["relevance_reason"] = reason
        scored_papers.append(paper_copy)
    
    # 按相关性分数排序（降序）
    scored_papers.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return scored_papers


def get_score_level(score: float) -> str:
    """Get score level label"""
    if score >= 8.0:
        return "必读"
    elif score >= 6.0:
        return "重要"
    elif score >= 4.0:
        return "参考"
    else:
        return "忽略"


def get_score_badge(score: float) -> str:
    """Get score badge for display (color-coded)"""
    if score >= 8.0:
        return "🟢"
    elif score >= 6.0:
        return "🟠"
    elif score >= 4.0:
        return "🔵"
    else:
        return "⚪"


if __name__ == "__main__":
    # Test scoring
    test_paper = {
        "title": "De novo assembly of the Myrmecia bull ant genome using HiFi and Hi-C data",
        "abstract": "We present a chromosome-level genome assembly of the bull ant Myrmecia...",
        "source": "arXiv"
    }
    
    config = get_default_config()
    score, reason = calculate_relevance_score(test_paper, config)
    print(f"Score: {score}/10")
    print(f"Level: {get_score_level(score)}")
    print(f"Reason: {reason}")
