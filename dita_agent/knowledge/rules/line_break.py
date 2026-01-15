"""
LineBreak rule - Hard line breaks are not supported in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

LINE_BREAK = Rule(
    name="LineBreak",
    severity=RuleSeverity.WARNING,
    message="Hard line breaks are not supported in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""DITA 1.3 does not support hard line breaks.

TO FIX (Outside Tables):
1. Remove the ' +' (space plus) at the end of lines
2. Split the text into multiple paragraphs (add blank line between)

TO FIX (Inside Tables):
When ` +` appears in table cells, it's used for line continuation.
The fix is to MERGE the content into a single line or restructure:

1. If the ` +` joins code/config elements, merge them:
   BEFORE: | `spec.config.` +
           `optionName` | value |
   AFTER:  | `spec.config.optionName` | value |

2. If content must wrap, restructure the cell without ` +`

PATTERNS TO REMOVE/FIX:
- 'text +' at end of line → merge content or split into paragraphs
- ':hardbreaks-option:' attribute → remove this attribute
- '[%hardbreaks]' option → remove this option

The goal is to use proper structure instead of forced line breaks.""",
    examples=[
        RuleExample(
            description="Remove hard line break marker",
            before="""An example +
hard line break.""",
            after="""An example paragraph.

A second paragraph with the continued content."""
        ),
        RuleExample(
            description="Fix line break in table cell - merge content",
            before="""| `spec.dashboardConfig.` +
`disableFeature` | `false` | Description here""",
            after="""| `spec.dashboardConfig.disableFeature` | `false` | Description here"""
        ),
        RuleExample(
            description="Remove hardbreaks attribute",
            before=""":hardbreaks-option:

An example
hard line break.""",
            after="""An example paragraph.

A second paragraph."""
        ),
    ],
)
