"""
AuthorLine rule - Author line formatting issue.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

AUTHOR_LINE = Rule(
    name="AuthorLine",
    severity=RuleSeverity.WARNING,
    message="Author line detected after title.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""AsciiDoc interprets the first line that directly follows the document title as an author line.

TO FIX:
1. Add an empty line after the document title
2. The :_mod-docs-content-type: attribute should follow the blank line

This prevents AsciiDoc from misinterpreting content as author metadata.""",
    examples=[
        RuleExample(
            description="Add blank line after title",
            before="""= Document Title
:_mod-docs-content-type: CONCEPT""",
            after="""= Document Title

:_mod-docs-content-type: CONCEPT""",
        ),
    ],
)
