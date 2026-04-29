from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, Field
from serpapi import GoogleSearch


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


def search_google_scholar_by_name(name: str, serpapi_key: str) -> str:
    """Search Google Scholar for papers by researcher name, extract their author_id."""
    params = {
        "engine": "google_scholar",
        "q": f'author:"{name}"',
        "api_key": serpapi_key,
        "num": "10",
    }
    results = GoogleSearch(params).get_dict()
    if "error" in results:
        raise ValueError(f"SerpAPI error: {results['error']}")

    for result in results.get("organic_results", []):
        for author in result.get("publication_info", {}).get("authors", []):
            link = author.get("link", "")
            if "scholar.google.com/citations" in link:
                user_ids = parse_qs(urlparse(link).query).get("user", [])
                if user_ids:
                    return user_ids[0]

    raise ValueError(f"No Google Scholar profile found for: {name!r}")


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
    profile_results = GoogleSearch(profile_params).get_dict()

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
            cite_results = GoogleSearch(cite_params).get_dict()
            abstract = cite_results.get("citation", {}).get("description")

        papers.append({
            "title": art.get("title", "Unknown Title"),
            "authors": art.get("authors"),
            "year": art.get("year"),
            "venue": art.get("publication"),
            "citation_count": art.get("cited_by", {}).get("value"),
            "paper_url": art.get("link"),
            "abstract": abstract,
        })

    relevant_papers = _filter_relevant_papers(papers, client, openai_model)

    return {
        "name": author.get("name"),
        "scholar_id": author_id,
        "affiliation": author.get("affiliations"),
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "papers": relevant_papers,
        "raw_data": {"serpapi_profile_response": profile_results},
    }
