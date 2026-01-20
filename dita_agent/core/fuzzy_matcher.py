"""
Fuzzy String Matching for Automated Fixes

Provides fallback matching when exact string matching fails due to minor LLM variations.
This is critical for handling long lines (200+ chars) where LLM might make tiny mistakes.

Production-ready features:
- 98% similarity threshold (strict but forgiving)
- Uniqueness check (prevents ambiguous replacements)
- Line-aware matching (respects line boundaries)
"""

from difflib import SequenceMatcher
from typing import Optional, List, Tuple


class FuzzyMatcher:
    """Fuzzy string matcher with safety guarantees for production use."""

    def __init__(self, similarity_threshold: float = 0.98):
        """
        Initialize fuzzy matcher.

        Args:
            similarity_threshold: Minimum similarity ratio (0.0-1.0)
                                 Default 0.98 = 98% similar
        """
        self.similarity_threshold = similarity_threshold

    def find_best_match(
        self,
        content: str,
        target: str,
        threshold: Optional[float] = None
    ) -> Optional[str]:
        """
        Find the best fuzzy match for target string in content.

        Args:
            content: Full file content
            target: String to find (may have minor variations)
            threshold: Override default similarity threshold

        Returns:
            The actual string from content that best matches target,
            or None if no match meets threshold or match is ambiguous
        """
        threshold = threshold or self.similarity_threshold

        # Try exact match first (fastest path)
        if target in content:
            return target

        # Find all potential matches
        matches = self._find_fuzzy_matches(content, target, threshold)

        # No matches
        if not matches:
            return None

        # Multiple matches = ambiguous, not safe
        if len(matches) > 1:
            # Check if all matches are identical (safe)
            if len(set(m[0] for m in matches)) == 1:
                return matches[0][0]
            return None  # Ambiguous

        # Single unique match = safe to use
        return matches[0][0]

    def _find_fuzzy_matches(
        self,
        content: str,
        target: str,
        threshold: float
    ) -> List[Tuple[str, float]]:
        """
        Find all strings in content that fuzzy match target above threshold.

        Returns:
            List of (matched_string, similarity_ratio) tuples
        """
        matches = []

        # Split content into potential match candidates
        # Strategy: Use sliding window of similar length to target
        target_len = len(target)
        lines = content.split('\n')

        # Single-line matches
        for line in lines:
            if not line.strip():
                continue

            ratio = SequenceMatcher(None, target, line).ratio()
            if ratio >= threshold:
                matches.append((line, ratio))

        # Multi-line matches (if target contains newlines)
        if '\n' in target:
            target_lines = target.count('\n') + 1
            for i in range(len(lines) - target_lines + 1):
                candidate = '\n'.join(lines[i:i + target_lines])
                ratio = SequenceMatcher(None, target, candidate).ratio()
                if ratio >= threshold:
                    matches.append((candidate, ratio))

        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches

    def apply_fuzzy_replacement(
        self,
        content: str,
        old_string: str,
        new_string: str,
        threshold: Optional[float] = None
    ) -> Optional[str]:
        """
        Apply fuzzy string replacement with safety checks.

        Args:
            content: Full file content
            old_string: String to replace (may not match exactly)
            new_string: Replacement string
            threshold: Override default similarity threshold

        Returns:
            Modified content, or None if fuzzy match is not safe
        """
        # Try exact match first
        if old_string in content:
            return content.replace(old_string, new_string, 1)  # Replace first occurrence only

        # Fallback to fuzzy match
        best_match = self.find_best_match(content, old_string, threshold)

        if best_match is None:
            return None

        # Apply replacement (only first occurrence for safety)
        return content.replace(best_match, new_string, 1)

    def get_similarity(self, str1: str, str2: str) -> float:
        """Get similarity ratio between two strings (0.0-1.0)."""
        return SequenceMatcher(None, str1, str2).ratio()


# Singleton instance for convenience
_fuzzy_matcher = FuzzyMatcher(similarity_threshold=0.98)


def find_best_match(content: str, target: str, threshold: float = 0.98) -> Optional[str]:
    """Find best fuzzy match (convenience function)."""
    return _fuzzy_matcher.find_best_match(content, target, threshold)


def apply_fuzzy_replacement(
    content: str,
    old_string: str,
    new_string: str,
    threshold: float = 0.98
) -> Optional[str]:
    """Apply fuzzy replacement (convenience function)."""
    return _fuzzy_matcher.apply_fuzzy_replacement(content, old_string, new_string, threshold)


def get_similarity(str1: str, str2: str) -> float:
    """Get similarity ratio (convenience function)."""
    return _fuzzy_matcher.get_similarity(str1, str2)
