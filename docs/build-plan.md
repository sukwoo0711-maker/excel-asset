# Intranet Build Plan

## Target Shape

```text
approved source documents
  -> optional PII masking
  -> parser / exporter
  -> local database or markdown export
  -> local search index
  -> consistency findings
  -> human review
```

## Repository Boundaries

Keep in Git:

- source code
- neutral documentation
- skill instructions
- small fixtures with synthetic data only

Keep out of Git:

- raw business documents
- generated Markdown vaults
- SQLite databases generated from real data
- vector databases
- search engine indexes
- execution logs and review reports
- local model files

## Recommended Folders

```text
project/
├── data/             # local-only input, ignored
├── build/            # generated output, ignored
├── exports/          # generated markdown/csv/xlsx, ignored
├── docs/             # neutral docs
├── skills/           # neutral skills
└── tools/            # optional scripts
```

## Build Steps

1. Place approved input files under `data/`.
2. Run masking or redaction if the input may contain PII.
3. Convert structured files to SQLite or Markdown.
4. Build local search indexes under `build/` or another ignored directory.
5. Run `python auto_grill.py scan` to generate consistency findings.
6. Review findings manually before changing source documents.

## Self-Healing Policy

Self-healing does not mean autonomous file edits.

Allowed:

- detect inconsistent statements
- produce an evidence-backed finding
- create an open query for a document owner
- propose a patch for review

Not allowed by default:

- modifying source docs without approval
- scanning user-global home directories
- storing raw sensitive text in logs
- mixing generated knowledge vaults into Git

## Offline Package Flow

For restricted intranet environments:

1. Prepare an approved package list.
2. Download wheels on an approved internet-connected machine.
3. Scan and archive the wheelhouse.
4. Install from the internal mirror.
5. Record package versions in the deployment note.
