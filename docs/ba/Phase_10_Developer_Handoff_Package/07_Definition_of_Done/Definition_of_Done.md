> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DEFINITION OF DONE — ASSETCORE WAVE 1

**Phiên bản:** 1.0
**Owner:** Tech Lead + QA Lead

---

## 1. Mục đích
Định nghĩa rõ "Done" cho mỗi cấp: Story / Sprint / Wave / Engineer Hand-off.

## 2. DoD cấp Story

Một user story được "Done" khi tất cả tiêu chí sau đạt:

- [ ] Code implement đầy đủ acceptance criteria.
- [ ] Unit test viết + pass; coverage ≥ 70%.
- [ ] Integration test (nếu áp dụng) pass.
- [ ] PR tạo + ≥ 1 reviewer approve (≥ 2 cho QMS-critical).
- [ ] Linter + format pass.
- [ ] Security checklist:
  - Không hardcode secret.
  - Permission enforced.
  - Input validate.
  - Audit trail tạo (nếu QMS-critical).
- [ ] DocType change → Naming convention compliance.
- [ ] Workflow change → Lifecycle Event đúng publish.
- [ ] UX change → mobile-friendly verified.
- [ ] Documentation:
  - Inline comment cho logic phức tạp.
  - README updated nếu cần.
  - API docs auto-generated.
- [ ] Migration script (nếu có schema change) idempotent + tested.
- [ ] Sample data updated (nếu cần).
- [ ] QA verify trên DEV/UAT.
- [ ] Story moved to "Done" trên board.

## 3. DoD cấp Sprint

Sprint được "Done" khi:
- [ ] Tất cả story trong sprint commit Done.
- [ ] Sprint review + retro hoàn tất.
- [ ] Demo cho stakeholder pass.
- [ ] CI/CD pipeline green.
- [ ] Velocity recorded.
- [ ] Backlog refinement cho sprint sau.
- [ ] Bug carry-over < 5 (mỗi backlog tracked).
- [ ] Smoke test trên UAT pass.

## 4. DoD cấp Wave 1 (Go-live ready)

Wave 1 được "Done" khi:

### 4.1 Functional
- [ ] 6 module IMM (04, 05, 08, 09, 11, 12) hoạt động đầy đủ.
- [ ] 6 engine cốt lõi vận hành.
- [ ] 90+ user stories Wave 1 Done.
- [ ] 8 Golden Scenarios pass UAT.

### 4.2 Quality
- [ ] Unit coverage ≥ 70%.
- [ ] Integration test pass 100%.
- [ ] E2E test cover top 30 flows.
- [ ] Performance NFR-P-* met.
- [ ] Security pen-test 0 high/critical open.

### 4.3 Data
- [ ] Migration sign-off đạt:
  - ≥ 95% asset Wave 1.
  - ≥ 90% LEGAL document.
  - ≥ 70% PM/Cal Plan critical.
- [ ] DQ audit ≤ 5% warning, 0 critical.
- [ ] Reconciliation MA ↔ Asset 0 lệch.

### 4.4 QMS
- [ ] 5 QC + 15 PR/SOP + 17 WI/JD + ~30 BM/HS/KPI baseline approved.
- [ ] Training compliance ≥ 80% role chính.
- [ ] CAPA + Compliance Case workflow vận hành thực ≥ 1 chu kỳ.

### 4.5 Operations
- [ ] 4 environment + DR ready.
- [ ] Backup + restore drill pass.
- [ ] DR drill thành công ≥ 1 lần.
- [ ] Monitoring + alert hoạt động.
- [ ] Hypercare team + plan ready.

### 4.6 Governance
- [ ] Audit trail 100% transition QMS-critical.
- [ ] E-signature enforced.
- [ ] Permission test pass.
- [ ] Vendor scoped access verified.

### 4.7 Sign-off
- [ ] BGĐ.
- [ ] Trưởng VTTBYT.
- [ ] Trưởng QLCL.
- [ ] Trưởng CNTT.
- [ ] Trưởng KTTC.

## 5. DoD cấp Engineer Hand-off

Hand-off giữa BA → Dev được "Done" khi:
- [ ] Acceptance criteria clear (Phase_08/02).
- [ ] DocType spec lock (Phase_03/05).
- [ ] Workflow spec lock (Phase_04/01).
- [ ] Permission matrix lock (Phase_04/02).
- [ ] UX wireframe approved (Phase_06).
- [ ] API contract OpenAPI lock (Phase_07/05).
- [ ] Test data prepared (Phase_10/05).
- [ ] Sample seed available (Phase_10/04).
- [ ] DoR per story signed.

## 6. DoD cấp Hypercare Exit

Hypercare exit khi:
- [ ] Adoption rate WO ≥ 90%.
- [ ] 0 Critical bug open.
- [ ] ≤ 5 High bug open.
- [ ] KPI dashboard có dữ liệu 4 tuần real.
- [ ] Stakeholder satisfaction ≥ 4/5.
- [ ] Operations team hand-off complete.
- [ ] Lessons learned documented.

## 7. Ký nhận DoD per Wave 1

| Vai trò | Họ tên | Ngày | Chữ ký |
|---------|--------|------|--------|
| Tech Lead |  |  |  |
| QA Lead |  |  |  |
| BA Lead |  |  |  |
| QMS Lead |  |  |  |
| PMO |  |  |  |
| Sponsor (BGĐ) |  |  |  |
