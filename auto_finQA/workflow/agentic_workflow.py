# agentic_workflow.py

import re
import sys
from typing import List, Tuple, TypedDict, Literal, Annotated
from operator import itemgetter

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import Tool
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from retriever.retrieval import RetrievalPipeline
from utils.model_loader import ModelLoader
from logger import GLOBAL_LOGGER as log
from exception.custom_exception import AutoFinQAException
from prompt_library.prompts import PROMPT_REGISTRY, PromptType
from workflow.simple_rag_workflow import format_docs 


# 1. DEFINE A SAFE CALCULATOR TOOL
SAFE_MATH_OPS_RE = re.compile(r"^[ \d\.\+\-\*\/\(\)eE]+$")

def safe_calculator(expression: str) -> str:
    """A secure calculator that evaluates simple arithmetic expressions."""
    clean_expression = expression.replace(",", "")
    log.info(f"Calculator received expression: {expression} (cleaned: {clean_expression})")
    
    if not SAFE_MATH_OPS_RE.fullmatch(clean_expression):
        log.warning(f"Calculator rejected unsafe expression: {expression}")
        return "Error: Input contains invalid characters. Only numbers and basic operators (+, -, *, /) are allowed."
    
    try:
        result = eval(clean_expression, {"__builtins__": None}, {})
        return str(result)
    except ZeroDivisionError:
        return "Error: Division by zero."
    except Exception as e:
        log.error(f"Calculator failed to evaluate: {clean_expression}", exc_info=e)
        return f"Error: Failed to evaluate expression. {str(e)}"

# 2. LOAD MODELS AND TOOLS
try:
    log.info("Initializing Agentic Workflow components...")
    model_loader = ModelLoader()
    llm = model_loader.load_llm()
    retriever_obj = RetrievalPipeline()
    doc_retriever = retriever_obj.get_retriever()
    log.info("Agentic Workflow components initialized successfully.")
except Exception as e:
    log.error("Failed to initialize agent components", exc_info=e)
    sys.exit(1) 

tools = [
    Tool(
        name="search_financial_documents",
        func=doc_retriever.invoke,
        description="""Use this tool to find any specific financial fact, figure, text, or date from the company's uploaded documents.
        This is your *only* way to access the documents.
        Critical Rules:
        1. Be Specific: Your input must be a clear, targeted search query.
        2. Deconstruct Questions: If a user asks for a calculation, find all individual numbers first."""
    ),
    Tool(
        name="calculator",
        func=safe_calculator,
        description="Use this tool for any mathematical calculations. Input must be a simple arithmetic string."
    )
]

# 3. DEFINE THE AGENT STATE
class AgentState(TypedDict):
    input: str
    chat_history: List[BaseMessage]
    retrieved_docs: List
    calculation_result: str
    agent_outcome: dict 
    recursion_depth: int
    grader_status: str

