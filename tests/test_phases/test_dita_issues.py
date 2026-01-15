"""
Tests for Phase 3: All Other DITA Issues.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from dita_agent.phases.dita_issues import (
    DITAIssuesPhase,
    DITAIssuesPhaseResult,
    FixAttempt,
)
from dita_agent.core.memory import SessionMemory
from dita_agent.llm.client import LLMClient, LLMResponse
from dita_agent.tools.vale import ValeRunner, ValeResult, ValeIssue


class TestDITAIssuesPhase:
    """Tests for DITAIssuesPhase class."""
    
    def create_mock_llm(self, old_string: str = "old text", new_string: str = "new text"):
        """Create a mock LLM client."""
        mock_llm = Mock(spec=LLMClient)
        mock_llm.generate.return_value = LLMResponse(
            success=True,
            content=json.dumps({
                "old_string": old_string,
                "new_string": new_string,
            }),
            parsed={
                "old_string": old_string,
                "new_string": new_string,
            },
            tokens_used=100,
        )
        return mock_llm
    
    def create_mock_vale(self, issues: list = None):
        """Create a mock Vale runner."""
        mock_vale = Mock(spec=ValeRunner)
        mock_vale.run.return_value = ValeResult(
            success=True,
            issues=issues or [],
        )
        return mock_vale
    
    def create_vale_issue(
        self,
        filepath: str,
        line: int,
        rule: str,
        severity: str,
        message: str,
        column: int = 1,
    ) -> ValeIssue:
        """Helper to create ValeIssue with all required fields."""
        return ValeIssue(
            filepath=Path(filepath),
            line=line,
            column=column,
            rule=rule,
            message=message,
            severity=severity,
        )
    
    def test_no_issues_found(self, tmp_path):
        """Test when Vale finds no issues."""
        test_file = tmp_path / "topic.adoc"
        test_file.write_text("= Title\n\nPerfect content.")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = DITAIssuesPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        phase.vale = self.create_mock_vale([])
        
        result = phase.run([test_file])
        
        assert result.success is True
        assert result.issues_found == 0
        assert result.issues_fixed == 0
    
    def test_groups_issues_by_file(self, tmp_path):
        """Test grouping issues by file."""
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = DITAIssuesPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        issues = [
            self.create_vale_issue(
                filepath=str(tmp_path / "file1.adoc"),
                line=10,
                column=1,
                rule="DITA.ShortDescription",
                severity="error",
                message="Missing abstract",
            ),
            self.create_vale_issue(
                filepath=str(tmp_path / "file1.adoc"),
                line=5,
                column=1,
                rule="DITA.BlockTitle",
                severity="warning",
                message="Block needs title",
            ),
            self.create_vale_issue(
                filepath=str(tmp_path / "file2.adoc"),
                line=3,
                column=1,
                rule="DITA.ListContinuation",
                severity="error",
                message="List continuation issue",
            ),
        ]
        
        grouped = phase._group_issues_by_file(issues)
        
        assert len(grouped) == 2
        # Issues should be sorted by line (descending)
        file1_issues = grouped[tmp_path / "file1.adoc"]
        assert len(file1_issues) == 2
        assert file1_issues[0].line == 10  # Higher line first
        assert file1_issues[1].line == 5
    
    def test_build_chunk_context(self, tmp_path):
        """Test building chunk context for multiple issues."""
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = DITAIssuesPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        content = "\n".join([f"line {i}" for i in range(1, 21)])
        issues = [
            self.create_vale_issue(
                filepath=str(tmp_path / "test.adoc"),
                line=10,
                column=1,
                rule="DITA.Test",
                severity="warning",
                message="Test issue",
            ),
        ]
        
        context = phase._build_chunk_context(issues, content, tmp_path / "test.adoc")
        
        # Should include the issue line
        assert "line 10" in context
        assert "Issue 1" in context
    
    def test_dry_run_does_not_modify(self, tmp_path):
        """Test that dry run doesn't modify files."""
        test_file = tmp_path / "topic.adoc"
        original_content = "= Title\n\nContent without abstract."
        test_file.write_text(original_content)
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm(
            old_string="Content without abstract",
            new_string="[role=\"_abstract\"]\nContent without abstract",
        )
        
        issues = [
            self.create_vale_issue(
                filepath=str(test_file),
                line=3,
                column=1,
                rule="DITA.ShortDescription",
                severity="error",
                message="Missing abstract",
            ),
        ]
        
        phase = DITAIssuesPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
            dry_run=True,
        )
        phase.vale = self.create_mock_vale(issues)
        
        result = phase.run([test_file])
        
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
            tokens_used=0,
        )
        
        issues = [
            self.create_vale_issue(
                filepath=str(test_file),
                line=3,
                column=1,
                rule="DITA.Test",
                severity="error",
                message="Test error",
            ),
        ]
        
        phase = DITAIssuesPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
            max_retries=1,
        )
        phase.vale = self.create_mock_vale(issues)
        
        result = phase.run([test_file])
        
        assert result.issues_failed == 1
    
    def test_validate_no_errors(self, tmp_path):
        """Test validation when no errors remain."""
        test_file = tmp_path / "topic.adoc"
        test_file.write_text("= Title\n\nContent")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        phase = DITAIssuesPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        phase.vale = self.create_mock_vale([])
        
        valid, remaining = phase.validate([test_file])
        
        assert valid is True
        assert len(remaining) == 0
    
    def test_validate_with_suggestions_ok(self, tmp_path):
        """Test validation passes with only suggestions (not errors/warnings)."""
        test_file = tmp_path / "topic.adoc"
        test_file.write_text("= Title\n\nContent")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        # Only suggestions, no errors or warnings
        suggestions = [
            self.create_vale_issue(
                filepath=str(test_file),
                line=3,
                column=1,
                rule="AsciiDocDITA.AttributeReference",
                severity="suggestion",
                message="Attribute reference found",
            ),
        ]
        
        phase = DITAIssuesPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        phase.vale = self.create_mock_vale(suggestions)
        
        valid, remaining = phase.validate([test_file])
        
        assert valid is True  # Suggestions don't cause failure
    
    def test_validate_with_warnings_fails(self, tmp_path):
        """Test validation fails with warnings (they're real DITA issues)."""
        test_file = tmp_path / "topic.adoc"
        test_file.write_text("= Title\n\nContent")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        # Warnings are real DITA issues (like CalloutList)
        warnings = [
            self.create_vale_issue(
                filepath=str(test_file),
                line=3,
                column=1,
                rule="AsciiDocDITA.CalloutList",
                severity="warning",
                message="Callouts are not supported in DITA",
            ),
        ]
        
        phase = DITAIssuesPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        phase.vale = self.create_mock_vale(warnings)
        
        valid, remaining = phase.validate([test_file])
        
        assert valid is False  # Warnings ARE actionable issues
    
    def test_validate_with_errors_fails(self, tmp_path):
        """Test validation fails with errors."""
        test_file = tmp_path / "topic.adoc"
        test_file.write_text("= Title\n\nContent")
        
        memory = SessionMemory()
        mock_llm = self.create_mock_llm()
        
        errors = [
            self.create_vale_issue(
                filepath=str(test_file),
                line=3,
                column=1,
                rule="DITA.Required",
                severity="error",
                message="Required element missing",
            ),
        ]
        
        phase = DITAIssuesPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        phase.vale = self.create_mock_vale(errors)
        
        valid, remaining = phase.validate([test_file])
        
        assert valid is False


