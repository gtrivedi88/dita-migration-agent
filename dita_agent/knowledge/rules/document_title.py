"""
DocumentTitle rule - Document title required for DITA topics.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

DOCUMENT_TITLE = Rule(
    name="DocumentTitle",
    severity=RuleSeverity.WARNING,
    message="Document is missing a title.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    skip_for_types=["SNIPPET"],  # Snippets don't need titles
    fix_instruction="""DITA 1.3 requires topics to have a title.

TO FIX:
1. Add a level-1 heading (= Title) if it's an assembly or module
2. OR add :_mod-docs-content-type: SNIPPET to mark it as a snippet

For modules/assemblies:
- Title must be a level-1 heading (single =)
- Title should be descriptive of the content
- Title should follow any content type attribute""",
    examples=[
        RuleExample(
            description="Add title to module",
            before=""":_mod-docs-content-type: PROCEDURE

.Procedure
. Run the command.
. Verify result.""",
            after=""":_mod-docs-content-type: PROCEDURE

= Installing the component

.Procedure
. Run the command.
. Verify result.""",
        ),
        RuleExample(
            description="Mark as snippet if no title needed",
            before="""// Common attributes
:product-name: My Product
:version: 1.0""",
            after=""":_mod-docs-content-type: SNIPPET

// Common attributes
:product-name: My Product
:version: 1.0""",
        ),
    ],
)
