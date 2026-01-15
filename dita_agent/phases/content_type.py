"""
Phase 1: Content Type Assignment

Ensures every AsciiDoc file has the :_mod-docs-content-type: attribute set correctly.

Flow:
1. SCAN: Find files missing :_mod-docs-content-type: attribute
2. FOR EACH file:
   a. Read file content
   b. Send to LLM with content type rules
   c. LLM returns: content_type + targeted edit
   d. Apply edit: Add :_mod-docs-content-type: <TYPE> at file start
   e. Verify syntax
3. VALIDATE: All files have :_mod-docs-content-type:?
   - YES → Proceed to Phase 2
   - NO → Retry (up to 3 attempts) or add to MANUAL_REVIEW.md
"""

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dita_agent.core.memory import SessionMemory, Phase, FixStatus
from dita_agent.knowledge.content_types import (
    ContentType,
    CONTENT_TYPE_RULES,
    detect_content_type_heuristic,
)
from dita_agent.llm.client import LLMClient, TargetedEdit
from dita_agent.llm.prompts import PromptBuilder
from dita_agent.utils.file_ops import (
    read_file_safe,
    write_file_safe,
    backup_file,
    restore_file,
)


# Regex to find :_mod-docs-content-type: attribute (new format)
MODULE_TYPE_PATTERN = re.compile(r'^:_mod-docs-content-type:\s*(\w+)', re.MULTILINE)

# Regex to find OLD :_module-type: attribute (deprecated format - needs replacement)
OLD_MODULE_TYPE_PATTERN = re.compile(r'^:_module-type:\s*(\w+)', re.MULTILINE)


@dataclass
class ContentTypeResult:
    """Result of processing a single file."""
    
    filepath: Path
    """Path to the file."""
    
    success: bool
    """Whether the fix was applied successfully."""
    
    content_type: Optional[str] = None
    """The content type assigned."""
    
    already_had_type: bool = False
    """Whether the file already had a content type."""
    
    error: Optional[str] = None
    """Error message if failed."""
    
    tokens_used: int = 0
    """Tokens used for LLM call."""


@dataclass
class PhaseResult:
    """Result of running the entire phase."""
    
    success: bool
    """Whether the phase completed successfully."""
    
    files_processed: int = 0
    """Total files processed."""
    
    files_fixed: int = 0
    """Files that were fixed."""
    
    files_skipped: int = 0
    """Files skipped (already had type)."""
    
    files_failed: int = 0
    """Files that failed to fix."""
    
    total_tokens: int = 0
    """Total tokens used."""
    
    duration_seconds: float = 0.0
    """Time taken for the phase."""
    
    failed_files: List[Tuple[Path, str]] = field(default_factory=list)
    """List of (filepath, error) for failed files."""


