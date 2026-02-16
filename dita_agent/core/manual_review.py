"""
Manual Review document generation.

Generates MANUAL_REVIEW.md file with AI-READY PROMPTS that users can
copy/paste directly into Cursor, Claude Code, or any AI assistant.

Each issue includes a self-contained prompt with:
- File path (using @ notation for Cursor)
- Line numbers
- Issue description
- Specific fix instructions
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dita_agent.utils.file_ops import write_file_safe, read_file_safe
from dita_agent.utils.git_ops import ensure_gitignore_updated


@dataclass
class ManualReviewItem:
    """A single item requiring manual review."""
    
    filepath: Path
    """Path to the file."""
    
    line: int
    """Line number of the issue."""
    
    rule: str
    """Rule that flagged the issue."""
    
    message: str
    """Error message."""
    
    reason: str
    """Reason why automated fix failed."""
    
    severity: str = "warning"
    """Severity: error, warning, suggestion."""
    
    context: Optional[str] = None
    """Context lines around the issue."""
    
    phase: str = "phase3"
    """Which phase generated this: phase1, phase2, phase3."""


@dataclass 
class ManualReviewReport:
    """Complete manual review report."""
    
    items: List[ManualReviewItem] = field(default_factory=list)
    """All items requiring review."""
    
    session_id: str = ""
    """Session ID for reference."""
    
    generated_at: datetime = field(default_factory=datetime.now)
    """When the report was generated."""
    
    def add_item(self, item: ManualReviewItem):
        """Add an item to the report."""
        self.items.append(item)
    
    def get_by_file(self) -> Dict[Path, List[ManualReviewItem]]:
        """Group items by file."""
        by_file: Dict[Path, List[ManualReviewItem]] = {}
        for item in self.items:
            if item.filepath not in by_file:
                by_file[item.filepath] = []
            by_file[item.filepath].append(item)
        return by_file
    
    def get_by_rule(self) -> Dict[str, List[ManualReviewItem]]:
        """Group items by rule."""
        by_rule: Dict[str, List[ManualReviewItem]] = {}
        for item in self.items:
            if item.rule not in by_rule:
                by_rule[item.rule] = []
            by_rule[item.rule].append(item)
        return by_rule
    
    def count_by_severity(self) -> Dict[str, int]:
        """Count items by severity."""
        counts: Dict[str, int] = {"error": 0, "warning": 0, "suggestion": 0}
        for item in self.items:
            sev = item.severity.lower()
            if sev in counts:
                counts[sev] += 1
        return counts


class ManualReviewGenerator:
    """
    Generates MANUAL_REVIEW.md with AI-ready prompts.
    
    Each issue is formatted as a copy-paste ready prompt for Cursor/Claude.
    """
    
    def __init__(self, project_dir: Path, session_id: str):
        """
        Initialize the generator.
        
        Args:
            project_dir: Project root directory.
            session_id: Current session ID.
        """
        self.project_dir = project_dir
        self.session_id = session_id
        self.report = ManualReviewReport(session_id=session_id)
    
    def add_item(
        self,
        filepath: Path,
        line: int,
        rule: str,
        message: str,
        reason: str,
        severity: str = "warning",
        context: Optional[str] = None,
        phase: str = "phase3",
    ):
        """Add an item requiring manual review."""
        item = ManualReviewItem(
            filepath=filepath,
            line=line,
            rule=rule,
            message=message,
            reason=reason,
            severity=severity,
            context=context,
            phase=phase,
        )
        self.report.add_item(item)
    
    def generate(self) -> Path:
        """Generate the MANUAL_REVIEW.md file."""
        ensure_gitignore_updated(self.project_dir, ".dita-agent/")
        
        output_dir = self.project_dir / ".dita-agent"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        content = self._generate_markdown()
        
        output_path = output_dir / "MANUAL_REVIEW.md"
        write_file_safe(output_path, content)
        
        return output_path
    
    def _generate_markdown(self) -> str:
        """Generate markdown content with AI-ready prompts."""
        lines = []

        # Header with clear instructions
        lines.append("# 🤖 AI-Ready Manual Review Prompts")
        lines.append("")
        lines.append("> **How to use:** Copy any prompt below and paste it directly into **Cursor**, **Claude Code**, or any AI assistant.")
        lines.append("> The prompts are self-contained and ready to use.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Session:** `{self.session_id}`")
        lines.append(f"- **Generated:** {self.report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.report.items:
            lines.append("✅ **No issues require manual review!**")
            return "\n".join(lines)

        # Calculate deduplicated count
        by_file = self.report.get_by_file()
        deduplicated_count = 0
        for filepath, items in by_file.items():
            deduplicated_count += len(self._deduplicate_items(items))

        lines.append(f"- **Total Issues:** {deduplicated_count}")
        if deduplicated_count < len(self.report.items):
            lines.append(f"  - _(Deduplicated from {len(self.report.items)} raw issues)_")
        lines.append("")

        # Quick copy section
        lines.append("## 📋 Quick Copy Prompts")
        lines.append("")
        lines.append("Each prompt below is ready to copy/paste into your AI assistant:")
        lines.append("")

        prompt_num = 1

        for filepath, items in sorted(by_file.items(), key=lambda x: str(x[0])):
            try:
                rel_path = filepath.relative_to(self.project_dir)
            except ValueError:
                rel_path = filepath

            # Deduplicate items: Group items by rule and proximity (within 5 lines)
            # This prevents duplicate prompts for the same section
            deduplicated_items = self._deduplicate_items(items)

            for item in deduplicated_items:
                # Generate the AI-ready prompt
                prompt = self._generate_prompt(item, rel_path)

                lines.append(f"### Prompt {prompt_num}: {item.rule} in `{rel_path.name}`")
                lines.append("")
                lines.append("<details>")
                lines.append("<summary>Click to expand prompt</summary>")
                lines.append("")
                lines.append("```")
                lines.append(prompt)
                lines.append("```")
                lines.append("")
                lines.append("</details>")
                lines.append("")
                lines.append("---")
                lines.append("")

                prompt_num += 1
        
        # Issues by rule summary
        lines.append("## Issues Summary")
        lines.append("")
        lines.append("| # | Rule | File | Line | Status |")
        lines.append("|---|------|------|------|--------|")

        prompt_num = 1
        for filepath, items in sorted(by_file.items(), key=lambda x: str(x[0])):
            try:
                rel_path = filepath.relative_to(self.project_dir)
            except ValueError:
                rel_path = filepath

            # Use deduplicated items for summary table too
            deduplicated_items = self._deduplicate_items(items)

            for item in deduplicated_items:
                lines.append(f"| {prompt_num} | {item.rule} | `{rel_path.name}` | {item.line} | 📋 Prompt ready |")
                prompt_num += 1
        
        lines.append("")
        
        # Resources
        lines.append("## Resources")
        lines.append("")
        lines.append("- [Red Hat Modular Documentation Guide](https://redhat-documentation.github.io/modular-docs/)")
        lines.append("- [AsciiDoc Syntax Reference](https://docs.asciidoctor.org/asciidoc/latest/syntax-quick-reference/)")
        lines.append("- [DITA Compatibility Guidelines](https://github.com/jhradilek/asciidoctor-dita-vale)")
        lines.append("")
        
        return "\n".join(lines)

    def _deduplicate_items(self, items: List[ManualReviewItem]) -> List[ManualReviewItem]:
        """
        Deduplicate manual review items from the same file.

        Groups items by rule and proximity (within 5 lines) to prevent
        duplicate prompts for the same section.

        Args:
            items: List of manual review items for a single file

        Returns:
            Deduplicated list with one item per logical section
        """
        if not items:
            return []

        # Sort by rule, then by line
        sorted_items = sorted(items, key=lambda x: (x.rule, x.line))

        deduplicated = []
        current_group: Optional[ManualReviewItem] = None

        for item in sorted_items:
            if current_group is None:
                # First item in group
                current_group = item
            elif (item.rule == current_group.rule and
                  abs(item.line - current_group.line) <= 5):
                # Same rule, within 5 lines → part of same section
                # Keep the FIRST occurrence (usually the heading)
                # Update reason to be more comprehensive if needed
                if len(item.reason) > len(current_group.reason):
                    current_group.reason = item.reason
            else:
                # Different rule or far apart → new group
                deduplicated.append(current_group)
                current_group = item

        # Don't forget the last group
        if current_group is not None:
            deduplicated.append(current_group)

        return deduplicated

    def _generate_prompt(self, item: ManualReviewItem, rel_path: Path) -> str:
        """
        Generate an AI-ready prompt for a specific issue.
        
        Each prompt is self-contained and can be copied directly into Cursor/Claude.
        """
        # Get context from file if not provided
        context = item.context
        if not context:
            context = self._get_file_context(item.filepath, item.line)
        
        # Use rule-specific prompt templates
        if item.rule == "AssemblyContents":
            return self._prompt_assembly_contents(item, rel_path, context)
        elif item.rule == "ShortDescription":
            return self._prompt_short_description(item, rel_path, context)
        elif item.rule == "RelatedLinks":
            return self._prompt_related_links(item, rel_path, context)
        elif item.rule == "LineBreak":
            return self._prompt_line_break(item, rel_path, context)
        elif item.rule == "ContentType":
            return self._prompt_content_type(item, rel_path, context)
        elif item.rule == "Callouts":
            return self._prompt_callouts(item, rel_path, context)
        elif item.rule == "ContentQuality":
            return self._prompt_content_quality(item, rel_path, context)
        else:
            return self._prompt_generic(item, rel_path, context)
    
    def _get_file_context(self, filepath: Path, line: int, context_lines: int = 5) -> str:
        """Get context lines around the issue."""
        content, error = read_file_safe(filepath)
        if error or not content:
            return "(Could not read file context)"
        
        lines = content.split('\n')
        start = max(0, line - context_lines - 1)
        end = min(len(lines), line + context_lines)
        
        context_parts = []
        for i in range(start, end):
            marker = ">>>" if i == line - 1 else "   "
            context_parts.append(f"{i+1:4d} {marker} {lines[i]}")
        
        return '\n'.join(context_parts)
    
    def _prompt_assembly_contents(self, item: ManualReviewItem, rel_path: Path, context: str) -> str:
        """Generate prompt for AssemblyContents issues."""
        # Detect the type of issue from context to give targeted guidance
        issue_type = self._classify_assembly_contents_issue(context)

        if issue_type == "misnamed_heading":
            return f"""Fix the AssemblyContents DITA compatibility issue in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}

