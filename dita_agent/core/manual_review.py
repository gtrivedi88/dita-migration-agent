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
        lines.append(f"- **Total Issues:** {len(self.report.items)}")
        lines.append("")
        
        if not self.report.items:
            lines.append("✅ **No issues require manual review!**")
            return "\n".join(lines)
        
        # Quick copy section
        lines.append("## 📋 Quick Copy Prompts")
        lines.append("")
        lines.append("Each prompt below is ready to copy/paste into your AI assistant:")
        lines.append("")
        
        by_file = self.report.get_by_file()
        prompt_num = 1
        
        for filepath, items in sorted(by_file.items(), key=lambda x: str(x[0])):
            try:
                rel_path = filepath.relative_to(self.project_dir)
            except ValueError:
                rel_path = filepath
            
            for item in sorted(items, key=lambda x: x.line):
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
            
            for item in sorted(items, key=lambda x: x.line):
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
        elif item.rule == "LineBreak":
            return self._prompt_line_break(item, rel_path, context)
        elif item.rule == "ContentType":
            return self._prompt_content_type(item, rel_path, context)
        elif item.rule == "Callouts":
            return self._prompt_callouts(item, rel_path, context)
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
        return f"""Fix the AssemblyContents DITA compatibility issue in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}
DETAILS: {item.reason}

CONTEXT (>>> marks the issue):
{context}

WHAT TO DO:
1. Open the file @{rel_path}
2. Find the plain text content between include:: directives (shown above)
3. This content needs to be moved to a separate module file
4. Create a new module file (e.g., modules/con-{rel_path.stem}-overview.adoc)
5. Move the paragraph content to the new module
6. Replace the removed content with: include::modules/con-{rel_path.stem}-overview.adoc[leveloffset=+1]

IMPORTANT:
- Do NOT delete the content - move it to a new file
- Keep all ifdef/endif conditional blocks in place
- The new module should have proper DITA attributes (:_mod-docs-content-type: CONCEPT)

Please make these changes."""
    
    def _prompt_short_description(self, item: ManualReviewItem, rel_path: Path, context: str) -> str:
        """Generate prompt for ShortDescription issues."""
        if "SNIPPET" in item.reason.upper():
            return f"""INFORMATION: No action needed for @{rel_path}

This file is a SNIPPET type, which does not require a [role="_abstract"] paragraph.
SNIPPET files are reusable content fragments, not standalone topics.

The DITA agent correctly skipped this file.

STATUS: ✅ No changes required"""
        
        return f"""Fix the ShortDescription DITA compatibility issue in @{rel_path}

ISSUE: {item.message}
LINE: {item.line}

CONTEXT (>>> marks the area):
{context}

WHAT TO DO:
1. Open the file @{rel_path}
2. Find the first paragraph AFTER the document title (= Title)
3. Add [role="_abstract"] on the line immediately before that paragraph

EXAMPLE:
Before:
= My Document Title

This is the first paragraph that describes the topic.

After:
= My Document Title

[role="_abstract"]
This is the first paragraph that describes the topic.

Please add the [role="_abstract"] attribute."""
    
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
