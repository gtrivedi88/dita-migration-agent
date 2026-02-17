---
name: validate-refs
description: Validate cross-references, includes, images, and duplicate IDs in an AsciiDoc documentation project. Reports broken xrefs, missing includes, missing images, and duplicate IDs.
argument-hint: <path-to-project> [--fix]
context: fork
allowed-tools: Read, Glob, Grep, Bash, Edit, Write, AskUserQuestion
---

# validate-refs

Validate all cross-references, includes, images, and IDs in the documentation.
Works with any AsciiDoc project that follows the Red Hat modular documentation
structure (assemblies/, topics/, snippets/).

## Usage

```
/validate-refs ../my-project/
/validate-refs ../my-project/ --fix
```

## What This Skill Does

### Step 1: Determine Project Root

The argument should be the project root directory (the one containing
`assemblies/`, `topics/`, etc.).

### Step 2: Run Validation

If the project has a `scripts/validate-refs.py` script, run it:

```bash
cd <project-root>
python3 scripts/validate-refs.py
```

If no validation script exists, perform manual validation by scanning all
`.adoc` files for:

1. **Broken xrefs** — every `xref:ID_{context}[]` must have a matching `[id="ID_{context}"]` in some file
2. **Missing includes** — every `include::path[]` must resolve to an existing file
3. **Missing images** — every `image::path[]` must resolve to a file under `images/`
4. **Duplicate IDs** — no two files should declare the same `[id="..."]`

### Step 3: Report Results

Print a structured report of all issues found.

### Step 4: Fix (if --fix passed)

For fixable issues:

**Broken xrefs**:
1. Read the target file to find the actual `[id="..."]`
2. If ID exists but doesn't match: fix the xref to match the actual ID
3. If target file doesn't exist: route to manual review

**Missing includes**:
1. Check if file was renamed (search for similar filenames)
2. If found: fix the include path
3. If not found: route to manual review

**Missing images**:
1. Search for the image in other directories
2. If found: fix the path
3. If not found: route to manual review

**Duplicate IDs**:
1. Always route to manual review — need to determine which file should keep the ID

### Step 5: Generate Manual Review

If any issues can't be auto-fixed, add them to `manual-review.md` in the
project root.

## ID Naming Caveats

Some files have IDs that don't include the filename prefix. The `[id="..."]` in
the file is canonical — xrefs must match it exactly.

ALWAYS read the target file to verify the actual ID before fixing an xref.

## Rules

- Never guess at IDs — always read the target file
- Never modify IDs without checking all referencing xrefs
- Route duplicate IDs to manual review (never auto-resolve)
