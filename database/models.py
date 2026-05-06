from pydantic import BaseModel

class UserSignpInput(BaseModel):
    username : str
    email : str
    password : str

class UserloginInput(BaseModel):
    email : str
    password : str

class GetNotebookInput(BaseModel):
    user_id : str

class AddNotebookInput(BaseModel):
    user_id     : str
    title       : str
    description : str = ''
    color_index : int = 0

class DeleteNotebook(BaseModel):
    notebook_id : str
    title       : str

class RenameNotebook(BaseModel):
    notebook_id : str
    new_title   : str

class GetPrevChats(BaseModel):
    notebook_id : str

class AddSourceInput(BaseModel):
    user_id : str
    notebook_id: str
    source_type: str
    url: str
    title: str

class DeleteSourceInput(BaseModel):
    notebook_id : str
    source_id: str
