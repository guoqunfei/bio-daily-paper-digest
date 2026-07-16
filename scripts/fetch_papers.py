#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文献抓取模块：多源检索 + 严格过滤 + 用户兴趣画像加分
"""

import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import Config
from github_feedback import MultiUserFeedbackStore


def log(msg: str):
    print(f"[FETCH] {msg}")
    sys.stdout.flush()


class PaperFetcher:
    def __init__(self):
        self.cfg = Config()
        self.core = self.cfg.core_keywords
        self.high = self.cfg.high_value_keywords
        self.exclude = self.cfg.exclude_keywords
        self.mufb = MultiUserFeedbackStore()
        self.user_weights = {}
        self.email_to = [e.strip() for e in os.getenv("EMAIL_TO", "").strip().split(",") if e.strip()]
        for email in self.email_to:
            self.user_weights[email] = self.mufb.get_user_weights(email)
        if any(self.user_weights.values()):
            log(f"Loaded user interest weights for {len(self.user_weights)} users")

    def fetch_all(self, lookback_days: int = None) -> List[Dict]:
        if lookback_days is None:
            lookback_days = self.cfg.lookback_days
        log(f"Starting fetch with lookback={lookback_days} days")
        log(f"Core: {len(self.core)}, High: {len(self.high)}, Exclude: {len(self.exclude)}")
        all_papers = []
        src_cfg = self.cfg.get_source_config
        if src_cfg("pubmed").get("enabled", True):
            all_papers.extend(self._fetch_pubmed(lookback_days))
            time.sleep(0.5)
        if src_cfg("arxiv").get("enabled", True):
            all_papers.extend(self._fetch_arxiv(lookback_days))
            time.sleep(0.5)
        if src_cfg("semantic_scholar").get("enabled", True):
            all_papers.extend(self._fetch_semantic_scholar(lookback_days))
        log(f"Raw total before dedup: {len(all_papers)}")
        return all_papers

    def score_and_filter(self, papers: List[Dict]) -> List[Dict]:
        filtered = []
        for p in papers:
            score, reason, excluded = self._score_relevance(p)
            if excluded:
                log(f"EXCLUDED: {p.get('title', '')[:50]}... | Reason: {excluded}")
                continue
            if score >= 1:
                p["relevance_score"] = min(score, 10)  # 强制上限
                p["match_reason"] = reason
                p["ignored_by"] = []
                for email in self.email_to:
                    key = p.get("doi", "") or p.get("arxiv_id", "") or p.get("title", "")[:50]
                    if self.mufb.is_ignored_by_user(key, email):
                        p["ignored_by"].append(email)
                filtered.append(p)
        filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        log(f"After strict filtering: {len(filtered)} papers")
        return filtered

    def _score_relevance(self, paper: Dict):
        title = (paper.get("title", "") or "").lower()
        abstract = (paper.get("abstract", "") or "").lower()
        full_text = f"{title} {abstract}"
        for ex in self.exclude:
            if ex.lower() in full_text:
                return 0, "", f"Excluded keyword: {ex}"
        score = 0
        matched = []
        for kw in self.core:
            kw_lower = kw.lower()
            if kw_lower in full_text:
                score += 1
                matched.append(kw)
                if kw_lower in title:
                    score += 2
        for hv in self.high:
            if hv.lower() in title:
                score += 3
                matched.append(f"[HIGH]{hv}")
        # 用户兴趣加分
        user_bonus = 0
        user_matched = []
        for email, weights in self.user_weights.items():
            for kw, weight in weights.items():
                if kw.lower() in full_text:
                    user_bonus = max(user_bonus, weight)
                    user_matched.append(f"{kw}(+{weight:.1f})")
        if user_matched:
            score += user_bonus
            matched = list(set(matched + user_matched))
        reason = ", ".join(matched[:5]) if matched else "No core match"
        return score, reason, ""

    def _fetch_pubmed(self, lookback_days: int) -> List[Dict]:
        core_terms = ["structural variation", "genome assembly", "mitochondrial genome", "antifreeze protein", "Hi-C", "long-read sequencing", "Myrmecia", "pig genome", "arthropod genomics", "TAD", "chromosome conformation"]
        query_or = " OR ".join([f'"{t}"[Title/Abstract]' for t in core_terms])
        end_date = datetime.now().strftime("%Y/%m/%d")
        start_date = (datetime.now() - timedelta(days=lookback_days * 2)).strftime("%Y/%m/%d")
        date_range = f"{start_date}:{end_date}[PDAT]"
        full_query = f"({query_or}) AND ({date_range})"
        log(f"PubMed query length: {len(full_query)} chars")
        try:
            esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            r = requests.get(esearch_url, params={"db": "pubmed", "term": full_query, "retmax": 100, "retmode": "json"}, timeout=30)
            r.raise_for_status()
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                log("PubMed: 0 results")
                return []
            log(f"PubMed: {len(ids)} IDs found")
            efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            r2 = requests.get(efetch_url, params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}, timeout=60)
            r2.raise_for_status()
            root = ET.fromstring(r2.content)
            papers = []
            for article in root.findall(".//PubmedArticle"):
                try:
                    title_elem = article.find(".//ArticleTitle")
                    title = (title_elem.text or "") if title_elem is not None else ""
                    abstract_parts = article.findall(".//Abstract/AbstractText")
                    abstract = " ".join([a.text or "" for a in abstract_parts])
                    doi_elem = article.find(".//ArticleId[@IdType='doi']")
                    doi = doi_elem.text if doi_elem is not None else ""
                    pmid_elem = article.find(".//PMID")
                    pmid = pmid_elem.text if pmid_elem is not None else ""
                    journal_elem = article.find(".//Journal/Title")
                    journal = journal_elem.text if journal_elem is not None else ""
                    author_list = []
                    for author in article.findall(".//Author"):
                        last = author.find("LastName")
                        first = author.find("ForeName")
                        if last is not None:
                            author_list.append(f"{last.text} {first.text if first is not None else ''}".strip())
                    authors = ", ".join(author_list[:3])
                    year_elem = article.find(".//PubDate/Year")
                    year = year_elem.text if year_elem is not None else ""
                    papers.append({"title": title.strip(), "abstract": abstract.strip(), "doi": doi, "pmid": pmid, "journal": journal, "date": year, "authors": authors, "source": "PubMed", "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else (f"https://doi.org/{doi}" if doi else "")})
                except Exception as e:
                    log(f"PubMed parse error: {e}")
                    continue
            log(f"PubMed parsed: {len(papers)} papers")
            return papers
        except Exception as e:
            log(f"PubMed fetch error: {e}")
            return []

    def _fetch_arxiv(self, lookback_days: int) -> List[Dict]:
        categories = self.cfg.get_source_config("arxiv").get("categories", ["q-bio.GN", "q-bio.PE", "cs.LG"])
        query_terms = " OR ".join(["genome assembly", "structural variation", "SV calling", "Hi-C scaffolding", "antifreeze protein", "arthropod", "mitochondrial"])
        papers = []
        for cat in categories:
            url = "http://export.arxiv.org/api/query"
            params = {"search_query": f"cat:{cat} AND ({query_terms})", "start": 0, "max_results": 30, "sortBy": "submittedDate", "sortOrder": "descending"}
            try:
                r = requests.get(url, params=params, timeout=30)
                r.raise_for_status()
                root = ET.fromstring(r.content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                for entry in root.findall("atom:entry", ns):
                    title = entry.find("atom:title", ns)
                    title = title.text if title is not None else ""
                    summary = entry.find("atom:summary", ns)
                    abstract = summary.text if summary is not None else ""
                    id_url = entry.find("atom:id", ns)
                    id_url = id_url.text if id_url is not None else ""
                    published = entry.find("atom:published", ns)
                    pub_date = published.text[:10] if published is not None else ""
                    arxiv_id = id_url.split("/")[-1] if id_url else ""
                    authors = [a.text for a in entry.findall("atom:author/atom:name", ns) if a.text]
                    papers.append({"title": title.replace("\n", " ").strip(), "abstract": abstract.replace("\n", " ").strip(), "doi": "", "arxiv_id": arxiv_id, "journal": f"arXiv:{cat}", "date": pub_date, "authors": ", ".join(authors[:3]), "source": "arXiv", "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else id_url})
            except Exception as e:
                log(f"arXiv fetch error for {cat}: {e}")
                continue
        log(f"arXiv total: {len(papers)} papers")
        return papers

    def _fetch_semantic_scholar(self, lookback_days: int) -> List[Dict]:
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
        query = "structural variation genome assembly arthropod pig antifreeze protein Hi-C"
        headers = {"x-api-key": api_key} if api_key else {}
        start_date = (datetime.now() - timedelta(days=lookback_days * 3)).strftime("%Y-%m-%d")
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {"query": query, "fields": "title,abstract,authors,year,venue,externalIds,openAccessPdf,url", "limit": 30, "publicationDateOrYear": start_date}
        try:
            r = requests.get(url, params=params, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
            papers = []
            for p in data.get("data", []):
                authors_list = [a.get("name", "") for a in p.get("authors", [])[:3]]
                ext_ids = p.get("externalIds", {}) or {}
                doi = ext_ids.get("DOI", "")
                arxiv = ext_ids.get("ArXiv", "")
                oa = p.get("openAccessPdf", {}) or {}
                url_link = oa.get("url") or p.get("url") or (f"https://doi.org/{doi}" if doi else "") or (f"https://arxiv.org/abs/{arxiv}" if arxiv else "")
                papers.append({"title": p.get("title", ""), "abstract": p.get("abstract", "") or "", "doi": doi, "arxiv_id": arxiv, "journal": p.get("venue", "N/A") or "N/A", "date": str(p.get("year", "")), "authors": ", ".join(authors_list), "source": "Semantic Scholar", "url": url_link})
            log(f"Semantic Scholar: {len(papers)} papers")
            return papers
        except Exception as e:
            log(f"Semantic Scholar fetch error: {e}")
            return []


if __name__ == "__main__":
    import json as json_lib
    fetcher = PaperFetcher()
    papers = fetcher.fetch_all(lookback_days=2)
    filtered = fetcher.score_and_filter(papers)
    print(json_lib.dumps([{"title": p["title"], "score": p.get("relevance_score"), "reason": p.get("match_reason")} for p in filtered[:10]], ensure_ascii=False, indent=2))
