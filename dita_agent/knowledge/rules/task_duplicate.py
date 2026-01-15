"""
TaskDuplicate rule - Duplicate block titles in procedures.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

TASK_DUPLICATE = Rule(
    name="TaskDuplicate",
    severity=RuleSeverity.WARNING,
    message="Duplicate block titles are not allowed in DITA tasks.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    applicable_types=["PROCEDURE"],
    fix_instruction="""DITA task topics can only have ONE of each block title type.
Each maps to a specific DITA element that can appear only once.

TO FIX:
1. Remove duplicate block titles
2. Combine content under a single block title
3. If multiple procedures are needed, split into separate modules

DITA task structure (each element appears once):
- .Prerequisites → <prereq>
- .Procedure → <steps>
- .Verification/.Result → <result>
- .Troubleshooting → <tasktroubleshooting>
- .Next steps → <postreq>""",
    examples=[
        RuleExample(
            description="Combine duplicate prerequisites",
            before=""".Prerequisites
* Prerequisite 1

.Prerequisites
* Prerequisite 2""",
            after=""".Prerequisites
* Prerequisite 1
* Prerequisite 2""",
        ),
    ],
)
