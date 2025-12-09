import logging
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


@dataclass
class RepoMetadata:
    full_name: str
    url: str
    stars: int
    language: Optional[str]
    topics: List[str]
    languages: Dict[str, int]


def extract_repo_full_name(url: str) -> Optional[str]:
    """Return owner/repo for GitHub URLs."""
    if not url or "github.com" not in url:
        return None
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"{owner}/{repo}"


def unique_github_repos(urls: Iterable[str]) -> List[str]:
    names = []
    seen = set()
    for url in urls:
        name = extract_repo_full_name(url)
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _github_get(path: str, token: Optional[str]) -> Optional[dict]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "paper-dashboard"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(f"{GITHUB_API}/{path}", headers=headers, timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def fetch_repo_metadata(repo_full_name: str, token: Optional[str]) -> Optional[RepoMetadata]:
    try:
        meta = _github_get(f"repos/{repo_full_name}", token)
        if not meta:
            return None
        languages = _github_get(f"repos/{repo_full_name}/languages", token) or {}
    except requests.RequestException as exc:
        logger.warning("Skipping repo %s: %s", repo_full_name, exc)
        return None
    return RepoMetadata(
        full_name=repo_full_name,
        url=meta.get("html_url"),
        stars=meta.get("stargazers_count", 0),
        language=meta.get("language"),
        topics=meta.get("topics", []),
        languages={k: int(v) for k, v in languages.items()},
    )


def fetch_all_metadata(repos: Iterable[str], token: Optional[str]) -> List[RepoMetadata]:
    metadata: List[RepoMetadata] = []
    for name in repos:
        repo_meta = fetch_repo_metadata(name, token)
        if repo_meta:
            metadata.append(repo_meta)
    return metadata


def aggregate_languages(repos: Iterable[RepoMetadata]) -> List[Dict[str, int]]:
    totals: Dict[str, int] = {}
    for repo in repos:
        if repo.languages:
            for lang, size in repo.languages.items():
                totals[lang] = totals.get(lang, 0) + size
        elif repo.language:
            totals[repo.language] = totals.get(repo.language, 0) + 1
    return [
        {"language": lang, "bytes": totals[lang]} for lang in sorted(totals, key=totals.get, reverse=True)
    ]
