"""
Rule loader - Dynamically loads all rule definitions.

This module provides functions to access all rules from the modular rule files.
"""

from typing import Dict, List, Optional

from .base import Rule, RuleSeverity

# Import all rule definitions
from .admonition_title import ADMONITION_TITLE
from .assembly_contents import ASSEMBLY_CONTENTS
from .attribute_reference import ATTRIBUTE_REFERENCE
from .author_line import AUTHOR_LINE
from .block_title import BLOCK_TITLE
from .callout_list import CALLOUT_LIST
from .conditional_code import CONDITIONAL_CODE
from .content_type import CONTENT_TYPE
from .discrete_heading import DISCRETE_HEADING
from .document_id import DOCUMENT_ID
from .document_title import DOCUMENT_TITLE
from .entity_reference import ENTITY_REFERENCE
from .equation_formula import EQUATION_FORMULA
from .example_block import EXAMPLE_BLOCK
from .include_directive import INCLUDE_DIRECTIVE
from .line_break import LINE_BREAK
from .nested_section import NESTED_SECTION
from .page_break import PAGE_BREAK
from .related_links import RELATED_LINKS
from .short_description import SHORT_DESCRIPTION
from .sidebar_block import SIDEBAR_BLOCK
from .table_footer import TABLE_FOOTER
from .tag_directive import TAG_DIRECTIVE
from .task_contents import TASK_CONTENTS
from .task_duplicate import TASK_DUPLICATE
from .task_example import TASK_EXAMPLE
from .task_section import TASK_SECTION
from .task_step import TASK_STEP
from .task_title import TASK_TITLE
from .thematic_break import THEMATIC_BREAK


# All rules in a dictionary for easy lookup
ALL_RULES: Dict[str, Rule] = {
    "AdmonitionTitle": ADMONITION_TITLE,
    "AssemblyContents": ASSEMBLY_CONTENTS,
    "AttributeReference": ATTRIBUTE_REFERENCE,
    "AuthorLine": AUTHOR_LINE,
    "BlockTitle": BLOCK_TITLE,
    "CalloutList": CALLOUT_LIST,
    "ConditionalCode": CONDITIONAL_CODE,
    "ContentType": CONTENT_TYPE,
    "DiscreteHeading": DISCRETE_HEADING,
    "DocumentId": DOCUMENT_ID,
    "DocumentTitle": DOCUMENT_TITLE,
    "EntityReference": ENTITY_REFERENCE,
    "EquationFormula": EQUATION_FORMULA,
    "ExampleBlock": EXAMPLE_BLOCK,
    "IncludeDirective": INCLUDE_DIRECTIVE,
    "LineBreak": LINE_BREAK,
    "NestedSection": NESTED_SECTION,
    "PageBreak": PAGE_BREAK,
    "RelatedLinks": RELATED_LINKS,
    "ShortDescription": SHORT_DESCRIPTION,
    "SidebarBlock": SIDEBAR_BLOCK,
    "TableFooter": TABLE_FOOTER,
    "TagDirective": TAG_DIRECTIVE,
    "TaskContents": TASK_CONTENTS,
    "TaskDuplicate": TASK_DUPLICATE,
    "TaskExample": TASK_EXAMPLE,
    "TaskSection": TASK_SECTION,
    "TaskStep": TASK_STEP,
    "TaskTitle": TASK_TITLE,
    "ThematicBreak": THEMATIC_BREAK,
}


def get_rule(rule_name: str) -> Optional[Rule]:
    """
    Get a rule by name.
    
    Args:
        rule_name: Name of the Vale rule (e.g., 'LineBreak').
        
    Returns:
        Rule object if found, None otherwise.
    """
    return ALL_RULES.get(rule_name)


def get_fix_instruction(rule_name: str) -> Optional[str]:
    """
    Get fix instruction for a rule.
    
    Args:
        rule_name: Name of the Vale rule.
        
    Returns:
        Fix instruction string, or None if rule not found.
    """
    rule = get_rule(rule_name)
    if rule:
        return rule.fix_instruction
    return None


def get_rule_severity(rule_name: str) -> RuleSeverity:
    """
    Get severity level for a rule.
    
    Args:
        rule_name: Name of the Vale rule.
        
    Returns:
        Severity level (defaults to WARNING if not found).
    """
    rule = get_rule(rule_name)
    if rule:
        return rule.severity
    return RuleSeverity.WARNING


def get_prompt_context(rule_name: str) -> Optional[str]:
    """
    Get full prompt context for a rule (includes examples).
    
    Args:
        rule_name: Name of the Vale rule.
        
    Returns:
        Formatted prompt context, or None if rule not found.
    """
    rule = get_rule(rule_name)
    if rule:
        return rule.get_prompt_context()
    return None


def get_error_rules() -> Dict[str, Rule]:
    """Get all rules with ERROR severity."""
    return {
        name: rule for name, rule in ALL_RULES.items()
        if rule.severity == RuleSeverity.ERROR
    }


def get_warning_rules() -> Dict[str, Rule]:
    """Get all rules with WARNING severity."""
    return {
        name: rule for name, rule in ALL_RULES.items()
        if rule.severity == RuleSeverity.WARNING
    }


def get_suggestion_rules() -> Dict[str, Rule]:
    """Get all rules with SUGGESTION severity."""
    return {
        name: rule for name, rule in ALL_RULES.items()
        if rule.severity == RuleSeverity.SUGGESTION
    }


def get_actionable_rules() -> Dict[str, Rule]:
    """Get all rules that are actionable (ERROR or WARNING)."""
    return {
        name: rule for name, rule in ALL_RULES.items()
        if rule.severity in (RuleSeverity.ERROR, RuleSeverity.WARNING)
    }


def get_rules_for_content_type(content_type: Optional[str]) -> Dict[str, Rule]:
    """
    Get rules that apply to a specific content type.
    
    Args:
        content_type: Content type (PROCEDURE, CONCEPT, etc.)
        
    Returns:
        Dictionary of rules that apply to this content type.
    """
    return {
        name: rule for name, rule in ALL_RULES.items()
        if rule.should_apply(content_type)
    }


def should_skip_rule(rule_name: str, content_type: Optional[str]) -> bool:
    """
    Check if a rule should be skipped for a content type.
    
    Args:
        rule_name: Name of the Vale rule.
        content_type: Content type of the file.
        
    Returns:
        True if rule should be skipped, False otherwise.
    """
    rule = get_rule(rule_name)
    if rule:
        return not rule.should_apply(content_type)
    return False


# List of all rule names
RULE_NAMES: List[str] = list(ALL_RULES.keys())

# Count of rules by severity
RULE_COUNTS = {
    "total": len(ALL_RULES),
    "errors": len(get_error_rules()),
    "warnings": len(get_warning_rules()),
    "suggestions": len(get_suggestion_rules()),
}
