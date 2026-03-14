# SOP-to-XML Compiler

Converts verbose Markdown SOP files into dense DSPy-style XML state machines.
Targets **40-60% token reduction** on prose-heavy SOPs while preserving all rules.

## Files

| File | Purpose |
|------|---------|
| `sop_compiler.py` | Main compiler: Markdown → XML state machine |
| `token_counter.py` | Token estimation and reduction reporting |

## Usage

```bash
# Compile a Markdown SOP to XML
python3 sop_compiler.py compile WORKFLOW_AUTO.md --output workflow_compiled.xml

# Show token reduction stats (without writing output)
python3 sop_compiler.py stats BOOTSTRAP.md

# Count tokens for a single file
python3 token_counter.py WORKFLOW_AUTO.md

# Compare original vs compiled
python3 token_counter.py WORKFLOW_AUTO.md --xml workflow_compiled.xml

# Run self-tests
python3 sop_compiler.py --test
python3 token_counter.py --test
```

## How it works

Each Markdown `##` heading becomes a `<state id="...">` element.

Rules are classified and compressed:
- `- Do not X` → `<constraint>NO X</constraint>`
- `- If blocked by Y, do Z` → `<transition>ON block(Y): do Z</transition>`
- `- Execute X after Y` → `<action>Execute X after Y</action>`
- Tables → compact `<entry>` elements with attributes

A `<mapping>` element at the end maps original section headings to state IDs.

## Example

Input (44 words, ~57 tokens):
```markdown
## 6.1) Proactive execution mandate
- Do not ask permission for routine, reversible execution steps.
- Prefer action over proposal: execute the next logical step and report outcome.
- If blocked by missing auth/credentials, report the exact unblock command and continue other non-blocked work.
- After each completion, advance to the highest-priority dependent next step automatically.
```

Output:
```xml
<state id="proactive_execution_mandate" title="6.1) Proactive execution mandate">
  <transition>ON block(missing auth/credentials): report unblock command AND continue unblocked work</transition>
  <transition>ON complete: auto-advance to highest-priority dependent</transition>
  <constraint>NO ask permission for routine/reversible steps</constraint>
  <rule>PREFER action>proposal: execute next step and report outcome</rule>
</state>
```

## Performance

| SOP type | Expected reduction |
|----------|--------------------|
| Verbose prose (WORKFLOW, BOOTSTRAP) | 40-60% |
| Mixed prose+tables | 20-40% |
| Already-dense Markdown (AGENTS.md) | Near 0% — already optimal |

> **Note**: XML structural overhead (~5-10%) means very dense Markdown may not compress.
> Best results on SOPs with verbose English sentences and repeated filler phrases.

## Requirements

- Python 3.9+
- Pure stdlib (no pip installs needed)
