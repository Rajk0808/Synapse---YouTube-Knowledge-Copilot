from langchain_core.output_parsers import JsonOutputParser
from AI_Backend.src.Ingestion.structureOutput.artifactsOutput import (
    SummaryOutput,
    GlossaryOutput,
    KeyPointsOutput,
    QuizOutput
)

summary_parser = JsonOutputParser(pydantic_object=SummaryOutput)
glossary_parser = JsonOutputParser(pydantic_object=GlossaryOutput)
keypoints_parser = JsonOutputParser(pydantic_object=KeyPointsOutput)
quiz_parser = JsonOutputParser(pydantic_object=QuizOutput)