class TestFixAttempt:
    """Tests for FixAttempt dataclass."""
    
    def test_successful_fix(self):
        """Test successful fix attempt."""
        result = FixAttempt(
            success=True,
            tokens_used=150,
            used_llm=True,
        )
        
        assert result.success is True
        assert result.error is None
        assert result.caused_regression is False
    
    def test_failed_fix(self):
        """Test failed fix attempt."""
        result = FixAttempt(
            success=False,
            error="old_string not found",
            tokens_used=100,
            used_llm=True,
        )
        
        assert result.success is False
        assert result.error == "old_string not found"
    
    def test_regression_detected(self):
        """Test fix that caused regression."""
        result = FixAttempt(
            success=False,
            error="Fix introduced new errors",
            tokens_used=200,
            used_llm=True,
            caused_regression=True,
        )
        
        assert result.success is False
        assert result.caused_regression is True


class TestDITAIssuesPhaseResult:
    """Tests for DITAIssuesPhaseResult dataclass."""
    
    def test_success_with_all_fixed(self):
        """Test success when all issues are fixed."""
        result = DITAIssuesPhaseResult(
            success=True,
            files_processed=3,
            issues_found=10,
            issues_fixed=10,
            issues_failed=0,
            fixes_by_rule={"DITA.ShortDescription": 5, "DITA.BlockTitle": 5},
        )
        
        assert result.success is True
        assert len(result.remaining_issues) == 0
    
    def test_failure_with_remaining(self, tmp_path):
        """Test failure when issues remain."""
        remaining = [
            ValeIssue(
                filepath=tmp_path / "file.adoc",
                line=10,
                column=1,
                rule="DITA.Complex",
                severity="error",
                message="Complex issue",
            ),
        ]
        
        result = DITAIssuesPhaseResult(
            success=False,
            files_processed=3,
            issues_found=10,
            issues_fixed=9,
            issues_failed=1,
            remaining_issues=remaining,
        )
        
        assert result.success is False
        assert len(result.remaining_issues) == 1


class TestIntegration:
    """Integration tests for DITA issues phase."""
    
    def test_full_flow_no_vale_issues(self, tmp_path):
        """Test full flow when Vale finds no issues."""
        # Create clean files
        for i in range(3):
            f = tmp_path / f"topic{i}.adoc"
            f.write_text(f"= Topic {i}\n\n[role=\"_abstract\"]\nClean content.")
        
        files = list(tmp_path.glob("*.adoc"))
        
        memory = SessionMemory()
        mock_llm = Mock(spec=LLMClient)
        
        phase = DITAIssuesPhase(
            llm_client=mock_llm,
            memory=memory,
            project_dir=tmp_path,
        )
        
        # Mock Vale to return no issues
        phase.vale = Mock(spec=ValeRunner)
        phase.vale.run.return_value = ValeResult(
            success=True,
            issues=[],
        )
        
        result = phase.run(files)
        
        assert result.success is True
        assert result.issues_found == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
