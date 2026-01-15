"""
TaskContents rule - Procedure modules need .Procedure block title.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

TASK_CONTENTS = Rule(
    name="TaskContents",
    severity=RuleSeverity.WARNING,
    message="This procedure module is missing the .Procedure block title.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    applicable_types=["PROCEDURE"],
    fix_instruction="""To correctly map contents to <steps> in DITA 1.3, all procedure modules must
contain the .Procedure block title before the numbered steps.

TO FIX:
1. Add '.Procedure' on its own line before the numbered list
2. Ensure the numbered list follows immediately after .Procedure

Standard procedure structure:
= Task Title
:_mod-docs-content-type: PROCEDURE

[role="_abstract"]
Brief description.

.Prerequisites
* First prerequisite

.Procedure
. First step
. Second step

.Verification
* Verify the result""",
    examples=[
        RuleExample(
            description="Add .Procedure block title",
            before=""":_mod-docs-content-type: PROCEDURE

= Installing the component

. Run the install command.
. Verify installation.""",
            after=""":_mod-docs-content-type: PROCEDURE

= Installing the component

[role="_abstract"]
Install the component on your system.

.Procedure
. Run the install command.
. Verify installation.""",
        ),
    ],
)
