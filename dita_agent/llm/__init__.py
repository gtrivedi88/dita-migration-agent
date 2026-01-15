"""
LLM integration module.

Handles all communication with Gemini API for targeted edits.
Key principle: Always use targeted edits (old_string → new_string),
never full file rewrites.
"""

from dita_agent.llm.client import LLMClient, LLMResponse
from dita_agent.llm.prompts import PromptBuilder, PromptType

__all__ = [
    "LLMClient",
    "LLMResponse",
    "PromptBuilder",
    "PromptType",
]
