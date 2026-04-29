from typing import Any
from src.Core.prompts.artifacts_prompt import (
    summary_prompt_template, 
    glossary_prompt_template, 
    keypoints_prompt_template,
    quiz_prompt_template)
from src.Core.Parser.artifactsParser import (
    summary_parser,
    glossary_parser,
    keypoints_parser,
    quiz_parser
)
from src.Core.models.base_huggingface_llm import BaseHuggingFaceLLM

class Artifacts:
    def __init__(self):
        self.model = BaseHuggingFaceLLM(model_name="Qwen/Qwen2.5-7B-Instruct")

    def build_summary(self, text : str)->dict:
        """This method takes a text input and generates a summary using the defined prompt template. It then parses the output as JSON and returns it as a dictionary."""
        prompt = summary_prompt_template.format(
            text=text,
            format_instructions=summary_parser.get_format_instructions(),
        )
        result = self.model.invoke(prompt=prompt)
        return summary_parser.parse(str(result))

    def build_glossary(self,text : str) -> dict:
        """This method takes a text input and extracts key terms and their definitions using the defined prompt template. It then parses the output as JSON and returns it as a dictionary."""
        prompt = glossary_prompt_template.format(
            text=text,
            format_instructions=glossary_parser.get_format_instructions(),
        )
        result = self.model.invoke(prompt=prompt)
        return glossary_parser.parse(str(result)) 
    
    def build_key_points(self,text : str, chunk_id : int, ) -> dict:
        """This method takes a text input and extracts key points using the defined prompt template. It then parses the output as JSON and returns it as a dictionary."""
        prompt = keypoints_prompt_template.format(
            text=text,
            chunk_id=chunk_id,
            format_instructions=keypoints_parser.get_format_instructions(),
        )
        result = self.model.invoke(prompt=prompt)
        return keypoints_parser.parse(str(result)) 
    
    def build_quiz(self,text : str) -> dict:
        """This method takes a text input and generates quiz questions using the defined prompt template. It then parses the output as JSON and returns it as a dictionary."""
        prompt = quiz_prompt_template.format(
            text=text,
            format_instructions=quiz_parser.get_format_instructions(),
        )
        result = self.model.invoke(prompt=prompt)
        return quiz_parser.parse(str(result)) 

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
            return {"error": str(exc)}

    def invoke(self, segment: dict[str,Any]) -> dict[str,Any]:
        """Generate chunk-level and document-level derived artifacts."""

        transcript_chunks = segment.get("transcript_chunks", [])

        for chunk in transcript_chunks:
            text = chunk.get('text', '')
            chunk_id = chunk.get('chunk_id', 0)
            chunk['artifacts'] = {
                'summary': self._safe_parse(self.build_summary, text),
                'glossary': self._safe_parse(self.build_glossary, text),
                'key_points': self._safe_parse(self.build_key_points, text, chunk_id),
                'quiz': self._safe_parse(self.build_quiz, text),
            }

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
