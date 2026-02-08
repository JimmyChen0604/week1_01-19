# ---------------------Step 1: Embed the search query and other documents---------------------
import openai
import numpy as np
from scipy.spatial import distance
import os

# Load API key from environment
# Make sure to set OPENAI_API_KEY in your .env file or environment
openai.api_key = os.getenv("OPENAI_API_KEY")

#----------------------Step 1.1: Combined texts loaded from JSON Files---------------------
user_history = []  # Used to store the user's history (list of document IDs or unique identifiers)

# Document is in JSON format - adjust field names based on your actual data structure
def combined_json(document):
    """Combine document fields into a single text string for embedding"""
    return f"""Title1: {document.get('title1', '')}
    Title2: {document.get('title2', '')}
    Title3: {document.get('title3', '')}"""

#----------------------Step 1.2: Embed the documents using the OpenAI API---------------------
def embed_documents(texts):
    """Embed a list of texts using OpenAI API"""
    if isinstance(texts, str):
        texts = [texts]  # Convert single string to list
    
    response = openai.embeddings.create(
        input=texts,
        model="text-embedding-3-small"
    )
    
    response_dict = response.model_dump()
    return [data["embedding"] for data in response_dict["data"]]

#----------------------Step 2: Calculate similarity scores using cosine similarity----------------------
def find_n_closest(query_vector, embeddings, n=3):
    """Find the n closest documents to the query vector"""
    distances = []
    for i, embedding in enumerate(embeddings):
        dist = distance.cosine(query_vector, embedding)
        distances.append({"index": i, "distance": dist})
    distances_sorted = sorted(distances, key=lambda x: x["distance"])
    return distances_sorted[:n]

#----------------------Step 3: Main recommendation function----------------------
def recommend_documents(query, documents, user_history, n=3):
    """
    Recommend documents based on query, excluding items in user_history
    
    Args:
        query: Search query string
        documents: List of document dictionaries (each should have a unique 'id' field)
        user_history: List of document IDs that user has already viewed
        n: Number of recommendations to return
    
    Returns:
        List of recommended documents
    """
    # Filter out documents that are in the user's history
    # Compare by unique ID (adjust 'id' field name based on your data structure)
    history_ids = set(user_history) if user_history else set()
    documents_filtered = [
        doc for doc in documents 
        if doc.get('id') not in history_ids
    ]
    
    if not documents_filtered:
        print("No new documents to recommend. All documents are in user history.")
        return []
    
    # Embed the filtered documents
    documents_filtered_texts = [combined_json(document) for document in documents_filtered]
    document_embeddings = embed_documents(documents_filtered_texts)
    
    # Embed the query
    query_embedding = embed_documents(query)
    query_vector = query_embedding[0]
    
    # Find closest documents
    hits = find_n_closest(query_vector, document_embeddings, n=n)
    
    # Return recommended documents
    recommendations = []
    for hit in hits:
        document = documents_filtered[hit["index"]]
        recommendations.append(document)
        print(f"Recommended: {document.get('title1', 'N/A')} (distance: {hit['distance']:.4f})")
    
    return recommendations

#----------------------Example Usage----------------------
if __name__ == "__main__":
    # Example documents (replace with your actual data)
    documents = [
        {"id": 1, "title1": "Walking for Mental Health", "title2": "Exercise Benefits", "title3": "Outdoor Activities"},
        {"id": 2, "title1": "Depression Support", "title2": "Mental Health Resources", "title3": "Counseling"},
        {"id": 3, "title1": "Nature Therapy", "title2": "Outdoor Wellness", "title3": "Mindfulness"},
        # Add more documents...
    ]
    
    # Example query
    query = "I feel very depressed and I want to go for a walk"
    
    # Get recommendations (excluding items in user_history)
    recommendations = recommend_documents(query, documents, user_history, n=3)
    
    # Add recommended documents to user history
    for doc in recommendations:
        if doc.get('id') not in user_history:
            user_history.append(doc.get('id'))
    
    print(f"\nUser history updated: {user_history}")