from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from dotenv import load_dotenv
import os

load_dotenv()

class BaseHuggingFaceLLM:
    def __init__(self, model_name: str):
        self.llm = HuggingFaceEndpoint(
            model=model_name,
            huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN")
        )
        self.model = ChatHuggingFace(llm=self.llm)

    def invoke(self, prompt: str):
        response = self.model.invoke(prompt)
        return response.content