# Paper Dashboard

Static dashboard that summarizes graph/transformer fraud & anomaly detection papers from [`safe-graph/graph-fraud-detection-papers`](https://github.com/safe-graph/graph-fraud-detection-papers). The build script pulls the upstream list, extracts the tables, computes trends, and renders an interactive page for GitHub Pages.

## Features
- Pulls the latest paper list and parses every table row into structured data (year, venue, links, category/section).
- Computes year, venue, topic, and category distributions plus code availability and GitHub language stats (when code links point to GitHub).
- Generates a static `site/index.html` with Plotly charts, a searchable/sortable table (Grid.js), and resource links (toolboxes, datasets, surveys).
- GitHub Actions workflow auto-builds on push, schedule, or repository dispatch and deploys to GitHub Pages.

## Quick start (local)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# build dashboard into site/
python scripts/build_dashboard.py --paper-repo-dir tmp_papers_repo --output-dir site --skip-code-fetch
# open site/index.html in a browser
```
- Omit `--skip-code-fetch` to query GitHub for stars/languages (set `GITHUB_TOKEN` to avoid rate limits).
- Add `--skip-sync` to reuse a pre-cloned paper repo without pulling.
- The script clones the paper list into `data/papers_repo` by default; override with `--paper-repo-dir` if desired.

## Deploying to GitHub Pages
1. Enable Pages in repo settings with source: GitHub Actions.
2. Push to `main` (or run the workflow manually). The workflow builds `site/` and publishes it.

## Updating when the paper repo changes
- The workflow triggers on a nightly schedule and on `repository_dispatch` with type `paper-repo-updated`.
- To refresh immediately after the upstream repo changes, trigger a dispatch:
  ```bash
  curl -X POST \
    -H "Authorization: token <YOUR_PAT>" \
    -H "Accept: application/vnd.github.everest-preview+json" \
    https://api.github.com/repos/<YOUR_ACCOUNT>/<THIS_REPO>/dispatches \
    -d '{"event_type": "paper-repo-updated"}'
  ```
- You can also set up a webhook or action in `safe-graph/graph-fraud-detection-papers` that sends this dispatch.

## Project layout
- `scripts/build_dashboard.py` – orchestrates cloning, parsing, analysis, and rendering.
- `paper_dashboard/parser.py` – markdown table parser for the upstream README.
- `paper_dashboard/analysis.py` – stats, topic extraction, insights.
- `paper_dashboard/code_repos.py` – optional GitHub metadata and language aggregation.
- `templates/index.html.j2` – HTML/JS template for the dashboard.
- `site/` – generated static site (ignored from git).
