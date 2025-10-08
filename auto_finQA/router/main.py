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
from workflow.simple_rag_workflow import invoke_chain
from etl.data_ingestion import DataIngestion
from logger import GLOBAL_LOGGER as log
from exception.custom_exception import AutoFinQAException

# --- Singleton Instances and Lifespan Management ---

# Global dictionary to hold our initialized services
app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup events. Initializes the DataIngestion pipeline once.
    The simple RAG workflow's models are loaded automatically on module import.
    """
    log.info("Server is starting up...")
    try:
        # On startup, initialize the ingestion component for the /upload route
        app_state["ingestion_instance"] = DataIngestion()
        log.info("Data Ingestion pipeline has been successfully initialized.")
        # Create a temporary directory for file uploads
        Path("temp_uploads").mkdir(exist_ok=True)
    except Exception as e:
        log.error("CRITICAL: Failed to initialize services during startup.", exc_info=e)
        raise RuntimeError("Could not initialize the core services.") from e
    
    yield  # The application runs here
    
    log.info("Server is shutting down.")
    # Cleanup can be added here if needed

# --- Application Setup ---
load_dotenv()
app = FastAPI(
    title="AutoFinQA Simple RAG API",
    version="1.0",
    description="A simple RAG API for uploading documents and answering questions.",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- Pydantic Models for API Data Structure ---
class QueryRequest(BaseModel):
    query: str = Field(..., description="The user's question about financial documents.")

class QueryResponse(BaseModel):
    answer: str

class UploadResponse(BaseModel):
    message: str
    filename: str

# --- API Endpoints ---
@app.get("/health", summary="Health Check")
def health():
    """Confirms that the API is running."""
    log.info("Health check endpoint was called.")
    return {"status": "ok"}

@app.post("/upload", response_model=UploadResponse, summary="Upload and Process a Document")
def upload_document(file: UploadFile = File(...)):
    """
    Accepts a document, saves it temporarily, and ingests its content
    into the vector database.
    """
    ingestion_instance = app_state.get("ingestion_instance")
    if not ingestion_instance:
        raise HTTPException(status_code=503, detail="Ingestion service is not ready.")

    temp_dir = Path("temp_uploads")
    safe_filename = Path(file.filename).name
    file_path = temp_dir / safe_filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        log.info(f"File '{file.filename}' saved temporarily to '{file_path}'")

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
    This endpoint uses the simple, non-agentic RAG workflow to answer a question.
    """
    try:
        log.info(f"Received simple RAG query: '{request.query}'")
        
        # The 'invoke_chain' function from your working script is called here.
        answer = invoke_chain(query=request.query)
        
        log.info("Successfully generated answer with simple RAG.")
        return QueryResponse(answer=answer)
    
    except Exception as e:
        log.error("An unexpected server error occurred during query.", exc_info=e)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

