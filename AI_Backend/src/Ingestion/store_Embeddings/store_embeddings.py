from database.connection import vectore_db_client
from typing import Dict

class StoreEmbeddings():
    def __init__(self):
        self.client_pc = vectore_db_client()

    def invoke(self, data :Dict):
        index_name = f'{data['notebook_id']}'
        namespace = data['source_id']
        pc = self.client_pc
        if not pc.has_index(index_name):
            pc.create_index_for_model(
                name=index_name,
                cloud="aws",
                region="us-east-1",
                embed={
                    "model":"llama-text-embed-v2",
                    "field_map":{"text": "text"}
                }
            )
        chunks = []
        for chunk in data['chunks']:
            chunks.append({
                'id' : chunk['id'],
                "text": chunk['text']
            })
            
        if not chunks:
            raise ValueError("No transcript chunks were generated for this video. The video might not have English captions available, or it is too short.")
            
        index = pc.Index(name=index_name)
        index.upsert_records(namespace=namespace,records=chunks)
        return data