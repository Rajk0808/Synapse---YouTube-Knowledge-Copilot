from AI_Backend.src.llms.base_huggingface_llm import BaseHuggingFaceLLM
import logging
class Generation:
    def __init__(self):
        self.model = BaseHuggingFaceLLM(model_name='Qwen/Qwen2.5-7B-Instruct')

    def invoke(self,data):
        prompt = data['prompt']
        logging.info(f'PROMPT : {prompt}')
        data['response'] = self.model.invoke(prompt)
        return data