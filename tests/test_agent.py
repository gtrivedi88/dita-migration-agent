"""
Tests for the main DITA Migration Agent orchestrator.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from dita_agent.agent import DITAAgent, AgentResult
from dita_agent.llm.client import LLMClient, LLMResponse
from dita_agent.phases.content_type import PhaseResult as ContentTypeResult
from dita_agent.phases.callouts import CalloutsPhaseResult
from dita_agent.phases.dita_issues import DITAIssuesPhaseResult


class TestAgentResult:
    """Tests for AgentResult dataclass."""
    
    def test_success_result(self):
        """Test creating a successful result."""
        result = AgentResult(
            success=True,
            files_processed=10,
            issues_fixed=25,
            issues_remaining=0,
            total_tokens=5000,
            duration_seconds=30.5,
        )
        
        assert result.success is True
        assert result.files_processed == 10
        assert result.issues_fixed == 25
    
    def test_partial_result(self, tmp_path):
        """Test creating a partial success result."""
        result = AgentResult(
            success=False,
            files_processed=10,
            issues_fixed=20,
            issues_remaining=5,
            total_tokens=8000,
            duration_seconds=45.0,
            manual_review_path=tmp_path / ".dita-agent" / "MANUAL_REVIEW.md",
        )
        
        assert result.success is False
        assert result.issues_remaining == 5
        assert result.manual_review_path is not None


class TestDITAAgent:
    """Tests for DITAAgent class."""
    
    def create_mock_config(self, api_key: str = "test-key"):
        """Create a mock configuration."""
        return {
            "api_key": api_key,
            "model": "gemini-3-flash-preview",
        }
    
    def test_init(self, tmp_path):
        """Test agent initialization."""
        config = self.create_mock_config()
        agent = DITAAgent(
            config=config,
            project_dir=tmp_path,
        )
        
        assert agent.project_dir == tmp_path
        assert agent.dry_run is False
    
    def test_init_with_assembly(self, tmp_path):
        """Test agent initialization with assembly."""
        config = self.create_mock_config()
        assembly_path = tmp_path / "assemblies" / "test.adoc"
        
        agent = DITAAgent(
            config=config,
            project_dir=tmp_path,
            assembly=assembly_path,
        )
        
        assert agent.assembly == assembly_path
    
    def test_init_with_topics(self, tmp_path):
        """Test agent initialization with specific topics."""
        config = self.create_mock_config()
        topics = [
            tmp_path / "modules" / "topic1.adoc",
            tmp_path / "modules" / "topic2.adoc",
        ]
        
        agent = DITAAgent(
            config=config,
            project_dir=tmp_path,
            topics=topics,
        )
        
        assert agent.topics == topics
    
    def test_dry_run_no_api_key(self, tmp_path):
        """Test that dry run works without API key."""
        config = {"api_key": "", "model": "gemini-3-flash-preview"}
        
        # Create some test files
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()
        (modules_dir / "topic.adoc").write_text(":_mod-docs-content-type: CONCEPT\n\n= Title\n\nContent")
        
        agent = DITAAgent(
            config=config,
            project_dir=tmp_path,
            dry_run=True,
        )
        
        # In dry run mode, agent should work even without API key
        # (it won't make actual LLM calls)
        result = agent.run()
        
        # Should complete (may have warnings about API key, but won't fail)
        assert result is not None
    
    def test_resolve_scope_project(self, tmp_path):
        """Test scope resolution for entire project."""
        # Create test structure
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()
        (modules_dir / "topic1.adoc").write_text("= Topic 1")
        (modules_dir / "topic2.adoc").write_text("= Topic 2")
        
        config = self.create_mock_config()
        agent = DITAAgent(
            config=config,
            project_dir=tmp_path,
        )
        
        files = agent._resolve_scope()
        
        assert len(files) >= 2
    
    def test_resolve_scope_with_limit(self, tmp_path):
        """Test scope resolution with file limit."""
        # Create test structure
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()
        for i in range(10):
            (modules_dir / f"topic{i}.adoc").write_text(f"= Topic {i}")
        
        config = self.create_mock_config()
        agent = DITAAgent(
            config=config,
            project_dir=tmp_path,
            limit=3,
        )
        
        files = agent._resolve_scope()
        
        assert len(files) <= 3
    
    def test_resolve_scope_specific_topics(self, tmp_path):
        """Test scope resolution with specific topics."""
        # Create test structure
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()
        topic1 = modules_dir / "topic1.adoc"
        topic2 = modules_dir / "topic2.adoc"
        topic1.write_text("= Topic 1")
        topic2.write_text("= Topic 2")
        
        config = self.create_mock_config()
        agent = DITAAgent(
            config=config,
            project_dir=tmp_path,
            topics=[topic1, topic2],
        )
        
        files = agent._resolve_scope()
        
        assert topic1 in files
        assert topic2 in files


class TestAgentIntegration:
    """Integration tests for the agent."""
    
    def test_run_empty_project(self, tmp_path):
        """Test running agent on empty project."""
        config = {"api_key": "test", "model": "gemini-3-flash-preview"}
        
        agent = DITAAgent(
            config=config,
            project_dir=tmp_path,
            dry_run=True,
        )
        
        result = agent.run()
        
        assert result.success is True
        assert result.files_processed == 0
    
    def test_run_with_already_compliant_files(self, tmp_path):
        """Test running agent on already compliant files."""
        # Create compliant files
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()
        
        compliant_content = """:_mod-docs-content-type: CONCEPT

