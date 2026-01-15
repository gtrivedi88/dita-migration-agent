"""
Specialized fixers for specific DITA issues.

Some issues have predictable patterns that can be fixed with regex,
saving LLM costs and being more reliable. LLM is used as fallback
when the pattern is unclear.
"""

from .short_description import ShortDescriptionFixer

__all__ = ["ShortDescriptionFixer"]
