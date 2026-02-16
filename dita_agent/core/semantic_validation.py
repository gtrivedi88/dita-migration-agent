"""
Semantic validation for DITA fixes.

Validates that fixes preserve meaning and meet DITA semantic requirements.
Goes beyond Vale's syntax checking to ensure content quality.
"""

import re
from dataclasses import dataclass
from typing import Tuple


@dataclass
class ValidationResult:
    """Result of semantic validation."""
    is_valid: bool
    error: str = ""
    suggestion: str = ""


class SemanticValidator:
    """Validates fixes for semantic correctness beyond Vale rules."""

    def validate_short_description(self, text: str) -> ValidationResult:
        """
        Validate that text is suitable as a DITA short description.

        Requirements:
        1. Self-contained (no dependency on following content)
        2. No colon at end (indicates incomplete thought)
        3. No forward references ("following", "below", etc.)
        4. Reasonable length (10-75 words)
        5. Grammatically complete

        Returns:
            ValidationResult with is_valid=False if issues found
        """
        text = text.strip()

        # Check 1: Ends with colon (incomplete)
        if text.endswith(":"):
            return ValidationResult(
                is_valid=False,
                error="Short description ends with ':' which indicates an incomplete thought",
                suggestion="Rewrite to be a complete sentence without depending on following content. "
                          "Incorporate key information from bullets into the paragraph itself."
            )

        # Check 2: Forward references
        forward_refs = [
            "the following",
            "as follows:",
            "listed below",
            "shown below",
            " if:",
            " when:",
            " where:",
            "these include:",
            "including:",
        ]
        text_lower = text.lower()
        for ref in forward_refs:
            if ref in text_lower:
                return ValidationResult(
                    is_valid=False,
                    error=f"Short description contains forward reference: '{ref}'",
                    suggestion="Rewrite to include key information inline instead of referencing following content"
                )

        # Check 3: Too short (not descriptive)
        word_count = len(text.split())
        if word_count < 10:
            return ValidationResult(
                is_valid=False,
                error=f"Short description is too brief ({word_count} words, minimum 10)",
                suggestion="Expand to provide a meaningful summary of the topic"
            )

        # Check 4: Too long (not concise)
        if word_count > 75:
            return ValidationResult(
                is_valid=False,
                error=f"Short description is too long ({word_count} words, maximum 75)",
                suggestion="Condense to be more concise while retaining key information"
            )

        # Check 5: Unresolved attributes — only flag malformed references,
        # NOT normal AsciiDoc product attributes like {ProductName}.
        # AsciiDoc attributes are expected in Red Hat docs and resolve at build time.
        # Only flag references that look broken: empty braces, unclosed braces, or
        # braces containing spaces (likely formatting errors).
        if re.search(r'\{[ \t]*\}|\{[^}]*\n', text):
            return ValidationResult(
                is_valid=False,
                error="Short description contains malformed attribute references (empty or unclosed braces)",
                suggestion="Fix the malformed attribute reference syntax"
            )

        # Check 6: Ends with incomplete sentence indicators
        incomplete_endings = [" if", " when", " where", " because", " since", " unless"]
        for ending in incomplete_endings:
            if text_lower.endswith(ending):
                return ValidationResult(
                    is_valid=False,
                    error=f"Short description ends with incomplete phrase: '{ending}'",
                    suggestion="Complete the thought or rephrase as a full sentence"
                )

        return ValidationResult(is_valid=True)

    def validate_related_links(self, content: str) -> ValidationResult:
        """
        Validate that Additional Resources section contains only links.

        Requirements:
        1. Each list item must contain link: or xref:
        2. No plain text items
        3. No code blocks or formatted text without links

        Returns:
            ValidationResult with details of non-link content
        """
        lines = content.strip().split("\n")
        non_link_items = []

        link_pattern = re.compile(r'(link:https?://|xref:)')

        for i, line in enumerate(lines, 1):
            # Skip empty lines, headers, role attributes
            stripped = line.strip()
            if not stripped or stripped.startswith("==") or stripped.startswith("[role="):
                continue

            # Must be a list item
            if not stripped.startswith("*"):
                continue

            # Check if it contains a link
            if not link_pattern.search(line):
                # Extract the item text for error message
                item_text = stripped[1:].strip()[:60]  # First 60 chars after *
                non_link_items.append(f"Line {i}: {item_text}")

        if non_link_items:
            return ValidationResult(
                is_valid=False,
                error=f"Found {len(non_link_items)} list items without links",
                suggestion="Convert to actual links (link: or xref:), move to body text, or remove:\n" +
                          "\n".join(non_link_items)
            )

        return ValidationResult(is_valid=True)

    def validate_no_discrete_heading(self, content: str) -> ValidationResult:
        """
        Check if content would create a discrete heading violation.

        Returns:
            ValidationResult with is_valid=False if [discrete] found
        """
        if re.search(r'^\[discrete\b', content, re.MULTILINE):
            return ValidationResult(
                is_valid=False,
                error="Content contains [discrete] which is not DITA-compatible",
                suggestion="Remove [discrete] and use proper section headings instead"
            )

        return ValidationResult(is_valid=True)

    def extract_abstract_text(self, content: str) -> str:
        """
        Extract the text that will become the short description.

        Finds the paragraph that follows [role="_abstract"].

        Args:
            content: Full file content

        Returns:
            The paragraph text, or empty string if not found
        """
        lines = content.split('\n')
        in_abstract = False
        abstract_lines = []

        for line in lines:
            stripped = line.strip()

            # Found the marker
            if stripped == '[role="_abstract"]':
                in_abstract = True
                continue

            # If we're collecting abstract text
            if in_abstract:
                # Stop at empty line or next block
                if not stripped or stripped.startswith(('=', '[', '*', '.', '|')):
                    break
                abstract_lines.append(line)

        return ' '.join(abstract_lines).strip()
