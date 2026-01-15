"""
Session memory module.

Tracks what the agent does during a session:
- Files processed
- Fixes applied
- Errors encountered
- LLM calls and costs

This data is used for:
1. Reporting at end of session
2. Avoiding repeated failed approaches
3. Generating session logs for debugging
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any


class FixStatus(Enum):
    """Status of a fix attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLBACK = "rollback"


class Phase(Enum):
    """Processing phases."""
    CONTENT_TYPE = "phase1_content_type"
    CALLOUTS = "phase2_callouts"
    DITA_ISSUES = "phase3_dita_issues"


@dataclass
class FixAttempt:
    """Record of a single fix attempt."""
    
    file: str
    """Path to the file being fixed."""
    
    phase: str
    """Which phase this fix is part of."""
    
    rule: str
    """The rule being fixed (e.g., 'ShortDescription', 'ContentType')."""
    
    status: str
    """Status: success, failed, skipped, rollback."""
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    """When the fix was attempted."""
    
    llm_used: bool = False
    """Whether LLM was used for this fix."""
    
    tokens_used: int = 0
    """Number of tokens used if LLM was involved."""
    
    error_message: Optional[str] = None
    """Error message if the fix failed."""
    
    retry_count: int = 0
    """Number of retries attempted."""


@dataclass
class PhaseResult:
    """Result of a single phase."""
    
    phase: str
    """Phase identifier."""
    
    files_processed: int = 0
    """Number of files processed."""
    
    fixes_applied: int = 0
    """Number of successful fixes."""
    
    fixes_failed: int = 0
    """Number of failed fixes."""
    
    llm_calls: int = 0
    """Number of LLM API calls."""
    
    tokens_used: int = 0
    """Total tokens used."""
    
    duration_seconds: float = 0.0
    """Time taken for this phase."""
    
    errors: List[str] = field(default_factory=list)
    """Errors encountered."""


