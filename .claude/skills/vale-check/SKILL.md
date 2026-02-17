---
name: vale-check
description: Run vale linting on AsciiDoc files and report all violations without making changes. Shows a structured summary grouped by severity, rule, and file.
argument-hint: <path-to-project-files> [--severity error|warning|all]
context: fork
allowed-tools: Read, Glob, Grep, Bash
---

# vale-check

Run vale and report all violations without modifying any files. Use this to
audit the current state of documentation before deciding what to fix.

Works with any AsciiDoc project that has a `.vale.ini` configured to use
AsciiDocDITA and/or RedHat styles.

## Usage

```
/vale-check ../my-project/topics/administration_guide/
/vale-check ../my-project/assemblies/
/vale-check ../my-project/topics/proc_installing.adoc
/vale-check ../my-project/ --severity error
```

## What This Skill Does

### Step 0: Find Project Root

Determine the project root directory by walking up from the target path until
you find a `.vale.ini` file. All vale commands must be run from this directory.

### Step 1: Run Vale

```bash
cd <project-root>
vale --output=JSON <target-path> 2>/dev/null
```

If `--severity error` is passed, filter results to error-level only.
If `--severity all` is passed, include suggestions (vale's MinAlertLevel is warning by default).
Default: show errors and warnings.

### Step 2: Parse and Classify

Parse the JSON output and classify each violation:

1. **Style**: `AsciiDocDITA` or `RedHat`
2. **Rule**: The specific rule name
3. **Severity**: error / warning / suggestion
4. **Fixability**: Whether `/vale-fix` can auto-fix this
   - AUTO: Deterministic fix available
   - MANUAL: Requires human judgment
   - SKIP: Informational only (suggestions)

### Step 3: Report

Print a structured report:

```
vale-check: <project-root>/topics/administration_guide/

ERRORS (must fix):
  AsciiDocDITA.NestedSection — 2 files, 3 issues [AUTO/MANUAL]
  RedHat.TermsErrors — 1 file, 5 issues [AUTO]

WARNINGS (should fix):
  AsciiDocDITA.CalloutList — 3 files, 8 issues [AUTO]
  AsciiDocDITA.ShortDescription — 1 file, 1 issue [AUTO]
  RedHat.CaseSensitiveTerms — 4 files, 12 issues [AUTO]
  RedHat.Hyphens — 2 files, 3 issues [AUTO]

TOTAL: 32 issues (8 errors, 24 warnings) across 11 files
  Auto-fixable: 28 (run /vale-fix to apply)
  Manual review: 4
```

### Step 4: Detail View

For each issue, show the file, line, and context:

```
topics/administration_guide/con_example.adoc:
  Line 15: AsciiDocDITA.NestedSection (ERROR)
    "Level 2, 3, 4, and 5 sections are not supported in DITA."
    >>> === Nested Heading
    Fix: Convert to bold *Nested Heading* or flatten to ==

  Line 42: RedHat.CaseSensitiveTerms (WARNING)
    "Use 'OpenShift' rather than 'Openshift'."
    >>> Deploy Openshift on your cluster.
    Fix: Auto-fixable — replace Openshift → OpenShift
```

## Rules

- NEVER modify any files
- NEVER run fixes — this is read-only
- Show all violations with their fixability status
- Group by severity, then by rule
- Include file paths relative to project root
