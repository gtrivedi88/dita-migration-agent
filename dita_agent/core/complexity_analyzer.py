"""
Complexity Analyzer - Analyze file complexity for intelligent routing.

This module measures file complexity to determine the best fixer strategy:
- Low complexity → LLM with full context
- Medium complexity → LLM with smart context windowing
- High complexity → Pattern matching or manual review

Enterprise production standards:
- Fast complexity scoring (O(n) single pass)
- Clear thresholds for routing decisions
- Detailed complexity breakdown for debugging
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class ComplexityScore:
    """Complexity analysis result."""
    total_score: int
    nested_conditionals: int
    long_lines: int
    attribute_refs: int
    include_directives: int
    max_line_length: int
    total_lines: int
    complexity_level: str  # "LOW", "MEDIUM", "HIGH", "VERY_HIGH"

    def __str__(self) -> str:
        return (
            f"Complexity: {self.complexity_level} (score={self.total_score})\n"
            f"  - Nested conditionals: {self.nested_conditionals}\n"
            f"  - Long lines (200+ chars): {self.long_lines}\n"
            f"  - Attribute references: {self.attribute_refs}\n"
            f"  - Include directives: {self.include_directives}\n"
            f"  - Max line length: {self.max_line_length}\n"
            f"  - Total lines: {self.total_lines}"
        )


class ComplexityAnalyzer:
    """Analyze AsciiDoc file complexity for intelligent routing."""

    # Complexity thresholds
    LOW_THRESHOLD = 20
    MEDIUM_THRESHOLD = 50
    HIGH_THRESHOLD = 100

    # Scoring weights
    NESTED_CONDITIONAL_WEIGHT = 10  # Each level of nesting
    LONG_LINE_WEIGHT = 5            # Lines over 200 chars
    ATTRIBUTE_REF_WEIGHT = 2        # {attribute} references
    INCLUDE_DIRECTIVE_WEIGHT = 1    # include:: directives

    def __init__(self):
        # Regex patterns
        self.r_ifdef = re.compile(r'^\s*ifdef::')
        self.r_ifndef = re.compile(r'^\s*ifndef::')
        self.r_ifeval = re.compile(r'^\s*ifeval::')
        self.r_endif = re.compile(r'^\s*endif::')
        self.r_attribute_ref = re.compile(r'\{[A-Za-z0-9_-]+\}')
        self.r_include = re.compile(r'^\s*include::')

    def analyze_file(self, file_path: Path) -> ComplexityScore:
        """Analyze a file and return complexity score."""
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            # Can't read file, treat as high complexity (manual review)
            return ComplexityScore(
                total_score=999,
                nested_conditionals=0,
                long_lines=0,
                attribute_refs=0,
                include_directives=0,
                max_line_length=0,
                total_lines=0,
                complexity_level="VERY_HIGH"
            )

        return self.analyze_content(content)

    def analyze_content(self, content: str) -> ComplexityScore:
        """Analyze content string and return complexity score."""
        lines = content.split('\n')

        # Track metrics
        nested_conditionals = 0
        max_nesting = 0
        current_nesting = 0
        long_lines = 0
        attribute_refs = 0
        include_directives = 0
        max_line_length = 0

        for line in lines:
            line_len = len(line)
            max_line_length = max(max_line_length, line_len)

            # Count nesting depth
            if self.r_ifdef.match(line) or self.r_ifndef.match(line) or self.r_ifeval.match(line):
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            elif self.r_endif.match(line):
                current_nesting = max(0, current_nesting - 1)

            # Count long lines (200+ chars)
            if line_len > 200:
                long_lines += 1

            # Count attribute references
            attribute_refs += len(self.r_attribute_ref.findall(line))

            # Count include directives
            if self.r_include.match(line):
                include_directives += 1

        nested_conditionals = max_nesting

        # Calculate total score
        total_score = (
            nested_conditionals * self.NESTED_CONDITIONAL_WEIGHT +
            long_lines * self.LONG_LINE_WEIGHT +
            attribute_refs * self.ATTRIBUTE_REF_WEIGHT +
            include_directives * self.INCLUDE_DIRECTIVE_WEIGHT
        )

        # Determine complexity level
        if total_score < self.LOW_THRESHOLD:
            complexity_level = "LOW"
        elif total_score < self.MEDIUM_THRESHOLD:
            complexity_level = "MEDIUM"
        elif total_score < self.HIGH_THRESHOLD:
            complexity_level = "HIGH"
        else:
            complexity_level = "VERY_HIGH"

        return ComplexityScore(
            total_score=total_score,
            nested_conditionals=nested_conditionals,
            long_lines=long_lines,
            attribute_refs=attribute_refs,
            include_directives=include_directives,
            max_line_length=max_line_length,
            total_lines=len(lines),
            complexity_level=complexity_level
        )

    def extract_context_window(
        self,
        content: str,
        issue_line: int,
        window_size: int = 15
    ) -> Tuple[str, int]:
        """
        Extract smart context window around an issue.

        Args:
            content: Full file content
            issue_line: Line number of the issue (1-indexed)
            window_size: Number of lines before and after (default=15)

        Returns:
            Tuple of (context_string, offset_line_number)
            offset_line_number is the line number where context starts (1-indexed)
        """
        lines = content.split('\n')
        total_lines = len(lines)

        # Convert to 0-indexed
        issue_idx = issue_line - 1

        # Calculate window bounds
        start_idx = max(0, issue_idx - window_size)
        end_idx = min(total_lines, issue_idx + window_size + 1)

        # Expand to include complete conditional blocks
        start_idx, end_idx = self._expand_to_conditional_boundaries(
            lines, start_idx, end_idx
        )

        # Extract context
        context_lines = lines[start_idx:end_idx]
        context_string = '\n'.join(context_lines)

        # Return context with 1-indexed offset
        offset_line = start_idx + 1

        return context_string, offset_line

    def _expand_to_conditional_boundaries(
        self,
        lines: List[str],
        start_idx: int,
        end_idx: int
    ) -> Tuple[int, int]:
        """
        Expand context window to include complete conditional blocks.

        If the context starts/ends in the middle of an ifdef/endif block,
        expand to include the full block for context.
        """
        # Track nesting when scanning backwards
        nesting = 0
        for i in range(start_idx, -1, -1):
            line = lines[i]
            if self.r_endif.match(line):
                nesting += 1
            elif self.r_ifdef.match(line) or self.r_ifndef.match(line):
                if nesting > 0:
                    nesting -= 1
                else:
                    # Found opening of a block, expand to include it
                    start_idx = i
                    break

        # Track nesting when scanning forwards
        nesting = 0
        for i in range(end_idx - 1, len(lines)):
            line = lines[i]
            if self.r_ifdef.match(line) or self.r_ifndef.match(line):
                nesting += 1
            elif self.r_endif.match(line):
                if nesting > 0:
                    nesting -= 1
                else:
                    # Found closing of a block, expand to include it
                    end_idx = i + 1
                    break

        return start_idx, end_idx

    def should_use_context_window(self, complexity: ComplexityScore) -> bool:
        """Determine if smart context windowing should be used."""
        # Use windowing for MEDIUM and HIGH complexity
        # VERY_HIGH should route to pattern matching or manual review
        return complexity.complexity_level in ["MEDIUM", "HIGH"]

    def should_skip_llm(self, complexity: ComplexityScore) -> bool:
        """Determine if LLM should be skipped entirely (use pattern matching)."""
        # Skip LLM for VERY_HIGH complexity
        return complexity.complexity_level == "VERY_HIGH"

    def flatten_conditionals(self, content: str, target: str = 'upstream') -> str:
        """
        Flatten conditional blocks for a specific target.

        This removes ambiguity for LLM by showing only the active conditional branch.

        Args:
            content: Original AsciiDoc content with conditionals
            target: Build target ('upstream' or 'downstream')

        Returns:
            Flattened content with only active conditionals expanded

        Example:
            Input:
                ifndef::upstream[]
                Content for downstream
                endif::[]
                ifdef::upstream[]
                Content for upstream
                endif::[]

            Output (target='upstream'):
                Content for upstream
        """
        lines = content.split('\n')
        result = []
        skip_depth = 0  # Track nesting depth of skipped blocks
        active_depth = 0  # Track nesting depth of active blocks

        for line in lines:
            stripped = line.strip()

            # Check for ifdef/ifndef directives
            if stripped.startswith('ifdef::'):
                # Extract the condition (e.g., 'upstream' from 'ifdef::upstream[]')
                condition = stripped.replace('ifdef::', '').replace('[]', '').strip()

                if condition == target:
                    # This block should be included
                    active_depth += 1
                    continue  # Don't include the ifdef line itself
                else:
                    # This block should be skipped
                    skip_depth += 1
                    continue

            elif stripped.startswith('ifndef::'):
                # Extract the condition
                condition = stripped.replace('ifndef::', '').replace('[]', '').strip()

                if condition != target:
                    # This block should be included (NOT the target)
                    active_depth += 1
                    continue
                else:
                    # This block should be skipped (IS the target)
                    skip_depth += 1
                    continue

            elif stripped.startswith('endif::'):
                # Close the most recent block
                if skip_depth > 0:
                    skip_depth -= 1
                elif active_depth > 0:
                    active_depth -= 1
                continue  # Don't include endif lines

            # Include line if not in a skipped block
            if skip_depth == 0:
                result.append(line)

        return '\n'.join(result)


# Singleton instance
_analyzer = ComplexityAnalyzer()


def analyze_file(file_path: Path) -> ComplexityScore:
    """Analyze file complexity (convenience function)."""
    return _analyzer.analyze_file(file_path)


def analyze_content(content: str) -> ComplexityScore:
    """Analyze content complexity (convenience function)."""
    return _analyzer.analyze_content(content)


def extract_context_window(content: str, issue_line: int, window_size: int = 15) -> Tuple[str, int]:
    """Extract smart context window (convenience function)."""
    return _analyzer.extract_context_window(content, issue_line, window_size)


def flatten_conditionals(content: str, target: str = 'upstream') -> str:
    """Flatten conditional blocks (convenience function)."""
    return _analyzer.flatten_conditionals(content, target)
