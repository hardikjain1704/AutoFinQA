# workflow/agentic_workflow.py

import re
import sys
import math
import json
from typing import List, Tuple, TypedDict, Literal, Annotated, Any
from operator import itemgetter, add

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
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

# Helper function for robust JSON parsing
def extract_json_from_response(response_text: str) -> dict:
    """
    Extracts JSON from a string that might contain conversational text.
    Fixes the issue where Llama-3 chatters before giving the JSON.
    """
    try:
        # Try cleaning code block markers
        cleaned_text = response_text.strip()
        if "```json" in cleaned_text:
            cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned_text:
            cleaned_text = cleaned_text.split("```")[0].strip()

        # Attempt direct parsing
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        # Fallback: Regex search for the FIRST outer brace pair
        # This logic intentionally ignores any text or second JSON block after the first one.
        # This forces sequential execution if the LLM tries to output multiple actions.
        match = re.search(r"\{[\s\S]*?\}", response_text)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        log.warning(f"Failed to parse JSON from response: {response_text}")
        # Return a fallback finish action to prevent system crash
        return {
            "thought_process": "Error parsing JSON response.",
            "action": "finish", 
            "args": {"answer": f"I generated an answer but it was not formatted correctly. Raw response: {response_text}"}
        }

# Safe Calculator Tool
SAFE_MATH_OPS_RE = re.compile(r"^[ \d\.\+\-\*\/\(\)eE,]+$")

def safe_calculator(expression: str) -> str:
    """
    A secure calculator that evaluates arithmetic expressions.
    Supports basic math plus log, exp, sqrt.
    """
    # Clean expression (remove commas for large numbers like 1,000)
    clean_expression = expression.replace(",", "").strip()
    
    # Auto-correct "log(a b)" to "log(a, b)" for imperfect LLMs
    clean_expression = re.sub(r'log\(\s*(\d+)\s+(\d+)\s*\)', r'log(\1, \2)', clean_expression)
    
    log.info(f"Calculator received expression: {expression} (cleaned: {clean_expression})")
    
    allowed_names = {
        "math": math,
        "log": math.log,
        "exp": math.exp,
        "sqrt": math.sqrt,
        "abs": abs,
        "round": round
    }
    
    try:
        # Evaluate in a restricted scope
        result = eval(clean_expression, {"__builtins__": None}, allowed_names)
        log.info(f"Calculation result: {result}")
        return str(result)
    except ZeroDivisionError:
        return "Error: Division by zero."
    except Exception as e:
        log.error(f"Calculator failed to evaluate: {clean_expression}", exc_info=e)
        return f"Error: Failed to evaluate expression. {str(e)}"

# Initialization using Hybrid Model Strategy
try:
    log.info("Initializing Agentic Workflow components...")
    model_loader = ModelLoader()
    
    # Load TWO models to optimize costs/limits
    llm_smart = model_loader.load_llm(mode="smart")
    llm_fast = model_loader.load_llm(mode="fast")
    
    retriever_obj = RetrievalPipeline()
    
    # Default to 'rerank' mode
    doc_retriever = retriever_obj.get_retriever(mode="rerank")
    log.info("Agentic Workflow components initialized successfully.")
except Exception as e:
    log.error("Failed to initialize agent components", exc_info=e)
    sys.exit(1) 

# Wrapper for the Table Tool
def fetch_table_tool(table_id: str) -> str:
    return retriever_obj.fetch_table_by_id(table_id)

tools = [
    Tool(
        name="search_financial_documents",
        func=doc_retriever.invoke,
        description="Use this tool to find specific financial facts, figures, or text segments. Input should be a specific query."
    ),
    Tool(
        name="get_whole_table",
        func=fetch_table_tool,
        description="Use this tool ONLY when you have a 'table_id' from a previous search and need the FULL table content to perform aggregation (sum, avg) or trend analysis."
    ),
    Tool(
        name="calculator",
        func=safe_calculator,
        description="Use this tool for any mathematical calculations. Input must be a valid python arithmetic expression (e.g., '200 + 500' or 'math.log(10)')."
    )
]

class AgentState(TypedDict):
    input: str
    chat_history: List[BaseMessage] # Long-term history
    
    # Short-term memory for the current reasoning loop.
    # This list accumulates tool outputs (like "Calc result: 3") so the agent doesn't forget them.
    # The 'add' operator ensures new messages are appended, not overwritten.
    scratchpad_messages: Annotated[List[BaseMessage], add]
    
    retrieved_docs: List
    agent_outcome: dict 
    recursion_depth: int
    grader_loop_count: int
    grader_status: str
    router_decision: str 

# Node Functions

def call_router(state: AgentState):
    """
    Decides if the input is 'general_chat' or 'financial_query'.
    USES FAST MODEL (8B)
    """
    log.info("Router Node: Analyzing user intent...")
    prompt = ChatPromptTemplate.from_template(PROMPT_REGISTRY[PromptType.INTENT_ROUTER].template)
    
    # Use llm_fast to save tokens
    chain = prompt | llm_fast | StrOutputParser()
    
    decision = chain.invoke({"input": state["input"]})
    clean_decision = decision.strip().lower().replace('"', '')
    
    log.info(f"Router Decision: {clean_decision}")
    return {"router_decision": clean_decision}

