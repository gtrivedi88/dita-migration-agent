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
DO NOT suggest adding [discrete] as a fix - it creates a new violation.

VALE'S BLOCKTITLE RULE CONTEXT:
Vale's BlockTitle.yml has special logic for PROCEDURE modules:
- In procedures, these titles are ALLOWED: .Prerequisites, .Procedure, .Verification, .Results, .Troubleshooting, .Next steps
- If you see a BlockTitle warning, it means:
  1. The file is NOT a procedure module, OR
  2. The title doesn't match exactly, OR
  3. It's genuinely unsupported

TO FIX:

Option 1 (Preferred for simple titles): Convert to bold emphasis
  Before: .Important note
  After:  *Important note:*

  Use when the title is just labeling content, not creating structure.

Option 2 (For assembly sections): Convert to proper level-1 heading
  Before: .Prerequisites
  After:  == Prerequisites

  IMPORTANT: Do this WITHOUT [discrete]!
  Use only in ASSEMBLIES when you need a true section.
  The heading becomes a real section in the document structure.

Option 3 (Remove if unnecessary):
  Before: .My title
          Some text
  After:  Some text

  Use when the title adds no value.

WRONG APPROACHES (DO NOT DO THESE):

❌ WRONG: [discrete]
          == Prerequisites

   Why wrong: [discrete] triggers DiscreteHeading warning!
   This creates a new DITA violation while trying to fix BlockTitle.

❌ WRONG: Convert .Prerequisites to == Prerequisites in a PROCEDURE module

   Why wrong: .Prerequisites is ALLOWED in procedures by Vale's rule.
   The warning only appears if it's NOT a procedure.

VERIFICATION:
After fixing, the heading should be:
- Either bold text (*Title:*), OR
- A section heading (== Title) WITHOUT [discrete], OR
- Removed entirely

Never produce output with [discrete] in it.""",
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
