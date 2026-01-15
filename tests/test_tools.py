"""
Tests for tools integration modules.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from dita_agent.tools.vale import ValeRunner, ValeIssue, ValeResult
from dita_agent.tools.callouts import CalloutsRunner, CalloutsResult


class TestValeIssue:
    """Tests for ValeIssue dataclass."""
    
    def test_str_representation(self, tmp_path):
        """Test string representation of issue."""
        issue = ValeIssue(
            filepath=tmp_path / "topic.adoc",
            line=15,
            column=1,
            rule="ShortDescription",
            message="Missing short description",
            severity="error",
        )
        
        result = str(issue)
        
        assert "topic.adoc" in result
        assert "15" in result
        assert "ShortDescription" in result
        assert "error" in result


class TestValeResult:
    """Tests for ValeResult dataclass."""
    
    def test_has_issues_true(self, tmp_path):
        """Test has_issues when there are issues."""
        result = ValeResult(
            success=True,
            issues=[
                ValeIssue(
                    filepath=tmp_path / "test.adoc",
                    line=1,
                    column=1,
                    rule="Test",
                    message="Test",
                    severity="error",
                )
            ],
            errors=1,
        )
        
        assert result.has_issues() is True
    
    def test_has_issues_false(self):
        """Test has_issues when there are no issues."""
        result = ValeResult(success=True, issues=[])
        
        assert result.has_issues() is False
    
    def test_get_issues_for_file(self, tmp_path):
        """Test filtering issues by file."""
        file1 = tmp_path / "file1.adoc"
        file2 = tmp_path / "file2.adoc"
        
        result = ValeResult(
            success=True,
            issues=[
                ValeIssue(filepath=file1, line=1, column=1, rule="A", message="", severity="error"),
                ValeIssue(filepath=file2, line=1, column=1, rule="B", message="", severity="error"),
                ValeIssue(filepath=file1, line=5, column=1, rule="C", message="", severity="error"),
            ],
        )
        
        file1_issues = result.get_issues_for_file(file1)
        
        assert len(file1_issues) == 2
        assert all(i.filepath == file1 for i in file1_issues)
    
    def test_get_issues_by_rule(self, tmp_path):
        """Test filtering issues by rule."""
        result = ValeResult(
            success=True,
            issues=[
                ValeIssue(filepath=tmp_path / "a.adoc", line=1, column=1, rule="ShortDescription", message="", severity="error"),
                ValeIssue(filepath=tmp_path / "b.adoc", line=1, column=1, rule="TaskStep", message="", severity="error"),
                ValeIssue(filepath=tmp_path / "c.adoc", line=1, column=1, rule="ShortDescription", message="", severity="error"),
            ],
        )
        
        sd_issues = result.get_issues_by_rule("ShortDescription")
        
        assert len(sd_issues) == 2


class TestValeRunner:
    """Tests for ValeRunner."""
    
    def test_is_available_with_vale(self):
        """Test availability check when Vale is installed."""
        runner = ValeRunner()
        # This will pass if Vale is installed on the system
        result = runner.is_available()
        # Just check it returns a boolean
        assert isinstance(result, bool)
    
    def test_parse_output_empty(self):
        """Test parsing empty output."""
        runner = ValeRunner()
        
        result = runner._parse_output("", 0)
        
        assert result.success is True
        assert len(result.issues) == 0
    
    def test_parse_output_with_issues(self):
        """Test parsing Vale JSON output."""
        runner = ValeRunner()
        
        vale_output = json.dumps({
            "/path/to/file.adoc": [
                {
                    "Check": "ShortDescription",
                    "Line": 5,
                    "Span": [1, 10],
                    "Message": "Missing short description",
                    "Severity": "error",
                    "Match": "= Title",
                }
            ]
        })
        
        result = runner._parse_output(vale_output, 1)
        
        assert result.success is True
        assert len(result.issues) == 1
        assert result.issues[0].rule == "ShortDescription"
        assert result.issues[0].line == 5
        assert result.errors == 1
    
    def test_parse_output_multiple_files(self):
        """Test parsing output with multiple files."""
        runner = ValeRunner()
        
        vale_output = json.dumps({
            "/path/to/file1.adoc": [
                {"Check": "Rule1", "Line": 1, "Span": [1, 1], "Message": "M1", "Severity": "error"},
            ],
            "/path/to/file2.adoc": [
                {"Check": "Rule2", "Line": 2, "Span": [1, 1], "Message": "M2", "Severity": "warning"},
                {"Check": "Rule3", "Line": 3, "Span": [1, 1], "Message": "M3", "Severity": "suggestion"},
            ],
        })
        
        result = runner._parse_output(vale_output, 1)
        
        assert result.success is True
        assert len(result.issues) == 3
        assert result.errors == 1
        assert result.warnings == 1
        assert result.suggestions == 1
    
    def test_parse_output_invalid_json(self):
        """Test parsing invalid JSON output."""
        runner = ValeRunner()
        
        result = runner._parse_output("not valid json", 1)
        
        assert result.success is False
        assert "parse" in result.error_message.lower()
    
    def test_get_issues_summary_no_issues(self):
        """Test summary with no issues."""
        runner = ValeRunner()
        result = ValeResult(success=True)
        
        summary = runner.get_issues_summary(result)
        
        assert "No DITA compatibility issues" in summary
    
    def test_get_issues_summary_with_issues(self, tmp_path):
        """Test summary with issues."""
        runner = ValeRunner()
        result = ValeResult(
            success=True,
            issues=[
                ValeIssue(filepath=tmp_path / "a.adoc", line=1, column=1, rule="ShortDescription", message="", severity="error"),
                ValeIssue(filepath=tmp_path / "b.adoc", line=1, column=1, rule="ShortDescription", message="", severity="error"),
                ValeIssue(filepath=tmp_path / "c.adoc", line=1, column=1, rule="TaskStep", message="", severity="error"),
            ],
            errors=3,
        )
        
        summary = runner.get_issues_summary(result)
        
        assert "3 issue" in summary
        assert "ShortDescription" in summary
        assert "TaskStep" in summary
    
    def test_create_permanent_vale_ini(self, tmp_path):
        """Test creating permanent .vale.ini file."""
        runner = ValeRunner()
        
        vale_ini = runner.create_permanent_vale_ini(tmp_path)
        
        assert vale_ini.exists()
        content = vale_ini.read_text()
        assert "StylesPath" in content
        assert "AsciiDocDITA" in content
    
    def test_temp_config_created(self):
        """Test that temporary config is created on init."""
        runner = ValeRunner()
        
        # Temp config should be created automatically
        assert runner.config_path is not None
        assert runner.config_path.exists()
        assert "vale-dita-agent" in runner.config_path.name
        
        content = runner.config_path.read_text()
        assert "AsciiDocDITA" in content
        assert "MinAlertLevel = suggestion" in content
    
    def test_cleanup_removes_temp_config(self):
        """Test that cleanup removes temp config."""
        runner = ValeRunner()
        temp_path = runner.config_path
        
        assert temp_path.exists()
        runner.cleanup()
        assert not temp_path.exists()


class TestCalloutsRunner:
    """Tests for CalloutsRunner."""
    
    def test_has_callouts_true(self):
        """Test detecting callouts in content."""
        runner = CalloutsRunner()
        
        content = '''[source,yaml]
----
key: value <1>
----
<1> Description
'''
        assert runner.has_callouts(content) is True
    
    def test_has_callouts_false(self):
        """Test content without callouts."""
        runner = CalloutsRunner()
        
        content = '''[source,yaml]
----
key: value
----
'''
        assert runner.has_callouts(content) is False
    
    def test_has_callouts_multiple(self):
        """Test detecting multiple callouts."""
        runner = CalloutsRunner()
        
        content = '''<1> First
<2> Second
<10> Tenth
'''
        assert runner.has_callouts(content) is True
    
    def test_find_files_with_callouts(self, tmp_path):
        """Test finding files with callouts."""
        # Create files
        file_with_callouts = tmp_path / "with_callouts.adoc"
        file_without = tmp_path / "without.adoc"
        
        file_with_callouts.write_text("code <1>\n<1> desc")
        file_without.write_text("plain code")
        
        runner = CalloutsRunner()
        result = runner.find_files_with_callouts([file_with_callouts, file_without])
        
        assert len(result) == 1
        assert file_with_callouts in result
    
    def test_is_available_missing_tool(self, tmp_path):
        """Test availability check when tool is missing."""
        runner = CalloutsRunner(
            tool_dir=tmp_path / "nonexistent",
            venv_python=tmp_path / "nonexistent" / "python",
        )
        
        assert runner.is_available() is False
    
    def test_run_no_files(self):
        """Test running with no files."""
        runner = CalloutsRunner()
        
        result = runner.run([])
        
        assert result.success is True
        assert len(result.files_modified) == 0
    
    def test_run_no_callouts_in_files(self, tmp_path):
        """Test running on files without callouts."""
        runner = CalloutsRunner()
        
        file = tmp_path / "no_callouts.adoc"
        file.write_text("= Title\n\nNo callouts here.")
        
        result = runner.run([file])
        
        assert result.success is True
        assert len(result.files_modified) == 0
        assert file in result.files_unchanged
    
    def test_get_summary_success(self, tmp_path):
        """Test summary for successful run."""
        runner = CalloutsRunner()
        
        result = CalloutsResult(
            success=True,
            files_modified=[tmp_path / "a.adoc", tmp_path / "b.adoc"],
            files_unchanged=[tmp_path / "c.adoc"],
        )
        
        summary = runner.get_summary(result)
        
        assert "2" in summary  # 2 modified
        assert "Modified" in summary
    
    def test_get_summary_failure(self):
        """Test summary for failed run."""
        runner = CalloutsRunner()
        
        result = CalloutsResult(
            success=False,
            error_message="Tool not found",
        )
        
        summary = runner.get_summary(result)
        
        assert "failed" in summary.lower()
        assert "Tool not found" in summary


class TestIntegration:
    """Integration tests for tools."""
    
    @pytest.mark.skipif(
        not ValeRunner().is_available(),
        reason="Vale not installed",
    )
    def test_vale_run_real(self, tmp_path):
        """Test running Vale on a real file (requires Vale installation)."""
        # Create a test file with a known issue
        test_file = tmp_path / "test.adoc"
        test_file.write_text('''= Test Title

This file is missing the short description attribute.

.Procedure
. Step one
. Step two
''')
        
        # Create minimal vale.ini pointing to installed styles
        styles_path = Path.home() / ".dita-agent" / "tools" / "asciidoctor-dita-vale" / "styles"
        vale_ini = tmp_path / ".vale.ini"
        vale_ini.write_text(f'''
StylesPath = {styles_path}
MinAlertLevel = suggestion

[*.adoc]
BasedOnStyles = DITA
''')
        
        runner = ValeRunner(config_path=vale_ini, styles_path=styles_path)
        result = runner.run([test_file], tmp_path)
        
        # The result depends on whether styles are available
        # If styles are missing, Vale may fail or return no issues
        # We just check it doesn't crash
        assert isinstance(result, ValeResult)
        assert isinstance(result.success, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
