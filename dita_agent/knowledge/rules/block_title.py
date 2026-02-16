"""
BlockTitle rule - Block title usage restrictions in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

BLOCK_TITLE = Rule(
    name="BlockTitle",
    severity=RuleSeverity.WARNING,
    message="Block titles are only supported on specific elements in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""In DITA 1.3, only <example>, <fig>, and <table> elements can have titles.

CRITICAL: NEVER suggest [discrete] headings!
[discrete] headings are NOT DITA-compatible and will trigger DiscreteHeading warnings.

VALE RULE BEHAVIOR (BlockTitle.yml):
The rule is CONTENT-TYPE AWARE. Different block titles are allowed depending
on the file's :_mod-docs-content-type: value.

PROCEDURE files — these block titles are ALLOWED (vale skips them):
  .Prerequisites, .Prerequisite
  .Procedure
  .Verification
  .Result, .Results
  .Troubleshooting, .Troubleshooting step, .Troubleshooting steps
  .Next steps, .Next step

ALL content types — this block title is ALLOWED:
  .Additional resources

CONCEPT / REFERENCE / ASSEMBLY files — ALL block titles are FORBIDDEN
except .Additional resources. Even .Prerequisites, .Procedure, etc.
trigger a warning in non-PROCEDURE files.

HOW TO FIX (depends on content type):

For CONCEPT / REFERENCE files:
  - .Prerequisites / .Procedure / .Next steps etc. should NOT appear.
    If they do, the file may actually be a PROCEDURE (wrong content type).
    Check if the file has numbered steps — if so, it should be PROCEDURE.
  - Other block titles (.Some title): convert to bold text (*Some title:*)
    or remove if unnecessary.

For ASSEMBLY files:
  - .Next step / .Next steps: merge links into .Additional resources section.
    "Next step" is NOT recognized as valid after include directives.
  - Other block titles: convert to bold text or remove.

For PROCEDURE files:
  - If you get a BlockTitle warning in a PROCEDURE, the title name does
    NOT match the allowed list exactly. Check spelling and case:
    ".Prerequisite" (singular) is allowed, ".Pre-requisites" is NOT.
  - For custom titles (.Important note): convert to bold (*Important note:*).

WRONG APPROACHES:
- DO NOT add [discrete] — triggers DiscreteHeading warning.
- DO NOT convert .Prerequisites to == Prerequisites in a PROCEDURE —
  that triggers TaskSection error (== headings forbidden in procedures).
- DO NOT use .Next step in assemblies — only .Additional resources is valid.""",
    examples=[
        RuleExample(
            description="Remove title from paragraph",
            before=""".A paragraph title
This is a paragraph that doesn't need a block title.""",
            after="""This is a paragraph that doesn't need a block title.""",
        ),
        RuleExample(
            description="Convert to bold if title is needed",
            before=""".Important information
This paragraph has important content.""",
            after="""*Important information:* This paragraph has important content.""",
        ),
    ],
)
