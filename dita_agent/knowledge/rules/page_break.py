"""
PageBreak rule - Page breaks not supported in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

PAGE_BREAK = Rule(
    name="PageBreak",
    severity=RuleSeverity.WARNING,
    message="Page breaks are not supported in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""DITA 1.3 does not support page breaks.

TO FIX:
1. Remove the page break marker (<<<)
2. If visual separation is needed, use horizontal content organization:
   - Split into separate topics
   - Use sections (== headings)
   - Use block separators naturally

Page breaks are a print-specific concept that doesn't translate to DITA's
topic-based architecture.""",
    examples=[
        RuleExample(
            description="Remove page break",
            before="""First section content.

<<<

Second section content.""",
            after="""First section content.

Second section content.""",
        ),
    ],
)
