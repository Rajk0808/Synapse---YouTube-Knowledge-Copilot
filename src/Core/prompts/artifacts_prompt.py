from langchain_core.prompts import PromptTemplate
from src.Core.Parser.artifactsParser import (
    summary_parser, 
    glossary_parser, 
    keypoints_parser,
    quiz_parser)
summary_prompt_template = PromptTemplate(
    input_variables=["text"],
    template=(
        "You are a helpful assistant that summarizes the following text.\n\n"
        "Text:\n{text}\n\n"
        "Return only valid JSON.\n"
        "{format_instructions}"
    ),
    partial_variables={"format_instructions": summary_parser.get_format_instructions()}
)

glossary_prompt_template = PromptTemplate(
    input_variables=["text"],
    template=(
        "You are a helpful assistant that extracts key terms and their definitions from the following text.\n\n"
        "Text:\n{text}\n\n"
        "Return only valid JSON.\n"
        "{format_instructions}"
    ),
    partial_variables={"format_instructions": glossary_parser.get_format_instructions()}
)

keypoints_prompt_template = PromptTemplate(
    input_variables=["text", "chunk_id" ],
    template=(
        "You are a helpful assistant that extracts key points from the following text.\n\n"
        "Chunk id: {chunk_id}\n"
        "Text:\n{text}\n\n"
        "Return only valid JSON.\n"
        "{format_instructions}"
    ),
    partial_variables={"format_instructions": keypoints_parser.get_format_instructions()}
)

quiz_prompt_template = PromptTemplate(
    input_variables=["text"],
    template=(
        "You are a helpful assistant that generates quiz questions based on the following text.\n\n"
        "Text:\n{text}\n\n"
        "Return only valid JSON.\n"
        "{format_instructions}"
    ),
    partial_variables={"format_instructions":  quiz_parser.get_format_instructions()})
