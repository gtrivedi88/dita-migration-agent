# DITA Migration Agent

**Claude Code skills that fix DITA compatibility and Red Hat style issues in AsciiDoc documentation.** Works with any AsciiDoc project. Run setup, point at your project, and start fixing.

---

## What It Does

When you run the skills on your AsciiDoc project, they automatically fix:

| Category | What gets fixed | Examples |
|----------|----------------|---------|
| **DITA structure** | 31 AsciiDocDITA compatibility rules | Missing abstracts, nested sections, unsupported block titles, example block nesting |
| **Grammar and terminology** | 35 Red Hat style rules | "Openshift" -> "OpenShift", "on premises" -> "on-premises", repeated words, abbreviation periods |
| **Callout conversion** | Code block callouts | `<1>`, `<2>` markers -> DITA-compatible definition lists |
| **Content type** | Missing `:_mod-docs-content-type:` | Auto-detects PROCEDURE / CONCEPT / REFERENCE / ASSEMBLY and adds the attribute |
| **Everything else** | All other vale violations | Entity references, line breaks, page breaks, heading punctuation, conscious language |

Anything the skills can't auto-fix gets routed to `manual-review.md` with context and recommended options.

---

## Getting Started

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (or Cursor)
- Git

That's it. The setup script installs everything else.

### Install

```bash
# 1. Clone this repo
git clone <this-repo-url>
cd dita-migration-agent

# 2. Run setup on your AsciiDoc project
./setup.sh ../path-to-your-asciidoc-project
```

