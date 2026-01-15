"""
TaskStep rule - Content after .Procedure must be a single list.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

TASK_STEP = Rule(
    name="TaskStep",
    severity=RuleSeverity.WARNING,
    message="Content other than a single list cannot be mapped to DITA tasks.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    applicable_types=["PROCEDURE"],
    fix_instruction="""DITA 1.3 allows only one <steps> or <steps-unordered> element in a task topic.
All content after .Procedure must be part of a single list.

TO FIX:
1. Ensure all steps are in one continuous numbered/bulleted list
2. Use list continuation (+) to attach paragraphs/blocks to steps
3. Move content before the list to .Prerequisites or the intro
4. Move content after the list to .Verification, .Result, or .Next steps

LIST CONTINUATION SYNTAX:
. Step text
+
Additional paragraph or block attached to this step.
+
[source,bash]
----
code block attached to this step
----

. Next step""",
    examples=[
        RuleExample(
            description="Use list continuation for mid-step content",
            before=""".Procedure
. Run the command.

This paragraph breaks the list.

. Verify the result.""",
            after=""".Procedure
. Run the command.
+
This paragraph is now attached to step 1.

. Verify the result.""",
        ),
        RuleExample(
            description="Move post-step content to Result",
            before=""".Procedure
. Run the command.
. Check output.

The output shows success.

Congratulations!""",
            after=""".Procedure
. Run the command.
. Check output.

.Verification
The output shows success.

Congratulations!""",
        ),
    ],
)
