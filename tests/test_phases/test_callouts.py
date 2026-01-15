"""
Tests for Phase 2: Callouts Conversion.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from dita_agent.phases.callouts import (
    CalloutsPhase,
    CalloutsPhaseResult,
    CalloutFixResult,
    CALLOUT_IN_CODE_PATTERN,
)
from dita_agent.core.memory import SessionMemory
from dita_agent.llm.client import LLMClient, LLMResponse
from dita_agent.tools.callouts import CalloutsRunner, CalloutsResult


class TestCalloutPatterns:
    """Tests for callout detection patterns."""
    
    def test_matches_simple_callout(self):
        """Test matching simple callout marker."""
        content = "code here <1>"
        match = CALLOUT_IN_CODE_PATTERN.search(content)
        
        assert match is not None
        assert match.group(1) == "1"
    
    def test_matches_multiple_callouts(self):
        """Test matching multiple callout markers."""
        content = "line1 <1>\nline2 <2>\nline3 <10>"
        matches = CALLOUT_IN_CODE_PATTERN.findall(content)
        
        assert len(matches) == 3
        assert "1" in matches
        assert "2" in matches
        assert "10" in matches
    
    def test_no_match_without_callouts(self):
        """Test no match when no callouts present."""
        content = "plain code without callouts"
        match = CALLOUT_IN_CODE_PATTERN.search(content)
        
        assert match is None
    
    def test_matches_callout_in_code_block(self):
        """Test matching callout inside code block."""
        content = '''[source,yaml]
----
apiVersion: v1 <1>
kind: Pod <2>
----
<1> API version
<2> Resource type
'''
        matches = CALLOUT_IN_CODE_PATTERN.findall(content)
        
        # Should find 4: 2 in code, 2 in list
        assert len(matches) == 4


class TestCalloutsPhase:
    """Tests for CalloutsPhase class."""
    
    def create_mock_llm(self, success: bool = True, review_correct: bool = True):
        """Create a mock LLM client."""
        mock_llm = Mock(spec=LLMClient)
        
        if review_correct:
            review_response = {
                "is_correct": True,
                "issues": [],
            }
        else:
            review_response = {
                "is_correct": False,
                "fix_needed": True,
                "old_string": "wrong",
                "new_string": "correct",
            }
        
        fix_response = {
            "old_string": "code <1>\n<1> desc",
            "new_string": "code\n\ncode:: desc",
        }
        
        mock_llm.generate.return_value = LLMResponse(
            success=success,
            content=json.dumps(review_response if success else {}),
            parsed=review_response if success else None,
            tokens_used=100,
            error=None if success else "API error",
        )
        
        return mock_llm
    
    def test_skips_files_without_callouts(self, tmp_path):
        """Test that files without callouts are skipped."""
        # Create file without callouts
        test_file = tmp_path / "no_callouts.adoc"
        test_file.write_text("= Title\n\nNo callouts here.\n\n.Procedure\n. Step 1")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = CalloutsPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        result = phase.run([test_file])
        
        assert result.success is True
        assert result.files_skipped == 1
        assert result.files_fixed_by_tool == 0
        assert result.files_fixed_by_llm == 0
    
    def test_detects_files_with_callouts(self, tmp_path):
        """Test detection of files with callouts."""
        # Create file with callouts
        file_with = tmp_path / "with_callouts.adoc"
        file_with.write_text("= Title\n\n[source]\n----\ncode <1>\n----\n<1> desc")
        
        # Create file without callouts
        file_without = tmp_path / "without.adoc"
        file_without.write_text("= Title\n\nPlain content")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = CalloutsPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        files_with_callouts = phase._find_files_with_callouts([file_with, file_without])
        
        assert len(files_with_callouts) == 1
        assert file_with in files_with_callouts
    
    def test_has_callouts_true(self, tmp_path):
        """Test _has_callouts returns True for content with callouts."""
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = CalloutsPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        content = "code <1>\n<1> description"
        assert phase._has_callouts(content) is True
    
    def test_has_callouts_false(self, tmp_path):
        """Test _has_callouts returns False for content without callouts."""
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = CalloutsPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        content = "plain content\nno callouts"
        assert phase._has_callouts(content) is False
    
    def test_find_first_callout_line(self, tmp_path):
        """Test finding the first callout line."""
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = CalloutsPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        content = "line 1\nline 2\ncode <1>\nline 4"
        line = phase._find_first_callout_line(content)
        
        assert line == 3
    
    def test_dry_run_does_not_modify(self, tmp_path):
        """Test that dry run doesn't modify files."""
        test_file = tmp_path / "topic.adoc"
        original_content = "= Title\n\n[source]\n----\ncode <1>\n----\n<1> desc"
        test_file.write_text(original_content)
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = CalloutsPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
            dry_run=True,
        )
        
        result = phase.run([test_file])
        
        # File should be unchanged
        assert test_file.read_text() == original_content
    
    def test_validate_no_callouts(self, tmp_path):
        """Test validation when no callouts remain."""
        file1 = tmp_path / "file1.adoc"
        file2 = tmp_path / "file2.adoc"
        
        file1.write_text("= Title\n\nNo callouts")
        file2.write_text("= Title\n\nAlso no callouts")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = CalloutsPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        valid, remaining = phase.validate([file1, file2])
        
        assert valid is True
        assert len(remaining) == 0
    
    def test_validate_with_callouts(self, tmp_path):
        """Test validation when callouts remain."""
        file1 = tmp_path / "file1.adoc"
        file2 = tmp_path / "file2.adoc"
        
        file1.write_text("= Title\n\nNo callouts")
        file2.write_text("= Title\n\ncode <1>\n<1> still has callouts")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = CalloutsPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        valid, remaining = phase.validate([file1, file2])
        
        assert valid is False
        assert len(remaining) == 1
        assert file2 in remaining
    
    def test_extract_callout_context(self, tmp_path):
        """Test extracting context around a callout."""
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = CalloutsPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        content = "\n".join([f"line {i}" for i in range(1, 21)])
        context = phase._extract_callout_context(content, 10, context_lines=6)
        
        # Should include lines around line 10
        assert "line 7" in context or "line 8" in context
        assert "line 10" in context or "line 11" in context


