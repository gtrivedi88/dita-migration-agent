"""
Phase 2: Callouts Conversion

Converts callout markers (<1>, <2>, etc.) in code blocks to DITA-compatible format.

Flow:
1. DETECT: Find files with callout markers in code blocks
2. SNAPSHOT: Save original state of files
3. RUN TOOL: Execute callouts_orchestrator.py on scoped files
4. LLM REVIEWS TOOL'S FIXES:
   - Compare before/after for each modified file
   - Verify conversion is semantically correct
   - If incorrect → LLM provides corrective fix
5. FOR ISSUES TOOL COULDN'T FIX:
   - LLM attempts targeted fix
   - Up to 3 retries
6. VALIDATE: No callout markers remain?
   - YES → Proceed to Phase 3
   - NO → Add unfixable to MANUAL_REVIEW.md
"""

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dita_agent.core.memory import SessionMemory, Phase, FixStatus
from dita_agent.llm.client import LLMClient, LLMResponse
from dita_agent.llm.prompts import PromptBuilder
from dita_agent.tools.callouts import CalloutsRunner
from dita_agent.utils.file_ops import (
    read_file_safe,
    write_file_safe,
    backup_file,
    restore_file,
)


# Regex patterns for detecting callouts
CALLOUT_IN_CODE_PATTERN = re.compile(r'<(\d+)>')
CALLOUT_LIST_PATTERN = re.compile(r'^<(\d+)>\s+', re.MULTILINE)


@dataclass
class CalloutsPhaseResult:
    """Result of running the callouts phase."""
    
    success: bool
    """Whether the phase completed successfully."""
    
    files_processed: int = 0
    """Total files processed."""
    
    files_fixed_by_tool: int = 0
    """Files fixed by the callouts-conversion tool."""
    
    files_fixed_by_llm: int = 0
    """Files fixed by LLM."""
    
    files_skipped: int = 0
    """Files with no callouts."""
    
    files_failed: int = 0
    """Files that failed to fix."""
    
    total_tokens: int = 0
    """Total tokens used for LLM calls."""
    
    duration_seconds: float = 0.0
    """Time taken for the phase."""
    
    failed_files: List[Tuple[Path, str]] = field(default_factory=list)
    """List of (filepath, error) for failed files."""


