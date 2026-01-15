"""
AttributeReference rule - Lists attribute references (informational).

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

ATTRIBUTE_REFERENCE = Rule(
    name="AttributeReference",
    severity=RuleSeverity.SUGGESTION,
    message="Attribute reference found.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#suggestions",
    fix_instruction="""INFORMATIONAL ONLY - NO FIX NEEDED.

This rule lists attribute references ({attribute-name}) in the file.
This information helps you decide which attribute definitions to supply
during DITA conversion.

Common attributes that may need definition:
- {product-name}, {product-version}
- {nbsp}, {mdash}, {ndash}
- Custom project attributes

Ensure all referenced attributes are defined in your attribute files
or conversion configuration.""",
    examples=[],
)
