---
name: build
description: Build AsciiDoc documentation and report any errors. Supports asciidoctor HTML build and ccutil Pantheon build.
argument-hint: <path-to-project> [--html|--ccutil|--all]
context: fork
allowed-tools: Read, Bash, Glob, Grep
---

# build

Build the documentation and report any errors.

Works with any AsciiDoc project that has a build script (`build.sh`) or
standard asciidoctor setup.

## Usage

```
/build ../my-project/
/build ../my-project/ --html
/build ../my-project/ --ccutil
/build ../my-project/ --all
```

Default (no flag): runs the asciidoctor HTML build only.

## What This Skill Does

### Step 0: Determine Project Root

The argument should be the project root directory.

### HTML Build (--html or default)

Look for a build script in the project root and run it:

```bash
cd <project-root>
./build.sh          # If build.sh exists
```

If no `build.sh` exists, look for `titles/` or `master.adoc` and run
asciidoctor directly.

Output typically goes to `titles-generated/`. Report:
- Build success/failure
- Any asciidoctor warnings or errors
- Missing includes or images flagged during build

### ccutil Build (--ccutil)

```bash
cd <project-root>
bash tools/ccutil.sh    # If ccutil.sh exists
```

Requires podman. Runs the ccutil container for each guide in `pantheon/`.
Output goes to `pantheon/*/build/tmp/en-US/`.

Report:
- Build success/failure per guide
- Any ccutil-specific errors (stricter than asciidoctor)

### All Builds (--all)

Run both HTML and ccutil builds sequentially.

### Report Format

```
build complete:
  Project: <project-root>
  HTML build: PASS / FAIL
    Warnings: N
    Errors: N
  ccutil build: PASS / FAIL (or SKIPPED if --html only)
```

If build fails, show the relevant error lines from the output.

## Common Build Failures

| Error Pattern | Cause | Fix |
|---|---|---|
| `include file not found` | Broken include path | Run `/validate-refs --fix` |
| `invalid cross reference` | Broken xref | Run `/validate-refs --fix` |
| `image not found` | Missing image file | Check images/ directory |
| `invalid block style` | `[bash,...]` instead of `[source,bash]` | Fix source block syntax |
| `bold delimiters` | `*` inside backticks matching across literals | Escape: `` `\*` `` |

## Rules

- NEVER modify source files — this is a read-only build check
- Report all warnings and errors clearly
- Show file paths relative to project root
