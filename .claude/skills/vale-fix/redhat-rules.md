# RedHat Vale Rules — Fix Reference

This file contains fix instructions for all RedHat vale style rules.
Read this file at the start of every `/vale-fix` invocation.

The RedHat style enforces Red Hat documentation standards for terminology,
grammar, and style. Most substitution rules embed the fix in vale's message:
`"Use 'X' rather than 'Y'."` — parse the message and apply the replacement.

---

## ERROR-Level Rules (Must Fix)

### Abbreviations
- **Severity**: ERROR
- **Detects**: Periods in uppercase abbreviations: `I.B.M.`, `U.S.`, `A.P.I.`
- **Message**: "Do not use periods in all-uppercase abbreviations such as 'X.Y.Z.'."

**Auto-fix** (parse message, remove periods):
```
Before: Deploy on I.B.M. hardware.
After:  Deploy on IBM hardware.
```
Extract the abbreviation from the message (`such as 'X.Y.Z.'`), remove all periods, replace in text.

---

### DoNotUseTerms
- **Severity**: ERROR
- **Message**: Custom per term (not standard "Use X rather than Y" format)
- **Detects**: Prohibited terms

**Manual review always**: Messages are custom and context-dependent. Examples:
- `and/or` → "Use 'a and b', 'a or b', or 'a, b, or both'"
- `please` → Remove from technical documentation
- `foo`, `bar` → Use realistic examples

Route to manual review with the exact vale message.

---

### MergeConflictMarkers
- **Severity**: ERROR
- **Detects**: `<<<<<<<`, `=======`, `>>>>>>>` conflict markers
- **Message**: "Do not commit Git merge conflict markers in source code."

**Manual review always**: While the markers themselves can be identified, the
surrounding content has unresolved conflicts that require human judgment to
resolve. Route to manual review with the conflicting sections shown.

---

### Spacing
- **Severity**: ERROR
- **Detects**: Multiple spaces between sentences (`word.  Word`)
- **Message**: "Keep one space between words in 'X'."

**Auto-fix** (deterministic):
```
Before: End of sentence.  Start of next.
After:  End of sentence. Start of next.
```
Replace multiple spaces with single space.

---

### TermsErrors
- **Severity**: ERROR
- **Detects**: 472+ mandatory term corrections
- **Message**: "Use 'X' rather than 'Y'."

**Auto-fix** (parse message, apply substitution):
Parse the message to extract replacement and original. Apply on the flagged line only.

Common corrections:
| Wrong | Correct |
|---|---|
| `healthcheck` | `health check` |
| `bare metal` (before noun) | `bare-metal` |
| `acknowledgement` | `acknowledgment` |
| `analyse` | `analyze` |
| `colour` | `color` |
| `24/7` | `24x7` |
| `backend` | `back end` (noun) or `back-end` (adj) |
| `frontend` | `front end` (noun) or `front-end` (adj) |

**Manual review when**: Message format is not standard "Use X rather than Y", or replacement is context-dependent (e.g., backend → "back end" vs "back-end").

---

## WARNING-Level Rules (Should Fix)

### CaseSensitiveTerms
- **Severity**: WARNING
- **Detects**: 330+ case-sensitive term corrections
- **Message**: "Use 'X' rather than 'Y'."

**Auto-fix** (parse message, apply substitution):
```
Before: Install Openshift on your cluster.
After:  Install OpenShift on your cluster.
```

Common corrections:
| Wrong | Correct |
|---|---|
| `Openshift` | `OpenShift` |
| `Github` | `GitHub` |
| `Gitlab` | `GitLab` |
| `Javascript` | `JavaScript` |
| `Typescript` | `TypeScript` |
| `YAML` | `YAML` (not `yaml`) |
| `nodejs` | `Node.js` |
| `Golang` | `Go` |

---

### ConsciousLanguage
- **Severity**: WARNING
- **Detects**: Non-inclusive terminology
- **Message**: "Use X rather than 'Y'." (note: replacement may not be quoted when multiple options)

**Auto-fix for deterministic cases**:
| Wrong | Correct | Action |
|---|---|---|
| `blacklist` | `blocklist` | Auto-fix |
| `whitelist` | `allowlist` | Auto-fix |

