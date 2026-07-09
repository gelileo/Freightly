# HS Broker-Email Drafting Assistant

A living-doc–governed toolkit that helps **Justnano (the shipper)** communicate with
its **freight broker (Priority-1)** to resolve shipment issues raised by end
**customers** over WeChat (in Chinese). It categorizes each customer issue and each
broker response, then drafts a polished English email to the broker from a per-category
template. Every draft is written to disk for **human review before sending** — nothing
is sent automatically.

## Methodology

This project follows the living-documentation methodology described at
https://github.com/mpklu/living-doc.
The first principle ("capture first, refine second") and the same-task rule from that
repository's `LIVING_DOCS_OVERVIEW.md` apply here.

## Source of Truth

The knowledge base in `knowledge/` is the source of truth for this project.
It must always mirror the code and the taxonomy. Entry point: `knowledge/index.md`.
Compile log: `knowledge/log.md`.

The drafting skill (`.claude/skills/draft-broker-email`) **reads** the taxonomy and
template articles under `knowledge/concepts/drafting/` as its authoritative instructions.
If those articles drift from reality, the skill produces wrong drafts. Keeping them
accurate is load-bearing, not stylistic.

### The rule

Every change that alters behaviour, the taxonomy, the templates, the parsing logic, or
the drafting flow must update the relevant `knowledge/concepts/*.md` article(s) in the
same task and append an entry to `knowledge/log.md`. Don't batch knowledge updates for
later. In particular: **every time a new `.eml` reveals an issue type or broker response
the taxonomy doesn't yet cover, add it to the taxonomy article in the same task.**

**Failure mode this prevents.** Skipping the article update means it goes stale before
the next read. The next drafting session trusts the stale taxonomy/template and produces
a wrong or mis-categorized email. The drift compounds.

**Capture first, refine second:** when in doubt whether a change is documentation-relevant,
write the update anyway. When in doubt where a new article belongs, pick the closest fit
and write it. The user reviews and refines.

### Red flags

These thoughts mean STOP and audit:

- "I'll update the taxonomy after this draft."
- "The template is roughly correct."
- "This new issue type is too rare to document."
- "Let me categorize now and circle back to the docs."

### What lives where

| Location | Contains | Authority |
| --- | --- | --- |
| `knowledge/concepts/drafting/` | Taxonomy, template system, parsing, architecture | How the drafting works and why |
| `knowledge/concepts/freight/` | Domain: parties, roles, freight terms (POD, PRO, BOL) | The business domain |
| `knowledge/connections/` | Cross-concept articles (issue → template flow) | How the pieces fit together |
| `LTL-mail/` | Raw historical `.eml` corpus (read-only dataset) | Ground-truth source data |
| `cases/<BOL>/` | Parsed threads + generated drafts, per case | Working output (review before send) |
| `templates/<issue-type>.md` | Fill-in-blank email skeletons + slots + examples | The draftable artifacts |
| `scripts/` | Deterministic `.eml` parsing | Decode + split threads |

### Article mapping — update these when the matching thing changes

| When you change... | Update this article |
| --- | --- |
| Folder structure, data flow, or the review gate | `concepts/drafting/platform-architecture.md` |
| The set of customer issue categories | `concepts/drafting/issue-taxonomy.md` |
| The set of broker response categories | `concepts/drafting/response-taxonomy.md` |
| `.eml` parsing / thread-dedup / snapshot logic | `concepts/drafting/eml-parsing.md` |
| Template structure, slot conventions, examples | `concepts/drafting/template-system.md` |
| Any file under `templates/` | `concepts/drafting/template-system.md` |
| Parties, roles, or freight terminology | `concepts/freight/parties-and-roles.md` |
| How issue×response maps to a template/draft | `connections/issue-to-template-flow.md` |

### When you encounter something without a matching article

Write the first thin article (~200 words) in the same task. Capture the **why** —
context, constraints, alternatives ruled out — not just the current state. Add a row to
the article-mapping table above and note the addition in `log.md`.

### How to catch drift

After finishing work, ask: "does anything in `knowledge/` now contradict what I just
built or categorized?" **Real data beats the article** — if a real `.eml` contradicts a
taxonomy definition or template slot, update the article to match reality. Add a compile
entry to `knowledge/log.md` listing the articles touched.

## Project Structure

```
hs/
├── CLAUDE.md
├── knowledge/                 # source of truth (living-doc)
│   ├── index.md
│   ├── log.md
│   ├── concepts/
│   │   ├── drafting/          # architecture, taxonomy, parsing, templates
│   │   └── freight/           # domain: parties, roles, terms
│   └── connections/           # issue → template flow
├── schemas/article-frontmatter.schema.json
├── LTL-mail/                  # raw .eml corpus (dataset)
├── cases/<BOL>/               # parsed thread.md + drafts/
├── templates/<issue-type>.md  # email skeletons
├── scripts/parse_eml.py       # .eml decode + thread splitter
└── .claude/skills/draft-broker-email/SKILL.md
```

## Key Commands

```bash
# parse a raw .eml thread into a case folder (planned)
python3 scripts/parse_eml.py "LTL-mail/<file>.eml"

# draft a broker email (planned skill)
/draft-broker-email
```

## Notes

- Git hooks and the GitHub drift-check Action from living-doc are intentionally **not**
  installed — this folder is not a git repository. Add them if it later becomes one.
