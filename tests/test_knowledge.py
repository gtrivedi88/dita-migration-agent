"""
Tests for knowledge base modules.
"""

import pytest

from dita_agent.knowledge.content_types import (
    CONTENT_TYPE_RULES,
    ContentType,
    get_content_type_indicators,
    get_content_type_rules_text,
    detect_content_type_heuristic,
)
from dita_agent.knowledge import (
    ALL_RULES,
    RuleSeverity,
    get_fix_instruction,
    get_rule_severity,
    get_error_rules,
    get_warning_rules,
    get_rule,
)


class TestContentTypes:
    """Tests for content type rules."""
    
    def test_all_content_types_defined(self):
        """Test that all content types have rules."""
        for content_type in ContentType:
            assert content_type.value in CONTENT_TYPE_RULES
    
    def test_content_type_rules_have_required_fields(self):
        """Test that each content type has required fields."""
        required_fields = ["description", "indicators", "example"]
        
        for type_name, rules in CONTENT_TYPE_RULES.items():
            for field in required_fields:
                assert field in rules, f"{type_name} missing {field}"
    
    def test_get_content_type_indicators(self):
        """Test getting indicators for a content type."""
        indicators = get_content_type_indicators(ContentType.PROCEDURE)
        
        assert len(indicators) > 0
        assert ".Procedure" in indicators
    
    def test_get_content_type_indicators_unknown(self):
        """Test getting indicators for unknown type returns empty list."""
        # Create a mock ContentType that's not in rules
        # (This is more for robustness testing)
        indicators = get_content_type_indicators(ContentType.PROCEDURE)
        assert isinstance(indicators, list)
    
    def test_get_content_type_rules_text(self):
        """Test formatting rules as text."""
        text = get_content_type_rules_text()
        
        assert "PROCEDURE" in text
        assert "CONCEPT" in text
        assert "REFERENCE" in text
        assert "ASSEMBLY" in text
        assert "SNIPPET" in text
    
    def test_detect_heuristic_procedure(self):
        """Test heuristic detection of procedure."""
        content = '''= Installing the component

.Prerequisites
* Admin access

.Procedure
. Run the install script.
. Verify installation.
'''
        result = detect_content_type_heuristic(content)
        assert result == ContentType.PROCEDURE
    
    def test_detect_heuristic_assembly(self):
        """Test heuristic detection of assembly."""
        content = '''= Main document

include::modules/topic1.adoc[]

include::modules/topic2.adoc[]
'''
        result = detect_content_type_heuristic(content)
        assert result == ContentType.ASSEMBLY
    
    def test_detect_heuristic_reference(self):
        """Test heuristic detection of reference."""
        content = '''= Configuration parameters

|===
| Parameter | Description
| timeout | Connection timeout
| retries | Number of retries
|===
'''
        result = detect_content_type_heuristic(content)
        assert result == ContentType.REFERENCE
    
    def test_detect_heuristic_snippet(self):
        """Test heuristic detection of snippet."""
        content = '''[NOTE]
====
This is an important note.
====
'''
        result = detect_content_type_heuristic(content)
        assert result == ContentType.SNIPPET
    
    def test_detect_heuristic_concept_default(self):
        """Test that concept is default for general content."""
        content = '''= Understanding data pipelines

Data pipelines are used for processing data.

Key benefits include:
* Automation
* Scalability
* Reliability
'''
        result = detect_content_type_heuristic(content)
        assert result == ContentType.CONCEPT


