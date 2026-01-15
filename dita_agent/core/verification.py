"""
Verification module for ensuring fix quality.

Provides checks for:
- Content loss detection
- Conditional block validation  
- Regression detection
- Syntax validation
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dita_agent.utils.file_ops import read_file_safe


# Patterns for conditional blocks
CONDITIONAL_PATTERNS = [
    re.compile(r'ifdef::(\w+)\[\]', re.MULTILINE),
    re.compile(r'ifndef::(\w+)\[\]', re.MULTILINE),
    re.compile(r'ifeval::\[(.*?)\]', re.MULTILINE),
    re.compile(r'endif::\[\]', re.MULTILINE),
]

# Pattern for AsciiDoc title
TITLE_PATTERN = re.compile(r'^=\s+.+', re.MULTILINE)

# Pattern for include directives
INCLUDE_PATTERN = re.compile(r'^include::(.+)\[.*\]', re.MULTILINE)


@dataclass
class VerificationResult:
    """Result of a verification check."""
    
    passed: bool
    """Whether the verification passed."""
    
    issues: List[str]
    """List of issues found."""
    
    severity: str = "error"
    """Severity level: error, warning, info."""


@dataclass
class ContentIntegrityReport:
    """Report on content integrity after modifications."""
    
    file_path: Path
    """Path to the file."""
    
    original_lines: int
    """Original line count."""
    
    modified_lines: int
    """Modified line count."""
    
    line_diff_percent: float
    """Percentage change in lines."""
    
    original_chars: int
    """Original character count."""
    
    modified_chars: int
    """Modified character count."""
    
    char_diff_percent: float
    """Percentage change in characters."""
    
    conditionals_preserved: bool
    """Whether all conditionals were preserved."""
    
    title_preserved: bool
    """Whether the document title was preserved."""
    
    includes_preserved: bool
    """Whether all include directives were preserved."""


class Verifier:
    """
    Verifies fix quality and content integrity.
    """
    
    # Thresholds for content loss detection
    MAX_LINE_LOSS_PERCENT = 20.0  # Fail if more than 20% lines lost
    MAX_CHAR_LOSS_PERCENT = 30.0  # Fail if more than 30% chars lost
    
    def __init__(self):
        """Initialize the verifier."""
        pass
    
    def verify_content_integrity(
        self,
        original: str,
        modified: str,
        filepath: Optional[Path] = None,
    ) -> VerificationResult:
        """
        Verify that content integrity is maintained after a fix.
        
        Args:
            original: Original file content.
            modified: Modified file content.
            filepath: Optional file path for reporting.
            
        Returns:
            VerificationResult with pass/fail and issues.
        """
        issues = []
        
        # Check line count
        orig_lines = len(original.split('\n'))
        mod_lines = len(modified.split('\n'))
        line_diff = (orig_lines - mod_lines) / orig_lines * 100 if orig_lines > 0 else 0
        
        if line_diff > self.MAX_LINE_LOSS_PERCENT:
            issues.append(
                f"Significant line loss: {line_diff:.1f}% ({orig_lines} → {mod_lines})"
            )
        
        # Check character count
        orig_chars = len(original)
        mod_chars = len(modified)
        char_diff = (orig_chars - mod_chars) / orig_chars * 100 if orig_chars > 0 else 0
        
        if char_diff > self.MAX_CHAR_LOSS_PERCENT:
            issues.append(
                f"Significant content loss: {char_diff:.1f}% ({orig_chars} → {mod_chars} chars)"
            )
        
        # Check conditionals preserved
        cond_result = self.verify_conditionals(original, modified)
        if not cond_result.passed:
            issues.extend(cond_result.issues)
        
        # Check title preserved
        title_result = self.verify_title_preserved(original, modified)
        if not title_result.passed:
            issues.extend(title_result.issues)
        
        # Check includes preserved
        inc_result = self.verify_includes_preserved(original, modified)
        if not inc_result.passed:
            issues.extend(inc_result.issues)
        
        return VerificationResult(
            passed=len(issues) == 0,
            issues=issues,
            severity="error" if issues else "info",
        )
    
    def verify_conditionals(
        self,
        original: str,
        modified: str,
    ) -> VerificationResult:
        """
        Verify that conditional blocks are preserved.
        
        Args:
            original: Original content.
            modified: Modified content.
            
        Returns:
            VerificationResult.
        """
        issues = []
        
        # Extract conditional blocks from both
        orig_conds = self._extract_conditionals(original)
        mod_conds = self._extract_conditionals(modified)
        
        # Check for missing conditionals
        for cond_type, cond_values in orig_conds.items():
            mod_values = mod_conds.get(cond_type, [])
            
            for value in cond_values:
                if value not in mod_values:
                    issues.append(f"Missing conditional: {cond_type}::{value}")
        
        # Check for balance (ifdef/endif pairs)
        orig_balance = self._check_conditional_balance(original)
        mod_balance = self._check_conditional_balance(modified)
        
        if not mod_balance and orig_balance:
            issues.append("Conditional blocks are unbalanced after modification")
        
        return VerificationResult(
            passed=len(issues) == 0,
            issues=issues,
        )
    
    def verify_title_preserved(
        self,
        original: str,
        modified: str,
    ) -> VerificationResult:
        """
        Verify that the document title is preserved.
        
        Args:
            original: Original content.
            modified: Modified content.
            
        Returns:
            VerificationResult.
        """
        issues = []
        
        orig_title = TITLE_PATTERN.search(original)
        mod_title = TITLE_PATTERN.search(modified)
        
        if orig_title and not mod_title:
            issues.append("Document title was removed")
        elif orig_title and mod_title:
            # Titles should be similar (allow minor edits)
            orig_text = orig_title.group(0).strip()
            mod_text = mod_title.group(0).strip()
            
            # Just check the main title text (after = )
            orig_title_text = orig_text.lstrip('= ').strip()
            mod_title_text = mod_text.lstrip('= ').strip()
            
            # Allow the title to remain or be very similar
            # (we're not requiring exact match, just that it exists)
        
        return VerificationResult(
            passed=len(issues) == 0,
            issues=issues,
        )
    
    def verify_includes_preserved(
        self,
        original: str,
        modified: str,
    ) -> VerificationResult:
        """
        Verify that include directives are preserved.
        
        Args:
            original: Original content.
            modified: Modified content.
            
        Returns:
            VerificationResult.
        """
        issues = []
        
        orig_includes = set(INCLUDE_PATTERN.findall(original))
        mod_includes = set(INCLUDE_PATTERN.findall(modified))
        
        missing = orig_includes - mod_includes
        for inc in missing:
            issues.append(f"Missing include directive: {inc}")
        
        return VerificationResult(
            passed=len(issues) == 0,
            issues=issues,
        )
    
    def verify_syntax(self, content: str) -> VerificationResult:
        """
        Basic syntax verification for AsciiDoc.
        
        Args:
            content: File content to verify.
            
        Returns:
            VerificationResult.
        """
        issues = []
        
        # Check for common syntax errors
        lines = content.split('\n')
        
        # Check for unclosed blocks
        block_markers = ['----', '....', '====', '++++', '****']
        for marker in block_markers:
            count = content.count('\n' + marker + '\n') + content.count(marker + '\n')
            if count % 2 != 0:
                issues.append(f"Unclosed block with marker '{marker}'")
        
        # Check for unbalanced conditionals
        if not self._check_conditional_balance(content):
            issues.append("Unbalanced conditional blocks (ifdef/endif)")
        
        return VerificationResult(
            passed=len(issues) == 0,
            issues=issues,
            severity="warning",
        )
    
    def get_integrity_report(
        self,
        filepath: Path,
        original: str,
        modified: str,
    ) -> ContentIntegrityReport:
        """
        Generate a detailed content integrity report.
        
        Args:
            filepath: Path to the file.
            original: Original content.
            modified: Modified content.
            
        Returns:
            ContentIntegrityReport.
        """
        orig_lines = len(original.split('\n'))
        mod_lines = len(modified.split('\n'))
        orig_chars = len(original)
        mod_chars = len(modified)
        
        line_diff = ((mod_lines - orig_lines) / orig_lines * 100) if orig_lines > 0 else 0
        char_diff = ((mod_chars - orig_chars) / orig_chars * 100) if orig_chars > 0 else 0
        
        cond_result = self.verify_conditionals(original, modified)
        title_result = self.verify_title_preserved(original, modified)
        inc_result = self.verify_includes_preserved(original, modified)
        
        return ContentIntegrityReport(
            file_path=filepath,
            original_lines=orig_lines,
            modified_lines=mod_lines,
            line_diff_percent=line_diff,
            original_chars=orig_chars,
            modified_chars=mod_chars,
            char_diff_percent=char_diff,
            conditionals_preserved=cond_result.passed,
            title_preserved=title_result.passed,
            includes_preserved=inc_result.passed,
        )
    
    def _extract_conditionals(self, content: str) -> Dict[str, List[str]]:
        """Extract conditional blocks from content."""
        result: Dict[str, List[str]] = {
            'ifdef': [],
            'ifndef': [],
            'ifeval': [],
            'endif': [],
        }
        
        for match in re.finditer(r'ifdef::(\w+)\[\]', content):
            result['ifdef'].append(match.group(1))
        
        for match in re.finditer(r'ifndef::(\w+)\[\]', content):
            result['ifndef'].append(match.group(1))
        
        for match in re.finditer(r'ifeval::\[(.*?)\]', content):
            result['ifeval'].append(match.group(1))
        
        result['endif'] = [''] * len(re.findall(r'endif::\[\]', content))
        
        return result
    
    def _check_conditional_balance(self, content: str) -> bool:
        """Check if conditional blocks are balanced."""
        opens = (
            len(re.findall(r'ifdef::', content)) +
            len(re.findall(r'ifndef::', content)) +
            len(re.findall(r'ifeval::', content))
        )
        closes = len(re.findall(r'endif::', content))
        
        return opens == closes
