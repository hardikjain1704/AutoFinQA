# auto_finQA/router/main.py

import os
import uvicorn
import shutil
from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Tuple, Dict

from workflow.simple_rag_workflow import invoke_chain as invoke_simple_chain
from workflow.agentic_workflow import invoke_agent_chain
from etl.data_ingestion import DataIngestion
from logger import GLOBAL_LOGGER as log
from exception.custom_exception import AutoFinQAException

# --- Singleton Instances and Lifespan Management ---

app_state = {}

#Simple in-memory session store
# Stores chat history as: {session_id: [(user_query, ai_response), ...]}
# In production, use Redis or a database.
session_memory: Dict[str, Dict[str, List[Tuple[str, str]]]] = {
    "simple_rag": {},
    "agent_rag": {}
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup events. Initializes the DataIngestion pipeline once.
    """
    log.info("Server is starting up...")
    try:
        app_state["ingestion_instance"] = DataIngestion()
        log.info("Data Ingestion pipeline has been successfully initialized.")
        Path("temp_uploads").mkdir(exist_ok=True)
    except Exception as e:
        log.error("CRITICAL: Failed to initialize services during startup.", exc_info=e)
        raise RuntimeError("Could not initialize the core services.") from e
    
    yield  # The application runs here
    
    log.info("Server is shutting down.")
    if Path("temp_uploads").exists():
        shutil.rmtree("temp_uploads")

# Application Setup
load_dotenv()
app = FastAPI(
    title="AutoFinQA RAG API",
    version="1.0",
    description="API for comparing Simple RAG and Agentic RAG workflows.",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# Pydantic Models
class QueryRequest(BaseModel):
    query: str = Field(..., description="The user's question about financial documents.")
    # Session ID is now required for memory
    session_id: str = Field("default_user", description="A unique ID for the user session.")

class QueryResponse(BaseModel):
    answer: str
    session_id: str

class UploadResponse(BaseModel):
    message: str
    filename: str

# API Endpoints
@app.get("/health", summary="Health Check")
def health():
    log.info("Health check endpoint was called.")
    return {"status": "ok"}

@app.post("/upload", response_model=UploadResponse, summary="Upload and Process a Document")
def upload_document(file: UploadFile = File(...)):
    ingestion_instance = app_state.get("ingestion_instance")
    if not ingestion_instance:
        raise HTTPException(status_code=503, detail="Ingestion service is not ready.")

    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    
    safe_filename = Path(file.filename).name
    file_path = temp_dir / safe_filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        log.info(f"File '{file.filename}' saved temporarily to '{file_path}'")

        # Ingest the file
        ingestion_instance.ingest_single_document(str(file_path))
        
        return UploadResponse(
            message="File processed and ingested successfully.",
            filename=file.filename
        )
    except Exception as e:
        log.error(f"Failed to ingest file: {file.filename}", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if file_path.exists():
            os.remove(file_path)
            log.info(f"Temporary file '{file_path}' deleted.")

@app.post("/ask", response_model=QueryResponse, summary="Ask a Question (Simple RAG)")
def ask_question(request: QueryRequest):
    """
    This endpoint uses the simple, conversational RAG workflow.
    It maintains chat history based on `session_id`.
    """
    try:
        log.info(f"Received simple RAG query for session: '{request.session_id}'")
        
        # 1. Retrieve chat history
        history = session_memory["simple_rag"].get(request.session_id, [])
        
        # 2. Call the workflow with history
        answer = invoke_simple_chain(query=request.query, chat_history=history)
        
        # 3. Update chat history
        history.append((request.query, answer))
        session_memory["simple_rag"][request.session_id] = history
        
        log.info("Successfully generated answer with simple RAG.")
        return QueryResponse(answer=answer, session_id=request.session_id)
    
    except Exception as e:
        log.error("An unexpected server error occurred during query.", exc_info=e)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

# ENDPOINT FOR AGENTIC RAG
@app.post("/ask-agent", response_model=QueryResponse, summary="Ask a Question (Agentic RAG)")
def ask_agent_question(request: QueryRequest):
    """
    This endpoint uses the advanced, agentic RAG workflow.
    It maintains separate chat history and uses tools (retriever, calculator).
    """
    try:
        log.info(f"Received Agentic RAG query for session: '{request.session_id}'")
        
        # 1. Retrieve chat history (Agent has its own memory space)
        history = session_memory["agent_rag"].get(request.session_id, [])
        
        # 2. Call the agent workflow
        # We pass None for callbacks (it uses LangSmith via env vars by default)
        answer = invoke_agent_chain(
            query=request.query, 
            session_id=request.session_id, 
            chat_history=history, 
            callbacks=None 
        )
        
        # 3. Update chat history
        history.append((request.query, answer))
        session_memory["agent_rag"][request.session_id] = history
        
        log.info("Successfully generated answer with Agentic RAG.")
        return QueryResponse(answer=answer, session_id=request.session_id)
    
    except Exception as e:
        log.error("An unexpected server error occurred during agent query.", exc_info=e)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")