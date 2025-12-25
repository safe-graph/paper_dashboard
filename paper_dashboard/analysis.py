import logging
import re
from collections import Counter
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
    return {
        "with_code": with_code,
        "without_code": total - with_code,
        "total": total,
        "percentage": round(percentage, 2),
    }


METHOD_KEYWORDS = {
    "Transformer/LLM": [r"transformer", r"llm", r"gpt", r"prompt", r"in-context"],
    "Graph Transformer": [r"graph transformer", r"gt\b", r"graphformer", r"gformer"],
    "Contrastive": [r"contrast", r"consist", r"info(nce)?"],
    "Diffusion": [r"diffusion", r"denois"],
    "Few/Fine-tuning": [r"few-?shot", r"meta", r"prompt-?tuning", r"tuning"],
    "Fairness": [r"fair"],
    "Robustness/Attack": [r"attack", r"robust", r"adversar", r"defen"],
    "Heterophily": [r"heteroph", r"hetero"],
    "Hyperbolic/Geometry": [r"hyperbol", r"geometric", r"curv"],
}


def method_families(papers: Iterable[PaperEntry]) -> List[Dict[str, int]]:
    counter: Counter[str] = Counter()
    for paper in papers:
        lower = paper.title.lower()
        matched = False
        for family, patterns in METHOD_KEYWORDS.items():
            if any(re.search(pat, lower) for pat in patterns):
                counter[family] += 1
                matched = True
        if not matched:
            counter["Other"] += 1
    return [{"method": k, "count": counter[k]} for k in sorted(counter.keys(), key=lambda x: (-counter[x], x))]


DOMAIN_KEYWORDS = {
    "Finance/Credit": [r"credit", r"loan", r"financial", r"bank", r"risk", r"account", r"transaction"],
    "E-commerce/Ads": [r"e-?commerce", r"voucher", r"promotion", r"advertis", r"review", r"product", r"shop"],
    "Social Media/News": [r"fake news", r"rumor", r"social", r"news", r"engagement", r"bot", r"spam"],
    "Blockchain/Crypto": [r"blockchain", r"bitcoin", r"ethereum", r"crypto", r"phishing", r"token"],
    "Telecom": [r"telecom", r"telecommunications", r"call detail", r"cdr"],
    "Cybersecurity/Malware": [r"malware", r"intrusion", r"phishing", r"attack", r"security"],
}


def infer_domain(title: str) -> str:
    lower = title.lower()
    for domain, patterns in DOMAIN_KEYWORDS.items():
        if any(re.search(pat, lower) for pat in patterns):
            return domain
    return "General"


def domain_focus(papers: Iterable[PaperEntry]) -> List[Dict[str, int]]:
    counter: Counter[str] = Counter()
    for paper in papers:
        counter[infer_domain(paper.title)] += 1
    return [{"domain": k, "count": counter[k]} for k in sorted(counter.keys(), key=lambda x: (-counter[x], x))]


TOP_VENUES = {
    "KDD",
    "NeurIPS",
    "ICLR",
    "ICML",
    "WWW",
    "TheWebConf",
    "AAAI",
    "IJCAI",
    "WSDM",
    "SDM",
    "CIKM",
    "SIGIR",
    "ACL",
    "EMNLP",
    "ECML",
    "PAKDD",
    "TKDE",
    "TNNLS",
    "TIFS",
    "TBD",
    "TKDD",
    "ICDE",
    "ICDM",
}


def venue_strata(papers: Iterable[PaperEntry]) -> List[Dict[str, int]]:
    counter: Counter[str] = Counter()
    for paper in papers:
        venue = paper.venue.lower()
        if "arxiv" in venue:
            counter["arXiv"] += 1
        elif "workshop" in venue:
            counter["Workshop"] += 1
        elif any(v.lower() in venue for v in TOP_VENUES):
            counter["Top conf/journal"] += 1
        elif "journal" in venue or "transactions" in venue:
            counter["Journal"] += 1
        else:
            counter["Other"] += 1
    return [{"stratum": k, "count": counter[k]} for k in sorted(counter.keys(), key=lambda x: (-counter[x], x))]


DATASET_KEYWORDS = {
    "DGraph": [r"\bdgraph"],
    "Elliptic": [r"elliptic"],
    "Ethereum": [r"ethereum", r"eth\b"],
    "Bitcoin": [r"bitcoin"],
    "Twitter/UTwitter": [r"twitter"],
    "Amazon": [r"amazon"],
    "Yelp": [r"yelp"],
    "Mercari": [r"mercari"],
    "Venmo": [r"venmo"],
    "JPMC": [r"jpmc"],
    "Weibo": [r"weibo"],
    "Alibaba/Tianchi": [r"tianchi"],
    "AML (Anti-Money Laundering)": [r"\baml\b", r"money laundering"],
    "IEEE-CIS": [r"ieee-cis"],
}


def dataset_mentions(papers: Iterable[PaperEntry], top_k: int = 12) -> List[Dict[str, int]]:
    counter: Counter[str] = Counter()
    for paper in papers:
        lower = paper.title.lower()
        for dataset, patterns in DATASET_KEYWORDS.items():
            if any(re.search(pat, lower) for pat in patterns):
                counter[dataset] += 1
    most_common = counter.most_common(top_k)
    return [{"dataset": name, "count": count} for name, count in most_common]


def derive_insights(stats: Dict) -> List[str]:
    insights: List[str] = []
    year_counts = stats.get("year_counts", [])
    venue_counts = stats.get("venue_counts", [])
    topics = stats.get("topics", [])
    code_stats = stats.get("code_availability", {})
    category_counts = stats.get("category_counts", [])
    domain_counts = stats.get("domain_counts", [])
    method_counts = stats.get("method_counts", [])

    if year_counts:
        peak = max(year_counts, key=lambda x: x["count"])
        insights.append(
            f"{peak['year']} is the busiest year with {peak['count']} papers listed."
        )
        # if len(year_counts) > 1:
        #     first, last = year_counts[0], year_counts[-1]
        #     change = last["count"] - first["count"]
        #     if change > 0:
        #         insights.append(
        #             f"Paper volume grew by {change} from {first['year']} to {last['year']}."
        #         )
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
    # if category_counts:
    #     top_cat = max(category_counts, key=lambda x: x["count"])
    #     insights.append(
    #         f"{top_cat['category']} contains the most entries ({top_cat['count']})."
    #     )
    # if domain_counts:
    #     top_domain = max(domain_counts, key=lambda x: x["count"])
    #     insights.append(f"Most common domain focus: {top_domain['domain']}.")
    # if method_counts:
    #     top_method = max(method_counts, key=lambda x: x["count"])
    #     insights.append(f"Prevalent method family: {top_method['method']}.")
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
            "domain": infer_domain(paper.title),
        }
        for paper in papers
    ]
