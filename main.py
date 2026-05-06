from fastapi import FastAPI, Request, Response, status, responses, HTTPException
import uvicorn
import time
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database.connection import get_client
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from AI_Backend.pipeline.ingestion_pipeline import Ingest
from AI_Backend.pipeline.deletion_pipeline import Remove
from AI_Backend.pipeline.rag_pipeline import retrieve
from database.models import UserSignpInput, UserloginInput, AddNotebookInput, DeleteNotebook, RenameNotebook, AddSourceInput, DeleteSourceInput
import logging
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")

ph = PasswordHasher()
app = FastAPI()
client_db = get_client()


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
async def chat_ws(websocket : WebSocket, notebook_id: str = None, sources_ids: str = None): 
    await websocket.accept()
    rag = retrieve()
    conv = client_db.table('Conversation').select('*').eq('notebook_id', notebook_id).execute().data
    if not conv:        
        insert_data = {
            "notebook_id": notebook_id,
            "title" : notebook_id
        }
        client_db.table('Conversation').insert(insert_data).execute()
        conversation_id = client_db.table('Conversation').select('conversation_id').eq('notebook_id', notebook_id).execute()
    else:
        conversation_id = conv[0]['conversation_id']
    s_ids = sources_ids.split(',') if sources_ids else []
    data = {'notebook_id': notebook_id, 'sources_ids': s_ids}
    try:
        last_six_messages = client_db.table('Message').select('*').eq('conversation_id',conversation_id).order('created_at', desc=True).limit(6).execute().data[::-1]
        while True:
            user_msg = await websocket.receive_text()
            client_db.table('Message').insert({
                'conversation_id' : conversation_id,
                'sender_type' : 'HumanMessage',
                'content' : user_msg
            }).execute()
            last_six_messages.append({
                'conversation_id' : conversation_id,
                'sender_type' : 'HumanMessage',
                'content' : user_msg,
                'created_at' : time.time()
                })
            if not notebook_id or notebook_id == 'null':
                await websocket.send_text("Error: No notebook active. Please select a notebook to chat.")
                continue
            data['messages'] = last_six_messages
            data['query'] = user_msg
            
            try:
                response = rag.invoke(data=data)
                if hasattr(response, 'content'):
                    content = str(response.content)
                else:
                    content = str(response['response'])
                client_db.table('Message').insert({
                        'conversation_id' : conversation_id,
                        'sender_type' : 'AIMessage',
                        'content' : content
                    }).execute()
                last_six_messages.append({'conversation_id' : conversation_id,
                        'sender_type' : 'AIMessage',
                        'content' : content,
                        'created_at' : time.time()
                        })
                last_six_messages = last_six_messages[-6:]
                await websocket.send_text(content)

            except Exception as e:
                await websocket.send_text(f"An error occurred: {e}")

    except WebSocketDisconnect:
        print("Client disconnected")

@app.get("/chat/",response_class=HTMLResponse)
async def chat(request : Request):
    notebook_id = request.query_params.get("notebook_id")
    data = await loadNotebookSource(notebook_id)
    sources = []
    for source in data.get('sources', []):
        sources.append(source['source_id'])
    return templates.TemplateResponse(
        request=request, 
        name="chatbot.html", 
        context={"message": "chat window", "notebook_id": notebook_id, 'sources' : sources}
    )

@app.get('/chat/get_prev_chat')
async def getPrevChats(notebook_id: str):
    try:
        chats = client_db.table('Conversation').select('*').eq('notebook_id', notebook_id).execute()
        if chats is None:
            return {'messages': []}
        conversation_id = chats.data[0]['conversation_id']
        messages = client_db.table('Message').select('*').eq('conversation_id', conversation_id).execute()
        return {'messages': messages.data if messages.data else []}
    except Exception as e:
        raise e

@app.post('/notebook/sources/add/')
async def addSource(request: AddSourceInput):
    insert_response = client_db.table('Source').insert({
        'notebook_id': request.notebook_id,
        'source_type': request.source_type,
        'file_path': request.url,
        'original_filename': request.title
    }).execute()

    source_id = insert_response.data[0]['source_id']

    ingest_data = {
        'notebook_id': request.notebook_id,
        'user_id': request.user_id,
        'source_id': source_id,
        'url': request.url,
        'languages': ['en'],   
    }

    ingest = Ingest()
    try:
        logger.info(f"Starting ingestion for source_id={source_id}, url={request.url}")
        result = ingest.invoke(ingest_data)
        # Extract title safely; support both legacy and new result formats
        title = None
        if isinstance(result, dict):
            title = result.get("title")
            if not title:
                title = result.get("document", {}).get("title")
        if not title:
            raise HTTPException(status_code=400, detail="Ingestion did not return a title")
        # Update source title regardless of transcript availability
        client_db.table('Source').update({'original_filename': title}).eq('source_id', source_id).execute()
        # Handle possible transcript errors without failing the request
        transcript_error = result.get("transcript_error")
        if transcript_error:
            logger.warning(f"Ingestion completed but transcript missing for source_id={source_id}: {transcript_error}")
            return {"title": title, "warning": transcript_error}
        else:
            logger.info(f"Ingestion successful for source_id={source_id}")
            return title

    except ValueError as e:
        logger.error(f"Ingestion failed for source_id={source_id}: {e}")
        client_db.table('Source').delete().eq('source_id', source_id).execute()
        raise HTTPException(status_code=400, detail=str(e))