**Manual review for context-dependent cases**:
| Wrong | Options | Action |
|---|---|---|
| `master branch` | `main branch` or `primary branch` | Auto-fix: use `main` |
| `master node` | `control plane node` | Auto-fix |
| `master` (other) | `primary` / `source` / `controller` / `host` / `director` | Manual review |
| `slave` (any) | `secondary` / `replica` / `worker` / `consumer` / `responder` | Manual review |

**Exceptions**: `master broker` and `slave broker` are NOT flagged (negative
lookahead in rule). Do not change these terms if they appear unflagged.

See Decision Tree 8 in decision-guide.md for full routing logic.

---

### EmDash
- **Severity**: WARNING
- **Detects**: Em dash character `—` or `&mdash;`
- **Message**: "Do not use em dashes. Use punctuation marks such as commas, parentheses, or colons instead."

**Manual review always**: The correct replacement (comma, parentheses, colon, or sentence restructuring) depends on the sentence context.

---

### GitLinks
- **Severity**: WARNING
- **Detects**: Links to github.com or gitlab.com (with exceptions for openshift/redhat repos)
- **Message**: "Do not include a link to X unless it is explicitly approved."

**Manual review always**: Need to determine if the link is approved or should be removed/replaced.

---

### HeadingPunctuation
- **Severity**: WARNING
- **Detects**: Trailing punctuation in headings: `.`, `?`, `!`
- **Message**: "Do not use end punctuation in headings."

**Auto-fix** (deterministic):
```
Before: == Installing the product.
After:  == Installing the product

Before: == What is OpenShift?
After:  == What is OpenShift
```
Remove trailing `.`, `?`, or `!` from the heading.

---

### Hyphens
- **Severity**: WARNING
- **Detects**: 237 hyphenation corrections
- **Message**: "Use X rather than 'Y'."

**Auto-fix** (parse message, apply substitution):
| Wrong | Correct |
|---|---|
| `addon` | `add-on` |
| `meta-data` | `metadata` |
| `plug-in` | `plugin` |
| `on premise` | `on-premises` |
| `pre-install` | `preinstall` |
| `run-time` (noun) | `runtime` |

---

### RepeatedWords
- **Severity**: WARNING
- **Detects**: Adjacent duplicate words: `the the`, `is is`, `a a`
- **Message**: "'X' is repeated."

**Auto-fix** (parse message, remove duplicate):
```
Before: This is the the best approach.
After:  This is the best approach.
```
Remove the second occurrence of the duplicated word (keeping the first one).
Match is case-insensitive: `The the` → `The`.

---

### Slash
- **Severity**: WARNING
- **Detects**: Word/word patterns (using `/` instead of `or`/`and`)
- **Message**: "Use either 'or' or 'and' in 'X'"
- **Exceptions**: I/O, TCP/IP, SSL/TLS, client/server, read/write, CI/CD, and 50+ technical terms

**Manual review always**: Need to determine if "or" or "and" is correct in context.

---

### SmartQuotes
- **Severity**: WARNING
- **Detects**: Curly/smart quotation marks
- **Message**: "Do not use smart quotation marks. Use X rather than X."

**Auto-fix** (deterministic):
```
Before: Use the "option" parameter.
After:  Use the "option" parameter.
```
Replace smart/curly quotes with straight ASCII quotes.

---

### Spelling
- **Severity**: WARNING
- **Detects**: Words not in the American English dictionary
- **Message**: "Verify the word 'X'. It is not in the American English spelling dictionary used by Vale."

**Manual review always**: Need to verify if the word is a legitimate technical term, proper noun, or actual misspelling.

---

### TermsWarnings
- **Severity**: WARNING
- **Detects**: 78 cautionary term replacements
- **Message**: "Consider using 'X' rather than 'Y' unless updating existing content that uses the term."

**Auto-fix** (parse message, apply substitution):
| Wrong | Correct |
|---|---|
| `can not` | `cannot` |
| `click on` | `click` |
| `bugfix` | `bug fix` |
| `Ctrl-click` | `press Ctrl and click` |
| `hamburger menu` | `more options icon` |

---

### Using
- **Severity**: WARNING
- **Detects**: `using` after a noun (should be `by using`)
- **Message**: "Use 'by using' instead of 'using' when it follows a noun for clarity."

**Auto-fix** (deterministic):
```
Before: Deploy the application using the CLI.
After:  Deploy the application by using the CLI.
```
Replace `using` with `by using` at the flagged location.

---

## SUGGESTION-Level Rules (Skip Unless --severity all)

