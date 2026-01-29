# DITA Migration Agent

**Autonomous AI agent** that fixes DITA compatibility issues in AsciiDoc documentation. It understands your project structure, makes intelligent decisions, and keeps iterating until **zero errors and zero warnings**.

## How to use the agent

**Step 1: Get API Access**

- Get your Gemini API key: https://gitlab.cee.redhat.com/models-corp/user-documentation/-/blob/main/getting-started.md
- Gemini API URL: https://gitlab.cee.redhat.com/models-corp/user-documentation/-/blob/main/models/gemini.md

**Step 2: Install and Run**

```bash
# First install
pip install https://github.com/gtrivedi88/dita-migration-agent/archive/main.zip

# Completely clean install:
pip uninstall -y dita-migration-agent
rm -rf ~/.local/lib/python3.*/site-packages/dita_agent
rm -rf ~/.local/lib/python3.*/site-packages/dita_migration_agent*
pip install --no-cache-dir https://github.com/gtrivedi88/dita-migration-agent/archive/main.zip

# Verify the fix is installed:
python -c "from dita_agent.fixers.registry import RelatedLinksTemplateFixer; print('Fix present!')"


# Setup
dita-agent setup # Fill in the API URL, Select Model 1, and enter API key
# API URL: https://gemini--apicast-production.apps.int.stc.ai.prod.us-east-1.aws.paas.redhat.com/v1beta/openai


# Run - choose one of these commands (inside your AsciiDoc project)

# Full migration in one go
dita-agent run

# Fix ONE assembly + all its included topics
dita-agent run --assembly <path-to-assembly>

# Fix specific topics (1-10 files)
dita-agent run --topics topics/proc_installing.adoc topics/con_overview.adoc

# Fix first N files with issues
dita-agent run --limit 5

# Preview without modifying
dita-agent run --dry-run
```

**That's it.** The agent automatically:
- Analyzes your project structure (assemblies, topics, snippets)
- Sets up required tools (first run only)
- Prompts for API credentials (first run only)
- Fixes all DITA issues using rules + LLM
- Verifies every fix is safe
- Keeps going until **zero errors AND zero warnings**

---


## Usage

### Scope Options

| Option | What It Does | Use Case |
|--------|--------------|----------|
| `--assembly FILE` | Fixes assembly + ALL includes (recursive) | "Fix my Getting Started guide" |
| `--topics FILE...` | Fixes exactly those files (max 10) | "Fix these specific files" |
| `--limit N` | Fixes first N files with issues | "Small PR with 5 files" |
| (none) | Fixes entire project | Full migration |

### Example Workflow

```bash
# Day 1: Fix the "Getting Started" guide
dita-agent run --assembly guides/assembly_getting-started.adoc
git add . && git commit -m "Fix DITA issues in Getting Started guide"

# Day 2: Fix the "Installation" guide  
dita-agent run --assembly guides/assembly_installing.adoc
git add . && git commit -m "Fix DITA issues in Installation guide"

# Day 3: Fix 5 remaining files
dita-agent run --limit 5
git add . && git commit -m "Fix 5 more files"
```

---

## Features

| Feature | Description |
|---------|-------------|
| **Three-Phase Processing** | Content Type → Callouts → All Other DITA Issues |
| **Structure-Aware** | Understands assemblies vs topics vs snippets |
| **Conditional-Safe** | Preserves `ifdef`/`ifndef`/`ifeval` blocks and `{variables}` |
| **Targeted Edits** | Precise fixes (not full file rewrites) to preserve content |
| **Incremental** | Processes in chunks, verifies each |
| **Self-Correcting** | Automatic rollback on syntax errors |
| **Learning Memory** | Learns fix patterns, propagates to similar issues |
| **Cost-Efficient** | Pattern fixes first (FREE), LLM only when needed |

### Three-Phase Processing

| Phase | Description | Strategy |
|-------|-------------|----------|
| **Phase 1** | Content Type Assignment (`:_mod-docs-content-type:`) | LLM analysis |
| **Phase 2** | Callouts Conversion (code block callouts) | External tool |
| **Phase 3** | All Other DITA Issues (30+ Vale rules) | Rule-first + LLM |

### Issues It Fixes

| Issue | Description | Strategy |
|-------|-------------|----------|
| ShortDescription | Missing `[role="_abstract"]` | Pattern + LLM |
| ContentType | Missing content type declaration | LLM |
| TaskStep | Content after `.Procedure` not in list | LLM |
| TaskSection | Sections inside procedures | LLM |
| BlockTitle | Non-standard block titles | Pattern |
| CalloutList | Callout markers in code | External tool |
| ExampleBlock | Nested example blocks | LLM |
| RelatedLinks | Non-link content in resources | LLM |
| DocumentTitle | Missing document title | Pattern |
| AuthorLine | Line after title interpreted as author | Pattern |
| LineBreak | Hard line breaks (` +`) | Pattern + LLM |
| AssemblyContents | Content in assemblies | Manual review |
| **+ 18 more** | All DITA compatibility rules | Mixed |

---

## Configuration

