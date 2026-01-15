"""
Prompt templates for LLM interactions.

All prompts follow the key principle: Request TARGETED EDITS (old_string → new_string),
never ask for complete file rewrites.
"""

from enum import Enum
from typing import Dict, Optional


class PromptType(Enum):
    """Types of prompts available."""
    CONTENT_TYPE = "content_type"
    CALLOUTS_REVIEW = "callouts_review"
    CALLOUTS_FIX = "callouts_fix"
    DITA_FIX = "dita_fix"


# System prompt that emphasizes targeted edits
SYSTEM_PROMPT = """You are a documentation expert specializing in AsciiDoc and DITA compatibility.

CRITICAL RULES:
1. NEVER rewrite entire files - only provide targeted edits
2. ALWAYS preserve existing content exactly as-is except for the specific fix
3. NEVER modify ifdef/ifndef/endif conditional blocks
4. ALWAYS return valid JSON with 'old_string' and 'new_string' fields
5. The 'old_string' must be an EXACT match of text in the file (including whitespace)
6. Make the MINIMAL change needed to fix the issue

Return ONLY a JSON object, no explanations or markdown."""


class PromptBuilder:
    """
    Builder for LLM prompts.
    
    Creates prompts that always request targeted edits.
    """
    
    @staticmethod
    def content_type_prompt(file_content: str, filename: str) -> str:
        """
        Build prompt for content type detection and assignment.
        
        Args:
            file_content: Full file content.
            filename: Name of the file.
            
        Returns:
            Prompt string.
        """
        return f'''Analyze this AsciiDoc file to determine its content type and add the appropriate :_mod-docs-content-type: attribute.

CONTENT TYPE RULES (from Red Hat Modular Documentation Guide):

PROCEDURE:
• Describes HOW to do something step-by-step
• Has .Procedure block title followed by numbered list
• May have .Prerequisites, .Verification, .Next steps sections

CONCEPT:
• Explains WHAT something is or WHY it matters
• Descriptive, explanatory paragraphs
• No step-by-step procedures

REFERENCE:
• Reference information users look up
• Tables with parameters, options, settings
• Lists of values or configuration attributes

ASSEMBLY:
• Contains include:: directives to combine multiple modules
• Acts as a container/wrapper for other content

SNIPPET:
• Small reusable text fragment
• No title, meant to be included in other files
• Typically very short

---

FILENAME: {filename}

FILE CONTENT:
{file_content}

---

Determine the content type. Return a targeted edit to add :_mod-docs-content-type: attribute.

CRITICAL: :_mod-docs-content-type: MUST be the VERY FIRST LINE of the file.
Nothing should come before it - not the title, not comments, nothing.

Return JSON:
{{
  "content_type": "PROCEDURE|CONCEPT|REFERENCE|ASSEMBLY|SNIPPET",
  "reasoning": "Brief explanation of why this type",
  "old_string": "<exact first line of file>",
  "new_string": ":_mod-docs-content-type: <TYPE>\\n\\n<same first line>"
}}'''

    @staticmethod
    def callouts_review_prompt(original: str, modified: str, filename: str) -> str:
        """
        Build prompt for reviewing callouts conversion tool output.
        
        Args:
            original: Original file content.
            modified: Modified file content.
            filename: Name of the file.
            
        Returns:
            Prompt string.
        """
        return f'''The callouts-conversion tool modified this file. Review the changes.

FILENAME: {filename}

ORIGINAL:
```
{original}
```

AFTER TOOL:
```
{modified}
```

Review the tool's changes:
1. Are callout markers (<1>, <2>) properly removed from code blocks?
2. Is the explanation list correctly converted to a description list?
3. Is any content lost or corrupted?
4. Are the changes semantically correct?

Return JSON:
{{
  "is_correct": true/false,
  "issues": ["list of problems if any"],
  "fix_needed": true/false,
  "old_string": "...",  // Only if fix_needed is true
  "new_string": "..."   // Only if fix_needed is true
}}'''

    @staticmethod
    def callouts_fix_prompt(content: str, filename: str, line: int) -> str:
        """
        Build prompt for fixing callouts that the tool couldn't handle.
        
        Args:
            content: File content around the callout.
            filename: Name of the file.
            line: Line number of the callout issue.
            
        Returns:
            Prompt string.
        """
        return f'''Fix the callout markers in this AsciiDoc code block.

FILENAME: {filename}
ISSUE LINE: {line}

Callouts like <1>, <2> in code blocks must be converted to description lists.

CONTENT:
```
{content}
```

Convert the callout markers to DITA-compatible format.

BEFORE (example):
```
[source,yaml]
----
apiVersion: v1 <1>
kind: Pod <2>
----
<1> API version
<2> Resource type
```

AFTER (example):
```
[source,yaml]
----
apiVersion: v1
kind: Pod
----

apiVersion: v1:: API version
kind: Pod:: Resource type
```

Return JSON with the targeted edit:
{{
  "old_string": "<exact text to replace>",
  "new_string": "<corrected text>"
}}'''

    @staticmethod
    def dita_fix_prompt(
        filename: str,
        line: int,
        rule_name: str,
        error_message: str,
        context: str,
        fix_instruction: str,
    ) -> str:
        """
        Build prompt for fixing a DITA compatibility issue.
        
        Args:
            filename: Name of the file.
            line: Line number of the issue.
            rule_name: Name of the Vale rule that flagged this.
            error_message: The error message from Vale.
            context: Lines around the error.
            fix_instruction: How to fix this issue.
            
        Returns:
            Prompt string.
        """
        return f'''Fix this DITA compatibility issue.

FILE: {filename}
LINE: {line}
RULE: {rule_name}
ERROR: {error_message}

CONTEXT (lines around error):
```
{context}
```

HOW TO FIX: {fix_instruction}

CRITICAL RULES:
• Make the MINIMAL change needed
• Do NOT move any content - only ADD or MODIFY in place
• Do NOT modify or reorder any ifdef/ifndef/endif/ifeval blocks
• If adding content before a conditional, place it BEFORE the ifdef line
• If adding content after a conditional block (endif), place it after endif
• Preserve ALL existing content structure
• The old_string must EXACTLY match text in the file (including whitespace)

Return ONLY JSON:
{{
  "old_string": "<exact text to find and replace>",
  "new_string": "<corrected text>"
}}'''

    @staticmethod
    def short_description_prompt(
        filename: str,
        line: int,
        context: str,
        title: str,
    ) -> str:
        """
        Build prompt specifically for ShortDescription issues.
        
        This is a common issue that needs careful handling.
        
        Args:
            filename: Name of the file.
            line: Line number of the issue.
            context: Lines around the title.
            title: The document title.
            
        Returns:
            Prompt string.
        """
        return f'''Add a short description (abstract paragraph) to this AsciiDoc file.

FILE: {filename}
TITLE: {title}

CONTEXT:
```
{context}
```

The file needs a [role="_abstract"] paragraph after the title but before any other content.

RULES:
• Add [role="_abstract"] on a line by itself
• Follow it with a single paragraph that summarizes the content
• The abstract should be 1-2 sentences
• Place it AFTER the title line, BEFORE any .Prerequisites or .Procedure sections

Return JSON:
{{
  "abstract_text": "One or two sentence summary of what this content covers",
  "old_string": "<exact lines to replace, including title and what follows>",
  "new_string": "<title line>\\n\\n[role=\\"_abstract\\"]\\n<abstract paragraph>\\n\\n<rest of content>"
}}'''

    @staticmethod
    def get_system_prompt() -> str:
        """Get the system prompt for all LLM interactions."""
        return SYSTEM_PROMPT
    
    @staticmethod
    def get_prompt(
        prompt_type: PromptType,
        **kwargs,
    ) -> str:
        """
        Get a prompt by type.
        
        Args:
            prompt_type: Type of prompt to generate.
            **kwargs: Arguments for the specific prompt type.
            
        Returns:
            Prompt string.
        """
        if prompt_type == PromptType.CONTENT_TYPE:
            return PromptBuilder.content_type_prompt(
                kwargs["file_content"],
                kwargs["filename"],
            )
        elif prompt_type == PromptType.CALLOUTS_REVIEW:
            return PromptBuilder.callouts_review_prompt(
                kwargs["original"],
                kwargs["modified"],
                kwargs["filename"],
            )
        elif prompt_type == PromptType.CALLOUTS_FIX:
            return PromptBuilder.callouts_fix_prompt(
                kwargs["content"],
                kwargs["filename"],
                kwargs["line"],
            )
        elif prompt_type == PromptType.DITA_FIX:
            return PromptBuilder.dita_fix_prompt(
                kwargs["filename"],
                kwargs["line"],
                kwargs["rule_name"],
                kwargs["error_message"],
                kwargs["context"],
                kwargs["fix_instruction"],
            )
        else:
            raise ValueError(f"Unknown prompt type: {prompt_type}")