CONTEXT (>>> marks the issue):
{context}

ROOT CAUSE: The assembly has a heading after include directives that is NOT
"Additional resources". The vale rule ONLY recognizes "Additional resources"
(exact text, case-sensitive) as valid content after includes.

INVALID headings: .Next step, .Next steps, .Additional Resources (capital R),
== Next step, or any other heading name.

WHAT TO DO:
1. Open @{rel_path}
2. Find ALL sections after the last include:: directive
3. Merge their link items into a SINGLE "Additional resources" section
4. Use this exact format:

[role="_additional-resources"]
.Additional resources

* link:URL1[Text1]
* link:URL2[Text2]

RULES:
- The heading must be EXACTLY ".Additional resources" or "== Additional resources"
- Case matters: lowercase 'r' in "resources"
- Only ONE such section is allowed
- It can ONLY contain bulleted link/xref items

Please merge and rename the sections."""

        if issue_type == "wrong_case":
            return f"""Fix the AssemblyContents DITA compatibility issue in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}

CONTEXT (>>> marks the issue):
{context}

ROOT CAUSE: The "Additional Resources" heading has wrong capitalization.
The vale rule requires EXACTLY "Additional resources" (lowercase 'r').

WHAT TO DO:
1. Open @{rel_path}
2. Change ".Additional Resources" to ".Additional resources"
   OR change "== Additional Resources" to "== Additional resources"