The setup script will:
- Check if [vale](https://vale.sh) is installed (offers to install if missing)
- Configure `.vale.ini` in your project to use the bundled styles
- Verify the setup works by running vale on a test file

```
============================================================
  DITA Migration Agent — Setup
============================================================

  Agent repo:     /path/to/dita-migration-agent
  Target project: /path/to/your-project

[INFO] vale is installed: vale version 3.9.0
[INFO] Found 31 AsciiDocDITA rules and 35 RedHat rules
[INFO] Created .vale.ini with StylesPath = ../dita-migration-agent/styles
[INFO] Vale runs successfully. Found 42 issues in test file.

============================================================
  Setup complete
============================================================

  Next steps:

  1. Open Claude Code from this directory:
     cd dita-migration-agent && claude

  2. Run a check on your project:
     /vale-check ../your-project/

  3. Fix violations (recommended: one assembly at a time):
     /vale-fix ../your-project/assemblies/assembly_getting-started.adoc

============================================================
```

### Start Using

```bash
# 3. Open Claude Code from this repo
cd dita-migration-agent
claude

# 4. Start with a read-only check
/vale-check ../your-project/

# 5. Fix one assembly at a time (recommended)
/vale-fix ../your-project/assemblies/assembly_getting-started.adoc
```

---

## Available Skills

| Skill | What it does | Modifies files? |
|-------|-------------|-----------------|
| `/vale-check` | Audit — reports all violations without changing anything | No |
| `/vale-fix` | Fix — auto-fixes violations, creates manual-review.md for the rest | Yes |
| `/validate-refs` | Validates xrefs, includes, images, duplicate IDs | Optional (`--fix`) |
| `/build` | Runs HTML and/or ccutil build, reports errors | No |

---

## How to Run

### Scope options

You can run on a single file, a directory, multiple paths, or an entire project:

```
# One assembly (recommended — keeps changes reviewable)
/vale-fix ../your-project/assemblies/assembly_getting-started.adoc

# One topic
/vale-fix ../your-project/topics/administration_guide/proc_installing.adoc

# One directory
/vale-fix ../your-project/topics/administration_guide/

# Multiple directories
/vale-fix ../your-project/assemblies/ ../your-project/topics/

# Entire project
/vale-fix ../your-project/

# Errors only (skip warnings)
/vale-fix ../your-project/ --severity error
```

### Recommended workflow

```
# Step 1: Audit — see what needs fixing
/vale-check ../your-project/assemblies/assembly_getting-started.adoc

# Step 2: Fix — auto-fix what's possible
/vale-fix ../your-project/assemblies/assembly_getting-started.adoc

# Step 3: Validate references — make sure nothing broke
/validate-refs ../your-project/

# Step 4: Build — verify the docs still compile
/build ../your-project/

# Step 5: Review manual-review.md for anything that needs human judgment
```

### Assembly-by-assembly workflow

For large projects, fix one assembly at a time:

```
# Day 1: Getting Started guide
/vale-fix ../your-project/assemblies/assembly_getting-started.adoc
# Review changes, commit

# Day 2: Installation guide
/vale-fix ../your-project/assemblies/assembly_installing.adoc
# Review changes, commit

# Day 3: Remaining files
/vale-fix ../your-project/topics/
# Review changes, commit
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
│     └─ decision-guide.md (decision trees + manual review routing)           │
│                                                                             │
│  2. GATHER CONTEXT                                                          │
│     ├─ Content type (:_mod-docs-content-type:)                              │
│     ├─ File type (assembly, procedure, concept, reference, snippet)         │
│     └─ Cross-reference dependencies                                         │
│                                                                             │
│  3. RUN VALE                                                                │
│     └─ vale --output=JSON <target>                                          │
│                                                                             │
│  4. FIX ISSUES                                                              │
│     ├─ Sort by line number DESCENDING (bottom-up to preserve line numbers)  │
│     ├─ Deterministic issues → auto-fix                                      │
│     └─ Ambiguous issues → route to manual-review.md                         │
│                                                                             │
│  5. VERIFY                                                                  │
│     ├─ Re-run vale on every modified file                                   │
│     ├─ If fix introduced regression → revert + route to manual review       │
│     └─ Confirm: zero new violations from fixes                              │
│                                                                             │
│  6. OUTPUT                                                                  │
│     ├─ Summary with counts (fixed / manual / verified)                      │
│     └─ manual-review.md (file, line, context, options)                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Safety guarantees

| Guarantee | How |
|-----------|-----|
| **No phantom fixes** | Only fixes what vale flags — zero modifications to unflagged content |
| **No regressions** | Re-runs vale after every fix; reverts if new issues appear |
| **No guessing** | Ambiguous cases go to manual-review.md with context and options |
| **No scope creep** | Fixes only the specific violation, nothing else |
| **Protected elements** | Never modifies xref IDs, include paths, attribute references, code blocks, URLs, ifdef/endif |

---

## Repository Structure

```
dita-migration-agent/
│
├── .claude/skills/
│   ├── vale-fix/                    # Main fix skill
│   │   ├── SKILL.md                 # Skill workflow (7 steps)
│   │   ├── dita-rules.md            # Fix instructions for 31 AsciiDocDITA rules
│   │   ├── redhat-rules.md          # Fix instructions for 35 RedHat rules
│   │   └── decision-guide.md        # Decision trees + manual review routing
│   ├── vale-check/SKILL.md          # Read-only audit
│   ├── validate-refs/SKILL.md       # Reference validation
│   └── build/SKILL.md               # Build verification
│
├── styles/                           # Vale style definitions (bundled)
│   ├── AsciiDocDITA/                 # 31 DITA compatibility rules (.yml)
│   └── RedHat/                       # 35 Red Hat style rules (.yml)
│
├── setup.sh                          # Setup script (installs vale, configures project)
├── CLAUDE.md                         # Project instructions for Claude Code
├── README.md                         # This file
├── LICENSE                           # Apache License 2.0
└── .gitignore
```

---

## Troubleshooting

### "vale: command not found"

Run setup again or install manually:
```bash
# macOS
brew install vale

# Linux
snap install vale

# Or: https://vale.sh/docs/install/
```

### "No styles found" or vale returns errors

Re-run setup:
```bash
./setup.sh ../your-project
```

### Skills not discovered in Claude Code

1. Make sure you open Claude Code **from the dita-migration-agent directory**
2. Start a new conversation (skills are discovered at conversation start)
3. Verify skill files exist: `ls .claude/skills/*/SKILL.md`

### Vale reports zero issues but files have problems

Vale checks prose content only. For other checks:
- Cross-references and includes: `/validate-refs ../your-project/`
- Build correctness: `/build ../your-project/`

---

## Credits

| Project | Author | Purpose |
|---------|--------|---------|
| [asciidoctor-dita-vale](https://github.com/jhradilek/asciidoctor-dita-vale) | **Jaromir Hradilek** | AsciiDocDITA vale rules for DITA compatibility |
| [RedHat vale style](https://github.com/redhat-documentation/vale-at-red-hat) | Red Hat Documentation | Red Hat documentation style rules |

### Author

**Gaurav Trivedi** ([@gtrivedi88](https://github.com/gtrivedi88))

---

## License

Apache License 2.0 — See [LICENSE](LICENSE) for details.
