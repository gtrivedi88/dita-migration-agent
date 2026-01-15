"""
DITA Knowledge Base - Modular rules and prompts.

This package contains:
- rules/: Individual rule definitions (30 rules from asciidoctor-dita-vale)
- prompts/: Prompt generation for LLM fixes
- content_types.py: Content type detection logic

Based on: https://github.com/jhradilek/asciidoctor-dita-vale
"""

# Re-export from rules module
from .rules.loader import (
    ALL_RULES,
    RULE_NAMES,
    RULE_COUNTS,
    get_rule,
    get_fix_instruction,
    get_rule_severity,
    get_prompt_context,
    get_error_rules,
    get_warning_rules,
    get_suggestion_rules,
    get_actionable_rules,
    get_rules_for_content_type,
    should_skip_rule,
)

from .rules.base import Rule, RuleSeverity, RuleExample

# Re-export from prompts module
from .prompts import PromptGenerator, generate_fix_prompt, generate_batch_fix_prompt

# Re-export content types
from .content_types import ContentType, CONTENT_TYPE_RULES, detect_content_type_heuristic

__all__ = [
    # Rules
    "ALL_RULES",
    "RULE_NAMES", 
    "RULE_COUNTS",
    "Rule",
    "RuleSeverity",
    "RuleExample",
    "get_rule",
    "get_fix_instruction",
    "get_rule_severity",
    "get_prompt_context",
    "get_error_rules",
    "get_warning_rules",
    "get_suggestion_rules",
    "get_actionable_rules",
    "get_rules_for_content_type",
    "should_skip_rule",
    # Prompts
    "PromptGenerator",
    "generate_fix_prompt",
    "generate_batch_fix_prompt",
    # Content Types
    "ContentType",
    "CONTENT_TYPE_RULES",
    "detect_content_type_heuristic",
]
