# auto_finQA/workflow/simple_rag_workflow.py

import sys
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from prompt_library.prompts import PROMPT_REGISTRY, PromptType
from retriever.retrieval import RetrievalPipeline
from utils.model_loader import ModelLoader
from logger import GLOBAL_LOGGER as log
from exception.custom_exception import AutoFinQAException

# These are initialized once when the module is imported, which is efficient.
retriever_obj = RetrievalPipeline()
model_loader = ModelLoader()

def format_docs(docs) -> str:
    """
    Formats retrieved financial documents for the prompt.
    """
    if not docs:
        return "No relevant documents were found to answer the question."

    formatted_chunks = []
    for d in docs:
        meta = d.metadata or {}
        # Use metadata relevant to financial documents
        formatted = (
            f"Source: {meta.get('source', 'N/A')}\n"
            f"Page: {meta.get('page', 'N/A')}\n"
            f"Content: {d.page_content.strip()}"
        )
        formatted_chunks.append(formatted)

    return "\n\n---\n\n".join(formatted_chunks)

def build_chain():
    """
    Builds the RAG pipeline chain once.
    This is more efficient than rebuilding it on every request.
    """
    retriever = retriever_obj.get_retriever()
    llm = model_loader.load_llm()
    prompt = ChatPromptTemplate.from_template(
        PROMPT_REGISTRY[PromptType.FINANCIAL_QA].template
    )

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain

# Build the chain once when the module is loaded.
rag_chain = build_chain()

def invoke_chain(query: str):
    """
    Runs the pre-built chain with a user query.
    """
    try:
        log.info(f"Invoking simple RAG chain with query: '{query}'")
        response = rag_chain.invoke(query)
        return response
    except Exception as e:
        log.error("Error invoking simple RAG chain", exc_info=e)
        raise AutoFinQAException("Failed to get a response from the RAG chain.", e)


if __name__ == '__main__':
    """
    Standalone runner for testing the simple RAG workflow.
    """
    try:
        log.info("--- STARTING SIMPLE RAG WORKFLOW TEST ---")
        
        # --- DEFINE YOUR TEST QUERY HERE ---
        # Make sure this question is relevant to a document you have ingested.
        user_query = "What is 2+14/3?"
        
        print(f"\n[INFO] Executing test query: '{user_query}'")
        print("-" * 30)

        response = invoke_chain(user_query)
        
        print("-" * 30)
        print("\n--- FINAL ANSWER ---")
        print(response)
        
        log.info("--- SIMPLE RAG WORKFLOW TEST COMPLETED ---")

    except AutoFinQAException as e:
        log.error("An error occurred during the simple RAG workflow test.", exc_info=e)