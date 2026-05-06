from database.connection import vectore_db_client
from typing import Dict
class Retrieve:
    def __init__(self):
        self.pc = vectore_db_client()

    def invoke(self, data : Dict):    
        query      = data['query']
        index      = self.pc.Index(f"{data['notebook_id']}")
        
        contexts = []
        if data['sources_ids']:
            for name_space in data.get('sources_ids', []):
                try:
                    res = index.search(
                        namespace = name_space,
                        query     = {
                            "inputs": {"text": query}, 
                            "top_k" : 5
                        },
                        fields=["category", "text"]
                    )
                    hits = res['result']['hits']
                    for hit in hits:
                        contexts.append(hit)
                except Exception as e:
                    print(f"Error searching namespace {name_space}: {e}")
        contexts = sorted(contexts, key= lambda x : x['_score'], reverse=True)
        data['context'] = contexts[:5]

        return data
        
