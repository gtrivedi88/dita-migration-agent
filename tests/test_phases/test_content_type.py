"""
Tests for Phase 1: Content Type Assignment.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from dita_agent.phases.content_type import (
    ContentTypePhase,
    ContentTypeResult,
    PhaseResult,
    MODULE_TYPE_PATTERN,
)
from dita_agent.core.memory import SessionMemory
from dita_agent.llm.client import LLMClient, LLMResponse


class TestModuleTypePattern:
    """Tests for the :_mod-docs-content-type: regex pattern."""
    
    def test_matches_procedure(self):
        """Test matching PROCEDURE type."""
        content = ":_mod-docs-content-type: PROCEDURE\n\n= Title"
        match = MODULE_TYPE_PATTERN.search(content)
        
        assert match is not None
        assert match.group(1) == "PROCEDURE"
    
    def test_matches_concept(self):
        """Test matching CONCEPT type."""
        content = "= Title\n:_mod-docs-content-type: CONCEPT"
        match = MODULE_TYPE_PATTERN.search(content)
        
        assert match is not None
        assert match.group(1) == "CONCEPT"
    
    def test_matches_with_spaces(self):
        """Test matching with extra spaces."""
        content = ":_mod-docs-content-type:   REFERENCE"
        match = MODULE_TYPE_PATTERN.search(content)
        
        assert match is not None
        assert match.group(1) == "REFERENCE"
    
    def test_no_match_without_attribute(self):
        """Test no match when attribute is missing."""
        content = "= Title\n\nContent without module type."
        match = MODULE_TYPE_PATTERN.search(content)
        
        assert match is None


class TestContentTypePhase:
    """Tests for ContentTypePhase class."""
    
    def create_mock_llm(self, content_type: str = "PROCEDURE"):
        """Create a mock LLM client."""
        mock_llm = Mock(spec=LLMClient)
        mock_llm.generate.return_value = LLMResponse(
            success=True,
            content=json.dumps({
                "content_type": content_type,
                "reasoning": "Has .Procedure block",
                "old_string": "= Title",
                "new_string": f":_mod-docs-content-type: {content_type}\n\n= Title",
            }),
            parsed={
                "content_type": content_type,
                "reasoning": "Has .Procedure block",
                "old_string": "= Title",
                "new_string": f":_mod-docs-content-type: {content_type}\n\n= Title",
            },
            tokens_used=100,
        )
        return mock_llm
    
    def test_skips_file_with_existing_type(self, tmp_path):
        """Test that files with existing type are skipped."""
        # Create file with existing type
        test_file = tmp_path / "topic.adoc"
        test_file.write_text(":_mod-docs-content-type: PROCEDURE\n\n= Title\n\nContent")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = ContentTypePhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        result = phase.run([test_file])
        
        assert result.success is True
        assert result.files_skipped == 1
        assert result.files_fixed == 0
        # LLM should not be called
        mock_llm.generate.assert_not_called()
    
    def test_fixes_file_missing_type(self, tmp_path):
        """Test fixing a file missing content type."""
        # Create file without type
        test_file = tmp_path / "topic.adoc"
        test_file.write_text("= Title\n\n.Procedure\n. Step 1")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm("PROCEDURE")
        
        phase = ContentTypePhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        result = phase.run([test_file])
        
        assert result.success is True
        assert result.files_fixed == 1
        
        # Verify file was updated
        content = test_file.read_text()
        assert ":_mod-docs-content-type: PROCEDURE" in content
    
    def test_dry_run_does_not_modify(self, tmp_path):
        """Test that dry run doesn't modify files."""
        test_file = tmp_path / "topic.adoc"
        original_content = "= Title\n\nContent"
        test_file.write_text(original_content)
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = ContentTypePhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
            dry_run=True,
        )
        
        result = phase.run([test_file])
        
        assert result.success is True
        # File should be unchanged
        assert test_file.read_text() == original_content
    
    def test_handles_llm_error(self, tmp_path):
        """Test handling of LLM errors."""
        test_file = tmp_path / "topic.adoc"
        test_file.write_text("= Title\n\nContent")
        
        memory = SessionMemory()
        mock_llm = Mock(spec=LLMClient)
        mock_llm.generate.return_value = LLMResponse(
            success=False,
            error="API timeout",
        )
        
        phase = ContentTypePhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
            max_retries=1,
        )
        
        result = phase.run([test_file])
        
        assert result.success is False
        assert result.files_failed == 1
    
    def test_handles_invalid_content_type(self, tmp_path):
        """Test handling of invalid content type from LLM."""
        test_file = tmp_path / "topic.adoc"
        test_file.write_text("= Title\n\nContent")
        
        memory = SessionMemory()
        mock_llm = Mock(spec=LLMClient)
        mock_llm.generate.return_value = LLMResponse(
            success=True,
            parsed={"content_type": "INVALID_TYPE"},
            tokens_used=50,
        )
        
        phase = ContentTypePhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
            max_retries=1,
        )
        
        result = phase.run([test_file])
        
        assert result.success is False
        assert result.files_failed == 1
    
    def test_creates_backup_before_edit(self, tmp_path):
        """Test that backups are created."""
        test_file = tmp_path / "topic.adoc"
        test_file.write_text("= Title\n\nContent")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = ContentTypePhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        phase.run([test_file])
        
        # Check backup directory was created
        backup_dir = tmp_path / ".dita-agent" / "backups"
        assert backup_dir.exists()
    
    def test_get_files_missing_type(self, tmp_path):
        """Test finding files missing type."""
        # File with type
        file_with_type = tmp_path / "with_type.adoc"
        file_with_type.write_text(":_mod-docs-content-type: CONCEPT\n\n= Title")
        
        # File without type
        file_without_type = tmp_path / "without_type.adoc"
        file_without_type.write_text("= Title\n\nContent")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = ContentTypePhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        missing = phase.get_files_missing_type([file_with_type, file_without_type])
        
        assert len(missing) == 1
        assert file_without_type in missing
    
    def test_validate_all_have_type(self, tmp_path):
        """Test validation when all files have type."""
        file1 = tmp_path / "file1.adoc"
        file2 = tmp_path / "file2.adoc"
        
        file1.write_text(":_mod-docs-content-type: PROCEDURE\n\n= Title 1")
        file2.write_text(":_mod-docs-content-type: CONCEPT\n\n= Title 2")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = ContentTypePhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        valid, missing = phase.validate([file1, file2])
        
        assert valid is True
        assert len(missing) == 0
    
    def test_validate_some_missing(self, tmp_path):
        """Test validation when some files are missing type."""
        file1 = tmp_path / "file1.adoc"
        file2 = tmp_path / "file2.adoc"
        
        file1.write_text(":_mod-docs-content-type: PROCEDURE\n\n= Title 1")
        file2.write_text("= Title 2\n\nNo type here")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = ContentTypePhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        valid, missing = phase.validate([file1, file2])
        
        assert valid is False
        assert len(missing) == 1
        assert file2 in missing


