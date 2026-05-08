> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# WAVE 1 COVERAGE MATRIX — Phase 2 Consolidated Spec Coverage Assessment

**Phiên bản:** 2.0 (Phase 2 Final)  
**Owner:** SA Lead + BA Lead + Tech Lead  
**Ngày đánh giá:** 2026-05-06  
**Mục tiêu:** Xác định các khuyết điểm trong tài liệu spec Wave 1 trước IT handover

---

## Huyền thoại: Status Markers

- **✅ COMPLETE** — Đủ chi tiết, rõ ràng, sẵn sàng implement
- **⚠️ PARTIAL** — Có nhưng thiếu chi tiết (ghi rõ lỗ hổng)
- **❌ MISSING** — Chưa có hoàn toàn (cần viết)

---

## Coverage Matrix — 6 Modules IMM ưu tiên Wave 1

### **IMM-04: Commissioning & Asset Registry**

| Tiêu chí | Business Rules | DocType Spec | Workflow States | Permission Matrix | SLA Rules | Test Cases | QMS Artifacts | Golden Scenario |
|----------|----------------|--------------|-----------------|-------------------|-----------|-----------|---------------|-----------------|
| **Trạng thái** | ✅ COMPLETE | ✅ COMPLETE | ✅ COMPLETE | ✅ COMPLETE | ⚠️ PARTIAL | ✅ COMPLETE | ⚠️ PARTIAL | ✅ COMPLETE |
| **Coverage %** | 95% | 100% | 100% | 95% | 60% | 90% | 70% | 100% |

**Khuyết điểm:** 
- SLA cho IQ/OQ/PQ approval flow chưa spec chi tiết
- QMS Tier 1 (Quy chế commission) chưa viết

---

### **IMM-05: Document Management & Compliance**

| Tiêu chí | Business Rules | DocType Spec | Workflow States | Permission Matrix | SLA Rules | Test Cases | QMS Artifacts | Golden Scenario |
|----------|----------------|--------------|-----------------|-------------------|-----------|-----------|---------------|-----------------|
| **Trạng thái** | ✅ COMPLETE | ⚠️ PARTIAL | ✅ COMPLETE | ✅ COMPLETE | ⚠️ PARTIAL | ⚠️ PARTIAL | ❌ MISSING | ✅ COMPLETE |
| **Coverage %** | 100% | 80% | 100% | 100% | 50% | 70% | 0% | 100% |

**Khuyết điểm:**
- Document Record field chưa chi tiết (effective_by, supersede_by, version_number)
- QMS Tier 1 "Quy chế Quản lý Tài liệu" chưa viết
- Test case "Expiry alert" chưa đầy đủ

---

### **IMM-08: Preventive Maintenance & PM Compliance**

| Tiêu chí | Business Rules | DocType Spec | Workflow States | Permission Matrix | SLA Rules | Test Cases | QMS Artifacts | Golden Scenario |
|----------|----------------|--------------|-----------------|-------------------|-----------|-----------|---------------|-----------------|
| **Trạng thái** | ✅ COMPLETE | ✅ COMPLETE | ✅ COMPLETE | ✅ COMPLETE | ⚠️ PARTIAL | ⚠️ PARTIAL | ⚠️ PARTIAL | ✅ COMPLETE |
| **Coverage %** | 95% | 90% | 95% | 90% | 65% | 75% | 60% | 100% |

**Khuyết điểm:**
- PM Task Checklist template (BOM-like) chưa spec
- SLA pause window tính toán chưa test
- QMS Tier 2 "SOP Bảo trì Định kỳ" chưa viết

---

### **IMM-09: Corrective Maintenance & Failure Handling**

| Tiêu chí | Business Rules | DocType Spec | Workflow States | Permission Matrix | SLA Rules | Test Cases | QMS Artifacts | Golden Scenario |
|----------|----------------|--------------|-----------------|-------------------|-----------|-----------|---------------|-----------------|
| **Trạng thái** | ✅ COMPLETE | ⚠️ PARTIAL | ✅ COMPLETE | ⚠️ PARTIAL | ✅ COMPLETE | ⚠️ PARTIAL | ❌ MISSING | ✅ COMPLETE |
| **Coverage %** | 95% | 75% | 100% | 80% | 90% | 65% | 0% | 100% |

**Khuyết điểm:**
- Failure Report field `escalation_path`, `conflict_asset` chưa spec
- Failure Analysis (RCA tree) chưa spec chi tiết
- QMS Tier 2 "SOP CM" chưa viết

---

### **IMM-11: Calibration & Measurement System**

| Tiêu chí | Business Rules | DocType Spec | Workflow States | Permission Matrix | SLA Rules | Test Cases | QMS Artifacts | Golden Scenario |
|----------|----------------|--------------|-----------------|-------------------|-----------|-----------|---------------|-----------------|
| **Trạng thái** | ✅ COMPLETE | ⚠️ PARTIAL | ✅ COMPLETE | ⚠️ PARTIAL | ⚠️ PARTIAL | ⚠️ PARTIAL | ⚠️ PARTIAL | ✅ COMPLETE |
| **Coverage %** | 95% | 75% | 100% | 75% | 70% | 70% | 70% | 100% |

