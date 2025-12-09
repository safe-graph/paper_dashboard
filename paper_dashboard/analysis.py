import logging
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict
from typing import Dict, Iterable, List, Optional

from .parser import PaperEntry


logger = logging.getLogger(__name__)

STOPWORDS = {
    "for",
    "and",
    "with",
    "graph",
    "graphs",
    "network",
    "networks",
    "detection",
    "fraud",
    "anomaly",
    "anomalies",
    "gnn",
    "gnns",
    "based",
    "learning",
    "via",
    "using",
    "model",
    "models",
    "analysis",
    "graph-based",
    "graphical",
    "data",
    "system",
    "systems",
    "neural",
    "deep",
    "towards",
    "benchmark",
    "benchmarking",
    "study",
    "dataset",
    "framework",
    "approach",
}


def word_frequencies(titles: Iterable[str], top_k: int = 20) -> List[Dict[str, int]]:
    counter: Counter[str] = Counter()
    for title in titles:
        tokens = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", title.lower())
        for token in tokens:
            if token in STOPWORDS:
                continue
            counter[token] += 1
    most_common = counter.most_common(top_k)
    return [{"topic": word, "count": count} for word, count in most_common]


def counts_by_year(papers: Iterable[PaperEntry]) -> List[Dict[str, int]]:
    counter: Counter[int] = Counter()
    for paper in papers:
        if paper.year:
            counter[paper.year] += 1
    return [
        {"year": year, "count": counter[year]}
        for year in sorted(counter.keys())
    ]


def counts_by_category(papers: Iterable[PaperEntry]) -> List[Dict[str, int]]:
    counter: Counter[str] = Counter()
    for paper in papers:
        counter[paper.category] += 1
    return [{"category": c, "count": counter[c]} for c in sorted(counter.keys())]


def counts_by_venue(papers: Iterable[PaperEntry], top_k: int = 15) -> List[Dict[str, int]]:
    counter: Counter[str] = Counter()
    for paper in papers:
        venue = paper.venue.strip()
        if venue:
            counter[venue] += 1
    most_common = counter.most_common(top_k)
    return [{"venue": venue, "count": count} for venue, count in most_common]


def code_availability(papers: Iterable[PaperEntry]) -> Dict[str, float]:
    total = 0
    with_code = 0
    for paper in papers:
        total += 1
        if paper.has_code:
            with_code += 1
    percentage = (with_code / total * 100) if total else 0
    return {"with_code": with_code, "total": total, "percentage": round(percentage, 2)}


def derive_insights(stats: Dict) -> List[str]:
    insights: List[str] = []
    year_counts = stats.get("year_counts", [])
    venue_counts = stats.get("venue_counts", [])
    topics = stats.get("topics", [])
    code_stats = stats.get("code_availability", {})
    category_counts = stats.get("category_counts", [])

    if year_counts:
        peak = max(year_counts, key=lambda x: x["count"])
        insights.append(
            f"{peak['year']} is the busiest year with {peak['count']} papers listed."
        )
        if len(year_counts) > 1:
            first, last = year_counts[0], year_counts[-1]
            change = last["count"] - first["count"]
            if change > 0:
                insights.append(
                    f"Paper volume grew by {change} from {first['year']} to {last['year']}."
                )
    if venue_counts:
        top = venue_counts[0]
        insights.append(f"{top['venue']} appears most often ({top['count']} times).")
    if topics:
        top_topics = ", ".join(t["topic"] for t in topics[:5])
        insights.append(f"Dominant themes across titles: {top_topics}.")
    if code_stats.get("total"):
        insights.append(
            f"Code is linked for {code_stats['with_code']} papers ({code_stats['percentage']}%)."
        )
    if category_counts:
        top_cat = max(category_counts, key=lambda x: x["count"])
        insights.append(
            f"{top_cat['category']} contains the most entries ({top_cat['count']})."
        )
    return insights


def to_serializable(papers: Iterable[PaperEntry]) -> List[Dict]:
    return [
        {
            "year": paper.year,
            "title": paper.title,
            "venue": paper.venue,
            "paper_url": paper.paper_url,
            "code_url": paper.code_url,
            "category": paper.category,
            "subcategory": paper.subcategory,
            "has_code": paper.has_code,
        }
        for paper in papers
    ]
