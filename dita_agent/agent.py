"""
DITA Migration Agent - Main Orchestrator

This module orchestrates the three-phase DITA migration process:
1. Phase 1: Content Type Assignment
2. Phase 2: Callouts Conversion
3. Phase 3: All Other DITA Issues

Each phase must complete with zero relevant errors before the next begins.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from dita_agent.core.scope import ScopeResolver
from dita_agent.core.memory import SessionMemory, SessionMemoryV2, Phase
from dita_agent.core.verification import Verifier
from dita_agent.core.manual_review import ManualReviewGenerator
from dita_agent.llm.client import LLMClient
from dita_agent.phases.content_type import ContentTypePhase
from dita_agent.phases.callouts import CalloutsPhase
from dita_agent.phases.dita_issues import DITAIssuesPhase
from dita_agent.utils.git_ops import ensure_gitignore_updated

console = Console()


@dataclass
class AgentResult:
    """Result of running the agent."""
    
    success: bool
    """Whether all issues were resolved."""
    
    files_processed: int = 0
    """Total files processed."""
    
    issues_fixed: int = 0
    """Total issues fixed."""
    
    issues_remaining: int = 0
    """Issues that couldn't be fixed."""
    
    total_tokens: int = 0
    """Total LLM tokens used."""
    
    duration_seconds: float = 0.0
    """Total time taken."""
    
    manual_review_path: Optional[Path] = None
    """Path to manual review document if generated."""
    
    phase_results: Dict[str, dict] = field(default_factory=dict)
    """Results from each phase."""


