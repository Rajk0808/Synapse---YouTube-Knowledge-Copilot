from langchain_core.messages import HumanMessage, SystemMessage
from Phase_three.model import ChatModel

messages = [
    SystemMessage(    
    "You are Synapse, a helpful and intelligent AI assistant. "
    "Format your responses using markdown — use **bold**, bullet points, "
    "tables, code blocks, and headings where appropriate. "
    "Be concise, clear, and friendly.")
]
def chat_openrouter(user_input: str, messages: list)-> str:
    if len(messages) > 7:
        system_message = messages[0]
        messages = messages[-6:]
        messages = system_message + messages
    messages.append(HumanMessage(content = user_input))
    response = ChatModel.invoke(messages)
    messages.append(response)
    return messages, response
