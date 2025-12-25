import logging
import re
import time
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Optional, Tuple

from urllib.parse import unquote

import requests

from .parser import PaperEntry


logger = logging.getLogger(__name__)

OPENALEX_API_BASE = "https://api.openalex.org/works"
OPENALEX_FIELDS = "display_name,cited_by_count,publication_year,doi,id"
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s?#]+", re.IGNORECASE)
ARXIV_RE = re.compile(r"arxiv\.org/(abs|pdf)/([^?#]+)", re.IGNORECASE)


def normalize_title(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return " ".join(cleaned.split())


def title_similarity(a: str, b: str) -> float:
    a_norm = normalize_title(a)
    b_norm = normalize_title(b)
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    if a_norm in b_norm or b_norm in a_norm:
        return 0.95
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def extract_doi(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    match = DOI_RE.search(url)
    if match:
        return match.group(0).rstrip(").,;")
    return None


def extract_arxiv_id(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    match = ARXIV_RE.search(url)
    if not match:
        return None
    raw = unquote(match.group(2)).strip()
    raw = raw.replace(".pdf", "")
    raw = re.sub(r"v\d+$", "", raw)
    return raw or None


def _openalex_headers() -> Dict[str, str]:
    return {"User-Agent": "paper-dashboard/1.0"}


def _openalex_params(email: Optional[str]) -> Dict[str, str]:
    params = {"select": OPENALEX_FIELDS}
    if email:
        params["mailto"] = email
    return params


def _openalex_venue(data: Dict) -> Optional[str]:
    host = data.get("host_venue") or {}
    venue = host.get("display_name")
    if venue:
        return venue
    primary = data.get("primary_location") or {}
    source = primary.get("source") or {}
    return source.get("display_name")


def _openalex_landing_url(data: Dict) -> Optional[str]:
    primary = data.get("primary_location") or {}
    url = primary.get("landing_page_url")
    if url:
        return url
    return data.get("id")


def fetch_openalex_by_filter(
    filter_value: str, email: Optional[str], timeout: int = 30
) -> Optional[Dict]:
    params = _openalex_params(email)
    params["filter"] = filter_value
    params["per-page"] = 1
    try:
        resp = requests.get(
            OPENALEX_API_BASE,
            params=params,
            headers=_openalex_headers(),
            timeout=timeout,
        )
    except requests.RequestException as exc:
        logger.warning("OpenAlex filter request failed: %s", exc)
        return None
    if resp.status_code != 200:
        logger.warning(
            "OpenAlex filter request failed: %s %s",
            resp.status_code,
            resp.text[:200],
        )
        return None
    payload = resp.json()
    results = payload.get("results", []) if isinstance(payload, dict) else []
    if not results:
        return None
    return results[0]


def search_openalex_by_title(
    title: str, year: Optional[int], email: Optional[str], timeout: int = 30
) -> Optional[Dict]:
    params = _openalex_params(email)
    params["search"] = title
    params["per-page"] = 5
    try:
        resp = requests.get(
            OPENALEX_API_BASE,
            params=params,
            headers=_openalex_headers(),
            timeout=timeout,
        )
    except requests.RequestException as exc:
        logger.warning("OpenAlex search failed: %s", exc)
        return None
    if resp.status_code != 200:
        logger.warning(
            "OpenAlex search failed: %s %s",
            resp.status_code,
            resp.text[:200],
        )
        return None
    payload = resp.json()
    candidates = payload.get("results", []) if isinstance(payload, dict) else []
    best = None
    best_score = 0.0
    for cand in candidates:
        cand_title = cand.get("display_name") or ""
        score = title_similarity(title, cand_title)
        if year and cand.get("publication_year") == year:
            score += 0.05
        if score > best_score:
            best_score = score
            best = cand
    if best_score < 0.6:
        return None
    return best


def build_openalex_entry(paper: PaperEntry, data: Dict) -> Dict:
    return {
        "title": paper.title,
        "citation_count": int(data.get("cited_by_count") or 0),
        "year": paper.year or data.get("publication_year"),
        "venue": paper.venue or _openalex_venue(data),
        "paper_url": paper.paper_url or _openalex_landing_url(data),
        "openalex_url": data.get("id"),
    }


def dedupe_entries(entries: List[Dict], top_k: int) -> List[Dict]:
    deduped: List[Dict] = []
    seen = set()
    for entry in sorted(entries, key=lambda x: x["citation_count"], reverse=True):
        key = normalize_title(entry["title"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
        if len(deduped) >= top_k:
            break
    return deduped


def extract_openalex_filter(url: Optional[str]) -> Optional[str]:
    doi = extract_doi(url)
    if doi:
        return f"doi:{doi.lower()}"
    return None


def fetch_top_cited(
    papers: Iterable[PaperEntry],
    openalex_email: Optional[str] = None,
    top_k: int = 10,
    limit: Optional[int] = None,
    sleep_seconds: float = 0.0,
) -> Tuple[List[Dict], Optional[str], Optional[str]]:
    openalex_results: List[Dict] = []
    openalex_lookups: List[Tuple[str, PaperEntry]] = []
    openalex_titles: List[Tuple[str, PaperEntry]] = []
    for paper in papers:
        if limit is not None and (len(openalex_lookups) + len(openalex_titles)) >= limit:
            break
        filter_value = extract_openalex_filter(paper.paper_url)
        if filter_value:
            openalex_lookups.append((filter_value, paper))
        else:
            openalex_titles.append((paper.title, paper))

    if openalex_lookups:
        for filter_value, paper in openalex_lookups:
            data = fetch_openalex_by_filter(filter_value, email=openalex_email)
            if data and data.get("cited_by_count") is not None:
                openalex_results.append(build_openalex_entry(paper, data))
            if sleep_seconds:
                time.sleep(sleep_seconds)

    if openalex_titles:
        for title, paper in openalex_titles:
            data = search_openalex_by_title(title, paper.year, email=openalex_email)
            if data and data.get("cited_by_count") is not None:
                openalex_results.append(build_openalex_entry(paper, data))
            if sleep_seconds:
                time.sleep(sleep_seconds)

    if openalex_results:
        return dedupe_entries(openalex_results, top_k), None, "OpenAlex"

    return [], "No citation data returned from OpenAlex.", None
