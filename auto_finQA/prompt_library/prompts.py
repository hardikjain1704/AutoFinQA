# prompt_library/prompts.py

from enum import Enum
from typing import Dict
import string

class PromptType(str, Enum):
    """Enumeration for different types of prompts used in the application."""
    FINANCIAL_QA = "financial_qa"
    RELEVANCE_GRADER = "relevance_grader"
    QUERY_REWRITER = "query_rewriter"

class PromptTemplate:
    """A wrapper for a prompt string that validates placeholders."""
    def __init__(self, template: str, description: str = "", version: str = "v1"):
        self.template = template.strip()
        self.description = description
        self.version = version

    def get_placeholders(self) -> list[str]:
        """Returns a list of required placeholder keys in the template."""
        return [
            field_name
            for _, field_name, _, _ in string.Formatter().parse(self.template)
            if field_name is not None
        ]

# --- Central Prompt Registry ---

PROMPT_REGISTRY: Dict[PromptType, PromptTemplate] = {
    
    PromptType.FINANCIAL_QA: PromptTemplate(
        """You are a highly skilled financial analyst AI. Your task is to provide accurate, data-driven answers based ONLY on the provided financial document context.

Do not make up information or use outside knowledge. If the answer is not available in the context, you must state that clearly.
When you provide numerical answers, cite the source document from the metadata if possible (e.g., "Source: aple-10k.pdf, Page: 42").

Context from financial documents:
{context}

User Question: {question}

Answer:""",
        description="The main prompt for answering financial questions based on context."
    ),

    PromptType.RELEVANCE_GRADER: PromptTemplate(
        """You are a grader assessing the relevance of a retrieved context to a user's question.
Your goal is to filter out irrelevant information.

Respond with a single word: 'yes' if the context is relevant to the question, or 'no' if it is not. Do not provide any explanation.

Retrieved context:
{context}

User question: {question}""",
        description="A prompt to grade if the retrieved context is relevant to the question."
    ),

    PromptType.QUERY_REWRITER: PromptTemplate(
        """You are a query rewriting expert. Your task is to rewrite a user's question to be more optimal for a vector database search.

Do not answer the question itself. Only provide the rewritten, standalone query that is more specific and clear.

Original question: {question}""",
        description="A prompt to rewrite a user's question for better retrieval."
    )
}