@dataclass
class SessionMemory:
    """
    Memory for a single agent session.
    
    Tracks all actions taken during the session for reporting
    and debugging purposes.
    """
    
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    """Unique session identifier."""
    
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    """Session start time."""
    
    end_time: Optional[str] = None
    """Session end time."""
    
    # Scope information
    scope_type: str = "project"
    """Type of scope: project, assembly, topics."""
    
    entry_point: Optional[str] = None
    """Entry point file (assembly or first topic)."""
    
    files_in_scope: List[str] = field(default_factory=list)
    """All files in scope."""
    
    # Phase results
    phase_results: Dict[str, dict] = field(default_factory=dict)
    """Results for each phase."""
    
    # Individual fix attempts
    fix_attempts: List[dict] = field(default_factory=list)
    """Record of all fix attempts."""
    
    # Files that couldn't be fixed
    manual_review_files: List[dict] = field(default_factory=list)
    """Files requiring manual review."""
    
    # Totals
    total_files_processed: int = 0
    total_fixes_applied: int = 0
    total_fixes_failed: int = 0
    total_llm_calls: int = 0
    total_tokens_used: int = 0
    estimated_cost: float = 0.0
    
    def record_scope(
        self,
        scope_type: str,
        files: List[Path],
        entry_point: Optional[Path] = None,
    ):
        """
        Record the resolved scope.
        
        Args:
            scope_type: Type of scope (project, assembly, topics).
            files: List of files in scope.
            entry_point: Entry point file if applicable.
        """
        self.scope_type = scope_type
        self.files_in_scope = [str(f) for f in files]
        if entry_point:
            self.entry_point = str(entry_point)
    
    def start_phase(self, phase: Phase) -> str:
        """
        Mark the start of a phase.
        
        Args:
            phase: The phase starting.
            
        Returns:
            Phase identifier string.
        """
        phase_id = phase.value
        self.phase_results[phase_id] = {
            "phase": phase_id,
            "start_time": datetime.now().isoformat(),
            "files_processed": 0,
            "fixes_applied": 0,
            "fixes_failed": 0,
            "llm_calls": 0,
            "tokens_used": 0,
            "errors": [],
        }
        return phase_id
    
    def end_phase(self, phase: Phase, duration_seconds: float):
        """
        Mark the end of a phase.
        
        Args:
            phase: The phase ending.
            duration_seconds: Duration of the phase.
        """
        phase_id = phase.value
        if phase_id in self.phase_results:
            self.phase_results[phase_id]["end_time"] = datetime.now().isoformat()
            self.phase_results[phase_id]["duration_seconds"] = duration_seconds
    
    def record_fix(
        self,
        filepath: Path,
        phase: Phase,
        rule: str,
        status: FixStatus,
        llm_used: bool = False,
        tokens_used: int = 0,
        error_message: Optional[str] = None,
        retry_count: int = 0,
    ):
        """
        Record a fix attempt.
        
        Args:
            filepath: Path to the file.
            phase: Which phase this fix is part of.
            rule: The rule being fixed.
            status: Status of the fix.
            llm_used: Whether LLM was used.
            tokens_used: Tokens used if LLM was involved.
            error_message: Error message if failed.
            retry_count: Number of retries.
        """
        attempt = FixAttempt(
            file=str(filepath),
            phase=phase.value,
            rule=rule,
            status=status.value,
            llm_used=llm_used,
            tokens_used=tokens_used,
            error_message=error_message,
            retry_count=retry_count,
        )
        self.fix_attempts.append(asdict(attempt))
        
        # Update phase stats
        phase_id = phase.value
        if phase_id in self.phase_results:
            if status == FixStatus.SUCCESS:
                self.phase_results[phase_id]["fixes_applied"] += 1
                self.total_fixes_applied += 1
            elif status == FixStatus.FAILED:
                self.phase_results[phase_id]["fixes_failed"] += 1
                self.total_fixes_failed += 1
            
            if llm_used:
                self.phase_results[phase_id]["llm_calls"] += 1
                self.phase_results[phase_id]["tokens_used"] += tokens_used
                self.total_llm_calls += 1
                self.total_tokens_used += tokens_used
    
    def record_manual_review(
        self,
        filepath: Path,
        rule: str,
        line: int,
        message: str,
        reason: str,
    ):
        """
        Record a file that needs manual review.
        
        Args:
            filepath: Path to the file.
            rule: The rule that couldn't be fixed.
            line: Line number of the issue.
            message: Error message.
            reason: Why auto-fix failed.
        """
        self.manual_review_files.append({
            "file": str(filepath),
            "rule": rule,
            "line": line,
            "message": message,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })
    
    def calculate_cost(self, cost_per_1k_tokens: float = 0.0001):
        """
        Calculate estimated cost based on token usage.
        
        Args:
            cost_per_1k_tokens: Cost per 1000 tokens.
        """
        self.estimated_cost = (self.total_tokens_used / 1000) * cost_per_1k_tokens
    
    def finalize(self):
        """Mark the session as complete."""
        self.end_time = datetime.now().isoformat()
        self.total_files_processed = len(self.files_in_scope)
        self.calculate_cost()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the session.
        
        Returns:
            Dictionary with session summary.
        """
        return {
            "session_id": self.session_id,
            "scope_type": self.scope_type,
            "files_in_scope": len(self.files_in_scope),
            "total_fixes_applied": self.total_fixes_applied,
            "total_fixes_failed": self.total_fixes_failed,
            "manual_review_needed": len(self.manual_review_files),
            "total_llm_calls": self.total_llm_calls,
            "total_tokens_used": self.total_tokens_used,
            "estimated_cost": self.estimated_cost,
            "duration": self._calculate_duration(),
        }
    
    def _calculate_duration(self) -> str:
        """Calculate session duration."""
        if not self.end_time:
            return "In progress"
        
        start = datetime.fromisoformat(self.start_time)
        end = datetime.fromisoformat(self.end_time)
        duration = end - start
        
        total_seconds = int(duration.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def save(self, project_dir: Path) -> Path:
        """
        Save the session memory to disk.
        
        Args:
            project_dir: Project root directory.
            
        Returns:
            Path to the saved file.
        """
        logs_dir = project_dir / ".dita-agent" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = logs_dir / f"session_{self.session_id}.json"
        
        # Convert to dict and save
        data = asdict(self)
        log_file.write_text(json.dumps(data, indent=2))
        
        return log_file
    
    @classmethod
    def load(cls, log_file: Path) -> Optional["SessionMemory"]:
        """
        Load a session memory from disk.
        
        Args:
            log_file: Path to the log file.
            
        Returns:
            SessionMemory instance, or None if loading fails.
        """
        try:
            data = json.loads(log_file.read_text())
            memory = cls()
            
            # Restore attributes
            for key, value in data.items():
                if hasattr(memory, key):
                    setattr(memory, key, value)
            
            return memory
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠ Failed to load session: {e}")
            return None
