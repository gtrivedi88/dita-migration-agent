"""
RelatedLinks rule - Additional resources must contain only links.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

RELATED_LINKS = Rule(
    name="RelatedLinks",
    severity=RuleSeverity.WARNING,
    message="The .Additional resources section can only contain links.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""In DITA 1.3, the <related-links> element can only contain links.

TO FIX:
1. Format .Additional resources as an unordered list of links
2. Remove any explanatory text before/after links
3. Remove any list items that aren't links
4. Each item should contain ONLY a link (xref: or link:)

Valid link formats:
- xref:other-topic.adoc[Topic Title]
- link:https://example.com[External Link]

Do not include text like "For more information, see..." or "Related topics include:".""",
    examples=[
        RuleExample(
            description="Remove non-link text",
            before=""".Additional resources
* For more information, see xref:other-topic.adoc[Other Topic].
* The configuration guide has more details.
* link:https://example.com[External Resource]""",
            after=""".Additional resources
* xref:other-topic.adoc[Other Topic]
* xref:configuration-guide.adoc[Configuration Guide]
* link:https://example.com[External Resource]""",
        ),
    ],
)
