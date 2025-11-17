# data_ingestion.py

import os
import sys
import json
import pandas as pd
import pdfplumber
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any

from docx import Document as DocxDocument
from dotenv import load_dotenv
from pymongo import MongoClient

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_mongodb import MongoDBAtlasVectorSearch

from utils.model_loader import ModelLoader
from logger import GLOBAL_LOGGER as log
from exception.custom_exception import AutoFinQAException
from utils.config_loader import load_config


SUPPORTED_EXTENSIONS = {
    '.pdf', '.txt', '.docx', '.md', 
    '.csv', '.json', '.xls', '.xlsx'
}

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
                
                log.info(f"Loading document: {file_path.name}")
                
                if extension == '.pdf':
                    docs.extend(DocumentLoader._load_pdf(file_path))
                elif extension == '.docx':
                    docs.extend(DocumentLoader._load_docx(file_path))
                elif extension in ['.txt', '.md']:
                    docs.extend(DocumentLoader._load_text(file_path))
                elif extension == '.csv':
                    docs.extend(DocumentLoader._load_csv(file_path))
                elif extension in ['.xls', '.xlsx']:
                    docs.extend(DocumentLoader._load_excel(file_path))
                elif extension == '.json':
                    docs.extend(DocumentLoader._load_json(file_path))
                    
            except Exception as e:
                raise AutoFinQAException(f"Failed to load document: {file_path}", e)
        return docs
    
    # PDF loader using pdfplumber (for tables) and PyMuPDF (for text)
    @staticmethod
    def _load_pdf(file_path: Path) -> List[Document]:
        docs = []
        file_name = file_path.name
        
        # 1. Extract tables with pdfplumber
        log.info(f"Extracting tables from {file_name} with pdfplumber...")
        table_docs = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    for table_id, table in enumerate(tables, 1):
                        # Convert table to a list of dicts for clean content
                        if not table: continue
                        headers = table[0]
                        for row_num, row_data in enumerate(table[1:], 1):
                            row_dict = {headers[i]: cell for i, cell in enumerate(row_data) if i < len(headers)}
                            content = json.dumps(row_dict)
                            metadata = {
                                "source": file_name,
                                "page_number": page_num,
                                "doc_type": "tabular",
                                "table_id": table_id,
                                "row_number": row_num
                            }
                            table_docs.append(Document(page_content=content, metadata=metadata))
            log.info(f"Extracted {len(table_docs)} table rows from {file_name}.")
            docs.extend(table_docs)
        except Exception as e:
            log.warning(f"pdfplumber failed to extract tables from {file_name}", error=str(e))

        # 2. Extract text with PyMuPDF (fitz)
        log.info(f"Extracting text from {file_name} with PyMuPDF...")
        try:
            with fitz.open(file_path) as doc:
                for page_num, page in enumerate(doc, 1):
                    # We will extract text and *not* table text to avoid duplication
                    # A simple way is to just extract blocks
                    text_blocks = page.get_text("blocks", sort=True)
                    page_text_content = []
                    
                    for block in text_blocks:
                        block_text = block[4] # The text content is at index 4
                        # Simple heuristic: if a block has many newlines or spaced-out text,
                        # it might be part of a table pdfplumber missed.
                        # For now, we'll just check if it's too short to be a paragraph.
                        if len(block_text.split()) > 5: # Only keep blocks with > 5 words
                            page_text_content.append(block_text.strip())
                    
                    full_page_text = "\n\n".join(page_text_content)
                    
                    if full_page_text:
                        metadata = {
                            "source": file_name,
                            "page_number": page_num,
                            "doc_type": "text"
                        }
                        docs.append(Document(page_content=full_page_text, metadata=metadata))
            log.info(f"Extracted {len(doc)} text pages from {file_name}.")
        except Exception as e:
            log.warning(f"PyMuPDF failed to extract text from {file_name}", error=str(e))
            
        return docs

    @staticmethod
    def _load_docx(file_path: Path) -> List[Document]:
        doc = DocxDocument(file_path)
        content = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        # Also extract tables from docx
        table_docs = []
        for table_id, table in enumerate(doc.tables, 1):
            for row_num, row in enumerate(table.rows[1:], 1): # Assuming first row is header
                try:
                    headers = [cell.text for cell in table.rows[0].cells]
                    row_data = [cell.text for cell in row.cells]
                    row_dict = {headers[i]: cell for i, cell in enumerate(row_data) if i < len(headers)}
                    content = json.dumps(row_dict)
                    metadata = {
                        "source": file_path.name,
                        "doc_type": "tabular",
                        "table_id": f"docx_table_{table_id}",
                        "row_number": row_num
                    }
                    table_docs.append(Document(page_content=content, metadata=metadata))
                except Exception:
                    continue # Skip malformed rows
        
        text_doc = Document(page_content=content, metadata={"source": file_path.name, "doc_type": "text"})
        return [text_doc] + table_docs

    @staticmethod
    def _load_text(file_path: Path) -> List[Document]:
        content = file_path.read_text(encoding="utf-8")
        return [Document(page_content=content, metadata={"source": file_path.name, "doc_type": "text"})]

    # Load CSV row by row
    @staticmethod
    def _load_csv(file_path: Path) -> List[Document]:
        df = pd.read_csv(file_path)
        docs = []
        for index, row in df.iterrows():
            content_dict = row.to_dict()
            content_str = json.dumps(content_dict)
            metadata = {
                "source": file_path.name,
                "doc_type": "tabular",
                "row_number": index + 1
            }
            docs.append(Document(page_content=content_str, metadata=metadata))
        log.info(f"Loaded {len(docs)} rows from CSV: {file_path.name}")
        return docs
        
    # Load Excel row by row
    @staticmethod
    def _load_excel(file_path: Path) -> List[Document]:
        df = pd.read_excel(file_path)
        docs = []
        for index, row in df.iterrows():
            content_dict = row.to_dict()
            # Convert numpy types to native Python types for JSON serialization
            content_dict_serializable = {k: (str(v) if pd.isna(v) else v) for k, v in content_dict.items()}
            content_str = json.dumps(content_dict_serializable, default=str)
            metadata = {
                "source": file_path.name,
                "doc_type": "tabular",
                "row_number": index + 1
            }
            docs.append(Document(page_content=content_str, metadata=metadata))
        log.info(f"Loaded {len(docs)} rows from Excel: {file_path.name}")
        return docs

    # Load JSON object by object (if list)
    @staticmethod
    def _load_json(file_path: Path) -> List[Document]:
        docs = []
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, list):
            # If it's a list of records, treat each item as a doc
            for i, record in enumerate(data):
                content_str = json.dumps(record, indent=2)
                metadata = {
                    "source": file_path.name,
                    "doc_type": "tabular", # Treat as structured data
                    "row_number": i + 1
                }
                docs.append(Document(page_content=content_str, metadata=metadata))
            log.info(f"Loaded {len(docs)} objects from JSON list: {file_path.name}")
        elif isinstance(data, dict):
            # If it's a single large object, treat as one text doc
            content_str = json.dumps(data, indent=2)
            docs.append(Document(page_content=content_str, metadata={"source": file_path.name, "doc_type": "text"}))
            log.info(f"Loaded 1 object from JSON dict: {file_path.name}")
        return docs


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
            raise AutoFinQAException(f"Missing required key in config.yaml under 'mongodb': {e}", e)

    def _split_documents(self, docs: List[Document]) -> List[Document]:
        # Only split text docs, pass tabular docs through
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        
        text_docs = []
        tabular_docs = []
        
        for doc in docs:
            if doc.metadata.get("doc_type") == "tabular":
                tabular_docs.append(doc)
            else:
                text_docs.append(doc)
                
        if text_docs:
            chunks = text_splitter.split_documents(text_docs)
            log.info(f"Split {len(text_docs)} text documents into {len(chunks)} chunks.")
        else:
            chunks = []
            
        final_docs = chunks + tabular_docs
        log.info(f"Total documents to ingest: {len(final_docs)} ({len(chunks)} text chunks + {len(tabular_docs)} tabular docs)")
        return final_docs
    
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
                collection=collection,
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
            
            log.info(f"Ingesting {len(chunks)} total document chunks into MongoDB...")
            MongoDBAtlasVectorSearch.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                collection=collection,
                index_name=self.index_name
            )
            log.info(f"Successfully added {len(chunks)} document chunks to MongoDB.")

        except Exception as e:
            raise AutoFinQAException("Data ingestion pipeline failed.", e)

if __name__ == '__main__':
    """
    This block allows the script to be run directly from the command line
    to ingest documents from a specified directory.
    """
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