def call_general_chat(state: AgentState):
    """
    Handles chit-chat without tools.
    USES FAST MODEL (8B)
    """
    log.info("General Chat Node: Generating response.")
    prompt = ChatPromptTemplate.from_template(PROMPT_REGISTRY[PromptType.GENERAL_CHAT].template)
    
    # Use llm_fast for simple chat
    chain = prompt | llm_fast | StrOutputParser()
    
    response = chain.invoke({"input": state["input"]})
    return {"agent_outcome": {"action": "finish", "args": {"answer": response}}}

def call_agent(state: AgentState):
    """
    The main financial agent node.
    USES SMART MODEL (70B) for high reasoning capability.
    """
    depth = state['recursion_depth']
    log.info(f"Agent Brain called. Recursion depth: {depth}")
    
    # Loop Prevention Guardrail
    force_answer_hint = ""
    # If we have plenty of scratchpad info (calcs/docs), force an answer
    if depth >= 4 and (state.get('scratchpad_messages') or state.get('retrieved_docs')):
        log.warning("Loop detected. Injecting instruction to stop searching.")
        force_answer_hint = "\n[SYSTEM INSTRUCTION]: You have gathered sufficient information. DO NOT USE TOOLS AGAIN. Synthesize the answer now."
    
    if depth > 10:
        return {"agent_outcome": {"action": "finish", "args": {"answer": "I reached the search limit. Please try a more specific query."}}}
    
    agent_prompt = ChatPromptTemplate.from_template(PROMPT_REGISTRY[PromptType.FINANCIAL_AGENT].template)
    
    # Format History
    history_str = "\n".join([f"{'Human' if isinstance(m, HumanMessage) else ('AI' if isinstance(m, AIMessage) else 'System')}: {m.content}" for m in state['chat_history']])
    
    # Format Scratchpad
    # Combine Retrieved Docs + Calculation Results into one context block
    scratchpad_content = ""
    if state['retrieved_docs']:
        scratchpad_content += f"\n[Observation] Retrieved Documents:\n{format_docs(state['retrieved_docs'])}"
    
    # Add messages from the scratchpad (Calculator results, previous thoughts)
    if state.get("scratchpad_messages"):
        for m in state["scratchpad_messages"]:
            scratchpad_content += f"\n[Observation] {m.content}"

    scratchpad_content += force_answer_hint

    chain = (
        RunnableLambda(lambda x: {
            "input": x["input"],
            "chat_history": history_str,
            "agent_scratchpad": scratchpad_content,
            "tools": "\n".join([f"{t.name}: {t.description}" for t in tools]) 
        })
        | agent_prompt
        | llm_smart  # Use SMART model for reasoning
        | StrOutputParser()
    )
    
    try:
        raw_response = chain.invoke(state)
        agent_decision = extract_json_from_response(raw_response)
        log.info(f"Agent Action: {agent_decision.get('action')}")
        
        # Save the Agent's Thought to the scratchpad so it remembers its plan
        thought_msg = AIMessage(content=f"Thought: {agent_decision.get('thought_process')}")
        
        return {
            "agent_outcome": agent_decision,
            "recursion_depth": depth + 1,
            "grader_loop_count": 0,
            "scratchpad_messages": [thought_msg] # Add thought to scratchpad
        }
    except Exception as e:
        log.error("Agent LLM call or JSON parsing failed.", exc_info=e)
        return {"agent_outcome": {"action": "finish", "args": {"answer": "I encountered an error processing the request."}}}

def call_retriever(state: AgentState):
    """Calls the retrieval tool."""
    query = state.get("agent_outcome", {}).get("args", {}).get("query")
    log.info(f"Retriever Node: Searching for: {query}")
    docs = doc_retriever.invoke(query)
    return {"retrieved_docs": docs}

def call_table_tool(state: AgentState):
    """Calls the table fetching tool."""
    table_id = state.get("agent_outcome", {}).get("args", {}).get("table_id")
    log.info(f"Table Tool: Fetching table {table_id}")
    content = retriever_obj.fetch_table_by_id(table_id)
    from langchain_core.documents import Document
    
    # We return a new doc list. Graph ensures this replaces the old list or we can append logic here.
    # For simplicity, we just pass it.
    doc = Document(page_content=content, metadata={"source": "Database", "table_id": table_id})
    current_docs = state.get("retrieved_docs", [])
    return {"retrieved_docs": current_docs + [doc]}

def call_calculator(state: AgentState):
    """Calls the calculator and appends result to scratchpad."""
    args = state.get("agent_outcome", {}).get("args", {})
    expression = args.get("expression") or args.get("query")
    
    result = safe_calculator(str(expression))
    
    # Create a ToolMessage to persist in scratchpad
    result_msg = ToolMessage(
        tool_call_id="calc", # ID is placeholder
        content=f"Calculation result for '{expression}': {result}"
    )
    
    # Return to graph - 'add' reducer will append this to the list
    return {"scratchpad_messages": [result_msg]}