These rules are NOT reported by default (`MinAlertLevel = warning`). Only
process them when `--severity all` is passed.

### Auto-fixable suggestions

| Rule | Message format | Fix strategy |
|---|---|---|
| Contractions | "Avoid contractions. Use 'X' rather than 'Y.'" | Parse message, replace contraction with expanded form |
| Ellipses | "Avoid the ellipsis (...) except to indicate omitted words." | Remove `...` or `…` (manual review if indicating omission) |
| ReleaseNotes | "For release notes, consider using 'X' rather than 'Y'." | `Now` → `With this update`, `Previously` → `Before this update` |
| SimpleWords | "Use simple language. Consider using 'X' rather than 'Y'." | Parse message, apply substitution |
| TermsSuggestions | "Depending on the context, consider using 'X' rather than 'Y'." | Parse message, apply substitution (manual review if context-dependent) |
| UserReplacedValues | "Separate words by underscores in user-replaced values." | Replace `-` with `_` in `<placeholder-values>` |

### Manual-review-only suggestions

| Rule | What it flags | Why manual review |
|---|---|---|
| Conjunctions | Sentences starting with And, But, Or, So | Rewriting sentence structure requires context |
| Definitions | Undefined acronyms on first use | Need to write the definition |
| Headings | Non-sentence-case headings | May be proper nouns (267 exceptions in rule) |
| ObviousTerms | Self-explanatory UI field names | Need to evaluate if documentation is needed |
| OxfordComma | Missing Oxford comma in `a, b and c` | Add comma: `a, b, and c` (auto-fixable in most cases) |
| PascalCamelCase | Unwrapped PascalCase/camelCase terms | Wrap in backticks or verify it's a proper noun (210 exceptions) |
| PassiveVoice | Passive constructions (`is taken`, `was done`) | Rewrite in active voice requires context |
| ProductCentricWriting | "allows you", "enables you", "lets you" | Rewrite to focus on user action |
| ReadabilityGrade | Flesch-Kincaid grade > 9 | Simplify sentence structure (context-dependent) |
| SelfReferentialText | "this section", "this topic", "this chapter" | Rewrite without self-reference |
| SentenceLength | Sentences > 32 words | Split or simplify (context-dependent) |
| Symbols | `!` and `&` in prose (not in code/URLs) | Remove or rewrite |

**For suggestion-level rules**: Only process if `--severity all` is passed. Otherwise skip entirely.

---

## Generic Substitution Fix Pattern

Most RedHat rules use substitution and produce messages in these formats:

1. `"Use 'replacement' rather than 'original'."` — both quoted
2. `"Use replacement rather than 'original'."` — replacement unquoted (multiple options separated by `|`)
3. `"Consider using 'replacement' rather than 'original'."` — suggestion variant
4. `"Avoid contractions. Use 'replacement' rather than 'original.'"` — contraction variant
5. `"For release notes, consider using 'replacement' rather than 'original'."` — domain-specific

**Parsing algorithm**:
1. Look for `rather than '` in the message — this separates replacement from original
2. Extract the ORIGINAL: text between the last `rather than '` and the closing `'`
3. Extract the REPLACEMENT: text between `Use ` (or `using `) and ` rather than`
4. Strip quotes from both values if present
5. Find `original` on the flagged line (case-sensitive match)
6. Replace FIRST occurrence only with `replacement`

**When replacement contains `|` (multiple options)**:
- Use the FIRST option by default: `primary|source|controller` → use `primary`
- Exception: `master`/`slave` in ConsciousLanguage → route to manual review (see Decision Tree 8)
- Exception: `back end|back-end` in TermsErrors → determine noun vs adjective from context:
  - Before a noun → use hyphenated form (`back-end server`)
  - Standalone → use space form (`the back end`)

**Protected zones — NEVER replace inside these**:
- Code blocks (between `----` or `....` delimiters)
- Inline code (between backticks)
- Attribute definitions (`:attr-name: value`)
- Attribute references (`{attribute}`)
- ID declarations (`[id="..."]`)
- URL values (`link:https://...[]`, `image::path[]`)
- xref targets (`xref:id_{context}[]`)
- ifdef/endif conditionals
- Passthrough blocks (`pass:[]`, `++++`...`++++`)

**NEVER**: Replace on lines other than the flagged line.
**NEVER**: Modify content vale did not flag.
