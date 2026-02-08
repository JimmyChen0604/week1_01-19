# ---------------------Step 1: Embed the search query and other documents---------------------
import openai
import numpy as np
from scipy.spatial import distance
#----------------------Step 1.1: Combined texts loaded from JSON Files---------------------
json_files = []

def combined_json(json_files):
    return f"""Title1: {json_files['title1']}
    Title2: {json_files["title2"]}
    Title3: {json_files["title3"]}"""

documents = [combined_json(json_file) for json_file in json_files]
#----------------------Step 1.2: Embed the documents using the OpenAI API---------------------
def embed_documents(documents):
    return openai.embeddings.create(
        input=documents,
        model="text-embedding-3-small"
    )

    response_dict = response.model_dump()
    return [data["embedding"] for data in response_dict["data"]]

embeddings = embed_documents(documents)
#----------------------Step 2: Calculate similarity scores between the query and documents using cosine similarity----------------------
# Find the n closest documents to the query vector, in this case is 3
def find_n_closest(query_vector, embeddings, n=3):
    distances = []
    for i, embedding in enumerate(embeddings):
        dist = distance.cosine(query_vector, embedding)
        distances.append({"index": i, "distance": dist})
    distances_sorted = sorted(distances, key=lambda x: x["distance"])
    return distances_sorted[:n]
#----------------------Step 3: Returning the search results----------------------
query = "I feel very depressed and I want to go for a walk"
query_vector = embed_documents(query)[0]

hits = find_n_closest(query_vector, embeddings)
for hit in hits:
    document = documents[hit["index"]]
    print(document['title of interest'])