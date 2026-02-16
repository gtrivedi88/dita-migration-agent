"""
NestedSection rule - Nested sections not supported in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

NESTED_SECTION = Rule(
    name="NestedSection",
    severity=RuleSeverity.ERROR,
    message="Nested sections are not supported in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#errors",
    fix_instruction="""DITA 1.3 does not support nested sections. Sections cannot contain subsections.

VALE RULE BEHAVIOR (NestedSection.yml):
- Matches: === (level 2), ==== (level 3), ===== (level 4), ====== (level 5)
- Does NOT match: == (level 1 sections are allowed)
- Applies to: ALL content types (CONCEPT, REFERENCE, ASSEMBLY, PROCEDURE)

This means == subsections ARE allowed in CONCEPT and REFERENCE files.
Only === and deeper are forbidden by this rule.

NOTE: In PROCEDURE files, even == is forbidden — but that is caught by the
separate TaskSection rule, not NestedSection.

TO FIX:
1. Convert === subsections to == sections (flatten by one level).
   This resolves the nesting while keeping the section structure.
2. If flattening creates too many sections, convert the subsection heading
   to bold text (*Heading text*) or a description list term.
3. For deeply nested content (====, =====), consider splitting into
   separate topic files included from an assembly.
4. DO NOT use [discrete] headings — they trigger DiscreteHeading warnings.""",
    examples=[
        RuleExample(
            description="Flatten nested section from === to bold text",
            before="""= Main Topic

== First Section

=== Nested Subsection

Content here.

== Second Section""",
            after="""= Main Topic

== First Section

*Nested Subsection*

Content here.

== Second Section""",
        ),
        RuleExample(
            description="Flatten deeply nested ==== by promoting to ==",
            before="""= Main Topic

== Section A

=== Sub A1

==== Deep Nested

Some content.

== Section B""",
            after="""= Main Topic

== Section A

== Sub A1

*Deep Nested*

Some content.

== Section B""",
        ),
    ],
)
