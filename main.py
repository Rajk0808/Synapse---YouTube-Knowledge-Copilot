from fastapi import FastAPI, Request, Response, status, responses
from pydantic import BaseModel
from Phase_one.embeddings import embed
from Phase_one.semanticSearch import cosine_similarity, euclidean_distance, dot_product
from logging import getLogger
import asyncio
import time
from fastapi import WebSocket, WebSocketDisconnect
import Phase_three.chat_openrouter as chat_openrouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

logger = getLogger()
app = FastAPI()


# MiddleWares
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=30)
    except asyncio.TimeoutError:
        return Response(content="Service Timeout", status_code=504)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    print(f"Request: {request.method} {request.url.path} | Time: {process_time:.4f}s")
    return response

allowed_methods = set(['GET','POST'])
@app.middleware('http')
async def cors_middleware(request: Request, call_next):
    if request.method not in allowed_methods and request.method != 'OPTIONS':
        return responses.JSONResponse(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            content = {"detail": f"Method {request.method} not allowed"}
        )
    response = await call_next(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Web Sockets
@app.websocket('/ws/chat')
async def chat(websocket : WebSocket): 
    await websocket.accept()
    messages = chat_openrouter.messages
    try:
        while True:
            user_msg = await websocket.receive_text()
            
            messages, response = chat_openrouter.chat_openrouter(user_msg, messages)
            print(messages)
            await websocket.send_text(response.content)

    except WebSocketDisconnect:
        print("Client disconnected")


@app.get("/",response_class=HTMLResponse)
async def get(request : Request):
    return templates.TemplateResponse(
        request=request, 
        name="chatbot.html", 
        context={"message": "Hello World"}
    )
