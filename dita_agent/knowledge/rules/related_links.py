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
    fix_instruction="""In DITA 1.3, the <related-links> element can ONLY contain actual links.

WHAT COUNTS AS A LINK IN DITA:
✅ VALID links (will convert to <related-links>):
- link:https://example.com[Link text] - External URL with link: macro
- link:https://docs.example.com/guide[Documentation] - External docs
- xref:other-file.adoc[Cross reference] - Internal cross-reference
- xref:../modules/topic.adoc[Module topic] - Relative xref

❌ NOT VALID as links (must be removed or converted):
- Plain text: "See the documentation" - NO link: macro
- Command references: `perf help COMMAND` - Formatted code, not a link
- Man page references: `perf`(1) man page on your system - Local reference
- Formatted text: `command --option` - Code formatting, not a link
- Descriptions: "For more information..." - Prose without URL

CRITICAL: The link: or xref: macro MUST be present!
Just formatting text with backticks ` or bold * does NOT make it a link.

🚨 CRITICAL RULE: Only fix what you can SEE and VERIFY
- DO NOT search for URLs on the internet
- DO NOT assume URLs exist
- DO NOT invent or guess link destinations
- ONLY work with links that are ALREADY in the file

TO FIX - ANALYZE EACH LIST ITEM:

Step 1: Identify what's in the Additional Resources section
- Look at each `* ...` list item
- Check if it contains `link:` or `xref:` macro

Step 2: For items WITH link: or xref: macros
✅ ACTION: Keep them! Just ensure they're formatted correctly.
- Clean up any extra prose around the link
- Ensure link: macro has proper URL syntax
- These are already DITA-compatible

Step 3: For items WITHOUT link: or xref: macros
❌ ACTION: Flag for MANUAL REVIEW - DO NOT attempt to fix!

WHY? Because the LLM cannot:
- Search the internet for URLs
- Assume where documentation lives
- Guess correct link destinations
- Know if a URL exists for this content

MANUAL REVIEW GUIDANCE to provide:
"This item in Additional resources is not a link and cannot be automatically converted:
- Item: [show the text]
- Options for the author:
  1. Convert to a link (if you know the URL)
  2. Move to a NOTE or IMPORTANT block in the last module
  3. Delete if redundant
  4. Convert to body text if it's procedural help"

Step 4: If NO link: or xref: macros exist in Additional Resources
❌ ACTION: Flag ENTIRE section for manual review
GUIDANCE: "Additional resources section contains no links. All items need author review to either add links or move content elsewhere."

EXAMPLES:

Example 1 - Command reference (NO link macro):
  ❌ Current: * `perf help _COMMAND_`
  ❌ LLM Action: CANNOT fix - no URL available
  ✅ Correct Action: Flag for MANUAL_REVIEW with guidance:
     "Options: (1) Delete if redundant, (2) Move to NOTE in last module,
      (3) Convert to body text"

Example 2 - Generic text (NO link macro):
  ❌ Current: * The Kubernetes documentation
  ❌ LLM Action: CANNOT fix - no URL provided
  ✅ Correct Action: Flag for MANUAL_REVIEW with guidance:
     "Author needs to either: (1) Add URL if known, (2) Delete if generic"

Example 3 - Man page reference (NO link macro):
  ❌ Current: * `perf`(1) man page on your system
  ❌ LLM Action: CANNOT fix - local reference, no URL
  ✅ Correct Action: Flag for MANUAL_REVIEW with guidance:
     "Options: (1) Add link to online man page if available,
      (2) Delete (users know how to access local man pages)"

Example 4 - Already has link macro:
  ✅ Current: * link:https://example.com[Example]
  ✅ LLM Action: Keep as-is (already valid!)

Example 5 - Link with extra prose:
  ⚠️ Current: * For more info, see link:https://example.com[Documentation]
  ✅ LLM Fix: * link:https://example.com[Documentation]
  (Remove the prose, keep the link)

WRONG APPROACHES (DO NOT DO THESE):

❌ WRONG #1: Search or assume URLs exist
   Example: `perf documentation` → * link:https://perf.wiki.kernel.org/[Perf Wiki]
   Why wrong: LLM cannot search the internet or assume URL locations!
   Correct: Flag for manual review

❌ WRONG #2: Guess or invent link destinations
   Example: `man page` → * link:https://man7.org/linux/man-pages/man1/perf.1.html[man page]
   Why wrong: LLM should not assume which man page or where it's hosted!
   Correct: Flag for manual review

❌ WRONG #3: Make text more verbose without link
   Example: `perf help` → "Use perf help to get command help"
   Why wrong: Still not a link! Doesn't solve the DITA problem.
   Correct: Flag for manual review

❌ WRONG #4: Add link: to non-URL text
   Example: * link:`perf help COMMAND`
   Why wrong: Not a valid URL, link: requires https:// or file path
   Correct: Flag for manual review

❌ WRONG #5: Delete items without author input
   Example: Remove all non-link items silently
   Why wrong: Content might be important, needs author decision
   Correct: Flag for manual review with options

VERIFICATION:
After fixing, every remaining list item should:
- Start with `* link:https://` OR `* xref:`
- Contain actual clickable link in DITA output
- Have NO plain text items without link macros""",
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
