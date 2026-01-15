"""
ThematicBreak rule - Thematic breaks not supported in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

THEMATIC_BREAK = Rule(
    name="ThematicBreak",
    severity=RuleSeverity.WARNING,
    message="Thematic breaks are not supported in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""DITA 1.3 does not support thematic breaks (horizontal rules).

TO FIX:
1. Remove the thematic break marker (''' or ---)
2. If visual separation is needed:
   - Use sections (== headings) to organize content
   - Split into separate topics
   - Use block titles (.Title) for logical separation
   - Simply use paragraph breaks (blank lines)

Thematic breaks are visual-only elements that don't translate to DITA's
semantic structure.""",
    examples=[
        RuleExample(
            description="Remove thematic break",
            before="""First section content.

'''

Second section content.""",
            after="""First section content.

Second section content.""",
        ),
        RuleExample(
            description="Replace with section heading",
            before="""Introduction content.

---

Main content begins here.""",
            after="""Introduction content.

== Main Content

Main content begins here.""",
        ),
    ],
)
