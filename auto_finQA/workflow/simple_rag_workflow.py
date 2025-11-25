# workflow/simple_rag_workflow.py

import sys
from typing import List, Tuple, Optional
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

# Initialize components globally for application performance
try:
    retriever_obj = RetrievalPipeline()
    model_loader = ModelLoader()
except Exception as e:
    log.error("Failed to initialize Simple RAG components", exc_info=e)
    sys.exit(1)

def format_docs(docs) -> str:
    """
    Formats retrieved financial documents for the prompt with explicit metadata citations.
    Includes Table ID and Row Number for precise grounding.
    """
    if not docs:
        return "No relevant documents were found."

    formatted_chunks = []
    for d in docs:
        meta = d.metadata or {}
        source = meta.get('source', 'Unknown Source')
        
        # Build detailed citation
        citation_parts = [f"Source: {source}"]
        if 'page_number' in meta:
            citation_parts.append(f"Page: {meta.get('page_number')}")
        if 'table_id' in meta:
            citation_parts.append(f"Table ID: {meta.get('table_id')}")
        if 'row_number' in meta:
            citation_parts.append(f"Row: {meta.get('row_number')}")
        
        citation_str = ", ".join(citation_parts)
        
        formatted = (
            f"--- Document Snippet ---\n"
            f"Citation: [{citation_str}]\n"
            f"Content: {d.page_content.strip()}"
        )
        formatted_chunks.append(formatted)

    return "\n\n".join(formatted_chunks)

def build_chain(retrieval_mode: str = "rerank"):
    """
    Builds the Simple RAG pipeline chain.
    
    Args:
        retrieval_mode: The mode to use ('simple', 'mmr', 'rerank').
                        Defaults to 'rerank' for best performance in the main app.
    """
    # Get retriever dynamically based on the requested mode
    retriever = retriever_obj.get_retriever(mode=retrieval_mode)
    llm = model_loader.load_llm(mode="smart")
    
    # Retrieve the base system prompt
    system_prompt_text = PROMPT_REGISTRY[PromptType.FINANCIAL_QA].template
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_text),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])

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

# Initialize default chain for the API (fastest response)
rag_chain = build_chain(retrieval_mode="rerank")

def invoke_chain(query: str, chat_history: List[Tuple[str, str]], retrieval_mode: Optional[str] = None):
    """
    Runs the chain with user query and history.
    
    Args:
        query: User question.
        chat_history: List of (Human, AI) tuples.
        retrieval_mode: Optional override (e.g., 'mmr') for evaluation purposes.
                        If None, uses the pre-built cached chain.
    """
    try:
        log.info(f"Invoking Simple RAG chain with query: '{query}'")
        
        # If a specific mode is requested (for eval), rebuild the chain temporarily
        # Otherwise use the global cached chain
        chain_to_use = rag_chain
        if retrieval_mode:
             log.info(f"Rebuilding chain for specific mode: {retrieval_mode}")
             chain_to_use = build_chain(retrieval_mode)
        
        history_messages = []
        for human, ai in chat_history:
            history_messages.append(HumanMessage(content=human))
            history_messages.append(AIMessage(content=ai))
        
        response = chain_to_use.invoke({
            "question": query,
            "chat_history": history_messages
        })
        
        return response
    except Exception as e:
        log.error("Error invoking simple RAG chain", exc_info=e)
        raise AutoFinQAException("Failed to get a response from the Simple RAG chain.", e)

if __name__ == '__main__':
    # Test block
    try:
        log.info("--- TEST START ---")
        user_query = "What is the revenue?"
        test_history = []
        # Example: Testing specifically with 'mmr' mode
        response = invoke_chain(user_query, test_history, retrieval_mode="mmr")
        print(response)
        log.info("--- TEST END ---")
    except Exception as e:
        print(e)