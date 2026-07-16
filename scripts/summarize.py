#!/usr/bin/env python3
"""
LLM 总结模块：使用 gpt-5.5 对文献进行结构化总结
"""

import os
import json
import urllib.request
import urllib.error
from typing import List, Dict


class PaperSummarizer:
    """文献总结器"""

    def __init__(self):
        self.api_key = os.environ.get("LLM_API_KEY", "")
        self.base_url = os.environ.get("LLM_BASE_URL", "https://dcsapi.dcs.cloud/api/aigress/unified/v1")
        self.model = os.environ.get("LLM_MODEL", "gpt-5.5")

    def summarize_papers(self, papers: List[Dict]) -> List[Dict]:
        """对文献列表进行总结"""
        summarized = []
        for i, paper in enumerate(papers[:15]):  # 最多总结15篇
            print(f"[Summarize] Processing {i+1}/{len(papers[:15])}: {paper['title'][:60]}...")
            try:
                summary = self._summarize_single(paper)
                paper["summary"] = summary
                summarized.append(paper)
            except Exception as e:
                print(f"[Summarize Error] {e}")
                paper["summary"] = {"error": str(e)}
                summarized.append(paper)
        return summarized

    def _summarize_single(self, paper: Dict) -> Dict:
        """对单篇文献进行总结"""
        prompt = self._build_prompt(paper)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a senior bioinformatics reviewer. Analyze papers in Chinese."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2048
        }

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(data).encode(),
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            content = result["choices"][0]["message"]["content"]
            return self._parse_response(content)

    def _build_prompt(self, paper: Dict) -> str:
        """构建提示词"""
        return f"""你是一位基因组学与生物信息学领域的资深审稿人。请对以下论文进行结构化分析，用中文输出：

1. **一句话总结**：核心痛点与解决方案
2. **方法创新**：算法/实验设计的关键创新点（具体到工具名称如 Sniffles2, bcftools, yahs 等）
3. **数据集**：物种、样本量、测序平台（PacBio/ONT/Hi-C 等）
4. **核心指标**：F1 score、contig N50、BUSCO、QV 等
5. **代码仓库**：GitHub 链接或生信流程可用性评估
6. **与你研究的相关性**：1-10 分，并说明理由（关注猪基因组、牛蚁属、抗冻蛋白、结构变异检测等）

请用 JSON 格式输出（不要包含 markdown 代码块标记），格式如下：
{{
    "one_sentence": "...",
    "method_innovation": "...",
    "dataset": "...",
    "core_metrics": "...",
    "code_repo": "...",
    "relevance_score": 8,
    "relevance_reason": "..."
}}

论文标题：{paper['title']}
摘要：{paper.get('abstract', '')}
"""

    def _parse_response(self, content: str) -> Dict:
        """解析 LLM 响应"""
        try:
            # 尝试直接解析 JSON
            import json
            # 移除可能的 markdown 代码块
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return json.loads(content.strip())
        except json.JSONDecodeError:
            # 如果解析失败，返回原始文本
            return {
                "one_sentence": content[:200],
                "method_innovation": "",
                "dataset": "",
                "core_metrics": "",
                "code_repo": "",
                "relevance_score": 0,
                "relevance_reason": "解析失败"
            }

    def generate_digest(self, papers: List[Dict]) -> str:
        """生成每日综述"""
        sections = []
        sections.append("# 📚 每日文献综述\n")
        sections.append(f"**生成时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        sections.append("**覆盖领域**: 结构变异检测 | 基因组组装 | 节肢动物/猪基因组 | 抗冻蛋白 | Hi-C/三维基因组 | 长读长测序\n")
        sections.append("---\n\n")

        # 按来源分组
        sources = {}
        for p in papers:
            source = p.get("source", "Unknown")
            if source not in sources:
                sources[source] = []
            sources[source].append(p)

        for source, spapers in sources.items():
            sections.append(f"## {source} ({len(spapers)} 篇)\n\n")
            for i, p in enumerate(spapers, 1):
                summary = p.get("summary", {})
                if isinstance(summary, dict):
                    one_sentence = summary.get("one_sentence", "")
                    relevance = summary.get("relevance_score", 0)
                else:
                    one_sentence = str(summary)[:100]
                    relevance = 0

                sections.append(f"### {i}. {p['title']}\n\n")
                sections.append(f"- **作者**: {p.get('authors', 'N/A')}\n")
                sections.append(f"- **日期**: {p.get('date', 'N/A')}\n")
                sections.append(f"- **期刊**: {p.get('journal', 'N/A')}\n")
                sections.append(f"- **链接**: {p.get('url', 'N/A')}\n")
                sections.append(f"- **相关性评分**: {relevance}/10\n")
                if one_sentence:
                    sections.append(f"- **总结**: {one_sentence}\n")
                sections.append("\n")

        return "\n".join(sections)
