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

**Manual review always**: Cannot auto-resolve merge conflicts.

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
- **Message**: "Use X rather than 'Y'." (note: replacement may not be quoted)

**Auto-fix** (parse message, apply substitution):
| Wrong | Correct |
|---|---|
| `blacklist` | `blocklist` |
| `whitelist` | `allowlist` |
| `master` | `primary` / `source` / `controller` / `host` |
| `slave` | `secondary` / `replica` / `worker` / `consumer` |

**Manual review when**: `master`/`slave` replacement is context-dependent (multiple valid options).

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
Remove the first occurrence of the duplicated word (keeping one).

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

These are informational and typically not auto-fixed:

| Rule | What it flags |
|---|---|
| Conjunctions | Sentences starting with And, But, Or, So |
| Contractions | `can't` → `cannot`, `don't` → `do not` |
| Definitions | Undefined acronyms on first use |
| Ellipses | `...` except for omitted words |
| Headings | Non-sentence-case headings |
| ObviousTerms | Self-explanatory UI field names |
| OxfordComma | Missing Oxford comma |
| PascalCamelCase | Unwrapped PascalCase terms |
| PassiveVoice | Passive voice constructions |
| ProductCentricWriting | "allows you", "enables you" |
| ReadabilityGrade | Flesch-Kincaid grade > 9 |
| ReleaseNotes | `Now` → `With this update` |
| SelfReferentialText | "this section", "this topic" |
| SentenceLength | Sentences > 32 words |
| SimpleWords | `utilize` → `use`, `accomplish` → `do` |
| Symbols | `!` and `&` usage |
| TermsSuggestions | Context-dependent term suggestions |
| UserReplacedValues | Hyphens in user-replaced values |

**For suggestion-level rules**: Only fix if `--severity all` is passed. Otherwise skip.

---

## Generic Substitution Fix Pattern

Most RedHat rules use substitution and produce messages in these formats:

1. `"Use 'replacement' rather than 'original'."` — both quoted
2. `"Use replacement rather than 'original'."` — replacement unquoted (may have multiple options separated by `|`)
3. `"Consider using 'replacement' rather than 'original'."` — suggestion variant
4. `"For release notes, consider using 'replacement' rather than 'original'."` — domain-specific

**Parsing algorithm**:
1. Extract text between `Use '` and `' rather than '` → replacement
2. Extract text between `rather than '` and `'.` → original
3. If no quotes around replacement: extract text between `Use ` and ` rather than '`
4. Find `original` on the flagged line
5. Replace first occurrence with `replacement`
6. If replacement contains `|`, use the FIRST option (most common)

**NEVER**: Replace occurrences on lines other than the flagged line.
**NEVER**: Replace inside code blocks, attribute definitions, or ID values.
