"""
EntityReference rule - HTML entity references not supported in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

ENTITY_REFERENCE = Rule(
    name="EntityReference",
    severity=RuleSeverity.ERROR,
    message="HTML character entity references are not supported in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#errors",
    fix_instruction="""DITA 1.3 only supports five XML character entity references:
- &amp; (ampersand)
- &lt; (less than)
- &gt; (greater than)
- &apos; (apostrophe)
- &quot; (quotation mark)

TO FIX:
Replace HTML entities with AsciiDoc built-in attributes:
- &nbsp; → {nbsp}
- &mdash; → {mdash} or --
- &ndash; → {ndash}
- &copy; → (C) or {copy}
- &reg; → (R) or {reg}
- &trade; → (TM) or {trade}
- &hellip; → ... or {ellipsis}
- &rarr; → -> or {rarr}
- &larr; → <- or {larr}

See: https://docs.asciidoctor.org/asciidoc/latest/attributes/character-replacement-ref/""",
    examples=[
        RuleExample(
            description="Replace nbsp entity",
            before="""Red&nbsp;Hat OpenShift""",
            after="""Red{nbsp}Hat OpenShift""",
        ),
        RuleExample(
            description="Replace mdash entity",
            before="""This option&mdash;when enabled&mdash;provides security.""",
            after="""This option--when enabled--provides security.""",
        ),
    ],
)
