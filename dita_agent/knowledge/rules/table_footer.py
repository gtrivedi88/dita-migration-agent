"""
TableFooter rule - Table footers not supported in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

TABLE_FOOTER = Rule(
    name="TableFooter",
    severity=RuleSeverity.WARNING,
    message="Table footers are not supported in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""DITA 1.3 does not support table footers.

TO FIX:
1. Remove the %footer option from table attributes
2. Remove options="footer" from table attributes
3. Move footer content to:
   - The last regular row of the table
   - A note below the table
   - A caption/title if it's summary information

Table footer patterns to remove:
- [%footer]
- [options="footer"]
- [options='footer']""",
    examples=[
        RuleExample(
            description="Remove footer option",
            before="""[%footer,cols="1,1"]
|===
|Header 1 |Header 2

|Data 1 |Data 2

|Footer 1 |Footer 2
|===""",
            after="""[cols="1,1"]
|===
|Header 1 |Header 2

|Data 1 |Data 2

|*Total:* |*Summary*
|===""",
        ),
    ],
)
