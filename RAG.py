from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
import pandas as pd
import numpy as np
from uuid import uuid4
import requests
from datetime import datetime
import os

# Load environment variables from .env file
def load_env_file(filepath=".env"):
    """Load variables from .env file into environment"""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip() #is a string method that removes leading and Trailing spaces and Newline characters \n
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1) #split the string only at the first = sign
                    os.environ[key.strip()] = value.strip()
#load .env file
load_env_file()

#Get API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
NYT_API_KEY = os.getenv("TEST_API_KEY")

#Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)
# Check if API key is set
if not NYT_API_KEY:
    raise ValueError("TEST_API_KEY not found in .env file. Please set it up first.")

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

def query_nyt_api(num_articles: int = 20):
    base_url = "https://api.nytimes.com/svc/mostpopular/v2"
    url = f"{base_url}/viewed/1.json"
    params = {"api-key": NYT_API_KEY}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        data = data["results"][:num_articles]

        # Prepare list for saving
        articles_data = []
        for i, article in enumerate(data):
            date = article["published_date"]
            title = article["title"]
            section = article["section"]
            url = article["url"]
            abstract = article["abstract"]
            per = article["per_facet"]
            per = [normalize_nyt_person(name) for name in per]

            # Convert lists to comma-seperated strings for CSV
            per_str = ", ".join(per) if per else ""

            # Store in dictionary for dataset
            article_dict = {
                "title": title,
                "published_date": date,
                "section": section,
                "url": url,
                "abstract": abstract,
                "per_facet": per_str,
            }
            articles_data.append(article_dict)

        # Save as CSV
        df = pd.DataFrame(articles_data)
        csv_filename = f"nyt_articles.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8')
        print(f"\n✅ Saved {len(articles_data)} articles to {csv_filename}")
    
    else:
        print(f"Error: {response.status_code}")

# This only needs to be run once to ingest documents into Pinecone
def ingest_documents(csv_filename, index_name=None):
    # Read the CSV file to ingest into Pinecone
    df = pd.read_csv(csv_filename)
    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    existing = [idx.name for idx in pc.list_indexes()]
    # Create index if it doesn't exist, or skip if it already exists
    if index_name not in existing:
        pc.create_index(
            name=index_name,
            dimension=1536,
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1",
            ),
        )
    index = pc.Index(index_name)
    #Ingesting documents into Pinecone
    batch_limit = 100
    num_batches = max(1, (len(df) + batch_limit - 1) // batch_limit)
    for batch in np.array_split(df, num_batches):
        def _str(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return ""
            return str(v)

        matadatas = [
            {
                "title": _str(row["title"]),
                "published_date": _str(row["published_date"]),
                "section": _str(row["section"]),
                "url": _str(row["url"]),
                "abstract": _str(row["abstract"]),
                "per_facet": _str(row["per_facet"]),
            }
            for _, row in batch.iterrows()
        ]
        texts = batch["abstract"].tolist()
        ids = [str(uuid4()) for _ in range(len(batch))]

        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small",
        )
        embeds = [np.array(r.embedding) for r in response.data]

        #Insert documents into Pinecone
        index.upsert(
            vectors=zip(ids, embeds, matadatas),
            namespace="nyt-articles",
        )

    return index

def retrieve(query: str, top_k: int = 5, namespace: str = "nyt-articles", index = None):
    if index is None:
        raise ValueError("Index is not initialized. Please ingest documents first and pass the index as an argument.")
    query_vector = client.embeddings.create(
        input=query,
        model="text-embedding-3-small",
    )
    query_vector = query_vector.data[0].embedding
    retrieved_docs = []
    sources = []

    docs = index.query(
        vector=query_vector,
        top_k=top_k,
        namespace=namespace,
        include_metadata=True,
    )

    for doc in docs['matches']:
        retrieved_docs.append(doc['metadata']['abstract'])
        sources.append((doc['metadata']['title'], doc['metadata']['url'])) #title, url

    return retrieved_docs, sources

def prompt_with_context(query: str, retrieved_docs: list[str]):
    delimeter = f"\n{'-'*100}\n"
    prompt_start = 'Answer the question based on the context below. \n\nContext:\n'
    prompt_end = f'\n\nQuestion: {query}\nAnswer:'
    prompt = prompt_start + delimeter.join(retrieved_docs) + prompt_end
    return prompt	

def question_answering(prompt, sources, chat_model):

    sys_prompt = "You are a helpful assistant that always answers questions."

    res = client.responses.create(
        model=chat_model,
        input=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ],
    )

    answer = res.output_text.strip()

    answer += "\n\nSources:"

    for source in sources:
        answer += "\n" + source[0] + ": " + source[1]
        #sources[0] = title, sources[1]=URL

    return answer

def main():
    query_nyt_api(num_articles = 20)
    # Ingest documents (.csv) into Pinecone. Run only once to avoid duplicates
    index = ingest_documents("nyt_articles.csv", index_name="articles")
    # Retrieve documents
    query = "Has President Trump decided how to proceed"
    retrieved_docs, sources = retrieve(query, top_k=5, index=index)
    prompt = prompt_with_context(query, retrieved_docs)
    answer = question_answering(prompt, sources, chat_model="gpt-5")
    print(answer)

if __name__ == "__main__":
    main()