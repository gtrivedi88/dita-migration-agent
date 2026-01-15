"""
ContentType rule - Missing content type definition.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

CONTENT_TYPE = Rule(
    name="ContentType",
    severity=RuleSeverity.WARNING,
    message="Missing :_mod-docs-content-type: attribute.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""Without a content type definition, Vale cannot reliably check procedure-specific rules.

TO FIX:
1. Add :_mod-docs-content-type: attribute at the VERY FIRST LINE of the file
2. Use one of these valid values:
   - PROCEDURE - for task/how-to modules
   - CONCEPT - for conceptual information
   - REFERENCE - for reference tables, lists
   - ASSEMBLY - for files that include other modules
   - SNIPPET - for reusable content fragments

The attribute MUST be on line 1, before any title or other content.""",
    examples=[
        RuleExample(
            description="Add content type to procedure",
            before="""= Installing the component

.Procedure
. Run the install command.
. Verify installation.""",
            after=""":_mod-docs-content-type: PROCEDURE

= Installing the component

.Procedure
. Run the install command.
. Verify installation.""",
        ),
        RuleExample(
            description="Add content type to concept",
            before="""= Understanding the architecture

The system consists of multiple components.""",
            after=""":_mod-docs-content-type: CONCEPT

= Understanding the architecture

The system consists of multiple components.""",
        ),
    ],
)
