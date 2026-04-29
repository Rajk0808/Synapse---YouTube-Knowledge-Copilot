from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv('OPENROUTER_API_KEY'),
)

def embed(text):
    return client.embeddings.create(
        model="nvidia/llama-nemotron-embed-vl-1b-v2:free",
        input=[
            {
                "content": [
                    {"type": "text", "text": text}
                ]
            }
        ],
        encoding_format="float"
    )


#print(len(embed("What is the capital of France?").data[0].embedding))