Please fix the capitalization."""

        # Default: prose content between/after includes
        return f"""Fix the AssemblyContents DITA compatibility issue in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}
DETAILS: {item.reason}

CONTEXT (>>> marks the issue):
{context}

ROOT CAUSE: Content other than "Additional resources" appears after include
directives. In DITA-compatible assemblies, the ONLY allowed content after
include directives is a single "Additional resources" section with links.

WHAT TO DO — choose based on what the flagged content is:

Option A: If the content is prose/paragraphs between includes:
  - DELETE if it's transitional text ("The following sections describe...")
  - MOVE to a new module if it's substantial content:
    1. Create a new file (e.g., topics/con_{rel_path.stem}-intro.adoc)
    2. Add :_mod-docs-content-type: CONCEPT and [role="_abstract"]
    3. Replace the prose with: include::topics/con_{rel_path.stem}-intro.adoc[leveloffset=+1]

Option B: If the content is a NOTE/WARNING/IMPORTANT block:
  - Move it into the last included topic module

Option C: If the content is a misnamed section (e.g., .Next step):
  - Merge its links into a single .Additional resources section

IMPORTANT:
- Keep all ifdef/endif conditional blocks in place
- Keep all include:: directives unchanged

Please make these changes."""

    def _classify_assembly_contents_issue(self, context: str) -> str:
        """Classify the type of AssemblyContents issue from context lines."""
        if not context:
            return "prose"
        context_lower = context.lower()
        # Check for misnamed headings like .Next step, == Next step, etc.
        import re
        if re.search(r'>>>\s*(?:={2,}\s+|\.{1,2})(?:next\s+steps?)', context_lower):
            return "misnamed_heading"
        # Check for wrong case: .Additional Resources (capital R)
        if re.search(r'>>>\s*(?:={2,}\s+|\.{1,2})additional\s+Resources', context):
            return "wrong_case"
        # Check for any non-"Additional resources" heading
        if re.search(r'>>>\s*(?:={2,}\s+|\.{1,2})(?!additional\s+resources\s*$)[a-z]', context_lower):
            return "misnamed_heading"
        return "prose"
    
    def _prompt_short_description(self, item: ManualReviewItem, rel_path: Path, context: str) -> str:
        """Generate prompt for ShortDescription issues."""
        if "SNIPPET" in item.reason.upper():
            return f"""INFORMATION: No action needed for @{rel_path}

