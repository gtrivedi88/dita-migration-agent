"""
Tests for verification and manual review modules.
"""

import pytest
from pathlib import Path
from datetime import datetime

from dita_agent.core.verification import (
    Verifier,
    VerificationResult,
    ContentIntegrityReport,
)
from dita_agent.core.manual_review import (
    ManualReviewGenerator,
    ManualReviewItem,
    ManualReviewReport,
)


class TestVerifier:
    """Tests for Verifier class."""
    
    def test_verify_content_integrity_passes(self):
        """Test that similar content passes integrity check."""
        verifier = Verifier()
        
        original = """= Title
        
Some content here.

More content.
"""
        modified = """= Title
        
Some content here with a small change.

More content.
"""
        
        result = verifier.verify_content_integrity(original, modified)
        
        assert result.passed is True
        assert len(result.issues) == 0
    
    def test_verify_content_integrity_fails_major_loss(self):
        """Test that major content loss fails integrity check."""
        verifier = Verifier()
        
        original = """= Title

This is a long document with lots of content.
Line 1
Line 2
Line 3
Line 4
Line 5
Line 6
Line 7
Line 8
Line 9
Line 10
"""
        modified = "= Title\n\nShort."
        
        result = verifier.verify_content_integrity(original, modified)
        
        assert result.passed is False
        assert any("loss" in issue.lower() for issue in result.issues)
    
    def test_verify_conditionals_preserved(self):
        """Test conditional block verification passes when preserved."""
        verifier = Verifier()
        
        original = """= Title

ifdef::cloud[]
Cloud-specific content.
endif::[]

Common content.
"""
        modified = """= Title

ifdef::cloud[]
Cloud-specific content with edits.
endif::[]

Common content updated.
"""
        
        result = verifier.verify_conditionals(original, modified)
        
        assert result.passed is True
    
    def test_verify_conditionals_fails_when_removed(self):
        """Test conditional block verification fails when removed."""
        verifier = Verifier()
        
        original = """= Title

ifdef::cloud[]
Cloud content.
endif::[]
"""
        modified = """= Title

Cloud content.
"""
        
        result = verifier.verify_conditionals(original, modified)
        
        assert result.passed is False
        assert any("ifdef" in issue.lower() or "conditional" in issue.lower() 
                   for issue in result.issues)
    
    def test_verify_title_preserved_passes(self):
        """Test title verification passes when title exists."""
        verifier = Verifier()
        
        original = "= My Document Title\n\nContent"
        modified = "= My Document Title\n\n[role=\"_abstract\"]\nContent"
        
        result = verifier.verify_title_preserved(original, modified)
        
        assert result.passed is True
    
    def test_verify_title_preserved_fails(self):
        """Test title verification fails when title removed."""
        verifier = Verifier()
        
        original = "= My Document Title\n\nContent"
        modified = "Content without title"
        
        result = verifier.verify_title_preserved(original, modified)
        
        assert result.passed is False
    
    def test_verify_includes_preserved_passes(self):
        """Test include verification passes when preserved."""
        verifier = Verifier()
        
        original = """= Assembly

include::modules/topic1.adoc[leveloffset=+1]
include::modules/topic2.adoc[leveloffset=+1]
"""
        modified = """= Assembly

:_mod-docs-content-type: ASSEMBLY

include::modules/topic1.adoc[leveloffset=+1]
include::modules/topic2.adoc[leveloffset=+1]
"""
        
        result = verifier.verify_includes_preserved(original, modified)
        
        assert result.passed is True
    
    def test_verify_includes_preserved_fails(self):
        """Test include verification fails when include removed."""
        verifier = Verifier()
        
        original = """= Assembly

include::modules/topic1.adoc[leveloffset=+1]
include::modules/topic2.adoc[leveloffset=+1]
"""
        modified = """= Assembly

include::modules/topic1.adoc[leveloffset=+1]
"""
        
        result = verifier.verify_includes_preserved(original, modified)
        
        assert result.passed is False
        assert any("topic2" in issue for issue in result.issues)
    
    def test_verify_syntax_balanced_blocks(self):
        """Test syntax verification for balanced blocks."""
        verifier = Verifier()
        
        content = """= Title

[source,yaml]
----
apiVersion: v1
kind: Pod
----

Normal content.
"""
        
        result = verifier.verify_syntax(content)
        
        assert result.passed is True
    
    def test_verify_syntax_unbalanced_blocks(self):
        """Test syntax verification catches unbalanced conditionals."""
        verifier = Verifier()
        
        # Unbalanced conditional (missing endif)
        content = """= Title

ifdef::cloud[]
Cloud content here.

Missing endif.
"""
        
        result = verifier.verify_syntax(content)
        
        assert result.passed is False
        assert any("unbalanced" in issue.lower() or "conditional" in issue.lower() 
                   for issue in result.issues)
    
    def test_get_integrity_report(self, tmp_path):
        """Test generating integrity report."""
        verifier = Verifier()
        
        filepath = tmp_path / "test.adoc"
        original = "= Title\n\nOriginal content line 1\nLine 2\nLine 3"
        modified = "= Title\n\nModified content line 1\nLine 2\nLine 3\nLine 4"
        
        report = verifier.get_integrity_report(filepath, original, modified)
        
        assert report.file_path == filepath
        assert report.original_lines == 5
        assert report.modified_lines == 6
        assert report.title_preserved is True
    
    def test_conditional_balance_check(self):
        """Test conditional balance checking."""
        verifier = Verifier()
        
        balanced = """
ifdef::cloud[]
content
endif::[]

ifndef::self-managed[]
other
endif::[]
"""
        
        unbalanced = """
ifdef::cloud[]
content
missing endif
"""
        
        assert verifier._check_conditional_balance(balanced) is True
        assert verifier._check_conditional_balance(unbalanced) is False


