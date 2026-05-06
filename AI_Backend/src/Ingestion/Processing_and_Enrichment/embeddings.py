"""
Embeddings module for processing and enrichment of YouTube chat data. This module provides functionality to generate embeddings from cleaned and chunked transcript data, which can be used for various downstream tasks such as search, summarization, or question-answering.
"""

from dotenv import load_dotenv
from AI_Backend.src.llms.embedding_model import Model
from typing import Any
load_dotenv()

class Embeddings:
    def __init__(self):
        self.endpoint_embeddings = Model().__get__()

    def invoke(self,segments : dict[str,Any]) -> dict[str, Any]:
        """
        Generate embeddings from cleaned and chunked transcript data.
        
        This function takes the cleaned and chunked transcript segments and generates vector embeddings for each segment. The embeddings can be used for various downstream tasks such as search, summarization, or question-answering.
        
        Input:
            segments: A list of dictionaries containing the cleaned and chunked transcript segments.
        
        Output:
            A list of embeddings corresponding to each segment.
        """
        transcript_chunks = segments.get('transcript_chunks', [])
        for transcript_chunk in transcript_chunks:
            text = transcript_chunk['metadata']['text']
            embedding = self.endpoint_embeddings.embed_query(text)
            transcript_chunk['values'] = embedding
        return segments

