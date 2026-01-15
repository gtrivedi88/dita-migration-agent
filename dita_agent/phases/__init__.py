"""
Phase implementations for DITA migration.

Phase 1: Content Type Assignment - Add :_mod-docs-content-type: attribute
Phase 2: Callouts Conversion - Convert callout markers to DITA format
Phase 3: All Other DITA Issues - Fix remaining Vale errors
"""

from dita_agent.phases.content_type import ContentTypePhase
from dita_agent.phases.callouts import CalloutsPhase
from dita_agent.phases.dita_issues import DITAIssuesPhase

__all__ = [
    "ContentTypePhase",
    "CalloutsPhase",
    "DITAIssuesPhase",
]