class TestManualReviewItem:
    """Tests for ManualReviewItem dataclass."""
    
    def test_create_item(self, tmp_path):
        """Test creating a review item."""
        item = ManualReviewItem(
            filepath=tmp_path / "test.adoc",
            line=10,
            rule="DITA.ShortDescription",
            message="Missing abstract paragraph",
            reason="LLM could not generate appropriate abstract",
            severity="error",
        )
        
        assert item.line == 10
        assert item.rule == "DITA.ShortDescription"
        assert item.severity == "error"


class TestManualReviewReport:
    """Tests for ManualReviewReport class."""
    
    def test_add_items(self, tmp_path):
        """Test adding items to report."""
        report = ManualReviewReport()
        
        item1 = ManualReviewItem(
            filepath=tmp_path / "file1.adoc",
            line=5,
            rule="DITA.Rule1",
            message="Error 1",
            reason="Reason 1",
        )
        item2 = ManualReviewItem(
            filepath=tmp_path / "file2.adoc",
            line=10,
            rule="DITA.Rule2",
            message="Error 2",
            reason="Reason 2",
        )
        
        report.add_item(item1)
        report.add_item(item2)
        
        assert len(report.items) == 2
    
    def test_get_by_file(self, tmp_path):
        """Test grouping items by file."""
        report = ManualReviewReport()
        
        file1 = tmp_path / "file1.adoc"
        file2 = tmp_path / "file2.adoc"
        
        report.add_item(ManualReviewItem(
            filepath=file1, line=5, rule="Rule1", 
            message="M1", reason="R1"
        ))
        report.add_item(ManualReviewItem(
            filepath=file1, line=10, rule="Rule2",
            message="M2", reason="R2"
        ))
        report.add_item(ManualReviewItem(
            filepath=file2, line=3, rule="Rule1",
            message="M3", reason="R3"
        ))
        
        by_file = report.get_by_file()
        
        assert len(by_file) == 2
        assert len(by_file[file1]) == 2
        assert len(by_file[file2]) == 1
    
    def test_get_by_rule(self, tmp_path):
        """Test grouping items by rule."""
        report = ManualReviewReport()
        
        report.add_item(ManualReviewItem(
            filepath=tmp_path / "f1.adoc", line=1, rule="DITA.Rule1",
            message="M1", reason="R1"
        ))
        report.add_item(ManualReviewItem(
            filepath=tmp_path / "f2.adoc", line=2, rule="DITA.Rule1",
            message="M2", reason="R2"
        ))
        report.add_item(ManualReviewItem(
            filepath=tmp_path / "f3.adoc", line=3, rule="DITA.Rule2",
            message="M3", reason="R3"
        ))
        
        by_rule = report.get_by_rule()
        
        assert len(by_rule["DITA.Rule1"]) == 2
        assert len(by_rule["DITA.Rule2"]) == 1
    
    def test_count_by_severity(self, tmp_path):
        """Test counting items by severity."""
        report = ManualReviewReport()
        
        report.add_item(ManualReviewItem(
            filepath=tmp_path / "f1.adoc", line=1, rule="R1",
            message="M", reason="R", severity="error"
        ))
        report.add_item(ManualReviewItem(
            filepath=tmp_path / "f2.adoc", line=2, rule="R2",
            message="M", reason="R", severity="error"
        ))
        report.add_item(ManualReviewItem(
            filepath=tmp_path / "f3.adoc", line=3, rule="R3",
            message="M", reason="R", severity="warning"
        ))
        
        counts = report.count_by_severity()
        
        assert counts["error"] == 2
        assert counts["warning"] == 1
        assert counts["suggestion"] == 0


