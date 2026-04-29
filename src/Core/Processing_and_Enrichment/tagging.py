from typing import Any
from langchain_core.output_parsers import PydanticOutputParser
from src.Core.prompts.autotagging_prompt import template, tags
from src.Core.models.base_huggingface_llm import BaseHuggingFaceLLM

class Tagging:
    def __init__(self):
        self.model = BaseHuggingFaceLLM(model_name="Qwen/Qwen2.5-7B-Instruct")
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
            prompt = template.format(text=text)
            prompt_with_format = (
                f"{prompt}\n\n"
                f"Return only valid JSON matching this schema:\n"
                f"{self.parser.get_format_instructions()}"
            )

            response_text = self.model.invoke(prompt_with_format)
            try:
                generated_tags = self.parser.parse(str(response_text))
                transcript_chunk['tags'] = generated_tags.model_dump()
            except Exception:
                # Keep pipeline resilient when model returns malformed JSON.
                transcript_chunk['tags'] = {
                    "topic": "unknown",
                    "difficulty": "unknown",
                    "entities": "unknown",
                    "speaker": "unknown",
                    "tone": "unknown",
                    "content_type": "unknown"
                }
        return segments
