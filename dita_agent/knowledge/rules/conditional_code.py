"""
ConditionalCode rule - Lists conditionals (informational).

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

CONDITIONAL_CODE = Rule(
    name="ConditionalCode",
    severity=RuleSeverity.SUGGESTION,
    message="Conditional directive found.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#suggestions",
    fix_instruction="""INFORMATIONAL ONLY - NO FIX NEEDED.

This rule lists ifdef, ifndef, and ifeval conditional statements.
This information helps you decide which attribute definitions to supply
during DITA conversion to control which content is included.

Conditional types:
- ifdef::attribute[] - include if attribute is defined
- ifndef::attribute[] - include if attribute is NOT defined  
- ifeval::[condition] - include if condition is true

Review conditionals to ensure correct content is included in the output.""",
    examples=[],
)
