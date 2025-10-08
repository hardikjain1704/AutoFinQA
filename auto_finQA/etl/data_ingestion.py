# data_ingestion.py

import os
import sys
import json
from pathlib import Path
from typing import List

import pandas as pd
from docx import Document as DocxDocument
from dotenv import load_dotenv
from pymongo import MongoClient

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_community.document_loaders import PyMuPDFLoader

from utils.model_loader import ModelLoader
from logger import GLOBAL_LOGGER as log
from exception.custom_exception import AutoFinQAException
from utils.config_loader import load_config


SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.md', '.csv', '.json'}

class DocumentLoader:
    @staticmethod
    def load_documents(file_paths: List[Path]) -> List[Document]:
        docs = []
        for file_path in file_paths:
            try:
                extension = file_path.suffix.lower()
                if extension not in SUPPORTED_EXTENSIONS:
                    log.warning(f"Skipping unsupported file type: {file_path}")
                    continue
                
                if extension == '.pdf':
                    loader = PyMuPDFLoader(str(file_path))
                    docs.extend(loader.load())
                elif extension == '.docx':
                    docs.append(DocumentLoader._load_docx(file_path))
                elif extension in ['.txt', '.md']:
                    docs.append(DocumentLoader._load_text(file_path))
                elif extension == '.csv':
                    docs.append(DocumentLoader._load_csv(file_path))
                elif extension == '.json':
                    docs.append(DocumentLoader._load_json(file_path))
            except Exception as e:
                raise AutoFinQAException(f"Failed to load document: {file_path}", e)
        return docs
    
    @staticmethod
    def _load_docx(file_path: Path) -> Document:
        doc = DocxDocument(file_path)
        content = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return Document(page_content=content, metadata={"source": str(file_path.name)})

    @staticmethod
    def _load_text(file_path: Path) -> Document:
        content = file_path.read_text(encoding="utf-8")
        return Document(page_content=content, metadata={"source": str(file_path.name)})

    @staticmethod
    def _load_csv(file_path: Path) -> Document:
        df = pd.read_csv(file_path)
        return Document(page_content=df.to_string(), metadata={"source": str(file_path.name)})

    @staticmethod
    def _load_json(file_path: Path) -> Document:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Document(page_content=json.dumps(data, indent=2), metadata={"source": str(file_path.name)})


class DataIngestion:
    def __init__(self):
        load_dotenv()
        self.config = load_config()
        self.model_loader = ModelLoader() 
        self.embeddings = self.model_loader.load_embeddings()
        
        self._load_db_config()
        log.info("DataIngestion pipeline initialized.")

    def _load_db_config(self):
        self.mongo_uri = os.getenv("MONGO_URI")
        if not self.mongo_uri:
            raise AutoFinQAException("Missing environment variable: MONGO_URI", sys)
        
        try:
            mongo_config = self.config['mongodb']
            self.db_name = mongo_config['db_name']
            self.collection_name = mongo_config['collection_name']
            self.index_name = mongo_config['index_name']
        except KeyError as e:
            raise AutoFinQAException(f"Missing required key in config.yaml under 'mongodb': {e}", sys)

    def _split_documents(self, docs: List[Document]) -> List[Document]:
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(docs)
        log.info(f"Split {len(docs)} documents into {len(chunks)} chunks.")
        return chunks
    
    def ingest_single_document(self, doc_path_str: str):
        """Loads, splits, and ingests a single document into the vector store."""
        try:
            log.info(f"Starting ingestion for single document: {doc_path_str}")
            doc_path = Path(doc_path_str)
            raw_documents = DocumentLoader.load_documents([doc_path])
            
            if not raw_documents:
                log.warning(f"No content could be loaded from {doc_path_str}.")
                return

            chunks = self._split_documents(raw_documents)
            
            client = MongoClient(self.mongo_uri)
            collection = client[self.db_name][self.collection_name]

            log.info("Adding documents to MongoDB Atlas Vector Search...")
            MongoDBAtlasVectorSearch.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                collection=collection, # Pass the collection object
                index_name=self.index_name
            )
            
            log.info(f"Successfully added {len(chunks)} chunks from '{doc_path.name}'.")

        except Exception as e:
            raise AutoFinQAException(f"Single document ingestion failed for {doc_path_str}", e)

    def ingest_from_directory(self, data_dir: str):
        try:
            data_path = Path(data_dir)
            if not data_path.is_dir():
                raise AutoFinQAException(f"Provided data path is not a directory: {data_dir}", sys)
            
            all_files = [p for p in data_path.rglob("*") if p.is_file()]
            raw_documents = DocumentLoader.load_documents(all_files)
            
            if not raw_documents:
                log.warning("No new supported documents found to ingest.")
                return

            chunks = self._split_documents(raw_documents)

            client = MongoClient(self.mongo_uri)
            collection = client[self.db_name][self.collection_name]
            
            MongoDBAtlasVectorSearch.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                collection=collection,
                index_name=self.index_name
            )
            log.info(f"Successfully added {len(chunks)} document chunks to MongoDB.")

        except Exception as e:
            raise AutoFinQAException("Data ingestion pipeline failed.", e)

# --- ADDED THIS EXECUTABLE BLOCK ---
if __name__ == '__main__':
    """
    This block allows the script to be run directly from the command line
    to ingest documents from a specified directory.
    """
    # By default, the script will look for a 'data' folder in the project's root.
    # Make sure this is consistent with your project structure.
    DATA_DIRECTORY = "data" 
    
    if not os.path.exists(DATA_DIRECTORY):
        os.makedirs(DATA_DIRECTORY)
        log.warning(f"Created '{DATA_DIRECTORY}' directory. Please add your financial documents to it and run again.")
        sys.exit(0)

    try:
        ingestion_pipeline = DataIngestion()
        ingestion_pipeline.ingest_from_directory(DATA_DIRECTORY)
        log.info("Data ingestion pipeline completed successfully.")
    except AutoFinQAException as e:
        log.error(e)
        sys.exit(1)