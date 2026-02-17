# Decision Guide — Fix Routing and Manual Review

This file contains decision trees for ambiguous cases and manual review routing.
Read this file at the start of every `/vale-fix` invocation.

---

## Core Principle: When In Doubt, Route to Manual Review

The goal is USER TRUST. A wrong auto-fix is worse than no fix. If ANY of these
conditions are true, route to manual-review.md:

1. Multiple valid fix approaches exist
2. Fix requires understanding surrounding content structure
3. Fix might break cross-references, includes, or builds
4. Fix changes the semantic meaning of the content
5. You are not 100% certain the fix is correct

---

## Decision Tree 1: Content Type Classification

When `AsciiDocDITA.ContentType` fires (missing `:_mod-docs-content-type:`):

**Priority order** — check in this order, use the FIRST match:

```
1. Is the file a reusable fragment (`snip_` prefix, in snippets/)?
   ├── YES → SNIPPET (stop here, snippets are excluded from vale)
   └── NO → Continue

2. Does the file have a `.Procedure` section with numbered steps (`. Step`)?
   ├── YES → PROCEDURE
   │   └── Does it also have `==` subsections?
   │       ├── YES → PROCEDURE (TaskSection will fire separately — don't fix headings here)
   │       └── NO → PROCEDURE ✓
   └── NO → Continue

3. Does the file have `include::` directives and `assembly_` prefix?
   ├── YES → ASSEMBLY
   └── NO → Continue

4. Does the file contain data tables, parameter lists, or lookup info?
   ├── YES → REFERENCE
   └── NO → Continue

5. Does the file explain what/why without actionable steps?
   ├── YES → CONCEPT
   └── NO → MANUAL REVIEW (content type unclear)
```

**Auto-fix when**: Classification is unambiguous (one clear match).
**Manual review when**: Content mixes types (e.g., has both `.Procedure` and
data tables), or none of the checks match.

**If `:_mod-docs-content-type:` exists but is WRONG** (e.g., says CONCEPT but
file has `.Procedure` with numbered steps): Route to manual review — changing
content type may require restructuring the file.

---

## Decision Tree 2: BlockTitle Fix Selection

When `AsciiDocDITA.BlockTitle` fires:

```
What is the file's content type?
│
├── PROCEDURE
│   └── Is the title in the allowed list?
│       ├── YES (exact match) → Should not fire. Verify vale config.
│       ├── CLOSE MATCH (.Pre-requisites → .Prerequisites) → Auto-fix: rename
│       └── NO MATCH (.Custom title) → Auto-fix: convert to bold *Custom title:*
│
├── CONCEPT or REFERENCE
│   └── Is the title a procedure marker? (.Prerequisites, .Procedure, .Verification)
│       ├── YES → MANUAL REVIEW: File may be misclassified
│       │   Options:
│       │   1. Change content type to PROCEDURE
│       │   2. Remove procedure markers and restructure
│       └── NO (.Custom title) → Auto-fix: convert to bold *Custom title:*
│
├── ASSEMBLY
│   └── Is the title .Next step or .Next steps?
│       ├── YES → MANUAL REVIEW: Merge into .Additional resources
│       └── NO → Auto-fix: convert to bold or remove
│
└── UNKNOWN (no content type set)
    └── → MANUAL REVIEW: Set content type first
```

---

## Decision Tree 3: NestedSection Fix Selection

When `AsciiDocDITA.NestedSection` fires:

```
What is the heading level?
│
├── === (level 2)
│   └── What is the content type?
│       ├── CONCEPT/REFERENCE → Auto-fix: flatten to == OR convert to *bold*
│       │   └── Would flattening create >5 sections at == level?
│       │       ├── YES → Convert to bold *Heading*
│       │       └── NO → Flatten to ==
│       ├── PROCEDURE → MANUAL REVIEW (all headings forbidden)
│       └── ASSEMBLY → MANUAL REVIEW
│
├── ==== (level 3) or deeper
│   └── MANUAL REVIEW always (requires structural analysis)
│       Options:
│       1. Flatten hierarchy (remove one = level)
│       2. Convert to bold text
│       3. Split into separate topic files
│
└── Any level in PROCEDURE
    └── MANUAL REVIEW: Convert to bold or split file
```

---

## Decision Tree 4: Callout Conversion

When `AsciiDocDITA.CalloutList` fires:

