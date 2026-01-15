"""
ExampleBlock rule - Example block placement restrictions in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

EXAMPLE_BLOCK = Rule(
    name="ExampleBlock",
    severity=RuleSeverity.ERROR,
    message="Example blocks can only appear in the main body of a topic in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#errors",
    fix_instruction="""DITA 1.3 allows the <example> element only in the main body of a topic.

TO FIX:
1. Move example blocks out of sections (== headings)
2. Move example blocks out of other blocks (admonitions, sidebars)
3. Move example blocks out of list items
4. Example blocks should be at the top level of the document body

If an example must appear in a nested location, consider:
- Using a code block instead of an example block
- Restructuring the content
- Moving the example to a separate file""",
    examples=[
        RuleExample(
            description="Move example out of section",
            before="""= Main Topic

== Section

====
An example in a section.
====""",
            after="""= Main Topic

====
An example in the main body.
====

== Section

The section content without the example.""",
        ),
    ],
)
