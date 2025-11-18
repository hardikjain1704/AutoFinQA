# simple_rag_workflow.py

import sys
from typing import List, Tuple
from operator import itemgetter

from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

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
    --- UPDATED: Now includes rich metadata (Table ID, Row Number) ---
    """
    if not docs:
        return "No relevant documents were found to answer the question."

    formatted_chunks = []
    for d in docs:
        meta = d.metadata or {}
        source = meta.get('source', 'N/A')
        
        # Build a detailed citation string dynamically
        citation_parts = [f"Source: {source}"]
        
        # Add specific location markers if they exist
        if 'page_number' in meta:
            citation_parts.append(f"Page: {meta.get('page_number')}")
        if 'table_id' in meta:
            citation_parts.append(f"Table: {meta.get('table_id')}")
        if 'row_number' in meta:
            citation_parts.append(f"Row: {meta.get('row_number')}")
        
        citation_str = ", ".join(citation_parts)
        
        formatted = (
            f"Citation: [{citation_str}]\n"
            f"Content: {d.page_content.strip()}"
        )
        formatted_chunks.append(formatted)

    return "\n\n---\n\n".join(formatted_chunks)

def build_chain():
    """
    Builds the RAG pipeline chain once.
    --- UPDATED: Supports Conversational Memory ---
    """
    retriever = retriever_obj.get_retriever()
    llm = model_loader.load_llm()
    
    # 1. Retrieve the base system prompt
    system_prompt_text = PROMPT_REGISTRY[PromptType.FINANCIAL_QA].template
    
    # 2. Create a ChatPromptTemplate that includes history
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_text),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])

    # 3. Build the chain using itemgetter for multiple inputs
    chain = (
        {
            "context": itemgetter("question") | retriever | format_docs,
            "question": itemgetter("question"),
            "chat_history": itemgetter("chat_history")
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain

# Build the chain once when the module is loaded.
rag_chain = build_chain()

def invoke_chain(query: str, chat_history: List[Tuple[str, str]]):
    """
    Runs the pre-built chain with a user query and history.
    --- UPDATED: Now accepts chat_history to prevent main.py crash ---
    """
    try:
        log.info(f"Invoking simple RAG chain with query: '{query}'")
        
        # Convert simple tuple history to BaseMessage objects
        # This is necessary for the MessagesPlaceholder in the prompt
        history_messages = []
        for human, ai in chat_history:
            history_messages.append(HumanMessage(content=human))
            history_messages.append(AIMessage(content=ai))
        
        # Invoke the chain with both inputs
        response = rag_chain.invoke({
            "question": query,
            "chat_history": history_messages
        })
        
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
        
        user_query = "What is the total revenue?"
        # Mock empty history for testing
        test_history = []
        
        print(f"\n[INFO] Executing test query: '{user_query}'")
        print("-" * 30)

        response = invoke_chain(user_query, test_history)
        
        print("-" * 30)
        print("\n--- FINAL ANSWER ---")
        print(response)
        
        log.info("--- SIMPLE RAG WORKFLOW TEST COMPLETED ---")

    except AutoFinQAException as e:
        log.error("An error occurred during the simple RAG workflow test.", exc_info=e)