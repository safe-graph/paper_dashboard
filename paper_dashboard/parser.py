import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


logger = logging.getLogger(__name__)


@dataclass
class PaperEntry:
    year: Optional[int]
    title: str
    venue: str
    paper_url: Optional[str]
    code_url: Optional[str]
    category: str
    subcategory: Optional[str] = None

    @property
    def has_code(self) -> bool:
        return bool(self.code_url)


@dataclass
class ResourceLink:
    title: str
    url: str
    category: str


@dataclass
class ParseResult:
    papers: List[PaperEntry]
    resources: List[ResourceLink]


def sync_repo(repo_url: str, dest: Path) -> None:
    """Clone or pull the source repo."""
    if dest.exists():
        logger.info("Updating existing repo at %s", dest)
        subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"], check=True)
    else:
        logger.info("Cloning %s into %s", repo_url, dest)
        subprocess.run(["git", "clone", repo_url, str(dest)], check=True)


def extract_link(cell: str) -> Optional[str]:
    """Extract first URL from a markdown link cell."""
    match = re.search(r"\((https?://[^)]+)\)", cell)
    if match:
        return match.group(1).strip()
    return None


def clean_title(raw: str) -> str:
    title = re.sub(r"\*\*(.*?)\*\*", r"\1", raw)
    title = title.replace("[", "").replace("]", "")
    return " ".join(title.split())


def _parse_table_lines(
    lines: List[str], category: str, subcategory: Optional[str]
) -> List[PaperEntry]:
    if len(lines) < 2:
        return []
    rows = lines[2:]  # skip header and separator
    entries: List[PaperEntry] = []
    for row in rows:
        if not row.strip().startswith("|"):
            continue
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) < 5:
            continue
        year_raw, title_raw, venue_raw, paper_cell, code_cell = cells[:5]
        try:
            year = int(year_raw)
        except ValueError:
            year = None
        title = clean_title(title_raw)
        venue = venue_raw.strip()
        paper_url = extract_link(paper_cell)
        code_url = extract_link(code_cell)
        entries.append(
            PaperEntry(
                year=year,
                title=title,
                venue=venue,
                paper_url=paper_url,
                code_url=code_url,
                category=category,
                subcategory=subcategory,
            )
        )
    return entries


RESOURCE_ONLY_SECTIONS = {"Toolbox", "Dataset", "Survey Paper", "Other Resource"}


def parse_readme(text: str) -> ParseResult:
    """Parse the README markdown tables into structured entries."""
    papers: List[PaperEntry] = []
    resources: List[ResourceLink] = []

    current_category: Optional[str] = None
    current_subcategory: Optional[str] = None
    table_buffer: List[str] = []
    lines = text.splitlines()

    def flush_table():
        nonlocal table_buffer, papers, current_category, current_subcategory
        if table_buffer and current_category:
            papers.extend(_parse_table_lines(table_buffer, current_category, current_subcategory))
        table_buffer = []

    for raw_line in lines + [""]:
        line = raw_line.strip()
        if line.startswith("## "):
            flush_table()
            current_category = line.lstrip("#").strip()
            current_category = re.sub(r"\s*\[\[Back.*", "", current_category).strip()
            current_subcategory = None
            continue

        if line.startswith("### "):
            flush_table()
            sub = line.lstrip("#").strip()
            sub = re.sub(r"\[\[Back.*", "", sub).strip()
            current_subcategory = sub
            continue

        if line.startswith("|"):
            table_buffer.append(line)
            continue

        # Standalone links for resource-only sections
        if current_category in RESOURCE_ONLY_SECTIONS:
            link_match = re.match(r"\[([^\]]+)\]\((https?://[^)]+)\)", line)
            if link_match:
                resources.append(
                    ResourceLink(
                        title=link_match.group(1).strip(),
                        url=link_match.group(2).strip(),
                        category=current_category,
                    )
                )
        if table_buffer:
            flush_table()

    return ParseResult(papers=papers, resources=resources)


def load_readme(repo_dir: Path) -> str:
    readme_path = repo_dir / "README.md"
    return readme_path.read_text(encoding="utf-8")
