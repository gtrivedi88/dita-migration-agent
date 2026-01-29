"""
Vale linter integration.

Runs Vale with asciidoctor-dita-vale styles to detect DITA compatibility issues.
"""

import json
import subprocess
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from dita_agent.knowledge import get_rule_severity, RuleSeverity


@dataclass
class ValeIssue:
    """A single issue reported by Vale."""
    
    filepath: Path
    """Path to the file with the issue."""
    
    line: int
    """Line number (1-based)."""
    
    column: int
    """Column number."""
    
    rule: str
    """Name of the Vale rule."""
    
    message: str
    """Error/warning message."""
    
    severity: str
    """Severity: error, warning, suggestion."""
    
    context: str = ""
    """The line content where issue was found."""
    
    def __str__(self) -> str:
        return f"{self.filepath}:{self.line}:{self.column} [{self.severity}] {self.rule}: {self.message}"


@dataclass
class ValeResult:
    """Result of running Vale."""
    
    success: bool
    """Whether Vale ran successfully."""
    
    issues: List[ValeIssue] = field(default_factory=list)
    """List of issues found."""
    
    errors: int = 0
    """Count of errors."""
    
    warnings: int = 0
    """Count of warnings."""
    
    suggestions: int = 0
    """Count of suggestions."""
    
    error_message: Optional[str] = None
    """Error message if Vale failed to run."""
    
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return len(self.issues) > 0
    
    def get_issues_for_file(self, filepath: Path) -> List[ValeIssue]:
        """Get issues for a specific file."""
        filepath_resolved = filepath.resolve()
        return [i for i in self.issues if i.filepath.resolve() == filepath_resolved]
    
    def get_issues_by_rule(self, rule: str) -> List[ValeIssue]:
        """Get issues for a specific rule."""
        return [i for i in self.issues if i.rule == rule]


