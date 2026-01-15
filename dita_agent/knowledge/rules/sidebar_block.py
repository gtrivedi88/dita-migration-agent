"""
SidebarBlock rule - Sidebar blocks not supported in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

SIDEBAR_BLOCK = Rule(
    name="SidebarBlock",
    severity=RuleSeverity.WARNING,
    message="Sidebars are not supported in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""DITA 1.3 does not support sidebar content.

TO FIX:
1. Remove the sidebar delimiters (****)
2. Remove [sidebar] attribute if present
3. Convert sidebar content to:
   - A regular paragraph
   - An admonition (NOTE, TIP, etc.) if it's supplementary info
   - A separate topic if it's substantial content

Sidebar patterns to remove:
- [sidebar] attribute
- **** delimiters""",
    examples=[
        RuleExample(
            description="Convert sidebar to admonition",
            before="""****
This is sidebar content with supplementary information.
****""",
            after="""[NOTE]
====
This is sidebar content with supplementary information.
====""",
        ),
        RuleExample(
            description="Convert sidebar to paragraph",
            before="""[sidebar]
Additional context for the main content.""",
            after="""Additional context for the main content.""",
        ),
    ],
)