This file is a SNIPPET type, which does not require a [role="_abstract"] paragraph.
SNIPPET files are reusable content fragments, not standalone topics.

The DITA agent correctly skipped this file.

STATUS: ✅ No changes required"""

        # Check for semantic validation failures
        if "ends with ':'" in item.reason or "colon" in item.reason.lower():
            return f"""Fix the ShortDescription semantic issue in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}
PROBLEM: {item.reason}

CONTEXT (>>> marks the paragraph):
{context}

🚫 CRITICAL ISSUE: The paragraph ends with a colon (:), making it INCOMPLETE.

In DITA, the [role="_abstract"] paragraph becomes the <shortdesc> element.
If it ends with a colon, it implies a list follows - but DITA <shortdesc>
cannot contain lists! This creates a BROKEN short description.

WHAT TO DO:

Step 1: REWRITE the paragraph to be SELF-CONTAINED
- Read the paragraph AND the bullets/list that follows it
- Incorporate the key information into a complete sentence
- Remove the colon and any reference to "the following", "if:", etc.

Step 2: Add [role="_abstract"]
- Once the paragraph is complete and standalone, add [role="_abstract"] before it

Step 3: Keep the detailed list below (optional)
- You can keep the bullets/list below for additional details

EXAMPLE:

Before:
= Archiving performance analysis
You can skip archiving if:
* The DSOs are already present
* Both systems match

After:
= Archiving performance analysis

[role="_abstract"]
You can skip archiving if the DSOs are already present on the target
system or if both systems have matching binaries and kernel versions.

You can skip archiving in the following cases:
* The DSOs are already present on the target system
* Both systems match (same binaries, kernel versions)

KEY RULE: The [role="_abstract"] paragraph must make COMPLETE sense
when read alone, without any following content!

Please rewrite the paragraph and add [role="_abstract"]."""

        # Check for forward references
        if any(ref in item.reason.lower() for ref in ["the following", "forward reference", "below"]):
            return f"""Fix the ShortDescription forward reference issue in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}
PROBLEM: {item.reason}

CONTEXT (>>> marks the paragraph):
{context}

🚫 ISSUE: The paragraph references "the following" or similar forward references.

In DITA, the [role="_abstract"] paragraph becomes the <shortdesc> element
which appears ALONE in search results, topic lists, and metadata.
If it says "the following steps" but the steps aren't included, it's BROKEN.

