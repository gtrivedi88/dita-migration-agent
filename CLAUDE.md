# CLAUDE.md — DITA Migration Agent

## Project Overview

This repo provides Claude Code skills for fixing DITA compatibility and Red Hat
style issues in AsciiDoc documentation. It works with **any** AsciiDoc project
that follows Red Hat modular documentation conventions.

The skills use vale as the single source of truth — they only fix what vale
flags, never invent problems, and route ambiguity to manual review.

## Available Skills

| Skill | Purpose | Modifies Files? |
|-------|---------|-----------------|
| `/vale-fix` | Run vale, fix violations, create manual-review.md | Yes |
| `/vale-check` | Run vale, report violations (read-only) | No |
| `/validate-refs` | Validate xrefs, includes, images, duplicate IDs | Optional (with --fix) |
| `/build` | Build documentation (HTML and/or ccutil) | No |

## How to Use

All skills take the path to the target project's files as their first argument:

```
/vale-check ../my-project/topics/
/vale-fix ../my-project/assemblies/assembly_getting-started.adoc
/validate-refs ../my-project/
/build ../my-project/
```

**Recommended approach**: Fix one assembly at a time for reviewable changes.

## How It Works

1. **Vale is the single source of truth** — only fix what vale flags
2. **No phantom issues** — never invent problems vale didn't report
3. **No scope creep** — fix only the specific violation, nothing else
4. **Manual review for ambiguity** — when multiple valid approaches exist, create manual-review.md
5. **Post-fix verification** — re-run vale after every fix to catch regressions

## What Gets Fixed

- **DITA structure**: Missing abstracts, unsupported block titles, nested sections, callout conversion, content type assignment, and 25+ more structural rules
- **Grammar and terminology**: Case-sensitive terms (OpenShift), hyphenation (on-premises), conscious language (blocklist), repeated words, abbreviation periods
- **Content type detection**: Auto-detects PROCEDURE/CONCEPT/REFERENCE/ASSEMBLY from file content and adds `:_mod-docs-content-type:`
- **Callouts**: Converts code block callouts to DITA-compatible definition lists

## Repository Structure

```
dita-migration-agent/
├── .claude/skills/
│   ├── vale-fix/              # Main fix skill
│   │   ├── SKILL.md           # Skill definition and workflow
│   │   ├── dita-rules.md      # All 31 AsciiDocDITA rule fixes
│   │   ├── redhat-rules.md    # All 35 RedHat rule fixes
│   │   └── decision-guide.md  # Decision trees + manual review routing
│   ├── vale-check/            # Read-only check skill
│   ├── validate-refs/         # Reference validation skill
│   └── build/                 # Build verification skill
├── styles/
│   ├── AsciiDocDITA/          # 31 DITA compatibility rules
│   └── RedHat/                # 35 Red Hat style rules
├── setup.sh                   # Auto-install vale + configure target project
├── CLAUDE.md                  # This file
└── README.md                  # User documentation
```

## Target Project Layout

The skills work with projects following this structure:

```
your-project/
├── assemblies/           # Assembly files (include topics)
├── topics/               # Individual content modules (proc_, con_, ref_)
├── snippets/             # Reusable fragments (excluded from vale)
├── common/               # Shared attributes (excluded from vale)
├── images/               # All images
├── .vale.ini             # Vale config (created by setup.sh)
└── scripts/              # Optional validation scripts
```

## Content Types

| Type | Prefix | `:_mod-docs-content-type:` | Key Feature |
|------|--------|----------------------------|-------------|
| Procedure | `proc_` | PROCEDURE | Has `.Procedure` with numbered steps |
| Concept | `con_` | CONCEPT | Explains what/why, no steps |
| Reference | `ref_` | REFERENCE | Lookup tables, parameter lists |
| Assembly | `assembly_` | ASSEMBLY | Groups topics via `include::` |
| Snippet | `snip_` | SNIPPET | Reusable fragment, excluded from vale |

## Vale Rules Summary

### AsciiDocDITA (31 rules)
- **6 errors**: NestedSection, EntityReference, ExampleBlock, MismatchedId, TaskExample, TaskSection
- **22 warnings**: AdmonitionTitle, AssemblyContents, AuthorLine, BlockTitle, CalloutList, ContentType, DiscreteHeading, DocumentId, DocumentTitle, EquationFormula, LineBreak, PageBreak, RelatedLinks, ShortDescription, SidebarBlock, TableFooter, TaskContents, TaskDuplicate, TaskStep, TaskTitle, ThematicBreak
- **3 suggestions**: AttributeReference, ConditionalCode, IncludeDirective, TagDirective

### RedHat (35 rules)
- **5 errors**: Abbreviations, DoNotUseTerms, MergeConflictMarkers, Spacing, TermsErrors
- **10 warnings**: CaseSensitiveTerms, ConsciousLanguage, EmDash, GitLinks, HeadingPunctuation, Hyphens, RepeatedWords, Slash, SmartQuotes, Spelling, TermsWarnings, Using
- **20 suggestions**: Conjunctions, Contractions, Definitions, Ellipses, Headings, ObviousTerms, OxfordComma, PascalCamelCase, PassiveVoice, ProductCentricWriting, ReadabilityGrade, ReleaseNotes, SelfReferentialText, SentenceLength, SimpleWords, Symbols, TermsSuggestions, UserReplacedValues

## Critical Rules

### When using any skill:
- **Vale is king** — only fix what vale reports, nothing else
- **Read before edit** — always read the file before modifying it
- **Content type matters** — check `:_mod-docs-content-type:` before deciding fixes
- **Verify after fix** — re-run vale on modified files
- **Protect these elements** — never modify xref IDs, include paths, attribute references, code blocks, URLs, ifdef/endif blocks
- **Route ambiguity** — if unsure, add to manual-review.md instead of guessing
