# Invoice Field/Layout Labeler Implementation Plan

> **For agentic workers:** implement task-by-task and verify each behavior before continuing.

**Goal:** Ship a local web app and a public GitHub dataset workflow for invoice field/layout annotations and Colab validation.

**Architecture:** Python stdlib HTTP server with PyPDFium2 rendering; vanilla HTML/CSS/JS canvas UI; per-invoice JSON annotations for merge-friendly Git collaboration; Python validation/export tools and a Colab notebook.

**Tech Stack:** Python 3.11+, stdlib `http.server`/`json`/`csv`/`hashlib`/`unittest`, PyPDFium2, HTML/CSS/vanilla JS, Google Colab notebook.

**Spec:** `docs/superpowers/specs/2026-11-02-field-layout-labeler-design.md`

## Global Constraints

- All new work lives in the standalone `field_layout_labeler` directory in the workspace.
- Use existing public remote `https://github.com/nguyenhung1204/data_detection-layout`; do not create a repository.
- Never modify source PDFs, recognition annotations/progress, or existing apps.
- OCR suggestions are not field/layout ground truth.
- No model fine-tuning in this task.
- Store one annotation file per invoice; detect import/merge conflicts rather than silently overwriting.
- PDFs are public only under user's stated authorization; no secrets in repo.

## Review Focus

- Invalid or out-of-page normalized coordinates: reject with a visible validation error; test malformed bounds.
- Stale/mismatched PDF checksum: refuse to merge; test changed-source hash.
- Annotation edits and page changes: preserve current field/transcript state and unsaved warning; test save/reload.
- Two annotators editing same invoice differently: report conflict without overwriting; test conflict report.
- PDF paths supplied by browser: constrain to manifest-owned files; test traversal rejection.
- A single invoice/page in multiple splits: validator reports leakage; test cross-split invoice.

## File Map

- `app/server.py`: local HTTP API, PDF rendering, strict path and payload validation.
- `app/static/index.html`, `app/static/app.js`, `app/static/styles.css`: three-panel annotation UI.
- `app/config.py`: repo-relative paths and schema constants.
- `data/pdfs/`: verified copies of active PDFs.
- `data/annotations/by_invoice/*.json`: annotation state, one file per invoice.
- `data/manifests/invoice_manifest.csv`, `assignment_manifest.csv`, `source_snapshot.json`.
- `schema/fields.json`: canonical fields, layout types and schema version.
- `tools/bootstrap_dataset.py`: copy/checksum source PDFs and seed OCR candidate annotations, non-destructive.
- `tools/validate_dataset.py`: manifest, annotations, coordinates, split and row checks.
- `tools/merge_annotations.py`: merge reviewer packages with explicit conflict report.
- `tools/export_dataset.py`: verified/review JSONL, CSV, detection labels and ZIP.
- `notebooks/Prepare_Field_Layout_Data_Colab.ipynb`: clone pinned revision, validate and write Drive output.
- `tests/`: unittest coverage for importer, server APIs, validation, merge and export.
- `start_labeler.ps1`, `requirements.txt`, `.gitignore`, README/docs.

## Tasks

### Task 1: Repository bootstrap and source inventory

**Files:** create package skeleton, `schema/fields.json`, `tools/bootstrap_dataset.py`, `tests/test_bootstrap.py`, dataset manifests and per-invoice JSON.

- [ ] Test active-manifest matching by basename and SHA-256; test mismatched/missing file refusal.
- [ ] Implement idempotent bootstrap: 208 included PDFs only, preserve source; combine OCR candidate geometry with transcript-review state, but keep field labels unassigned.
- [ ] Validate pixel and normalized coordinates against rendered page dimensions.
- [ ] Generate deterministic Duy/Vân/owner assignment and preserve existing per-PDF split if valid.
- [ ] Run bootstrap validation and record counts/source checksums.

### Task 2: Local backend and rendering

**Files:** create `app/server.py`, `app/config.py`, `tests/test_server.py`.

- [ ] Test API response for dataset/invoice/page, atomic annotation save/reload, invalid field/status/bounds rejection, and path traversal rejection.
- [ ] Implement localhost-only stdlib server with JSON APIs, manifest-scoped PDF access, 300-DPI lazy page render/cache and annotation atomic writes.
- [ ] Add assignment-scoped retrieval and import/export endpoints; return clear errors and no partial writes.

### Task 3: Annotation UI

**Files:** create `app/static/index.html`, `app/static/app.js`, `app/static/styles.css`, `tests/test_ui_contract.py`.

- [ ] Add contract checks for field keys, save payload, canvas bounds and keyboard focus.
- [ ] Build responsive three-panel page with invoice search/filters, PDF image/canvas overlay, annotation property editor and history.
- [ ] Implement draw/move/resize/delete boxes, field/layout labels, transcript, row_id, recognition provenance, explicit status, save feedback and undo.
- [ ] Confirm browser rendering at desktop and narrow widths; ensure keyboard controls and visible focus.

### Task 4: Assignment, merge, validation and export

**Files:** create `tools/validate_dataset.py`, `tools/merge_annotations.py`, `tools/export_dataset.py`, tests for each.

- [ ] Test confirmed vs pending separation, same-invoice split leakage, duplicate IDs, checksum mismatch, conflicting labels and row integrity.
- [ ] Implement deterministic validation and machine-readable report.
- [ ] Implement per-invoice packages and merge that stops on conflicting content, with backup/report.
- [ ] Export confirmed and review sets separately, generic JSONL/CSV and documented PaddleOCR detector labels where validated.
- [ ] Build ZIP and verify image/annotation/manifest counts and references.

### Task 5: Colab and collaborator docs

**Files:** create `notebooks/Prepare_Field_Layout_Data_Colab.ipynb`, README, DATA_SCHEMA, COLAB_GUIDE, CONTRIBUTING, DATA_LICENSE.

- [ ] Verify notebook JSON structure and execute equivalent validation code locally where practical.
- [ ] Notebook clones repo at explicit commit, validates schema/data, mounts Drive and writes timestamped report/export without modifying source.
- [ ] Document fork/clone, Duy/Vân assignment, PR, conflict merge and Colab steps.

### Task 6: End-to-end verification and publish

- [ ] Run unittest suite, bootstrap dry-run/integrity, export/merge self-checks, `git diff --check`.
- [ ] Run app and manually verify PDF render, box annotation, save/reload, history edit, filters and assignment flow.
- [ ] Confirm 208 PDF checksums and source progress files are unchanged; inspect staged files for secrets and unintended artifacts.
- [ ] Commit and push to the existing repository's initial `main` branch only if remote is still empty; otherwise push a feature branch and preserve remote history.
- [ ] Verify remote commit and public file listing after push; report exact URLs and limits.