**Khuyết điểm:**
- Cal Record `standard_reference_document`, `acceptance_criteria_json` chưa spec
- Cal Lab Engineer + Vendor Cal Lab permission chưa rõ
- QMS Tier 1 "Quy chế Hiệu chuẩn" chưa hoàn thiện

---

### **IMM-12: Priority 1 CM SLA & Escalation**

| Tiêu chí | Business Rules | DocType Spec | Workflow States | Permission Matrix | SLA Rules | Test Cases | QMS Artifacts | Golden Scenario |
|----------|----------------|--------------|-----------------|-------------------|-----------|-----------|---------------|-----------------|
| **Trạng thái** | ✅ COMPLETE | ⚠️ PARTIAL | ✅ COMPLETE | ⚠️ PARTIAL | ✅ COMPLETE | ⚠️ PARTIAL | ❌ MISSING | ✅ COMPLETE |
| **Coverage %** | 95% | 70% | 100% | 75% | 95% | 60% | 0% | 100% |

**Khuyết điểm:**
- Escalation path spec chưa chi tiết (role → SMS channel)
- WO CM "pause" logic chưa hỗ trợ multi-level
- SoD matrix chưa chính thức
- QMS Tier 2 "SOP CM P1 / SOP Escalation" chưa viết

---

## Summary Coverage Table — Aggregate View

| Module | BR-Coverage | DocType-Coverage | Workflow-Coverage | Perm-Coverage | SLA-Coverage | Test-Coverage | QMS-Coverage | Overall % |
|--------|-------------|------------------|-------------------|---------------|--------------|---------------|--------------|-----------|
| **IMM-04** | 95% | 100% | 100% | 95% | 60% | 90% | 70% | **87%** |
| **IMM-05** | 100% | 80% | 100% | 100% | 50% | 70% | 0% | **71%** |
| **IMM-08** | 95% | 90% | 95% | 90% | 65% | 75% | 60% | **81%** |
| **IMM-09** | 95% | 75% | 100% | 80% | 90% | 65% | 0% | **72%** |
| **IMM-11** | 95% | 75% | 100% | 75% | 70% | 70% | 70% | **79%** |
| **IMM-12** | 95% | 70% | 100% | 75% | 95% | 60% | 0% | **71%** |
| **AVERAGE** | **96%** | **81%** | **99%** | **86%** | **72%** | **72%** | **33%** | **77%** |

---

## ACTION PLAN — Prioritized Gap Fixes

### Critical Path (Week 1-2)
1. ✅ Viết 6 Tier 1 PR (Quy chế) — Policies phải sẵn trước khi dev (~12h)
2. ✅ Tạo AC Failure Analysis + AC Escalation Route DocType (~6h)
3. ✅ Expand DocType schema: WO pause_log, FR escalation_path, Cal standard_reference (~11h)

### Phase 1 (Week 3)
4. ✅ Viết SOP + WI Document Management (IMM-05) (~16h)
5. ✅ Test Document lifecycle + Commission workflow (~24h)

### Phase 2 (Week 4)
6. ✅ Viết SOP + WI PM execution (IMM-08) (~10h)
7. ✅ Test PM plan → WO auto-generation + pause logic (~16h)

### Phase 3 (Week 5-6)
8. ✅ Viết SOP + WI CM / RCA (IMM-09) (~18h)
9. ✅ Test FR mobile + escalation chain (~24h)

### Phase 4 (Week 7-8)
10. ✅ Execute 8 Golden Scenarios end-to-end (~72h)
11. ✅ UAT closure + defect fixes (~30h)

### Phase 5 (Week 9-10)
12. ✅ Final integration testing + sign-off (~35h)

---

## HANDOVER READINESS CHECKLIST

- [ ] All 6 Tier 1 PR (Quy chế) written + approved by QMS Lead
- [ ] All DocType fields normalized per Glossary_Normalized.md
- [ ] All 12 Workflows created + tested (transition pass/fail)
- [ ] All SLA Rules configured + tested escalation
- [ ] All 6 Golden Scenarios executed ≥90% pass on UAT
- [ ] All QMS Artifacts (Tier 1/2/3/4) created
- [ ] Migration tool dry-run pass on 2,000 legacy assets
- [ ] API endpoints documented per Phase 07 spec
- [ ] Mobile offline + E-signature verified
- [ ] ERPNext sync (MA ↔ Asset) bidirectional pass
- [ ] Audit trail: no missing Lifecycle Events
- [ ] Performance: dashboard load p95 < 1s for 1k assets
- [ ] Pen-test: vendor escalation attempt blocked

---

**STATUS:** Phase 2 Gap Analysis Complete  
**NEXT STEP:** Kick-off Phase 3 with prioritized action plan  
**TARGET:** All gaps closed by 2026-07-15 (10 tuần)

