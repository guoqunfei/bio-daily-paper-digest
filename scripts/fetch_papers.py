#!/usr/bin/env python3
"""
Fetch Papers Module - Multi-source paper retrieval
多源文献抓取：arXiv / PubMed / bioRxiv
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

        link_url = ""
        if link is not None:
            if hasattr(link, 'get'):
                link_url = link.get("href") or ""
            elif hasattr(link, 'text') and link.text:
                link_url = link.text

        papers.append({
            "source": "arXiv",
            "title": title.text.strip().replace("\n", " ") if title is not None else "N/A",
            "authors": author_names,
            "abstract": summary.text.strip().replace("\n", " ")[:500] if summary is not None else "",
            "published": published.text[:10] if published is not None else "",
            "url": link_url,
            "doi": ""
        })

    return papers


def fetch_pubmed(keywords: List[str], max_results: int = 10, api_key: str = None) -> List[Dict]:
    """Fetch papers from PubMed / NCBI E-utilities"""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    query = " OR ".join([f"{kw}[Title/Abstract]" for kw in keywords])

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
        author_list = doc.get("authors", [])
        author_names = ", ".join([a.get("name", "") for a in author_list[:3]])
        if len(author_list) > 3:
            author_names += " et al."

        papers.append({
            "source": "PubMed",
            "title": doc.get("title", "N/A"),
            "authors": author_names,
            "abstract": doc.get("abstract", "")[:500],
            "published": str(doc.get("pubdate", ""))[:10],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "doi": doc.get("elocationid", "")
        })

    return papers


def fetch_biorxiv(keywords: List[str], max_results: int = 10) -> List[Dict]:
    """Fetch papers from bioRxiv API"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    all_papers = []
    cursor = 0
    batch_size = 100

    try:
        while len(all_papers) < max_results * 3:
            url = f"https://api.biorxiv.org/details/biorxiv/{start_date}/{end_date}/{cursor}"
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            collection = data.get("collection", [])
            if not collection:
                break

            for item in collection:
                title = item.get("title", "")
                text_to_search = f"{title} {item.get('abstract', '')}".lower()
                if any(kw.lower() in text_to_search for kw in keywords):
                    authors_raw = item.get("authors", "")
                    author_list = [a.strip() for a in authors_raw.split(";") if a.strip()]
                    author_names = ", ".join(author_list[:3])
                    if len(author_list) > 3:
                        author_names += " et al."

                    doi_val = item.get("doi", "")
                    if doi_val and doi_val.startswith("doi:"):
                        url_val = doi_val.replace("doi:", "https://doi.org/")
                    elif doi_val:
                        url_val = f"https://doi.org/{doi_val}"
                    else:
                        url_val = ""

                    all_papers.append({
                        "source": "bioRxiv",
                        "title": title.strip(),
                        "authors": author_names,
                        "abstract": item.get("abstract", "")[:500],
                        "published": item.get("date", ""),
                        "url": url_val,
                        "doi": doi_val
                    })

            cursor += batch_size
            if len(collection) < batch_size:
                break

        return all_papers[:max_results]

    except Exception as e:
        print(f"[bioRxiv] Error fetching: {e}")
        return []


def fetch_all_sources(keywords: List[str], max_results: int = 10, api_key: str = None) -> List[Dict]:
    """Fetch papers from all configured sources"""
    all_papers = []
    all_papers.extend(fetch_arxiv(keywords, max_results))
    all_papers.extend(fetch_pubmed(keywords, max_results, api_key))
    all_papers.extend(fetch_biorxiv(keywords, max_results))
    print(f"[Fetcher] Raw papers: {len(all_papers)} (arXiv + PubMed + bioRxiv)")
    return all_papers
