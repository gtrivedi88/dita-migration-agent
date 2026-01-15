"""
Phase 3 v2: DITA Issues - Rule-First Processing

This is the improved Phase 3 implementation with:
1. Rule-First Processing: Process by rule across all files, not file-by-file
2. Three-Tier Fixers: Pattern → Template → LLM cascade
3. Learning Memory: Learn patterns from LLM and propagate to similar issues
4. Checkpointing: Resumable processing if interrupted

Processing Flow:
1. Scan ALL files with Vale
2. Group issues by RULE (not by file)
3. Sort rules by tier (process patterns first)
4. For each rule, fix ALL instances across all files
5. Verify each fix immediately
6. Learn from LLM fixes and propagate patterns
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from dita_agent.core.memory import SessionMemoryV2, FixStatus
from dita_agent.fixers.registry import FixerRegistry, FixResult
from dita_agent.llm.client import LLMClient
from dita_agent.tools.vale import ValeRunner, ValeIssue
from dita_agent.utils.file_ops import (
    read_file_safe,
    write_file_safe,
    backup_file,
    restore_file,
)

console = Console()


@dataclass
class DITAIssuesPhaseResult:
    """Result of running the DITA issues phase."""
    
    success: bool
    """Whether the phase completed successfully (zero errors)."""
    
    files_processed: int = 0
    """Total files that had issues."""
    
    issues_found: int = 0
    """Total issues found by Vale."""
    
    issues_fixed: int = 0
    """Issues successfully fixed."""
    
    issues_failed: int = 0
    """Issues that could not be fixed."""
    
    issues_skipped: int = 0
    """Issues skipped (suggestions)."""
    
    fixes_by_rule: Dict[str, int] = field(default_factory=dict)
    """Count of fixes per rule."""
    
    fixes_by_tier: Dict[str, int] = field(default_factory=dict)
    """Count of fixes per tier."""
    
    total_tokens: int = 0
    """Total tokens used for LLM calls."""
    
    llm_calls: int = 0
    """Number of LLM API calls made."""
    
    llm_calls_saved: int = 0
    """LLM calls saved by pattern propagation."""
    
    duration_seconds: float = 0.0
    """Time taken for the phase."""
    
    rules_processed: int = 0
    """Number of unique rules processed."""


class DITAIssuesPhase:
    """
    Phase 3 v2: Rule-First DITA Issue Resolution.
    
    Key architectural changes from v1:
    1. Groups issues by RULE instead of by file
    2. Processes rules in tier order (Pattern → Template → LLM)
    3. Learns fix patterns and propagates them
    4. Saves checkpoints for resumability
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        memory: SessionMemoryV2,
        project_dir: Path,
        dry_run: bool = False,
    ):
        """
        Initialize the phase.
        
        Args:
            llm_client: LLM client for fix generation.
            memory: Enhanced session memory with learning.
            project_dir: Project root directory.
            dry_run: If True, don't modify files.
        """
        self.llm = llm_client
        self.memory = memory
        self.project_dir = project_dir
        self.dry_run = dry_run
        
        # Initialize Vale runner
        self.vale = ValeRunner()
        
        # Initialize fixer registry with tier system
        self.registry = FixerRegistry(llm_client, memory)
    
    def run(self, files: List[Path]) -> DITAIssuesPhaseResult:
        """
        Run the DITA issues phase with rule-first processing.
        
        Args:
            files: List of files to process.
            
        Returns:
            DITAIssuesPhaseResult with statistics.
        """
        start_time = time.time()
        result = DITAIssuesPhaseResult(success=True)
        
        # ====================================================================
        # STEP 1: Scan all files with Vale
        # ====================================================================
        console.print("  [dim]Scanning files with Vale...[/dim]")
        vale_result = self.vale.run(files, self.project_dir)
        
        if not vale_result.success:
            console.print(f"  [red]Vale error: {vale_result.error_message}[/red]")
            result.success = False
            result.duration_seconds = time.time() - start_time
            return result
        
        # Filter to actionable issues only (errors + warnings, not suggestions)
        all_issues = vale_result.issues
        actionable_issues = [i for i in all_issues if i.severity in ("error", "warning")]
        suggestions = [i for i in all_issues if i.severity == "suggestion"]
        
        result.issues_found = len(all_issues)
        result.issues_skipped = len(suggestions)
        
        console.print(f"  [dim]Found {len(all_issues)} total issues:[/dim]")
        console.print(f"    [yellow]Errors/Warnings: {len(actionable_issues)}[/yellow]")
        console.print(f"    [dim]Suggestions (skipped): {len(suggestions)}[/dim]")
        
        if not actionable_issues:
            console.print("  [green]No errors or warnings to fix![/green]")
            result.duration_seconds = time.time() - start_time
            return result
        
        # ====================================================================
        # STEP 2: Group issues by RULE (the key architectural change!)
        # ====================================================================
        self.memory.record_issues(actionable_issues)
        issues_by_rule = self._group_by_rule(actionable_issues)
        
        console.print(f"\n  [dim]Issues grouped into {len(issues_by_rule)} rules[/dim]")
        
        # Count unique files
        unique_files = set()
        for issues in issues_by_rule.values():
            for issue in issues:
                unique_files.add(issue.filepath)
        result.files_processed = len(unique_files)
        
        # ====================================================================
        # STEP 3: Sort rules by tier (process patterns first!)
        # ====================================================================
        tier_map = self.registry.get_tier_map()
        sorted_rules = self._sort_rules_by_tier(list(issues_by_rule.keys()), tier_map)
        
        # ====================================================================
        # STEP 4: Process each rule across ALL its files
        # ====================================================================
        console.print("\n  [bold]Processing rules (by tier):[/bold]")
        
        for rule in sorted_rules:
            # Skip if already processed (resumability)
            if self.memory.is_rule_processed(rule):
                console.print(f"    [dim]✓ {rule} (already processed)[/dim]")
                continue
            
            issues = issues_by_rule[rule]
            tier = self.registry.get_tier(rule)
            tier_label = self.registry.get_tier_label(rule)
            
            # Process this rule across all files
            rule_result = self._process_rule(rule, issues, tier, tier_label)
            
            # Update statistics
            result.issues_fixed += rule_result["fixed"]
            result.issues_failed += rule_result["failed"]
            result.total_tokens += rule_result["tokens"]
            result.llm_calls += rule_result["llm_calls"]
            result.llm_calls_saved += rule_result["llm_saved"]
            result.rules_processed += 1
            
            result.fixes_by_rule[rule] = rule_result["fixed"]
            result.fixes_by_tier[tier_label] = result.fixes_by_tier.get(tier_label, 0) + rule_result["fixed"]
            
            # Mark rule as processed and save checkpoint
            self.memory.end_rule(rule)
            if not self.dry_run:
                self.memory.save_checkpoint(self.project_dir)
        
        # ====================================================================
        # STEP 5: Cleanup and finalize
        # ====================================================================
        self.vale.cleanup()
        
        result.duration_seconds = time.time() - start_time
        result.success = result.issues_failed == 0
        
        # Print summary
        self._print_summary(result)
        
        return result
    
    def _group_by_rule(self, issues: List[ValeIssue]) -> Dict[str, List[ValeIssue]]:
        """
        Group issues by rule name.
        
        This is the key architectural change - we process RULE by RULE,
        not file by file.
        """
        grouped: Dict[str, List[ValeIssue]] = {}
        
        for issue in issues:
            rule = self._extract_rule_name(issue.rule)
            
            if rule not in grouped:
                grouped[rule] = []
            grouped[rule].append(issue)
        
        return grouped
    
    def _extract_rule_name(self, full_rule: str) -> str:
        """Extract rule name (e.g., 'AsciiDocDITA.ShortDescription' -> 'ShortDescription')."""
        if '.' in full_rule:
            return full_rule.split('.')[-1]
        return full_rule
    
    def _sort_rules_by_tier(self, rules: List[str], tier_map: Dict[str, int]) -> List[str]:
        """
        Sort rules by tier - process patterns first, then templates, then LLM.
        
        This maximizes efficiency:
        1. Pattern fixes are instant (no LLM)
        2. Template fixes use LLM once then propagate
        3. LLM fixes are most expensive, do last
        """
        return sorted(rules, key=lambda r: tier_map.get(r, 3))
    
    def _process_rule(
        self,
        rule: str,
        issues: List[ValeIssue],
        tier: int,
        tier_label: str,
    ) -> Dict:
        """
        Process ALL instances of ONE rule across all files.
        
        This is where the magic happens:
        - For PATTERN tier: Apply regex fix to each file (instant)
        - For TEMPLATE tier: LLM generates fix for first file, then propagate
        - For LLM tier: Use LLM for each file
        """
        stats = {
            "fixed": 0,
            "failed": 0,
            "tokens": 0,
            "llm_calls": 0,
            "llm_saved": 0,
        }
        
        # Start tracking this rule
        self.memory.start_rule(rule, tier, len(issues))
        
        # Get the fixer for this rule
        fixer = self.registry.get_fixer(rule)
        
        # Sort issues by file path for consistent ordering
        issues = sorted(issues, key=lambda x: (str(x.filepath), -x.line))
        
        console.print(f"\n    [{self._tier_color(tier)}][{tier_label}][/{self._tier_color(tier)}] {rule} ({len(issues)} files)")
        
        # Process each issue
        for issue in issues:
            filepath = Path(issue.filepath)
            backup_path = None
            
            # Backup file before modification
            if not self.dry_run:
                backup_path = backup_file(filepath, self.project_dir, self.memory.session_id)
            
            # Read file content
            content, error = read_file_safe(filepath)
            if error:
                console.print(f"      [red]✗ {filepath.name} - Cannot read: {error}[/red]")
                stats["failed"] += 1
                self.memory.record_fix(
                    filepath=filepath,
                    rule=rule,
                    line=issue.line,
                    status=FixStatus.FAILED,
                    method="error",
                    error=error,
                )
                continue
            
            # Apply the fixer
            fix_result = fixer.fix(filepath, content, issue.line, issue.message)
            
            # Check if pattern fixer needs escalation for table contexts
            if fix_result.error == "TABLE_CONTEXT_NEEDS_LLM":
                # Use specialized TableLineBreakFixer which processes full rows
                table_fixer = self.registry.table_line_break_fixer
                fix_result = table_fixer.fix(filepath, content, issue.line, issue.message)
                
                # If table fixer already processed this row (multi ` +` in same row), skip
                if fix_result.error == "Row already fixed in this session":
                    console.print(f"      [dim]~ {filepath.name}:{issue.line} - row already fixed[/dim]")
                    continue
                
                # If intentional formatting detected (CLI args, code examples), skip auto-fix
                if fix_result.error == "INTENTIONAL_FORMATTING":
                    console.print(f"      [yellow]⚠ {filepath.name}:{issue.line} - intentional formatting (manual review)[/yellow]")
                    self.memory.record_manual_review(
                        filepath=filepath,
                        rule=rule,
                        line=issue.line,
                        message=issue.message,
                        reason="Intentional formatting (CLI args or code examples) - manual review required",
                    )
                    stats["failed"] += 1
                    continue
                
                console.print(f"      [cyan]↗ {filepath.name}:{issue.line} - using table row fixer[/cyan]")
            
            if fix_result.success and fix_result.old_string:
                # Apply the fix
                if not self.dry_run:
                    new_content = content.replace(fix_result.old_string, fix_result.new_string, 1)
                    write_error = write_file_safe(filepath, new_content)
                    
                    if write_error:
                        console.print(f"      [red]✗ {filepath.name} - Write error: {write_error}[/red]")
                        stats["failed"] += 1
                        continue
                    
                    # Verify the fix (pass old/new strings for content-based verification)
                    if self._verify_fix(filepath, rule, issue.line, fix_result.old_string, fix_result.new_string):
                        console.print(f"      [green]✓ {filepath.name}[/green] [{fix_result.method}]")
                        stats["fixed"] += 1
                        self.memory.record_fix(
                            filepath=filepath,
                            rule=rule,
                            line=issue.line,
                            status=FixStatus.SUCCESS,
                            method=fix_result.method,
                            old_string=fix_result.old_string,
                            new_string=fix_result.new_string,
                            tokens_used=fix_result.tokens_used,
                        )
                        
                        # Track LLM usage
                        if fix_result.method == "llm":
                            stats["llm_calls"] += 1
                            stats["tokens"] += fix_result.tokens_used
                        elif fix_result.method == "template_propagation":
                            stats["llm_saved"] += 1
                    else:
                        # Verification failed - rollback
                        if backup_path:
                            restore_file(filepath, backup_path)
                        console.print(f"      [yellow]→ {filepath.name} - Verification failed[/yellow]")
                        stats["failed"] += 1
                        self.memory.record_fix(
                            filepath=filepath,
                            rule=rule,
                            line=issue.line,
                            status=FixStatus.FAILED,
                            method=fix_result.method,
                            error="Verification failed",
                        )
                else:
                    # Dry run - just report
                    console.print(f"      [dim]○ {filepath.name} (dry run)[/dim]")
                    stats["fixed"] += 1
            
            elif fix_result.success and fix_result.method == "skipped":
                # Successfully determined no action needed (e.g., SNIPPET files)
                # This is NOT a failure - the agent correctly identified no fix is required
                console.print(f"      [dim]○ {filepath.name} - {fix_result.error or 'No action needed'}[/dim]")
                # Don't add to manual review, count as handled (not failed)
                stats["fixed"] += 1
            
            elif fix_result.success and not fix_result.old_string:
                # Success but nothing to change (already correct)
                console.print(f"      [dim]○ {filepath.name} - Already correct[/dim]")
                stats["fixed"] += 1
            
            else:
                # Fix failed or requires manual review
                error_msg = fix_result.error or "Unknown error"
                
                # Check if this is a manual review item (not a failure)
                if error_msg.startswith("MANUAL_REVIEW:"):
                    # Extract the guidance from the error message
                    guidance = error_msg.replace("MANUAL_REVIEW:", "").strip()
                    console.print(f"      [magenta]📋 {filepath.name}:{issue.line} - Manual review required[/magenta]")
                    console.print(f"         [dim]{guidance[:80]}{'...' if len(guidance) > 80 else ''}[/dim]")
                    
                    self.memory.record_manual_review(
                        filepath=filepath,
                        rule=rule,
                        line=issue.line,
                        message=issue.message,
                        reason=guidance,
                    )
                    # Don't count as failed - it's flagged for review
                    stats["failed"] += 1  # Still count for summary purposes
                else:
                    # Actual failure
                    console.print(f"      [yellow]→ {filepath.name} - {error_msg}[/yellow]")
                    stats["failed"] += 1
                    self.memory.record_fix(
                        filepath=filepath,
                        rule=rule,
                        line=issue.line,
                        status=FixStatus.MANUAL_REVIEW,
                        method=fix_result.method,
                        error=error_msg,
                    )
                    self.memory.record_manual_review(
                        filepath=filepath,
                        rule=rule,
                        line=issue.line,
                        message=issue.message,
                        reason=error_msg,
                    )
        
        return stats
    
    def _verify_fix(
        self, 
        filepath: Path, 
        rule: str, 
        line: int,
        old_string: str = None,
        new_string: str = None,
    ) -> bool:
        """
        Verify that the fix resolved the issue.
        
        Two verification strategies:
        1. Content-based: Check if old_string was replaced (faster, more reliable for tables)
        2. Vale-based: Re-run Vale to check if issue is gone (more thorough)
        
        For LineBreak in tables, we use content-based verification because
        adjacent rows have issues within ±2 lines which confuses Vale-based checks.
        """
        # Content-based verification: check if old was replaced with new
        if old_string and new_string:
            content, _ = read_file_safe(filepath)
            if content:
                # The fix was successful if:
                # 1. old_string no longer exists, AND
                # 2. new_string now exists
                if old_string not in content and new_string in content:
                    return True
                # For LineBreak specifically, also check if ` +\n` was removed
                if rule == "LineBreak" and ' +\n' not in new_string:
                    if new_string in content:
                        return True
        
        # Fall back to Vale-based verification for non-table fixes
        verify_result = self.vale.run_single(filepath, self.project_dir)
        
        # Check if the specific issue is still present
        for issue in verify_result.issues:
            issue_rule = self._extract_rule_name(issue.rule)
            # Check if same rule and same line (or close to it)
            if issue_rule == rule and abs(issue.line - line) <= 2:
                return False
        
        return True
    
    def _tier_color(self, tier: int) -> str:
        """Get color for tier display."""
        colors = {1: "green", 2: "cyan", 3: "yellow"}
        return colors.get(tier, "white")
    
    def _print_summary(self, result: DITAIssuesPhaseResult):
        """Print summary of the phase."""
        console.print("\n  [bold]Summary:[/bold]")
        console.print(f"    Rules processed: {result.rules_processed}")
        console.print(f"    Files with issues: {result.files_processed}")
        console.print(f"    Issues found: {result.issues_found}")
        console.print(f"    [green]Fixed: {result.issues_fixed}[/green]")
        if result.issues_failed > 0:
            console.print(f"    [red]Failed: {result.issues_failed}[/red]")
        if result.issues_skipped > 0:
            console.print(f"    [dim]Skipped (suggestions): {result.issues_skipped}[/dim]")
        
        # Tier breakdown
        console.print("\n    [bold]Fixes by tier:[/bold]")
        for tier_label, count in result.fixes_by_tier.items():
            color = {"PATTERN": "green", "TEMPLATE": "cyan", "LLM": "yellow"}.get(tier_label, "white")
            console.print(f"      [{color}]{tier_label}: {count}[/{color}]")
        
        # LLM efficiency
        if result.llm_calls > 0 or result.llm_calls_saved > 0:
            total_potential = result.llm_calls + result.llm_calls_saved
            savings_pct = (result.llm_calls_saved / total_potential * 100) if total_potential > 0 else 0
            console.print(f"\n    [bold]LLM efficiency:[/bold]")
            console.print(f"      Calls made: {result.llm_calls}")
            console.print(f"      Calls saved (pattern propagation): {result.llm_calls_saved}")
            console.print(f"      Savings: {savings_pct:.0f}%")
            console.print(f"      Tokens used: {result.total_tokens:,}")
        
        console.print(f"\n    Duration: {result.duration_seconds:.1f}s")
