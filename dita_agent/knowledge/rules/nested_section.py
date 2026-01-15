"""
NestedSection rule - Nested sections not supported in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

NESTED_SECTION = Rule(
    name="NestedSection",
    severity=RuleSeverity.ERROR,
    message="Nested sections are not supported in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#errors",
    fix_instruction="""DITA 1.3 allows the <section> element only within the main body of a topic.
Sections cannot be nested inside other sections.

TO FIX:
1. Move level 2+ sections (===, ====) to separate files
2. Convert subsections to bold text or description lists
3. Use a flat structure with only level 1 sections (==)
4. Create an assembly that includes multiple modules

The DITA information architecture encourages small, focused topics rather than
deeply nested documents.""",
    examples=[
        RuleExample(
            description="Flatten nested sections",
            before="""= Main Topic

== First Section

=== Nested Section

Content here.

== Second Section""",
            after="""= Main Topic

== First Section

*Nested Section*

Content here.

== Second Section""",
        ),
    ],
)
