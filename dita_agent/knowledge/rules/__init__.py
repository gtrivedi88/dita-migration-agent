"""
Modular Vale rules for DITA compatibility checking.

Each rule is defined in its own file for easy maintenance.
Rules are loaded dynamically by the loader module.

Based on: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity

__all__ = ["Rule", "RuleSeverity"]
