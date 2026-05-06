from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser



#output Schema
class tags(BaseModel):
    topic: str = Field(description="The main topic of the content, such as politics, trailer, tutorial, interview.")
    difficulty: str = Field(description="The difficulty level of the content, such as beginner, intermediate, advanced.")
    entities: str = Field(description="The key entities mentioned in the content, such as people, organizations, places.")
    speaker: str = Field(description="The speaker of the content if detectable.")
    tone: str = Field(description="The tone of the content, which is optional.")
    content_type: str = Field(description="The type of content, such as explanation, argument, announcement, Q&A.")

parser = JsonOutputParser(pydantic_object=tags)


template = PromptTemplate(
    template = """
                You are an expert in tagging and categorizing content. Your task is to analyze the following text and generate a list of relevant tags that best describe the content.
                
                For each chunk, generate structured tags:
                
                topic: politics, trailer, tutorial, interview
                
                difficulty: beginner, intermediate, advanced
                
                entities: people, orgs, places
                
                speaker: if detectable
                
                tone: optional
                
                content_type: explanation, argument, announcement, Q&A
                
                here is the text to analyze:
                {text}
                """,
                input_variables=["text"],
                partial_variables={"format_instructions" : parser.get_format_instructions()},   
                )