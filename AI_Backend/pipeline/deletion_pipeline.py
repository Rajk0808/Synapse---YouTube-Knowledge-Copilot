from database.connection import vectore_db_client

class Remove():
    def __init__(self):
        self.pc = vectore_db_client()
    
    def invoke(self,data):
        index = self.pc.Index(name= f"{data['notebook_id']}")
        index.delete_namespace(namespace=data['source_id'])
        return {'message' : 'source files removed.'}
        