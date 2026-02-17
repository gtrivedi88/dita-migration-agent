---
name: vale-fix
description: "Run vale linting on AsciiDoc files and fix all AsciiDocDITA and RedHat violations. Auto-fixes DITA structure, grammar, callouts, content types, and more. Creates manual-review.md for ambiguous cases. Usage: /vale-fix <path-to-project-files> [--severity error|warning|all]"
---

# vale-fix

Fix all vale violations in AsciiDoc documentation files. This skill runs vale,
parses violations, applies deterministic fixes, and routes ambiguous issues to
a manual-review.md file.

Works with any AsciiDoc project that has a `.vale.ini` configured to use
AsciiDocDITA and/or RedHat styles.

## Usage

The argument is a path to the target project's files — a single file, a
directory, or multiple paths. Can be absolute or relative.

```
/vale-fix ../my-project/assemblies/assembly_getting-started.adoc
/vale-fix ../my-project/topics/administration_guide/
/vale-fix ../my-project/assemblies/ ../my-project/topics/
/vale-fix ../my-project/ --severity error
```

**Recommended approach**: Fix one assembly at a time. This keeps changes
reviewable and limits blast radius.

## What This Skill Does

### Step 0: Find Project Root

Determine the project root directory by walking up from the target path until
you find a `.vale.ini` file. Stop at the FIRST `.vale.ini` found (closest
parent). All vale commands must be run from this directory.

```bash
# Example: if target is ../my-project/topics/admin/proc_install.adoc
# Walk up to find: ../my-project/.vale.ini
# Project root = ../my-project/
```

**If no `.vale.ini` is found**: Report an error and stop. Vale requires a
configuration file. Tell the user to run `setup.sh` first.

**Excluded directories**: Files in `snippets/` and `common/` are excluded from
vale by the `.vale.ini` configuration. If the target path is entirely within
these directories, vale will find zero violations — this is expected.

### Step 1: Read Guidelines

Read these guideline files from the skill directory before doing anything:

1. `dita-rules.md` — Fix instructions for all 31 AsciiDocDITA rules
2. `redhat-rules.md` — Fix instructions for all RedHat style rules
3. `decision-guide.md` — Decision trees for ambiguous cases + manual review routing

### Step 2: Gather Context

Before fixing any file, gather full context:

1. **Content type**: Read the `:_mod-docs-content-type:` attribute (PROCEDURE, CONCEPT, REFERENCE, ASSEMBLY, SNIPPET)
   - If MISSING: auto-detect from file content and prefix, then add the attribute (this is one of the fixes)
2. **File type**: Determine from path and prefix:
   - `assembly_*` in `assemblies/` → assembly
   - `proc_*` in `topics/` → procedure topic
   - `con_*` in `topics/` → concept topic
   - `ref_*` in `topics/` → reference topic
   - `snip_*` in `snippets/` → snippet (excluded from vale)
3. **File role**: Understand what guide the file belongs to (by directory path)
4. **Cross-references**: Note any xref/include dependencies

### Step 3: Run Vale

Run vale with JSON output from the project root:

```bash
cd <project-root>
vale --output=JSON <target-path> 2>/dev/null
```

If `--severity all` is passed, also include suggestions:
```bash
vale --output=JSON --minAlertLevel=suggestion <target-path> 2>/dev/null
```

Default: only errors and warnings are reported (`.vale.ini` sets `MinAlertLevel = warning`).

Parse the JSON output into structured issues:
```json
{
  "file.adoc": [
    {
      "Line": 42,
      "Check": "AsciiDocDITA.CalloutList",
      "Severity": "warning",
      "Message": "Callouts are not supported in DITA.",
      "Span": [1, 3]
    }
  ]
}
```

**If vale returns an empty JSON object `{}`**: Report "All clear — no
violations found" and exit. Do not create manual-review.md.

**If vale fails to run** (non-zero exit, no JSON output): Report the error
and stop. Do not proceed without valid vale output.

### Step 4: Process Each File

For each file with violations:

1. Read the file content
2. Determine content type from `:_mod-docs-content-type:` header
3. **Process issues in this order** (prevents cascading violations):
   a. Content type fixes FIRST (ContentType, BlockTitle misclassification)
   b. Structural fixes SECOND (NestedSection, TaskSection, ExampleBlock)
   c. Content fixes THIRD (CalloutList, EntityReference, LineBreak, PageBreak)
   d. Style fixes LAST (RedHat substitutions, grammar, punctuation)
4. Within each category, sort by line number DESCENDING (fix bottom-up to preserve line numbers)
5. For each issue:
   a. Look up the rule: `AsciiDocDITA.*` → dita-rules.md, `RedHat.*` → redhat-rules.md
   b. Determine if fix is DETERMINISTIC or AMBIGUOUS using decision-guide.md
   c. If DETERMINISTIC: apply the fix using Edit tool
   d. If AMBIGUOUS: add to manual-review list with context and options
6. After fixing each file, re-run vale on THAT FILE alone to catch cascading violations
   - If new violations appear, fix them following the same process
   - Maximum 3 re-run iterations per file — if violations persist, route remaining to manual review
7. NEVER modify content that vale did not flag
8. NEVER make stylistic changes beyond what the specific rule requires
9. NEVER change xref targets, link URLs, or attribute names unless the rule specifically requires it

