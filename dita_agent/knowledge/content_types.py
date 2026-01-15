"""
Content type rules from Red Hat Modular Documentation Reference Guide.

Source: https://redhat-documentation.github.io/modular-docs/

This module defines the rules for determining AsciiDoc file content types
based on their content (not filename, as filenames can vary).
"""

from enum import Enum
from typing import Dict, List


class ContentType(Enum):
    """Content types for AsciiDoc modules."""
    PROCEDURE = "PROCEDURE"
    CONCEPT = "CONCEPT"
    REFERENCE = "REFERENCE"
    ASSEMBLY = "ASSEMBLY"
    SNIPPET = "SNIPPET"


# Content type rules from Modular Documentation Reference Guide
CONTENT_TYPE_RULES: Dict[str, Dict] = {
    "PROCEDURE": {
        "description": "A procedure module describes the steps required to accomplish a goal.",
        "url": "https://redhat-documentation.github.io/modular-docs/#con-creating-procedure-modules_writing-mod-docs",
        "indicators": [
            ".Procedure",
            "numbered list after .Procedure",
            ".Prerequisites",
            ".Verification",
            ".Next steps",
            "Additional resources",
        ],
        "must_have": [
            "A .Procedure block title followed by numbered steps",
        ],
        "may_have": [
            "Introductory paragraph",
            ".Prerequisites section",
            ".Verification section", 
            ".Next steps section",
            "Additional resources",
        ],
        "example": '''= Installing the component
:_mod-docs-content-type: PROCEDURE

This procedure explains how to install the component.

.Prerequisites
* You have administrator access.
* The system meets minimum requirements.

.Procedure
. Log in to the system.
. Run the installation command:
+
[source,bash]
----
./install.sh
----
. Verify the installation.

.Verification
* Check the service status.
''',
    },
    
    "CONCEPT": {
        "description": "A concept module explains what something is or why it matters.",
        "url": "https://redhat-documentation.github.io/modular-docs/#creating-concept-modules",
        "indicators": [
            "explains what/why",
            "descriptive paragraphs",
            "no .Procedure block",
            "no numbered steps",
            "educational content",
        ],
        "must_have": [
            "Explanatory/descriptive content",
        ],
        "may_have": [
            "Diagrams or images",
            "Bullet lists (not numbered procedures)",
            "Links to related concepts",
        ],
        "example": '''= Understanding data pipelines
:_mod-docs-content-type: CONCEPT

A data pipeline is a set of data processing elements connected in series.

Data pipelines are commonly used for:

* Extracting data from multiple sources
* Transforming data into a usable format
* Loading data into a target system

The key benefit of using data pipelines is automation of repetitive data processing tasks.
''',
    },
    
    "REFERENCE": {
        "description": "A reference module provides information users look up.",
        "url": "https://redhat-documentation.github.io/modular-docs/#creating-reference-modules",
        "indicators": [
            "tables with parameters",
            "configuration options",
            "API reference",
            "list of values",
            "settings/properties",
            "lookup information",
        ],
        "must_have": [
            "Reference information users look up (tables, parameter lists, etc.)",
        ],
        "may_have": [
            "Brief introductory text",
            "Links to procedures that use these parameters",
        ],
        "example": '''= Configuration parameters
:_mod-docs-content-type: REFERENCE

The following table describes the available configuration parameters.

[cols="2,3,1"]
|===
| Parameter | Description | Default

| `timeout`
| Connection timeout in seconds
| 30

| `retries`
| Number of retry attempts
| 3

| `debug`
| Enable debug logging
| false
|===
''',
    },
    
    "ASSEMBLY": {
        "description": "An assembly combines multiple modules into a cohesive document.",
        "url": "https://redhat-documentation.github.io/modular-docs/#assembly-guidelines",
        "indicators": [
            "include:: directives",
            "combines multiple modules",
            "wrapper/container document",
            "minimal own content",
        ],
        "must_have": [
            "At least one include:: directive",
        ],
        "may_have": [
            "Brief introduction",
            "Context-setting content",
            "Multiple include:: directives",
        ],
        "example": '''= Installing and configuring the component
:_mod-docs-content-type: ASSEMBLY

include::modules/concept-overview.adoc[leveloffset=+1]

include::modules/proc-prerequisites.adoc[leveloffset=+1]

include::modules/proc-installation.adoc[leveloffset=+1]

include::modules/ref-configuration.adoc[leveloffset=+1]
''',
    },
    
    "SNIPPET": {
        "description": "A snippet is a small reusable text fragment meant to be included in other files.",
        "url": "https://redhat-documentation.github.io/modular-docs/#using-text-snippets",
        "indicators": [
            "no title (= heading)",
            "small fragment",
            "meant to be included",
            "typically very short",
            "reusable text",
        ],
        "must_have": [
            "Content meant to be included elsewhere",
            "No document title",
        ],
        "may_have": [
            "Paragraphs",
            "Lists",
            "Admonitions",
        ],
        "example": '''// snippet - no title
:_mod-docs-content-type: SNIPPET

[IMPORTANT]
====
Before proceeding, ensure you have backed up your data.
====
''',
    },
}


def get_content_type_indicators(content_type: ContentType) -> List[str]:
    """
    Get the indicators for a content type.
    
    Args:
        content_type: The content type to get indicators for.
        
    Returns:
        List of indicator strings.
    """
    rules = CONTENT_TYPE_RULES.get(content_type.value, {})
    return rules.get("indicators", [])


def get_content_type_rules_text() -> str:
    """
    Get a formatted text representation of all content type rules.
    
    Useful for including in LLM prompts.
    
    Returns:
        Formatted string with all rules.
    """
    lines = []
    
    for type_name, rules in CONTENT_TYPE_RULES.items():
        lines.append(f"\n{type_name}:")
        lines.append(f"  Description: {rules['description']}")
        lines.append(f"  Indicators: {', '.join(rules['indicators'][:3])}")
        if rules.get('must_have'):
            lines.append(f"  Must have: {rules['must_have'][0]}")
    
    return "\n".join(lines)


def detect_content_type_heuristic(content: str) -> ContentType:
    """
    Simple heuristic-based content type detection.
    
    This is a fallback when LLM is not available.
    For production, always prefer LLM-based detection.
    
    Args:
        content: File content.
        
    Returns:
        Best guess content type.
    """
    content_lower = content.lower()
    
    # Check for assembly (include directives)
    if "include::" in content:
        return ContentType.ASSEMBLY
    
    # Check for procedure (.Procedure block)
    if ".procedure" in content_lower:
        return ContentType.PROCEDURE
    
    # Check for reference (tables)
    if "|===" in content or "[cols=" in content_lower:
        return ContentType.REFERENCE
    
    # Check for snippet (no title)
    lines = content.strip().split("\n")
    has_title = any(line.startswith("= ") for line in lines[:5])
    if not has_title and len(content) < 500:
        return ContentType.SNIPPET
    
    # Default to concept
    return ContentType.CONCEPT