def call_grader(state: AgentState):
    """Grades relevance using FAST model."""
    if not state["retrieved_docs"]:
        return {"grader_status": "no"}

    log.info("Grader Node: Grading retrieved documents.")
    grader_prompt = ChatPromptTemplate.from_template(PROMPT_REGISTRY[PromptType.RELEVANCE_GRADER].template)
    chain = grader_prompt | llm_fast | StrOutputParser()
    
    decision = chain.invoke({
        "context": format_docs(state["retrieved_docs"][-3:]), 
        "question": state["input"]
    })
    log.info(f"Grader Node: Decision: '{decision}'")
    return {"grader_status": "yes" if "yes" in decision.lower() else "no"} 

def call_query_rewriter(state: AgentState):
    """Rewrites query using FAST model."""
    log.info("Query Rewriter Node: Rewriting query.")
    history_str = "\n".join([f"{'Human' if isinstance(m, HumanMessage) else 'AI'}: {m.content}" for m in state['chat_history']])
    
    rewriter_prompt = ChatPromptTemplate.from_template(PROMPT_REGISTRY[PromptType.QUERY_REWRITER].template)
    chain = rewriter_prompt | llm_fast | StrOutputParser()
    
    last_query = state.get("agent_outcome", {}).get("args", {}).get("query")
    new_query = chain.invoke({
        "chat_history": history_str,
        "question": last_query or state["input"]
    })
    
    log.info(f"Query Rewriter Node: New query: '{new_query}'")
    
    # Increment grader loop counter
    new_count = state.get("grader_loop_count", 0) + 1
    return {
        "agent_outcome": {"action": "search_financial_documents", "args": {"query": new_query}},
        "grader_loop_count": new_count
    }

# Routing Logic

def route_initial_request(state: AgentState):
    decision = state.get("router_decision", "financial_query")
    return "call_general_chat" if "general" in decision else "call_agent"

def route_agent_decision(state: AgentState):
    action = state.get("agent_outcome", {}).get("action")
    if action == "search_financial_documents": return "call_retriever"
    if action == "get_whole_table": return "call_table_tool"
    if action == "calculator": return "call_calculator"
    return "finish"

def route_grader_decision(state: AgentState):
    if state.get("grader_status") == "yes": return "call_agent"
    if state.get('grader_loop_count', 0) >= 3:
         log.info("Grader: Rewrite limit reached. Forcing return to agent to use what we have.")
         return "call_agent"
    return "rewrite_query"

# Graph Construction

log.info("Building agent graph...")
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("router", call_router)
workflow.add_node("general_chat", call_general_chat)
workflow.add_node("agent", call_agent)
workflow.add_node("call_retriever", call_retriever)
workflow.add_node("call_table_tool", call_table_tool)
workflow.add_node("call_calculator", call_calculator)
workflow.add_node("grade_relevance", call_grader)
workflow.add_node("rewrite_query", call_query_rewriter)

# Set Entry
workflow.set_entry_point("router")

# Edges
workflow.add_conditional_edges(
    "router",
    route_initial_request,
    {
        "call_general_chat": "general_chat",
        "call_agent": "agent"
    }
)

workflow.add_edge("general_chat", END)

workflow.add_conditional_edges(
    "agent",
    route_agent_decision,
    {
        "call_retriever": "call_retriever",
        "call_table_tool": "call_table_tool",
        "call_calculator": "call_calculator",
        "finish": END
    }
)

# Retriever Logic with Grader Loop
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

# Tool Logic
workflow.add_edge("call_table_tool", "agent")
workflow.add_edge("call_calculator", "agent")

agent_graph = workflow.compile(checkpointer=MemorySaver())
log.info("Agent graph compiled successfully.")

def invoke_agent_chain(query: str, session_id: str, chat_history: List[Tuple[str, str]], callbacks=None):
    """
    Runs the agent chain.
    """
    try:
        log.info(f"Invoking Agentic RAG chain for session {session_id}")
        
        history_messages = []
        for human, ai in chat_history:
            history_messages.append(HumanMessage(content=human))
            history_messages.append(AIMessage(content=ai))

        config = {"configurable": {"thread_id": session_id}, "callbacks": callbacks, "recursion_limit": 50}
        initial_state = {
            "input": query,
            "chat_history": history_messages,
            "recursion_depth": 0,
            "grader_loop_count": 0,
            "retrieved_docs": [],
            "scratchpad_messages": [], # Start with empty scratchpad
        }
        
        final_state = agent_graph.invoke(initial_state, config=config)
        
        agent_outcome = final_state.get("agent_outcome", {})
        
        # Extraction Logic
        answer = None
        if isinstance(agent_outcome, dict):
            args = agent_outcome.get("args", {})
            if isinstance(args, dict):
                answer = args.get("answer")
            elif isinstance(args, str):
                answer = args
            if not answer:
                answer = agent_outcome.get("answer")
        
        if not answer:
            answer = str(agent_outcome)
            
        return answer
    
    except Exception as e:
        log.error("Error invoking agent chain", exc_info=e)
        raise AutoFinQAException("Failed to get a response from the agent.", e)