@dataclass
class DITAAgent:
    """
    Main orchestrator for DITA migration.
    
    Follows the sequential phase model:
    - Phase 1 must complete with zero ContentType issues
    - Phase 2 must complete with zero Callout issues
    - Phase 3 must complete with zero Vale errors (or document unfixable)
    """
    
    config: dict
    project_dir: Path
    assembly: Optional[Path] = None
    topics: Optional[List[Path]] = None
    limit: Optional[int] = None
    dry_run: bool = False
    
    # Internal state
    start_time: datetime = field(default_factory=datetime.now)
    files_in_scope: List[Path] = field(default_factory=list)
    
    def run(self) -> AgentResult:
        """
        Run the complete DITA migration workflow.
        
        Returns:
            AgentResult with statistics and status.
        """
        start_time = time.time()
        
        # Initialize components
        memory = SessionMemory()
        verifier = Verifier()
        manual_review = ManualReviewGenerator(self.project_dir, memory.session_id)
        
        # Initialize LLM client
        api_key = self.config.get("api_key", "")
        model = self.config.get("model", "gemini-3-flash-preview")
        base_url = self.config.get("base_url")
        cert_path = self.config.get("cert_path")
        
        if not api_key and not self.dry_run:
            console.print("[red]Error: API key not configured. Run 'dita-agent setup' first.[/red]")
            return AgentResult(success=False)
        
        llm = LLMClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            cert_path=cert_path,
        )
        
        # Display header
        self._print_header(memory.session_id)
        
        # Ensure .dita-agent is gitignored
        ensure_gitignore_updated(self.project_dir, ".dita-agent/")
        
        # Step 1: Resolve scope
        console.print("\n[bold cyan]Step 1/4: Resolving Scope[/bold cyan]")
        files = self._resolve_scope()
        
        if not files:
            console.print("[yellow]No files to process.[/yellow]")
            return AgentResult(success=True, duration_seconds=time.time() - start_time)
        
        # Determine scope type
        if self.topics:
            scope_type = "topics"
            entry_point = None
        elif self.assembly:
            scope_type = "assembly"
            entry_point = self.assembly
        else:
            scope_type = "project"
            entry_point = self.project_dir
        
        memory.record_scope(scope_type, files, entry_point)
        self.files_in_scope = files
        
        console.print(f"  Found [green]{len(files)}[/green] files to process")
        
        if self.dry_run:
            console.print("  [yellow]DRY RUN MODE - no files will be modified[/yellow]")
        
        # Initialize result tracking
        total_issues_fixed = 0
        total_issues_remaining = 0
        total_tokens = 0
        phase_results = {}
        
        # Step 2: Phase 1 - Content Type Assignment
        console.print("\n[bold cyan]Step 2/4: Phase 1 - Content Type Assignment[/bold cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Adding :_mod-docs-content-type: attributes...", total=len(files))
            
            phase1 = ContentTypePhase(
                llm_client=llm,
                memory=memory,
                project_dir=self.project_dir,
                dry_run=self.dry_run,
            )
            
            phase1_result = phase1.run(files)
            progress.update(task, completed=len(files))
        
        self._print_phase_summary("Phase 1", phase1_result)
        phase_results["content_type"] = {
            "fixed": phase1_result.files_fixed,
            "skipped": phase1_result.files_skipped,
            "failed": phase1_result.files_failed,
            "tokens": phase1_result.total_tokens,
        }
        total_issues_fixed += phase1_result.files_fixed
        total_tokens += phase1_result.total_tokens
        
        # Add failed items to manual review
        for filepath, error in phase1_result.failed_files:
            manual_review.add_item(
                filepath=filepath,
                line=1,
                rule="ContentType",
                message="Missing :_mod-docs-content-type: attribute",
                reason=error,
                severity="error",
            )
        
        # Step 3: Phase 2 - Callouts Conversion
        console.print("\n[bold cyan]Step 3/4: Phase 2 - Callouts Conversion[/bold cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Converting callout markers...", total=len(files))
            
            phase2 = CalloutsPhase(
                llm_client=llm,
                memory=memory,
                project_dir=self.project_dir,
                dry_run=self.dry_run,
            )
            
            phase2_result = phase2.run(files)
            progress.update(task, completed=len(files))
        
        self._print_phase_summary("Phase 2", phase2_result)
        phase_results["callouts"] = {
            "fixed_by_tool": phase2_result.files_fixed_by_tool,
            "fixed_by_llm": phase2_result.files_fixed_by_llm,
            "skipped": phase2_result.files_skipped,
            "failed": phase2_result.files_failed,
            "tokens": phase2_result.total_tokens,
        }
        total_issues_fixed += phase2_result.files_fixed_by_tool + phase2_result.files_fixed_by_llm
        total_tokens += phase2_result.total_tokens
        
        # Add failed items to manual review
        for filepath, error in phase2_result.failed_files:
            manual_review.add_item(
                filepath=filepath,
                line=1,
                rule="CalloutList",
                message="Callout markers need conversion",
                reason=error,
                severity="error",
            )
        
        # Step 4: Phase 3 - All Other DITA Issues (Rule-First Processing)
        console.print("\n[bold cyan]Step 4/4: Phase 3 - All Other DITA Issues[/bold cyan]")
        
        # Phase 3 uses enhanced memory with learning capabilities
        memory_v2 = SessionMemoryV2()
        memory_v2.record_scope(scope_type, files, entry_point)
        
        # Phase 3 handles its own progress output for better visibility
        phase3 = DITAIssuesPhase(
            llm_client=llm,
            memory=memory_v2,
            project_dir=self.project_dir,
            dry_run=self.dry_run,
            vale_path=self.config.get("vale_path"),
        )
        
        phase3_result = phase3.run(files)
        
        self._print_phase_summary("Phase 3", phase3_result)
        phase_results["dita_issues"] = {
            "found": phase3_result.issues_found,
            "fixed": phase3_result.issues_fixed,
            "failed": phase3_result.issues_failed,
            "tokens": phase3_result.total_tokens,
            "by_rule": phase3_result.fixes_by_rule,
            "by_tier": phase3_result.fixes_by_tier,
            "llm_calls": phase3_result.llm_calls,
            "llm_calls_saved": phase3_result.llm_calls_saved,
        }
        total_issues_fixed += phase3_result.issues_fixed
        total_tokens += phase3_result.total_tokens
        
        # Add remaining issues to manual review using actual failure reasons from memory_v2
        for item in memory_v2.manual_review_items:
            manual_review.add_item(
                filepath=Path(item["filepath"]),
                line=item["line"],
                rule=item["rule"],
                message=item["message"],
                reason=item["reason"],
                severity="warning",  # Default to warning
            )
        
        # Calculate totals
        total_issues_remaining = (
            phase1_result.files_failed +
            phase2_result.files_failed +
            phase3_result.issues_failed
        )
        
        # Generate manual review document if there are items
        manual_review_path = None
        if manual_review.has_items():
            manual_review_path = manual_review.generate()
            console.print(f"\n[yellow]⚠ Manual review required: {manual_review_path}[/yellow]")
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Print final summary
        success = total_issues_remaining == 0
        self._print_final_summary(
            success=success,
            files_processed=len(files),
            issues_fixed=total_issues_fixed,
            issues_remaining=total_issues_remaining,
            total_tokens=total_tokens,
            duration=duration,
            manual_review_path=manual_review_path,
        )
        
        return AgentResult(
            success=success,
            files_processed=len(files),
            issues_fixed=total_issues_fixed,
            issues_remaining=total_issues_remaining,
            total_tokens=total_tokens,
            duration_seconds=duration,
            manual_review_path=manual_review_path,
            phase_results=phase_results,
        )
    
    def _resolve_scope(self) -> List[Path]:
        """Resolve which files to process based on user input."""
        resolver = ScopeResolver(self.project_dir)
        
        # Use the unified resolve method
        result = resolver.resolve(
            assembly=self.assembly,
            topics=self.topics,
            limit=self.limit,
        )
        
        if result.errors:
            for error in result.errors:
                console.print(f"[yellow]Warning: {error}[/yellow]")
        
        return result.files
    
    def _print_header(self, session_id: str):
        """Print agent header."""
        console.print(Panel.fit(
            f"[bold]DITA Migration Agent v2.0[/bold]\n\n"
            f"Session: [cyan]{session_id}[/cyan]\n"
            f"Project: [cyan]{self.project_dir}[/cyan]",
            border_style="blue",
        ))
    
    def _print_phase_summary(self, phase_name: str, result):
        """Print summary for a phase."""
        if hasattr(result, 'files_fixed'):
            # Phase 1
            console.print(f"  ✓ Fixed: [green]{result.files_fixed}[/green]")
            console.print(f"  ○ Skipped: [dim]{result.files_skipped}[/dim]")
            if result.files_failed > 0:
                console.print(f"  ✗ Failed: [red]{result.files_failed}[/red]")
        elif hasattr(result, 'files_fixed_by_tool'):
            # Phase 2
            console.print(f"  ✓ Fixed (tool): [green]{result.files_fixed_by_tool}[/green]")
            console.print(f"  ✓ Fixed (LLM): [green]{result.files_fixed_by_llm}[/green]")
            console.print(f"  ○ Skipped: [dim]{result.files_skipped}[/dim]")
            if result.files_failed > 0:
                console.print(f"  ✗ Failed: [red]{result.files_failed}[/red]")
        elif hasattr(result, 'issues_found'):
            # Phase 3
            console.print(f"\n  [bold]Summary:[/bold]")
            console.print(f"  Found: [yellow]{result.issues_found}[/yellow] issues")
            console.print(f"  ✓ Fixed: [green]{result.issues_fixed}[/green]")
            if hasattr(result, 'issues_skipped') and result.issues_skipped > 0:
                console.print(f"  ○ Skipped (suggestions): [dim]{result.issues_skipped}[/dim]")
            if result.issues_failed > 0:
                console.print(f"  ✗ Failed: [red]{result.issues_failed}[/red]")
        
        if hasattr(result, 'total_tokens') and result.total_tokens > 0:
            console.print(f"  Tokens: [dim]{result.total_tokens:,}[/dim]")
    
    def _print_final_summary(
        self,
        success: bool,
        files_processed: int,
        issues_fixed: int,
        issues_remaining: int,
        total_tokens: int,
        duration: float,
        manual_review_path: Optional[Path],
    ):
        """Print final summary panel."""
        status = "[bold green]✓ SUCCESS[/bold green]" if success else "[bold yellow]⚠ PARTIAL[/bold yellow]"
        
        summary = Table.grid(padding=(0, 2))
        summary.add_column(justify="right")
        summary.add_column()
        
        summary.add_row("Status:", status)
        summary.add_row("Files processed:", f"[cyan]{files_processed}[/cyan]")
        summary.add_row("Issues fixed:", f"[green]{issues_fixed}[/green]")
        
        if issues_remaining > 0:
            summary.add_row("Issues remaining:", f"[red]{issues_remaining}[/red]")
        
        summary.add_row("Total tokens:", f"[dim]{total_tokens:,}[/dim]")
        summary.add_row("Duration:", f"[dim]{duration:.1f}s[/dim]")
        
        if manual_review_path:
            summary.add_row("Manual review:", f"[yellow]{manual_review_path.name}[/yellow]")
        
        console.print("\n")
        console.print(Panel(
            summary,
            title="[bold]Migration Complete[/bold]",
            border_style="green" if success else "yellow",
        ))
        
        if success:
            console.print("\n[green]All DITA compatibility issues have been resolved![/green]")
        else:
            console.print(f"\n[yellow]Some issues require manual review. See {manual_review_path}[/yellow]")
