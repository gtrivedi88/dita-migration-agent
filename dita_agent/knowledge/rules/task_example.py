"""
TaskExample rule - Only one example block in task topics.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

TASK_EXAMPLE = Rule(
    name="TaskExample",
    severity=RuleSeverity.ERROR,
    message="DITA tasks allow only one example block.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#errors",
    applicable_types=["PROCEDURE"],
    fix_instruction="""DITA 1.3 allows only one <example> element in a task topic.

TO FIX:
1. Combine multiple example blocks into a single example block
2. Or move additional examples into the verification/result section
3. Or convert extra examples to regular paragraphs/code blocks

If multiple distinct examples are needed, consider:
- Combining them with clear headings inside one example block
- Using numbered examples within the single block""",
    examples=[
        RuleExample(
            description="Combine multiple examples",
            before="""====
First example content.
====

====
Second example content.
====""",
            after="""====
*Example 1: First scenario*

First example content.

*Example 2: Second scenario*

Second example content.
====""",
        ),
    ],
)
