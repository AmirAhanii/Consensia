from datetime import datetime
from serpapi import GoogleSearch
from pydantic import BaseModel, Field
from typing import List
from app.core.config import settings
from app.core.llm_client import LLMClient

# ==========================================
# RELEVANCE FILTER SCHEMAS
# ==========================================

class FilteredPaperReason(BaseModel):
    index: int = Field(description="0-based index of the paper in the original list.")
    title: str = Field(description="Title of the excluded paper.")
    reason: str = Field(description="One sentence explaining why this paper is outside Software Engineering.")

class PaperRelevanceFilter(BaseModel):
    relevant_indices: List[int] = Field(
        description="0-based indices of papers relevant to Software Engineering."
    )
    filtered_papers: List[FilteredPaperReason] = Field(
        description="Papers excluded from the pipeline, each with an individual reason."
    )

FILTER_SYSTEM = """
You are a domain relevance classifier for Software Engineering research.
Given a list of papers, identify which ones are relevant to Software Engineering
and which should be excluded because they belong to a completely different field.

A paper IS relevant if it involves: software development, testing, maintenance,
mining software repositories, code analysis, programming languages, software tools,
empirical studies of software systems, or related computing topics.

A paper is NOT relevant if it belongs to an entirely different scientific domain
(e.g., physics, chemistry, solar energy, biology, economics unrelated to SE).

For each excluded paper, provide a specific one-sentence reason explaining
which domain it belongs to and why it is outside Software Engineering.

Be strict: if in doubt, include the paper.
"""

def _filter_relevant_papers(papers: list) -> tuple[list, list]:
    """
    Separate scraped papers into relevant (SE) and filtered (out-of-domain).
    Returns (relevant_papers, filtered_papers_with_reasons).
    """
    if not papers:
        return papers, []

    llm = LLMClient()

    paper_titles = [
        {"index": i, "title": p.get("title", ""), "venue": p.get("venue", "")}
        for i, p in enumerate(papers)
    ]

    filter_prompt = (
        f"Here are papers from a researcher's Google Scholar profile. "
        f"Identify which are relevant to Software Engineering research:\n"
        f"{__import__('json').dumps(paper_titles, ensure_ascii=False)}"
    )

    result = llm.generate_structured(FILTER_SYSTEM, filter_prompt, PaperRelevanceFilter)

    # Log each excluded paper with its individual reason
    for fp in result.get("filtered_papers", []):
        print(
            f"[Filter] Excluded paper #{fp['index']}: "
            f"'{fp['title']}' — {fp['reason']}"
        )

    relevant_indices = set(result.get("relevant_indices", range(len(papers))))
    relevant_papers = [p for i, p in enumerate(papers) if i in relevant_indices]

    filtered_papers = [
        {"title": fp["title"], "reason": fp["reason"]}
        for fp in result.get("filtered_papers", [])
    ]

    return relevant_papers, filtered_papers


def scrape_google_scholar_author(author_id: str) -> dict:
    print(f"\n--- Starting scrape for Author ID: {author_id} ---")

    # 1. First API call: Get the author's main profile and up to 100 papers
    profile_params = {
        "engine": "google_scholar_author",
        "author_id": author_id,
        "api_key": settings.serpapi_api_key,
        "num": "100",        # <--- GRABS UP TO 100 PAPERS ON PAGE 1
        "no_cache": "true" 
    }

    profile_search = GoogleSearch(profile_params)
    profile_results = profile_search.get_dict()

    # THE BUG CATCHER
    if "error" in profile_results:
        print(f"\n[!!!] SERPAPI RETURNED AN ERROR FOR {author_id}:")
        print(f"Error Message: {profile_results['error']}")
        return {
            "name": None,
            "scholar_id": author_id,
            "papers": [],
            "raw_data": {"serpapi_profile_response": profile_results}
        }

    author = profile_results.get("author", {})
    all_articles = profile_results.get("articles", [])
    
    # HARD CAP AT 50 PAPERS TO PROTECT API CREDITS
    articles = all_articles[:50]

    papers = []

    print(f"Found {len(all_articles)} total papers. Capping at {len(articles)} for abstract fetching...")

    # 2. Loop through our capped list to get the abstracts
    for index, art in enumerate(articles, start=1):
        title = art.get("title", "Unknown Title")
        citation_id = art.get("citation_id")

        print(f"[{index}/{len(articles)}] Fetching: {title}")

        abstract = None

        if citation_id:
            citation_params = {
                "engine": "google_scholar_author",
                "view_op": "view_citation",
                "citation_id": citation_id,
                "api_key": settings.serpapi_api_key,
                "no_cache": "true" 
            }
            citation_search = GoogleSearch(citation_params)
            citation_results = citation_search.get_dict()

            citation_data = citation_results.get("citation", {})
            abstract = citation_data.get("description")

        papers.append({
            "title": title,
            "authors": art.get("authors"),
            "year": art.get("year"),
            "venue": art.get("publication"),
            "citation_count": art.get("cited_by", {}).get("value"),
            "paper_url": art.get("link"),
            "abstract": abstract
        })

    # 3. Filter out papers outside Software Engineering
    print(f"\nRunning domain relevance filter on {len(papers)} papers...")
    relevant_papers, filtered_papers = _filter_relevant_papers(papers)
    print(f"Kept {len(relevant_papers)} relevant papers, excluded {len(filtered_papers)}.")

    # 4. Finish and return the compiled data
    print(f"--- Finished scraping {author.get('name')} ---\n")

    return {
        "name": author.get("name"),
        "scholar_id": author_id,
        "affiliation": author.get("affiliations"),
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "papers": relevant_papers,
        "filtered_papers": filtered_papers,
        "raw_data": {
            "serpapi_profile_response": profile_results
        }
    }