from enum import Enum
from typing import Dict
import string


class PromptType(str, Enum):
    FINANCIAL_QA_BOT = "finqa_bot"
    # REVIEW_BOT = "review_bot"
    # COMPARISON_BOT = "comparison_bot"


class PromptTemplate:
    def __init__(self, template: str, description: str = "", version: str = "v1"):
        self.template = template.strip()
        self.description = description
        self.version = version

    def format(self, **kwargs) -> str:
        # Validate placeholders before formatting
        missing = [
            f for f in self.required_placeholders() if f not in kwargs
        ]
        if missing:
            raise ValueError(f"Missing placeholders: {missing}")
        return self.template.format(**kwargs)

    def required_placeholders(self):
        return [field_name for _, field_name, _, _ in string.Formatter().parse(self.template) if field_name]


# Central Registry
PROMPT_REGISTRY: Dict[PromptType, PromptTemplate] = {
    PromptType.FINANCIAL_QA_BOT: PromptTemplate(
    """
    You are an expert Quantitative Financial Analyst AI. Your purpose is to provide precise, data-driven answers by performing accurate mathematical calculations based ONLY on the financial context provided.

    To answer the question, you must follow this exact process:
    1.  **EXTRACT:** Identify and list all the specific numerical values and corresponding text from the CONTEXT that are required to answer the QUESTION.
    2.  **PLAN:** Formulate a step-by-step mathematical plan (e.g., addition, subtraction, division, ratio calculation) using the extracted values.
    3.  **EXECUTE:** Perform the calculation as per your plan.
    4.  **CONCLUDE:** State the final answer clearly and concisely.

    If the CONTEXT lacks the necessary information to answer the QUESTION, you must state: "The provided context does not contain sufficient information to answer this question." Do not use outside knowledge.

    CONTEXT:
    {context}

    QUESTION: {question}

    YOUR ANSWER:
    """,
    description="A prompt for a financial bot that performs numerical reasoning and calculation by showing its work."
    )
}
