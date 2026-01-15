"""
Tests for utility modules: git_ops and file_ops.
"""

import tempfile
import pytest
from pathlib import Path

from dita_agent.utils.git_ops import (
    ensure_gitignore_updated,
    is_git_repository,
    get_git_root,
)
from dita_agent.utils.file_ops import (
    backup_file,
    restore_file,
    read_file_safe,
    write_file_safe,
    get_backup_dir,
    get_file_hash,
    files_are_identical,
)


class TestGitOps:
    """Tests for git operations."""
    
    def test_ensure_gitignore_creates_new_file(self, tmp_path):
        """Test creating a new .gitignore file."""
        result = ensure_gitignore_updated(tmp_path, silent=True)
        
        assert result is True
        gitignore = tmp_path / ".gitignore"
        assert gitignore.exists()
        
        content = gitignore.read_text()
        assert ".dita-agent/" in content
    
    def test_ensure_gitignore_updates_existing_file(self, tmp_path):
        """Test updating an existing .gitignore file."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("# Existing content\nnode_modules/\n")
        
        result = ensure_gitignore_updated(tmp_path, silent=True)
        
        assert result is True
        content = gitignore.read_text()
        assert "node_modules/" in content  # Original preserved
        assert ".dita-agent/" in content   # New entry added
    
    def test_ensure_gitignore_idempotent(self, tmp_path):
        """Test that running twice doesn't duplicate entries."""
        # First run
        ensure_gitignore_updated(tmp_path, silent=True)
        # Second run
        result = ensure_gitignore_updated(tmp_path, silent=True)
        
        assert result is False  # No changes needed
        
        content = (tmp_path / ".gitignore").read_text()
        # Should appear only once
        assert content.count(".dita-agent/") == 1
    
    def test_is_git_repository_true(self, tmp_path):
        """Test detecting a git repository."""
        (tmp_path / ".git").mkdir()
        
        assert is_git_repository(tmp_path) is True
        
        # Subdir should also detect the repo
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        assert is_git_repository(subdir) is True
    
    def test_is_git_repository_false(self, tmp_path):
        """Test non-git directory."""
        assert is_git_repository(tmp_path) is False
    
    def test_get_git_root(self, tmp_path):
        """Test finding git root."""
        (tmp_path / ".git").mkdir()
        subdir = tmp_path / "a" / "b" / "c"
        subdir.mkdir(parents=True)
        
        root = get_git_root(subdir)
        assert root == tmp_path
    
    def test_get_git_root_not_found(self, tmp_path):
        """Test when not in a git repository."""
        root = get_git_root(tmp_path)
        assert root is None


class TestFileOps:
    """Tests for file operations."""
    
    def test_read_file_safe_success(self, tmp_path):
        """Test reading a file successfully."""
        test_file = tmp_path / "test.adoc"
        test_file.write_text("= Title\n\nContent here.")
        
        content, error = read_file_safe(test_file)
        
        assert error is None
        assert content == "= Title\n\nContent here."
    
    def test_read_file_safe_not_found(self, tmp_path):
        """Test reading a non-existent file."""
        test_file = tmp_path / "nonexistent.adoc"
        
        content, error = read_file_safe(test_file)
        
        assert content is None
        assert "not found" in error.lower()
    
    def test_write_file_safe_success(self, tmp_path):
        """Test writing a file successfully."""
        test_file = tmp_path / "test.adoc"
        
        error = write_file_safe(test_file, "= New Title\n\nNew content.")
        
        assert error is None
        assert test_file.exists()
        assert test_file.read_text() == "= New Title\n\nNew content."
    
    def test_write_file_safe_creates_parents(self, tmp_path):
        """Test that write creates parent directories."""
        test_file = tmp_path / "a" / "b" / "c" / "test.adoc"
        
        error = write_file_safe(test_file, "Content")
        
        assert error is None
        assert test_file.exists()
    
    def test_backup_file_success(self, tmp_path):
        """Test creating a backup successfully."""
        # Create original file
        original = tmp_path / "modules" / "topic.adoc"
        original.parent.mkdir(parents=True)
        original.write_text("Original content")
        
        # Create backup
        backup_path = backup_file(original, tmp_path, "test_session")
        
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.read_text() == "Original content"
        
        # Check path structure
        expected_rel = Path(".dita-agent/backups/test_session/modules/topic.adoc")
        assert str(backup_path).endswith(str(expected_rel).replace("/", str(Path("/"))))
    
    def test_backup_file_nonexistent(self, tmp_path):
        """Test backing up a file that doesn't exist."""
        nonexistent = tmp_path / "nonexistent.adoc"
        
        backup_path = backup_file(nonexistent, tmp_path)
        
        assert backup_path is None
    
    def test_restore_file_success(self, tmp_path):
        """Test restoring a file from backup."""
        # Create original and backup
        original = tmp_path / "topic.adoc"
        original.write_text("Original content")
        
        backup_path = backup_file(original, tmp_path, "session1")
        
        # Modify original
        original.write_text("Modified content")
        assert original.read_text() == "Modified content"
        
        # Restore
        result = restore_file(original, backup_path)
        
        assert result is True
        assert original.read_text() == "Original content"
    
    def test_restore_file_missing_backup(self, tmp_path):
        """Test restoring when backup doesn't exist."""
        original = tmp_path / "topic.adoc"
        original.write_text("Content")
        
        fake_backup = tmp_path / "nonexistent_backup.adoc"
        
        result = restore_file(original, fake_backup)
        
        assert result is False
    
    def test_get_backup_dir_creates_directory(self, tmp_path):
        """Test that backup dir is created."""
        backup_dir = get_backup_dir(tmp_path)
        
        assert backup_dir.exists()
        assert backup_dir.is_dir()
        assert ".dita-agent" in str(backup_dir)
        assert "backups" in str(backup_dir)
    
    def test_get_file_hash(self, tmp_path):
        """Test file hashing."""
        file1 = tmp_path / "file1.adoc"
        file2 = tmp_path / "file2.adoc"
        
        file1.write_text("Same content")
        file2.write_text("Same content")
        
        hash1 = get_file_hash(file1)
        hash2 = get_file_hash(file2)
        
        assert hash1 is not None
        assert hash1 == hash2
    
    def test_get_file_hash_different_files(self, tmp_path):
        """Test that different files have different hashes."""
        file1 = tmp_path / "file1.adoc"
        file2 = tmp_path / "file2.adoc"
        
        file1.write_text("Content A")
        file2.write_text("Content B")
        
        hash1 = get_file_hash(file1)
        hash2 = get_file_hash(file2)
        
        assert hash1 != hash2
    
    def test_files_are_identical_true(self, tmp_path):
        """Test identical files."""
        file1 = tmp_path / "file1.adoc"
        file2 = tmp_path / "file2.adoc"
        
        file1.write_text("Same content")
        file2.write_text("Same content")
        
        assert files_are_identical(file1, file2) is True
    
    def test_files_are_identical_false(self, tmp_path):
        """Test different files."""
        file1 = tmp_path / "file1.adoc"
        file2 = tmp_path / "file2.adoc"
        
        file1.write_text("Content A")
        file2.write_text("Content B")
        
        assert files_are_identical(file1, file2) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
