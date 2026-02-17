# DITA Migration Agent

Claude Code skills that fix DITA compatibility and Red Hat style issues in AsciiDoc documentation.

## Install

```bash
git clone git@github.com:gtrivedi88/dita-migration-agent.git
cd dita-migration-agent
./setup.sh
```

The setup script checks that vale is installed (offers to install if missing)
and verifies the agent's styles and configuration are intact. No files are
created in your project — the agent is self-contained.

## Use

Open Claude Code from this directory and run skills on your project:

```bash
claude
```

### Check (read-only audit)

```
/vale-check ../your-project/
```

### Fix (recommended: one assembly at a time)

```
/vale-fix ../your-project/assemblies/assembly_getting-started.adoc
```

### Other scopes

```
/vale-fix ../your-project/topics/administration_guide/proc_installing.adoc
/vale-fix ../your-project/topics/administration_guide/
/vale-fix ../your-project/assemblies/ ../your-project/topics/
/vale-fix ../your-project/
```

### Validate references and build

```
/validate-refs ../your-project/
/validate-refs ../your-project/ --fix
/build ../your-project/
/build ../your-project/ --all
```

## What gets fixed

| Category | Examples |
|----------|---------|
| DITA structure | Missing `[role="_abstract"]`, nested sections, unsupported block titles, example blocks |
| Grammar | "Openshift" -> "OpenShift", "on premises" -> "on-premises", repeated words |
| Callouts | Code block `<1>` markers -> DITA-compatible definition lists |
| Content type | Auto-adds `:_mod-docs-content-type: PROCEDURE/CONCEPT/REFERENCE/ASSEMBLY` |
| Terminology | Abbreviation periods, conscious language, heading punctuation |

Anything that can't be auto-fixed goes to `manual-review.md` with context and options.

By default, only errors and warnings are processed. Use `--severity all` to
also include 22 suggestion-level rules (contractions, passive voice, Oxford
comma, sentence length, etc.).

## Available skills

| Skill | Purpose | Modifies files? |
|-------|---------|-----------------|
| `/vale-check` | Report violations (read-only) | No |
| `/vale-fix` | Fix violations + create manual-review.md | Yes |
| `/validate-refs` | Check xrefs, includes, images, duplicate IDs | Optional (`--fix`) |
| `/build` | Run HTML or ccutil build | No |

## Recommended workflow

```
/vale-check ../your-project/assemblies/assembly_getting-started.adoc
/vale-fix ../your-project/assemblies/assembly_getting-started.adoc
/validate-refs ../your-project/
/build ../your-project/
```

Then review `manual-review.md`, commit, and move to the next assembly.

## Credits

- [asciidoctor-dita-vale](https://github.com/jhradilek/asciidoctor-dita-vale) by Jaromir Hradilek — AsciiDocDITA rules
- [vale-at-red-hat](https://github.com/redhat-documentation/vale-at-red-hat) by Red Hat Documentation — RedHat style rules

## License

Apache License 2.0
