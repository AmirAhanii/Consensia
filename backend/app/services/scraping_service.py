from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel


def _google_search(params: dict) -> Any:
    """Lazy import so the rest of the API can start without `google-search-results` installed."""
    try:
        from serpapi import GoogleSearch
    except ImportError as exc:
        raise ImportError(
            "SerpAPI client missing. Install: pip install google-search-results"
        ) from exc
    return GoogleSearch(params)


class _FilteredPaperReason(BaseModel):
    index: int
    title: str
    reason: str


class _PaperRelevanceFilter(BaseModel):
    relevant_indices: list[int]
    filtered_papers: list[_FilteredPaperReason]


_FILTER_SYSTEM = """
You are a domain relevance classifier for Software Engineering research.
Given a list of papers, identify which ones are relevant to Software Engineering
and which should be excluded because they belong to a completely different field.

A paper IS relevant if it involves: software development, testing, maintenance,
mining software repositories, code analysis, programming languages, software tools,
empirical studies of software systems, or related computing topics.

A paper is NOT relevant if it belongs to an entirely different scientific domain
(e.g., physics, chemistry, solar energy, biology, economics unrelated to SE).

Be strict: if in doubt, include the paper.
"""


def _filter_relevant_papers(
    papers: list[dict], client: Any, openai_model: str
) -> list[dict]:
    if not papers:
        return papers

    paper_titles = [
        {"index": i, "title": p.get("title", ""), "venue": p.get("venue", "")}
        for i, p in enumerate(papers)
    ]

    response = client.beta.chat.completions.parse(
        model=openai_model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": _FILTER_SYSTEM.strip()},
            {
                "role": "user",
                "content": f"Filter SE-relevant papers:\n{json.dumps(paper_titles, ensure_ascii=False)}",
            },
        ],
        response_format=_PaperRelevanceFilter,
    )

    result = response.choices[0].message.parsed
    relevant_indices = set(result.relevant_indices if result else range(len(papers)))
    return [p for i, p in enumerate(papers) if i in relevant_indices]


def _normalize_name(name: str) -> str:
    """Normalize names for safer matching."""
    name = unicodedata.normalize("NFKD", name or "")
    name = "".join(ch for ch in name if not unicodedata.combining(ch))
    name = re.sub(r"\([^)]*\)", " ", name)
    name = re.sub(r"[^a-zA-Z\s]", " ", name)
    return re.sub(r"\s+", " ", name).strip().lower()


def _name_score(expected: str, actual: str) -> float:
    """
    Score how likely actual name matches expected name.
    """
    expected_norm = _normalize_name(expected)
    actual_norm = _normalize_name(actual)

    if not expected_norm or not actual_norm:
        return 0.0

    if expected_norm == actual_norm:
        return 1.0

    expected_tokens = expected_norm.split()
    actual_tokens = actual_norm.split()

    expected_last = expected_tokens[-1]
    actual_last = actual_tokens[-1]

    if expected_last != actual_last:
        return 0.0

    expected_first = expected_tokens[0]
    actual_first = actual_tokens[0]

    first_matches = (
        expected_first == actual_first
        or expected_first.startswith(actual_first)
        or actual_first.startswith(expected_first)
    )

    if first_matches:
        return 0.90

    overlap = len(set(expected_tokens) & set(actual_tokens)) / len(set(expected_tokens))
    similarity = SequenceMatcher(None, expected_norm, actual_norm).ratio()

    return 0.70 * overlap + 0.30 * similarity


def _extract_author_id(link: str) -> str | None:
    """Extract Google Scholar author_id from profile URL."""
    if not link:
        return None

    query = parse_qs(urlparse(link).query)
    user_ids = query.get("user", [])

    return user_ids[0] if user_ids else None


def search_google_scholar_by_name(name: str, serpapi_key: str) -> str:
    """
    Search Google Scholar for a researcher name and return the correct author_id.

    Fix:
    - Do NOT return the first Scholar profile found in paper authors.
    - First collect possible candidates.
    - Then open each profile and verify profile['author']['name'].
    """
    params = {
        "engine": "google_scholar",
        "q": f'author:"{name}"',
        "api_key": serpapi_key,
        "num": "20",
    }

    results = _google_search(params).get_dict()

    if "error" in results:
        raise ValueError(f"SerpAPI error: {results['error']}")

    candidate_ids: set[str] = set()

    for result in results.get("organic_results", []):
        authors = result.get("publication_info", {}).get("authors", [])

        for author in authors:
            author_name = author.get("name", "")
            link = author.get("link", "")

            author_id = _extract_author_id(link)

            if not author_id:
                continue

            if _name_score(name, author_name) >= 0.65:
                candidate_ids.add(author_id)

    if not candidate_ids:
        raise ValueError(f"No Google Scholar profile candidates found for: {name!r}")

    best_author_id = None
    best_score = 0.0
    checked_profiles = []

    for author_id in candidate_ids:
        profile_params = {
            "engine": "google_scholar_author",
            "author_id": author_id,
            "api_key": serpapi_key,
            "no_cache": "true",
        }

        profile = _google_search(profile_params).get_dict()

        if "error" in profile:
            continue

        author = profile.get("author", {})
        profile_name = author.get("name", "")
        affiliation = author.get("affiliations", "")

        score = _name_score(name, profile_name)

        checked_profiles.append(
            {
                "author_id": author_id,
                "name": profile_name,
                "affiliation": affiliation,
                "score": score,
            }
        )

        if score > best_score:
            best_score = score
            best_author_id = author_id

    if not best_author_id or best_score < 0.80:
        debug = "\n".join(
            f"- {p['name']} | {p['affiliation']} | score={p['score']:.2f}"
            for p in sorted(checked_profiles, key=lambda x: x["score"], reverse=True)
        )

        raise ValueError(
            f"No verified Google Scholar profile found for: {name!r}.\n"
            f"Checked profiles:\n{debug}"
        )

    return best_author_id


def scrape_google_scholar_author(
    author_id: str, serpapi_key: str, client: Any, openai_model: str
) -> dict[str, Any]:
    """Scrape a Google Scholar author profile and papers, filter to SE-relevant ones."""
    profile_params = {
        "engine": "google_scholar_author",
        "author_id": author_id,
        "api_key": serpapi_key,
        "num": "100",
        "no_cache": "true",
    }

    profile_results = _google_search(profile_params).get_dict()

    if "error" in profile_results:
        raise ValueError(f"SerpAPI profile error: {profile_results['error']}")

    author = profile_results.get("author", {})
    articles = profile_results.get("articles", [])[:50]

    papers = []

    for art in articles:
        abstract = None
        citation_id = art.get("citation_id")

        if citation_id:
            cite_params = {
                "engine": "google_scholar_author",
                "view_op": "view_citation",
                "citation_id": citation_id,
                "api_key": serpapi_key,
                "no_cache": "true",
            }

            cite_results = _google_search(cite_params).get_dict()
            abstract = cite_results.get("citation", {}).get("description")

        papers.append(
            {
                "title": art.get("title", "Unknown Title"),
                "authors": art.get("authors"),
                "year": art.get("year"),
                "venue": art.get("publication"),
                "citation_count": art.get("cited_by", {}).get("value"),
                "paper_url": art.get("link"),
                "abstract": abstract,
            }
        )

    relevant_papers = _filter_relevant_papers(papers, client, openai_model)

    return {
        "name": author.get("name"),
        "scholar_id": author_id,
        "affiliation": author.get("affiliations"),
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "papers": relevant_papers,
        "raw_data": {"serpapi_profile_response": profile_results},
    }