"""
TaskSection rule - Sections not allowed in task topics.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

TASK_SECTION = Rule(
    name="TaskSection",
    severity=RuleSeverity.ERROR,
    message="Sections (== headings) are not allowed in DITA task topics.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#errors",
    applicable_types=["PROCEDURE"],
    fix_instruction="""DITA 1.3 does not allow sections (== level headings) in task topics.

TO FIX:
1. Remove == section headings from procedure modules
2. Use the allowed block titles instead:
   - .Prerequisites
   - .Procedure
   - .Verification / .Result
   - .Next steps
   - .Additional resources
3. If a section is truly needed, move it to a separate file
4. Convert section headings to bold text if just visual emphasis is needed""",
    examples=[
        RuleExample(
            description="Convert section to block title",
            before=""":_mod-docs-content-type: PROCEDURE

= Main procedure

== Before you begin

Some prerequisite info.

.Procedure
. Step 1""",
            after=""":_mod-docs-content-type: PROCEDURE

= Main procedure

.Prerequisites
Some prerequisite info.

.Procedure
. Step 1""",
        ),
    ],
)