WHAT TO DO:

1. REWRITE the paragraph to describe WHAT the content covers, not HOW it's organized
2. Remove references to "the following", "below", "as shown", etc.
3. Make it a standalone summary of the topic
4. Then add [role="_abstract"]

EXAMPLE:

Before:
= Configuring the system
This procedure includes the following steps:
* Install packages
* Configure settings

After:
= Configuring the system

[role="_abstract"]
This procedure installs required packages, configures system settings,
and validates the configuration.

.Procedure
* Install packages...
* Configure settings...

Please rewrite the paragraph and add [role="_abstract"]."""

        # Default ShortDescription prompt
        return f"""Fix the ShortDescription DITA compatibility issue in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}

CONTEXT (>>> marks the area):
{context}

WHAT TO DO:
1. Open the file @{rel_path}
2. Find the first paragraph AFTER the document title (= Title)
3. Ensure it's a SELF-CONTAINED summary (no colons, no "the following", etc.)
4. Add [role="_abstract"] on the line immediately before that paragraph

EXAMPLE:
Before:
= My Document Title

This document describes how to configure the feature.

After:
= My Document Title

[role="_abstract"]
This document describes how to configure the feature.

CRITICAL RULES:
- The paragraph must NOT end with a colon (:)
- The paragraph must NOT reference "the following", "below", etc.
- The paragraph must make complete sense when read ALONE

Please add the [role="_abstract"] attribute."""

    def _prompt_related_links(self, item: ManualReviewItem, rel_path: Path, context: str) -> str:
        """Generate prompt for RelatedLinks issues (non-link content in Additional resources)."""
        return f"""Fix the RelatedLinks DITA compatibility issue in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}
DETAILS: {item.reason}

CONTEXT (>>> marks the issue):
{context}

🚨 CRITICAL DITA RULE: Additional resources can ONLY contain LINKS

DITA's <related-links> element can ONLY contain:
- Bulleted links: * link:https://example.com[Text]
- Cross-references: * xref:file.adoc[Text]
- Email links: * mailto:email@example.com[Text]

FORBIDDEN in Additional resources:
- ❌ Plain text without link: macro
- ❌ Command references like `perf help`
- ❌ Man page references like "see man page"
- ❌ NOTE/TIP/IMPORTANT blocks
- ❌ Any content that's not a clickable link

⚠️ IMPORTANT: DO NOT DELETE THE "Additional resources" SECTION!
Only modify or move the ITEMS within the section that are not valid links.
Keep the section header and any valid links intact.

WHAT TO DO WITH NON-LINK ITEMS:

Option 1: Convert to actual link (if you know the URL)
  Example: * link:https://perf.wiki.kernel.org/[Perf documentation]
  Note: Only use this if you KNOW the correct URL!

Option 2: Move to a NOTE/TIP block in the last module
  Example: Add to end of the last included module:
  [NOTE]
  ====
  For command-specific help, run `perf help _COMMAND_` in your terminal.
  ====

Option 3: Move to body text if it's procedural help
  Example: Add as a paragraph in relevant module:
  "For command-specific help, run `perf help _COMMAND_`."

Option 4: Delete the non-link item if redundant
  Example: If there's already a link to the man page, delete the text reference

MAKE YOUR DECISION:
1. Open @{rel_path}
2. Find the Additional resources section
3. KEEP the section header: [role="_additional-resources"] and == Additional resources
4. For each non-link item, choose Option 1, 2, 3, or 4
5. Apply the changes to the ITEMS ONLY, not the section itself

RESULT: The Additional resources section should remain, but contain only valid links.

Please fix this issue by choosing the most appropriate option for each non-link item."""

    def _prompt_line_break(self, item: ManualReviewItem, rel_path: Path, context: str) -> str:
        """Generate prompt for LineBreak issues (intentional formatting)."""
        return f"""Review the LineBreak formatting in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}
DETAILS: {item.reason}

CONTEXT (>>> marks the issue):
{context}

This appears to be INTENTIONAL FORMATTING (e.g., CLI arguments or code examples).

OPTIONS:
1. **Keep as-is** if the line breaks are necessary for readability in source
2. **Convert to literal block** if this is code/CLI content:
   [literal]
   --arg1
   --arg2
   --arg3

