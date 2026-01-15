"""
Modular prompts for DITA issue fixes.

This module provides prompt templates that incorporate rule-specific
fix instructions and examples.
"""

from .base import PromptGenerator, generate_fix_prompt, generate_batch_fix_prompt

__all__ = ["PromptGenerator", "generate_fix_prompt", "generate_batch_fix_prompt"]
