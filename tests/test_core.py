"""
Tests for core modules: scope and memory.
"""

import json
import pytest
from pathlib import Path

from dita_agent.core.scope import ScopeResolver, ScopeResult
from dita_agent.core.memory import SessionMemory, Phase, FixStatus


class TestScopeResolver:
    """Tests for scope resolution."""
    
    def test_resolve_project_finds_all_adoc_files(self, tmp_path):
        """Test finding all AsciiDoc files in a project."""
        # Create test structure
        (tmp_path / "modules").mkdir()
        (tmp_path / "assemblies").mkdir()
        
        (tmp_path / "modules" / "topic1.adoc").write_text("= Topic 1")
        (tmp_path / "modules" / "topic2.adoc").write_text("= Topic 2")
        (tmp_path / "assemblies" / "master.adoc").write_text("= Master")
        (tmp_path / "README.md").write_text("Not an adoc file")
        
        resolver = ScopeResolver(tmp_path)
        result = resolver.resolve()
        
        assert len(result.files) == 3
        assert result.errors == []
    
    def test_resolve_project_skips_dita_agent_dir(self, tmp_path):
        """Test that .dita-agent directory is skipped."""
        (tmp_path / "topic.adoc").write_text("= Topic")
        (tmp_path / ".dita-agent" / "backups").mkdir(parents=True)
        (tmp_path / ".dita-agent" / "backups" / "backup.adoc").write_text("Backup")
        
        resolver = ScopeResolver(tmp_path)
        result = resolver.resolve()
        
        assert len(result.files) == 1
        assert "backup.adoc" not in str(result.files[0])
    
    def test_resolve_project_skips_hidden_dirs(self, tmp_path):
        """Test that hidden directories are skipped."""
        (tmp_path / "topic.adoc").write_text("= Topic")
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "hidden.adoc").write_text("Hidden")
        
        resolver = ScopeResolver(tmp_path)
        result = resolver.resolve()
        
        assert len(result.files) == 1
    
    def test_resolve_project_with_limit(self, tmp_path):
        """Test limiting the number of files."""
        for i in range(10):
            (tmp_path / f"topic{i}.adoc").write_text(f"= Topic {i}")
        
        resolver = ScopeResolver(tmp_path)
        result = resolver.resolve(limit=3)
        
        assert len(result.files) == 3
    
    def test_resolve_assembly_finds_includes(self, tmp_path):
        """Test resolving an assembly with includes."""
        # Create assembly with includes
        # Note: include paths are relative to the assembly file's location
        assembly_content = """= Assembly
        
include::../modules/topic1.adoc[]

include::../modules/topic2.adoc[]
"""
        (tmp_path / "assemblies").mkdir()
        (tmp_path / "modules").mkdir()
        
        (tmp_path / "assemblies" / "master.adoc").write_text(assembly_content)
        (tmp_path / "modules" / "topic1.adoc").write_text("= Topic 1")
        (tmp_path / "modules" / "topic2.adoc").write_text("= Topic 2")
        
        resolver = ScopeResolver(tmp_path)
        result = resolver.resolve(assembly=Path("assemblies/master.adoc"))
        
        assert len(result.files) == 3
        assert result.entry_point is not None
        assert "master.adoc" in str(result.entry_point)
    
    def test_resolve_assembly_handles_nested_includes(self, tmp_path):
        """Test resolving nested includes."""
        # Assembly includes topic1, topic1 includes snippet
        (tmp_path / "assemblies").mkdir()
        (tmp_path / "modules").mkdir()
        (tmp_path / "snippets").mkdir()
        
        assembly = tmp_path / "assemblies" / "master.adoc"
        topic1 = tmp_path / "modules" / "topic1.adoc"
        snippet = tmp_path / "snippets" / "snippet.adoc"
        
        assembly.write_text("= Assembly\n\ninclude::../modules/topic1.adoc[]")
        topic1.write_text("= Topic 1\n\ninclude::../snippets/snippet.adoc[]")
        snippet.write_text("This is a snippet.")
        
        resolver = ScopeResolver(tmp_path)
        result = resolver.resolve(assembly=assembly)
        
        assert len(result.files) == 3
    
    def test_resolve_assembly_handles_circular_includes(self, tmp_path):
        """Test that circular includes don't cause infinite loops."""
        (tmp_path / "file1.adoc").write_text("include::file2.adoc[]")
        (tmp_path / "file2.adoc").write_text("include::file1.adoc[]")
        
        resolver = ScopeResolver(tmp_path)
        result = resolver.resolve(assembly=tmp_path / "file1.adoc")
        
        # Should have both files, but not loop forever
        assert len(result.files) == 2
    
    def test_resolve_assembly_missing_file(self, tmp_path):
        """Test resolving a non-existent assembly."""
        resolver = ScopeResolver(tmp_path)
        result = resolver.resolve(assembly=Path("nonexistent.adoc"))
        
        assert len(result.files) == 0
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].lower()
    
    def test_resolve_topics(self, tmp_path):
        """Test resolving specific topics."""
        (tmp_path / "topic1.adoc").write_text("= Topic 1")
        (tmp_path / "topic2.adoc").write_text("= Topic 2")
        (tmp_path / "topic3.adoc").write_text("= Topic 3")
        
        resolver = ScopeResolver(tmp_path)
        result = resolver.resolve(topics=[
            tmp_path / "topic1.adoc",
            tmp_path / "topic2.adoc",
        ])
        
        assert len(result.files) == 2
    
    def test_resolve_topics_missing_file(self, tmp_path):
        """Test resolving topics with a missing file."""
        (tmp_path / "topic1.adoc").write_text("= Topic 1")
        
        resolver = ScopeResolver(tmp_path)
        result = resolver.resolve(topics=[
            tmp_path / "topic1.adoc",
            tmp_path / "nonexistent.adoc",
        ])
        
        assert len(result.files) == 1
        assert len(result.errors) == 1
    
    def test_include_tree_populated(self, tmp_path):
        """Test that include tree is correctly populated."""
        (tmp_path / "assembly.adoc").write_text("include::topic.adoc[]")
        (tmp_path / "topic.adoc").write_text("= Topic")
        
        resolver = ScopeResolver(tmp_path)
        result = resolver.resolve(assembly=tmp_path / "assembly.adoc")
        
        assert len(result.include_tree) > 0
    
    def test_handles_attribute_includes(self, tmp_path):
        """Test handling includes with attributes."""
        # Includes with attributes like {snippets-dir} are tricky
        (tmp_path / "snippets").mkdir()
        (tmp_path / "assembly.adoc").write_text(
            "include::{snippets-dir}/snippet.adoc[]"
        )
        (tmp_path / "snippets" / "snippet.adoc").write_text("Snippet content")
        
        resolver = ScopeResolver(tmp_path)
        result = resolver.resolve(assembly=tmp_path / "assembly.adoc")
        
        # Should find the assembly at minimum
        assert len(result.files) >= 1


