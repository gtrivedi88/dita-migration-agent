"""
Git operations utility module.

Handles .gitignore management to ensure agent-created files
don't pollute the user's git status.
"""

from pathlib import Path
from typing import Optional

# Files/directories the agent creates in project directory
AGENT_IGNORES = [
    ".dita-agent/",
]


def ensure_gitignore_updated(project_dir: Path, silent: bool = False) -> bool:
    """
    Ensure .dita-agent/ is in .gitignore BEFORE creating any files.
    
    This MUST be called at the very start of any operation that creates
    files in the user's project directory. This prevents backup files
    and session data from appearing in git status.
    
    Args:
        project_dir: Path to the project root directory.
        silent: If True, don't print messages.
        
    Returns:
        True if .gitignore was updated, False if already configured.
        
    Example:
        >>> ensure_gitignore_updated(Path("/path/to/project"))
        True  # .gitignore was updated
        >>> ensure_gitignore_updated(Path("/path/to/project"))
        False  # Already configured, no changes needed
    """
    gitignore = project_dir / ".gitignore"
    entries_to_add = []
    
    # Check which entries need to be added
    if gitignore.exists():
        try:
            content = gitignore.read_text()
        except (IOError, OSError) as e:
            if not silent:
                print(f"⚠ Could not read .gitignore: {e}")
            return False
        
        for entry in AGENT_IGNORES:
            if entry not in content:
                entries_to_add.append(entry)
    else:
        entries_to_add = AGENT_IGNORES.copy()
    
    # Nothing to add
    if not entries_to_add:
        return False
    
    # Build the content to append
    new_content = "\n# DITA Migration Agent (auto-added)\n"
    for entry in entries_to_add:
        new_content += f"{entry}\n"
    
    # Write to .gitignore
    try:
        if gitignore.exists():
            with open(gitignore, "a") as f:
                f.write(new_content)
        else:
            gitignore.write_text(new_content.strip() + "\n")
        
        if not silent:
            print(f"ℹ Added {', '.join(entries_to_add)} to .gitignore")
        return True
        
    except (IOError, OSError) as e:
        if not silent:
            print(f"⚠ Could not update .gitignore: {e}")
        return False


def is_git_repository(path: Path) -> bool:
    """
    Check if the given path is inside a git repository.
    
    Args:
        path: Path to check.
        
    Returns:
        True if path is inside a git repository.
    """
    current = path.resolve()
    while current != current.parent:
        if (current / ".git").is_dir():
            return True
        current = current.parent
    return False


def get_git_root(path: Path) -> Optional[Path]:
    """
    Find the root of the git repository containing the given path.
    
    Args:
        path: Path inside the repository.
        
    Returns:
        Path to git root, or None if not in a git repository.
    """
    current = path.resolve()
    while current != current.parent:
        if (current / ".git").is_dir():
            return current
        current = current.parent
    return None
