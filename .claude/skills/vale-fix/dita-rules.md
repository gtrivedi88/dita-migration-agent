# AsciiDocDITA Vale Rules — Fix Reference

This file contains fix instructions for all 31 AsciiDocDITA vale rules.
Read this file at the start of every `/vale-fix` invocation.

## How to Use This File

When vale reports a violation like `AsciiDocDITA.CalloutList`, find the
`CalloutList` section below for the exact fix. Each section includes:
- **Severity**: error / warning / suggestion
- **What vale detects**: The pattern that triggers the rule
- **Fix**: Exact fix with before/after examples
- **Content-type behavior**: Whether the fix depends on the file's content type
- **Manual review**: When to route to manual-review.md instead of auto-fixing

---

## ERROR-Level Rules (Must Fix)

### NestedSection
- **Severity**: ERROR
- **Detects**: Level 2+ section headings: `===`, `====`, `=====`, `======`
- **Does NOT detect**: `==` (level 1 sections are allowed in CONCEPT/REFERENCE)
- **Message**: "Level 2, 3, 4, and 5 sections are not supported in DITA."

**Fix by content type**:

| Content Type | `===` (level 2) | `====` (level 3) | `=====` (level 4) |
|---|---|---|---|
| CONCEPT | Convert to `==` | Convert to bold `*text*` | → manual review (split file) |
| REFERENCE | Convert to `==` | Convert to bold `*text*` | → manual review (split file) |
| PROCEDURE | → manual review (all headings forbidden) | → manual review | → manual review |
| ASSEMBLY | → manual review | → manual review | → manual review |

**Auto-fix** (CONCEPT/REFERENCE only):
```
Before: === Subsection Title
After:  *Subsection Title*
```
Or flatten one level:
```
Before: === Subsection Title
After:  == Subsection Title
```

**NEVER**: Use `[discrete]` — triggers DiscreteHeading warning.

**Manual review when**: File is PROCEDURE/ASSEMBLY, or `====`/deeper nesting exists, or flattening would create too many `==` sections.

---

### EntityReference
- **Severity**: ERROR
- **Detects**: HTML character entities like `&nbsp;`, `&copy;`, `&mdash;`, `&reg;`, etc.
- **Allowed entities**: `&amp;`, `&lt;`, `&gt;`, `&apos;`, `&quot;`
- **Message**: "HTML character entity references are not supported in DITA."

**Auto-fix** (deterministic replacements):
| Entity | Replacement |
|---|---|
| `&nbsp;` | `{nbsp}` |
| `&mdash;` | `--` or `{mdash}` |
| `&ndash;` | `{ndash}` |
| `&copy;` | `(C)` or `{copy}` |
| `&reg;` | `(R)` or `{reg}` |
| `&trade;` | `(TM)` or `{trade}` |
| `&hellip;` | `\...` or `{ellipsis}` |
| `&rarr;` | `\->` or `{rarr}` |
| `&larr;` | `<-` or `{larr}` |

**Manual review when**: Entity is not in the table above.

---

### ExampleBlock
- **Severity**: ERROR
- **Detects**: Example blocks (`====`) nested inside other blocks
- **Message**: "Examples can not be inside of other blocks in DITA."

**Manual review always**: Restructuring nested example blocks requires understanding the surrounding content structure. Add to manual-review.md with the full context.

---

### MismatchedId
- **Severity**: ERROR
- **Detects**: ID attributes with mismatched quotes: `[id="text']`, `[id='text"]`, `[id=text"]`, `[id="text]`
- **Message**: "The quotes in the ID are mismatched."

**Auto-fix** (always deterministic):
```
Before: [id='my-section_{context}"]
After:  [id="my-section_{context}"]

Before: [id=my-section_{context}"]
After:  [id="my-section_{context}"]
```
Always normalize to double quotes.

---