class TestSessionMemory:
    """Tests for session memory."""
    
    def test_session_id_generated(self):
        """Test that session ID is auto-generated."""
        memory = SessionMemory()
        
        assert memory.session_id is not None
        assert len(memory.session_id) > 0
    
    def test_record_scope(self, tmp_path):
        """Test recording scope information."""
        memory = SessionMemory()
        
        files = [tmp_path / "file1.adoc", tmp_path / "file2.adoc"]
        memory.record_scope("assembly", files, tmp_path / "master.adoc")
        
        assert memory.scope_type == "assembly"
        assert len(memory.files_in_scope) == 2
        assert memory.entry_point is not None
    
    def test_phase_tracking(self):
        """Test phase start and end tracking."""
        memory = SessionMemory()
        
        # Start phase
        phase_id = memory.start_phase(Phase.CONTENT_TYPE)
        assert phase_id == "phase1_content_type"
        assert phase_id in memory.phase_results
        assert "start_time" in memory.phase_results[phase_id]
        
        # End phase
        memory.end_phase(Phase.CONTENT_TYPE, 10.5)
        assert "end_time" in memory.phase_results[phase_id]
        assert memory.phase_results[phase_id]["duration_seconds"] == 10.5
    
    def test_record_fix_success(self, tmp_path):
        """Test recording a successful fix."""
        memory = SessionMemory()
        memory.start_phase(Phase.CONTENT_TYPE)
        
        memory.record_fix(
            filepath=tmp_path / "topic.adoc",
            phase=Phase.CONTENT_TYPE,
            rule="ContentType",
            status=FixStatus.SUCCESS,
            llm_used=True,
            tokens_used=150,
        )
        
        assert len(memory.fix_attempts) == 1
        assert memory.total_fixes_applied == 1
        assert memory.total_llm_calls == 1
        assert memory.total_tokens_used == 150
    
    def test_record_fix_failure(self, tmp_path):
        """Test recording a failed fix."""
        memory = SessionMemory()
        memory.start_phase(Phase.DITA_ISSUES)
        
        memory.record_fix(
            filepath=tmp_path / "topic.adoc",
            phase=Phase.DITA_ISSUES,
            rule="ShortDescription",
            status=FixStatus.FAILED,
            error_message="LLM returned invalid JSON",
        )
        
        assert memory.total_fixes_failed == 1
        assert memory.fix_attempts[0]["error_message"] == "LLM returned invalid JSON"
    
    def test_record_manual_review(self, tmp_path):
        """Test recording a manual review item."""
        memory = SessionMemory()
        
        memory.record_manual_review(
            filepath=tmp_path / "topic.adoc",
            rule="NestedSection",
            line=45,
            message="DITA does not allow nested sections",
            reason="Requires creating new files",
        )
        
        assert len(memory.manual_review_files) == 1
        assert memory.manual_review_files[0]["rule"] == "NestedSection"
    
    def test_calculate_cost(self):
        """Test cost calculation."""
        memory = SessionMemory()
        memory.total_tokens_used = 10000
        
        memory.calculate_cost(cost_per_1k_tokens=0.001)
        
        assert memory.estimated_cost == pytest.approx(0.01)
    
    def test_get_summary(self, tmp_path):
        """Test getting session summary."""
        memory = SessionMemory()
        memory.record_scope("project", [tmp_path / "file.adoc"])
        memory.start_phase(Phase.CONTENT_TYPE)
        memory.record_fix(
            tmp_path / "file.adoc",
            Phase.CONTENT_TYPE,
            "ContentType",
            FixStatus.SUCCESS,
            llm_used=True,
            tokens_used=100,
        )
        memory.finalize()
        
        summary = memory.get_summary()
        
        assert summary["scope_type"] == "project"
        assert summary["files_in_scope"] == 1
        assert summary["total_fixes_applied"] == 1
        assert summary["total_llm_calls"] == 1
    
    def test_save_and_load(self, tmp_path):
        """Test saving and loading session memory."""
        # Create and populate memory
        memory = SessionMemory()
        memory.record_scope("assembly", [tmp_path / "file.adoc"])
        memory.start_phase(Phase.CONTENT_TYPE)
        memory.record_fix(
            tmp_path / "file.adoc",
            Phase.CONTENT_TYPE,
            "ContentType",
            FixStatus.SUCCESS,
        )
        memory.finalize()
        
        # Save
        log_file = memory.save(tmp_path)
        assert log_file.exists()
        
        # Load
        loaded = SessionMemory.load(log_file)
        
        assert loaded is not None
        assert loaded.session_id == memory.session_id
        assert loaded.total_fixes_applied == 1
    
    def test_duration_calculation(self):
        """Test duration calculation in summary."""
        memory = SessionMemory()
        memory.start_time = "2026-01-15T10:00:00"
        memory.end_time = "2026-01-15T10:05:30"
        
        duration = memory._calculate_duration()
        
        assert "5m" in duration
    
    def test_duration_in_progress(self):
        """Test duration when session is in progress."""
        memory = SessionMemory()
        memory.end_time = None
        
        duration = memory._calculate_duration()
        
        assert duration == "In progress"
    
    def test_multiple_phases(self):
        """Test tracking multiple phases."""
        memory = SessionMemory()
        
        # Phase 1
        memory.start_phase(Phase.CONTENT_TYPE)
        memory.end_phase(Phase.CONTENT_TYPE, 5.0)
        
        # Phase 2
        memory.start_phase(Phase.CALLOUTS)
        memory.end_phase(Phase.CALLOUTS, 3.0)
        
        # Phase 3
        memory.start_phase(Phase.DITA_ISSUES)
        memory.end_phase(Phase.DITA_ISSUES, 10.0)
        
        assert len(memory.phase_results) == 3
        assert memory.phase_results["phase1_content_type"]["duration_seconds"] == 5.0
        assert memory.phase_results["phase2_callouts"]["duration_seconds"] == 3.0
        assert memory.phase_results["phase3_dita_issues"]["duration_seconds"] == 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
