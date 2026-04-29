import os
from typing import Literal

from src.Core.Ingestion_Service.Input_Ingestion import Utils
from src.Indexing_layer.indexing import IndexingLayer
from src.Indexing_layer.supabase_vector_client import SupabaseVectorClient
from src.Core.Processing_and_Enrichment.preprocessing_enrichment import (
    preprocessing_enrichment,
)


step1 = Utils()
step2 = preprocessing_enrichment()
storage_mode: Literal["local", "vectordb", "both"] = os.getenv("INDEX_STORAGE_MODE", "local")  # type: ignore[assignment]

vector_db_client = None
if storage_mode in {"vectordb", "both"}:
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not supabase_key:
        raise ValueError(
            "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
            "when INDEX_STORAGE_MODE is 'vectordb' or 'both'."
        )

    vector_db_client = SupabaseVectorClient(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
    )

step3 = IndexingLayer(storage_mode=storage_mode, vector_db_client=vector_db_client)

chain = step1 | step2 | step3


if __name__ == "__main__":
    url = "https://youtu.be/dhSJKmbHaEY?si=1blKeIu_o5S3xfut"
    data = {
        "url": url,
        "languages": ["en"],
        "workspace_id": os.getenv("WORKSPACE_ID"),
        "owner_user_id": os.getenv("OWNER_USER_ID"),
    }
    result = chain.invoke(data)
    print("index_result:", result)

