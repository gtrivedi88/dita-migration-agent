"""
Utility functions.

File operations and git integration helpers.
"""

from dita_agent.utils.git_ops import ensure_gitignore_updated
from dita_agent.utils.file_ops import (
    backup_file,
    restore_file,
    read_file_safe,
    write_file_safe,
    get_backup_dir,
)

__all__ = [
    "ensure_gitignore_updated",
    "backup_file",
    "restore_file",
    "read_file_safe",
    "write_file_safe",
    "get_backup_dir",
]
