import argparse
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

from paper_dashboard import analysis
from paper_dashboard.builder import render_dashboard
from paper_dashboard.code_repos import (
    RepoMetadata,
    aggregate_languages,
    fetch_all_metadata,
    unique_github_repos,
)
from paper_dashboard.parser import ParseResult, parse_readme, sync_repo, load_readme


def build_stats(parsed: ParseResult, token: str, skip_code_fetch: bool) -> Dict:
    papers = parsed.papers
    stats: Dict = {
        "year_counts": analysis.counts_by_year(papers),
        "venue_counts": analysis.counts_by_venue(papers),
        "topics": analysis.word_frequencies([p.title for p in papers]),
        "code_availability": analysis.code_availability(papers),
        "category_counts": analysis.counts_by_category(papers),
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
    stats["insights"] = analysis.derive_insights(stats)
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
        "--skip-sync",
        action="store_true",
        help="Skip git clone/pull (assumes paper repo directory already contains README).",
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
    stats = build_stats(parsed, token=token, skip_code_fetch=args.skip_code_fetch)

    context = {
        "papers": papers_serializable,
        "stats": stats,
        "resources": [asdict(r) for r in parsed.resources],
    }
    render_dashboard(template_path, output_dir, context)


if __name__ == "__main__":
    main()
