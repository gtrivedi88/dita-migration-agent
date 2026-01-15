"""
Base class for Vale rules.

Each rule file inherits from this base and defines:
- Rule metadata (name, severity, message)
- Fix instruction for LLM
- Before/after examples from fixtures
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class RuleSeverity(Enum):
    """Severity levels for Vale rules."""
    ERROR = "error"
    WARNING = "warning"
    SUGGESTION = "suggestion"


@dataclass
class RuleExample:
    """Before/after example for a rule."""
    description: str
    before: str
    after: str


@dataclass
class Rule:
    """
    Base class for Vale DITA rules.
    
    Each rule contains:
    - Metadata: name, severity, message, link
    - Fix instruction: detailed instructions for LLM
    - Examples: before/after code samples
    - Applicable content types: which file types this rule applies to
    """
    
    name: str
    """Vale rule name (e.g., 'LineBreak', 'ShortDescription')."""
    
    severity: RuleSeverity
    """Severity level: error, warning, or suggestion."""
    
    message: str
    """The message Vale displays when this rule triggers."""
    
    fix_instruction: str
    """Detailed instructions for LLM on how to fix this issue."""
    
    link: str = "https://github.com/jhradilek/asciidoctor-dita-vale"
    """Link to documentation about this rule."""
    
    examples: List[RuleExample] = field(default_factory=list)
    """Before/after examples showing correct fixes."""
    
    applicable_types: Optional[List[str]] = None
    """Content types this rule applies to (None = all types).
    
    Values: PROCEDURE, CONCEPT, REFERENCE, ASSEMBLY, SNIPPET
    If None, rule applies to all content types.
    If empty list [], rule is skipped for all types.
    """
    
    skip_for_types: Optional[List[str]] = None
    """Content types this rule should be SKIPPED for.
    
    For example, ShortDescription should skip SNIPPET files.
    """
    
    def should_apply(self, content_type: Optional[str]) -> bool:
        """
        Check if this rule should apply to a file with given content type.
        
        Args:
            content_type: The file's content type (PROCEDURE, CONCEPT, etc.)
            
        Returns:
            True if rule should be applied, False to skip.
        """
        # If skip_for_types is set and content_type matches, skip
        if self.skip_for_types and content_type:
            if content_type.upper() in [t.upper() for t in self.skip_for_types]:
                return False
        
        # If applicable_types is None, apply to all
        if self.applicable_types is None:
            return True
        
        # If applicable_types is empty, skip all
        if len(self.applicable_types) == 0:
            return False
        
        # Check if content_type is in applicable_types
        if content_type:
            return content_type.upper() in [t.upper() for t in self.applicable_types]
        
        # No content type specified, apply by default
        return True
    
    def get_prompt_context(self) -> str:
        """
        Generate prompt context for LLM including fix instructions and examples.
        
        Returns:
            Formatted string for inclusion in LLM prompt.
        """
        context = f"""Rule: {self.name}
Severity: {self.severity.value}
Message: {self.message}

FIX INSTRUCTION:
{self.fix_instruction}
"""
        
        if self.examples:
            context += "\nEXAMPLES:\n"
            for i, example in enumerate(self.examples, 1):
                context += f"""
Example {i}: {example.description}

BEFORE (problematic):
```asciidoc
{example.before}
```

AFTER (fixed):
```asciidoc
{example.after}
```
"""
        
        return context
