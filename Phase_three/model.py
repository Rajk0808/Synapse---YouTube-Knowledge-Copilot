from langchain_openrouter import ChatOpenRouter
import os
from dotenv import load_dotenv
load_dotenv()

ChatModel = ChatOpenRouter(
    model = 'nvidia/nemotron-3-super-120b-a12b:free',
    api_key = os.getenv('OPENROUTER_API_KEY'),
    temperature=0.7
)
