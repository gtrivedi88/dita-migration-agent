"""
Scope resolution module.

Determines which files to process based on user input:
- Entire project
- Single assembly + all its includes
- Specific topic files
- First N files with issues

This module handles the complex task of parsing AsciiDoc includes
and building the complete dependency tree.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from dita_agent.utils.file_ops import read_file_safe


# Regex patterns for parsing AsciiDoc
INCLUDE_PATTERN = re.compile(
    r'^include::([^\[]+)\[',
    re.MULTILINE
)

# Directories to skip when scanning
SKIP_DIRS = {
    '.git',
    '.dita-agent',
    'node_modules',
    'build',
    'dist',
    '__pycache__',
    '.venv',
    'venv',
    'titles-generated',
}

# File extensions to process
ADOC_EXTENSIONS = {'.adoc', '.asciidoc'}


@dataclass
class ScopeResult:
    """Result of scope resolution."""
    
    files: List[Path]
    """List of files to process."""
    
    entry_point: Optional[Path] = None
    """The assembly or main file if specified."""
    
    include_tree: dict = field(default_factory=dict)
    """Mapping of files to their includes."""
    
    errors: List[str] = field(default_factory=list)
    """Any errors encountered during resolution."""


class ScopeResolver:
    """
    Resolves the scope of files to process.
    
    Handles three main scenarios:
    1. Assembly mode: Process assembly + all included files
    2. Topics mode: Process specific files
    3. Project mode: Process all AsciiDoc files in project
    """
    
    def __init__(self, project_dir: Path):
        """
        Initialize the scope resolver.
        
        Args:
            project_dir: Root directory of the documentation project.
        """
        self.project_dir = project_dir.resolve()
        self._visited: Set[Path] = set()
        self._include_tree: dict = {}
    
    def resolve(
        self,
        assembly: Optional[Path] = None,
        topics: Optional[List[Path]] = None,
        limit: Optional[int] = None,
    ) -> ScopeResult:
        """
        Resolve the scope of files to process.
        
        Args:
            assembly: If provided, process this assembly and all its includes.
            topics: If provided, process these specific files.
            limit: If provided, limit to first N files.
            
        Returns:
            ScopeResult containing the files to process.
        """
        self._visited.clear()
        self._include_tree.clear()
        
        if assembly:
            return self._resolve_assembly(assembly)
        elif topics:
            return self._resolve_topics(topics)
        else:
            return self._resolve_project(limit)
    
    def _resolve_assembly(self, assembly: Path) -> ScopeResult:
        """
        Resolve an assembly and all its includes.
        
        Args:
            assembly: Path to the assembly file.
            
        Returns:
            ScopeResult with assembly and all included files.
        """
        assembly_path = self._normalize_path(assembly)
        
        if not assembly_path.exists():
            return ScopeResult(
                files=[],
                errors=[f"Assembly not found: {assembly}"],
            )
        
        # Recursively find all includes
        files = self._find_includes(assembly_path)
        
        return ScopeResult(
            files=files,
            entry_point=assembly_path,
            include_tree=self._include_tree.copy(),
        )
    
    def _resolve_topics(self, topics: List[Path]) -> ScopeResult:
        """
        Resolve specific topic files.
        
        Args:
            topics: List of topic file paths.
            
        Returns:
            ScopeResult with the specified files.
        """
        files = []
        errors = []
        
        for topic in topics:
            topic_path = self._normalize_path(topic)
            
            if topic_path.exists():
                files.append(topic_path)
            else:
                errors.append(f"Topic not found: {topic}")
        
        return ScopeResult(
            files=files,
            errors=errors,
        )
    
    def _resolve_project(self, limit: Optional[int] = None) -> ScopeResult:
        """
        Resolve all AsciiDoc files in the project.
        
        Args:
            limit: Maximum number of files to return.
            
        Returns:
            ScopeResult with all project files.
        """
        files = list(self._find_all_adoc_files())
        
        if limit:
            files = files[:limit]
        
        return ScopeResult(files=files)
    
    def _normalize_path(self, path: Path) -> Path:
        """
        Normalize a path relative to the project directory.
        
        Args:
            path: Path to normalize.
            
        Returns:
            Absolute, resolved path.
        """
        if path.is_absolute():
            return path.resolve()
        return (self.project_dir / path).resolve()
    
    def _find_includes(self, filepath: Path) -> List[Path]:
        """
        Recursively find all files included by a file.
        
        Args:
            filepath: Path to the file to analyze.
            
        Returns:
            List of all files (including the input file) in dependency order.
        """
        resolved = filepath.resolve()
        
        # Prevent infinite loops from circular includes
        if resolved in self._visited:
            return []
        
        self._visited.add(resolved)
        result = [resolved]
        
        # Read file content
        content, error = read_file_safe(filepath)
        if error:
            return result
        
        # Find all includes
        includes = self._parse_includes(content, filepath.parent)
        self._include_tree[resolved] = includes
        
        # Recursively process includes
        for include_path in includes:
            if include_path.exists() and include_path not in self._visited:
                result.extend(self._find_includes(include_path))
        
        return result
    
    def _parse_includes(self, content: str, base_dir: Path) -> List[Path]:
        """
        Parse include directives from AsciiDoc content.
        
        Handles various include formats:
        - include::path/to/file.adoc[]
        - include::{attribute}/file.adoc[]
        - include::../relative/path.adoc[]
        
        Args:
            content: AsciiDoc file content.
            base_dir: Directory to resolve relative paths from.
            
        Returns:
            List of included file paths.
        """
        includes = []
        
        for match in INCLUDE_PATTERN.finditer(content):
            include_ref = match.group(1).strip()
            
            # Skip attribute-based includes (e.g., {snippets-dir}/...)
            # These need attribute resolution which is complex
            if '{' in include_ref:
                # Try to handle common patterns
                include_ref = self._resolve_common_attributes(include_ref)
                if '{' in include_ref:
                    # Still has unresolved attributes, skip
                    continue
            
            # Resolve the path
            include_path = (base_dir / include_ref).resolve()
            
            # Only include .adoc files that exist
            if include_path.suffix.lower() in ADOC_EXTENSIONS:
                includes.append(include_path)
        
        return includes
    
    def _resolve_common_attributes(self, include_ref: str) -> str:
        """
        Attempt to resolve common AsciiDoc attributes in include paths.
        
        Args:
            include_ref: Include reference with potential attributes.
            
        Returns:
            Resolved reference (may still contain unresolved attributes).
        """
        # Common attribute patterns to resolve
        common_attrs = {
            '{snippets-dir}': 'snippets',
            '{modules-dir}': 'modules',
            '{assemblies-dir}': 'assemblies',
            '{imagesdir}': 'images',
        }
        
        for attr, value in common_attrs.items():
            include_ref = include_ref.replace(attr, value)
        
        return include_ref
    
    def _find_all_adoc_files(self) -> Set[Path]:
        """
        Find all AsciiDoc files in the project.
        
        Excludes:
        - Hidden directories
        - Common build/cache directories
        - Files in .dita-agent/
        
        Returns:
            Set of paths to all AsciiDoc files.
        """
        adoc_files = set()
        visited_paths = set()  # Prevent symlink loops
        
        def scan_directory(directory: Path):
            try:
                resolved = directory.resolve()
                if resolved in visited_paths:
                    return  # Symlink loop detected
                visited_paths.add(resolved)
                
                for item in directory.iterdir():
                    # Skip hidden files/directories
                    if item.name.startswith('.'):
                        continue
                    
                    # Skip excluded directories
                    if item.is_dir() and item.name in SKIP_DIRS:
                        continue
                    
                    if item.is_dir():
                        scan_directory(item)
                    elif item.suffix.lower() in ADOC_EXTENSIONS:
                        adoc_files.add(item.resolve())
                        
            except PermissionError:
                pass  # Skip directories we can't read
        
        scan_directory(self.project_dir)
        return adoc_files
    
    def get_file_count(self) -> int:
        """Get the number of files in scope."""
        return len(self._visited)
    
    def print_tree(self) -> str:
        """
        Generate a text representation of the include tree.
        
        Returns:
            String representation of the include tree.
        """
        lines = []
        
        def print_node(path: Path, indent: int = 0):
            rel_path = self._get_relative_path(path)
            prefix = "  " * indent + ("├── " if indent > 0 else "")
            lines.append(f"{prefix}{rel_path}")
            
            includes = self._include_tree.get(path, [])
            for include in includes:
                print_node(include, indent + 1)
        
        for root in self._include_tree.keys():
            if not any(root in includes for includes in self._include_tree.values()):
                print_node(root)
        
        return "\n".join(lines)
    
    def _get_relative_path(self, path: Path) -> str:
        """Get path relative to project directory."""
        try:
            return str(path.relative_to(self.project_dir))
        except ValueError:
            return str(path)
