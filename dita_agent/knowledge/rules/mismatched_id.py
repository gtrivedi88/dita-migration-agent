"""
MismatchedId rule - Mismatched quotes in custom ID attributes.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

MISMATCHED_ID = Rule(
    name="MismatchedId",
    severity=RuleSeverity.ERROR,
    message="The quotes in the ID are mismatched.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#errors",
    fix_instruction="""The [id=...] attribute has mismatched or missing quotes.

VALE RULE BEHAVIOR (MismatchedId.yml):
Detects ID attributes where quotes are inconsistent:
- One quote missing: [id="foo] or [id=foo"]
- Mixed quote types: [id="foo'] or [id='foo"]

TO FIX:
Normalize the ID attribute to use consistent double quotes:
  Before: [id='my-section_{context}"]
  After:  [id="my-section_{context}"]

  Before: [id=my-section_{context}"]
  After:  [id="my-section_{context}"]

Always use double quotes for ID attributes in AsciiDoc.""",
    examples=[
        RuleExample(
            description="Fix mismatched quotes (single to double)",
            before="""[id='my-section_{context}"]
= My Section""",
            after="""[id="my-section_{context}"]
= My Section""",
        ),
        RuleExample(
            description="Fix missing opening quote",
            before="""[id=my-section_{context}"]
= My Section""",
            after="""[id="my-section_{context}"]
= My Section""",
        ),
    ],
)
