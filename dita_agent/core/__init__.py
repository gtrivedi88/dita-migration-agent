"""
Core infrastructure module.

Contains scope resolution, session memory, verification, and manual review generation.
"""

from dita_agent.core.scope import ScopeResolver, ScopeResult
from dita_agent.core.memory import (
    # New v2 classes
    SessionMemoryV2,
    LearnedFix,
    FixerTier,
    # Common classes
    Phase,
    FixStatus,
    # Legacy classes (backward compatibility)
    SessionMemory,
    FixAttempt,
)
from dita_agent.core.verification import (
    Verifier,
    VerificationResult,
    ContentIntegrityReport,
)
from dita_agent.core.manual_review import (
    ManualReviewGenerator,
    ManualReviewItem,
    ManualReviewReport,
)

__all__ = [
    "ScopeResolver",
    "ScopeResult",
    # Memory - new
    "SessionMemoryV2",
    "LearnedFix",
    "FixerTier",
    # Memory - common
    "Phase",
    "FixStatus",
    # Memory - legacy
    "SessionMemory",
    "FixAttempt",
    # Verification
    "Verifier",
    "VerificationResult",
    "ContentIntegrityReport",
    # Manual review
    "ManualReviewGenerator",
    "ManualReviewItem",
    "ManualReviewReport",
]
