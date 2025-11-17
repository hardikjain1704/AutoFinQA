# retrieval.py

import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient

from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain.retrievers.document_compressors import CrossEncoderReranker

from utils.config_loader import load_config
from utils.model_loader import ModelLoader
from logger import GLOBAL_LOGGER as log
from exception.custom_exception import AutoFinQAException

class RetrievalPipeline:
    def __init__(self):
        load_dotenv()
        self.config = load_config()
        self.model_loader = ModelLoader()
        self.embeddings = self.model_loader.load_embeddings()
        self.vector_store = self._connect_to_vector_store()
        log.info("RetrievalPipeline initialized.")

    def _connect_to_vector_store(self):
        try:
            mongo_uri = os.getenv("MONGO_URI")
            if not mongo_uri:
                raise AutoFinQAException("Missing environment variable: MONGO_URI", sys)
            
            db_config = self.config['mongodb']
            client = MongoClient(mongo_uri)
            collection = client[db_config['db_name']][db_config['collection_name']]
            
            vector_store = MongoDBAtlasVectorSearch(
                collection=collection,
                embedding=self.embeddings,
                index_name=db_config['index_name']
            )
            log.info(f"Successfully connected to MongoDB Atlas collection: {db_config['collection_name']}")
            return vector_store
        except Exception as e:
            raise AutoFinQAException("Failed to connect to MongoDB Atlas Vector Store.", e)

    def get_retriever(self):
        try:
            retriever_config = self.config.get('retriever', {})
            top_k = retriever_config.get('top_k', 5)
            fetch_k = retriever_config.get('fetch_k', 20)
            lambda_mult = retriever_config.get('lambda_mult', 0.7)

            base_retriever = self.vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={'k': top_k, 'fetch_k': fetch_k, 'lambda_mult': lambda_mult}
            )
            log.info(f"Base MMR retriever created with k={top_k}.")
            
            cross_encoder_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
            compressor = CrossEncoderReranker(model=cross_encoder_model, top_n=3)
            
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=base_retriever
            )
            log.info("ContextualCompressionRetriever with Reranker created successfully.")
            return compression_retriever
        except Exception as e:
            raise AutoFinQAException("Failed to build the retriever.", e)


if __name__ == '__main__':
    try:
        log.info("--- STARTING RETRIEVAL PIPELINE TEST ---")
        retrieval_pipeline = RetrievalPipeline()
        retriever = retrieval_pipeline.get_retriever()
        
        query = "What was the company's outlook for Q4?"
        
        print(f"\n[INFO] Executing test query: '{query}'")
        
        results = retriever.invoke(query)
        
        print("\n--- RETRIEVED DOCUMENTS ---")
        if not results:
            print("[WARNING] No documents were retrieved for this query.")
        else:
            for i, doc in enumerate(results):
                print(f"\n--- Document {i+1} ---")
                print(f"  Source: {doc.metadata.get('source', 'N/A')}")
                print(f"  Page: {doc.metadata.get('page', 'N/A')}")
                # --- ADDED METADATA FOR TABLES ---
                if 'table_id' in doc.metadata:
                    print(f"  Table ID: {doc.metadata.get('table_id')}")
                if 'row_number' in doc.metadata:
                    print(f"  Row: {doc.metadata.get('row_number')}")
                print(f"  Content: {doc.page_content}\n")
        
        log.info("--- RETRIEVAL PIPELINE TEST COMPLETED ---")

    except AutoFinQAException as e:
        log.error("An error occurred during the retrieval test.", exc_info=e)