= Understanding the Topic

[role="_abstract"]
This topic explains the concept.

The concept is important because it provides value.
"""
        (modules_dir / "topic.adoc").write_text(compliant_content)
        
        config = {"api_key": "test", "model": "gemini-3-flash-preview"}
        
        agent = DITAAgent(
            config=config,
            project_dir=tmp_path,
            dry_run=True,
        )
        
        result = agent.run()
        
        # Should process files but not need to fix much
        assert result is not None
        assert result.files_processed >= 1


class TestPhaseSummaryPrinting:
    """Tests for phase summary output."""
    
    def test_print_phase1_summary(self, tmp_path, capsys):
        """Test Phase 1 summary printing."""
        config = {"api_key": "test", "model": "test"}
        agent = DITAAgent(config=config, project_dir=tmp_path)
        
        result = ContentTypeResult(
            success=True,
            files_processed=10,
            files_fixed=5,
            files_skipped=4,
            files_failed=1,
            total_tokens=500,
        )
        
        agent._print_phase_summary("Phase 1", result)
        # Should not raise any errors
    
    def test_print_phase2_summary(self, tmp_path):
        """Test Phase 2 summary printing."""
        config = {"api_key": "test", "model": "test"}
        agent = DITAAgent(config=config, project_dir=tmp_path)
        
        result = CalloutsPhaseResult(
            success=True,
            files_processed=10,
            files_fixed_by_tool=3,
            files_fixed_by_llm=2,
            files_skipped=4,
            files_failed=1,
            total_tokens=300,
        )
        
        agent._print_phase_summary("Phase 2", result)
        # Should not raise any errors
    
    def test_print_phase3_summary(self, tmp_path):
        """Test Phase 3 summary printing."""
        config = {"api_key": "test", "model": "test"}
        agent = DITAAgent(config=config, project_dir=tmp_path)
        
        result = DITAIssuesPhaseResult(
            success=True,
            files_processed=10,
            issues_found=15,
            issues_fixed=12,
            issues_failed=3,
            total_tokens=1000,
        )
        
        agent._print_phase_summary("Phase 3", result)
        # Should not raise any errors


class TestAgentConfiguration:
    """Tests for agent configuration handling."""
    
    def test_missing_api_key_error(self, tmp_path):
        """Test that missing API key returns error (non-dry-run)."""
        # Create a test file so there's something to process
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()
        (modules_dir / "topic.adoc").write_text("= Title\n\nContent")
        
        config = {"api_key": "", "model": "gemini-3-flash-preview"}
        
        agent = DITAAgent(
            config=config,
            project_dir=tmp_path,
            dry_run=False,  # Not dry run
        )
        
        result = agent.run()
        
        # Should fail due to missing API key
        assert result.success is False
    
    def test_custom_model_config(self, tmp_path):
        """Test that custom model configuration is used."""
        config = {
            "api_key": "test-key",
            "model": "gemini-1.5-pro",
        }
        
        agent = DITAAgent(
            config=config,
            project_dir=tmp_path,
        )
        
        assert agent.config["model"] == "gemini-1.5-pro"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
