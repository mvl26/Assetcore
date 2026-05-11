# IMM-04 Light-Touch Audit Report

**Date:** 2026-05-10
**Scope:** Light-touch — fill section gaps vs `docs/template/`, add WHO + GMDN cross-references, refresh README. No content rewrite.

## Audit method

For each file `02–09`, diffed `^#{1,3} ` headings vs corresponding template file. Distinguished:
- **Real content gaps** → patched with minimal explanatory subsection.
- **Casing/rename differences** (e.g. "Kiểm Thử" vs "Kiểm thử") → ignored, not real gaps.
- **Subsection content present but parent header missing** → added the wrapper header.

## Files & sections touched

### `02_Analysis_Design.md`
- Added `## II.1. Phân biệt 3 khái niệm` — distinguishes BPMN / Use Case / Activity Diagram (was missing — file jumped straight from §II header to §II.2 As-Is).
- Added `## III.6. UC ↔ Sequence Diagram mapping` — maps UC-01/04/07 to SD-04-01/02/03 in 03_Diagrams.md.
- Extended `## I.6. Ràng buộc Compliance` with row for QĐ 3107/QĐ-BYT and a "Source documents tham chiếu" block linking to `docs/WHO/` (4 files) and `docs/gmdn/` (3 QĐ files) and `docs/architecture/Ho_so_kien_truc_IMMIS.md`.

### `03_Diagrams.md`
- Added `## II.1. Class Diagram — 2 cấp` wrapper header (existing II.1.a / II.1.b were orphan subsections).
- Added `## III.1. Khi nào vẽ sequence?` — guidance subsection present in template but missing.
- Added `## IV.1. Khi nào dùng?`, `## IV.2. Convention`, `## IV.3. Numbering scheme` — Communication diagram meta sections (only IV.4 existed).
- Added `## V.1. Khi nào vẽ?` — Package diagram rationale (only V.2–V.5 existed).

### `README.md`
- Updated header table: title corrected to "Lắp đặt, Định danh & Kiểm tra Ban đầu", file count fixed to 9, last-updated bumped to 2026-05-10.
- Replaced flat reference list with structured `Tham chiếu` block grouped into Template / Source documents / Codebase ground truth — added WHO (4 files), GMDN (`docs/gmdn/`), architecture (`Ho_so_kien_truc_IMMIS.md`), DocType + Workflow paths.

## Files NOT modified (already adequate)

- `04_Backend_Design.md` — only diff vs template is "Pattern thực tế" header style; content of §4/§4b/§5 fully present.
- `05_API_Specification.md` — §0 catalog, §1.1–1.5, §4 (Webhook/Realtime Events) all present; missing items in diff were heading-text differences (e.g. "Endpoint chi tiết" vs "Endpoint").
- `06_Frontend_Design.md` — §3.a/3.b/3.c, §7 / 7d / 7e all present (diff caught minor wording variations).
- `07_Testing_QA.md`, `08_Deployment.md`, `09_Release.md` — diff hits were 100% Title-Case-vs-sentence-case and "Phần III — Security Review" vs "Phần III — Security Review (gate)". Content fully matches template; no edits made.

## Cross-reference coverage added

- **WHO HTM**: 3 source files now linked from `02 §I.6` and `README.md`.
- **GMDN / NĐ98 risk class**: 3 QĐ files linked from `02 §I.6` (with QĐ 3107 specifically tied to VR-07 Clinical Hold gate) and `README.md`.
- **Architecture**: `docs/architecture/Ho_so_kien_truc_IMMIS.md` linked from both.

## Anti-actions taken

- Did NOT rewrite or restructure existing prose.
- Did NOT modify real `docs/imm-04/` — all edits in sandbox output dir only.
- Did NOT add new diagrams, KPIs, or business rules.
