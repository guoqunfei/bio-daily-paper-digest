#!/usr/bin/env python3
"""
文献获取模块：从 PubMed、arXiv、Semantic Scholar 获取最新文献
"""

import os
import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET


class PaperFetcher:
    """文献获取器"""

    def __init__(self, cache_dir: str = ".paper-digest-cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def fetch_all(self, lookback_days: int = 1) -> List[Dict]:
        """从所有来源获取文献"""
        papers = []

        print("[Fetcher] Fetching from PubMed...")
        papers.extend(self.fetch_pubmed(lookback_days))
        time.sleep(1)

        print("[Fetcher] Fetching from arXiv...")
        papers.extend(self.fetch_arxiv(lookback_days))
        time.sleep(1)

        print("[Fetcher] Fetching from Semantic Scholar...")
        papers.extend(self.fetch_semantic_scholar(lookback_days))

        # 去重（基于 DOI）
        seen_dois = set()
        unique_papers = []
        for p in papers:
            doi = p.get("doi", "")
            if doi and doi in seen_dois:
                continue
            if doi:
                seen_dois.add(doi)
            unique_papers.append(p)

        return unique_papers

    def fetch_pubmed(self, lookback_days: int = 1) -> List[Dict]:
        """从 PubMed 获取文献"""
        papers = []
        try:
            # 构建 PubMed 检索式
            query = self._build_pubmed_query(lookback_days)
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": "50",
                "retmode": "json",
                "sort": "date"
            }
            url = f"{search_url}?{urllib.parse.urlencode(params)}"

            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read().decode())
                ids = data.get("esearchresult", {}).get("idlist", [])

            if not ids:
                return papers

            # 获取详细信息
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "xml"
            }
            fetch_url_str = f"{fetch_url}?{urllib.parse.urlencode(fetch_params)}"

            with urllib.request.urlopen(fetch_url_str, timeout=30) as response:
                xml_data = response.read().decode()

            # 解析 XML
            root = ET.fromstring(xml_data)
            for article in root.findall(".//PubmedArticle"):
                paper = self._parse_pubmed_article(article)
                if paper:
                    papers.append(paper)

        except Exception as e:
            print(f"[PubMed Error] {e}")

        print(f"[PubMed] Fetched {len(papers)} papers")
        return papers

    def _build_pubmed_query(self, lookback_days: int) -> str:
        """构建 PubMed 检索式"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        date_range = f"{start_date.strftime('%Y/%m/%d')}:{end_date.strftime('%Y/%m/%d')}[PDAT]"

        keywords = [
            '"structural variation"[Title/Abstract]',
            '"genome assembly"[Title/Abstract]',
            '"mitochondrial genome"[Title/Abstract]',
            '"antifreeze protein"[Title/Abstract]',
            '"Hi-C"[Title/Abstract]',
            '"long-read sequencing"[Title/Abstract]',
            '"Myrmecia"[Title/Abstract]',
            '"pig genome"[Title/Abstract]',
            '"arthropod genomics"[Title/Abstract]',
            '"TAD"[Title/Abstract]',
            '"chromosome conformation"[Title/Abstract]',
            '"SV calling"[Title/Abstract]',
            '"chromosome-level"[Title/Abstract]',
            '"ice-binding"[Title/Abstract]',
            '"bull ant"[Title/Abstract]',
            '"PacBio"[Title/Abstract]',
            '"Oxford Nanopore"[Title/Abstract]',
            '"3D genome"[Title/Abstract]',
        ]

        query = f"({' OR '.join(keywords)}) AND {date_range}"
        return query

    def _parse_pubmed_article(self, article: ET.Element) -> Optional[Dict]:
        """解析 PubMed XML"""
        try:
            # 标题
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else ""

            # 摘要
            abstract_elem = article.find(".//Abstract/AbstractText")
            abstract = abstract_elem.text if abstract_elem is not None else ""

            # DOI
            doi = ""
            for el in article.findall(".//ArticleId"):
                if el.get("IdType") == "doi":
                    doi = el.text or ""

            # 作者
            authors = []
            for author in article.findall(".//Author"):
                last = author.find("LastName")
                first = author.find("ForeName")
                if last is not None:
                    name = f"{first.text} {last.text}" if first is not None else last.text
                    authors.append(name)

            # 日期
            date_elem = article.find(".//PubDate")
            pub_date = ""
            if date_elem is not None:
                year = date_elem.find("Year")
                month = date_elem.find("Month")
                day = date_elem.find("Day")
                pub_date = f"{year.text or ''}-{month.text or ''}-{day.text or ''}"

            # 期刊
            journal = ""
            journal_elem = article.find(".//Journal/Title")
            if journal_elem is not None:
                journal = journal_elem.text or ""

            # URL
            url = f"https://pubmed.ncbi.nlm.nih.gov/{article.find('.//PMID').text}/" if article.find(".//PMID") is not None else ""

            return {
                "source": "PubMed",
                "title": title,
                "abstract": abstract,
                "authors": ", ".join(authors[:5]),
                "date": pub_date,
                "journal": journal,
                "doi": doi,
                "url": url
            }
        except Exception as e:
            print(f"[PubMed Parse Error] {e}")
            return None

    def fetch_arxiv(self, lookback_days: int = 1) -> List[Dict]:
        """从 arXiv 获取文献"""
        papers = []
        try:
            # arXiv 分类
            categories = ["q-bio.GN", "q-bio.PE", "cs.LG", "q-bio.BM"]
            cat_query = " OR ".join([f"cat:{c}" for c in categories])

            # 构建查询
            keywords = [
                "genome assembly",
                "structural variation",
                "SV calling",
                "Hi-C scaffolding",
                "antifreeze protein",
                "arthropod",
                "mitochondrial",
                "long-read",
                "benchmark"
            ]
            keyword_query = " OR ".join([f'"{kw}"' for kw in keywords])
            query = f"({cat_query}) AND ({keyword_query})"

            # 日期过滤（arXiv 使用 submittedDate）
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            date_filter = f"submittedDate:[{start_date.strftime('%Y%m%d')}0000 TO {end_date.strftime('%Y%m%d')}235959]"

            url = f"http://export.arxiv.org/api/query?search_query={urllib.parse.quote(query + ' AND ' + date_filter)}&start=0&max_results=30&sortBy=submittedDate&sortOrder=descending"

            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read().decode()

            # 解析 Atom feed
            root = ET.fromstring(data)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                title_elem = entry.find("atom:title", ns)
                title = title_elem.text if title_elem is not None else ""

                summary_elem = entry.find("atom:summary", ns)
                summary = summary_elem.text if summary_elem is not None else ""

                authors = []
                for author in entry.findall("atom:author", ns):
                    name = author.find("atom:name", ns)
                    if name is not None:
                        authors.append(name.text)

                link_elem = entry.find("atom:link[@rel='alternate']", ns)
                url = link_elem.get("href") if link_elem is not None else ""

                published_elem = entry.find("atom:published", ns)
                published = published_elem.text[:10] if published_elem is not None else ""

                papers.append({
                    "source": "arXiv",
                    "title": title,
                    "abstract": summary,
                    "authors": ", ".join(authors[:5]),
                    "date": published,
                    "journal": "arXiv",
                    "doi": "",
                    "url": url
                })

        except Exception as e:
            print(f"[arXiv Error] {e}")

        print(f"[arXiv] Fetched {len(papers)} papers")
        return papers

    def fetch_semantic_scholar(self, lookback_days: int = 1) -> List[Dict]:
        """从 Semantic Scholar 获取文献"""
        papers = []
        try:
            api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
            query = "structural variation genome assembly arthropod pig antifreeze protein Hi-C"

            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote(query)}&fields=title,abstract,authors,year,externalIds,url,openAccessPdf&limit=30&sort=publicationDate&order=desc"

            headers = {}
            if api_key:
                headers["x-api-key"] = api_key

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())

            for item in data.get("data", []):
                # 日期过滤
                year = item.get("year", 0)
                if year < datetime.now().year - 1:
                    continue

                authors = [a.get("name", "") for a in item.get("authors", [])[:5]]
                external_ids = item.get("externalIds", {})
                doi = external_ids.get("DOI", "")

                papers.append({
                    "source": "Semantic Scholar",
                    "title": item.get("title", ""),
                    "abstract": item.get("abstract", ""),
                    "authors": ", ".join(authors),
                    "date": str(year),
                    "journal": "",
                    "doi": doi,
                    "url": item.get("url", "")
                })

        except Exception as e:
            print(f"[Semantic Scholar Error] {e}")

        print(f"[Semantic Scholar] Fetched {len(papers)} papers")
        return papers