### TaskExample
- **Severity**: ERROR
- **Detects**: Multiple example blocks in a PROCEDURE file
- **Message**: "Examples are allowed only once in DITA tasks."

**Manual review always**: Combining or restructuring multiple examples requires understanding the content. Route to manual-review.md.

---

### TaskSection
- **Severity**: ERROR
- **Detects**: `==` section headings inside PROCEDURE files
- **Message**: "Sections are not allowed in DITA tasks."
- **Only applies to**: PROCEDURE content type

**Fix options** (route to manual review with these options):
1. Convert `== Heading` to bold text `*Heading*`
2. Convert to description list term
3. Split into separate procedure files

**Manual review always**: The correct approach depends on the content structure.

---

## WARNING-Level Rules (Should Fix)

### AdmonitionTitle
- **Severity**: WARNING
- **Detects**: Block title (`.Title`) immediately before `[NOTE]`, `[TIP]`, `[IMPORTANT]`, `[WARNING]`, `[CAUTION]`
- **Message**: "Admonition titles are not supported in DITA."

**Auto-fix**:
```
Before:
.Important warning
[WARNING]
====
Be careful with this operation.
====

After:
[WARNING]
====
*Important warning:* Be careful with this operation.
====
```
Move the title text into the admonition body as bold text.

---

### AssemblyContents
- **Severity**: WARNING
- **Detects**: Content (other than "Additional resources") after `include::` directives in ASSEMBLY files
- **Message**: "Content other than additional resources cannot follow include directives."

**Manual review always**: Multiple valid approaches exist. Route to manual-review.md with these options:
1. DELETE if transitional text ("The following sections describe...")
2. MOVE to a new concept module if substantial content
3. MERGE links into `.Additional resources` section if misnamed heading (.Next step)
4. FIX capitalization if `.Additional Resources` (capital R) → `.Additional resources`

---

### AuthorLine
- **Severity**: WARNING
- **Detects**: Non-empty line after document title that looks like author attribution
- **Message**: "Author lines are not supported for topics."

**Auto-fix**: Delete the author line.

---

### BlockTitle
- **Severity**: WARNING
- **Detects**: Block titles (`.Title`) on unsupported elements
- **Message**: "Block titles can only be assigned to examples, figures, and tables in DITA."

**CRITICAL**: This rule is CONTENT-TYPE AWARE.

**PROCEDURE files — these block titles are ALLOWED (vale skips them)**:
- `.Prerequisites`, `.Prerequisite`
- `.Procedure`
- `.Verification`
- `.Result`, `.Results`
- `.Troubleshooting`, `.Troubleshooting step`, `.Troubleshooting steps`
- `.Next steps`, `.Next step`
- `.Additional resources`

**ALL files — this is ALWAYS allowed**:
- `.Additional resources`

**If BlockTitle fires in a PROCEDURE**: The title doesn't match the allowed list exactly. Check spelling/case.

**If BlockTitle fires in a CONCEPT/REFERENCE**:
- `.Prerequisites` / `.Procedure` → file may be misclassified. Check if it has numbered steps → should be PROCEDURE. Route to manual review.
- Other titles (`.Custom title`) → auto-fix: convert to bold `*Custom title:*`

**If BlockTitle fires in an ASSEMBLY**:
- `.Next step` / `.Next steps` → merge into `.Additional resources`
- Other titles → convert to bold or remove

**Auto-fix** (when deterministic):
```
Before: .Custom paragraph title
After:  *Custom paragraph title:*
```

**NEVER**: Add `[discrete]` — triggers DiscreteHeading.
**NEVER**: Convert to `==` heading in PROCEDURE — triggers TaskSection.

---

### CalloutList
- **Severity**: WARNING
- **Detects**: Callout markers `<1>`, `<2>`, `<3>` at line start
- **Message**: "Callouts are not supported in DITA."

**Auto-fix** (deterministic conversion to description list):

