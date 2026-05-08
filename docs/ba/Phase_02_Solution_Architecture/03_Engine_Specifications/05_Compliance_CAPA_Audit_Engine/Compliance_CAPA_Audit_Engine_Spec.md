> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# COMPLIANCE / CAPA / AUDIT ENGINE — SPEC

**Phiên bản:** 1.0
**Owner:** SA Lead + QMS Lead
**Wave:** 1 (cơ bản) → 1.5 (đầy đủ)

---

## 1. Mục tiêu
- Phát hiện non-compliance → xử lý → đóng — có audit trail và effectiveness check.
- Hỗ trợ recall, FSCA, change control, risk register, management review.
- Là **đường thoát** cho mọi exception nghiêm trọng từ engine khác.

## 2. DocType chính

### 2.1 AC Nonconformity (NC)
| Field | Mô tả |
|-------|-------|
| nc_no | Naming series |
| source | WO/Audit/Complaint/Inspection/Recall/Internal Report |
| severity | 1 (critical) / 2 (major) / 3 (minor) |
| reported_at | Datetime |
| reporter_user | – |
| description | Long Text |
| linked_asset / linked_wo / linked_document | tùy nguồn |
| state | draft → triaged → linked_to_capa → closed |

### 2.2 AC CAPA
| Field | Mô tả |
|-------|-------|
| capa_no | Naming series |
| source_nc | Link NC (1..n qua child) |
| capa_type | Corrective / Preventive / Both |
| owner_user | – |
| approver_user | – |
| root_cause | Long Text |
| rca_method | 5 Why / Fishbone / FMEA / Other |
| action_plan | Table AC CAPA Action |
| effectiveness_check_plan | Table (timepoint 30/60/90, owner, criteria) |
| effectiveness_result | Pass/Fail |
| state | draft → approved → in_progress → effectiveness_pending → closed → reopened |

### 2.3 AC CAPA Action (child)
| Field | Mô tả |
|-------|-------|
| action_no, description, owner_user, due_date, status, evidence |

### 2.4 AC Compliance Case
| Field | Mô tả |
|-------|-------|
| case_no | Naming series |
| case_type | License Expired / PM Overdue / Cal Overdue / Recall / FSCA / Audit Finding / Vendor SLA Breach / Other |
| linked_asset / linked_doc / linked_wo / linked_capa | – |
| severity | 1..3 |
| regulatory_authority | Bộ Y tế / Sở Y tế / Internal / ISO Auditor / JCI |
| disclosure_required | Check |
| disclosure_due_at | Datetime |
| state | open → investigating → action_in_progress → resolved → closed |
| owner_user | – |
| evidence_refs | Table |

### 2.5 AC Recall (subtype Compliance Case)
- Bổ sung field: scope (model/lot/batch), affected_assets table, action_required (replace/repair/quarantine), notification_log.

### 2.6 AC Risk Entry
| Field | Mô tả |
|-------|-------|
| risk_no | – |
| scope | Asset / Process / Project |
| linked_subject | Dynamic Link |
| severity / probability / score | – |
| mitigation_plan | – |
| status | open / mitigated / accepted / closed |
| review_due_date | – |

### 2.7 AC Change Control Request
| Field | Mô tả |
|-------|-------|
| cr_no | – |
| change_scope | Document / Process / Configuration / Asset Setting |
| linked_subject | – |
| reason | – |
| impact_analysis | – |
| approver_chain | Table |
| state | draft → assessed → approved → implemented → verified → closed |

### 2.8 AC Audit (Internal Audit)
| Field | Mô tả |
|-------|-------|
| audit_no | – |
| audit_type | Internal / External / Pre-certification |
| period_from / period_to | – |
| scope | Modules / Departments |
| auditor_team | Table |
| findings | Table (NC link) |
| state | planned → in_progress → reported → closed |

### 2.9 AC Management Review
| Field | Mô tả |
|-------|-------|
| review_period | – |
| inputs | Table (KPI, audit, CAPA backlog, risk, customer feedback…) |
| outputs | Table (decisions, resource adjustments, training needs) |
| state | scheduled → completed |

## 3. Workflow chính

### 3.1 NC → CAPA
```
NC opened ─► triaged
              │
              ├─► severity 1: open CAPA in 24h (BR-051)
              ├─► severity 2: open CAPA in 5 days
              └─► severity 3: optional CAPA (decided by QMS)
```

### 3.2 CAPA Lifecycle
```
draft ─► approved ─► in_progress ─► effectiveness_pending ─► closed
                                          │
                                          └─► reopened (if not effective)
```

### 3.3 Recall workflow
1. Vendor/Bộ Y tế thông báo → QMS mở Compliance Case (Recall).
2. Identify scope (qua AC Device Model + serial/lot).
3. Bulk create WO type=Recall cho mỗi asset thuộc scope.
4. Disclosure: thông báo Bộ Y tế trong 48h (SLA-QMS-05).
5. Theo dõi đóng từng asset.
6. Đóng Compliance Case khi đã xử lý 100% asset.

### 3.4 Change Control
- Mọi change ảnh hưởng QMS-critical (SOP, asset setting trọng yếu, role/permission, integration contract) phải qua CR.
- CR được CCB phê duyệt (Phase_00/04).

## 4. Hooks tự động
- `WO CM lặp ≥ 3/90 ngày` → tự sinh CAPA (BR-035).
- `License expired & asset in use` → tự sinh Compliance Case (BR-014).
- `Calibration Fail` → stand-down + CAPA (BR-042).
- `PM overdue ≥ X ngày` → Compliance Case (BR-026).

## 5. Effectiveness Check
- Mỗi CAPA action close có ≥ 1 timepoint check (vd 30/60/90 ngày).
- Cron tạo task check mỗi timepoint.
- Owner assess pass/fail; QMS Lead duyệt.
- Fail → reopen CAPA + thêm action.

## 6. Audit Trail
- Mọi CAPA action close, Compliance Case state change, Recall step → publish Lifecycle Event (LE-22..27).
- Các hành động CRITICAL (close CAPA, close case) yêu cầu e-signature.

## 7. Permissions
- Open NC: bất kỳ user.
- Triage NC + CAPA: AC QMS Officer + AC QMS Lead.
- Close CAPA: AC QMS Lead.
- Compliance Case Recall: AC QMS Lead + AC Pháp chế.
- Risk Entry: AC QMS Officer + scope owner.

## 8. Public API
- `assetcore.compliance.open_nc(...)`
- `assetcore.compliance.open_capa(...)`
- `assetcore.compliance.open_case(case_type, ...)`
- `assetcore.compliance.bulk_recall(model, lot, action)`
- `assetcore.compliance.run_effectiveness_check(capa)`

## 9. Tiêu chí nghiệm thu Wave 1
- NC + CAPA chu trình đầy đủ.
- Compliance Case 4 case_type cơ bản (License Expired, PM Overdue, Cal Overdue, Vendor SLA Breach) tự sinh đúng.
- Effectiveness check chu kỳ chính xác.
- Recall (Wave 1.5) bulk create + tracking đến đóng.
- Risk Register có ≥ 30 risk baseline trên Wave 1 module.
