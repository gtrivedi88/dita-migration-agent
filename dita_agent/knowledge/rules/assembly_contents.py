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
    fix_instruction="""In assemblies, include directives can be followed only by the 'Additional resources' section.

TO FIX:
1. Remove plain text content placed between include:: directives
2. Move that content to separate module files that get included
3. Only .Additional resources section is allowed after includes

CRITICAL - DO NOT REMOVE:
- Conditional blocks (ifdef::, ifndef::, endif::) - these are STRUCTURAL elements
- Include directives inside conditionals - these are intentional
- Context-setting variables (:context:, :parent-context:)
- Attribute includes like include::../_artifacts/document-attributes-global.adoc[]

WHAT TO REMOVE:
- Plain paragraph text between include directives
- Headings between includes (move to separate modules)

Assemblies should primarily contain:
- Title and metadata
- Context setting (brief intro paragraph with [role="_abstract"])
- Conditional blocks with includes (for preview/build variants)
- include:: directives for modules
- Optional .Additional resources section at the end""",
    examples=[
        RuleExample(
            description="Remove text content between includes, but preserve conditionals",
            before="""= Assembly Title
:_mod-docs-content-type: ASSEMBLY

ifdef::preview[]
include::../_artifacts/document-attributes-global.adoc[]
endif::preview[]

include::modules/module-a.adoc[leveloffset=+1]

Some text between includes that should be in a module.

include::modules/module-b.adoc[leveloffset=+1]""",
            after="""= Assembly Title
:_mod-docs-content-type: ASSEMBLY

ifdef::preview[]
include::../_artifacts/document-attributes-global.adoc[]
endif::preview[]

include::modules/module-a.adoc[leveloffset=+1]
include::modules/module-b.adoc[leveloffset=+1]""",
        ),
    ],
)