```
Before:
----
command --option value # <1>
command --flag         # <2>
----
<1> Description of option
<2> Description of flag

After:
----
command --option value
command --flag
----

option:: Description of option
flag:: Description of flag
```

Steps:
1. Remove `# <N>` or `// <N>` markers from inside the code block
2. Convert `<N> Description` list items to `term:: Description` definition list
3. Use the code token being annotated as the definition list term

**Manual review when**: Callout references span multiple code blocks or have complex nesting.

---

### ContentType
- **Severity**: WARNING
- **Detects**: Missing `:_mod-docs-content-type:` attribute
- **Message**: "The '_mod-docs-content-type' attribute definition is missing."

**Auto-fix** (based on file analysis):
1. Read the file content
2. Classify using decision-guide.md rules:
   - Has `.Procedure` + numbered steps → PROCEDURE
   - Has `include::` directives + `assembly_` prefix → ASSEMBLY
   - Has data tables, lists, lookup info → REFERENCE
   - Explains what/why with no steps → CONCEPT
   - Is a reusable fragment → SNIPPET
3. Add `:_mod-docs-content-type: TYPE` as the first line

**Manual review when**: Content mixes types (e.g., concept with embedded steps).

---

### DiscreteHeading
- **Severity**: WARNING
- **Detects**: `[discrete]` block attribute
- **Message**: "Discrete headings are not supported in DITA."

**Auto-fix**:
```
Before:
[discrete]
== Some Heading

After:
*Some Heading*
```
Remove `[discrete]` and convert the heading to bold text.

---

### DocumentId
- **Severity**: WARNING
- **Detects**: Level 0 heading (`= Title`) without preceding `[id="..."]`
- **Message**: "The document id assigned to the level 0 heading is missing."

**Auto-fix** (derive ID from filename):
```
Before:
= Installing Dev Spaces

After:
[id="proc_installing-dev-spaces_{context}"]
= Installing Dev Spaces
```
- Use the filename (without `.adoc`) as the ID base
- Append `_{context}` suffix
- Prefix matches the file prefix (`proc_`, `con_`, `ref_`, `assembly_`)

**Manual review when**: File has no clear naming convention or is in an unexpected location.

---

### DocumentTitle
- **Severity**: WARNING
- **Detects**: No level 0 heading (`= Title`) in the file
- **Message**: "The document title (a level 0 heading) is missing."

**Manual review always**: Adding a title requires understanding the content to write an appropriate heading.

---

### EquationFormula
- **Severity**: WARNING
- **Detects**: `:stem:`, `[stem]`, `[asciimath]`, `[latexmath]`, `stem:`, `asciimath:`, `latexmath:`
- **Message**: "Equations and formulas are not implemented."

**Manual review always**: Mathematical notation needs domain expertise to convert.

---

### LineBreak
- **Severity**: WARNING
- **Detects**: Hard line breaks: ` +` at line end, `:hardbreaks-option:`, `%hardbreaks`
- **Message**: "Hard line breaks are not supported in DITA."

**Auto-fix**:
```
Before: First line +
        Second line

After:  First line
        Second line
```
Remove trailing ` +`. Remove `:hardbreaks-option:` or `%hardbreaks` attributes.

---

### PageBreak
- **Severity**: WARNING
- **Detects**: `<<<` page break syntax
- **Message**: "Page breaks are not supported in DITA."

**Auto-fix**: Delete the `<<<` line.

---

### RelatedLinks
- **Severity**: WARNING
- **Detects**: Non-link content in "Additional resources" sections
- **Message**: "Content other than links cannot be mapped to DITA related-links."

**Manual review always**: Need to determine if the non-link content should be converted to links, moved elsewhere, or deleted.

---

### ShortDescription
- **Severity**: WARNING
- **Detects**: No `[role="_abstract"]` paragraph after the level 0 heading
- **Message**: 'Assign [role="_abstract"] to a paragraph to use it as <shortdesc> in DITA.'

