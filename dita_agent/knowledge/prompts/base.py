"""
Base prompt generator for DITA fixes.

Generates prompts dynamically based on rule definitions and file context.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..rules.loader import get_rule, get_prompt_context, ALL_RULES


@dataclass
class IssueContext:
    """Context for a single issue to fix."""
    rule_name: str
    line: int
    message: str
    context_lines: str  # Lines around the issue


class PromptGenerator:
    """
    Generates prompts for LLM-based DITA fixes.
    
    Uses rule definitions to create targeted, effective prompts.
    """
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get the system prompt for DITA fixes."""
        return """You are an expert AsciiDoc to DITA migration assistant.

Your task is to fix AsciiDoc content to be compatible with DITA 1.3.

CRITICAL RULES:
1. Return ONLY valid JSON with targeted edits
2. Each edit must have "old_string" (exact text to find) and "new_string" (replacement)
3. The old_string MUST exist exactly in the content (including whitespace)
4. Make MINIMAL changes - only fix the specific issue
5. NEVER delete content unless absolutely necessary
6. PRESERVE all conditionals (ifdef, ifndef, ifeval, endif)
7. PRESERVE all include directives
8. PRESERVE document structure

RESPONSE FORMAT:
{
  "fixes": [
    {
      "old_string": "exact text from file",
      "new_string": "fixed text",
      "explanation": "brief explanation"
    }
  ]
}

If an issue cannot be fixed automatically, return:
{
  "fixes": [],
  "unfixable_reason": "explanation of why"
}"""
    
    @staticmethod
    def generate_single_fix_prompt(
        file_content: str,
        filename: str,
        issue: IssueContext,
    ) -> str:
        """
        Generate prompt for fixing a single issue.
        
        Args:
            file_content: Full file content.
            filename: Name of the file.
            issue: Issue context with rule, line, message.
            
        Returns:
            Formatted prompt string.
        """
        # Get rule-specific context
        rule_context = get_prompt_context(issue.rule_name)
        if not rule_context:
            rule_context = f"Fix the issue: {issue.message}"
        
        prompt = f"""Fix the following DITA compatibility issue in {filename}:

ISSUE:
- Rule: {issue.rule_name}
- Line: {issue.line}
- Message: {issue.message}

{rule_context}

CONTEXT AROUND LINE {issue.line}:
```asciidoc
{issue.context_lines}
```

FULL FILE:
```asciidoc
{file_content}
```

Provide a targeted fix using old_string/new_string format.
The old_string must match exactly what's in the file."""
        
        return prompt
    
    @staticmethod
    def generate_batch_fix_prompt(
        file_content: str,
        filename: str,
        issues: List[IssueContext],
    ) -> str:
        """
        Generate prompt for fixing multiple issues at once.
        
        Args:
            file_content: Full file content.
            filename: Name of the file.
            issues: List of issue contexts.
            
        Returns:
            Formatted prompt string.
        """
        issues_text = ""
        for i, issue in enumerate(issues, 1):
            rule_context = get_prompt_context(issue.rule_name)
            if not rule_context:
                rule_context = f"Fix: {issue.message}"
            
            issues_text += f"""
### Issue {i}: {issue.rule_name} (Line {issue.line})

Message: {issue.message}

{rule_context}

Context around line {issue.line}:
```asciidoc
{issue.context_lines}
```

---
"""
        
        prompt = f"""Fix the following {len(issues)} DITA compatibility issues in {filename}:

{issues_text}

FULL FILE CONTENT:
```asciidoc
{file_content}
```

IMPORTANT:
1. Provide one fix per issue in order
2. Each fix needs old_string (exact match) and new_string
3. Return as JSON array with {len(issues)} fixes

Response format:
{{
  "fixes": [
    {{"old_string": "...", "new_string": "...", "explanation": "..."}},
    ...
  ]
}}"""
        
        return prompt


def generate_fix_prompt(
    file_content: str,
    filename: str,
    rule_name: str,
    line: int,
    message: str,
    context_lines: str,
) -> str:
    """
    Convenience function to generate a fix prompt.
    
    Args:
        file_content: Full file content.
        filename: Name of the file.
        rule_name: Vale rule name.
        line: Line number of issue.
        message: Issue message.
        context_lines: Context around the issue.
        
    Returns:
        Formatted prompt string.
    """
    issue = IssueContext(
        rule_name=rule_name,
        line=line,
        message=message,
        context_lines=context_lines,
    )
    return PromptGenerator.generate_single_fix_prompt(file_content, filename, issue)


def generate_batch_fix_prompt(
    file_content: str,
    filename: str,
    issues: List[Dict[str, Any]],
) -> str:
    """
    Convenience function to generate a batch fix prompt.
    
    Args:
        file_content: Full file content.
        filename: Name of the file.
        issues: List of issue dicts with keys: rule_name, line, message, context_lines
        
    Returns:
        Formatted prompt string.
    """
    issue_contexts = [
        IssueContext(
            rule_name=i["rule_name"],
            line=i["line"],
            message=i["message"],
            context_lines=i.get("context_lines", ""),
        )
        for i in issues
    ]
    return PromptGenerator.generate_batch_fix_prompt(file_content, filename, issue_contexts)
