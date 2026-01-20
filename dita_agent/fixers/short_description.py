"""
ShortDescription fixer - adds [role="_abstract"] without moving content.

Strategy:
1. Try regex approach first (fast, reliable when structure is clear)
2. Fall back to LLM only when structure is unclear

The key insight: we should NEVER move content, only ADD the [role="_abstract"] line.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from dita_agent.llm.client import LLMClient
from dita_agent.core.semantic_validation import SemanticValidator


@dataclass
class FixResult:
    """Result of a fix attempt."""
    success: bool
    old_string: Optional[str] = None
    new_string: Optional[str] = None
    method: str = "none"  # "regex" or "llm"
    error: Optional[str] = None


class ShortDescriptionFixer:
    """
    Fixes ShortDescription issues by adding [role="_abstract"] to the first paragraph.
    
    CRITICAL: Never moves content - only adds the attribute line.
    """
    
    # Pattern to detect if file already has abstract
    ABSTRACT_PATTERN = re.compile(r'^\[role=["\']?_abstract["\']?\]', re.MULTILINE)
    
    # Pattern to detect title line
    TITLE_PATTERN = re.compile(r'^=\s+.+$', re.MULTILINE)
    
    # Pattern to detect content type attribute
    CONTENT_TYPE_PATTERN = re.compile(r'^:_mod-docs-content-type:\s*\w+', re.MULTILINE)
    
    # Pattern to detect conditional blocks
    CONDITIONAL_START = re.compile(r'^(?:ifdef|ifndef|ifeval)::', re.MULTILINE)
    CONDITIONAL_END = re.compile(r'^endif::', re.MULTILINE)
    
    # Pattern to detect include directives  
    INCLUDE_PATTERN = re.compile(r'^include::', re.MULTILINE)
    
    # Pattern to detect block titles (like .Prerequisites)
    BLOCK_TITLE_PATTERN = re.compile(r'^\.[A-Z][a-zA-Z\s]+$', re.MULTILINE)
    
    # Pattern to detect section headings
    SECTION_PATTERN = re.compile(r'^==+\s+', re.MULTILINE)
    
    # Pattern to detect ID blocks
    ID_PATTERN = re.compile(r'^\[id=["\'][^"\']+["\']\]', re.MULTILINE)
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the fixer.

        Args:
            llm_client: Optional LLM client for complex cases.
        """
        self.llm = llm_client
        self.validator = SemanticValidator()
    
    def fix(self, content: str, filepath: Path) -> FixResult:
        """
        Fix ShortDescription issue in the content.
        
        Args:
            content: File content.
            filepath: Path to the file (for context).
            
        Returns:
            FixResult with old_string/new_string if successful.
        """
        # Already has abstract?
        if self.ABSTRACT_PATTERN.search(content):
            return FixResult(success=True, method="none", error="Already has abstract")
        
        # Try regex approach first
        result = self._try_regex_fix(content)
        if result.success:
            return result
        
        # Fall back to LLM if available
        if self.llm:
            return self._try_llm_fix(content, filepath)
        
        return FixResult(
            success=False,
            method="none",
            error="Could not find suitable paragraph for abstract"
        )
    
    def _try_regex_fix(self, content: str) -> FixResult:
        """
        Try to fix using regex pattern matching.
        
        This works when there's a clear first paragraph after:
        - Title
        - Content type attribute
        - Any conditional blocks (ifdef/endif)
        - Any include directives
        """
        lines = content.split('\n')
        
        # Find the first content paragraph
        first_para_start = self._find_first_paragraph(lines)
        
        if first_para_start is None:
            return FixResult(
                success=False,
                method="regex",
                error="Could not locate first paragraph"
            )
        
        # Check if the paragraph is actually content (not a directive or empty)
        para_line = lines[first_para_start].strip()
        if not para_line or para_line.startswith(':') or para_line.startswith('['):
            return FixResult(
                success=False,
                method="regex",
                error="First content line is not a paragraph"
            )

        # SEMANTIC VALIDATION: Check if this paragraph is suitable as short description
        # Extract the full paragraph (might span multiple lines)
        paragraph_text = self._extract_paragraph(lines, first_para_start)

        validation = self.validator.validate_short_description(paragraph_text)

        if not validation.is_valid:
            # Paragraph fails semantic validation - needs manual review
            return FixResult(
                success=False,
                method="regex",
                error=f"MANUAL_REVIEW: {validation.error}. {validation.suggestion}"
            )

        # Build the fix
        # We need to add [role="_abstract"] on the line BEFORE the paragraph
        old_string = lines[first_para_start]
        new_string = f'[role="_abstract"]\n{old_string}'

        return FixResult(
            success=True,
            old_string=old_string,
            new_string=new_string,
            method="regex"
        )
    
    def _find_first_paragraph(self, lines: list) -> Optional[int]:
        """
        Find the line number of the first content paragraph.
        
        Skips:
        - Empty lines
        - Comments
        - Attributes (:name: value)
        - Title (= ...)
        - ID blocks ([id="..."])
        - Conditional blocks (ifdef/endif)
        - Include directives
        - Block titles (.Title)
        - Section headings (== ...)
        
        Returns:
            Line index of first paragraph, or None.
        """
        in_conditional = 0  # Nesting level
        found_title = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Skip comments
            if stripped.startswith('//'):
                continue
            
            # Skip attributes
            if stripped.startswith(':') and ':' in stripped[1:]:
                continue
            
            # Track title
            if self.TITLE_PATTERN.match(stripped):
                found_title = True
                continue
            
            # Skip ID blocks
            if stripped.startswith('[id='):
                continue
            
            # Track conditional blocks
            if self.CONDITIONAL_START.match(stripped):
                in_conditional += 1
                continue
            if stripped.startswith('endif::'):
                in_conditional = max(0, in_conditional - 1)
                continue
            
            # Skip include directives
            if stripped.startswith('include::'):
                continue
            
            # Skip block titles (like .Prerequisites, .Procedure)
            if self.BLOCK_TITLE_PATTERN.match(stripped):
                continue
            
            # Skip section headings
            if self.SECTION_PATTERN.match(stripped):
                continue
            
            # Skip attribute blocks that aren't ID
            if stripped.startswith('[') and stripped.endswith(']'):
                continue
            
            # If we're past the title and not in a conditional, this is the paragraph
            if found_title and in_conditional == 0:
                return i
        
        return None
    
    def _try_llm_fix(self, content: str, filepath: Path) -> FixResult:
        """
        Use LLM to find the appropriate paragraph for abstract.
        
        This is used when the structure is unclear and we need
        the LLM to analyze the content.
        """
        prompt = f"""Analyze this AsciiDoc file and find the first content paragraph that should be marked as the abstract (short description).

RULES:
1. The abstract should be the FIRST content paragraph after the title
2. It should NOT be a block title (.Prerequisites, .Procedure, etc.)
3. It should NOT be inside a conditional block that might not always render
4. You must ADD [role="_abstract"] on the line BEFORE the paragraph
5. DO NOT move any content - only add the attribute line

FILE CONTENT:
```asciidoc
{content}
```

If you find a suitable paragraph, respond with JSON:
{{
  "found": true,
  "old_string": "exact text of the paragraph line",
  "new_string": "[role=\\"_abstract\\"]\\nexact text of the paragraph line"
}}

If no suitable paragraph exists (the file might need a new paragraph added), respond:
{{
  "found": false,
  "reason": "explanation"
}}
"""
        
        response = self.llm.generate(
            prompt,
            expect_json=True,
        )
        
        if not response.success:
            return FixResult(
                success=False,
                method="llm",
                error=f"LLM error: {response.error}"
            )
        
        try:
            parsed = response.parsed
            if parsed.get("found"):
                old_string = parsed.get("old_string", "")
                new_string = parsed.get("new_string", "")
                
                # Validate the fix doesn't move content
                if old_string and old_string in content:
                    return FixResult(
                        success=True,
                        old_string=old_string,
                        new_string=new_string,
                        method="llm"
                    )
                else:
                    return FixResult(
                        success=False,
                        method="llm",
                        error="LLM's old_string not found in content"
                    )
            else:
                return FixResult(
                    success=False,
                    method="llm",
                    error=parsed.get("reason", "No suitable paragraph found")
                )
        except Exception as e:
            return FixResult(
                success=False,
                method="llm",
                error=f"Failed to parse LLM response: {e}"
            )

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
