#!/usr/bin/env python3
"""
Digest Generation Module - Generate structured literature summary using LLM
综述生成模块 - 使用大语言模型生成结构化文献摘要
"""

import os
from typing import List, Dict


def generate_daily_digest(papers: List[Dict], output_path: str) -> None:
    """Generate a markdown digest from paper list"""
    today = os.path.basename(output_path).split("_")[0]

    lines = [
        f"# Daily Literature Digest - {today}",
        "",
        f"> **Total Papers:** {len(papers)}  |  **Sources:** arXiv, PubMed",
        "",
        "---",
        "",
    ]

    for i, paper in enumerate(papers, 1):
        lines.extend([
            f"## {i}. {paper['title']}",
            "",
            f"- **Source:** {paper['source']}  |  **Published:** {paper['published']}",
            f"- **Authors:** {paper['authors']}",
            f"- **URL:** {paper['url']}",
            "",
            "### Abstract",
            "",
            paper['abstract'] if paper['abstract'] else "*No abstract available.*",
            "",
            "---",
            "",
        ])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