### Global Config (`~/.dita-agent/config.json`)

```json
{
  "provider": "gemini",
  "base_url": "https://generativelanguage.googleapis.com",
  "model": "gemini-2.5-flash-preview-05-20",
  "api_key": "your-api-key"
}
```

### Project Files

The agent creates a `.dita-agent/` directory in your project for:
- Backup files (before each modification)
- Session logs
- Checkpoints (for resumable processing)
- `MANUAL_REVIEW.md` (issues needing human review)

This directory is automatically added to `.gitignore`.

### Reset & Troubleshooting

```bash
# Reset API credentials (re-prompts on next run)
rm ~/.dita-agent/config.json

# Clear all global cache and tools
rm -rf ~/.dita-agent/

# Clear project-specific cache and backups
rm -rf .dita-agent/

# Start completely fresh
rm -rf ~/.dita-agent/ .dita-agent/
dita-agent run  # Will re-setup everything
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS DITA MIGRATION AGENT                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. SCOPE RESOLUTION                                                        │
│     ├─ Entire project (default)                                             │
│     ├─ Single assembly + all includes (recursive)                           │
│     ├─ Specific topics (1-10 files)                                         │
│     └─ First N files with issues                                            │
│                                                                             │
│  2. PHASE 1: CONTENT TYPE ASSIGNMENT                                        │
│     └─ Adds :_mod-docs-content-type: attribute (ASSEMBLY/PROCEDURE/etc.)    │
│                                                                             │
│  3. PHASE 2: CALLOUTS CONVERSION                                            │
│     └─ Converts code callouts to DITA-compatible format                     │
│                                                                             │
│  4. PHASE 3: ALL OTHER DITA ISSUES (Rule-First Architecture)                │
│     ├─ Scans with Vale (30+ DITA rules)                                     │
│     ├─ Groups issues by rule type                                           │
│     ├─ Tier 1: Pattern Fixers (regex/template - FREE)                       │
│     ├─ Tier 2: Template Fixers (LLM learns pattern, propagates)             │
│     ├─ Tier 3: LLM Fixers (complex, context-dependent)                      │
│     └─ Learning Memory (stores successful patterns)                         │
│                                                                             │
│  5. VERIFICATION & VALIDATION                                               │
│     ├─ Syntax check after every fix                                         │
│     ├─ Automatic rollback on errors                                         │
│     └─ Vale re-scan to confirm fix worked                                   │
│                                                                             │
│  6. OUTPUT                                                                  │
│     ├─ Success report with statistics                                       │
│     └─ MANUAL_REVIEW.md (AI-ready prompts for remaining issues)             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Autonomous Loop

```
    ┌────────────────────────────────────────────────────────────┐
    │                                                            │
    │     SCAN → BACKUP → FIX → VERIFY → VALIDATE                │
    │       │                              │                     │
    │       │     (if errors introduced)   │                     │
    │       │             ↓                │                     │
    │       │        ROLLBACK ────────────→│                     │
    │       │                              │                     │
    │       │     (if zero issues)         │                     │
    │       │             ↓                │                     │
    │       └──────── SUCCESS! ←──────────┘                      │
    │                                                            │
    │     REPEAT until: ZERO errors + ZERO warnings              │
    │                                                            │
    └────────────────────────────────────────────────────────────┘
```

---

## Output Examples

### Success

```
════════════════════════════════════════════════════════════
  ✅ SUCCESS - All DITA compatibility issues resolved!
════════════════════════════════════════════════════════════
  Files processed: 6
  Phase 1 (Content Type): 6 fixed
  Phase 2 (Callouts): 3 fixed
  Phase 3 (DITA Issues): 12 fixed
  Total LLM calls: 21
  Cost: $0.12
════════════════════════════════════════════════════════════
```

### Partial Success

When some issues can't be fixed automatically:

```
════════════════════════════════════════════════════════════
  ⚠️  PARTIAL SUCCESS
════════════════════════════════════════════════════════════
  Files processed: 6
  Issues fixed: 18
  Issues needing manual review: 2
  
  📄 See: MANUAL_REVIEW.md
════════════════════════════════════════════════════════════
```

The `MANUAL_REVIEW.md` file contains **AI-ready prompts** that you can copy-paste directly into Cursor, Claude, or other AI assistants to fix the remaining issues.

---

## Credits

This project builds on the work of several contributors and tools:

### Core Dependencies

| Project | Author | Purpose |
|---------|--------|---------|
| [asciidoctor-dita-vale](https://github.com/jhradilek/asciidoctor-dita-vale) | **Jaromír Hradílek** ([@jhradilek](https://github.com/jhradilek)) | Vale rules for DITA validation - the foundation of all DITA compatibility checks. His work on `asciidoctor-dita-vale` provides the validation backbone for detecting all DITA compatibility issues. |
| [callouts-conversion](https://github.com/gtrivedi88/callouts-conversion) | **Gaurav Trivedi** | Automated callout fixing tool |

### Author

**Gaurav Trivedi** ([@gtrivedi88](https://github.com/gtrivedi88))

---

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.
