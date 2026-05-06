from supabase import create_client, Client
from dotenv import load_dotenv
import os    
from pinecone import Pinecone

load_dotenv()

def get_client()-> Client:
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    return create_client(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)

def vectore_db_client():
    PINECONE_KEY = os.getenv('PINECONE_API_KEY')
    pc = Pinecone(api_key=PINECONE_KEY)
    return pc