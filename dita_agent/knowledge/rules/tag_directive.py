"""
TagDirective rule - Lists tag directives (informational).

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

TAG_DIRECTIVE = Rule(
    name="TagDirective",
    severity=RuleSeverity.SUGGESTION,
    message="Tag directive found.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#suggestions",
    fix_instruction="""INFORMATIONAL ONLY - NO FIX NEEDED.

This rule lists tag directives (tag:: and end::) in the file.
Tags are used to mark regions of content that can be selectively included.

Tag syntax:
- // tag::tagname[]  - start of tagged region
- // end::tagname[]  - end of tagged region

Include tagged regions with:
- include::file.adoc[tag=tagname]
- include::file.adoc[tags=tag1;tag2]

Review tag usage to decide how to handle conditional content after conversion.""",
    examples=[],
)
