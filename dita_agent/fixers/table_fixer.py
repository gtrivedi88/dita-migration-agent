"""
Specialized Table LineBreak Fixer.

Handles ` +` line breaks inside AsciiDoc tables by:
1. Extracting the COMPLETE table row (which may span multiple lines)
2. Merging multi-line cell content into single lines
3. Removing ` +` line continuation markers

This solves the problem of complex table structures with multi-line cells.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from dita_agent.llm.client import LLMClient


@dataclass
class TableRow:
    """Represents a complete table row (may span multiple lines)."""
    start_line: int      # 1-based line number where row starts
    end_line: int        # 1-based line number where row ends
    content: str         # Full row content including all lines
    line_numbers: List[int]  # All line numbers this row spans


@dataclass 
class FixResult:
    """Result of a fix attempt."""
    success: bool
    old_string: Optional[str] = None
    new_string: Optional[str] = None
    error: Optional[str] = None
    method: str = "unknown"
    tokens_used: int = 0


class TableLineBreakFixer:
    """
    Specialized fixer for LineBreak issues inside tables.
    
    Key insight: Table rows in AsciiDoc can span multiple lines.
    A row starts with | and ends when the next | appears at line start.
    We need to extract and fix the ENTIRE row.
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        # Track which rows we've already fixed (to avoid duplicate fixes)
        self._fixed_rows: set = set()
    
    def fix(self, filepath: Path, content: str, line: int, message: str) -> FixResult:
        """
        Fix LineBreak in a table by extracting and fixing the complete row.
        """
        lines = content.split('\n')
        
        # Find the table boundaries
        table_start, table_end = self._find_table_boundaries(lines, line)
        if table_start is None:
            return FixResult(
                success=False,
                error="Could not find table boundaries",
                method="table_fixer"
            )
        
        # Extract the complete row containing this line
        row = self._extract_table_row(lines, line, table_start, table_end)
        if row is None:
            return FixResult(
                success=False,
                error="Could not extract table row",
                method="table_fixer"
            )
        
        # Check if we've already fixed this row (multiple ` +` in same row)
        row_key = f"{filepath}:{row.start_line}-{row.end_line}"
        if row_key in self._fixed_rows:
            return FixResult(
                success=True,
                method="table_fixer",
                error="Row already fixed in this session"
            )
        
        # Try pattern-based fix first (for simple cases)
        pattern_result = self._try_pattern_fix(row)
        if pattern_result.success:
            self._fixed_rows.add(row_key)
            return pattern_result
        
        # Fall back to LLM for complex cases
        llm_result = self._fix_with_llm(filepath, row)
        if llm_result.success:
            self._fixed_rows.add(row_key)
        
        return llm_result
    
    def _find_table_boundaries(
        self, 
        lines: List[str], 
        target_line: int
    ) -> Tuple[Optional[int], Optional[int]]:
        """Find the start and end of the table containing target_line."""
        table_start = None
        table_end = None
        in_table = False
        
        for i, line in enumerate(lines):
            line_num = i + 1  # 1-based
            stripped = line.strip()
            
            if stripped.startswith('|==='):
                if not in_table:
                    in_table = True
                    table_start = line_num
                else:
                    table_end = line_num
                    if table_start <= target_line <= table_end:
                        return (table_start, table_end)
                    in_table = False
                    table_start = None
        
        return (None, None)
    
    def _extract_table_row(
        self,
        lines: List[str],
        target_line: int,
        table_start: int,
        table_end: int,
    ) -> Optional[TableRow]:
        """
        Extract the complete table row containing target_line.
        
        A row in AsciiDoc table starts when a line begins with | (first cell)
        and ends when another line begins with | or |=== (table end).
        """
        # Find row start: scan backwards to find line starting with |
        row_start = target_line
        for i in range(target_line, table_start - 1, -1):
            line_content = lines[i - 1]  # Convert to 0-based
            stripped = line_content.strip()
            
            # Found start of a row (line starting with |)
            if stripped.startswith('|') and not stripped.startswith('|==='):
                row_start = i
                break
        
        # Find row end: scan forward to find next line starting with | or table end
        row_end = target_line
        for i in range(target_line + 1, table_end + 1):
            if i > len(lines):
                row_end = table_end - 1
                break
                
            line_content = lines[i - 1]  # Convert to 0-based
            stripped = line_content.strip()
            
            # Found next row start or table end
            if stripped.startswith('|'):
                row_end = i - 1
                break
        else:
            row_end = table_end - 1
        
        # Extract the row content
        row_lines = lines[row_start - 1:row_end]
        row_content = '\n'.join(row_lines)
        line_numbers = list(range(row_start, row_end + 1))
        
        return TableRow(
            start_line=row_start,
            end_line=row_end,
            content=row_content,
            line_numbers=line_numbers,
        )
    
    def _is_intentional_formatting(self, row: TableRow) -> bool:
        """
        Detect if ` +` is used for intentional formatting (not an error).
        
        Intentional formatting patterns (should be manual review):
        - Multiple separate backtick items: `--arg1` + `--arg2` + `--arg3`
        - CLI arguments or code examples formatted for readability
        
        NOT intentional (should be fixed):
        - Single property split: `spec.config.` + `name` (ends with dot)
        - Label on separate line: `name` + (Technology Preview)
        """
        content = row.content
        
        # Count lines with ` +` continuation
        continuation_lines = re.findall(r'`[^`]+`\s*\+\s*$', content, re.MULTILINE)
        
        if len(continuation_lines) < 2:
            # Only 1 or 0 continuations - not a list, safe to fix
            return False
        
        # Check if it's a property split (first backtick ends with .)
        # Pattern: `spec.something.` + `name` - this is ONE property, not a list
        property_split = re.search(r'`[^`]+\.`\s*\+\s*\n', content)
        if property_split:
            return False  # It's a property split, safe to fix
        
        # Check if multiple COMPLETE backtick items are on separate lines
        # This indicates intentional list formatting (e.g., CLI args)
        # Pattern: multiple lines each with `something` +
        separate_items = re.findall(r'^\s*`[^`]+`\s*\+\s*$', content, re.MULTILINE)
        if len(separate_items) >= 2:
            # Check if they look like separate items (not parts of one thing)
            # CLI args start with - or --
            cli_args = [item for item in separate_items if re.search(r'`--?[a-zA-Z]', item)]
            if len(cli_args) >= 2:
                return True  # Multiple CLI arguments - intentional formatting
        
        return False
    
    def _try_pattern_fix(self, row: TableRow) -> FixResult:
        """
        Try to fix the row using pattern matching.
        
        Handles common patterns:
        1. Backtick content split: `spec.config.` + newline + `name`
        2. Multi-line cell content with ` +` continuation
        3. Empty lines within cells
        
        Flags intentional formatting for manual review.
        """
        content = row.content
        original = content
        
        # FIRST: Check if this is intentional formatting (CLI args, code examples)
        if self._is_intentional_formatting(row):
            return FixResult(
                success=False, 
                method="table_pattern", 
                error="INTENTIONAL_FORMATTING"  # Signal for manual review
            )
        
        # Pattern 1: Merge backtick content split by ` +`
        # `spec.dashboardConfig.` +\n`disableSomething` → `spec.dashboardConfig.disableSomething`
        # This is the MAIN pattern that works well - keep it!
        backtick_split = re.compile(r'(`[^`]+)`\s*\+\s*\n\s*`([^`]+`)')
        content = backtick_split.sub(r'\1\2', content)
        
        # Pattern 2: Handle ` +` followed by empty line(s) and then parenthetical
        # `name` +\n\n(Technology Preview) → `name` (Technology Preview)
        continuation_with_empty = re.compile(r'(`[^`]+`)\s*\+\s*\n(\s*\n)*\s*(\([^)]+\))')
        content = continuation_with_empty.sub(r'\1 \3', content)
        
        # Pattern 3: Simple ` +` at end of line before parenthetical on next line
        # `name` +\n(Technology Preview) → `name` (Technology Preview)
        simple_paren = re.compile(r'(`[^`]+`)\s*\+\s*\n\s*(\([^)]+\))')
        content = simple_paren.sub(r'\1 \2', content)
        
        # Pattern 4: Clean up multiple empty lines to single
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Pattern 5: Remove trailing ` +` at end of content (if any left)
        content = re.sub(r'\s+\+\s*$', '', content)
        
        # Validate: make sure we didn't break the table structure
        if original.count('|') != content.count('|'):
            return FixResult(success=False, method="table_pattern", error="Would break table structure")
        
        if content != original:
            return FixResult(
                success=True,
                old_string=original,
                new_string=content,
                method="table_pattern",
            )
        
        return FixResult(success=False, method="table_pattern")
    
    def _fix_with_llm(self, filepath: Path, row: TableRow) -> FixResult:
        """Use LLM to fix complex table row line breaks."""
        
        prompt = f"""Fix this AsciiDoc table row by removing the ` +` line continuation markers.

CURRENT ROW:
{row.content}

RULES:
1. Merge backtick code like `spec.config.` + `name` into `spec.config.name`
2. Keep parenthetical text like (Technology Preview) on the same line as the item it describes
3. Remove all ` +` markers
4. Keep the table structure valid (same number of | cell separators)
5. Collapse empty lines within cells

Return ONLY the fixed row content, no explanation:
"""

        response = self.llm.generate(prompt, expect_json=False)
        
        if not response.success:
            return FixResult(
                success=False,
                error=f"LLM error: {response.error}",
                method="table_llm",
                tokens_used=response.tokens_used,
            )
        
        try:
            new_string = response.content.strip()
            
            # Clean up markdown code fences if present
            if new_string.startswith("```"):
                lines = new_string.split('\n')
                # Find the end of the code block
                if lines[-1].strip() == '```':
                    new_string = '\n'.join(lines[1:-1])
                else:
                    new_string = '\n'.join(lines[1:])
            
            # Also handle ``` at end
            if new_string.endswith("```"):
                new_string = new_string[:-3].strip()
            
            if not new_string:
                return FixResult(
                    success=False,
                    error="LLM returned empty response",
                    method="table_llm",
                    tokens_used=response.tokens_used,
                )
            
            # Basic validation
            if row.content.count('|') != new_string.count('|'):
                return FixResult(
                    success=False,
                    error="LLM response has different number of cell separators",
                    method="table_llm",
                    tokens_used=response.tokens_used,
                )
            
            return FixResult(
                success=True,
                old_string=row.content,
                new_string=new_string,
                method="table_llm",
                tokens_used=response.tokens_used,
            )
            
        except Exception as e:
            return FixResult(
                success=False,
                error=f"Failed to process LLM response: {e}",
                method="table_llm",
                tokens_used=response.tokens_used,
            )
    
    def reset(self):
        """Reset the fixed rows tracker for a new session."""
        self._fixed_rows.clear()
