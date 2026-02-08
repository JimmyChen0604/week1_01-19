import requests
import os
import pandas as pd
import json
from datetime import datetime

'''
#最近政黨的趨勢或人物的趨勢
 1. Able to search the most popular articles with descriptors, people facets, organization facets....
 2. People click into the content, they are able to communicate with chatbot to read the content with personal assistant (e.g, summarize the content, ask questions).
 3. Visualize the data in a dashboard to the trend of the most popular articles with descriptors, people facets, organization facets....

Future Direction:
This project implements a Facet-Aware Retrieval-Augmented Generation (RAG) system to analyze political discourse using structured metadata from New York Times articles.
The core idea is to improve the reliability and interpretability of LLM outputs by combining semantic retrieval with editor-curated facets such as people, organizations, locations, topics, and time.

What the System Does : 

When a user asks a question about political narratives (e.g., party decline involving specific figures or countries), the system:

Retrieves relevant articles from a local corpus instead of relying on the LLM’s internal knowledge.

Uses structured facets (e.g., per_facet, org_facet, geo_facet, des_facet) to filter documents before semantic similarity ranking.

Generates grounded answers using only the retrieved article content.

Provides transparent evidence, listing the articles and facets used to support each response.

Why Facet-Aware Retrieval Matters

Traditional RAG systems rely solely on text similarity, which can return loosely related documents and reduce trust in results.
By incorporating structured facets during retrieval, this system achieves:

Higher precision (documents must match relevant people, organizations, or locations)

Reduced hallucination (LLM responses are constrained by retrieved evidence)

Improved explainability (users can see why each document was selected)

Technical Approach

Articles are stored with both text content (title + abstract) and structured metadata (facets and publication date).

Retrieval follows a two-stage pipeline:

Facet filtering to remove irrelevant articles.

Semantic ranking using text embeddings to select the most relevant documents.

The selected documents are passed to an LLM, which produces a synthesized answer and cites the source articles.
'''

#------------------------------------1. Prerequisites------------------------------------
# Load environment variables from .env file manually
def load_env_file(filepath=".env"):
    """Load variables from .env file into environment"""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

# Load .env file
load_env_file()

base_url = "https://api.nytimes.com/svc/mostpopular/v2"
API_KEY = os.getenv("TEST_API_KEY")

# Check if API key is set
if not API_KEY:
    raise ValueError("TEST_API_KEY not found in .env file. Please set it up first.")

url = f"{base_url}/viewed/1.json"
params = {"api-key": API_KEY}

response = requests.get(url, params=params)
#print(response.json()['results'][0])
#print(response.json())
# data = response.json()
# data_adx_keywords = data["results"][0]['adx_keywords']
# data_url = data["results"][0]['url']
# print(data_adx_keywords)
# print(data_url)

def normalize_nyt_person(name: str) -> str:
    """
    Convert NYT person facet from 'Last, First Middle' to 'First Middle Last'.
    Keeps suffixes reasonably well (e.g., 'King Jr., Martin Luther' -> 'Martin Luther King Jr.').
    """
    if not name or not isinstance(name, str):
        return name

    name = name.strip() #remove redundant spaces

    # If there's no comma, assume it's already in display order
    if "," not in name:
        return " ".join(name.split()) #split words and join them with a space

    # Split only on the first comma
    last, rest = name.split(",", 1)
    last = last.strip()
    rest = rest.strip()

    # Simple handling for suffixes that sometimes appear with last name (rare in NYT facets but possible)
    # e.g., "King Jr., Martin Luther" -> last = "King Jr."
    # This already works: "Martin Luther" + "King Jr."
    display = f"{rest} {last}".strip()

    # Normalize whitespace
    return " ".join(display.split()) 

#------------------------------------3. Query the NYT API------------------------------------
def query_nyt_api(num_articles: int = 20):
    if response.status_code == 200:
        data = response.json()
        first_data = data["results"][:num_articles]  # Get first num_articles articles
        
        # Prepare data for saving
        articles_data = []
        
        for i, article in enumerate(first_data):
            date = article["published_date"]
            title = article["title"]
            url = article["url"]
            section = article["section"]
            abstract = article["abstract"]
            
            des = article["des_facet"]
            org = article["org_facet"]
            # Normalize each person name in the list: 'Last, First' -> 'First Last'
            per_raw = article["per_facet"]
            per = [normalize_nyt_person(name) for name in per_raw] if per_raw else []
            geo = article["geo_facet"]
            
            # Convert lists to comma-separated strings for CSV
            des_str = ", ".join(des) if des else "" 
            org_str = ", ".join(org) if org else ""
            per_str = ", ".join(per) if per else ""
            geo_str = ", ".join(geo) if geo else ""

            print(des_str)
        

            # Store in dictionary for dataset
            article_dict = {
                "title": title,
                "published_date": date,
                "section": section,
                "url": url,
                "abstract": abstract,
                "des_facet": des_str,  # String version for CSV
                "org_facet": org_str,
                "per_facet": per_str,
                "geo_facet": geo_str,
                "des_facet_list": des,  # Keep original list for JSON
                "org_facet_list": org,
                "per_facet_list": per,
                "geo_facet_list": geo
            }
            articles_data.append(article_dict)

            # Print to console
            print(f"{i+1}. {title} ({date}) | {section}")
            print(f"   Descriptors: {des_str}")
            print(f"   People: {per_str}")
            print(f"   Organizations: {org_str}")
            print(f"   Locations: {geo_str}")
            print(f"   Abstract: {abstract[:100]}...")  # Truncate for display
            print(f"   URL: {url}")
            print("-" * 120)
        
        # Save to CSV
        df = pd.DataFrame(articles_data)
        # Remove list columns for CSV (keep only string versions)
        df_csv = df.drop(columns=['des_facet_list', 'org_facet_list', 'per_facet_list', 'geo_facet_list'])
        csv_filename = f"nyt_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_csv.to_csv(csv_filename, index=False, encoding='utf-8')
        print(f"\n✅ Saved {len(articles_data)} articles to {csv_filename}")
        
    else:
        print("Error:", response.status_code)

def main():
    query_nyt_api(num_articles = 2)

if __name__ == "__main__":
    main()