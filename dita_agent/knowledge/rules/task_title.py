"""
TaskTitle rule - Invalid block titles in task topics.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

TASK_TITLE = Rule(
    name="TaskTitle",
    severity=RuleSeverity.WARNING,
    message="Invalid block title in procedure topic.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    applicable_types=["PROCEDURE"],
    fix_instruction="""DITA task topics only support specific block titles that map to DITA elements.

VALID BLOCK TITLES (use these only):
- .Prerequisite / .Prerequisites → <prereq>
- .Procedure → <steps>
- .Verification / .Result / .Results → <result>
- .Troubleshooting / .Troubleshooting step / .Troubleshooting steps → <tasktroubleshooting>
- .Next step / .Next steps → <postreq>
- .Additional resources → <related-links>

TO FIX:
1. Rename invalid block titles to one of the valid options above
2. Or remove the block title if it's not needed
3. Or move the content to a concept/reference module if it doesn't fit the task structure

Do not use custom block titles like .Overview, .Introduction, .Note, etc.""",
    examples=[
        RuleExample(
            description="Rename invalid block title",
            before=""".Before you begin
* Admin access required
* Backup your data

.Procedure
. Run the command.""",
            after=""".Prerequisites
* Admin access required
* Backup your data

.Procedure
. Run the command.""",
        ),
    ],
)
