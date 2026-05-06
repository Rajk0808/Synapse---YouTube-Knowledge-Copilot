from typing import Any
from langchain_core.output_parsers import PydanticOutputParser
from AI_Backend.src.Ingestion.prompts.autotagging_prompt import template, tags
#from AI_Backend.src.Ingestion.llms.base_huggingface_llm import BaseHuggingFaceLLM
from AI_Backend.src.llms.OpenRouterChat import OpenRouterChat
from CustomException import CustomException
class Tagging:
    def __init__(self):
        self.model = OpenRouterChat(model_name='nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free')
        self.parser = PydanticOutputParser(pydantic_object=tags)

    def invoke(self,segments : dict[str,Any]) -> dict[str, Any]:
        """
        Generate tags for each transcript chunk using a language model.
        
        This function takes the cleaned and chunked transcript segments and generates relevant tags for each segment using a language model. The tags can be used for categorization, search, or other downstream tasks.
        
        Input:
            segments: A list of dictionaries containing the cleaned and chunked transcript segments.
        
        Output:
            A list of tags corresponding to each segment.
        """
        transcript_chunks = segments.get('transcript_chunks', [])
        for transcript_chunk in transcript_chunks:
            text = transcript_chunk['text']
            prompt = template.invoke({'text' : text})
            response_text = self.model.invoke(prompt)
            try:
                generated_tags = self.parser.parse(response_text.content)
                transcript_chunk['tags'] = generated_tags.model_dump()
            except Exception:
                raise CustomException('Error : in Tagging.')
        return segments
