"""
Fixer Registry - Manages all fixers organized by tier.

Tiers:
1. PATTERN: No LLM needed - regex/template based (~60% of issues)
2. TEMPLATE: LLM once per rule, then propagate pattern (~30% of issues)
3. LLM: LLM for each instance (~10% of issues)

The registry routes issues to the appropriate fixer based on rule type.
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from dita_agent.core.memory import SessionMemoryV2, LearnedFix, FixStatus
from dita_agent.llm.client import LLMClient
from dita_agent.knowledge import get_rule, get_prompt_context
from dita_agent.fixers.table_fixer import TableLineBreakFixer


class FixerTier(Enum):
    """Fixer tiers by LLM usage."""
    PATTERN = 1      # No LLM - deterministic
    TEMPLATE = 2     # LLM once, then propagate
    LLM = 3          # LLM each time


@dataclass
class FixResult:
    """Result of a fix attempt."""
    success: bool
    old_string: Optional[str] = None
    new_string: Optional[str] = None
    error: Optional[str] = None
    method: str = "unknown"  # "pattern", "template", "llm", "template_propagation"
    tokens_used: int = 0


def validate_fix_scope(
    content: str,
    old_string: str,
    issue_line: int,
    tolerance: int = 10,
) -> bool:
    """
    Validate that an LLM-proposed fix is scoped to the reported issue location.

    Prevents unsolicited edits where the LLM modifies content far from the
    reported issue line (e.g., backtick-quoting a proper noun on line 33
    when the issue was on line 25).

    Args:
        content: Full file content.
        old_string: The text the LLM wants to replace.
        issue_line: The line number (1-based) where vale reported the issue.
        tolerance: How many lines away from the issue line the fix can be.

    Returns:
        True if the fix overlaps with or is near the issue line.
    """
    # Find where old_string starts in the content
    idx = content.find(old_string)
    if idx == -1:
        return False

    # Calculate the line range of old_string
    fix_start_line = content[:idx].count('\n') + 1
    fix_end_line = fix_start_line + old_string.count('\n')

    # Check if the fix overlaps with or is near the issue line
    return (fix_start_line - tolerance) <= issue_line <= (fix_end_line + tolerance)


class BaseFixer(Protocol):
    """Protocol for all fixers."""
    
    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        """Fix a single issue."""
        ...


# =============================================================================
# TIER 1: Pattern Fixers (No LLM)
# =============================================================================

class PatternFixer:
    """
    Base class for pattern-based fixers.
    
    These fixers use regex patterns to find and fix issues.
    No LLM needed - 100% deterministic.
    """
    
    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        """Override in subclass."""
        raise NotImplementedError


class LineBreakFixer(PatternFixer):
    """Fix hard line breaks (` +` at end of lines).
    
    For simple cases (outside tables), uses pattern replacement.
    For table contexts, returns needs_llm=True to escalate to LLM.
    """
    
    def _is_inside_table(self, lines: list, line_num: int) -> bool:
        """Check if a line is inside a table block (between |=== markers)."""
        in_table = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('|==='):
                in_table = not in_table
            if i == line_num - 1:
                return in_table
        return False
    
    def _is_table_cell_line(self, line: str) -> bool:
        """Check if line appears to be part of a table cell."""
        return line.strip().startswith('|')
    
    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        lines = content.split('\n')
        if line < 1 or line > len(lines):
            return FixResult(success=False, error="Invalid line number", method="pattern")
        
        target_line = lines[line - 1]
        
        # For table contexts, signal that LLM should handle this
        # (Pattern fixer can't properly restructure table cells)
        if self._is_inside_table(lines, line) or self._is_table_cell_line(target_line):
            return FixResult(
                success=False,
                error="TABLE_CONTEXT_NEEDS_LLM",  # Special marker for escalation
                method="pattern"
            )
        
        # Pattern 1: ` +` at end of line (outside tables) - simple removal
        if target_line.rstrip().endswith(' +'):
            old_string = target_line
            new_string = target_line.rstrip()[:-2]
            return FixResult(
                success=True,
                old_string=old_string,
                new_string=new_string,
                method="pattern",
            )
        
        # Pattern 2: :hardbreaks-option: attribute
        if ':hardbreaks-option:' in target_line:
            old_string = target_line + '\n'
            new_string = ''
            return FixResult(
                success=True,
                old_string=old_string,
                new_string=new_string,
                method="pattern",
            )
        
        # Pattern 3: [%hardbreaks] block option
        if '[%hardbreaks]' in target_line:
            old_string = target_line + '\n'
            new_string = ''
            return FixResult(
                success=True,
                old_string=old_string,
                new_string=new_string,
                method="pattern",
            )
        
        return FixResult(success=False, error="Pattern not found", method="pattern")


class PageBreakFixer(PatternFixer):
    """Fix page breaks (<<<)."""
    
    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        lines = content.split('\n')
        if line < 1 or line > len(lines):
            return FixResult(success=False, error="Invalid line number", method="pattern")
        
        target_line = lines[line - 1]
        
        if target_line.strip() == '<<<':
            old_string = target_line + '\n'
            new_string = ''  # Remove page break
            return FixResult(
                success=True,
                old_string=old_string,
                new_string=new_string,
                method="pattern",
            )
        
        return FixResult(success=False, error="Page break not found", method="pattern")


class ThematicBreakFixer(PatternFixer):
    """Fix thematic breaks (''' or ---)."""
    
    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        lines = content.split('\n')
        if line < 1 or line > len(lines):
            return FixResult(success=False, error="Invalid line number", method="pattern")
        
        target_line = lines[line - 1].strip()
        
        # Thematic break patterns
        if target_line in ("'''", "---", "- - -", "* * *", "___"):
            old_string = lines[line - 1] + '\n'
            new_string = ''  # Remove thematic break
            return FixResult(
                success=True,
                old_string=old_string,
                new_string=new_string,
                method="pattern",
            )
        
        return FixResult(success=False, error="Thematic break not found", method="pattern")


class AuthorLineFixer(PatternFixer):
    """Fix author lines (:author: attribute)."""
    
    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        lines = content.split('\n')
        if line < 1 or line > len(lines):
            return FixResult(success=False, error="Invalid line number", method="pattern")
        
        target_line = lines[line - 1]
        
        if target_line.strip().startswith(':author:'):
            old_string = target_line + '\n'
            new_string = ''  # Remove author line
            return FixResult(
                success=True,
                old_string=old_string,
                new_string=new_string,
                method="pattern",
            )
        
        return FixResult(success=False, error="Author line not found", method="pattern")


class EntityReferenceFixer(PatternFixer):
    """Fix entity references (&nbsp;, &amp;, etc.)."""
    
    ENTITY_MAP = {
        '&nbsp;': '{nbsp}',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&apos;': "'",
    }
    
    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        lines = content.split('\n')
        if line < 1 or line > len(lines):
            return FixResult(success=False, error="Invalid line number", method="pattern")
        
        target_line = lines[line - 1]
        
        for entity, replacement in self.ENTITY_MAP.items():
            if entity in target_line:
                old_string = target_line
                new_string = target_line.replace(entity, replacement)
                return FixResult(
                    success=True,
                    old_string=old_string,
                    new_string=new_string,
                    method="pattern",
                )
        
        return FixResult(success=False, error="Entity not found", method="pattern")


class MismatchedIdFixer(PatternFixer):
    """Fix mismatched quotes in [id=...] attributes."""

    # Matches [id= with mismatched/missing quotes and captures the ID value
    _ID_RE = re.compile(r'^\[id=["\']?([^"\'\]]+)["\']?\]')

    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        lines = content.split('\n')
        if line < 1 or line > len(lines):
            return FixResult(success=False, error="Line out of range", method="pattern")

        target = lines[line - 1]
        m = self._ID_RE.match(target.strip())
        if not m:
            return FixResult(success=False, error="Could not parse ID attribute", method="pattern")

        id_value = m.group(1).strip()
        new_line = target.replace(target.strip(), f'[id="{id_value}"]')

        return FixResult(
            success=True,
            old_string=target,
            new_string=new_line,
            method="pattern",
        )


# =============================================================================
# RedHat Style Fixers (generic, message-based)
# =============================================================================


class RedHatSubstitutionFixer(PatternFixer):
    """Generic fixer for RedHat substitution rules.

    Parses Vale's message format: "Use 'replacement' rather than 'original'."
    Applies the replacement on the reported line only.

    Handles: CaseSensitiveTerms, ConsciousLanguage, Hyphens, and any other
    RedHat substitution rule that uses the standard message format.
    """

    _MSG_PATTERNS = [
        re.compile(r"Use '([^']+)' rather than '([^']+)'"),
        re.compile(r"Use ([^']+?) rather than '([^']+)'"),
        re.compile(r"consider using '([^']+)' rather than '([^']+)'"),
    ]

    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        replacement, original = self._parse_substitution(message)
        if not replacement or not original:
            return FixResult(
                success=False,
                error="Could not parse substitution from vale message",
                method="pattern",
            )

        lines = content.split('\n')
        if not (0 < line <= len(lines)):
            return FixResult(success=False, error="Line out of range", method="pattern")

        old_line = lines[line - 1]
        new_line = old_line.replace(original, replacement, 1)
        if old_line == new_line:
            return FixResult(
                success=False,
                error=f"Term '{original}' not found on line {line}",
                method="pattern",
            )

        return FixResult(
            success=True, old_string=old_line, new_string=new_line, method="pattern"
        )

    def _parse_substitution(self, message: str):
        """Extract (replacement, original) from a vale substitution message."""
        for pattern in self._MSG_PATTERNS:
            m = pattern.search(message)
            if m:
                return m.group(1).strip("'"), m.group(2).strip("'")
        return None, None


class RedHatRepeatedWordFixer(PatternFixer):
    """Fix repeated words flagged by RedHat.RepeatedWords.

    Message format: "'the' is repeated."
    """

    _MSG_RE = re.compile(r"'([^']+)' is repeated")

    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        m = self._MSG_RE.search(message)
        if not m:
            return FixResult(
                success=False, error="Could not parse repeated word", method="pattern"
            )

        word = m.group(1)
        lines = content.split('\n')
        if not (0 < line <= len(lines)):
            return FixResult(success=False, error="Line out of range", method="pattern")

        old_line = lines[line - 1]
        dup_re = re.compile(
            r'\b(' + re.escape(word) + r')\s+\1\b', re.IGNORECASE
        )
        new_line = dup_re.sub(r'\1', old_line, count=1)
        if old_line == new_line:
            return FixResult(
                success=False, error="Could not remove duplicate", method="pattern"
            )

        return FixResult(
            success=True, old_string=old_line, new_string=new_line, method="pattern"
        )


class HeadingPunctuationFixer(PatternFixer):
    """Fix trailing punctuation in headings (RedHat.HeadingPunctuation).

    Message: "Do not use end punctuation in headings."
    """

    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        lines = content.split('\n')
        if not (0 < line <= len(lines)):
            return FixResult(success=False, error="Line out of range", method="pattern")

        old_line = lines[line - 1]
        new_line = re.sub(r'[.?!]+\s*$', '', old_line)
        if old_line == new_line:
            return FixResult(
                success=False, error="No trailing punctuation found", method="pattern"
            )

        return FixResult(
            success=True, old_string=old_line, new_string=new_line, method="pattern"
        )


class AbbreviationPeriodFixer(PatternFixer):
    """Fix periods in uppercase abbreviations (RedHat.Abbreviations).

    Message: "Do not use periods in all-uppercase abbreviations such as 'A.B.C.'."
    """

    _MSG_RE = re.compile(r"such as '([^']+)'")

    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        m = self._MSG_RE.search(message)
        if not m:
            return FixResult(
                success=False, error="Could not parse abbreviation", method="pattern"
            )

        abbrev_with_periods = m.group(1)
        abbrev_clean = abbrev_with_periods.replace('.', '')

        lines = content.split('\n')
        if not (0 < line <= len(lines)):
            return FixResult(success=False, error="Line out of range", method="pattern")

        old_line = lines[line - 1]
        new_line = old_line.replace(abbrev_with_periods, abbrev_clean, 1)
        if old_line == new_line:
            return FixResult(
                success=False, error="Abbreviation not found on line", method="pattern"
            )

        return FixResult(
            success=True, old_string=old_line, new_string=new_line, method="pattern"
        )


class AssemblyContentsFixer(PatternFixer):
    """
    AssemblyContents - Flags for manual review (NO auto-fix).

    This rule detects plain text content between include directives in assemblies.
    Auto-fixing is NOT appropriate because:
    1. The content isn't wrong - it's just in the wrong place
    2. It should be MOVED to a module file, not deleted
    3. This requires human judgment about where to put the content
    
    This fixer analyzes the structure and provides actionable guidance.
    """
    
    # Patterns for case-variant "Additional resources" headings that vale rejects.
    # Vale only accepts exact: .Additional resources or == Additional resources
    _CASE_VARIANT_RE = re.compile(
        r'^(\.{1,2}|={2,}\s+)additional\s+resources[ \t]*$',
        re.IGNORECASE | re.MULTILINE,
    )

    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        """Analyze and fix case variants, or flag for manual review."""

        # First: try to fix case variants of "Additional resources" headings.
        # Vale only matches exact case: "Additional resources" (lowercase 'r').
        # Common wrong variants: ".Additional Resources", "== additional resources"
        for m in self._CASE_VARIANT_RE.finditer(content):
            original = m.group(0)
            prefix = m.group(1)
            correct = f"{prefix}Additional resources"
            if original != correct:
                return FixResult(
                    success=True,
                    old_string=original,
                    new_string=correct,
                    method="pattern",
                )

        lines = content.split('\n')

        # Find all include directives
        include_lines = []
        for i, line_content in enumerate(lines):
            if line_content.strip().startswith('include::'):
                include_lines.append(i + 1)  # 1-based

        if len(include_lines) < 2:
            return FixResult(
                success=False,
                error="MANUAL_REVIEW:Only one include directive found - cannot determine content placement issue",
                method="analysis"
            )
        
        # Find content between includes
        problem_sections = []
        for i in range(len(include_lines) - 1):
            start = include_lines[i]
            end = include_lines[i + 1]
            
            # Check for non-empty, non-comment content between includes
            for j in range(start, end - 1):
                if j < len(lines):
                    line_content = lines[j].strip()
                    # Skip empty lines, comments, conditionals
                    if (line_content and 
                        not line_content.startswith('//') and
                        not line_content.startswith('ifdef::') and
                        not line_content.startswith('ifndef::') and
                        not line_content.startswith('endif::') and
                        not line_content.startswith('ifeval::') and
                        not line_content.startswith(':') and
                        not line_content.startswith('include::')):
                        problem_sections.append({
                            'line': j + 1,
                            'content': line_content[:60] + ('...' if len(line_content) > 60 else ''),
                            'between': f"includes at lines {start} and {end}"
                        })
        
        if not problem_sections:
            return FixResult(
                success=False,
                error="MANUAL_REVIEW:Could not identify specific content to move",
                method="analysis"
            )
        
        # Build detailed guidance
        lines_list = [str(p['line']) for p in problem_sections[:5]]
        guidance = f"MANUAL_REVIEW:Lines {', '.join(lines_list)} contain content between include directives. " \
                   f"ACTION: Move this content to a separate module file and include it. " \
                   f"Content preview: '{problem_sections[0]['content']}'"
        
        return FixResult(
            success=False,
            error=guidance,
            method="manual_review"
        )


# =============================================================================
# TIER 2: Template Fixers (LLM once, then propagate)
# =============================================================================

class TemplateFixer:
    """
    Base class for template fixers.

    Uses LLM for the first instance of a rule, then learns the pattern
    and applies it to remaining instances without LLM.

    Enterprise features:
    - Complexity analysis for intelligent routing
    - Smart context windowing for complex files
    """

    def __init__(self, llm_client: LLMClient, memory: SessionMemoryV2, rule: str):
        self.llm = llm_client
        self.memory = memory
        self.rule = rule
        # Import complexity analyzer
        from dita_agent.core.complexity_analyzer import ComplexityAnalyzer
        self.complexity_analyzer = ComplexityAnalyzer()
    
    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        """Fix using learned pattern or LLM."""
        
        # Check if we have a learned pattern
        if self.memory.has_learned_fix(self.rule):
            result = self._apply_learned_pattern(filepath, content, line)
            if result.success:
                return result
        
        # No pattern or pattern didn't work - use LLM
        return self._fix_with_llm(filepath, content, line, message)
    
    def _apply_learned_pattern(self, filepath: Path, content: str, line: int) -> FixResult:
        """Apply a learned pattern to the content."""
        # Override in subclass with rule-specific logic
        return FixResult(success=False, error="Not implemented", method="template_propagation")
    
    def _fix_with_llm(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        """Use LLM to generate a fix with smart context windowing."""
        # Analyze file complexity
        complexity = self.complexity_analyzer.analyze_content(content)

        # Route based on complexity
        if self.complexity_analyzer.should_skip_llm(complexity):
            # VERY_HIGH complexity - route to manual review
            return FixResult(
                success=False,
                error=f"MANUAL_REVIEW: File complexity too high for LLM ({complexity.total_score}). "
                      f"Nested conditionals: {complexity.nested_conditionals}, "
                      f"Long lines: {complexity.long_lines}. "
                      f"Manual review recommended for line {line}.",
                method="complexity_bypass"
            )

        # Get rule context
        rule_info = get_rule(self.rule)
        prompt_context = get_prompt_context(self.rule) if rule_info else ""

        # Use smart context windowing for MEDIUM/HIGH complexity
        if self.complexity_analyzer.should_use_context_window(complexity):
            context, offset_line = self.complexity_analyzer.extract_context_window(
                content, line, window_size=15
            )
            context_line = line - offset_line + 1

            # Format context with line numbers
            context_lines = context.split('\n')
            formatted_lines = []
            for i, line_content in enumerate(context_lines):
                actual_line = offset_line + i
                marker = " >> " if i == context_line - 1 else "    "
                formatted_lines.append(f"{actual_line:4d}{marker}{line_content}")
            formatted_context = '\n'.join(formatted_lines)

            prompt = f"""Fix this DITA compatibility issue.

RULE: {self.rule}
FILE: {filepath.name}
LINE: {offset_line + context_line - 1}
MESSAGE: {message}
COMPLEXITY: {complexity.complexity_level} (windowed context for performance)

{prompt_context}

CONTEXT (the >> marks the problematic line):
```
{formatted_context}
```

IMPORTANT:
- This is a WINDOWED context (not full file)
- Make the MINIMAL change needed
- The old_string must EXACTLY match text in the context

Return ONLY a JSON object:
{{
    "old_string": "exact text to replace (must match file exactly)",
    "new_string": "replacement text"
}}"""

            response = self.llm.generate(prompt, expect_json=True)

            if not response.success:
                return FixResult(
                    success=False,
                    error=response.error,
                    method="template_llm_windowed",
                    tokens_used=response.tokens_used,
                )

            try:
                old_string = response.parsed.get("old_string", "")
                new_string = response.parsed.get("new_string", "")

                if not old_string or old_string not in context:
                    return FixResult(
                        success=False,
                        error="old_string not found in context window",
                        method="template_llm_windowed",
                        tokens_used=response.tokens_used,
                    )

                return FixResult(
                    success=True,
                    old_string=old_string,
                    new_string=new_string,
                    method="template_llm_windowed",
                    tokens_used=response.tokens_used,
                )

            except Exception as e:
                return FixResult(
                    success=False,
                    error=f"Failed to parse LLM response: {str(e)}",
                    method="template_llm_windowed",
                    tokens_used=response.tokens_used,
                )

        # LOW complexity - use standard approach
        # Extract context around the issue
        lines = content.split('\n')
        start = max(0, line - 5)
        end = min(len(lines), line + 5)
        context_lines = []
        for i in range(start, end):
            marker = " >> " if i == line - 1 else "    "
            context_lines.append(f"{i+1:4d}{marker}{lines[i]}")
        context = '\n'.join(context_lines)

        prompt = f"""Fix this DITA compatibility issue.

RULE: {self.rule}
FILE: {filepath.name}
LINE: {line}
MESSAGE: {message}
COMPLEXITY: {complexity.complexity_level}

{prompt_context}

CONTEXT (the >> marks the problematic line):
```
{context}
```

Return ONLY a JSON object:
{{
    "old_string": "exact text to replace (must match file exactly)",
    "new_string": "replacement text"
}}"""

        response = self.llm.generate(prompt, expect_json=True)

        if not response.success:
            return FixResult(
                success=False,
                error=response.error,
                method="template_llm",
                tokens_used=response.tokens_used,
            )

        try:
            old_string = response.parsed.get("old_string", "")
            new_string = response.parsed.get("new_string", "")

            if not old_string or old_string not in content:
                return FixResult(
                    success=False,
                    error="old_string not found in content",
                    method="template_llm",
                    tokens_used=response.tokens_used,
                )

            if not validate_fix_scope(content, old_string, line):
                return FixResult(
                    success=False,
                    error=f"LLM fix targets lines far from issue line {line} — rejected as out of scope",
                    method="template_llm",
                    tokens_used=response.tokens_used,
                )
            
            # Learn this fix pattern for future use
            self.memory.learn_fix(
                rule=self.rule,
                old_string=old_string,
                new_string=new_string,
                pattern_type=self._detect_pattern_type(old_string, new_string),
            )
            
            return FixResult(
                success=True,
                old_string=old_string,
                new_string=new_string,
                method="llm",
                tokens_used=response.tokens_used,
            )
        
        except Exception as e:
            return FixResult(
                success=False,
                error=f"Failed to parse LLM response: {e}",
                method="llm",
                tokens_used=response.tokens_used,
            )
    
    def _detect_pattern_type(self, old: str, new: str) -> str:
        """Detect the type of transformation."""
        if len(new) > len(old):
            return "insert"
        elif len(new) < len(old):
            return "remove"
        else:
            return "replace"


class ShortDescriptionTemplateFixer(TemplateFixer):
    """
    Template fixer for ShortDescription rule.

    This fixer adds [role="_abstract"] before the first paragraph AFTER the title.
    It uses deterministic pattern matching - no LLM needed.
    """

    import re
    ABSTRACT_PATTERN = re.compile(r'^\[role=["\']?_abstract["\']?\]', re.MULTILINE)
    TITLE_PATTERN = re.compile(r'^=\s+.+$', re.MULTILINE)
    # Pattern to detect SNIPPET content type - these files should NOT have abstracts
    SNIPPET_PATTERN = re.compile(r'^:_mod-docs-content-type:\s*SNIPPET', re.MULTILINE | re.IGNORECASE)

    def __init__(self, llm_client: LLMClient, memory: SessionMemoryV2):
        super().__init__(llm_client, memory, "ShortDescription")
        # Import semantic validator
        from dita_agent.core.semantic_validation import SemanticValidator
        self.validator = SemanticValidator()
    
    def _is_snippet_file(self, content: str) -> bool:
        """Check if file is a SNIPPET type - these don't need abstracts."""
        return bool(self.SNIPPET_PATTERN.search(content))
    
    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        """
        Fix ShortDescription by adding [role="_abstract"] before first paragraph.
        
        Handles two cases:
        1. No abstract marker → Add marker before first paragraph
        2. Abstract marker exists but no paragraph → Generate paragraph with LLM
        """
        # SNIPPET files should NOT have abstracts - skip them
        if self._is_snippet_file(content):
            return FixResult(
                success=True,
                method="skipped",
                error="SNIPPET files do not need abstracts"
            )
        
        # Check if abstract marker already exists
        if self.ABSTRACT_PATTERN.search(content):
            # Verify there's actually a paragraph after the abstract marker
            if self._has_paragraph_after_abstract(content):
                return FixResult(success=True, method="pattern")
            else:
                # Abstract marker exists but NO paragraph - need LLM to generate one
                return self._generate_abstract_paragraph(filepath, content)
        
        # No abstract marker - use deterministic pattern to add one
        return self._find_and_mark_abstract(filepath, content)
    
    def _find_and_mark_abstract(self, filepath: Path, content: str) -> FixResult:
        """
        Find the first paragraph after the title and mark it as abstract.
        
        The abstract marker [role="_abstract"] goes BEFORE the first content
        paragraph that appears AFTER the document title (= Title).
        """
        lines = content.split('\n')
        
        # Step 1: Find the document title line (starts with '= ')
        title_line_idx = None
        for i, line_content in enumerate(lines):
            if line_content.startswith('= '):
                title_line_idx = i
                break
        
        if title_line_idx is None:
            return FixResult(
                success=False, 
                error="No document title found (line starting with '= ')", 
                method="pattern"
            )
        
        # Step 2: Scan FORWARD from title to find first content paragraph
        in_conditional = 0
        
        for i in range(title_line_idx + 1, len(lines)):
            line_content = lines[i]
            stripped = line_content.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Skip document attributes (e.g., :toc:, :icons:)
            if stripped.startswith(':') and ':' in stripped[1:]:
                continue
            
            # Track conditional blocks - don't mark content inside conditionals
            if stripped.startswith(('ifdef::', 'ifndef::', 'ifeval::')):
                in_conditional += 1
                continue
            if stripped.startswith('endif::'):
                in_conditional = max(0, in_conditional - 1)
                continue
            
            # Skip include directives
            if stripped.startswith('include::'):
                continue
            
            # Skip comments
            if stripped.startswith('//'):
                continue
            
            # Skip block attributes like [id="..."], [source], etc.
            if stripped.startswith('['):
                continue
            
            # Skip block titles like .My Title
            if stripped.startswith('.') and not stripped.startswith('..'):
                continue
            
            # Skip section headings (== , === , etc.)
            if stripped.startswith('=='):
                continue
            
            # Found first content paragraph (must be outside conditionals)
            if in_conditional == 0 and len(stripped) > 10:  # Reasonable paragraph length
                # SEMANTIC VALIDATION: Extract full paragraph and validate
                paragraph_text = self._extract_paragraph(lines, i)
                validation = self.validator.validate_short_description(paragraph_text)

                if not validation.is_valid:
                    # Paragraph fails semantic validation - needs manual review
                    return FixResult(
                        success=False,
                        method="pattern",
                        error=f"MANUAL_REVIEW: {validation.error}. {validation.suggestion}"
                    )

                # Validation passed - apply the fix
                old_string = line_content
                new_string = f'[role="_abstract"]\n{line_content}'
                return FixResult(
                    success=True,
                    old_string=old_string,
                    new_string=new_string,
                    method="pattern",
                )
        
        return FixResult(
            success=False, 
            error="No suitable paragraph found after title", 
            method="pattern"
        )
    
    def _has_paragraph_after_abstract(self, content: str) -> bool:
        """
        Check if there's a real content paragraph after [role="_abstract"].
        
        Returns False if abstract marker is followed only by:
        - Empty lines
        - Include directives
        - Comments
        - Section headings
        """
        lines = content.split('\n')
        
        # Find the abstract marker line
        abstract_line_idx = None
        for i, line_content in enumerate(lines):
            if '[role=' in line_content and '_abstract' in line_content:
                abstract_line_idx = i
                break
        
        if abstract_line_idx is None:
            return False
        
        # Check lines AFTER the abstract marker
        for i in range(abstract_line_idx + 1, min(abstract_line_idx + 10, len(lines))):
            stripped = lines[i].strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Skip include directives - NOT a paragraph
            if stripped.startswith('include::'):
                return False  # Include right after abstract = no paragraph
            
            # Skip comments
            if stripped.startswith('//'):
                continue
            
            # Skip conditionals
            if stripped.startswith(('ifdef::', 'ifndef::', 'ifeval::', 'endif::')):
                continue
            
            # Skip section headings
            if stripped.startswith('=='):
                return False  # Section heading = no abstract paragraph
            
            # Found real content paragraph!
            if len(stripped) > 10 and not stripped.startswith('['):
                return True
        
        return False

    def _extract_paragraph(self, lines: list, start_index: int) -> str:
        """
        Extract the full paragraph starting at start_index.

        A paragraph continues until we hit:
        - An empty line
        - A block delimiter (=, -, *, |, ., [)
        - Another paragraph

        Args:
            lines: List of file lines
            start_index: Starting line index

        Returns:
            The complete paragraph text
        """
        paragraph_lines = []

        for i in range(start_index, len(lines)):
            line = lines[i]
            stripped = line.strip()

            # Stop at empty line
            if not stripped:
                break

            # Stop at block delimiters
            if stripped.startswith(('=', '-', '*', '|', '.', '[')):
                # But include the first line if it's the start
                if i == start_index:
                    paragraph_lines.append(stripped)
                break

            paragraph_lines.append(stripped)

        return ' '.join(paragraph_lines)

    def _generate_abstract_paragraph(self, filepath: Path, content: str) -> FixResult:
        """
        Use LLM to generate an abstract paragraph when marker exists but no paragraph.
        
        This handles the case where [role="_abstract"] was added but there's no
        content paragraph after it - we need to generate one based on the title.
        """
        import re
        
        lines = content.split('\n')
        
        # Find the title
        title = None
        for line_content in lines:
            if line_content.startswith('= '):
                title = line_content[2:].strip()
                break
        
        if not title:
            return FixResult(
                success=False,
                error="Cannot generate abstract - no title found",
                method="llm"
            )
        
        # Find the abstract marker line to know where to insert
        abstract_line_idx = None
        abstract_line = None
        for i, line_content in enumerate(lines):
            if '[role=' in line_content and '_abstract' in line_content:
                abstract_line_idx = i
                abstract_line = line_content
                break
        
        if abstract_line_idx is None:
            return FixResult(
                success=False,
                error="Abstract marker not found",
                method="llm"
            )
        
        # Build prompt for LLM
        prompt = f"""Generate a SHORT introductory paragraph (1-2 sentences) for this AsciiDoc document.

Title: {title}
File: {filepath.name}

Requirements:
1. Maximum 2 sentences
2. Describe what the reader will learn/do
3. Use active voice
4. Don't start with "This document..." or "This topic..."
5. Return ONLY the paragraph text, nothing else

Example output for "Installing the application":
Install the application on your system using the package manager or manual installation method.

Your paragraph:"""

        try:
            response = self.llm.generate(prompt, expect_json=False)
            paragraph = response.content.strip()
            
            # Clean up any quotes or extra formatting
            paragraph = paragraph.strip('"\'')
            
            if not paragraph or len(paragraph) < 10:
                return FixResult(
                    success=False,
                    error="LLM generated empty or too short paragraph",
                    method="llm"
                )
            
            # The old string is just the abstract marker line
            old_string = abstract_line
            # New string is abstract marker + generated paragraph
            new_string = f'{abstract_line}\n{paragraph}'
            
            return FixResult(
                success=True,
                old_string=old_string,
                new_string=new_string,
                method="llm",
            )
            
        except Exception as e:
            return FixResult(
                success=False,
                error=f"LLM generation failed: {str(e)}",
                method="llm"
            )
    
    def _apply_learned_pattern(self, filepath: Path, content: str, line: int) -> FixResult:
        """Apply ShortDescription pattern - delegates to main fix logic."""
        if self._is_snippet_file(content):
            return FixResult(
                success=True,
                method="skipped",
                error="SNIPPET files do not need abstracts"
            )
        
        if self.ABSTRACT_PATTERN.search(content):
            if self._has_paragraph_after_abstract(content):
                return FixResult(success=True, method="pattern")
            else:
                return self._generate_abstract_paragraph(filepath, content)
        
        return self._find_and_mark_abstract(filepath, content)


class BlockTitleTemplateFixer(TemplateFixer):
    """Template fixer for BlockTitle rule."""

    def __init__(self, llm_client: LLMClient, memory: SessionMemoryV2):
        super().__init__(llm_client, memory, "BlockTitle")


class RelatedLinksTemplateFixer(TemplateFixer):
    """Custom fixer for RelatedLinks that validates before calling LLM."""

    def __init__(self, llm_client: LLMClient, memory: SessionMemoryV2):
        super().__init__(llm_client, memory, "RelatedLinks")

    # Regex for AsciiDoc link macros: link:https://... or xref:id[...]
    _LINK_RE = re.compile(r'(?:link:https?://|xref:)')

    @staticmethod
    def _is_valid_link(line_text: str) -> bool:
        """Check if a list item contains a valid link: or xref: macro."""
        return line_text.startswith('*') and bool(
            RelatedLinksTemplateFixer._LINK_RE.search(line_text)
        )

    @staticmethod
    def _classify_section_items(lines: list[str], section_start: int) -> tuple[bool, list[str]]:
        """Classify items in the Additional resources section as links or non-links.

        Returns (has_links, non_link_items).
        """
        has_links = False
        non_link_items = []

        for i in range(section_start + 1, min(section_start + 20, len(lines))):
            line_content = lines[i].strip()

            # Stop at next section
            if line_content.startswith('==') or line_content.startswith('include::'):
                break

            if not line_content.startswith('*'):
                continue

            if RelatedLinksTemplateFixer._LINK_RE.search(line_content):
                has_links = True
            else:
                non_link_items.append(line_content)

        return has_links, non_link_items

    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        """Check if there are actual links before calling LLM."""

        lines = content.split('\n')

        # Find the Additional resources section (line is approximate)
        section_start = next(
            (i for i, l in enumerate(lines) if 'Additional resources' in l), -1
        )
        if section_start == -1:
            return FixResult(
                success=False,
                error="MANUAL_REVIEW: Could not find Additional resources section",
                method="pattern"
            )

        has_links, non_link_items = self._classify_section_items(lines, section_start)

        # No links at all — route to manual review immediately
        if not has_links:
            return FixResult(
                success=False,
                error=f"MANUAL_REVIEW: Additional resources section contains no links. "
                      f"All {len(non_link_items)} items need author review to either add links or move content elsewhere.",
                method="pattern"
            )

        # ALL items are valid links (no non-link items) — false positive from
        # Vale, e.g. links containing AsciiDoc attributes like {attr} in URL
        # or link text. Do NOT modify the file.
        if not non_link_items:
            return FixResult(
                success=True,
                method="pattern",
            )

        # Check if the specific flagged line is itself a valid link.
        # Vale may flag: * link:https://.../{attribute}[{attribute} text]
        # because it cannot resolve AsciiDoc attributes.
        if 0 < line <= len(lines) and self._is_valid_link(lines[line - 1].strip()):
            return FixResult(
                success=True,
                method="pattern",
            )

        # Has some links but also non-link items — let LLM try to fix
        return super().fix(filepath, content, line, message)


class DocumentTitleTemplateFixer(TemplateFixer):
    """Template fixer for DocumentTitle rule."""
    
    def __init__(self, llm_client: LLMClient, memory: SessionMemoryV2):
        super().__init__(llm_client, memory, "DocumentTitle")


# =============================================================================
# TIER 3: LLM Fixers (LLM each time)
# =============================================================================

class LLMFixer:
    """
    Fixer that uses LLM for each instance.

    Used for complex issues that require understanding context
    and can't be easily templated.

    Enterprise features:
    - Complexity analysis for intelligent routing
    - Smart context windowing (15 lines vs full file)
    - Automatic fallback for VERY_HIGH complexity files
    """

    def __init__(self, llm_client: LLMClient, rule: str):
        self.llm = llm_client
        self.rule = rule
        # Import complexity analyzer
        from dita_agent.core.complexity_analyzer import ComplexityAnalyzer
        self.complexity_analyzer = ComplexityAnalyzer()

    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        """Use LLM to generate a fix with smart context windowing."""

        # STEP 1: Analyze file complexity
        complexity = self.complexity_analyzer.analyze_content(content)

        # STEP 2: Route based on complexity
        if self.complexity_analyzer.should_skip_llm(complexity):
            # VERY_HIGH complexity - route to manual review
            return FixResult(
                success=False,
                error=f"MANUAL_REVIEW: File complexity too high for LLM ({complexity.total_score}). "
                      f"Nested conditionals: {complexity.nested_conditionals}, "
                      f"Long lines: {complexity.long_lines}. "
                      f"Manual review recommended for line {line}.",
                method="complexity_bypass"
            )

        # STEP 3: Use smart context windowing for MEDIUM/HIGH complexity
        if self.complexity_analyzer.should_use_context_window(complexity):
            context, offset_line = self.complexity_analyzer.extract_context_window(
                content, line, window_size=15
            )
            # Adjust line number to context-relative
            context_line = line - offset_line + 1
            return self._fix_with_context_window(
                filepath, context, context_line, offset_line, message, complexity
            )

        # STEP 4: LOW complexity - use standard full context
        return self._fix_with_full_context(filepath, content, line, message, complexity)

    def _fix_with_context_window(
        self,
        filepath: Path,
        context: str,
        context_line: int,
        offset_line: int,
        message: str,
        complexity
    ) -> FixResult:
        """Fix using smart context window (for MEDIUM/HIGH complexity)."""
        rule_info = get_rule(self.rule)
        prompt_context = get_prompt_context(self.rule) if rule_info else ""

        # Format context with line numbers
        context_lines = context.split('\n')
        formatted_lines = []
        for i, line_content in enumerate(context_lines):
            actual_line = offset_line + i
            marker = " >> " if i == context_line - 1 else "    "
            formatted_lines.append(f"{actual_line:4d}{marker}{line_content}")
        formatted_context = '\n'.join(formatted_lines)

        prompt = f"""Fix this DITA compatibility issue.

RULE: {self.rule}
FILE: {filepath.name}
LINE: {offset_line + context_line - 1}
MESSAGE: {message}
COMPLEXITY: {complexity.complexity_level} (windowed context for performance)

{prompt_context}

CONTEXT (the >> marks the problematic line):
```
{formatted_context}
```

IMPORTANT:
- This is a WINDOWED context (not full file)
- Make the MINIMAL change needed to fix THIS specific issue
- Preserve all existing content and structure
- The old_string must EXACTLY match text in the context
- Do NOT try to fix conditionals outside this window

Return ONLY a JSON object:
{{
    "old_string": "exact text to replace",
    "new_string": "replacement text"
}}"""

        response = self.llm.generate(prompt, expect_json=True)

        if not response.success:
            return FixResult(
                success=False,
                error=response.error,
                method="llm_windowed",
                tokens_used=response.tokens_used,
            )

        try:
            old_string = response.parsed.get("old_string", "")
            new_string = response.parsed.get("new_string", "")

            if not old_string or old_string not in context:
                return FixResult(
                    success=False,
                    error="old_string not found in context window",
                    method="llm_windowed",
                    tokens_used=response.tokens_used,
                )

            return FixResult(
                success=True,
                old_string=old_string,
                new_string=new_string,
                method="llm_windowed",
                tokens_used=response.tokens_used,
            )

        except Exception as e:
            return FixResult(
                success=False,
                error=f"Failed to parse LLM response: {str(e)}",
                method="llm_windowed",
                tokens_used=response.tokens_used,
            )

    def _fix_with_full_context(
        self,
        filepath: Path,
        content: str,
        line: int,
        message: str,
        complexity
    ) -> FixResult:
        """Fix using full context (for LOW complexity)."""
        rule_info = get_rule(self.rule)
        prompt_context = get_prompt_context(self.rule) if rule_info else ""

        # Extract context
        lines = content.split('\n')
        start = max(0, line - 8)
        end = min(len(lines), line + 8)
        context_lines = []
        for i in range(start, end):
            marker = " >> " if i == line - 1 else "    "
            context_lines.append(f"{i+1:4d}{marker}{lines[i]}")
        context = '\n'.join(context_lines)

        prompt = f"""Fix this DITA compatibility issue.

RULE: {self.rule}
FILE: {filepath.name}
LINE: {line}
MESSAGE: {message}
COMPLEXITY: {complexity.complexity_level}

{prompt_context}

CONTEXT (the >> marks the problematic line):
```
{context}
```

IMPORTANT:
- Make the MINIMAL change needed
- Preserve all existing content and structure
- The old_string must EXACTLY match text in the file

Return ONLY a JSON object:
{{
    "old_string": "exact text to replace",
    "new_string": "replacement text"
}}"""

        response = self.llm.generate(prompt, expect_json=True)

        if not response.success:
            return FixResult(
                success=False,
                error=response.error,
                method="llm",
                tokens_used=response.tokens_used,
            )
        
        try:
            old_string = response.parsed.get("old_string", "")
            new_string = response.parsed.get("new_string", "")

            if not old_string or old_string not in content:
                return FixResult(
                    success=False,
                    error="old_string not found in content",
                    method="llm",
                    tokens_used=response.tokens_used,
                )

            # Reject fixes that modify content far from the reported issue line.
            # This prevents unsolicited LLM edits (e.g., backtick-quoting a word
            # on line 33 when the issue was on line 25).
            if not validate_fix_scope(content, old_string, line):
                return FixResult(
                    success=False,
                    error=f"LLM fix targets lines far from issue line {line} — rejected as out of scope",
                    method="llm",
                    tokens_used=response.tokens_used,
                )
            
            return FixResult(
                success=True,
                old_string=old_string,
                new_string=new_string,
                method="llm",
                tokens_used=response.tokens_used,
            )
        
        except Exception as e:
            return FixResult(
                success=False,
                error=f"Failed to parse LLM response: {e}",
                method="llm",
                tokens_used=response.tokens_used,
            )


# =============================================================================
# Fixer Registry
# =============================================================================

class FixerRegistry:
    """
    Registry of all fixers organized by tier.
    
    Routes issues to the appropriate fixer based on rule type.
    """
    
    # Rule to tier mapping
    TIER_MAP: Dict[str, FixerTier] = {
        # TIER 1: Pattern-based (no LLM)
        "LineBreak": FixerTier.PATTERN,
        "PageBreak": FixerTier.PATTERN,
        "ThematicBreak": FixerTier.PATTERN,
        "AuthorLine": FixerTier.PATTERN,
        "EntityReference": FixerTier.PATTERN,
        "TagDirective": FixerTier.PATTERN,
        "IncludeDirective": FixerTier.PATTERN,
        "MismatchedId": FixerTier.PATTERN,
        "ConditionalCode": FixerTier.PATTERN,
        "TableFooter": FixerTier.PATTERN,
        "DiscreteHeading": FixerTier.PATTERN,
        "EquationFormula": FixerTier.PATTERN,
        
        # TIER 2: Template-based (LLM once, then propagate)
        "ShortDescription": FixerTier.TEMPLATE,
        "BlockTitle": FixerTier.TEMPLATE,
        "DocumentTitle": FixerTier.TEMPLATE,
        "DocumentId": FixerTier.TEMPLATE,
        "AdmonitionTitle": FixerTier.TEMPLATE,
        "ExampleBlock": FixerTier.TEMPLATE,
        "SidebarBlock": FixerTier.TEMPLATE,
        "RelatedLinks": FixerTier.TEMPLATE,
        
        # TIER 3: LLM-required (each instance)
        "TaskStep": FixerTier.LLM,
        "TaskContents": FixerTier.LLM,
        "TaskSection": FixerTier.LLM,
        "TaskTitle": FixerTier.LLM,
        "TaskDuplicate": FixerTier.LLM,
        "TaskExample": FixerTier.LLM,
        "NestedSection": FixerTier.LLM,
        "CalloutList": FixerTier.LLM,
        "AttributeReference": FixerTier.LLM,
        
        # AssemblyContents uses LLM to analyze and decide placement
        "AssemblyContents": FixerTier.LLM,  # Intelligent content placement analysis

        # RedHat style rules — PATTERN-fixable (message-based)
        "CaseSensitiveTerms": FixerTier.PATTERN,
        "ConsciousLanguage": FixerTier.PATTERN,
        "Hyphens": FixerTier.PATTERN,
        "RepeatedWords": FixerTier.PATTERN,
        "HeadingPunctuation": FixerTier.PATTERN,
        "Abbreviations": FixerTier.PATTERN,

        # RedHat style rules — LLM-routed (context-dependent)
        "EmDash": FixerTier.LLM,
        "DoNotUseTerms": FixerTier.LLM,
        "GitLinks": FixerTier.LLM,
        "MergeConflictMarkers": FixerTier.LLM,
    }
    
    def __init__(self, llm_client: LLMClient, memory: SessionMemoryV2):
        self.llm = llm_client
        self.memory = memory
        
        # Initialize pattern fixers (no LLM needed)
        _redhat_sub = RedHatSubstitutionFixer()
        self.pattern_fixers: Dict[str, PatternFixer] = {
            "LineBreak": LineBreakFixer(),
            "PageBreak": PageBreakFixer(),
            "ThematicBreak": ThematicBreakFixer(),
            "AuthorLine": AuthorLineFixer(),
            "EntityReference": EntityReferenceFixer(),
            "MismatchedId": MismatchedIdFixer(),
            # RedHat style pattern fixers (message-based)
            "CaseSensitiveTerms": _redhat_sub,
            "ConsciousLanguage": _redhat_sub,
            "Hyphens": _redhat_sub,
            "RepeatedWords": RedHatRepeatedWordFixer(),
            "HeadingPunctuation": HeadingPunctuationFixer(),
            "Abbreviations": AbbreviationPeriodFixer(),
        }
        
        # Initialize template fixers (LLM once, then propagate)
        self.template_fixers: Dict[str, TemplateFixer] = {
            "ShortDescription": ShortDescriptionTemplateFixer(llm_client, memory),
            "BlockTitle": BlockTitleTemplateFixer(llm_client, memory),
            "DocumentTitle": DocumentTitleTemplateFixer(llm_client, memory),
            "RelatedLinks": RelatedLinksTemplateFixer(llm_client, memory),
        }
        
        # Specialized fixer for table line breaks
        self.table_line_break_fixer = TableLineBreakFixer(llm_client)
        
        # LLM fixers are created on-demand
    
    def get_fixer(self, rule: str) -> Any:
        """Get the appropriate fixer for a rule."""
        # Check pattern fixers
        if rule in self.pattern_fixers:
            return self.pattern_fixers[rule]
        
        # Check template fixers
        if rule in self.template_fixers:
            return self.template_fixers[rule]
        
        # Default to LLM fixer
        return LLMFixer(self.llm, rule)
    
    def get_tier(self, rule: str) -> int:
        """Get the tier number for a rule (1, 2, or 3)."""
        tier = self.TIER_MAP.get(rule, FixerTier.LLM)
        return tier.value
    
    def get_tier_label(self, rule: str) -> str:
        """Get human-readable tier label."""
        tier = self.get_tier(rule)
        labels = {1: "PATTERN", 2: "TEMPLATE", 3: "LLM"}
        return labels.get(tier, "LLM")
    
    def get_tier_map(self) -> Dict[str, int]:
        """Get mapping of all rules to tier numbers."""
        return {rule: tier.value for rule, tier in self.TIER_MAP.items()}
