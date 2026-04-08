from datetime import datetime
from serpapi import GoogleSearch
from app.core.config import settings

def scrape_google_scholar_author(author_id: str) -> dict:
    print(f"\n--- Starting scrape for Author ID: {author_id} ---")
    
    # 1. First API call: Get the author's main profile and list of papers
    profile_params = {
        "engine": "google_scholar_author",
        "author_id": author_id,
        "api_key": settings.serpapi_api_key,
    }

    profile_search = GoogleSearch(profile_params)
    profile_results = profile_search.get_dict()

    author = profile_results.get("author", {})
    articles = profile_results.get("articles", [])

    papers = []
    
    print(f"Found {len(articles)} papers on main profile. Fetching abstracts now...")
    
    # 2. Loop through every single paper to get the abstract
    for index, art in enumerate(articles, start=1):
        title = art.get("title", "Unknown Title")
        citation_id = art.get("citation_id")
        
        print(f"[{index}/{len(articles)}] Fetching: {title}")
        
        abstract = None
        
        # If the paper has a citation ID, we can look up its full details
        if citation_id:
            citation_params = {
                "engine": "google_scholar_author",
                "view_op": "view_citation",
                "citation_id": citation_id,
                "api_key": settings.serpapi_api_key,
            }
            citation_search = GoogleSearch(citation_params)
            citation_results = citation_search.get_dict()
            
            citation_data = citation_results.get("citation", {})
            
            # SerpApi stores the abstract under 'description' in this specific endpoint
            abstract = citation_data.get("description")

        # 3. Append the fully enriched paper to our list
        papers.append({
            "title": title,
            "authors": art.get("authors"),
            "year": art.get("year"),
            "venue": art.get("publication"),
            "citation_count": art.get("cited_by", {}).get("value"),
            "paper_url": art.get("link"),
            "abstract": abstract 
        })

    # 4. Finish and return the compiled data
    print(f"--- Finished scraping {author.get('name')} ---\n")

    return {
        "name": author.get("name"),
        "scholar_id": author_id,
        "affiliation": author.get("affiliations"),
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "papers": papers,
        "raw_data": {
            "serpapi_profile_response": profile_results
        }
    }