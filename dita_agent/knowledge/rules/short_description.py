"""
ShortDescription rule - Add [role="_abstract"] for DITA short description.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

SHORT_DESCRIPTION = Rule(
    name="ShortDescription",
    severity=RuleSeverity.WARNING,
    message='Assign [role="_abstract"] to a paragraph to use it as <shortdesc> in DITA.',
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    skip_for_types=["SNIPPET"],  # Snippets don't need abstracts
    fix_instruction="""DITA 1.3 supports the <shortdesc> element for topic short descriptions.

TO FIX:
1. Find the FIRST content paragraph after the title (and any conditionals/includes)
2. Add [role="_abstract"] on a line BY ITSELF before that paragraph
3. DO NOT move any content - only ADD the attribute line

CRITICAL RULES:
- The [role="_abstract"] line goes BEFORE the paragraph, not after
- If there are conditionals (ifdef::, ifndef::, ifeval::), add [role="_abstract"] AFTER them
- If the paragraph follows include directives, add [role="_abstract"] right before the paragraph
- NEVER reorder paragraphs or move content around
- One [role="_abstract"] per file only

PLACEMENT ORDER:
1. = Title
2. :_mod-docs-content-type: TYPE
3. ifdef::condition[] / include:: directives / endif::[]
4. [role="_abstract"]  <-- ADD HERE
5. First paragraph (this becomes the short description)""",
    examples=[
        RuleExample(
            description="Basic topic needs abstract",
            before="""= Topic title

A paragraph.""",
            after="""= Topic title

[role="_abstract"]
A paragraph."""
        ),
        RuleExample(
            description="Topic with conditionals",
            before="""= Installing the component

ifdef::preview[]
include::../attributes.adoc[]
endif::preview[]

This topic describes how to install the component.""",
            after="""= Installing the component

ifdef::preview[]
include::../attributes.adoc[]
endif::preview[]

[role="_abstract"]
This topic describes how to install the component."""
        ),
    ],
)
