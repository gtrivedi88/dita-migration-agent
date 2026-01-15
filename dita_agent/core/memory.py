"""
Enhanced Session Memory with Learning Capabilities.

Key features:
1. Rule-first issue tracking (grouped by rule, not file)
2. Fix pattern learning and propagation
3. Checkpointing for resumability
4. Cross-session pattern storage (optional)
"""

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class FixStatus(Enum):
    """Status of a fix attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLBACK = "rollback"
    MANUAL_REVIEW = "manual_review"


class Phase(Enum):
    """Processing phases."""
    CONTENT_TYPE = "phase1_content_type"
    CALLOUTS = "phase2_callouts"
    DITA_ISSUES = "phase3_dita_issues"


class FixerTier(Enum):
    """Fixer tiers by LLM usage."""
    PATTERN = 1      # No LLM - regex/template based
    TEMPLATE = 2     # LLM once, then propagate pattern
    LLM = 3          # LLM for each instance


@dataclass
class LearnedFix:
    """
    A fix pattern learned from a successful LLM fix.
    
    Used to propagate fixes to similar issues without re-calling LLM.
    """
    
    rule: str
    """The rule this fix applies to (e.g., 'ShortDescription')."""
    
    pattern_type: str
    """Type of transformation (e.g., 'insert_before', 'replace', 'remove')."""
    
    structural_pattern: str
    """Human-readable description of what the fix does."""
    
    # Example successful fix (for reference)
    example_old: str
    """Original text from the example fix."""
    
    example_new: str
    """Fixed text from the example fix."""
    
    # Regex pattern extracted from the fix (if applicable)
    regex_pattern: Optional[str] = None
    """Regex pattern to find similar issues."""
    
    replacement_template: Optional[str] = None
    """Template for generating the fix."""
    
    # Statistics
    times_used: int = 1
    """Number of times this pattern has been used."""
    
    success_count: int = 1
    """Number of successful applications."""
    
    @property
    def success_rate(self) -> float:
        """Success rate of this pattern."""
        if self.times_used == 0:
            return 0.0
        return self.success_count / self.times_used
    
    def record_usage(self, success: bool):
        """Record a usage of this pattern."""
        self.times_used += 1
        if success:
            self.success_count += 1


@dataclass
class IssueRecord:
    """Record of a single issue found by Vale."""
    
    filepath: str
    line: int
    column: int
    rule: str
    message: str
    severity: str
    
    # Fix status
    status: FixStatus = FixStatus.SKIPPED
    fix_method: Optional[str] = None  # "pattern", "template", "llm"
    error: Optional[str] = None
    
    # For applying the fix
    old_string: Optional[str] = None
    new_string: Optional[str] = None


@dataclass
class RuleProgress:
    """Progress tracking for a single rule."""
    
    rule: str
    tier: FixerTier
    total_issues: int
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    manual_review: int = 0
    
    # Timing
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    @property
    def is_complete(self) -> bool:
        return self.processed >= self.total_issues
    
    @property
    def duration_seconds(self) -> float:
        if not self.started_at or not self.completed_at:
            return 0.0
        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(self.completed_at)
        return (end - start).total_seconds()


@dataclass
class SessionMemoryV2:
    """
    Enhanced session memory with learning and resumability.
    
    Key improvements over v1:
    - Issues grouped by RULE (not by file)
    - Learned fix patterns for propagation
    - Checkpointing for resumability
    - Better progress tracking
    """
    
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    
    # Scope information
    scope_type: str = "project"
    entry_point: Optional[str] = None
    files_in_scope: List[str] = field(default_factory=list)
    
    # Issue tracking (GROUPED BY RULE)
    issues_by_rule: Dict[str, List[dict]] = field(default_factory=dict)
    
    # Rule processing progress
    rule_progress: Dict[str, dict] = field(default_factory=dict)
    processed_rules: Set[str] = field(default_factory=set)
    current_rule: Optional[str] = None
    
    # LEARNING MEMORY - Key innovation!
    learned_fixes: Dict[str, dict] = field(default_factory=dict)
    
    # Results
    fix_results: List[dict] = field(default_factory=list)
    manual_review_items: List[dict] = field(default_factory=list)
    
    # Statistics
    total_issues: int = 0
    total_fixed: int = 0
    total_failed: int = 0
    total_manual_review: int = 0
    llm_calls: int = 0
    llm_calls_saved: int = 0  # Calls saved by pattern propagation
    tokens_used: int = 0
    
    # ------------------------------------------------------------------
    # Scope Management
    # ------------------------------------------------------------------
    
    def record_scope(
        self,
        scope_type: str,
        files: List[Path],
        entry_point: Optional[Path] = None,
    ):
        """Record the resolved scope."""
        self.scope_type = scope_type
        self.files_in_scope = [str(f) for f in files]
        if entry_point:
            self.entry_point = str(entry_point)
    
    # ------------------------------------------------------------------
    # Issue Tracking (Rule-First)
    # ------------------------------------------------------------------
    
    def record_issues(self, issues: List[Any]):
        """
        Record all issues grouped by RULE (not by file).
        
        This is the key architectural change - we process rule-by-rule.
        """
        self.issues_by_rule.clear()
        
        for issue in issues:
            rule = self._extract_rule_name(issue.rule)
            
            if rule not in self.issues_by_rule:
                self.issues_by_rule[rule] = []
            
            self.issues_by_rule[rule].append({
                "filepath": str(issue.filepath),
                "line": issue.line,
                "column": getattr(issue, 'column', 1),
                "rule": issue.rule,
                "message": issue.message,
                "severity": issue.severity,
                "status": FixStatus.SKIPPED.value,
            })
        
        self.total_issues = sum(len(v) for v in self.issues_by_rule.values())
    
    def _extract_rule_name(self, full_rule: str) -> str:
        """Extract rule name from full Vale rule (e.g., 'AsciiDocDITA.ShortDescription' -> 'ShortDescription')."""
        if '.' in full_rule:
            return full_rule.split('.')[-1]
        return full_rule
    
    def get_issues_for_rule(self, rule: str) -> List[dict]:
        """Get all issues for a specific rule."""
        return self.issues_by_rule.get(rule, [])
    
    def get_rules_sorted_by_tier(self, tier_map: Dict[str, int]) -> List[str]:
        """
        Get rules sorted by tier (process pattern fixers first).
        
        Args:
            tier_map: Dict mapping rule names to tier numbers (1, 2, 3)
        
        Returns:
            List of rule names sorted by tier
        """
        rules = list(self.issues_by_rule.keys())
        return sorted(rules, key=lambda r: tier_map.get(r, 3))
    
    # ------------------------------------------------------------------
    # Rule Progress Tracking
    # ------------------------------------------------------------------
    
    def start_rule(self, rule: str, tier: int, total_issues: int):
        """Mark the start of processing a rule."""
        self.current_rule = rule
        self.rule_progress[rule] = {
            "rule": rule,
            "tier": tier,
            "total_issues": total_issues,
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "manual_review": 0,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
        }
    
    def end_rule(self, rule: str):
        """Mark the end of processing a rule."""
        if rule in self.rule_progress:
            self.rule_progress[rule]["completed_at"] = datetime.now().isoformat()
        self.processed_rules.add(rule)
        self.current_rule = None
    
    def is_rule_processed(self, rule: str) -> bool:
        """Check if a rule has been fully processed."""
        return rule in self.processed_rules
    
    # ------------------------------------------------------------------
    # Fix Recording
    # ------------------------------------------------------------------
    
    def record_fix(
        self,
        filepath: Path,
        rule: str,
        line: int,
        status: FixStatus,
        method: str,
        old_string: Optional[str] = None,
        new_string: Optional[str] = None,
        error: Optional[str] = None,
        tokens_used: int = 0,
    ):
        """Record a fix attempt."""
        result = {
            "filepath": str(filepath),
            "rule": rule,
            "line": line,
            "status": status.value,
            "method": method,
            "old_string": old_string,
            "new_string": new_string,
            "error": error,
            "tokens_used": tokens_used,
            "timestamp": datetime.now().isoformat(),
        }
        self.fix_results.append(result)
        
        # Update rule progress
        if rule in self.rule_progress:
            self.rule_progress[rule]["processed"] += 1
            if status == FixStatus.SUCCESS:
                self.rule_progress[rule]["succeeded"] += 1
                self.total_fixed += 1
            elif status == FixStatus.FAILED:
                self.rule_progress[rule]["failed"] += 1
                self.total_failed += 1
            elif status == FixStatus.MANUAL_REVIEW:
                self.rule_progress[rule]["manual_review"] += 1
                self.total_manual_review += 1
        
        # Track LLM usage
        if method == "llm":
            self.llm_calls += 1
            self.tokens_used += tokens_used
        elif method == "template_propagation":
            self.llm_calls_saved += 1
    
    def record_manual_review(
        self,
        filepath: Path,
        rule: str,
        line: int,
        message: str,
        reason: str,
    ):
        """Record an item that needs manual review."""
        self.manual_review_items.append({
            "filepath": str(filepath),
            "rule": rule,
            "line": line,
            "message": message,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })
        self.total_manual_review += 1
    
    # ------------------------------------------------------------------
    # LEARNING MEMORY - Key Innovation!
    # ------------------------------------------------------------------
    
    def learn_fix(
        self,
        rule: str,
        old_string: str,
        new_string: str,
        pattern_type: str = "unknown",
    ):
        """
        Learn a fix pattern from a successful LLM fix.
        
        This is the key innovation - once LLM shows us how to fix
        ShortDescription in file 1, we can apply the same structural
        transformation to files 2-6 WITHOUT calling LLM again.
        """
        # Try to extract a structural pattern
        structural_pattern = self._analyze_transformation(old_string, new_string)
        
        # Try to create regex pattern for finding similar issues
        regex_pattern = self._extract_regex_pattern(old_string, new_string, pattern_type)
        
        learned = LearnedFix(
            rule=rule,
            pattern_type=pattern_type,
            structural_pattern=structural_pattern,
            example_old=old_string,
            example_new=new_string,
            regex_pattern=regex_pattern,
        )
        
        self.learned_fixes[rule] = asdict(learned)
    
    def get_learned_fix(self, rule: str) -> Optional[LearnedFix]:
        """Get a learned fix pattern for a rule."""
        data = self.learned_fixes.get(rule)
        if data:
            return LearnedFix(**data)
        return None
    
    def has_learned_fix(self, rule: str) -> bool:
        """Check if we have a learned fix for a rule."""
        return rule in self.learned_fixes
    
    def _analyze_transformation(self, old: str, new: str) -> str:
        """Analyze what transformation was applied."""
        # Simple heuristics to describe the transformation
        if len(new) > len(old):
            diff = new.replace(old, '')
            if diff.strip():
                return f"Insert: '{diff.strip()[:50]}...'"
            return "Content added"
        elif len(new) < len(old):
            return "Content removed"
        else:
            return "Content modified"
    
    def _extract_regex_pattern(
        self,
        old: str,
        new: str,
        pattern_type: str,
    ) -> Optional[str]:
        """Try to extract a regex pattern from the fix."""
        # Rule-specific pattern extraction
        if pattern_type == "insert_abstract":
            # ShortDescription pattern: insert [role="_abstract"] before paragraph
            return r'^(= .+?\n\n)(.+)$'
        
        # Generic: escape the old string as a literal match
        return re.escape(old)
    
    # ------------------------------------------------------------------
    # Checkpointing (Resumability)
    # ------------------------------------------------------------------
    
    def save_checkpoint(self, project_dir: Path):
        """
        Save current state for resumability.
        
        If the agent is interrupted, it can resume from this checkpoint.
        """
        checkpoint_dir = project_dir / ".dita-agent" / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint_file = checkpoint_dir / f"checkpoint_{self.session_id}.json"
        
        state = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "scope_type": self.scope_type,
            "entry_point": self.entry_point,
            "files_in_scope": self.files_in_scope,
            "issues_by_rule": self.issues_by_rule,
            "rule_progress": self.rule_progress,
            "processed_rules": list(self.processed_rules),
            "current_rule": self.current_rule,
            "learned_fixes": self.learned_fixes,
            "total_issues": self.total_issues,
            "total_fixed": self.total_fixed,
            "total_failed": self.total_failed,
            "llm_calls": self.llm_calls,
            "llm_calls_saved": self.llm_calls_saved,
            "tokens_used": self.tokens_used,
            "checkpoint_time": datetime.now().isoformat(),
        }
        
        checkpoint_file.write_text(json.dumps(state, indent=2))
    
    @classmethod
    def load_checkpoint(cls, project_dir: Path, session_id: str) -> Optional["SessionMemoryV2"]:
        """Load state from a checkpoint."""
        checkpoint_file = project_dir / ".dita-agent" / "checkpoints" / f"checkpoint_{session_id}.json"
        
        if not checkpoint_file.exists():
            return None
        
        try:
            state = json.loads(checkpoint_file.read_text())
            
            memory = cls()
            memory.session_id = state["session_id"]
            memory.start_time = state["start_time"]
            memory.scope_type = state["scope_type"]
            memory.entry_point = state["entry_point"]
            memory.files_in_scope = state["files_in_scope"]
            memory.issues_by_rule = state["issues_by_rule"]
            memory.rule_progress = state["rule_progress"]
            memory.processed_rules = set(state["processed_rules"])
            memory.current_rule = state["current_rule"]
            memory.learned_fixes = state["learned_fixes"]
            memory.total_issues = state["total_issues"]
            memory.total_fixed = state["total_fixed"]
            memory.total_failed = state["total_failed"]
            memory.llm_calls = state["llm_calls"]
            memory.llm_calls_saved = state["llm_calls_saved"]
            memory.tokens_used = state["tokens_used"]
            
            return memory
        
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load checkpoint: {e}")
            return None
    
    def can_resume(self, project_dir: Path) -> bool:
        """Check if there's a resumable checkpoint."""
        checkpoint_file = project_dir / ".dita-agent" / "checkpoints" / f"checkpoint_{self.session_id}.json"
        return checkpoint_file.exists()
    
    # ------------------------------------------------------------------
    # Finalization and Reporting
    # ------------------------------------------------------------------
    
    def finalize(self):
        """Mark the session as complete."""
        self.end_time = datetime.now().isoformat()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the session."""
        return {
            "session_id": self.session_id,
            "scope_type": self.scope_type,
            "files_in_scope": len(self.files_in_scope),
            "total_issues": self.total_issues,
            "total_fixed": self.total_fixed,
            "total_failed": self.total_failed,
            "total_manual_review": self.total_manual_review,
            "llm_calls": self.llm_calls,
            "llm_calls_saved": self.llm_calls_saved,
            "tokens_used": self.tokens_used,
            "rules_processed": len(self.processed_rules),
            "rules_total": len(self.issues_by_rule),
            "learned_patterns": len(self.learned_fixes),
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
    
    def save_session_log(self, project_dir: Path) -> Path:
        """Save the complete session log."""
        logs_dir = project_dir / ".dita-agent" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = logs_dir / f"session_{self.session_id}.json"
        
        data = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "summary": self.get_summary(),
            "rule_progress": self.rule_progress,
            "learned_fixes": self.learned_fixes,
            "fix_results": self.fix_results,
            "manual_review_items": self.manual_review_items,
        }
        
        log_file.write_text(json.dumps(data, indent=2))
        return log_file


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================
# Re-export legacy SessionMemory for Phase 1 and Phase 2 compatibility
# These phases will be updated to use SessionMemoryV2 in a future update

from dita_agent.core.memory_legacy import (
    SessionMemory,
    FixAttempt,
)

# Export both old and new for transition period
__all__ = [
    # New classes (v2)
    "SessionMemoryV2",
    "LearnedFix",
    "IssueRecord",
    "RuleProgress",
    "FixerTier",
    # Common (same in both)
    "FixStatus",
    "Phase",
    # Legacy (for backward compatibility)
    "SessionMemory",
    "FixAttempt",
]
