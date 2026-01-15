"""
Callouts conversion tool integration.

Runs the callouts-conversion tool from ~/.dita-agent/tools/
using the isolated venv at ~/.dita-agent/venv/
"""

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict

from dita_agent.utils.file_ops import read_file_safe


# Tool locations
TOOL_DIR = Path.home() / ".dita-agent" / "tools" / "callouts-conversion"
VENV_DIR = Path.home() / ".dita-agent" / "venv"


def get_venv_python() -> Path:
    """Get the path to Python in the isolated venv."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


@dataclass
class CalloutsResult:
    """Result of running callouts conversion."""
    
    success: bool
    """Whether the tool ran successfully."""
    
    files_modified: List[Path] = field(default_factory=list)
    """List of files that were modified."""
    
    files_unchanged: List[Path] = field(default_factory=list)
    """List of files that were not changed."""
    
    error_message: Optional[str] = None
    """Error message if tool failed."""
    
    stdout: str = ""
    """Standard output from the tool."""
    
    stderr: str = ""
    """Standard error from the tool."""


class CalloutsRunner:
    """
    Runner for the callouts-conversion tool.
    
    This tool converts callout markers (<1>, <2>, etc.) in code blocks
    to DITA-compatible description lists.
    """
    
    def __init__(
        self,
        tool_dir: Optional[Path] = None,
        venv_python: Optional[Path] = None,
    ):
        """
        Initialize the callouts runner.
        
        Args:
            tool_dir: Path to callouts-conversion tool.
                     Defaults to ~/.dita-agent/tools/callouts-conversion
            venv_python: Path to Python in the venv.
                        Defaults to ~/.dita-agent/venv/bin/python
        """
        self.tool_dir = tool_dir or TOOL_DIR
        self.venv_python = venv_python or get_venv_python()
        
        # Main orchestrator script
        self.orchestrator = self.tool_dir / "callouts_orchestrator.py"
    
    def is_available(self) -> bool:
        """Check if the tool is available."""
        return (
            self.tool_dir.exists() and
            self.orchestrator.exists() and
            self.venv_python.exists()
        )
    
    def has_callouts(self, content: str) -> bool:
        """
        Check if content has callout markers.
        
        Args:
            content: File content to check.
            
        Returns:
            True if callout markers are present.
        """
        import re
        # Look for <1>, <2>, etc. patterns
        return bool(re.search(r'<\d+>', content))
    
    def find_files_with_callouts(self, files: List[Path]) -> List[Path]:
        """
        Find files that contain callout markers.
        
        Args:
            files: List of files to check.
            
        Returns:
            List of files containing callouts.
        """
        result = []
        for filepath in files:
            content, error = read_file_safe(filepath)
            if content and self.has_callouts(content):
                result.append(filepath)
        return result
    
    def run(
        self,
        files: List[Path],
        dry_run: bool = False,
    ) -> CalloutsResult:
        """
        Run the callouts conversion tool on files.
        
        Args:
            files: List of files to process.
            dry_run: If True, don't modify files (just report).
            
        Returns:
            CalloutsResult with results.
        """
        if not self.is_available():
            missing = []
            if not self.tool_dir.exists():
                missing.append(f"Tool directory: {self.tool_dir}")
            if not self.orchestrator.exists():
                missing.append(f"Orchestrator script: {self.orchestrator}")
            if not self.venv_python.exists():
                missing.append(f"Venv Python: {self.venv_python}")
            
            return CalloutsResult(
                success=False,
                error_message=f"Callouts tool not available. Missing: {', '.join(missing)}",
            )
        
        if not files:
            return CalloutsResult(success=True)
        
        # Filter to only files with callouts
        files_to_process = self.find_files_with_callouts(files)
        
        if not files_to_process:
            return CalloutsResult(
                success=True,
                files_unchanged=list(files),
            )
        
        # Record original content for comparison
        original_content: Dict[Path, str] = {}
        for filepath in files_to_process:
            content, _ = read_file_safe(filepath)
            if content:
                original_content[filepath] = content
        
        # Build command
        cmd = [str(self.venv_python), str(self.orchestrator)]
        
        if dry_run:
            cmd.append("--dry-run")
        
        # Add files
        cmd.extend([str(f) for f in files_to_process])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            
            # Determine which files were modified
            modified = []
            unchanged = []
            
            for filepath in files_to_process:
                new_content, _ = read_file_safe(filepath)
                if new_content and original_content.get(filepath) != new_content:
                    modified.append(filepath)
                else:
                    unchanged.append(filepath)
            
            # Add files that weren't processed (no callouts)
            unchanged.extend([f for f in files if f not in files_to_process])
            
            return CalloutsResult(
                success=result.returncode == 0,
                files_modified=modified,
                files_unchanged=unchanged,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=result.stderr if result.returncode != 0 else None,
            )
            
        except subprocess.TimeoutExpired:
            return CalloutsResult(
                success=False,
                error_message="Callouts conversion timed out after 5 minutes",
            )
        except Exception as e:
            return CalloutsResult(
                success=False,
                error_message=f"Failed to run callouts conversion: {e}",
            )
    
    def run_single(self, filepath: Path, dry_run: bool = False) -> CalloutsResult:
        """
        Run the callouts conversion on a single file.
        
        Args:
            filepath: File to process.
            dry_run: If True, don't modify files.
            
        Returns:
            CalloutsResult with results.
        """
        return self.run([filepath], dry_run)
    
    def get_summary(self, result: CalloutsResult) -> str:
        """
        Get a human-readable summary of the conversion result.
        
        Args:
            result: CalloutsResult to summarize.
            
        Returns:
            Formatted summary string.
        """
        if not result.success:
            return f"Callouts conversion failed: {result.error_message}"
        
        lines = [
            f"Files modified: {len(result.files_modified)}",
            f"Files unchanged: {len(result.files_unchanged)}",
        ]
        
        if result.files_modified:
            lines.append("\nModified files:")
            for f in result.files_modified:
                lines.append(f"  • {f.name}")
        
        return "\n".join(lines)
