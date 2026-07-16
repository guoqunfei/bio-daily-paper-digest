#!/usr/bin/env python3
"""
Paper Fetching Module - Retrieve papers from multiple academic sources
文献抓取模块 - 从多个学术数据源获取文献
"""

import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict


def fetch_arxiv(keywords: List[str], max_results: int = 10) -> List[Dict]:
    """Fetch papers from arXiv API"""
    query = " OR ".join([f"all:{kw}" for kw in keywords])
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"[arXiv] Error fetching: {e}")
        return []

    root = ET.fromstring(resp.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    papers = []

    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns)
        summary = entry.find("atom:summary", ns)
        published = entry.find("atom:published", ns)
        link = entry.find("atom:link[@title='pdf']", ns)
        if link is None:
            link = entry.find("atom:id", ns)

        authors = entry.findall("atom:author/atom:name", ns)
        author_names = ", ".join([a.text for a in authors[:3]])
        if len(authors) > 3:
            author_names += " et al."

        papers.append({
            "source": "arXiv",
            "title": title.text.strip().replace("\n", " ") if title else "N/A",
            "authors": author_names,
            "abstract": summary.text.strip().replace("\n", " ")[:500] if summary else "",
            "published": published.text[:10] if published else "",
            "url": link.get("href") if link is not None and hasattr(link, 'get') else link.text if link else "",
            "doi": ""
        })

    return papers


def fetch_pubmed(keywords: List[str], max_results: int = 10, api_key: str = None) -> List[Dict]:
    """Fetch papers from PubMed / NCBI E-utilities"""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    query = " OR ".join([f"{kw}[Title/Abstract]" for kw in keywords])

    # Search
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": "date",
        "retmode": "json"
    }
    if api_key:
        search_params["api_key"] = api_key

    try:
        resp = requests.get(f"{base_url}/esearch.fcgi", params=search_params, timeout=30)
        data = resp.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"[PubMed] Search error: {e}")
        return []

    if not id_list:
        return []

    # Fetch summaries
    summary_params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "json"
    }
    if api_key:
        summary_params["api_key"] = api_key

    try:
        resp = requests.get(f"{base_url}/esummary.fcgi", params=summary_params, timeout=30)
        data = resp.json()
    except Exception as e:
        print(f"[PubMed] Summary error: {e}")
        return []

    papers = []
    for pmid in id_list:
        doc = data.get("result", {}).get(pmid, {})
        papers.append({
            "source": "PubMed",
            "title": doc.get("title", "N/A"),
            "authors": ", ".join([a.get("name", "") for a in doc.get("authors", [])[:3]]
                      + (" et al." if len(doc.get("authors", [])) > 3 else ""),
            "abstract": doc.get("abstract", "")[:500],
            "published": str(doc.get("pubdate", ""))[:10],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "doi": doc.get("elocationid", "")
        })

    return papers


def fetch_all_sources() -> List[Dict]:
    """Fetch papers from all configured sources"""
    keywords = os.environ.get("SEARCH_KEYWORDS", "structural variation,genome assembly").split(",")
    max_results = int(os.environ.get("MAX_RESULTS", "10"))
    api_key = os.environ.get("NCBI_API_KEY")

    all_papers = []
    all_papers.extend(fetch_arxiv(keywords, max_results))
    all_papers.extend(fetch_pubmed(keywords, max_results, api_key))

    # Deduplicate by title
    seen = set()
    unique = []
    for p in all_papers:
        key = p["title"].lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(p)

    return unique
