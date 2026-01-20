"""
ShortDescription rule - Add [role="_abstract"] for DITA short description.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

SHORT_DESCRIPTION = Rule(
    name="ShortDescription",
    severity=RuleSeverity.WARNING,
    message='Assign [role="_abstract"] to a paragraph to use it as <shortdesc> in DITA.',
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    skip_for_types=["SNIPPET"],  # Snippets don't need abstracts
    fix_instruction="""DITA 1.3 requires a short description (<shortdesc>) for topics.

CRITICAL SEMANTIC REQUIREMENTS FOR SHORT DESCRIPTIONS:
1. Must be SELF-CONTAINED and COMPLETE (no dependency on following content)
2. Must NOT end with a colon (:) - this indicates an incomplete thought
3. Must NOT reference "the following", "below", "if:", "when:", "where:", etc.
4. Must make complete sense when read ALONE (bullets/lists won't be included in <shortdesc>)
5. Should be 1-3 sentences (10-75 words) that summarize the entire topic

VALIDATION TEST - READ THIS BEFORE FIXING:
Read ONLY the paragraph you want to mark as [role="_abstract"].
Ask yourself: "Does this make complete sense on its own, without any following content?"
If the answer is NO → You MUST rewrite the paragraph first, then add [role="_abstract"]

COMMON PROBLEMS THAT REQUIRE REWRITING:

Problem 1: Paragraph ends with colon
  ❌ BAD:  You can do X if:
           * Condition 1
           * Condition 2

  In DITA, only "You can do X if:" becomes the short description. This is BROKEN!

  ✅ GOOD: First, rewrite to be complete:
           "You can do X if condition 1 or condition 2 is met."

           Then add [role="_abstract"]:
           [role="_abstract"]
           You can do X if condition 1 or condition 2 is met.

           Then keep the detailed list below for reference.

Problem 2: References "the following" or similar forward references
  ❌ BAD:  This procedure includes the following steps:
           * Step 1
           * Step 2

  ✅ GOOD: Rewrite to be self-contained:
           "This procedure configures X, validates Y, and enables Z."

Problem 3: Incomplete without following bullets
  ❌ BAD:  You can skip archiving if:
           * DSOs are present
           * Systems match

  ✅ GOOD: Rewrite inline:
           "You can skip archiving if the DSOs are already present or both systems have matching binaries."

           Then optionally keep bullets below for details.

TO FIX:

Step 1: VALIDATE the paragraph
- Find the FIRST content paragraph after title/conditionals
- Check if it ends with `:` → If YES, must rewrite
- Check if it contains "the following", "if:", "when:" → If YES, must rewrite
- Check if it makes sense alone → If NO, must rewrite

Step 2: REWRITE if necessary
- Incorporate key information from bullets/following content into the paragraph
- Make it a complete, standalone sentence or two
- Remove forward references
- Ensure it doesn't end with a colon

Step 3: ADD [role="_abstract"]
- Add on a line BY ITSELF before the now-complete paragraph
- Do NOT move content around, just add the attribute line

Step 4: VERIFY
- Read ONLY the [role="_abstract"] paragraph
- Does it make complete sense? ✅
- Would a reader understand the topic from this alone? ✅

PLACEMENT ORDER:
1. = Title
2. :_mod-docs-content-type: TYPE
3. ifdef::condition[] / include:: directives / endif::[]
4. [role="_abstract"]  <-- ADD HERE
5. First paragraph (self-contained, complete summary)
6. Optional: Keep detailed bullets/lists below

WRONG APPROACHES (DO NOT DO THESE):

❌ WRONG: Just add [role="_abstract"] to a paragraph ending with `:`
   Result: Broken short description in DITA

❌ WRONG: Add [role="_abstract"] to a paragraph that says "the following"
   Result: Short description references content that won't be included

❌ WRONG: Add [role="_abstract"] to an incomplete sentence
   Result: Grammatically broken short description""",
    examples=[
        RuleExample(
            description="Basic topic needs abstract",
            before="""= Topic title

A paragraph.""",
            after="""= Topic title

[role="_abstract"]
A paragraph."""
        ),
        RuleExample(
            description="Topic with conditionals",
            before="""= Installing the component

ifdef::preview[]
include::../attributes.adoc[]
endif::preview[]

This topic describes how to install the component.""",
            after="""= Installing the component

ifdef::preview[]
include::../attributes.adoc[]
endif::preview[]

[role="_abstract"]
This topic describes how to install the component."""
        ),
    ],
)
