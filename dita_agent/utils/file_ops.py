"""
File operations utility module.

Handles safe file reading/writing and backup management.
All file modifications go through this module to ensure:
1. Backups are created before any modification
2. Files can be restored on error
3. Encoding is handled consistently
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

# Default encoding for AsciiDoc files
DEFAULT_ENCODING = "utf-8"

# Backup directory name (inside project's .dita-agent/)
BACKUP_DIR_NAME = "backups"


def get_backup_dir(project_dir: Path) -> Path:
    """
    Get the backup directory for a project.
    
    Creates the directory structure if it doesn't exist:
    .dita-agent/backups/<timestamp>/
    
    Args:
        project_dir: Path to the project root.
        
    Returns:
        Path to the backup directory for current session.
    """
    backup_root = project_dir / ".dita-agent" / BACKUP_DIR_NAME
    backup_root.mkdir(parents=True, exist_ok=True)
    return backup_root


def get_session_backup_dir(project_dir: Path, session_id: Optional[str] = None) -> Path:
    """
    Get a session-specific backup directory.
    
    Args:
        project_dir: Path to the project root.
        session_id: Optional session identifier. If None, uses timestamp.
        
    Returns:
        Path to the session-specific backup directory.
    """
    backup_root = get_backup_dir(project_dir)
    
    if session_id is None:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    session_dir = backup_root / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def backup_file(
    filepath: Path,
    project_dir: Path,
    session_id: Optional[str] = None,
) -> Optional[Path]:
    """
    Create a backup of a file before modification.
    
    The backup preserves the relative path structure:
    .dita-agent/backups/<session>/<relative/path/to/file.adoc>
    
    Args:
        filepath: Path to the file to backup.
        project_dir: Path to the project root.
        session_id: Optional session identifier.
        
    Returns:
        Path to the backup file, or None if backup failed.
        
    Example:
        >>> backup_file(
        ...     Path("/project/modules/topic.adoc"),
        ...     Path("/project"),
        ...     "20260115_120000"
        ... )
        Path('/project/.dita-agent/backups/20260115_120000/modules/topic.adoc')
    """
    if not filepath.exists():
        return None
    
    try:
        # Get relative path from project root
        try:
            rel_path = filepath.resolve().relative_to(project_dir.resolve())
        except ValueError:
            # File is outside project - use filename only
            rel_path = Path(filepath.name)
        
        # Create backup path
        session_dir = get_session_backup_dir(project_dir, session_id)
        backup_path = session_dir / rel_path
        
        # Create parent directories
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        shutil.copy2(filepath, backup_path)
        
        return backup_path
        
    except (IOError, OSError, shutil.Error) as e:
        print(f"⚠ Failed to backup {filepath}: {e}")
        return None


def restore_file(
    filepath: Path,
    backup_path: Path,
) -> bool:
    """
    Restore a file from its backup.
    
    Args:
        filepath: Path to the file to restore.
        backup_path: Path to the backup file.
        
    Returns:
        True if restoration succeeded, False otherwise.
    """
    if not backup_path.exists():
        print(f"⚠ Backup not found: {backup_path}")
        return False
    
    try:
        shutil.copy2(backup_path, filepath)
        return True
    except (IOError, OSError, shutil.Error) as e:
        print(f"⚠ Failed to restore {filepath}: {e}")
        return False


def read_file_safe(
    filepath: Path,
    encoding: str = DEFAULT_ENCODING,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Safely read a file's contents.
    
    Args:
        filepath: Path to the file to read.
        encoding: Character encoding to use.
        
    Returns:
        Tuple of (content, error). If successful, error is None.
        If failed, content is None and error contains the error message.
        
    Example:
        >>> content, error = read_file_safe(Path("topic.adoc"))
        >>> if error:
        ...     print(f"Failed: {error}")
        ... else:
        ...     print(f"Read {len(content)} characters")
    """
    if not filepath.exists():
        return None, f"File not found: {filepath}"
    
    if not filepath.is_file():
        return None, f"Not a file: {filepath}"
    
    try:
        content = filepath.read_text(encoding=encoding)
        return content, None
    except UnicodeDecodeError as e:
        return None, f"Encoding error ({encoding}): {e}"
    except (IOError, OSError) as e:
        return None, f"Read error: {e}"


def write_file_safe(
    filepath: Path,
    content: str,
    encoding: str = DEFAULT_ENCODING,
    create_parents: bool = True,
) -> Optional[str]:
    """
    Safely write content to a file.
    
    Args:
        filepath: Path to the file to write.
        content: Content to write.
        encoding: Character encoding to use.
        create_parents: If True, create parent directories if needed.
        
    Returns:
        None if successful, error message if failed.
        
    Example:
        >>> error = write_file_safe(Path("topic.adoc"), new_content)
        >>> if error:
        ...     print(f"Failed: {error}")
    """
    try:
        if create_parents:
            filepath.parent.mkdir(parents=True, exist_ok=True)
        
        filepath.write_text(content, encoding=encoding)
        return None
        
    except (IOError, OSError) as e:
        return f"Write error: {e}"


def get_file_hash(filepath: Path) -> Optional[str]:
    """
    Get a hash of file contents for change detection.
    
    Args:
        filepath: Path to the file.
        
    Returns:
        MD5 hash of file contents, or None if file can't be read.
    """
    import hashlib
    
    content, error = read_file_safe(filepath)
    if error:
        return None
    
    return hashlib.md5(content.encode()).hexdigest()


def files_are_identical(file1: Path, file2: Path) -> bool:
    """
    Check if two files have identical contents.
    
    Args:
        file1: First file path.
        file2: Second file path.
        
    Returns:
        True if files have identical contents.
    """
    content1, _ = read_file_safe(file1)
    content2, _ = read_file_safe(file2)
    
    if content1 is None or content2 is None:
        return False
    
    return content1 == content2
