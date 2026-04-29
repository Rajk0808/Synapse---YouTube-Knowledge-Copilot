"""
Embedding model module for generating embeddings from cleaned and chunked transcript data. This module defines a Model class that initializes a HuggingFaceEndpointEmbeddings instance with the specified model and task. The Model class provides a method to retrieve the initialized embedding model, which can be used in the Embeddings class for generating embeddings for transcript chunks.
"""
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpointEmbeddings

load_dotenv()

class Model:
    def __init__(self):
        self.endpoint_embeddings = HuggingFaceEndpointEmbeddings(
            model="sentence-transformers/all-mpnet-base-v2",
            task="feature-extraction"
        )
    def __get__(self):
        return self.endpoint_embeddings
        
