"""
BlockTitle rule - Block title usage restrictions in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

BLOCK_TITLE = Rule(
    name="BlockTitle",
    severity=RuleSeverity.WARNING,
    message="Block titles are only supported on specific elements in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""In DITA 1.3, only <example>, <fig>, and <table> elements can have titles.

TO FIX:
1. Remove block titles from paragraphs, lists, and other blocks
2. Keep block titles only on:
   - Example blocks (====)
   - Images/figures
   - Tables
3. For procedure-specific titles, use the allowed block titles:
   - .Prerequisites / .Prerequisite
   - .Procedure
   - .Verification / .Result / .Results
   - .Additional resources
   - .Next step / .Next steps

If a title is necessary for other content, convert it to bold text or a heading.""",
    examples=[
        RuleExample(
            description="Remove title from paragraph",
            before=""".A paragraph title
This is a paragraph that doesn't need a block title.""",
            after="""This is a paragraph that doesn't need a block title.""",
        ),
        RuleExample(
            description="Convert to bold if title is needed",
            before=""".Important information
This paragraph has important content.""",
            after="""*Important information:* This paragraph has important content.""",
        ),
    ],
)
