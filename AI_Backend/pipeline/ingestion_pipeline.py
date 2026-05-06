from AI_Backend.src.Ingestion.Ingestion_Service.Input_Ingestion import Utils
from AI_Backend.src.Ingestion.Processing_and_Enrichment.preprocessing_enrichment import preprocessing_enrichment
from AI_Backend.src.Ingestion.store_Embeddings.store_embeddings import StoreEmbeddings

class Ingest:
    def __init__(self):
        '''
        Args :
              data : it is a dictionary which contains url, user_id, notebook_id, source_id, language.
        '''
        step1 = Utils()
        step2 = preprocessing_enrichment()
        step3 = StoreEmbeddings()

        self.chain = step1 | step2 | step3  

    def invoke(self,data):
        return self.chain.invoke(data)