def call_agent(state: AgentState):
    """The main agent node that decides what to do next."""
    log.info(f"Agent Brain called. Recursion depth: {state['recursion_depth']}")
    
    # GRACEFUL EXIT GUARDRAIL
    # If we hit the limit (e.g., 5 loops), FORCE an answer instead of crashing.
    if state['recursion_depth'] > 5:
        log.warning("Agent reached recursion limit. Forcing a final answer.")
        
        # Create a temporary chain just to summarize whatever we have
        fallback_chain = (
            RunnableLambda(lambda x: {
                "context": format_docs(state.get("retrieved_docs", [])), 
                "question": state["input"]
            })
            | ChatPromptTemplate.from_template(
                "You are a helpful financial assistant. You have searched for information but reached a time limit.\n"
                "Based ONLY on the context below, summarize what you found. If the context contains the specific numbers asked for, answer the question.\n\n"
                "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
            )
            | llm
            | StrOutputParser()
        )
        
        try:
            fallback_answer = fallback_chain.invoke(state)
        except Exception:
            fallback_answer = "I'm sorry, I searched multiple times but couldn't verify the exact information. Please try a simpler query."
            
        return {"agent_outcome": {"action": "finish", "args": {"answer": fallback_answer}}}
    
    agent_prompt = ChatPromptTemplate.from_template(PROMPT_REGISTRY[PromptType.FINANCIAL_AGENT].template)
    
    history_str = "\n".join([f"{'Human' if isinstance(m, HumanMessage) else 'AI'}: {m.content}" for m in state['chat_history']])
    
    scratchpad = ""
    if state['retrieved_docs']:
        scratchpad += f"\nI just retrieved these documents:\n{format_docs(state['retrieved_docs'])}"
    if state['calculation_result']:
        scratchpad += f"\nI just performed a calculation, the result was: {state['calculation_result']}"
        
    chain = (
        RunnableLambda(lambda x: {
            "input": x["input"],
            "chat_history": history_str,
            "agent_scratchpad": scratchpad,
            "tools": "\n".join([f"{t.name}: {t.description}" for t in tools]) 
        })
        | agent_prompt
        | llm
        | JsonOutputParser() 
    )
    
    try:
        agent_decision = chain.invoke(state)
        log.info(f"Agent decision: {agent_decision}")
    except Exception as e:
        log.error("Agent LLM call or JSON parsing failed.", exc_info=e)
        return {"agent_outcome": {"action": "finish", "args": {"answer": "I'm sorry, I encountered an error in my reasoning process."}}}
    
    return {
        "agent_outcome": agent_decision,
        "recursion_depth": state['recursion_depth'] + 1
        # Note: We do NOT clear retrieved_docs here anymore, so context persists
    }

def call_retriever(state: AgentState):
    """Calls the retrieval tool."""
    query = state.get("agent_outcome", {}).get("args", {}).get("query")
    if not query:
        return {"retrieved_docs": []}
        
    log.info(f"Retriever Node: Calling tool with query: {query}")
    docs = doc_retriever.invoke(query)
    # New docs overwrite old ones
    return {"retrieved_docs": docs}

def call_calculator(state: AgentState):
    """Calls the safe calculator tool."""
    expression = state.get("agent_outcome", {}).get("args", {}).get("expression")
    if not expression:
        return {"calculation_result": "Error: No expression provided."}

    log.info(f"Calculator Node: Calling tool with expression: {expression}")
    result = safe_calculator(str(expression))
    return {"calculation_result": result}

def call_grader(state: AgentState):
    """Grades the relevance of retrieved documents."""
    if not state["retrieved_docs"]:
        return {"grader_status": "no"}

    log.info("Grader Node: Grading retrieved documents.")
    
    grader_prompt = ChatPromptTemplate.from_template(PROMPT_REGISTRY[PromptType.RELEVANCE_GRADER].template)
    chain = grader_prompt | llm | StrOutputParser()
    
    decision = chain.invoke({
        "context": format_docs(state["retrieved_docs"]),
        "question": state["input"]
    })
    
    log.info(f"Grader Node: Decision: '{decision}'")
    
    # We do not clear Documents here
    # We just set a flag. The documents stay in the state.
    if "yes" in decision.lower():
        return {"grader_status": "yes"} 
    else:
        return {"grader_status": "no"} 

def call_query_rewriter(state: AgentState):
    """Rewrites the query if documents were not relevant."""
    log.info("Query Rewriter Node: Rewriting query.")
    
    history_str = "\n".join([f"{'Human' if isinstance(m, HumanMessage) else 'AI'}: {m.content}" for m in state['chat_history']])
    
    rewriter_prompt = ChatPromptTemplate.from_template(PROMPT_REGISTRY[PromptType.QUERY_REWRITER].template)
    chain = rewriter_prompt | llm | StrOutputParser()
    
    new_query = chain.invoke({
        "chat_history": history_str,
        "question": state["input"],
        "context": format_docs(state["retrieved_docs"])
    })
    
    log.info(f"Query Rewriter Node: New query: '{new_query}'")
    return {"agent_outcome": {"action": "search_financial_documents", "args": {"query": new_query}}}


#Routing Logic