```
Is the callout inside a code block?
│
├── YES
│   └── How many callouts?
│       ├── 1-5 callouts → Auto-fix:
│       │   1. Remove `# <N>` or `// <N>` from code lines
│       │   2. Identify the code token being annotated
│       │   3. Convert <N> list to definition list: `token:: description`
│       └── >5 callouts → MANUAL REVIEW (complex restructuring)
│
├── NO (standalone callout list)
│   └── MANUAL REVIEW: Need to understand what the callouts reference
│
└── Callout spans multiple code blocks
    └── MANUAL REVIEW: Complex restructuring needed
```

**Callout conversion example**:
```
BEFORE:
[source,yaml]
----
apiVersion: v1           # <1>
kind: ConfigMap           # <2>
metadata:
  name: my-config         # <3>
----
<1> API version for the resource
<2> Resource type
<3> Name of the ConfigMap

AFTER:
[source,yaml]
----
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
----

apiVersion:: API version for the resource
kind:: Resource type
name:: Name of the ConfigMap
```

---

## Decision Tree 5: ShortDescription (Abstract) Fix

When `AsciiDocDITA.ShortDescription` fires:

```
Is there a paragraph immediately after the title?
│
├── YES (clear paragraph text)
│   └── Is it a complete sentence (not a list, code, or admonition)?
│       ├── YES → Auto-fix: add [role="_abstract"] before the paragraph
│       └── NO → MANUAL REVIEW: Need to write an abstract paragraph
│
├── NO (file starts with a list, code block, ifdef, or section heading)
│   └── MANUAL REVIEW: Need to write an abstract paragraph
│
└── File is a SNIPPET
    └── SKIP: Snippets don't need abstracts
```

**NEVER**: Rewrite the abstract text. Only add the `[role="_abstract"]` marker.
**NEVER**: Add a second `[role="_abstract"]` if one already exists.

---

## Decision Tree 6: Entity Reference Fix

When `AsciiDocDITA.EntityReference` fires:

```
Is the entity in the known replacement table?
│
├── YES → Auto-fix using the table in dita-rules.md
│   &nbsp; → {nbsp}
│   &mdash; → --
│   &ndash; → {ndash}
│   &copy; → (C)
│   &reg; → (R)
│   &trade; → (TM)
│   &hellip; → ...
│   &rarr; → ->
│   &larr; → <-
│
├── NO (unknown entity)
│   └── MANUAL REVIEW: Need to determine correct AsciiDoc replacement
│
└── Entity is inside a code block or passthrough
    └── SKIP: Entities in code blocks are literal text