**Auto-fix** (when abstract paragraph is identifiable):
```
Before:
= Installing Dev Spaces

Install {prod-short} on your {orch-name} cluster.

After:
= Installing Dev Spaces

[role="_abstract"]
Install {prod-short} on your {orch-name} cluster.
```
Add `[role="_abstract"]` before the first paragraph after the title.

**Manual review when**: No clear abstract paragraph exists (file starts with a list, code block, or admonition).

---

### SidebarBlock
- **Severity**: WARNING
- **Detects**: `[sidebar]` or `****` delimiters
- **Message**: "Sidebars are not supported in DITA."

**Auto-fix**:
```
Before:
****
Important sidebar content.
****

After:
[NOTE]
====
Important sidebar content.
====
```
Convert to an admonition block (NOTE, TIP, etc. based on content).

---

### TableFooter
- **Severity**: WARNING
- **Detects**: `%footer` or `options=footer` in table attributes
- **Message**: "Table footers are not supported in DITA."

**Auto-fix**: Remove `%footer` or `footer` from the table options.

---

### TaskContents
- **Severity**: WARNING
- **Detects**: Missing `.Procedure` section in PROCEDURE files
- **Message**: "The '.Procedure' block title is missing."

**Auto-fix** (when ordered list exists):
Find the ordered list (`. Step one`) in the file and add `.Procedure` before it:
```
Before:
. Step one.
. Step two.

After:
.Procedure
. Step one.
. Step two.
```

**Manual review when**: No ordered list found in the file — the content type may be wrong.

---

### TaskDuplicate
- **Severity**: WARNING
- **Detects**: Duplicate section titles in PROCEDURE (two `.Prerequisites`, two `.Procedure`, etc.)
- **Message**: "Duplicate titles cannot be mapped to DITA tasks."

**Manual review always**: Need to determine which duplicate to keep, merge, or restructure.

---

### TaskStep
- **Severity**: WARNING
- **Detects**: Non-list content between `.Procedure` and the next section title
- **Message**: "Content other than a single list cannot be mapped to DITA tasks."

**Manual review always**: Need to understand whether the non-list content should be moved to prerequisites, absorbed into a step, or restructured.

---

### TaskTitle
- **Severity**: WARNING
- **Detects**: Unsupported section titles in PROCEDURE files
- **Allowed titles**: `.Prerequisites`, `.Procedure`, `.Verification`, `.Results`, `.Troubleshooting`, `.Next steps`, `.Additional resources` (and variants)
- **Message**: "Unsupported titles cannot be mapped to DITA tasks."

**Auto-fix** (rename to closest match):
| Flagged Title | Fix |
|---|---|
| `.Pre-requisites` | `.Prerequisites` |
| `.Prereqs` | `.Prerequisites` |
| `.Steps` | `.Procedure` |
| `.Verify` | `.Verification` |
| `.See also` | `.Additional resources` |
| `.Related information` | `.Additional resources` |

For unrecognized titles: convert to bold `*Title:*`

---

### ThematicBreak
- **Severity**: WARNING
- **Detects**: `'''`, `***`, `___`, `* * *`, `- - -`, `_ _ _`
- **Message**: "Thematic breaks are not supported in DITA."

**Auto-fix**: Delete the thematic break line.

---

## SUGGESTION-Level Rules (Informational)

### AttributeReference
- **Severity**: SUGGESTION
- **Detects**: Custom attribute references `{custom-name}`
- **Action**: No fix required. Informational only.

### ConditionalCode
- **Severity**: SUGGESTION
- **Detects**: `ifdef::`, `ifndef::`, `ifeval::`
- **Action**: No fix required. Informational only.

### IncludeDirective
- **Severity**: SUGGESTION
- **Detects**: `include::path[]` directives
- **Action**: No fix required. Informational only.

### TagDirective
- **Severity**: SUGGESTION
- **Detects**: `tag::name[]` directives
- **Action**: No fix required. Informational only.