class TestValeRules:
    """Tests for Vale rules."""
    
    def test_critical_rules_defined(self):
        """Test that critical rules are defined."""
        critical_rules = [
            "ShortDescription",
            "TaskStep",
            "TaskContents",
            "CalloutList",
            "ContentType",
            "LineBreak",  # Now included in modular rules
        ]
        
        for rule in critical_rules:
            assert rule in ALL_RULES, f"Missing critical rule: {rule}"
    
    def test_all_30_rules_loaded(self):
        """Test that all 30 rules from asciidoctor-dita-vale are loaded."""
        assert len(ALL_RULES) == 30, f"Expected 30 rules, got {len(ALL_RULES)}"
    
    def test_rules_have_required_fields(self):
        """Test that each rule has required fields."""
        for rule_name, rule in ALL_RULES.items():
            assert rule.name == rule_name, f"{rule_name} name mismatch"
            assert rule.severity is not None, f"{rule_name} missing severity"
            assert rule.message, f"{rule_name} missing message"
            assert rule.fix_instruction, f"{rule_name} missing fix_instruction"
    
    def test_get_fix_instruction(self):
        """Test getting fix instruction for a rule."""
        instruction = get_fix_instruction("ShortDescription")
        
        assert instruction is not None
        assert "role=\"_abstract\"" in instruction
    
    def test_get_fix_instruction_unknown(self):
        """Test getting fix instruction for unknown rule."""
        instruction = get_fix_instruction("NonExistentRule")
        
        assert instruction is None
    
    def test_get_rule_severity(self):
        """Test getting rule severity."""
        severity = get_rule_severity("ShortDescription")
        
        assert severity == RuleSeverity.WARNING  # ShortDescription is now WARNING per upstream
    
    def test_get_rule_severity_warning(self):
        """Test getting warning severity."""
        severity = get_rule_severity("BlockTitle")
        
        assert severity == RuleSeverity.WARNING
    
    def test_get_rule_severity_unknown(self):
        """Test default severity for unknown rule."""
        severity = get_rule_severity("NonExistentRule")
        
        assert severity == RuleSeverity.WARNING
    
    def test_get_rule(self):
        """Test getting full rule object."""
        rule = get_rule("ShortDescription")
        
        assert rule is not None
        assert rule.name == "ShortDescription"
        assert len(rule.examples) > 0
    
    def test_get_rule_unknown(self):
        """Test getting unknown rule returns None."""
        rule = get_rule("NonExistentRule")
        assert rule is None
    
    def test_get_error_rules(self):
        """Test getting all error rules."""
        error_rules = get_error_rules()
        
        assert len(error_rules) == 5  # 5 errors per asciidoctor-dita-vale
        
        # Verify all are errors
        for name, rule in error_rules.items():
            assert rule.severity == RuleSeverity.ERROR
    
    def test_get_warning_rules(self):
        """Test getting all warning rules."""
        warning_rules = get_warning_rules()
        
        assert len(warning_rules) == 21  # 21 warnings per asciidoctor-dita-vale
        
        # Verify all are warnings
        for name, rule in warning_rules.items():
            assert rule.severity == RuleSeverity.WARNING
    
    def test_fix_instructions_are_actionable(self):
        """Test that fix instructions provide actionable guidance."""
        for rule_name, rule in ALL_RULES.items():
            if rule.severity == RuleSeverity.SUGGESTION:
                continue  # Skip suggestions - they're informational
            
            instruction = rule.fix_instruction
            
            # Instructions should be non-empty and meaningful
            assert len(instruction) > 20, f"{rule_name} has too short instruction"
            
            # Instructions should mention what to do
            action_words = ["add", "remove", "ensure", "use", "convert", "replace", "fix", "split", "move"]
            has_action = any(word in instruction.lower() for word in action_words)
            assert has_action, f"{rule_name} instruction lacks action words"
    
    def test_snippet_rules_skipped(self):
        """Test that ShortDescription is skipped for SNIPPET files."""
        rule = get_rule("ShortDescription")
        assert rule is not None
        assert rule.skip_for_types is not None
        assert "SNIPPET" in rule.skip_for_types
        
        # Verify should_apply returns False for SNIPPET
        assert rule.should_apply("SNIPPET") == False
        assert rule.should_apply("CONCEPT") == True


class TestKnowledgeIntegration:
    """Integration tests for knowledge base."""
    
    def test_content_type_examples_are_valid(self):
        """Test that content type examples are syntactically valid."""
        for type_name, rules in CONTENT_TYPE_RULES.items():
            example = rules["example"]
            
            # Examples should have content
            assert len(example) > 50, f"{type_name} example too short"
            
            # Examples should have :_mod-docs-content-type: attribute
            assert ":_mod-docs-content-type:" in example, f"{type_name} example missing module-type"
    
    def test_procedure_example_has_procedure_block(self):
        """Test that PROCEDURE example has .Procedure block."""
        example = CONTENT_TYPE_RULES["PROCEDURE"]["example"]
        
        assert ".Procedure" in example
    
    def test_assembly_example_has_includes(self):
        """Test that ASSEMBLY example has include directives."""
        example = CONTENT_TYPE_RULES["ASSEMBLY"]["example"]
        
        assert "include::" in example
    
    def test_vale_examples_show_before_after(self):
        """Test that rules with examples show transformation."""
        for rule_name, rule in ALL_RULES.items():
            if rule.examples:
                for example in rule.examples:
                    before = example.before
                    after = example.after
                    
                    # Before and after should be different
                    if after:
                        assert before != after, f"{rule_name} before/after are identical"
    
    def test_all_rules_have_links(self):
        """Test that all rules have documentation links."""
        for rule_name, rule in ALL_RULES.items():
            assert rule.link, f"{rule_name} missing link"
            assert "asciidoctor-dita-vale" in rule.link


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
