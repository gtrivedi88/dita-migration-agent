"""
DocumentId rule - Document ID required for DITA topics.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

DOCUMENT_ID = Rule(
    name="DocumentId",
    severity=RuleSeverity.WARNING,
    message="Document title is missing an ID.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""DITA 1.3 requires topics to have an ID.

TO FIX:
1. Add an ID attribute to the document title
2. Use the format: [id="unique-id"] before the title
3. Or use inline format: = Title [[unique-id]]

The ID should be:
- Lowercase
- Use hyphens for spaces
- Be descriptive of the content
- Be unique within the project""",
    examples=[
        RuleExample(
            description="Add ID using attribute syntax",
            before="""= Installing the component

Content here.""",
            after="""[id="installing-the-component"]
= Installing the component

Content here.""",
        ),
        RuleExample(
            description="Add ID using inline syntax",
            before="""= Understanding the architecture

Content here.""",
            after="""[[understanding-the-architecture]]
= Understanding the architecture

Content here.""",
        ),
    ],
)