class TestFallbackEdit:
    """Tests for fallback edit creation."""
    
    def test_creates_edit_for_file_with_title(self, tmp_path):
        """Test creating fallback edit for file with title."""
        memory = SessionMemory()
        mock_llm = Mock(spec=LLMClient)
        
        phase = ContentTypePhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        content = "= My Title\n\nSome content here."
        result = phase._create_fallback_edit(content, "PROCEDURE")
        
        assert result is not None
        old_string, new_string = result
        assert "= My Title" in old_string
        assert ":_mod-docs-content-type: PROCEDURE" in new_string
    
    def test_creates_edit_with_existing_attributes(self, tmp_path):
        """Test creating fallback edit when file has other attributes."""
        memory = SessionMemory()
        mock_llm = Mock(spec=LLMClient)
        
        phase = ContentTypePhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        content = "= My Title\n:author: John\n:date: 2024\n\nContent"
        result = phase._create_fallback_edit(content, "CONCEPT")
        
        assert result is not None
        old_string, new_string = result
        assert ":_mod-docs-content-type: CONCEPT" in new_string


class TestPhaseResult:
    """Tests for PhaseResult dataclass."""
    
    def test_success_when_no_failures(self):
        """Test that success is True when no failures."""
        result = PhaseResult(
            success=True,
            files_processed=5,
            files_fixed=3,
            files_skipped=2,
            files_failed=0,
        )
        
        assert result.success is True
    
    def test_failure_when_files_failed(self, tmp_path):
        """Test that success is False when files failed."""
        result = PhaseResult(
            success=False,
            files_processed=5,
            files_fixed=2,
            files_skipped=1,
            files_failed=2,
            failed_files=[
                (tmp_path / "file1.adoc", "Error 1"),
                (tmp_path / "file2.adoc", "Error 2"),
            ],
        )
        
        assert result.success is False
        assert len(result.failed_files) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
