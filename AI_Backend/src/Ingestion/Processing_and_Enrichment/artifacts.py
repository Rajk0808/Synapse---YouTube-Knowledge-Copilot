from typing import Any
from AI_Backend.src.Ingestion.prompts.artifacts_prompt import (
    summary_prompt_template, 
    glossary_prompt_template, 
    keypoints_prompt_template,
    quiz_prompt_template)
from AI_Backend.src.Ingestion.Parser.artifactsParser import (
    summary_parser,
    glossary_parser,
    keypoints_parser,
    quiz_parser
)

#from AI_Backend.src.Ingestion.llms.base_huggingface_llm import BaseHuggingFaceLLM
from AI_Backend.src.llms.OpenRouterChat import ChatOpenRouter

class Artifacts:
    def __init__(self):
        self.model = ChatOpenRouter(model_name='nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free')

    def build_summary(self, text : str)->dict:
        """This method takes a text input and generates a summary using the defined prompt template. It then parses the output as JSON and returns it as a dictionary."""
        prompt = summary_prompt_template.invoke(
            input={"text" : text,
            "format_instructions" : summary_parser.get_format_instructions()
            })
        result = self.model.invoke(prompt)
        return summary_parser.parse(str(result.content))

    def build_glossary(self,text : str) -> dict:
        """This method takes a text input and extracts key terms and their definitions using the defined prompt template. It then parses the output as JSON and returns it as a dictionary."""
        prompt = glossary_prompt_template.invoke({
            "text":text,
            "format_instructions":glossary_parser.get_format_instructions()
        })
        result = self.model.invoke(prompt)
        return glossary_parser.parse(result.content) 
    
    def build_key_points(self,text : str, id : int, ) -> dict:
        """This method takes a text input and extracts key points using the defined prompt template. It then parses the output as JSON and returns it as a dictionary."""
        prompt = keypoints_prompt_template.invoke({
            "text":text,
            "id":id,
            "format_instructions":keypoints_parser.get_format_instructions()
        })
        result = self.model.invoke(prompt)
        return keypoints_parser.parse(result.content) 
    
    def build_quiz(self,text : str) -> dict:
        """This method takes a text input and generates quiz questions using the defined prompt template. It then parses the output as JSON and returns it as a dictionary."""
        prompt = quiz_prompt_template.invoke({
            "text":text,
            "format_instructions":quiz_parser.get_format_instructions()
        })
        result = self.model.invoke(prompt)
        return quiz_parser.parse(str(result.content)) 

    def _safe_parse(self, builder, *args) -> dict[str, Any]:
        """Keep artifact generation resilient when the model output is malformed."""

        try:
            parsed = builder(*args)
            if hasattr(parsed, "model_dump"):
                return parsed.model_dump()
            if isinstance(parsed, dict):
                return parsed
            return {"raw": parsed}
        except Exception as exc:
            raise exc

    def invoke(self, segment: dict[str,Any]) -> dict[str,Any]:
        """Generate chunk-level and document-level derived artifacts."""

        transcript_chunks = segment.get("transcript_chunks", [])
        full_text = segment.get("transcript_text", "")
        if not full_text and transcript_chunks:
            full_text = " ".join(
                str(chunk.get("text", "")).strip()
                for chunk in transcript_chunks
                if str(chunk.get("text", "")).strip()
            )
        
        segment["artifacts"] = {
            "summary": self._safe_parse(self.build_summary, full_text) if full_text else {},
            "glossary": self._safe_parse(self.build_glossary, full_text) if full_text else {},
            "key_points": self._safe_parse(self.build_key_points, full_text, 0) if full_text else {},
            "quiz": self._safe_parse(self.build_quiz, full_text) if full_text else {},
        }
        return segment
