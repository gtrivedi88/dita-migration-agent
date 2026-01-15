"""
IncludeDirective rule - Lists include directives (informational).

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

INCLUDE_DIRECTIVE = Rule(
    name="IncludeDirective",
    severity=RuleSeverity.SUGGESTION,
    message="Include directive found.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#suggestions",
    fix_instruction="""INFORMATIONAL ONLY - NO FIX NEEDED.

This rule lists include:: directives in the file.
This information helps you decide if include directives should be
processed during conversion.

Include directive syntax:
- include::path/to/file.adoc[]
- include::path/to/file.adoc[leveloffset=+1]
- include::path/to/file.adoc[lines=1..10]
- include::path/to/file.adoc[tag=tagname]

Ensure all included files exist and are accessible during conversion.""",
    examples=[],
)
