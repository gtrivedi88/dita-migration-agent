"""
DiscreteHeading rule - Discrete headings are not supported in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

DISCRETE_HEADING = Rule(
    name="DiscreteHeading",
    severity=RuleSeverity.WARNING,
    message="Discrete headings are not supported in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""DITA 1.3 does not support discrete (floating) headings.

TO FIX depending on use case:
1. Use a description list for term definitions
2. Use a level 1 section (== Heading) if structure allows
3. Move the content to a separate file
4. Convert to bold text if visual emphasis is all that's needed

Discrete headings ([discrete]) create headings that don't affect document structure,
but this concept doesn't exist in DITA.""",
    examples=[
        RuleExample(
            description="Convert discrete heading to bold",
            before="""[discrete]
== A discrete heading

A paragraph.""",
            after="""*A discrete heading*

A paragraph.""",
        ),
        RuleExample(
            description="Convert to description list",
            before="""[discrete]
== Configuration Options

The following options are available.""",
            after="""Configuration Options::
The following options are available.""",
        ),
    ],
)
