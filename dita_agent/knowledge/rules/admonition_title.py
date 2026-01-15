"""
AdmonitionTitle rule - Admonition titles are not supported in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

ADMONITION_TITLE = Rule(
    name="AdmonitionTitle",
    severity=RuleSeverity.WARNING,
    message="Admonition titles are not supported in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""In DITA 1.3, the <note> element cannot have a title.

TO FIX:
1. Remove the block title (line starting with '.') before admonitions
2. If the title content is important, move it into the admonition text itself

PATTERNS TO FIX:
- '.Title' followed by '[NOTE]' → remove the '.Title' line
- '.Title' followed by 'NOTE:' → remove the '.Title' line
- Same applies to TIP, IMPORTANT, WARNING, CAUTION

You can incorporate the title's meaning into the admonition text if needed.""",
    examples=[
        RuleExample(
            description="Remove title from block admonition",
            before=""".An admonition title
[NOTE]
====
A note.
====""",
            after="""[NOTE]
====
A note.
====""",
        ),
        RuleExample(
            description="Remove title from paragraph admonition",
            before=""".An admonition title
NOTE: A note.""",
            after="""NOTE: A note.""",
        ),
        RuleExample(
            description="Move important title content into admonition",
            before=""".Critical Security Warning
[WARNING]
====
Update your credentials.
====""",
            after="""[WARNING]
====
*Critical Security Warning:* Update your credentials.
====""",
        ),
    ],
)
