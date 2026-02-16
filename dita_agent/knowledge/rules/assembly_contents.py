"""
AssemblyContents rule - Assembly include directive placement.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

ASSEMBLY_CONTENTS = Rule(
    name="AssemblyContents",
    severity=RuleSeverity.WARNING,
    message="Content between or after include directives is not supported.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    applicable_types=["ASSEMBLY"],
    fix_instruction="""In assemblies, the ONLY content allowed after include directives is an
"Additional resources" section. Everything else triggers this violation.

VALE RULE DETAILS (AssemblyContents.yml):
The vale rule recognizes "Additional resources" via this EXACT regex:
    ^(?:={2,}[ \\t]+|\\.{1,2})Additional resources[ \\t]*$

This means:
- VALID: `.Additional resources` or `== Additional resources`
- INVALID: `.Additional Resources` (capital R — case-sensitive!)
- INVALID: `.Next step` or `== Next step` (not "Additional resources")
- INVALID: `.Next steps` or any other heading name
- INVALID: Any prose, paragraphs, or non-link content after includes

COMMON MISTAKES AND FIXES:

1. **Wrong heading name** (e.g., `.Next step`, `.Next steps`)
   The vale rule ONLY recognizes "Additional resources" as valid after includes.
   FIX: Merge the links from the misnamed section into a single
   "Additional resources" section. Use either `.Additional resources`
   or `== Additional resources` as the heading.

2. **Wrong case** (e.g., `.Additional Resources` with capital R)
   The regex is case-sensitive.
   FIX: Change to `.Additional resources` (lowercase 'r').

3. **Multiple "Additional resources"-like sections**
   If the assembly has both `.Next step` and `.Additional resources`,
   merge all links into a single `.Additional resources` section.

4. **Prose content between includes**
   FIX: DELETE if transitional/redundant text. If substantial, move to
   a new CONCEPT module and include it from the assembly.

5. **NOTE/WARNING blocks after includes**
   FIX: Move into the last included topic module, not the assembly.

WHAT IS ALLOWED after includes:
- `[role="_additional-resources"]` (role attribute — not flagged)
- `.Additional resources` or `== Additional resources` (exact text)
- Bulleted link items: `* link:URL[text]` or `* xref:id[text]`
- Empty lines, attribute definitions, conditional blocks, ID/role attributes

WHAT IS NOT ALLOWED after includes:
- Any heading other than "Additional resources"
- Plain text paragraphs
- NOTE/TIP/IMPORTANT/WARNING blocks
- Code blocks or examples

CRITICAL - DO NOT REMOVE:
- Conditional blocks (ifdef::, ifndef::, endif::)
- Include directives inside conditionals
- Context-setting variables (:context:, :parent-context:)
- Attribute includes (e.g., include::../_artifacts/document-attributes-global.adoc[])""",
    examples=[
        RuleExample(
            description="Merge misnamed 'Next step' section into 'Additional resources'",
            before="""= About the product
:_mod-docs-content-type: ASSEMBLY

include::topics/con_overview.adoc[leveloffset=+1]

include::topics/con_features.adoc[leveloffset=+1]

[role="_additional-resources"]
.Next step

* link:https://example.com/getting-started[Getting Started Guide].

[role="_additional-resources"]
.Additional Resources

* link:https://example.com/docs[Product Documentation]""",
            after="""= About the product
:_mod-docs-content-type: ASSEMBLY

include::topics/con_overview.adoc[leveloffset=+1]

include::topics/con_features.adoc[leveloffset=+1]

[role="_additional-resources"]
.Additional resources

* link:https://example.com/getting-started[Getting Started Guide]
* link:https://example.com/docs[Product Documentation]""",
        ),
        RuleExample(
            description="Fix wrong case in 'Additional Resources' heading",
            before="""= Assembly Title
:_mod-docs-content-type: ASSEMBLY

include::modules/module-a.adoc[leveloffset=+1]

[role="_additional-resources"]
.Additional Resources

* link:https://example.com[Example]""",
            after="""= Assembly Title
:_mod-docs-content-type: ASSEMBLY

include::modules/module-a.adoc[leveloffset=+1]

[role="_additional-resources"]
.Additional resources

* link:https://example.com[Example]""",
        ),
        RuleExample(
            description="Remove text content between includes",
            before="""= Assembly Title
:_mod-docs-content-type: ASSEMBLY

include::modules/module-a.adoc[leveloffset=+1]

Some text between includes that should be in a module.

include::modules/module-b.adoc[leveloffset=+1]""",
            after="""= Assembly Title
:_mod-docs-content-type: ASSEMBLY

include::modules/module-a.adoc[leveloffset=+1]

include::modules/module-b.adoc[leveloffset=+1]""",
        ),
    ],
)
