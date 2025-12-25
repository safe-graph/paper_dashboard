import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
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
from paper_dashboard.parser import ParseResult, parse_readme, sync_repo, load_readme


def build_stats(
    parsed: ParseResult,
    token: str,
    skip_code_fetch: bool,
    skip_citations: bool,
    citations_limit: Optional[int],
    citations_top_k: int,
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
        stats["citation_note"] = "Citation fetch skipped (run without --skip-citations)."
    else:
        openalex_email = os.environ.get("OPENALEX_EMAIL")
        top_cited, note, source = citations.fetch_top_cited(
            papers,
            openalex_email=openalex_email,
            top_k=citations_top_k,
            limit=citations_limit,
        )
        stats["top_cited"] = top_cited
        if source:
            stats["citation_source"] = source
        if note:
            stats["citation_note"] = note
    return stats


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
    )

    context = {
        "papers": papers_serializable,
        "stats": stats,
        "resources": [asdict(r) for r in parsed.resources],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data.json").write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.json_only:
        render_dashboard(template_path, output_dir, context)


if __name__ == "__main__":
    main()