@app.post('/notebook/sources/delete/')
async def deleteSource(request: DeleteSourceInput):
    remove = Remove()
    try:
        source = client_db.table('Source').select('*').eq('source_id', request.source_id).maybe_single().execute()
        if source and source.data:
            chunks = client_db.table('SourceChunk').select('*').eq('source_id', request.source_id).execute()
            try:
                if chunks.data:
                    for chunk in chunks.data:
                        client_db.table('Citation').delete().eq('chunk_id', chunk['chunk_id']).execute()
                    client_db.table('SourceChunk').delete().eq('source_id', request.source_id).execute()
            except:
                print('No chunk data.')
        client_db.table('Source').delete().eq('source_id', request.source_id).execute()
        data = {
            'source_id' : request.source_id,
            'notebook_id' : request.notebook_id
        }
        remove.invoke(data)
        return {'message': 'Source Deleted'}
    except Exception as e:
        raise HTTPException(status_code=404, detail= str(e))

@app.get('/notebook/sources/')
async def loadNotebookSource(notebook_id: str):
    source = client_db.table('Source').select('*').eq('notebook_id', notebook_id).execute()
    return {'sources': source.data if source.data else []}


@app.get("/", response_class=HTMLResponse)
async def get(request : Request):
    return templates.TemplateResponse(
        request=request, 
        name="home.html", 
        context={"message": "chat window"}
    )

@app.get("/authentication/", response_class = HTMLResponse)
async def authentication(request : Request):
    return templates.TemplateResponse(
        request = request,
        name    = 'authentication.html',
        context = {'message' : 'authentication'}
    )

@app.post('/user/login')
async def login(request: UserloginInput):
    response = client_db.table('user').select('*').eq('email', request.email).maybe_single().execute()
    user = None if not response else response.data
    if not user:
        return {'authenticated': False, 'message': 'User not found'}
    try: 
        ph.verify(user['password_hash'], request.password)
        return {'authenticated': True, 'user': {'user_id': user['user_id'], 'name': user['username'], 'email': user['email']}}
    except VerifyMismatchError:
        return {'authenticated': False, 'message': 'Invalid password'}
    except Exception as e:
        return {'authenticated': False, 'message': str(e)}
    
@app.post('/user/signup/')
async def signup(request : UserSignpInput):
    existing = client_db.table('user').select('*').eq('email', request.email).maybe_single().execute()
    if existing and existing.data:
        return {'authenticated': False, 'message': 'Email already exists'}
    
    hashed_password = ph.hash(request.password)
    
    new_user = {
        'username' : request.username,
        'email' : request.email,
        'password_hash' : hashed_password
    }

    inserted = client_db.table('user').insert(new_user).execute()

    return {"authenticated" : True, "message": "User created", "user": {"user_id": inserted.data[0]['user_id'], "name": request.username, "email": request.email}}


@app.get('/notebooks/get/')
async def getNotebooks(user_id: str):
    try:
        data = client_db.table('Notebook').select('*').eq('user_id', user_id).execute()
    except Exception as e:
        return {'error' : e}
    return data.data if data.data else []

@app.post('/notebook/add/')
async def addNotebook(request : AddNotebookInput):
    new_notebook = {
        'user_id' : request.user_id,
        'title'   : request.title,
        'description' : request.description
    }
    client_db.table('Notebook').insert(new_notebook).execute()
    return {"message": "Notebook created", "title": request.title}

@app.post('/notebook/delete/')
async def deleteNotebook(request: DeleteNotebook):
    try:
        response =  client_db.table('Conversation').select('conversation_id').eq('notebook_id', request.notebook_id).execute()
        conversations = response.data 
        if conversations:
            for conv in conversations:
                client_db.table('Message').delete().eq('conversation_id', conv['conversation_id']).execute()
            client_db.table('Conversation').delete().eq('notebook_id', request.notebook_id).execute()
        sources = client_db.table('Source').select('source_id').eq('notebook_id', request.notebook_id).execute().data
        if sources:
            for source in sources:
                client_db.table('SourceChunk').delete().eq('source_id', source['source_id']).execute()
            client_db.table('Source').delete().eq('notebook_id', request.notebook_id).execute()
        client_db.table('Notebook').delete().eq('notebook_id', request.notebook_id).execute()
        return {'message': "NoteBook Deleted.", "title": request.title}
    except :
        return {'message' : 'Notebook not found', 'title' : request.title}

@app.post('/notebook/rename/')
async def renameNotebook(request: RenameNotebook):
    client_db.table('Notebook').update({'title': request.new_title}).eq('notebook_id', request.notebook_id).execute()
    client_db.table('Conversation').update({'title': request.new_title}).eq('notebook_id', request.notebook_id).execute()
    return {'message' : "NoteBook Renamed.","title": request.new_title}

@app.get('/notebook/sources/')
async def getNotebookSources(notebook_id: str):
    # Get notebook details
    notebook = client_db.table('Notebook').select('*').eq('notebook_id', notebook_id).maybe_single().execute()
    
    # Get sources for this notebook
    sources = client_db.table('Source').select('*').eq('notebook_id', notebook_id).execute()
    
    return {
        'notebook': notebook.data if notebook.data else None,
        'sources': sources.data if sources.data else []
    }

@app.get('/health/')
async def get_health():
    return {
        'status_code' : 200,
        'status' : "ok"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
