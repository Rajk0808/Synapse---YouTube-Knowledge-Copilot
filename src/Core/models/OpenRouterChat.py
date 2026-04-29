from langchain_openrouter import ChatOpenRouter
from pydantic import SecretStr
from dotenv import load_dotenv
import os
load_dotenv()

class OpenRouterChat:
    def __init__(self) -> None:
            self.model = ChatOpenRouter(
                model="qwen/qwen3.6-plus:free",
                temperature=0.8,
                api_key=SecretStr(os.getenv("OPENROUTER_API_KEY") or "")
            )
    def __get__(self):
        return self.model