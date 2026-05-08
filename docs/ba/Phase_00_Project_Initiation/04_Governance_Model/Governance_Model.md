> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# GOVERNANCE MODEL — ASSETCORE

**Phiên bản:** 1.0
**Owner:** PMO
**Ngày:** 2026-05-05

---

## 1. Mục tiêu Governance

Bảo đảm dự án AssetCore được điều hành xuyên suốt theo 4 nguyên tắc:
1. **Quyết định kiến trúc và nghiệp vụ phải được phê duyệt qua hội đồng đúng thẩm quyền** — không cá nhân quyết.
2. **Mọi thay đổi phạm vi/dữ liệu/quy trình** đi qua Change Control Board.
3. **Mọi rủi ro Cao** phải được đưa lên Steering trong vòng tối đa 5 ngày làm việc.
4. **Mọi artifact QMS** phải qua chu trình draft → review → approve → effective.

## 2. Cấu trúc tổ chức dự án

```
                 ┌──────────────────────────┐
                 │   STEERING COMMITTEE      │
                 │   (BGĐ + Trưởng phòng C1) │
                 └────────────┬──────────────┘
                              │
       ┌──────────────────────┼─────────────────────────┐
       │                      │                         │
┌──────▼──────┐       ┌───────▼────────┐       ┌────────▼────────┐
│ Architecture│       │ Change Control │       │  QMS Committee  │
│ Review Board│       │     Board      │       │                 │
│   (ARB)     │       │     (CCB)      │       │                 │
└──────┬──────┘       └───────┬────────┘       └────────┬────────┘
       │                      │                         │
       └──────────────────────┼─────────────────────────┘
                              │
                       ┌──────▼──────┐
                       │   PMO       │
                       └──────┬──────┘
                              │
                  ┌───────────┼───────────┐
                  │           │           │
              ┌───▼───┐   ┌───▼───┐   ┌───▼───┐
              │  BA   │   │  SA   │   │  Dev  │
              │ Team  │   │ Team  │   │ Team  │
              └───────┘   └───────┘   └───┬───┘
                                          │
                                      ┌───▼───┐
                                      │  QA   │
                                      └───────┘
```

## 3. Hội đồng & Vai trò

### 3.1 Steering Committee
- **Thành phần:** Sponsor (BGĐ), Trưởng VTTBYT, Trưởng CNTT, Trưởng QLCL, Trưởng KTTC.
- **Thẩm quyền:** Phê duyệt charter, ngân sách, mốc lớn, rủi ro Cao, scope change ảnh hưởng wave.
- **Tần suất:** 2 tuần/lần + ad-hoc khi escalation.
- **Quorum:** ≥ 4/5; Sponsor bắt buộc có mặt cho quyết định ngân sách & wave.

### 3.2 Architecture Review Board (ARB)
- **Thành phần:** SA Lead (chủ tịch), BA Lead, IT Lead, QMS Lead, Frappe Partner Tech Lead.
- **Thẩm quyền:** Phê duyệt blueprint, engine spec, DocType lớn, mapping ERPNext core, integration contract, NFR.
- **Tần suất:** Theo gate phase + tuần khi build.
- **Đầu ra bắt buộc:** Architecture Decision Record (ADR) cho mọi quyết định không tầm thường.

### 3.3 Change Control Board (CCB)
- **Thành phần:** PMO (chủ tịch), ARB đại diện, owner nghiệp vụ liên quan, QMS Lead.
- **Thẩm quyền:** Phê duyệt mọi change request có ảnh hưởng đến scope, timeline, dữ liệu master, workflow đã baseline.
- **Tần suất:** Tuần.
- **Quy trình:** CR submitted → impact analysis (BA + SA) → CCB review → approve/defer/reject → log.

### 3.4 QMS Committee
- **Thành phần:** QMS Lead (chủ tịch), Trưởng QLCL, Trưởng VTTBYT, đại diện KSNK, đại diện ARB.
- **Thẩm quyền:** Phê duyệt QMS artifact 4 tầng, CAPA, change control nội dung QMS, management review.
- **Tần suất:** Tháng.

### 3.5 PMO
- **Thành phần:** PM, Coordinator, Risk Officer.
- **Trách nhiệm:** Lịch trình, ngân sách, rủi ro, log dependency, communication, baseline.
- **Tần suất:** Hàng ngày trong build phase; tuần ngoài build.

## 4. RACI tổng hợp (cấp Phase)

| Phase | Sponsor | Steering | ARB | CCB | QMS | PMO | BA | SA | Dev | QA | Owner Nghiệp vụ |
|-------|---------|----------|-----|-----|-----|-----|----|----|----|----|------------------|
| 00 Initiation | A | C | I | I | I | R | C | C | I | I | C |
| 01 Discovery & BA | I | C | C | I | C | A | R | C | I | I | R |
| 02 Solution Architecture | I | I | A | I | C | C | C | R | I | I | C |
| 03 Data & Domain | I | I | A | C | C | C | C | R | C | I | C |
| 04 Process & Workflow | I | I | C | A | C | C | R | C | I | I | R |
| 05 QMS & Governance | I | I | C | C | A | C | C | C | I | I | R |
| 06 UX & Dashboard | I | I | C | I | C | C | R | C | I | I | C |
| 07 Integration & API | I | I | A | C | C | C | C | R | C | I | C |
| 08 QA Design | I | I | C | I | C | C | C | C | C | A | C |
| 09 Implementation Plan | I | A | C | C | C | R | C | C | C | C | C |
| 10 Hand-off | A | C | A | C | C | R | C | C | C | C | C |

(R = Responsible, A = Accountable, C = Consulted, I = Informed)

## 5. Quy trình ra quyết định

### 5.1 Architecture Decision
1. SA / BA / Dev đề xuất → ADR draft.
2. ARB review trong sprint → quyết định Yes / No / Need-more-info.
3. ADR ghi rõ: bối cảnh, lựa chọn, quyết định, hệ quả, alternatives bị loại.
4. ADR lưu tại `Phase_02_Solution_Architecture/04_Build_vs_Configure_Decision_Log/` với mã ADR-XXXX.

### 5.2 Change Request
1. Stakeholder submit CR template.
2. BA + SA làm impact analysis trong 3 ngày làm việc.
3. CCB phê duyệt / hoãn / từ chối.
4. Nếu approved → cập nhật baseline (scope/plan/spec) + thông báo team + log audit.

### 5.3 Risk Escalation
- Rủi ro Cao: escalate Steering trong ≤ 5 ngày làm việc.
- Rủi ro Trung bình: PMO xử lý hàng tuần, báo cáo Steering bằng dashboard.
- Rủi ro Thấp: log + theo dõi.

## 6. Quyền truy cập & Segregation of Duty (cấp dự án)

- BA không tự sửa DocType trên DEV/UAT.
- Dev không tự duyệt UAT scenario.
- QA không là người viết user story và là người approve cho cùng story đó.
- Migration team không có quyền xóa audit log.
- Tất cả quyền administrator trên PROD do IT Lead nắm + 1 backup; mọi hành động ghi log.

## 7. Tài liệu Governance

- Steering Meeting Minutes
- ARB Meeting Minutes + ADR Log
- CCB Change Request Log
- QMS Committee Minutes
- Risk Register (live)
- Issue Log
- Dependency Log
- Decision Log tổng hợp

## 8. Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| Sponsor |  |  |
| Trưởng QLCL |  |  |
| Trưởng VTTBYT |  |  |
| Trưởng CNTT |  |  |
| PMO |  |  |