class ValeRunner:
    """
    Runner for Vale linter with DITA styles.
    
    Uses asciidoctor-dita-vale styles from ~/.dita-agent/tools/
    Creates a temporary config file to avoid modifying user's existing .vale.ini
    """
    
    def __init__(
        self,
        styles_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
    ):
        """
        Initialize Vale runner.

        Args:
            styles_path: Path to Vale styles directory.
                        Defaults to ~/.dita-agent/tools/vale-styles (includes AsciiDocDITA, RedHat, AsciiDoc)
            config_path: Path to .vale.ini file.
                        If None, creates a temporary config with all DITA and RedHat styles.
        """
        self.styles_path = styles_path or (
            Path.home() / ".dita-agent" / "tools" / "vale-styles"
        )
        self._temp_config_path: Optional[Path] = None
        
        if config_path:
            self.config_path = config_path
        else:
            # Create temporary config with correct DITA styles
            self.config_path = self._create_temp_config()
    
    def is_available(self) -> bool:
        """Check if Vale is installed and available."""
        return shutil.which("vale") is not None

    @staticmethod
    def find_project_config(project_dir: Path) -> Optional[Path]:
        """
        Find the project's .vale.ini file.

        Searches upward from project_dir to find .vale.ini

        Args:
            project_dir: Starting directory to search from.

        Returns:
            Path to .vale.ini if found, None otherwise.
        """
        current = project_dir.resolve()

        # Search upward through parent directories
        while current != current.parent:
            vale_ini = current / ".vale.ini"
            if vale_ini.exists():
                return vale_ini
            current = current.parent

        return None
    
    def _create_temp_config(self) -> Path:
        """
        Create a temporary .vale.ini config file for DITA checking.
        
        This approach:
        - Never modifies user's existing .vale.ini
        - Ensures correct AsciiDocDITA styles are used
        - Cleans up automatically (temp file)
        
        Returns:
            Path to the temporary config file.
        """
        # Create temp file that persists until explicitly deleted or program ends
        fd, temp_path = tempfile.mkstemp(suffix='.ini', prefix='vale-dita-agent-')
        self._temp_config_path = Path(temp_path)
        
        config_content = f'''# Temporary Vale config for DITA Agent
# This file is auto-generated and will be cleaned up after the run

StylesPath = {self.styles_path}
MinAlertLevel = suggestion

[*.adoc]
BasedOnStyles = AsciiDocDITA, RedHat
'''
        
        # Write config
        with open(fd, 'w') as f:
            f.write(config_content)
        
        return self._temp_config_path
    
    def cleanup(self) -> None:
        """Clean up temporary config file if created."""
        if self._temp_config_path and self._temp_config_path.exists():
            try:
                self._temp_config_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors
    
    def __del__(self):
        """Destructor to clean up temp file."""
        self.cleanup()
    
    def run(
        self,
        files: List[Path],
        project_dir: Optional[Path] = None,
    ) -> ValeResult:
        """
        Run Vale on the specified files.

        Args:
            files: List of files to lint.
            project_dir: Project directory (for finding .vale.ini).

        Returns:
            ValeResult with all issues found.
        """
        if not self.is_available():
            return ValeResult(
                success=False,
                error_message="Vale is not installed. Please install Vale first.",
            )

        if not files:
            return ValeResult(success=True)

        # Determine which config to use
        config_to_use = self.config_path

        # If project_dir provided, try to find project's .vale.ini
        if project_dir:
            project_config = self.find_project_config(project_dir)
            if project_config:
                config_to_use = project_config

        # Build command
        cmd = ["vale", "--output", "JSON"]

        # Use the selected config
        cmd.extend(["--config", str(config_to_use)])

        # Add files
        cmd.extend([str(f) for f in files])
        
        try:
            # Run Vale
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_dir,
                timeout=120,  # 2 minute timeout
            )
            
            # Parse output
            # Vale may output to stderr for errors/warnings about config
            output = result.stdout or ""
            return self._parse_output(output, result.returncode)
            
        except subprocess.TimeoutExpired:
            return ValeResult(
                success=False,
                error_message="Vale timed out after 120 seconds",
            )
        except Exception as e:
            return ValeResult(
                success=False,
                error_message=f"Failed to run Vale: {e}",
            )
    
    def run_single(self, filepath: Path, project_dir: Optional[Path] = None) -> ValeResult:
        """
        Run Vale on a single file.
        
        Args:
            filepath: File to lint.
            project_dir: Project directory.
            
        Returns:
            ValeResult with issues for this file.
        """
        return self.run([filepath], project_dir)
    
    def _parse_output(self, output: str, return_code: int) -> ValeResult:
        """
        Parse Vale JSON output.
        
        Args:
            output: JSON output from Vale.
            return_code: Vale exit code.
            
        Returns:
            Parsed ValeResult.
        """
        issues = []
        errors = 0
        warnings = 0
        suggestions = 0
        
        if not output.strip():
            # No output = no issues
            return ValeResult(success=True)
        
        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            return ValeResult(
                success=False,
                error_message=f"Failed to parse Vale output: {e}",
            )
        
        # Vale output is a dict of filepath -> list of issues
        for filepath, file_issues in data.items():
            for issue_data in file_issues:
                severity = issue_data.get("Severity", "warning").lower()
                
                issue = ValeIssue(
                    filepath=Path(filepath),
                    line=issue_data.get("Line", 1),
                    column=issue_data.get("Span", [1, 1])[0],
                    rule=issue_data.get("Check", "Unknown"),
                    message=issue_data.get("Message", ""),
                    severity=severity,
                    context=issue_data.get("Match", ""),
                )
                issues.append(issue)
                
                # Count by severity
                if severity == "error":
                    errors += 1
                elif severity == "warning":
                    warnings += 1
                else:
                    suggestions += 1
        
        return ValeResult(
            success=True,
            issues=issues,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )
    
    def create_permanent_vale_ini(self, project_dir: Path) -> Path:
        """
        Create a permanent .vale.ini file for a project.
        
        Use this if you want to add DITA checking to your project permanently.
        The agent uses a temporary config by default to avoid modifying your project.
        
        Args:
            project_dir: Project root directory.
            
        Returns:
            Path to the created .vale.ini file.
        """
        vale_ini = project_dir / ".vale.ini"
        
        config_content = f'''# Vale configuration for DITA compatibility
# Generated by dita-agent - you can customize this file

StylesPath = {self.styles_path}

MinAlertLevel = suggestion

[*.adoc]
BasedOnStyles = AsciiDocDITA, RedHat
'''
        
        vale_ini.write_text(config_content)
        return vale_ini
    
    def get_issues_summary(self, result: ValeResult) -> str:
        """
        Get a human-readable summary of Vale issues.
        
        Args:
            result: ValeResult to summarize.
            
        Returns:
            Formatted summary string.
        """
        if not result.success:
            return f"Vale failed: {result.error_message}"
        
        if not result.has_issues():
            return "No DITA compatibility issues found."
        
        lines = [
            f"Found {len(result.issues)} issue(s):",
            f"  Errors: {result.errors}",
            f"  Warnings: {result.warnings}",
            f"  Suggestions: {result.suggestions}",
            "",
            "Issues by rule:",
        ]
        
        # Group by rule
        by_rule: Dict[str, int] = {}
        for issue in result.issues:
            by_rule[issue.rule] = by_rule.get(issue.rule, 0) + 1
        
        for rule, count in sorted(by_rule.items(), key=lambda x: -x[1]):
            lines.append(f"  {rule}: {count}")
        
        return "\n".join(lines)