3. **Use passthrough** if you need exact formatting preserved:
   ++++
   content here
   ++++

Please review and choose the best option for this content."""
    
    def _prompt_content_type(self, item: ManualReviewItem, rel_path: Path, context: str) -> str:
        """Generate prompt for ContentType issues."""
        return f"""Fix the ContentType issue in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}

CONTEXT:
{context}

WHAT TO DO:
1. Open the file @{rel_path}
2. Add the :_mod-docs-content-type: attribute after the first line
3. Choose the correct type based on the file content:
   - ASSEMBLY: For files that primarily include other modules
   - PROCEDURE: For step-by-step task instructions
   - CONCEPT: For explanatory/background information
   - REFERENCE: For reference tables, lists, specifications
   - SNIPPET: For reusable content fragments

EXAMPLE:
:_mod-docs-content-type: PROCEDURE

Please add the appropriate content type attribute."""
    
    def _prompt_callouts(self, item: ManualReviewItem, rel_path: Path, context: str) -> str:
        """Generate prompt for Callouts issues."""
        return f"""Fix the Callouts issue in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}

CONTEXT:
{context}

WHAT TO DO:
1. Open the file @{rel_path}
2. Find the callout markers (like <1>, <2>, etc.)
3. Convert them to DITA-compatible format

The callout numbers in code blocks should use:
- CO markers in the code: // <1>
- Callout list after the block:
  <1> Explanation for first callout
  <2> Explanation for second callout

Please review and fix the callout formatting."""
    
    def _prompt_content_quality(self, item: ManualReviewItem, rel_path: Path, context: str) -> str:
        """Generate prompt for content quality issues (NOT vale findings)."""
        return f"""CONTENT QUALITY SUGGESTION for @{rel_path}

NOTE: This is NOT a Vale linting finding. This is a content quality check
performed by the DITA agent. The file already has [role="_abstract"] and
passes Vale validation. This suggestion is about improving the abstract
text for DITA short description quality.

ISSUE: {item.reason}
LINE: {item.line}

CONTEXT (>>> marks the issue):
{context}

WHAT TO DO:
1. Open the file @{rel_path}
2. Go to line {item.line}
3. Review the [role="_abstract"] paragraph
4. If the abstract text could be improved, rewrite it to be:
   - A complete sentence (not ending with a colon)
   - Self-contained (no forward references like "the following")
   - 10-75 words long
   - Action-oriented (tell the user what they can do)
5. If the abstract is acceptable as-is, you may skip this suggestion

This is an OPTIONAL improvement, not a required fix."""

    def _prompt_generic(self, item: ManualReviewItem, rel_path: Path, context: str) -> str:
        """Generate generic prompt for other issues."""
        return f"""Fix the {item.rule} DITA compatibility issue in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}
DETAILS: {item.reason}

CONTEXT (>>> marks the issue):
{context}

WHAT TO DO:
1. Open the file @{rel_path}
2. Go to line {item.line}
3. Review the issue described above
4. Make the necessary changes to fix the DITA compatibility issue

RESOURCES:
- DITA Vale Rules: https://github.com/jhradilek/asciidoctor-dita-vale
- Red Hat Modular Docs: https://redhat-documentation.github.io/modular-docs/

Please fix this issue."""
    
    def _get_severity_icon(self, severity: str) -> str:
        """Get icon for severity level."""
        icons = {
            "error": "🔴",
            "warning": "🟡", 
            "suggestion": "🔵",
        }
        return icons.get(severity.lower(), "⚪")
    
    def has_items(self) -> bool:
        """Check if there are items requiring review."""
        return len(self.report.items) > 0
    
    def get_summary(self) -> str:
        """Get a brief summary of items."""
        if not self.report.items:
            return "No issues require manual review"
        
        counts = self.report.count_by_severity()
        parts = []
        if counts['error'] > 0:
            parts.append(f"{counts['error']} errors")
        if counts['warning'] > 0:
            parts.append(f"{counts['warning']} warnings")
        if counts['suggestion'] > 0:
            parts.append(f"{counts['suggestion']} suggestions")
        
        return f"{len(self.report.items)} issues require manual review: " + ", ".join(parts)