```

---

## Decision Tree 7: RedHat Substitution Rules

When any RedHat substitution rule fires (CaseSensitiveTerms, Hyphens,
TermsErrors, TermsWarnings, ConsciousLanguage):

```
Can the message be parsed as "Use 'X' rather than 'Y'"?
│
├── YES
│   └── Is the original term found on the flagged line?
│       ├── YES
│       │   └── Is the term inside a code block, attribute, or ID?
│       │       ├── YES → SKIP (don't modify code/attributes/IDs)
│       │       └── NO → Auto-fix: replace first occurrence on flagged line
│       └── NO → MANUAL REVIEW: Term not found on reported line
│
├── NO (custom message format, like DoNotUseTerms)
│   └── MANUAL REVIEW: Custom messages need human judgment
│
└── Replacement has multiple options (separated by |)
    └── Auto-fix: use the FIRST option
        Exception: master/slave → MANUAL REVIEW (context-dependent)
```

---

## Decision Tree 8: ConsciousLanguage Special Cases

When `RedHat.ConsciousLanguage` fires for `master` or `slave`:

```
What is the context?
│
├── "master branch" → Auto-fix: "main branch" or "primary branch"
├── "master node" → Auto-fix: "control plane node"
├── "master/slave" architecture → MANUAL REVIEW (multiple valid options)
├── "master" in product name → SKIP (proper noun, e.g., "Jenkins master")
│
├── "slave" → MANUAL REVIEW always (replacement depends on context):
│   Options: secondary, replica, worker, consumer, responder
│
└── "master" in other contexts → MANUAL REVIEW
    Options: primary, source, controller, host, director
```

---

## Manual Review File Format

When routing issues to manual review, generate this file:

**Filename**: `manual-review.md`
**Location**: Same directory as the target files, or repo root if scanning multiple directories

```markdown
# Manual Review Required

Generated by `/vale-fix` on YYYY-MM-DD

## Summary

- **Files scanned**: N
- **Issues found**: N total
- **Auto-fixed**: X issues across Y files
- **Manual review needed**: Z issues across W files
- **Post-fix verification**: PASS / FAIL

---

## Auto-Fixed Issues

| File | Line | Rule | Severity | Fix Applied |
|---|---|---|---|---|
| path/file.adoc | 42 | RedHat.CaseSensitiveTerms | warning | `Openshift` → `OpenShift` |
| path/file.adoc | 15 | AsciiDocDITA.PageBreak | warning | Removed `<<<` |

---

## Issues Requiring Manual Review

### path/to/file.adoc

#### Line 42: AsciiDocDITA.AssemblyContents (WARNING)

**Vale message**: Content other than additional resources cannot follow include directives.

**Context** (>>> marks the flagged line):
```
40     include::topics/proc_example.adoc[leveloffset=+1]
41
42 >>> This paragraph appears after includes.
43
44     [role="_additional-resources"]
```

**Why manual review**: Multiple valid fix approaches exist.

**Recommended options**:
1. Delete the transitional text if it's not adding value
2. Move substantial content to a new concept module
3. If it's a misnamed heading, merge into `.Additional resources`

---
```

## Rules for Manual Review Entries

1. ALWAYS include the vale message verbatim
2. ALWAYS include 3-5 lines of context around the issue
3. ALWAYS explain WHY it needs manual review
4. ALWAYS provide numbered options for how to fix
5. ALWAYS list the file path relative to the repo root
6. NEVER include fixes you already applied (those go in the auto-fixed table)
7. Group issues by file for readability

---

## Multiple Rules on the Same Line

When multiple vale rules flag the same line:

1. **Independent fixes** (e.g., CaseSensitiveTerms + Hyphens on different words):
   Apply both fixes. They don't interact.

2. **Overlapping fixes** (e.g., two rules flag the same word):
   Apply the higher-severity fix first. If both are the same severity, apply
   the more specific rule (AsciiDocDITA before RedHat).

3. **Conflicting fixes** (e.g., one rule says change X, another says keep X):
   Route both to manual review.

## Interactions Between Rules

Some fixes can trigger other rules. Watch for these chains:

| If You Fix | Watch Out For |
|---|---|
| NestedSection (flatten `===` → `==`) | TaskSection may fire if file is PROCEDURE |
| BlockTitle (add `.Procedure`) | TaskStep may fire if content after it isn't a list |
| DiscreteHeading (remove `[discrete]`, add bold) | BlockTitle may fire on the bold text |
| ContentType (set to PROCEDURE) | TaskContents, TaskStep, TaskSection may fire |
| SidebarBlock (convert to NOTE) | AdmonitionTitle may fire if titled |

**Prevention**: Process files in this order:
1. Content type fixes FIRST (ContentType, BlockTitle misclassification)
2. Structural fixes SECOND (NestedSection, TaskSection)
3. Content fixes THIRD (CalloutList, EntityReference, LineBreak)
4. Style fixes LAST (RedHat substitutions, spelling, punctuation)

**After fixing, re-run vale** to catch cascading issues.
- Maximum 3 re-run iterations per file
- If violations persist after 3 iterations, route remaining to manual review
- This prevents infinite loops from circular rule interactions

---

## Scope Guard: What NOT to Touch

These elements must NEVER be modified, even if they appear near a vale violation:

1. **xref targets**: `xref:some-id_{context}[]` — IDs are case-sensitive
2. **include paths**: `include::topics/path/file.adoc[leveloffset=+1]`
3. **Attribute definitions**: `:attr-name: value` in attributes.adoc
4. **Attribute references**: `{kubernetes}`, `{prod-short}`, `{orch-name}`
5. **ID declarations**: `[id="prefix_name_{context}"]`
6. **Code block content**: Text between `----` or `....` delimiters
7. **URL values**: `link:https://...[]` and `image::path[]`
8. **ifdef/endif blocks**: Conditional compilation directives
9. **Passthrough content**: `pass:[]`, `++++`...`++++`

When a vale violation occurs INSIDE these elements, SKIP it (do not fix).
When a vale violation occurs ADJACENT to these elements (on the same line or
sharing the same syntax construct), fix only the flagged text — never modify
the protected element itself. "Adjacent" means the violation is on a line that
also contains a protected element (e.g., a CaseSensitiveTerms violation on a
line with an xref — fix the term but do not touch the xref).