class CalloutsPhase:
    """
    Phase 2: Callouts Conversion.
    
    Uses the callouts-conversion tool first, then LLM to review/fix.
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        memory: SessionMemory,
        project_dir: Path,
        max_retries: int = 3,
        dry_run: bool = False,
    ):
        """
        Initialize the phase.
        
        Args:
            llm_client: LLM client for fix generation and review.
            memory: Session memory for tracking.
            project_dir: Project root directory.
            max_retries: Maximum retries per file.
            dry_run: If True, don't modify files.
        """
        self.llm = llm_client
        self.memory = memory
        self.project_dir = project_dir
        self.max_retries = max_retries
        self.dry_run = dry_run
        self.session_id = memory.session_id
        
        # Initialize the callouts-conversion tool
        self.callouts_tool = CalloutsRunner()
    
    def run(self, files: List[Path]) -> CalloutsPhaseResult:
        """
        Run the callouts conversion phase.
        
        Args:
            files: List of files to process.
            
        Returns:
            CalloutsPhaseResult with statistics.
        """
        start_time = time.time()
        
        # Start tracking in memory
        self.memory.start_phase(Phase.CALLOUTS)
        
        result = CalloutsPhaseResult(success=True)
        
        # Step 1: Find files with callouts
        files_with_callouts = self._find_files_with_callouts(files)
        
        if not files_with_callouts:
            result.files_skipped = len(files)
            result.duration_seconds = time.time() - start_time
            self.memory.end_phase(Phase.CALLOUTS, result.duration_seconds)
            return result
        
        result.files_skipped = len(files) - len(files_with_callouts)
        
        # Step 2: Create backups
        backups: Dict[Path, Path] = {}
        original_content: Dict[Path, str] = {}
        
        for filepath in files_with_callouts:
            content, _ = read_file_safe(filepath)
            if content:
                original_content[filepath] = content
                if not self.dry_run:
                    backup_path = backup_file(filepath, self.project_dir, self.session_id)
                    if backup_path:
                        backups[filepath] = backup_path
        
        # Step 3: Run the callouts-conversion tool
        if self.callouts_tool.is_available() and not self.dry_run:
            tool_result = self.callouts_tool.run(files_with_callouts)
            
            if tool_result.success:
                # Track which files were modified by the tool
                for filepath in tool_result.files_modified:
                    result.files_fixed_by_tool += 1
                    result.files_processed += 1
                    
                    # Record fix
                    self.memory.record_fix(
                        filepath=filepath,
                        phase=Phase.CALLOUTS,
                        rule="CalloutList",
                        status=FixStatus.SUCCESS,
                        llm_used=False,
                    )
        
        # Step 4: LLM reviews tool's fixes and fixes remaining issues
        for i, filepath in enumerate(files_with_callouts):
            result.files_processed += 1
            
            # Read current content
            current_content, _ = read_file_safe(filepath)
            if not current_content:
                continue
            
            # Check if callouts still remain
            has_callouts = self._has_callouts(current_content)
            if not has_callouts:
                # Tool fixed it completely
                if filepath not in [f for f, _ in result.failed_files]:
                    continue
            
            # FAST CLASSIFICATION: Determine complexity BEFORE attempting LLM fixes
            classification, unfixable_reason = self._classify_callouts(current_content)
            
            if classification == "unfixable":
                # Skip LLM entirely - flag for manual review immediately
                result.files_failed += 1
                result.failed_files.append((filepath, unfixable_reason))
                
                self.memory.record_manual_review(
                    filepath=filepath,
                    rule="CalloutList",
                    line=self._find_first_callout_line(current_content),
                    message="Callout conversion requires manual restructuring",
                    reason=unfixable_reason,
                )
                continue
            
            # Step 4a: If tool modified the file, have LLM review it
            if filepath in original_content and original_content[filepath] != current_content:
                review_result = self._llm_review_tool_fix(
                    filepath,
                    original_content[filepath],
                    current_content,
                )
                
                if review_result.success:
                    result.total_tokens += review_result.tokens_used
                    # Re-check if callouts remain after tool fix
                    current_content, _ = read_file_safe(filepath)
                    if not self._has_callouts(current_content):
                        continue
            
            # Step 4b: LLM fixes remaining callouts (simple or basic_conditional)
            fix_result = self._llm_fix_callouts(filepath, current_content)
            result.total_tokens += fix_result.tokens_used
            
            if fix_result.success:
                result.files_fixed_by_llm += 1
                self.memory.record_fix(
                    filepath=filepath,
                    phase=Phase.CALLOUTS,
                    rule="CalloutList",
                    status=FixStatus.SUCCESS,
                    llm_used=True,
                    tokens_used=fix_result.tokens_used,
                )
            else:
                result.files_failed += 1
                result.failed_files.append((filepath, fix_result.error or "Unknown error"))
                
                # Restore backup
                if filepath in backups:
                    restore_file(filepath, backups[filepath])
                
                self.memory.record_fix(
                    filepath=filepath,
                    phase=Phase.CALLOUTS,
                    rule="CalloutList",
                    status=FixStatus.FAILED,
                    llm_used=True,
                    error_message=fix_result.error,
                )
                
                # Record for manual review
                self.memory.record_manual_review(
                    filepath=filepath,
                    rule="CalloutList",
                    line=self._find_first_callout_line(current_content),
                    message="Callout markers in code blocks are not DITA-compatible",
                    reason=fix_result.error or "Could not convert callouts",
                )
        
        # Calculate duration
        result.duration_seconds = time.time() - start_time
        
        # End phase tracking
        self.memory.end_phase(Phase.CALLOUTS, result.duration_seconds)
        
        # Determine overall success
        result.success = result.files_failed == 0
        
        return result
    
    def _find_files_with_callouts(self, files: List[Path]) -> List[Path]:
        """
        Find files that contain callout markers.
        
        Args:
            files: List of files to check.
            
        Returns:
            List of files with callouts.
        """
        result = []
        for filepath in files:
            content, _ = read_file_safe(filepath)
            if content and self._has_callouts(content):
                result.append(filepath)
        return result
    
    def _classify_callouts(self, content: str) -> Tuple[str, Optional[str]]:
        """
        Classify callouts by complexity to route appropriately.
        
        Returns:
            Tuple of (classification, reason)
            - "simple": No conditionals, tool can handle
            - "basic_conditional": Single conditionals, LLM can fix
            - "unfixable": Duplicate markers in conditionals, needs manual review
        """
        # Check for conditionals
        has_conditionals = bool(re.search(r'(ifdef|ifndef|ifeval)::', content))
        
        if not has_conditionals:
            return ("simple", None)
        
        # Check for duplicate callout markers in different conditional branches
        # Pattern: same <N> appears multiple times in definition area (after ----)
        callout_defs = re.findall(r'^<(\d+)>\s', content, re.MULTILINE)
        if len(callout_defs) != len(set(callout_defs)):
            duplicates = [m for m in callout_defs if callout_defs.count(m) > 1]
            return ("unfixable", f"Duplicate callout markers <{duplicates[0]}> in conditional branches - requires manual restructuring")
        
        # Check for callout definitions inside conditionals
        # Pattern: ifdef/ifndef followed by <N> before endif
        conditional_callout = re.search(
            r'(ifdef|ifndef)::[^\]]*\].*?<\d+>.*?endif::',
            content,
            re.DOTALL
        )
        
        if conditional_callout:
            return ("basic_conditional", None)
        
        return ("simple", None)
    
    def _has_callouts(self, content: str) -> bool:
        """
        Check if content has callout markers.
        
        Args:
            content: File content to check.
            
        Returns:
            True if callout markers are present.
        """
        return bool(CALLOUT_IN_CODE_PATTERN.search(content))
    
    def _find_first_callout_line(self, content: str) -> int:
        """
        Find the line number of the first callout marker.
        
        Args:
            content: File content.
            
        Returns:
            Line number (1-based) or 1 if not found.
        """
        for i, line in enumerate(content.split('\n'), 1):
            if CALLOUT_IN_CODE_PATTERN.search(line):
                return i
        return 1
    
    def _llm_review_tool_fix(
        self,
        filepath: Path,
        original: str,
        modified: str,
    ) -> 'CalloutFixResult':
        """
        Have LLM review the tool's fix.
        
        Args:
            filepath: Path to the file.
            original: Original content.
            modified: Modified content.
            
        Returns:
            CalloutFixResult with result.
        """
        # Build review prompt
        prompt = PromptBuilder.callouts_review_prompt(
            original=original,
            modified=modified,
            filename=filepath.name,
        )
        
        # Get LLM response
        response = self.llm.generate(
            prompt,
            system_prompt=PromptBuilder.get_system_prompt(),
            expect_json=True,
        )
        
        if not response.success:
            return CalloutFixResult(
                success=False,
                error=f"LLM review error: {response.error}",
                tokens_used=response.tokens_used,
            )
        
        try:
            parsed = response.parsed
            is_correct = parsed.get("is_correct", True)
            
            if is_correct:
                return CalloutFixResult(
                    success=True,
                    tokens_used=response.tokens_used,
                )
            
            # Tool's fix was incorrect - apply LLM's correction
            if parsed.get("fix_needed", False):
                old_string = parsed.get("old_string", "")
                new_string = parsed.get("new_string", "")
                
                if old_string and new_string and old_string in modified:
                    if not self.dry_run:
                        corrected = modified.replace(old_string, new_string, 1)
                        write_file_safe(filepath, corrected)
                    
                    return CalloutFixResult(
                        success=True,
                        tokens_used=response.tokens_used,
                    )
            
            return CalloutFixResult(
                success=False,
                error="LLM indicated fix was incorrect but couldn't provide correction",
                tokens_used=response.tokens_used,
            )
            
        except (KeyError, TypeError) as e:
            return CalloutFixResult(
                success=False,
                error=f"Failed to parse LLM review: {e}",
                tokens_used=response.tokens_used,
            )
    
    def _llm_fix_callouts(
        self,
        filepath: Path,
        content: str,
    ) -> 'CalloutFixResult':
        """
        Use LLM to fix ALL callouts in a file in ONE request.
        
        Args:
            filepath: Path to the file.
            content: Current file content.
            
        Returns:
            CalloutFixResult with result.
        """
        total_tokens = 0
        
        
        for attempt in range(self.max_retries):
            
            # Build prompt asking LLM to fix ALL callouts at once
            prompt = self._build_all_callouts_prompt(content, filepath.name)
            
            # Get LLM response
            response = self.llm.generate(
                prompt,
                system_prompt=PromptBuilder.get_system_prompt(),
                expect_json=True,
            )
            total_tokens += response.tokens_used
            
            if not response.success:
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                    continue
                return CalloutFixResult(
                    success=False,
                    error=f"LLM error: {response.error}",
                    tokens_used=total_tokens,
                )
            
            try:
                parsed = response.parsed
                edits = parsed.get("edits", [])
                
                if not edits:
                    # LLM returned no edits - might be already fixed or unfixable
                    return CalloutFixResult(
                        success=True,
                        tokens_used=total_tokens,
                    )
                
                # Apply ALL edits
                new_content = content
                applied = 0
                for edit in edits:
                    old_string = edit.get("old_string", "")
                    new_string = edit.get("new_string", "")
                    
                    if old_string and old_string in new_content:
                        new_content = new_content.replace(old_string, new_string, 1)
                        applied += 1
                
                if applied == 0:
                    if attempt < self.max_retries - 1:
                        time.sleep(1)
                        continue
                    return CalloutFixResult(
                        success=False,
                        error="No edits could be applied",
                        tokens_used=total_tokens,
                    )
                
                # Verify fix didn't break anything
                if len(new_content) < len(content) * 0.5:
                    return CalloutFixResult(
                        success=False,
                        error="Fix caused significant content loss",
                        tokens_used=total_tokens,
                    )
                
                if not self.dry_run:
                    write_file_safe(filepath, new_content)
                
                return CalloutFixResult(
                    success=True,
                    tokens_used=total_tokens,
                )
                
            except (KeyError, TypeError) as e:
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                    continue
                return CalloutFixResult(
                    success=False,
                    error=f"Failed to parse LLM response: {e}",
                    tokens_used=total_tokens,
                )
        
        return CalloutFixResult(
            success=False,
            error="Max retries exceeded",
            tokens_used=total_tokens,
        )
    
    def _build_all_callouts_prompt(self, content: str, filename: str) -> str:
        """Build prompt to fix ALL callouts for DITA compatibility."""
        return f'''Convert AsciiDoc callouts to DITA-compatible format per Red Hat style guide.

CALLOUTS ARE NOT SUPPORTED IN DITA. Convert them to definition lists.

CONVERSION RULES:
1. INSIDE CODE BLOCKS: Remove `<1>`, `<2>` etc. from the end of lines
2. CALLOUT EXPLANATIONS: Convert `<1> Explanation` to `variablename:: Explanation`
   - Use the actual variable/field name from the code as the definition term
   - Example: `<1> Defines the namespace` for `namespace: foo <1>` becomes `namespace:: Defines the namespace`

CRITICAL - PRESERVE THESE (DO NOT MODIFY):
- The `+` character (AsciiDoc list continuation) - NEVER remove
- All `ifdef::`, `ifndef::`, `endif::` conditional directives
- All indentation and formatting
- Empty lines

FILE: {filename}

CONTENT:
```
{content}
```

Return JSON with "edits" array. Each edit needs:
- "old_string": Exact text to find (include context for uniqueness)
- "new_string": Replacement (preserve surrounding structure)

Example input:
```
  namespace: redhat-ods-operator <1>
----
+
<1> Defines the operator namespace.
```

Example output:
{{
  "edits": [
    {{"old_string": "namespace: redhat-ods-operator <1>\\n----", "new_string": "namespace: redhat-ods-operator\\n----"}},
    {{"old_string": "+\\n<1> Defines the operator namespace.", "new_string": "+\\nnamespace:: Defines the operator namespace."}}
  ]
}}

IMPORTANT: 
- The `+` on its own line MUST be preserved - it's an AsciiDoc list continuation
- Return {{"edits": []}} if no callouts found
'''
    
    def _extract_callout_context(self, content: str, line_num: int, context_lines: int = 20) -> str:
        """
        Extract context around a callout for the LLM.
        
        Args:
            content: Full file content.
            line_num: Line number of the callout.
            context_lines: Number of lines to include.
            
        Returns:
            Context string.
        """
        lines = content.split('\n')
        start = max(0, line_num - context_lines // 2)
        end = min(len(lines), line_num + context_lines // 2)
        return '\n'.join(lines[start:end])
    
    def validate(self, files: List[Path]) -> Tuple[bool, List[Path]]:
        """
        Validate that no callout markers remain.
        
        Args:
            files: List of files to validate.
            
        Returns:
            Tuple of (all_valid, files_with_callouts).
        """
        files_with_callouts = self._find_files_with_callouts(files)
        return (len(files_with_callouts) == 0, files_with_callouts)


@dataclass
class CalloutFixResult:
    """Result of a callout fix attempt."""
    
    success: bool
    """Whether the fix was successful."""
    
    error: Optional[str] = None
    """Error message if failed."""
    
    tokens_used: int = 0
    """Tokens used for LLM calls."""
