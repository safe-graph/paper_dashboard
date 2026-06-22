import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Ensure repository root is on sys.path when executed as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_dashboard import analysis
from paper_dashboard import citations
from paper_dashboard.builder import render_dashboard
from paper_dashboard.code_repos import (
    RepoMetadata,
    aggregate_languages,
    fetch_all_metadata,
    unique_github_repos,
)
from paper_dashboard.parser import (
    PaperEntry,
    ParseResult,
    load_readme,
    parse_readme,
    sync_repo,
)


def build_stats(
    parsed: ParseResult,
    token: str,
    skip_code_fetch: bool,
    skip_citations: bool,
    citations_limit: Optional[int],
    citations_top_k: int,
    openalex_email: Optional[str],
    openalex_api_key: Optional[str],
) -> Dict:
    papers = parsed.papers
    stats: Dict = {
        "year_counts": analysis.counts_by_year(papers),
        "venue_counts": analysis.counts_by_venue(papers),
        "topics": analysis.word_frequencies([p.title for p in papers]),
        "code_availability": analysis.code_availability(papers),
        "category_counts": analysis.counts_by_category(papers),
        "method_counts": analysis.method_families(papers),
        "domain_counts": analysis.domain_focus(papers),
        "venue_strata": analysis.venue_strata(papers),
        "dataset_counts": analysis.dataset_mentions(papers),
        "paper_count": len(papers),
    }

    code_repos: List[RepoMetadata] = []
    if not skip_code_fetch:
        repo_names = unique_github_repos([p.code_url for p in papers if p.code_url])
        if repo_names:
            code_repos = fetch_all_metadata(repo_names, token)
        stats["language_counts"] = aggregate_languages(code_repos)
    else:
        stats["language_counts"] = []

    stats["code_repos"] = [asdict(r) for r in code_repos]
    stats["top_repos"] = sorted(
        [
            {
                "full_name": r.full_name,
                "stars": r.stars,
                "url": r.url,
                "language": r.language,
            }
            for r in code_repos
        ],
        key=lambda x: x["stars"],
        reverse=True,
    )[:10]
    stats["insights"] = analysis.derive_insights(stats)
    if skip_citations:
        stats["top_cited"] = []
        stats["paper_citations"] = []
        stats["citation_note"] = "Citation fetch skipped (run without --skip-citations)."
    else:
        paper_citations, queried = citations.fetch_all_citations(
            papers,
            openalex_email=openalex_email,
            openalex_api_key=openalex_api_key,
            limit=citations_limit,
        )
        stats["paper_citations"] = paper_citations
        stats["top_cited"] = citations.dedupe_entries(
            paper_citations, citations_top_k
        )
        stats["citation_source"] = "OpenAlex"
        stats["citation_updated_at"] = datetime.now(timezone.utc).isoformat()
        stats["citation_coverage"] = {
            "matched": len(paper_citations),
            "queried": queried,
            "percentage": round((len(paper_citations) / queried) * 100, 1)
            if queried
            else 0,
        }
        if len(paper_citations) < queried:
            stats["citation_note"] = (
                f"OpenAlex matched {len(paper_citations)} of {queried} unique papers."
            )
    return stats


def build_resources(
    parsed: ParseResult,
    skip_citations: bool,
    openalex_email: Optional[str],
    openalex_api_key: Optional[str],
) -> List[Dict]:
    resources = [asdict(resource) for resource in parsed.resources]
    if skip_citations:
        return resources

    surveys = [
        PaperEntry(
            year=None,
            title=resource.title,
            venue="",
            paper_url=resource.url,
            code_url=None,
            category=resource.category,
        )
        for resource in parsed.resources
        if resource.category == "Survey Paper"
    ]
    survey_citations, _ = citations.fetch_all_citations(
        surveys,
        openalex_email=openalex_email,
        openalex_api_key=openalex_api_key,
    )
    citations_by_title = {entry["title"]: entry for entry in survey_citations}
    for resource in resources:
        citation = citations_by_title.get(resource["title"])
        if not citation:
            continue
        resource.update(
            {
                "citation_count": citation["citation_count"],
                "citation_source": citation["citation_source"],
                "citation_match_method": citation["match_method"],
                "openalex_url": citation["openalex_url"],
            }
        )
    return resources


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static dashboard for paper list.")
    parser.add_argument(
        "--paper-repo-url",
        default="https://github.com/safe-graph/graph-fraud-detection-papers",
        help="Source repo containing the curated paper list.",
    )
    parser.add_argument(
        "--paper-repo-dir",
        default="data/papers_repo",
        help="Where to clone/pull the paper list repository.",
    )
    parser.add_argument(
        "--output-dir",
        default="site",
        help="Directory where the static site will be written.",
    )
    parser.add_argument(
        "--template",
        default="templates/index.html.j2",
        help="Template used to render the dashboard.",
    )
    parser.add_argument(
        "--skip-code-fetch",
        action="store_true",
        help="Skip GitHub API calls for code repos (useful offline).",
    )
    parser.add_argument(
        "--skip-citations",
        action="store_true",
        help="Skip OpenAlex citation fetching.",
    )
    parser.add_argument(
        "--citations-limit",
        type=int,
        default=None,
        help="Limit the number of papers queried for citation counts.",
    )
    parser.add_argument(
        "--citations-top-k",
        type=int,
        default=10,
        help="Number of top cited papers to include in the dashboard.",
    )
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip git clone/pull (assumes paper repo directory already contains README).",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Only emit data.json (skip HTML rendering).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    openalex_email = os.environ.get("OPENALEX_EMAIL")
    openalex_api_key = os.environ.get("OPENALEX_API_KEY")
    if not args.skip_citations and not openalex_api_key:
        raise RuntimeError(
            "OPENALEX_API_KEY is required for complete citation enrichment. "
            "Create a free OpenAlex API key or use --skip-citations for an offline build."
        )

    paper_repo_dir = Path(args.paper_repo_dir)
    output_dir = Path(args.output_dir)
    template_path = Path(args.template)

    if not args.skip_sync:
        sync_repo(args.paper_repo_url, paper_repo_dir)
    readme_text = load_readme(paper_repo_dir)
    parsed = parse_readme(readme_text)
    papers_serializable = analysis.to_serializable(parsed.papers)
    stats = build_stats(
        parsed,
        token=token,
        skip_code_fetch=args.skip_code_fetch,
        skip_citations=args.skip_citations,
        citations_limit=args.citations_limit,
        citations_top_k=args.citations_top_k,
        openalex_email=openalex_email,
        openalex_api_key=openalex_api_key,
    )
    resources = build_resources(
        parsed,
        skip_citations=args.skip_citations,
        openalex_email=openalex_email,
        openalex_api_key=openalex_api_key,
    )

    context = {
        "papers": papers_serializable,
        "stats": stats,
        "resources": resources,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data.json").write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.json_only:
        render_dashboard(template_path, output_dir, context)


if __name__ == "__main__":
    main()
