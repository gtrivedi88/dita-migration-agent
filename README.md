# DITA Migration Agent — Claude Code Skills

**Claude Code skills for fixing DITA compatibility and Red Hat style issues in AsciiDoc documentation.** Skills run vale as the single source of truth, apply deterministic fixes, and route ambiguous cases to a manual review file.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        DITA Migration Fix Flow                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
   │  CHECK   │ ──▶ │   FIX    │ ──▶ │  VERIFY  │ ──▶ │  BUILD   │
   │  (audit) │     │  (apply) │     │  (refs)  │     │  (test)  │
   └──────────┘     └──────────┘     └──────────┘     └──────────┘
        │                │                │                │
        ▼                ▼                ▼                ▼
   Structured       Edit files       Broken xrefs     HTML / ccutil
   vale report      + manual-        Missing incl.    build output
   by severity      review.md        Dup. IDs

   ┌──────────────────────────────────────────────────────────────────────────────┐
   │  Vale is the single source of truth — only fix what vale flags              │
   │  No phantom issues — never invent problems vale didn't report               │
   │  No scope creep — fix only the specific violation, nothing else             │
   │  Manual review for ambiguity — when multiple valid fixes exist              │
   └──────────────────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [Vale](https://vale.sh/docs/install/) installed (`vale --version`)
- The target documentation repository (`devspaces-dita-migration/`) cloned alongside this repo

### Expected Directory Layout

Both repos must be siblings under the same parent directory:

```
combine/                                # Parent directory
├── dita-migration-agent/               # This repo (skills + vale styles)
│   ├── .claude/skills/                 # Claude Code skills
│   └── styles/                         # Vale styles (RedHat + AsciiDocDITA symlink)
├── devspaces-dita-migration/           # Target documentation repo
│   ├── .vale.ini                       # Points to ../dita-migration-agent/styles
│   ├── assemblies/                     # Assembly files
│   ├── topics/                         # Topic files (con_, proc_, ref_)
│   └── snippets/                       # Reusable fragments (excluded from vale)
└── asciidoctor-dita-vale/              # External vale rules (AsciiDocDITA)
    └── styles/AsciiDocDITA/            # Symlinked from dita-migration-agent/styles/
```

### Installation

```bash
# 1. Clone all three repos under the same parent directory
git clone <dita-migration-agent-url>
git clone <devspaces-dita-migration-url>
git clone <asciidoctor-dita-vale-url>

# 2. Verify vale works with the styles
cd devspaces-dita-migration
vale topics/administration_guide/con_che-architecture.adoc

# 3. Open Claude Code from the dita-migration-agent directory
cd ../dita-migration-agent
claude
```

The `.vale.ini` in `devspaces-dita-migration/` is already configured:

```ini
StylesPath = ../dita-migration-agent/styles
MinAlertLevel = warning

[*.adoc]
BasedOnStyles = AsciiDocDITA, RedHat
```

No API keys, no Python packages, no virtual environments. Claude Code provides the LLM capability.

---

## Available Skills

| Skill | Purpose | Modifies Files? |
|-------|---------|-----------------|
| `/vale-check` | Run vale, report violations (read-only audit) | No |
| `/vale-fix` | Run vale, fix violations, create manual-review.md | Yes |
| `/validate-refs` | Validate xrefs, includes, images, duplicate IDs | Optional (`--fix`) |
| `/build` | Build documentation (HTML and/or ccutil) | No |

---

## Complete Workflow

### Step 1: Audit Current State

Run a read-only check to see all violations before making any changes.

```
/vale-check topics/administration_guide/
```

**Output**: A structured report grouped by severity and rule, showing how many issues are auto-fixable vs. requiring manual review.

```
vale-check: devspaces-dita-migration/topics/administration_guide/

ERRORS (must fix):
  AsciiDocDITA.NestedSection — 2 files, 3 issues [AUTO/MANUAL]
  RedHat.TermsErrors — 1 file, 5 issues [AUTO]

WARNINGS (should fix):
  AsciiDocDITA.CalloutList — 3 files, 8 issues [AUTO]
  RedHat.CaseSensitiveTerms — 4 files, 12 issues [AUTO]

TOTAL: 28 issues (8 errors, 20 warnings) across 11 files
  Auto-fixable: 24 (run /vale-fix to apply)
  Manual review: 4
```

---

### Step 2: Fix Violations

Run the fixer on a file, directory, or the entire project.

```
/vale-fix topics/administration_guide/proc_installing-dev-spaces.adoc
/vale-fix topics/administration_guide/
/vale-fix assemblies/ topics/
```

**What happens**:

1. Reads all guideline files (66 vale rules with fix instructions)
2. Gathers context for each file (content type, file type, guide)
3. Runs `vale --output=JSON` on the target
4. Applies deterministic fixes bottom-up (descending line order)
5. Re-runs vale on every modified file to verify no regressions
6. Generates `manual-review.md` for anything that needs human judgment

**Output**:

```
vale-fix complete:
  Files scanned: 15
  Issues found: 42
  Auto-fixed: 38
  Manual review: 4 (see manual-review.md)
  Verification: PASS (no regressions)
```

The `manual-review.md` file contains the exact file, line, context, and recommended fix options for each issue that couldn't be auto-resolved.

---

### Step 3: Validate References

After fixing vale issues, verify that all cross-references, includes, and images still resolve.

```
/validate-refs
/validate-refs --fix
```

**What it checks**:

1. **Broken xrefs** — every `xref:ID_{context}[]` has a matching `[id="ID_{context}"]`
2. **Missing includes** — every `include::path[]` resolves to an existing file
3. **Missing images** — every `image::path[]` resolves to a file under `images/`
4. **Duplicate IDs** — no two files declare the same `[id="..."]`

With `--fix`, it auto-fixes broken paths where possible and routes unfixable issues to `manual-review.md`.

---

### Step 4: Build and Verify

Run the documentation build to catch any remaining issues.

```
/build              # HTML build (default)
/build --ccutil     # Pantheon ccutil build (requires podman)
/build --all        # Both HTML and ccutil
```

**Output**:

```
build complete:
  HTML build: PASS
    Warnings: 0
    Errors: 0
  ccutil build: PASS
    admin guide: PASS
    user guide: PASS
```

---

## Recommended Workflow by Scope

### Fix one file

```
/vale-check topics/administration_guide/proc_installing-dev-spaces.adoc
/vale-fix topics/administration_guide/proc_installing-dev-spaces.adoc
```

### Fix one guide directory

```
/vale-check topics/administration_guide/
/vale-fix topics/administration_guide/
/validate-refs
/build
```

### Fix the entire project

```
/vale-check .
/vale-fix assemblies/ topics/
/validate-refs --fix
/build --all
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          /vale-fix Workflow                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. READ GUIDELINES                                                         │
│     ├─ dita-rules.md (31 AsciiDocDITA rules with fix instructions)          │
│     ├─ redhat-rules.md (35 RedHat rules with fix instructions)              │
│     └─ decision-guide.md (8 decision trees + manual review routing)         │
│                                                                             │
│  2. GATHER CONTEXT                                                          │
│     ├─ Content type (:_mod-docs-content-type:)                              │
│     ├─ File type (assembly, procedure, concept, reference, snippet)         │
│     └─ Cross-reference dependencies                                         │
│                                                                             │
│  3. RUN VALE                                                                │
│     └─ vale --output=JSON [target]                                          │
│                                                                             │
│  4. PROCESS ISSUES                                                          │
│     ├─ Sort by line number DESCENDING (bottom-up to preserve line numbers)  │
│     ├─ Deterministic issues → auto-fix via Edit tool                        │
│     └─ Ambiguous issues → route to manual-review.md                         │
│                                                                             │
│  5. VERIFY                                                                  │
│     ├─ Re-run vale on every modified file                                   │
│     ├─ If fix introduced regression → revert + manual review                │
│     └─ Confirm: zero new violations from fixes                              │
│                                                                             │
│  6. OUTPUT                                                                  │
│     ├─ Summary with counts (fixed / manual / verified)                      │
│     └─ manual-review.md (file, line, context, options)                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Safety Guarantees

| Guarantee | How |
|-----------|-----|
| **No phantom fixes** | Only fix what vale flags — zero modifications to unflagged content |
| **No regressions** | Re-run vale after every fix; revert + manual review if new issues appear |
| **No guessing** | Ambiguous cases go to manual-review.md with context and options |
| **No scope creep** | Fix only the specific violation, nothing else on the line or file |
| **Protected elements** | Never modify xref IDs, include paths, attribute references, code blocks, URLs, ifdef/endif |

---

## What the Skills Fix

### AsciiDocDITA Rules (31 rules)

DITA 1.3 structural compatibility checks. These ensure AsciiDoc content can be transformed to DITA XML.

| Severity | Count | Examples |
|----------|-------|---------|
| **Error** | 6 | NestedSection, EntityReference, ExampleBlock, MismatchedId, TaskExample, TaskSection |
| **Warning** | 22 | ShortDescription, ContentType, CalloutList, BlockTitle, TaskStep, AssemblyContents |
| **Suggestion** | 3 | AttributeReference, ConditionalCode, IncludeDirective |

### RedHat Rules (35 rules)

Red Hat documentation style guide checks. These enforce terminology, capitalization, and grammar standards.

| Severity | Count | Examples |
|----------|-------|---------|
| **Error** | 5 | Abbreviations, DoNotUseTerms, MergeConflictMarkers, Spacing, TermsErrors |
| **Warning** | 10 | CaseSensitiveTerms, ConsciousLanguage, Hyphens, RepeatedWords, HeadingPunctuation |
| **Suggestion** | 20 | Contractions, PassiveVoice, OxfordComma, SimpleWords |

### Fix Strategy

| Strategy | Description | Rules |
|----------|-------------|-------|
| **Deterministic** | Parse vale message, apply replacement directly | CaseSensitiveTerms, Hyphens, RepeatedWords, Abbreviations, HeadingPunctuation |
| **Context-aware** | Read file content type and structure, then apply fix | BlockTitle, NestedSection, ShortDescription, TaskStep, ContentType |
| **Manual review** | Multiple valid approaches — route to manual-review.md | AssemblyContents, MergeConflictMarkers, TaskSection, EmDash, DoNotUseTerms |

---

## Skill Details

### `/vale-check` — Read-Only Audit

Reports all vale violations without modifying any files. Use this first to understand the scope of issues.

```
/vale-check topics/administration_guide/
/vale-check assemblies/
/vale-check . --severity error
```

**Classifies each violation**:
- **AUTO** — deterministic fix available via `/vale-fix`
- **MANUAL** — requires human judgment
- **SKIP** — informational only (suggestions)

---

### `/vale-fix` — Fix Violations

Runs vale, applies deterministic fixes, generates manual-review.md for ambiguous cases.

```
/vale-fix topics/administration_guide/proc_installing-dev-spaces.adoc
/vale-fix topics/
/vale-fix . --severity error
```

**Reference files the skill reads before fixing**:

| File | Content |
|------|---------|
| `dita-rules.md` | Fix instructions for all 31 AsciiDocDITA rules with before/after examples |
| `redhat-rules.md` | Fix instructions for all 35 RedHat rules, including message parsing patterns |
| `decision-guide.md` | 8 decision trees, scope guards, rule interaction chains, manual review format |

---

### `/validate-refs` — Reference Validation

Runs `scripts/validate-refs.py` to check xrefs, includes, images, and duplicate IDs.

```
/validate-refs
/validate-refs --fix
```

Without `--fix`: reports all issues. With `--fix`: auto-fixes where possible, routes others to manual review.

---

### `/build` — Build Verification

Builds the documentation and reports errors.

```
/build              # HTML build (asciidoctor)
/build --ccutil     # Pantheon build (requires podman)
/build --all        # Both
```

Read-only — never modifies source files.

---

## Repository Structure

```
dita-migration-agent/
│
├── .claude/
│   └── skills/
│       ├── vale-fix/                    # Main fix skill
│       │   ├── SKILL.md                 # Skill definition and workflow
│       │   ├── dita-rules.md            # Fix instructions for all 31 AsciiDocDITA rules
│       │   ├── redhat-rules.md          # Fix instructions for all 35 RedHat rules
│       │   └── decision-guide.md        # Decision trees + manual review routing
│       ├── vale-check/                  # Read-only audit skill
│       │   └── SKILL.md
│       ├── validate-refs/               # Reference validation skill
│       │   └── SKILL.md
│       └── build/                       # Build verification skill
│           └── SKILL.md
│
├── styles/                              # Vale style definitions
│   ├── AsciiDocDITA -> (symlink)        # Links to asciidoctor-dita-vale/styles/AsciiDocDITA
│   └── RedHat/                          # Red Hat style rules (35 .yml files)
│       ├── CaseSensitiveTerms.yml
│       ├── Hyphens.yml
│       ├── TermsErrors.yml
│       └── ...
│
├── CLAUDE.md                            # Project instructions for Claude Code
├── README.md                            # This file
├── LICENSE                              # Apache License 2.0
└── .gitignore
```

### Skill Files

Each skill follows the Claude Code skill format:

- **`SKILL.md`** — YAML frontmatter (name, description, allowed tools) + step-by-step workflow instructions
- **Supporting files** — Reference docs that the skill reads before taking action

| Skill | Files | Purpose |
|-------|-------|---------|
| `vale-fix` | 4 files | SKILL.md + 3 reference guides (dita-rules, redhat-rules, decision-guide) |
| `vale-check` | 1 file | SKILL.md (read-only, no reference files needed) |
| `validate-refs` | 1 file | SKILL.md (wraps `scripts/validate-refs.py` in the target repo) |
| `build` | 1 file | SKILL.md (wraps `build.sh` and `tools/ccutil.sh` in the target repo) |

---

## Quick Reference

| Task | Command |
|------|---------|
| Audit all violations | `/vale-check .` |
| Audit errors only | `/vale-check . --severity error` |
| Audit one directory | `/vale-check topics/user_guide/` |
| Fix all issues | `/vale-fix assemblies/ topics/` |
| Fix one file | `/vale-fix topics/administration_guide/proc_example.adoc` |
| Fix errors only | `/vale-fix . --severity error` |
| Check references | `/validate-refs` |
| Fix broken references | `/validate-refs --fix` |
| HTML build | `/build` |
| Full build | `/build --all` |

---

## Vale Rules Coverage

### Rules handled by `/vale-fix` (auto-fix)

| Rule | Strategy | Example |
|------|----------|---------|
| CaseSensitiveTerms | Parse message, replace | "Openshift" -> "OpenShift" |
| Hyphens | Parse message, replace | "on premises" -> "on-premises" |
| ConsciousLanguage | Parse message, replace | "blacklist" -> "blocklist" |
| RepeatedWords | Remove duplicate | "the the" -> "the" |
| HeadingPunctuation | Remove trailing punct | "== Heading." -> "== Heading" |
| Abbreviations | Remove periods | "I.B.M." -> "IBM" |
| ShortDescription | Add `[role="_abstract"]` | Insert before first paragraph |
| ContentType | Add attribute | Insert `:_mod-docs-content-type:` |
| BlockTitle | Context-dependent | Varies by content type |
| CalloutList | Convert format | Code callouts -> definition lists |

### Rules routed to manual review

| Rule | Reason |
|------|--------|
| AssemblyContents | Multiple valid restructuring approaches |
| MergeConflictMarkers | Cannot auto-resolve merge conflicts |
| TaskSection | Requires structural refactoring (subsections in procedures) |
| EmDash | Context-dependent replacement |
| DoNotUseTerms | Custom messages, no standard substitution format |

---

## AsciiDoc Attributes

The skills use these attributes (never hardcode the values):

| Attribute | Value |
|-----------|-------|
| `{prod}` | Red Hat OpenShift Dev Spaces |
| `{prod-short}` | OpenShift Dev Spaces |
| `{orch-name}` | OpenShift |
| `{orch-cli}` | oc |
| `{ocp}` | OpenShift Container Platform |
| `{kubernetes}` | Kubernetes |
| `{prod-cli}` | dsc |

---

## Troubleshooting

### "vale: command not found"

Install vale:
```bash
# macOS
brew install vale

# Linux
snap install vale

# Or download from https://vale.sh/docs/install/
```

### "No styles found" or "AsciiDocDITA not found"

Verify the styles symlink exists and is not broken:
```bash
ls -la dita-migration-agent/styles/AsciiDocDITA
# Should point to ../../asciidoctor-dita-vale/styles/AsciiDocDITA
```

If broken, recreate it:
```bash
cd dita-migration-agent/styles
ln -sf ../../asciidoctor-dita-vale/styles/AsciiDocDITA AsciiDocDITA
```

### "StylesPath not found"

Ensure `.vale.ini` in `devspaces-dita-migration/` points to the correct relative path:
```ini
StylesPath = ../dita-migration-agent/styles
```

### Skills not discovered in Claude Code

If `/vale-fix` returns "Unknown skill":

1. Start a new conversation — skills are discovered at conversation start
2. Check skill names — use exact names: `/vale-fix`, `/vale-check`, `/validate-refs`, `/build`
3. Verify files exist:
   ```bash
   ls .claude/skills/*/SKILL.md
   ```

### Vale reports zero issues but files have problems

Vale only checks prose content. It does not validate:
- Cross-references (use `/validate-refs`)
- Include paths (use `/validate-refs`)
- Build correctness (use `/build`)

---

## Credits

| Project | Author | Purpose |
|---------|--------|---------|
| [asciidoctor-dita-vale](https://github.com/jhradilek/asciidoctor-dita-vale) | **Jaromir Hradilek** ([@jhradilek](https://github.com/jhradilek)) | AsciiDocDITA vale rules — the foundation of all DITA compatibility checks |
| [RedHat vale style](https://github.com/redhat-documentation/vale-at-red-hat) | Red Hat Documentation | Red Hat documentation style rules |

### Author

**Gaurav Trivedi** ([@gtrivedi88](https://github.com/gtrivedi88))

---

## License

Apache License 2.0 — See [LICENSE](LICENSE) for details.