### What Gets Fixed

The skill auto-fixes these categories:

**a. DITA structural issues** (AsciiDocDITA rules):
- Missing `[role="_abstract"]` (ShortDescription)
- Unsupported block titles (BlockTitle)
- Nested example blocks (ExampleBlock)
- Entity references like `&nbsp;` (EntityReference)
- Hard line breaks (LineBreak)
- Page breaks (PageBreak)
- And 25+ more structural rules

**b. Grammar and terminology** (RedHat rules):
- Case-sensitive terms: "Openshift" → "OpenShift"
- Hyphenation: "on premises" → "on-premises"
- Conscious language: "blacklist" → "blocklist"
- Repeated words: "the the" → "the"
- Heading punctuation: remove trailing periods
- Abbreviation periods: "I.B.M." → "IBM"
- And more terminology corrections

**c. Callout conversion** (AsciiDocDITA.CalloutList):
- Code block callouts (`<1>`, `<2>`) → DITA-compatible definition lists

**d. Content type** (AsciiDocDITA.ContentType):
- Missing `:_mod-docs-content-type:` attribute → auto-detect and add
- Detects PROCEDURE (has `.Procedure` + numbered steps), CONCEPT (explains what/why),
  REFERENCE (lookup tables), ASSEMBLY (groups topics via includes)

**e. All other vale violations** as documented in dita-rules.md and redhat-rules.md

### Step 5: Final Verification

After all files are processed:

1. Re-run `vale --output=JSON` on ALL modified files together
2. Compare against the original violations:
   - Original violations resolved → confirmed
   - New violations introduced → revert the responsible fix and route to manual review
   - Remaining violations → should only be items already in manual review
3. If any auto-fix caused a regression in a DIFFERENT file (cross-file cascade),
   revert both fixes and route to manual review together

### Step 6: Generate Manual Review

If any issues were routed to manual review, create `manual-review.md` in the
project root directory:

```markdown
# Manual Review Required

Generated by `/vale-fix` on YYYY-MM-DD

## Summary

- **Auto-fixed**: X issues across Y files
- **Manual review**: Z issues across W files
- **Verification**: All auto-fixes confirmed clean by re-running vale

## Issues Requiring Manual Review

### path/to/file.adoc

#### Line 42: AsciiDocDITA.AssemblyContents (WARNING)

**Message**: Content other than additional resources cannot follow include directives.

**Context**:
```
41  include::topics/proc_example.adoc[leveloffset=+1]
42  >>> This paragraph appears after includes.
43
```

**Why manual review**: Multiple valid fix approaches exist.

**Options**:
1. Delete the transitional text if not needed
2. Move substantial content to a new concept module
3. Merge links into .Additional resources section
```

### Step 7: Report Results

Print a summary:
```
vale-fix complete:
  Project: <project-root>
  Files scanned: N
  Issues found: N
  Auto-fixed: N
  Manual review: N (see manual-review.md)
  Verification: PASS (no regressions)
```

## Critical Rules

### NEVER do these:
- NEVER modify files that have zero vale violations
- NEVER add `[discrete]` to headings — triggers DiscreteHeading warning
- NEVER change content that wasn't flagged by vale
- NEVER guess at fixes — if unsure, route to manual review
- NEVER change xref IDs, include paths, or attribute references unless the SPECIFIC vale rule requires it
- NEVER rewrite prose for "style" — only fix what vale flagged
- NEVER change capitalization of attribute names like `{kubernetes}`, `{prod-short}`, etc.
- NEVER delete links, URLs, or Additional resources sections unless vale explicitly flags them
- NEVER escape URLs in code blocks

### ALWAYS do these:
- ALWAYS read the file before modifying it
- ALWAYS check content type before deciding on a fix
- ALWAYS re-run vale after fixes to verify no regressions
- ALWAYS route to manual review when multiple valid approaches exist
- ALWAYS preserve ifdef/endif conditional blocks
- ALWAYS preserve include:: directives unchanged
- ALWAYS use the Edit tool for modifications (never Write entire files)

## Error Handling

- **Vale not installed**: Report error, tell user to run `setup.sh`
- **No `.vale.ini` found**: Report error, tell user to run `setup.sh`
- **Vale crashes or returns invalid JSON**: Report the error, stop processing
- **File unreadable**: Skip the file, add to manual review with "File unreadable" note
- **Edit tool fails**: Do not retry with Write tool. Route that fix to manual review
- **Zero violations**: Report "All clear" and exit cleanly (no manual-review.md)

## Quality Checklist

Before completing:
- [ ] All guideline files read (dita-rules.md, redhat-rules.md, decision-guide.md)
- [ ] Project root found (directory containing .vale.ini)
- [ ] Vale run with JSON output, results parsed correctly
- [ ] Each file's content type determined before fixing
- [ ] Fixes applied in correct order: content type → structural → content → style
- [ ] Within each category, fixes applied bottom-up (descending line order)
- [ ] No modifications to unflagged content
- [ ] No modifications to protected elements (xrefs, includes, attributes, code blocks, IDs, URLs)
- [ ] Vale re-run on all modified files — zero regressions
- [ ] manual-review.md generated for all ambiguous issues
- [ ] Summary printed with counts
