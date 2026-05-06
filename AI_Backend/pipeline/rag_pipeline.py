from AI_Backend.src.retrieval.retrieval import Retrieve
from AI_Backend.src.retrieval.augmentation import Augment
from AI_Backend.src.retrieval.generation import Generation
from langchain_core.runnables import RunnableLambda

class retrieve():
    def __init__(self):
        retriver = RunnableLambda(Retrieve().invoke)
        augmentator = RunnableLambda(Augment().invoke)
        generator = RunnableLambda(Generation().invoke)
    
        self.chain = retriver | augmentator | generator
    
    def invoke(self,data):
        """   
        data must contain notebook_id, source_id, query.
        """
        return self.chain.invoke(data)

