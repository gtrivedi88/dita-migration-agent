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

🚨 CRITICAL DITA RULE: Additional resources can ONLY contain LINKS
DITA's <related-links> element (which Additional resources maps to) can ONLY contain:
- Bulleted links with link: macro (e.g., * link:https://example.com[Text])
- Bulleted xref: macros (e.g., * xref:file.adoc[Text])
- Bulleted mailto: links

FORBIDDEN in Additional resources:
- ❌ NO NOTE blocks
- ❌ NO TIP/IMPORTANT/WARNING blocks
- ❌ NO paragraphs or plain text
- ❌ NO anything except bulleted links

ANALYZE THE CONTENT FIRST:
Before removing or moving content, determine what it is:

1. **Command help / Usage instructions** (e.g., "For command-specific help, run...")
   → ❌ CANNOT go in Additional resources (not a link!)
   → ✅ BEST OPTION: DELETE entirely
      Why? Because the man page link already provides this info
      Example: If there's already "* link:...perf(1) man page", then "run perf help"
               is redundant - just delete it
   → ✅ ALTERNATIVE: Convert to link if there's a relevant URL
      Example: link:https://perf.wiki.kernel.org/index.php/Tutorial#Commands[perf command reference]

2. **Introductory/explanatory text**
   → DELETE if it's just transitional text
   → If substantial, move to a new CONCEPT module with [role="_abstract"]

3. **Prerequisites or warnings**
   → DELETE if already covered in prerequisite sections of modules
   → If critical, flag for manual review to add to appropriate module

4. **Examples or code snippets**
   → DELETE (should be in module files, not assemblies)

TO FIX:
1. ANALYZE: What is the purpose of this content?
2. DECIDE: Is it redundant? Can it be deleted? Is there a link alternative?
3. APPLY: DELETE in most cases (assemblies should be minimal)

CRITICAL - DO NOT REMOVE:
- Conditional blocks (ifdef::, ifndef::, endif::) - these are STRUCTURAL elements
- Include directives inside conditionals - these are intentional
- Context-setting variables (:context:, :parent-context:)
- Attribute includes like include::../_artifacts/document-attributes-global.adoc[]

PREFERRED SOLUTIONS (in order):
1. **Best**: DELETE the content (most assembly content is redundant)
2. **Good**: Convert to a link if there's a relevant URL
3. **Acceptable**: Flag for manual review if unclear

Assemblies should primarily contain:
- Title and metadata
- Context setting (brief intro paragraph with [role="_abstract"])
- Conditional blocks with includes (for preview/build variants)
- include:: directives for modules
- Optional .Additional resources section at the end (LINKS ONLY!)""",
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
        RuleExample(
            description="Delete redundant command help text (man page link already exists)",
            before="""= Analyzing performance

include::modules/module-a.adoc[leveloffset=+1]
include::modules/module-b.adoc[leveloffset=+1]

For command-specific help, run `perf help _COMMAND_` in your terminal.

[role="_additional-resources"]
== Additional resources
* link:https://man7.org/linux/man-pages/man1/perf.1.html[perf(1) man page]""",
            after="""= Analyzing performance

include::modules/module-a.adoc[leveloffset=+1]
include::modules/module-b.adoc[leveloffset=+1]

[role="_additional-resources"]
== Additional resources
* link:https://man7.org/linux/man-pages/man1/perf.1.html[perf(1) man page]""",
        ),
    ],
)
