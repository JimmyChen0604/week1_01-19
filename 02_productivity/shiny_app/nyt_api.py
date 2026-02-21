# nyt_api.py
# NYT Most Popular API Helper Module
# Adapted from query_nyapi.py
# Jimmy

# This module handles all interaction with the New York Times
# Most Popular API. It loads the API key from .env, makes requests,
# parses responses, and returns structured article data.

# 0. Setup #################################

## 0.1 Load Packages ############################

import requests  # for HTTP requests to NYT API
import os        # for environment variable access
import json      # for JSON parsing
from datetime import datetime  # for date handling
from typing import List, Dict, Optional  # for type hints

# 1. Constants #################################

# NYT Most Popular API base URL
BASE_URL = "https://api.nytimes.com/svc/mostpopular/v2"

# Valid endpoint types and period options
VALID_ENDPOINTS = {"viewed": "Most Viewed", "emailed": "Most Emailed", "shared": "Most Shared"}
VALID_PERIODS = [1, 7, 30]

# 2. Custom Exception #################################

class NYTApiError(Exception):
    """Custom exception for NYT API errors.
    Provides friendly error messages for common issues
    like invalid keys, network failures, and rate limits."""
    pass

# 3. Environment Setup #################################

def _root_env_path():
    """Path to .env at project root (3 levels up from this file: shiny_app -> 02_productivity -> root)."""
    this_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(os.path.dirname(this_dir)))  # shiny_app -> 02_productivity -> root
    return os.path.join(root, ".env")


def load_env_file(filepath=None):
    """Load variables from .env file into environment.
    Reads each line, skips comments and blanks,
    and sets key=value pairs as environment variables.
    If filepath is None, uses .env at project root."""
    if filepath is None:
        filepath = _root_env_path()
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
        return True
    return False


def get_api_key(env_path=None):
    """Load .env and return the TEST_API_KEY value.
    If env_path is None, looks for .env at project root (same folder as query_nyapi.py, etc.).
    Returns None if the key is not found (instead of raising),
    so the caller can show a friendly message."""
    if env_path is None:
        env_path = _root_env_path()
    load_env_file(env_path)
    return os.getenv("TEST_API_KEY")

# 4. Name Normalization #################################

def normalize_nyt_person(name: str) -> str:
    """Convert NYT person facet from 'Last, First Middle' to 'First Middle Last'.
    Keeps suffixes reasonably well (e.g., 'King Jr., Martin Luther' -> 'Martin Luther King Jr.')."""
    if not name or not isinstance(name, str):
        return name

    name = name.strip()  # remove redundant spaces

    # If there's no comma, assume it's already in display order
    if "," not in name:
        return " ".join(name.split())

    # Split only on the first comma
    last, rest = name.split(",", 1)
    last = last.strip()
    rest = rest.strip()

    # Combine as 'First Last' (handles suffixes like Jr. naturally)
    display = f"{rest} {last}".strip()

    # Normalize whitespace
    return " ".join(display.split())

# 5. Article Parsing #################################

def parse_article(article: dict) -> dict:
    """Parse a single article from the NYT API response.
    Extracts title, date, section, url, abstract, and all facets.
    Returns a flat dictionary suitable for both table and JSON display."""
    # Normalize person names: 'Last, First' -> 'First Last'
    per_raw = article.get("per_facet", []) or []
    per = [normalize_nyt_person(name) for name in per_raw]

    des = article.get("des_facet", []) or []
    org = article.get("org_facet", []) or []
    geo = article.get("geo_facet", []) or []

    # Convert lists to comma-separated strings for table display
    des_str = ", ".join(des) if des else ""
    org_str = ", ".join(org) if org else ""
    per_str = ", ".join(per) if per else ""
    geo_str = ", ".join(geo) if geo else ""

    return {
        "title": article.get("title", "N/A"),
        "published_date": article.get("published_date", "N/A"),
        "section": article.get("section", "N/A"),
        "url": article.get("url", "N/A"),
        "abstract": article.get("abstract", "N/A"),
        "des_facet": des_str,
        "org_facet": org_str,
        "per_facet": per_str,
        "geo_facet": geo_str,
        # Keep original lists for JSON view
        "des_facet_list": des,
        "org_facet_list": org,
        "per_facet_list": per,
        "geo_facet_list": geo,
    }

# 6. Main API Fetch #################################

def fetch_articles(endpoint: str = "viewed", period: int = 1,
                   num_articles: int = 20, api_key: Optional[str] = None) -> List[Dict]:
    """Fetch most popular articles from the NYT API.
    
    Parameters:
        endpoint: One of 'viewed', 'emailed', 'shared'
        period: Time period in days (1, 7, or 30)
        num_articles: Number of articles to return (1-20)
        api_key: NYT API key (if None, loads from .env)
    
    Returns:
        List of parsed article dictionaries
    
    Raises:
        NYTApiError: On any API or network error with a friendly message
    """
    # Validate inputs
    if endpoint not in VALID_ENDPOINTS:
        raise NYTApiError(f"Invalid endpoint '{endpoint}'. Choose from: {list(VALID_ENDPOINTS.keys())}")
    if period not in VALID_PERIODS:
        raise NYTApiError(f"Invalid period '{period}'. Choose from: {VALID_PERIODS}")

    # Get API key if not provided
    if not api_key:
        api_key = get_api_key()
    if not api_key:
        raise NYTApiError("API key not found. Please add TEST_API_KEY to your .env file.")

    # Build request URL and parameters
    url = f"{BASE_URL}/{endpoint}/{period}.json"
    params = {"api-key": api_key}

    # Make the request with error handling
    try:
        response = requests.get(url, params=params, timeout=15)
    except requests.ConnectionError:
        raise NYTApiError("Network error: Could not connect to the NYT API. Check your internet connection.")
    except requests.Timeout:
        raise NYTApiError("Request timed out. The NYT API is not responding. Please try again.")
    except requests.RequestException as e:
        raise NYTApiError(f"Request failed: {str(e)}")

    # Handle HTTP error codes with friendly messages
    if response.status_code == 401:
        raise NYTApiError("Invalid API key. Please check your TEST_API_KEY in the .env file.")
    elif response.status_code == 403:
        raise NYTApiError("Access forbidden. Your API key may not have access to this endpoint.")
    elif response.status_code == 429:
        raise NYTApiError("Rate limit exceeded. Please wait a moment and try again.")
    elif response.status_code != 200:
        raise NYTApiError(f"API returned an error (HTTP {response.status_code}). Please try again later.")

    # Parse JSON response
    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError):
        raise NYTApiError("Could not parse the API response. The data format may have changed.")

    # Extract results
    if "results" not in data:
        raise NYTApiError("Unexpected API response format: no 'results' field found.")

    results = data["results"]
    if not results:
        raise NYTApiError("The API returned no articles for the selected parameters.")

    # Parse each article and limit to requested number
    articles = [parse_article(article) for article in results[:num_articles]]
    return articles

