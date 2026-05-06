from langchain_openrouter import ChatOpenRouter
from pydantic import SecretStr
from dotenv import load_dotenv
import os
load_dotenv()

class OpenRouterChat:
    def __init__(self,model_name = "qwen/qwen3.6-plus:free") -> None:
            self.model = ChatOpenRouter(
                model=model_name,
                temperature=0.8,
                api_key=SecretStr(os.getenv("OPENROUTER_API_KEY") or "")
            )
    def invoke(self, prompt):
        return self.model.invoke(input=prompt)