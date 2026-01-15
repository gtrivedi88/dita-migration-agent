"""
Tests for LLM module.

Note: These tests focus on parsing and prompt generation.
Actual API calls are mocked or skipped in unit tests.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from dita_agent.llm.client import (
    LLMClient,
    LLMResponse,
    TargetedEdit,
    InvalidResponseError,
)
from dita_agent.llm.prompts import PromptBuilder, PromptType, SYSTEM_PROMPT


class TestTargetedEdit:
    """Tests for TargetedEdit dataclass."""
    
    def test_valid_edit(self):
        """Test a valid edit."""
        edit = TargetedEdit(
            old_string="= Title\n\n.Prerequisites",
            new_string="= Title\n\n[role=\"_abstract\"]\nThis describes...\n\n.Prerequisites",
        )
        assert edit.is_valid() is True
    
    def test_invalid_empty_old_string(self):
        """Test edit with empty old_string."""
        edit = TargetedEdit(old_string="", new_string="something")
        assert edit.is_valid() is False
    
    def test_invalid_whitespace_old_string(self):
        """Test edit with whitespace-only old_string."""
        edit = TargetedEdit(old_string="   ", new_string="something")
        assert edit.is_valid() is False
    
    def test_invalid_same_strings(self):
        """Test edit where old and new are identical."""
        edit = TargetedEdit(old_string="same", new_string="same")
        assert edit.is_valid() is False
    
    def test_valid_deletion(self):
        """Test edit that deletes content (empty new_string)."""
        edit = TargetedEdit(old_string="remove this", new_string="")
        assert edit.is_valid() is True


class TestLLMClientJSONParsing:
    """Tests for JSON extraction from LLM responses."""
    
    def setup_method(self):
        """Setup for each test."""
        # Create a mock client without actually initializing the API
        with patch('openai.OpenAI'):
            self.client = LLMClient(api_key="fake_key")
    
    def test_extract_json_pure_json(self):
        """Test extracting pure JSON."""
        text = '{"old_string": "foo", "new_string": "bar"}'
        result = self.client._extract_json(text)
        
        assert result is not None
        assert result["old_string"] == "foo"
        assert result["new_string"] == "bar"
    
    def test_extract_json_markdown_block(self):
        """Test extracting JSON from markdown code block."""
        text = '''Here's the fix:
```json
{"old_string": "foo", "new_string": "bar"}
```
'''
        result = self.client._extract_json(text)
        
        assert result is not None
        assert result["old_string"] == "foo"
    
    def test_extract_json_unmarked_code_block(self):
        """Test extracting JSON from unmarked code block."""
        text = '''
```
{"old_string": "test", "new_string": "fixed"}
```
'''
        result = self.client._extract_json(text)
        
        assert result is not None
        assert result["old_string"] == "test"
    
    def test_extract_json_with_surrounding_text(self):
        """Test extracting JSON with surrounding explanation."""
        text = '''I'll fix this by adding the abstract.
        
{"old_string": "= Title", "new_string": "= Title\\n\\n[role=\\"_abstract\\"]\\nDescription."}

This adds the required short description.'''
        
        result = self.client._extract_json(text)
        
        assert result is not None
        assert "old_string" in result
    
    def test_extract_json_nested_object(self):
        """Test extracting JSON with nested objects."""
        text = '''{"content_type": "PROCEDURE", "edit": {"old_string": "foo", "new_string": "bar"}}'''
        
        result = self.client._extract_json(text)
        
        assert result is not None
        assert result["content_type"] == "PROCEDURE"
        assert result["edit"]["old_string"] == "foo"
    
    def test_extract_json_invalid(self):
        """Test that invalid JSON returns None."""
        text = "This is not JSON at all, just plain text."
        
        result = self.client._extract_json(text)
        
        assert result is None
    
    def test_extract_json_incomplete(self):
        """Test that incomplete JSON returns None."""
        text = '{"old_string": "foo", "new_string":'
        
        result = self.client._extract_json(text)
        
        assert result is None


class TestLLMClientFromConfig:
    """Tests for creating client from config."""
    
    def test_from_config_minimal(self):
        """Test creating client with minimal config."""
        with patch('openai.OpenAI'):
            config = {"api_key": "test_key"}
            client = LLMClient.from_config(config)
            
            assert client.model_name == "gemini-3-flash-preview"  # default
    
    def test_from_config_full(self):
        """Test creating client with full config."""
        with patch('openai.OpenAI'):
            config = {
                "api_key": "test_key",
                "model": "gemini-3-flash-preview",
                "base_url": "https://custom.endpoint.com",
            }
            client = LLMClient.from_config(config)
            
            assert client.model_name == "gemini-3-flash-preview"


class TestPromptBuilder:
    """Tests for prompt generation."""
    
    def test_content_type_prompt_structure(self):
        """Test content type prompt has required elements."""
        prompt = PromptBuilder.content_type_prompt(
            file_content="= Title\n\n.Procedure\n. Step 1",
            filename="topic.adoc",
        )
        
        assert "PROCEDURE" in prompt
        assert "CONCEPT" in prompt
        assert "REFERENCE" in prompt
        assert "ASSEMBLY" in prompt
        assert "SNIPPET" in prompt
        assert "topic.adoc" in prompt
        assert "old_string" in prompt
        assert "new_string" in prompt
    
    def test_dita_fix_prompt_structure(self):
        """Test DITA fix prompt has required elements."""
        prompt = PromptBuilder.dita_fix_prompt(
            filename="topic.adoc",
            line=15,
            rule_name="ShortDescription",
            error_message="Missing short description",
            context="= Title\n\n.Prerequisites",
            fix_instruction="Add [role=\"_abstract\"] paragraph",
        )
        
        assert "topic.adoc" in prompt
        assert "15" in prompt
        assert "ShortDescription" in prompt
        assert "old_string" in prompt
        assert "new_string" in prompt
        assert "ifdef" in prompt  # Should mention not to modify conditionals
    
    def test_callouts_review_prompt_structure(self):
        """Test callouts review prompt has required elements."""
        prompt = PromptBuilder.callouts_review_prompt(
            original="code <1>",
            modified="code\n1. explanation",
            filename="topic.adoc",
        )
        
        assert "ORIGINAL" in prompt
        assert "AFTER" in prompt
        assert "is_correct" in prompt
    
    def test_short_description_prompt_structure(self):
        """Test short description prompt has required elements."""
        prompt = PromptBuilder.short_description_prompt(
            filename="topic.adoc",
            line=5,
            context="= Installing the Component\n\n.Prerequisites",
            title="Installing the Component",
        )
        
        assert "[role=\"_abstract\"]" in prompt
        assert "abstract_text" in prompt
    
    def test_system_prompt_emphasizes_targeted_edits(self):
        """Test system prompt emphasizes targeted edits."""
        prompt = PromptBuilder.get_system_prompt()
        
        assert "NEVER rewrite" in prompt
        assert "targeted edit" in prompt.lower() or "old_string" in prompt
        assert "ifdef" in prompt or "conditional" in prompt.lower()
    
    def test_get_prompt_content_type(self):
        """Test getting prompt by type."""
        prompt = PromptBuilder.get_prompt(
            PromptType.CONTENT_TYPE,
            file_content="content",
            filename="test.adoc",
        )
        
        assert "content" in prompt
        assert "test.adoc" in prompt
    
    def test_get_prompt_unknown_type(self):
        """Test that unknown prompt type raises error."""
        with pytest.raises(ValueError):
            PromptBuilder.get_prompt("unknown_type")


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""
    
    def test_success_response(self):
        """Test a successful response."""
        response = LLMResponse(
            success=True,
            content='{"old_string": "a", "new_string": "b"}',
            parsed={"old_string": "a", "new_string": "b"},
            tokens_used=100,
        )
        
        assert response.success is True
        assert response.error is None
        assert response.tokens_used == 100
    
    def test_failure_response(self):
        """Test a failed response."""
        response = LLMResponse(
            success=False,
            error="API timeout",
            retry_count=3,
        )
        
        assert response.success is False
        assert response.error == "API timeout"
        assert response.content is None


class TestLLMClientGetTargetedEdit:
    """Tests for get_targeted_edit method."""
    
    def setup_method(self):
        """Setup for each test."""
        with patch('openai.OpenAI'):
            self.client = LLMClient(api_key="fake_key")
    
    def test_get_targeted_edit_success(self):
        """Test successful targeted edit extraction."""
        # Mock the generate method
        self.client.generate = Mock(return_value=LLMResponse(
            success=True,
            content='{"old_string": "foo", "new_string": "bar"}',
            parsed={"old_string": "foo", "new_string": "bar"},
        ))
        
        edit, error = self.client.get_targeted_edit("fix this")
        
        assert error is None
        assert edit is not None
        assert edit.old_string == "foo"
        assert edit.new_string == "bar"
    
    def test_get_targeted_edit_nested_structure(self):
        """Test extracting edit from nested JSON structure."""
        self.client.generate = Mock(return_value=LLMResponse(
            success=True,
            content='{"content_type": "PROCEDURE", "edit": {"old_string": "a", "new_string": "b"}}',
            parsed={"content_type": "PROCEDURE", "edit": {"old_string": "a", "new_string": "b"}},
        ))
        
        edit, error = self.client.get_targeted_edit("fix this")
        
        assert error is None
        assert edit is not None
        assert edit.old_string == "a"
    
    def test_get_targeted_edit_api_failure(self):
        """Test handling of API failure."""
        self.client.generate = Mock(return_value=LLMResponse(
            success=False,
            error="API error",
        ))
        
        edit, error = self.client.get_targeted_edit("fix this")
        
        assert edit is None
        assert error == "API error"
    
    def test_get_targeted_edit_invalid_response(self):
        """Test handling of invalid response format."""
        self.client.generate = Mock(return_value=LLMResponse(
            success=True,
            content='{"invalid": "structure"}',
            parsed={"invalid": "structure"},
        ))
        
        edit, error = self.client.get_targeted_edit("fix this")
        
        assert edit is None
        assert error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
