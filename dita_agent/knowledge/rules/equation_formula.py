"""
EquationFormula rule - LaTeX/AsciiMath formulas not supported.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

EQUATION_FORMULA = Rule(
    name="EquationFormula",
    severity=RuleSeverity.WARNING,
    message="LaTeX and AsciiMath formulas are not supported in DITA conversion.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""The DITA conversion tooling does not implement LaTeX or AsciiMath formula rendering.

TO FIX:
1. Convert simple formulas to plain text: x^2 → x², a/b → a÷b
2. For complex formulas, create an image and include it
3. Use Unicode characters for mathematical symbols where possible
4. Consider using a table for equation layout if appropriate

Common replacements:
- stem:[x^2] → x²
- stem:[sqrt(x)] → √x
- stem:[alpha] → α
- stem:[beta] → β
- stem:[sum] → Σ""",
    examples=[
        RuleExample(
            description="Convert simple formula to text",
            before="""The formula is stem:[x^2 + y^2 = z^2].""",
            after="""The formula is x² + y² = z².""",
        ),
    ],
)
