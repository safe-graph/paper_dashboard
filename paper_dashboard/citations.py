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
# Only request fields we actually consume. NOTE: `host_venue` was REMOVED from
# the OpenAlex API (superseded by `primary_location`); including it in `select`
# makes the whole request 400 and silently drops every result. Venue now comes
# from `primary_location.source.display_name`.
OPENALEX_FIELDS = ",".join(
    [
        "id",
        "display_name",
        "cited_by_count",
        "publication_year",
        "doi",
        "primary_location",
    ]
)
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s?#\"']+", re.IGNORECASE)
ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([^?#\s]+)", re.IGNORECASE)
# Bare arxiv ids that may appear in filenames/urls (e.g. arxiv_2401.10547).
# Lookbehind avoids grabbing the tail of a longer number; we don't use \b so
# underscore-prefixed filenames still match.
ARXIV_ID_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(v\d+)?")

# How close a title-search candidate must be before we trust it. DOI / arXiv-id
# matches are authoritative and skip these checks; only fuzzy title matches do.
TITLE_STRONG_THRESHOLD = 0.92  # accept on title alone
TITLE_WITH_YEAR_THRESHOLD = 0.82  # accept if the publication year also lines up
YEAR_TOLERANCE = 1  # arXiv preprint vs. published version can differ by a year


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
    # Substring containment is only meaningful for reasonably long titles;
    # short titles (e.g. "GNN") would otherwise match almost anything.
    if min(len(a_norm), len(b_norm)) >= 20 and (a_norm in b_norm or b_norm in a_norm):
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
    """Pull a bare arXiv id (e.g. 2001.06362) from a URL or filename."""
    if not url:
        return None
    match = ARXIV_RE.search(url)
    raw = None
    if match:
        raw = unquote(match.group(1)).strip()
    else:
        # Handle local filenames like 'arxiv_2401.10547.pdf' or query strings.
        id_match = ARXIV_ID_RE.search(url)
        if id_match:
            raw = id_match.group(1)
    if not raw:
        return None
    raw = raw.replace(".pdf", "")
    raw = re.sub(r"v\d+$", "", raw)  # strip version suffix
    return raw or None


def arxiv_doi(arxiv_id: str) -> str:
    """OpenAlex indexes arXiv works under the DataCite DOI 10.48550/arXiv.<id>."""
    return f"10.48550/arxiv.{arxiv_id.lower()}"


def _openalex_headers() -> Dict[str, str]:
    return {"User-Agent": "paper-dashboard/1.0 (citation enrichment)"}


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


def _openalex_year(data: Dict) -> Optional[int]:
    year = data.get("publication_year")
    try:
        return int(year) if year is not None else None
    except (TypeError, ValueError):
        return None


def _request_openalex(params: Dict[str, str], timeout: int) -> Optional[Dict]:
    try:
        resp = requests.get(
            OPENALEX_API_BASE,
            params=params,
            headers=_openalex_headers(),
            timeout=timeout,
        )
    except requests.RequestException as exc:
        logger.warning("OpenAlex request failed: %s", exc)
        return None
    if resp.status_code != 200:
        logger.warning(
            "OpenAlex request failed: %s %s", resp.status_code, resp.text[:200]
        )
        return None
    try:
        return resp.json()
    except ValueError:
        logger.warning("OpenAlex returned non-JSON response")
        return None


def fetch_openalex_by_filter(
    filter_value: str, email: Optional[str], timeout: int = 30
) -> Optional[Dict]:
    params = _openalex_params(email)
    params["filter"] = filter_value
    params["per-page"] = 1
    payload = _request_openalex(params, timeout)
    if not payload:
        return None
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
    payload = _request_openalex(params, timeout)
    if not payload:
        return None
    candidates = payload.get("results", []) if isinstance(payload, dict) else []
    best = None
    best_score = 0.0
    for cand in candidates:
        cand_title = cand.get("display_name") or ""
        score = title_similarity(title, cand_title)
        if score > best_score:
            best_score = score
            best = cand
    if best is None:
        return None

    # Verification: a fuzzy title match is only trustworthy when it is either a
    # near-exact title, or a solid match whose publication year also lines up.
    cand_year = _openalex_year(best)
    year_ok = (
        year is not None
        and cand_year is not None
        and abs(cand_year - year) <= YEAR_TOLERANCE
    )
    if best_score >= TITLE_STRONG_THRESHOLD:
        return best
    if best_score >= TITLE_WITH_YEAR_THRESHOLD and year_ok:
        return best
    logger.info(
        "Rejected weak OpenAlex title match (score=%.2f, year=%s vs %s) for %r",
        best_score,
        cand_year,
        year,
        title[:80],
    )
    return None


def build_openalex_entry(paper: PaperEntry, data: Dict, match: str) -> Dict:
    return {
        "title": paper.title,
        "citation_count": int(data.get("cited_by_count") or 0),
        "year": paper.year or _openalex_year(data),
        "venue": paper.venue or _openalex_venue(data),
        "paper_url": paper.paper_url or _openalex_landing_url(data),
        "openalex_url": data.get("id"),
        "match_method": match,
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


def _identifier_filters(paper: PaperEntry) -> List[Tuple[str, str]]:
    """Ordered authoritative lookups for a paper: (match_method, filter)."""
    filters: List[Tuple[str, str]] = []
    doi = extract_doi(paper.paper_url)
    arxiv_id = extract_arxiv_id(paper.paper_url)
    # A real publisher DOI is the strongest signal; prefer it over the arXiv DOI.
    if doi and "arxiv" not in doi.lower():
        filters.append(("doi", f"doi:{doi.lower()}"))
    if arxiv_id:
        filters.append(("arxiv", f"doi:{arxiv_doi(arxiv_id)}"))
    if doi and "arxiv" in doi.lower() and not arxiv_id:
        filters.append(("doi", f"doi:{doi.lower()}"))
    return filters


def fetch_citation_for_paper(
    paper: PaperEntry, email: Optional[str], timeout: int = 30
) -> Optional[Dict]:
    """Resolve a single paper to an OpenAlex record.

    Tries authoritative identifier lookups (publisher DOI, then arXiv DOI) and
    only falls back to a *verified* title search when no identifier resolves.
    """
    for method, filter_value in _identifier_filters(paper):
        data = fetch_openalex_by_filter(filter_value, email=email, timeout=timeout)
        if data and data.get("cited_by_count") is not None:
            return build_openalex_entry(paper, data, method)

    data = search_openalex_by_title(paper.title, paper.year, email=email, timeout=timeout)
    if data and data.get("cited_by_count") is not None:
        return build_openalex_entry(paper, data, "title")
    return None


def fetch_top_cited(
    papers: Iterable[PaperEntry],
    openalex_email: Optional[str] = None,
    top_k: int = 10,
    limit: Optional[int] = None,
    sleep_seconds: float = 0.0,
) -> Tuple[List[Dict], Optional[str], Optional[str]]:
    openalex_results: List[Dict] = []
    queried = 0
    for paper in papers:
        if limit is not None and queried >= limit:
            break
        queried += 1
        entry = fetch_citation_for_paper(paper, email=openalex_email)
        if entry is not None:
            openalex_results.append(entry)
        if sleep_seconds:
            time.sleep(sleep_seconds)

    if openalex_results:
        return dedupe_entries(openalex_results, top_k), None, "OpenAlex"

    return [], "No citation data returned from OpenAlex.", None
