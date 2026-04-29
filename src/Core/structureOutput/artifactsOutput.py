from pydantic import BaseModel, Field
class Points(BaseModel):
    point : str = Field(description="Key point extracted from the transcript chunk")
    chunk_id : int = Field(description="ID of the transcript chunk from which the key point was extracted")

class KeyPointsOutput(BaseModel):
    key_points : list[Points] = Field(description="List of key points extracted from the transcript chunk")

class Summary(BaseModel):
    short_summary : str = Field(description="A concise summary of the transcript chunk")
    long_summary : str = Field(description="A detailed summary of the transcript chunk")

class SummaryOutput(BaseModel):
    summary : dict[str, Summary] = Field(description="Summary of the transcript chunk")

class GlossaryTerm(BaseModel):
    term : str = Field(description="Key term extracted from the transcript chunk")
    definition : str = Field(description="Definition of the key term")

class GlossaryOutput(BaseModel):
    glossary : list[GlossaryTerm] = Field(description="List of key terms and their definitions extracted from the transcript chunk")

class QuizQuestion(BaseModel):
    question : str = Field(description="Quiz question generated from the transcript chunk")
    answer : str = Field(description="Answer to the quiz question")
    type : str = Field(description="Type of the quiz question (e.g., multiple choice, short answer)")

class QuizOutput(BaseModel):
    quiz : list[QuizQuestion] = Field(description="List of quiz questions generated from the transcript chunk")