def route_agent_decision(state: AgentState) -> Literal["call_retriever", "call_calculator", "finish"]:
    action = state.get("agent_outcome", {}).get("action")
    if action == "search_financial_documents":
        return "call_retriever"
    elif action == "calculator":
        return "call_calculator"
    else:
        return "finish"

def route_grader_decision(state: AgentState) -> Literal["call_agent", "rewrite_query"]:
    # Check the flag we set in call_grader
    if state.get("grader_status") == "yes":
        log.info("Grader Router: Docs are relevant. Returning to agent brain.")
        return "call_agent"
    else:
        # Guardrail: If we have looped too many times, just give up and let the agent try to answer
        # with what it has. This prevents infinite re-writing.
        if state['recursion_depth'] >= 3:
             log.info("Grader Router: Recursion limit approaching. Returning to agent despite irrelevant grade.")
             return "call_agent"
             
        log.info("Grader Router: Docs are irrelevant. Rewriting query.")
        return "rewrite_query"

log.info("Building agent graph...")
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_agent)
workflow.add_node("call_retriever", call_retriever)
workflow.add_node("call_calculator", call_calculator)
workflow.add_node("grade_relevance", call_grader)
workflow.add_node("rewrite_query", call_query_rewriter)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    route_agent_decision,
    {
        "call_retriever": "call_retriever",
        "call_calculator": "call_calculator",
        "finish": END
    }
)

workflow.add_edge("call_retriever", "grade_relevance")
workflow.add_conditional_edges(
    "grade_relevance",
    route_grader_decision,
    {
        "call_agent": "agent",
        "rewrite_query": "rewrite_query"
    }
)
workflow.add_edge("rewrite_query", "call_retriever") 
workflow.add_edge("call_calculator", "agent")

agent_graph = workflow.compile(checkpointer=MemorySaver())
log.info("Agent graph compiled successfully.")

def invoke_agent_chain(query: str, session_id: str, chat_history: List[Tuple[str, str]], callbacks=None):
    """
    Runs the agent chain with robust error handling and answer extraction.
    """
    try:
        log.info(f"Invoking Agentic RAG chain for session {session_id} with query: '{query}'")
        
        history_messages = []
        for human, ai in chat_history:
            history_messages.append(HumanMessage(content=human))
            history_messages.append(AIMessage(content=ai))

        config = {
            "configurable": {"thread_id": session_id}, 
            "callbacks": callbacks,
            "recursion_limit": 50 
        }

        initial_state = {
            "input": query,
            "chat_history": history_messages,
            "recursion_depth": 0,
            "retrieved_docs": [],
            "calculation_result": "",
            "grader_status": "unknown"
        }
        
        final_state = agent_graph.invoke(initial_state, config=config)
        
        # --- DEBUG LOG: See exactly what the agent output ---
        agent_outcome = final_state.get("agent_outcome", {})
        log.info(f"FINAL AGENT OUTCOME: {agent_outcome}") 
        
        # --- ROBUST EXTRACTION STRATEGY ---
        answer = None
        
        # 1. Check standard path (args -> answer)
        if isinstance(agent_outcome, dict):
            args = agent_outcome.get("args", {})
            if isinstance(args, dict):
                answer = args.get("answer")
            elif isinstance(args, str):
                # Sometimes args is just a string content
                answer = args
            
            # 2. Check flat path (direct 'answer' key)
            if not answer:
                answer = agent_outcome.get("answer")
            
            # 3. Check 'output' key (common LangChain variation)
            if not answer:
                answer = agent_outcome.get("output")

        # 4. Fallback: If the agent finished but we missed the key, dump the whole thing
        if not answer and agent_outcome:
            answer = str(agent_outcome)

        # 5. Final Fallback
        if not answer:
            answer = "I'm sorry, I processed the request but could not extract a final answer from the agent's state."
        
        log.info("Successfully generated answer with Agentic RAG.")
        return answer
    
    except Exception as e:
        log.error("Error invoking agent chain", exc_info=e)
        raise AutoFinQAException("Failed to get a response from the agent.", e)