class TestManualReviewGenerator:
    """Tests for ManualReviewGenerator class."""
    
    def test_generate_empty_report(self, tmp_path):
        """Test generating empty report."""
        generator = ManualReviewGenerator(tmp_path, "test-session-123")
        
        output_path = generator.generate()
        
        assert output_path.exists()
        content = output_path.read_text()
        assert "Manual Review Required" in content
        assert "No issues require manual review" in content
    
    def test_generate_with_items(self, tmp_path):
        """Test generating report with items."""
        generator = ManualReviewGenerator(tmp_path, "test-session-456")
        
        generator.add_item(
            filepath=tmp_path / "modules" / "topic.adoc",
            line=10,
            rule="DITA.ShortDescription",
            message="Missing abstract paragraph",
            reason="LLM could not determine appropriate summary",
            severity="error",
        )
        
        output_path = generator.generate()
        
        assert output_path.exists()
        content = output_path.read_text()
        assert "DITA.ShortDescription" in content
        assert "Missing abstract paragraph" in content
        assert "Line 10" in content
    
    def test_has_items(self, tmp_path):
        """Test has_items method."""
        generator = ManualReviewGenerator(tmp_path, "test")
        
        assert generator.has_items() is False
        
        generator.add_item(
            filepath=tmp_path / "test.adoc",
            line=1,
            rule="Rule",
            message="Msg",
            reason="Rsn",
        )
        
        assert generator.has_items() is True
    
    def test_get_summary(self, tmp_path):
        """Test get_summary method."""
        generator = ManualReviewGenerator(tmp_path, "test")
        
        assert "No issues" in generator.get_summary()
        
        generator.add_item(
            filepath=tmp_path / "test.adoc",
            line=1, rule="Rule", message="M", reason="R", severity="error"
        )
        generator.add_item(
            filepath=tmp_path / "test2.adoc",
            line=2, rule="Rule", message="M", reason="R", severity="warning"
        )
        
        summary = generator.get_summary()
        assert "2 issues" in summary
        assert "1 errors" in summary
        assert "1 warnings" in summary
    
    def test_gitignore_updated(self, tmp_path):
        """Test that .gitignore is updated."""
        # Create a git repo
        (tmp_path / ".git").mkdir()
        
        generator = ManualReviewGenerator(tmp_path, "test")
        generator.generate()
        
        gitignore = tmp_path / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text()
            assert ".dita-agent/" in content
    
    def test_severity_icons(self, tmp_path):
        """Test severity icons in generated markdown."""
        generator = ManualReviewGenerator(tmp_path, "test")
        
        assert "🔴" == generator._get_severity_icon("error")
        assert "🟡" == generator._get_severity_icon("warning")
        assert "🔵" == generator._get_severity_icon("suggestion")
    
    def test_report_includes_resources(self, tmp_path):
        """Test that report includes helpful resources."""
        generator = ManualReviewGenerator(tmp_path, "test")
        generator.add_item(
            filepath=tmp_path / "test.adoc",
            line=1, rule="Rule", message="M", reason="R"
        )
        
        output_path = generator.generate()
        content = output_path.read_text()
        
        assert "Resources" in content
        assert "Red Hat Modular Documentation" in content
        assert "AsciiDoc" in content


class TestIntegration:
    """Integration tests for verification and manual review."""
    
    def test_verify_and_report_flow(self, tmp_path):
        """Test full flow of verification leading to manual review."""
        verifier = Verifier()
        generator = ManualReviewGenerator(tmp_path, "integration-test")
        
        # Original content with conditionals
        original = """= Title

ifdef::cloud[]
Cloud content.
endif::[]

Other content.
"""
        
        # Bad modification that removes conditional
        modified = """= Title

Cloud content.

Other content.
"""
        
        # Verify
        result = verifier.verify_content_integrity(original, modified)
        
        # If verification fails, add to manual review
        if not result.passed:
            for issue in result.issues:
                generator.add_item(
                    filepath=tmp_path / "test.adoc",
                    line=3,
                    rule="ContentIntegrity",
                    message="Content integrity check failed",
                    reason=issue,
                    severity="error",
                )
        
        # Generate report
        if generator.has_items():
            output_path = generator.generate()
            assert output_path.exists()
            content = output_path.read_text()
            assert "ContentIntegrity" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