class TestCalloutsPhaseResult:
    """Tests for CalloutsPhaseResult dataclass."""
    
    def test_success_when_no_failures(self):
        """Test that success is True when no failures."""
        result = CalloutsPhaseResult(
            success=True,
            files_processed=5,
            files_fixed_by_tool=3,
            files_fixed_by_llm=1,
            files_skipped=1,
            files_failed=0,
        )
        
        assert result.success is True
    
    def test_failure_when_files_failed(self, tmp_path):
        """Test that success is False when files failed."""
        result = CalloutsPhaseResult(
            success=False,
            files_processed=5,
            files_fixed_by_tool=2,
            files_fixed_by_llm=1,
            files_skipped=0,
            files_failed=2,
            failed_files=[
                (tmp_path / "file1.adoc", "Error 1"),
                (tmp_path / "file2.adoc", "Error 2"),
            ],
        )
        
        assert result.success is False
        assert len(result.failed_files) == 2


class TestCalloutFixResult:
    """Tests for CalloutFixResult dataclass."""
    
    def test_success_result(self):
        """Test successful fix result."""
        result = CalloutFixResult(
            success=True,
            tokens_used=150,
        )
        
        assert result.success is True
        assert result.error is None
    
    def test_failure_result(self):
        """Test failed fix result."""
        result = CalloutFixResult(
            success=False,
            error="Could not find callout pattern",
            tokens_used=100,
        )
        
        assert result.success is False
        assert result.error == "Could not find callout pattern"


class TestIntegration:
    """Integration tests for callouts phase."""
    
    def test_full_flow_no_callouts(self, tmp_path):
        """Test full flow when no files have callouts."""
        # Create files without callouts
        for i in range(3):
            f = tmp_path / f"topic{i}.adoc"
            f.write_text(f"= Topic {i}\n\nContent without callouts.")
        
        files = list(tmp_path.glob("*.adoc"))
        
        memory = SessionMemory()
        mock_llm = Mock(spec=LLMClient)
        
        phase = CalloutsPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        result = phase.run(files)
        
        assert result.success is True
        assert result.files_skipped == 3
        assert result.files_fixed_by_tool == 0
        assert result.files_fixed_by_llm == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