class ContentTypePhase:
    """
    Phase 1: Content Type Assignment.
    
    Adds :_mod-docs-content-type: attribute to all files in scope.
    Uses LLM to analyze content and determine the correct type.
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
            llm_client: LLM client for content type detection.
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
    
    def run(self, files: List[Path]) -> PhaseResult:
        """
        Run the content type assignment phase.
        
        Args:
            files: List of files to process.
            
        Returns:
            PhaseResult with statistics.
        """
        start_time = time.time()
        
        # Start tracking in memory
        self.memory.start_phase(Phase.CONTENT_TYPE)
        
        result = PhaseResult(success=True)
        
        for filepath in files:
            file_result = self._process_file(filepath)
            
            result.files_processed += 1
            result.total_tokens += file_result.tokens_used
            
            if file_result.already_had_type:
                result.files_skipped += 1
            elif file_result.success:
                result.files_fixed += 1
            else:
                result.files_failed += 1
                result.failed_files.append((filepath, file_result.error or "Unknown error"))
        
        # Calculate duration
        result.duration_seconds = time.time() - start_time
        
        # End phase tracking
        self.memory.end_phase(Phase.CONTENT_TYPE, result.duration_seconds)
        
        # Determine overall success
        result.success = result.files_failed == 0
        
        return result
    
    def _process_file(self, filepath: Path) -> ContentTypeResult:
        """
        Process a single file.
        
        Args:
            filepath: Path to the file.
            
        Returns:
            ContentTypeResult with result.
        """
        # Read file content
        content, error = read_file_safe(filepath)
        if error:
            return ContentTypeResult(
                filepath=filepath,
                success=False,
                error=f"Could not read file: {error}",
            )
        
        # Check if file already has :_mod-docs-content-type: (new format)
        existing_type = self._get_existing_type(content)
        if existing_type:
            return ContentTypeResult(
                filepath=filepath,
                success=True,
                content_type=existing_type,
                already_had_type=True,
            )
        
        # Check if file has OLD :_module-type: (deprecated format) - replace it!
        old_type = self._has_old_format(content)
        if old_type:
            if not self.dry_run:
                # Create backup
                backup_path = backup_file(filepath, self.project_dir, self.session_id)
                
                # Replace old format with new format
                new_content = self._replace_old_format(content)
                
                # Write the file
                write_error = write_file_safe(filepath, new_content)
                if write_error:
                    if backup_path:
                        restore_file(filepath, backup_path)
                    return ContentTypeResult(
                        filepath=filepath,
                        success=False,
                        error=f"Could not write file: {write_error}",
                    )
            
            # Record success
            self.memory.record_fix(
                filepath=filepath,
                phase=Phase.CONTENT_TYPE,
                rule="ContentType",
                status=FixStatus.SUCCESS,
                llm_used=False,  # No LLM needed - just format conversion
                tokens_used=0,
            )
            
            return ContentTypeResult(
                filepath=filepath,
                success=True,
                content_type=old_type,
                already_had_type=False,  # We fixed it, count as fixed
            )
        
        # Try to fix with retries
        for attempt in range(self.max_retries):
            result = self._try_fix(filepath, content, attempt)
            
            if result.success:
                # Record success in memory
                self.memory.record_fix(
                    filepath=filepath,
                    phase=Phase.CONTENT_TYPE,
                    rule="ContentType",
                    status=FixStatus.SUCCESS,
                    llm_used=True,
                    tokens_used=result.tokens_used,
                )
                return result
            
            # Wait before retry
            if attempt < self.max_retries - 1:
                time.sleep(1)
        
        # All retries failed
        self.memory.record_fix(
            filepath=filepath,
            phase=Phase.CONTENT_TYPE,
            rule="ContentType",
            status=FixStatus.FAILED,
            llm_used=True,
            error_message=result.error,
            retry_count=self.max_retries,
        )
        
        # Record for manual review
        self.memory.record_manual_review(
            filepath=filepath,
            rule="ContentType",
            line=1,
            message="Missing :_mod-docs-content-type: attribute",
            reason=result.error or "LLM could not determine content type",
        )
        
        return result
    
    def _try_fix(
        self,
        filepath: Path,
        content: str,
        attempt: int,
    ) -> ContentTypeResult:
        """
        Try to fix a file (single attempt).
        
        Args:
            filepath: Path to the file.
            content: Current file content.
            attempt: Attempt number (0-based).
            
        Returns:
            ContentTypeResult with result.
        """
        # Build prompt
        prompt = PromptBuilder.content_type_prompt(
            file_content=content,
            filename=filepath.name,
        )
        
        # Get LLM response
        response = self.llm.generate(
            prompt,
            system_prompt=PromptBuilder.get_system_prompt(),
            expect_json=True,
        )
        
        tokens_used = response.tokens_used
        
        if not response.success:
            return ContentTypeResult(
                filepath=filepath,
                success=False,
                error=f"LLM error: {response.error}",
                tokens_used=tokens_used,
            )
        
        # Extract content type and edit
        try:
            parsed = response.parsed
            content_type = parsed.get("content_type", "").upper()
            
            # Validate content type
            if content_type not in [ct.value for ct in ContentType]:
                return ContentTypeResult(
                    filepath=filepath,
                    success=False,
                    error=f"Invalid content type: {content_type}",
                    tokens_used=tokens_used,
                )
            
            # Get the edit
            edit_data = parsed.get("edit", parsed)
            old_string = edit_data.get("old_string", "")
            new_string = edit_data.get("new_string", "")
            
            if not old_string or not new_string:
                # Try to create edit manually
                edit = self._create_fallback_edit(content, content_type)
                if edit:
                    old_string, new_string = edit
                else:
                    return ContentTypeResult(
                        filepath=filepath,
                        success=False,
                        error="LLM did not return valid edit",
                        tokens_used=tokens_used,
                    )
            
            # Verify old_string exists in content
            if old_string not in content:
                # Try fallback
                edit = self._create_fallback_edit(content, content_type)
                if edit:
                    old_string, new_string = edit
                else:
                    return ContentTypeResult(
                        filepath=filepath,
                        success=False,
                        error="old_string not found in file content",
                        tokens_used=tokens_used,
                    )
            
            # Apply the edit
            if self.dry_run:
                return ContentTypeResult(
                    filepath=filepath,
                    success=True,
                    content_type=content_type,
                    tokens_used=tokens_used,
                )
            
            # Create backup
            backup_path = backup_file(filepath, self.project_dir, self.session_id)
            
            # Apply edit
            new_content = content.replace(old_string, new_string, 1)
            
            # Verify the edit added the attribute
            if not self._get_existing_type(new_content):
                # Restore backup
                if backup_path:
                    restore_file(filepath, backup_path)
                return ContentTypeResult(
                    filepath=filepath,
                    success=False,
                    error="Edit did not add :_mod-docs-content-type: attribute",
                    tokens_used=tokens_used,
                )
            
            # Write the file
            write_error = write_file_safe(filepath, new_content)
            if write_error:
                # Restore backup
                if backup_path:
                    restore_file(filepath, backup_path)
                return ContentTypeResult(
                    filepath=filepath,
                    success=False,
                    error=f"Could not write file: {write_error}",
                    tokens_used=tokens_used,
                )
            
            return ContentTypeResult(
                filepath=filepath,
                success=True,
                content_type=content_type,
                tokens_used=tokens_used,
            )
            
        except (KeyError, TypeError, AttributeError) as e:
            return ContentTypeResult(
                filepath=filepath,
                success=False,
                error=f"Failed to parse LLM response: {e}",
                tokens_used=tokens_used,
            )
    
    def _get_existing_type(self, content: str) -> Optional[str]:
        """
        Check if content already has :_mod-docs-content-type: attribute.
        
        Args:
            content: File content.
            
        Returns:
            Content type string if found, None otherwise.
        """
        match = MODULE_TYPE_PATTERN.search(content)
        if match:
            return match.group(1).upper()
        return None
    
    def _has_old_format(self, content: str) -> Optional[str]:
        """
        Check if content has OLD :_module-type: attribute (deprecated).
        
        Args:
            content: File content.
            
        Returns:
            Content type string if found, None otherwise.
        """
        match = OLD_MODULE_TYPE_PATTERN.search(content)
        if match:
            return match.group(1).upper()
        return None
    
    def _replace_old_format(self, content: str) -> str:
        """
        Replace OLD :_module-type: with :_mod-docs-content-type:.
        
        Args:
            content: File content.
            
        Returns:
            Updated content with new attribute format.
        """
        return OLD_MODULE_TYPE_PATTERN.sub(r':_mod-docs-content-type: \1', content)
    
    def _create_fallback_edit(
        self,
        content: str,
        content_type: str,
    ) -> Optional[Tuple[str, str]]:
        """
        Create a fallback edit when LLM's edit doesn't work.
        
        IMPORTANT: :_mod-docs-content-type: MUST be at the VERY FIRST LINE of the file.
        Nothing should come before it.
        
        Args:
            content: File content.
            content_type: Content type to add.
            
        Returns:
            Tuple of (old_string, new_string) or None if can't create.
        """
        if not content.strip():
            return None
        
        # Get the first line of the file
        first_line = content.split('\n')[0]
        
        # :_mod-docs-content-type: MUST be at the very first line
        # Replace first line with: attribute + blank line + first line
        old_string = first_line
        new_string = f":_mod-docs-content-type: {content_type}\n\n{first_line}"
        
        return (old_string, new_string)
    
    def get_files_missing_type(self, files: List[Path]) -> List[Path]:
        """
        Get list of files missing :_mod-docs-content-type: attribute.
        
        Args:
            files: List of files to check.
            
        Returns:
            List of files missing the attribute.
        """
        missing = []
        for filepath in files:
            content, _ = read_file_safe(filepath)
            if content and not self._get_existing_type(content):
                missing.append(filepath)
        return missing
    
    def validate(self, files: List[Path]) -> Tuple[bool, List[Path]]:
        """
        Validate that all files have :_mod-docs-content-type: attribute.
        
        Args:
            files: List of files to validate.
            
        Returns:
            Tuple of (all_valid, files_missing_type).
        """
        missing = self.get_files_missing_type(files)
        return (len(missing) == 0, missing)
