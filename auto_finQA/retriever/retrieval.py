# retriever/retrieval.py

import os
import sys
import json
from typing import Optional, Literal
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
    """
    Manages the retrieval of documents from MongoDB Atlas.
    Enhanced to support multiple retrieval modes for evaluation purposes:
    - 'simple': Standard Vector Search (Baseline)
    - 'mmr': Maximal Marginal Relevance (Diversity)
    - 'rerank': Cross-Encoder Reranking (High Precision)
    """
    def __init__(self):
        load_dotenv()
        self.config = load_config()
        self.model_loader = ModelLoader()
        self.embeddings = self.model_loader.load_embeddings()
        
        # Holds the raw collection for direct table queries
        self.collection = None 
        self.vector_store = self._connect_to_vector_store()
        log.info("RetrievalPipeline initialized.")

    def _connect_to_vector_store(self):
        """
        Connects to MongoDB and returns the VectorStore object.
        Also initializes self.collection for direct access.
        """
        try:
            mongo_uri = os.getenv("MONGO_URI")
            if not mongo_uri:
                raise AutoFinQAException("Missing environment variable: MONGO_URI", sys)
            
            db_config = self.config['mongodb']
            client = MongoClient(mongo_uri)
            self.collection = client[db_config['db_name']][db_config['collection_name']]
            
            vector_store = MongoDBAtlasVectorSearch(
                collection=self.collection,
                embedding=self.embeddings,
                index_name=db_config['index_name']
            )
            log.info(f"Successfully connected to MongoDB Atlas collection: {db_config['collection_name']}")
            return vector_store
        except Exception as e:
            raise AutoFinQAException("Failed to connect to MongoDB Atlas Vector Store.", e)

    def get_retriever(self, mode: Literal["simple", "mmr", "rerank"] = "rerank"):
        """
        Constructs and returns the retriever based on the selected mode.
        
        Args:
            mode (str): The retrieval strategy to use.
                        'simple' -> Basic similarity search (k=top_k)
                        'mmr'    -> MMR search (k=top_k, fetch_k=fetch_k)
                        'rerank' -> MMR + Cross-Encoder Reranking
        """
        try:
            retriever_config = self.config.get('retriever', {})
            top_k = retriever_config.get('top_k', 5)
            fetch_k = retriever_config.get('fetch_k', 20)
            lambda_mult = retriever_config.get('lambda_mult', 0.7)

            log.info(f"Building retriever with mode: '{mode}'")

            if mode == "simple":
                # Baseline: Pure Semantic Search
                # Good for proving why simple vector search fails on similar-looking financial rows
                return self.vector_store.as_retriever(
                    search_type="similarity",
                    search_kwargs={'k': top_k}
                )

            elif mode == "mmr":
                # MMR: Diversity aware
                # Good for proving reduction in redundancy
                return self.vector_store.as_retriever(
                    search_type="mmr",
                    search_kwargs={'k': top_k, 'fetch_k': fetch_k, 'lambda_mult': lambda_mult}
                )

            elif mode == "rerank":
                # Rerank: High Precision (MMR -> Reranker)
                # The best performing mode for final Agent usage
                
                # 1. Get broad set using MMR
                base_retriever = self.vector_store.as_retriever(
                    search_type="mmr",
                    search_kwargs={'k': top_k * 2, 'fetch_k': fetch_k, 'lambda_mult': lambda_mult}
                )
                
                # 2. Rerank top results
                cross_encoder_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
                compressor = CrossEncoderReranker(model=cross_encoder_model, top_n=top_k)
                
                compression_retriever = ContextualCompressionRetriever(
                    base_compressor=compressor,
                    base_retriever=base_retriever
                )
                return compression_retriever
            
            else:
                raise ValueError(f"Unknown retrieval mode: {mode}")

        except Exception as e:
            raise AutoFinQAException(f"Failed to build the retriever in mode '{mode}'.", e)

    def fetch_table_by_id(self, table_id: str) -> str:
        """
        Fetches all rows associated with a specific table_id from MongoDB.
        Used by the Agent when it needs full table context.
        """
        if not self.collection:
            log.error("Collection not initialized.")
            return "Error: Database not connected."
            
        try:
            log.info(f"Fetching full table content for table_id: {table_id}")
            
            # Query for all chunks with this table_id
            cursor = self.collection.find({"metadata.table_id": table_id})
            
            # Sort by row number to reconstruct the table in order
            rows = sorted(list(cursor), key=lambda x: x['metadata'].get('row_number', 0))
            
            if not rows:
                return f"No table found with ID: {table_id}"

            # Reconstruct the table string
            table_content = []
            for doc in rows:
                # The page_content is already a JSON string of the row
                # Check 'text' field (common in some ingestions) or 'page_content'
                content = doc.get('text') or doc.get('page_content', '')
                table_content.append(content)
                
            joined_table = "\n".join(table_content)
            log.info(f"Successfully reconstructed table {table_id} with {len(rows)} rows.")
            return f"Full Table ({table_id}):\n{joined_table}"

        except Exception as e:
            log.error(f"Failed to fetch table {table_id}", exc_info=e)
            return f"Error retrieving table: {str(e)}"

if __name__ == '__main__':
    # Test Block
    try:
        print("--- Testing Retrieval Pipeline Modes ---")
        pipeline = RetrievalPipeline()
        
        query = "What is the total revenue?"
        
        # Test 1: Baseline
        print("\n1. Testing 'simple' mode...")
        r_simple = pipeline.get_retriever(mode="simple")
        res_simple = r_simple.invoke(query)
        print(f"   Retrieved {len(res_simple)} docs.")

        # Test 2: Rerank (Default)
        print("\n2. Testing 'rerank' mode...")
        r_rerank = pipeline.get_retriever(mode="rerank")
        res_rerank = r_rerank.invoke(query)
        print(f"   Retrieved {len(res_rerank)} docs.")
        
        log.info("Retrieval pipeline test complete.")
    except Exception as e:
        print(f"Test failed: {e}")