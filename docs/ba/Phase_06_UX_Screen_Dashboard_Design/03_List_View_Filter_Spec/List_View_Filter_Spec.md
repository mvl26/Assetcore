> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# LIST VIEW & FILTER SPEC — ASSETCORE

**Phiên bản:** 1.0
**Owner:** UX + BA Lead

---

## 1. Quy ước
- Mỗi DocType có "default list view" cho mỗi role chính.
- Saved filter cho các tác vụ phổ biến (Today's WO, License expiring 30, Open CAPA…).
- Quick filter chip ở header (state, criticality, dept).
- Bulk action: assign, close, export.

## 2. AC Medical Asset

### Default columns
- asset_code, device_model, department, criticality, state, last_pm_date, next_pm_due, next_calibration_due, license_status (computed), risk_level (computed).

### Saved Filters
| Filter | Logic |
|--------|-------|
| Tài sản của khoa tôi | department in user.department |
| Critical assets | criticality A |
| License expired & in-use | license_status=expired AND state=released_for_use |
| PM overdue | next_pm_due < today |
| Cal overdue | next_calibration_due < today |
| Stand-down | state=stand_down |
| Imported pending review | imported_from_legacy=1 AND state=draft |

### Bulk actions
- Bulk Stand-down (with reason).
- Bulk Movement (with target location).
- Bulk Issue QR/RFID.

## 3. AC Work Order

### Default columns
- wo_no, wo_type, medical_asset, priority, state, sla_due_at, assigned_user, planned_end_at, downtime_minutes (CM).

### Saved Filters
| Filter |
|--------|
| WO của tôi (assigned_user=self) |
| WO đến hạn hôm nay |
| WO breach SLA |
| WO PM tuần tới |
| WO CM Critical open |
| WO chưa validate |

### Bulk
- Assign to team.
- Close (admin).
- Export to CSV.

## 4. AC Failure Report

### Columns
- fr_no, asset, severity, reporter, reported_at, linked_wo, state.

### Saved Filters
| Filter |
|--------|
| FR cần triage (severity Critical/High, state=submitted) |
| FR ngày hôm nay |
| FR theo khoa của tôi |
| FR đã merge |

## 5. AC Document Record

### Columns
- doc_no, document_type, subtype, linked_asset (count or single), version, effective_date, expiry_date, state.

### Saved Filters
| Filter |
|--------|
| LEGAL hết hạn 30/60/90 ngày |
| Tài liệu chờ duyệt |
| Document liên quan asset của tôi |
| Cal Cert mới phát hành |

## 6. AC QMS Artifact

### Columns
- artifact_no, tier, title, version, owner_unit, effective_date, next_review_date, state.

### Saved Filters
| Filter |
|--------|
| Tier 1/2 effective |
| Artifact tới hạn review |
| Artifact của đơn vị tôi |
| Pending approval |

## 7. AC CAPA

### Columns
- capa_no, source, severity, owner, state, days_open, next_effectiveness_check.

### Saved Filters
| Filter |
|--------|
| CAPA của tôi (owner) |
| CAPA quá hạn |
| Effectiveness pending |
| CAPA closed Q1/Q2/… |

## 8. AC Compliance Case

### Columns
- case_no, case_type, severity, linked_asset (count), state, days_open, disclosure_due_at.

### Saved Filters
| Filter |
|--------|
| Open Critical |
| Recall in progress |
| Disclosure due trong 24h |
| License expired cases |

## 9. AC Risk Entry

Columns: risk_no, scope, severity, probability, score, status, review_due_date, owner.
Saved filters: High/Critical, Mine, Review due, By scope.

## 10. AC Asset Movement / Stand-Down / Decommission / Disposal

Columns: record_no, asset, from→to / reason, state, approver_progress, dates.
Saved filters: Pending approval (mine), This month, Pending finance step, Pending legal step.

## 11. Quick filter chips

Áp dụng cho mọi list view chính:
- State (multi-select).
- Department (filter scope).
- Criticality.
- Date range (created/effective/closed).

## 12. Mobile list views

- Card layout thay vì bảng.
- Hiển thị 2-3 field chính.
- Swipe action (Quick complete WO, mark as read…).
- Pull-to-refresh.

## 13. Permission-based list filtering

- AC Department Head → tự động filter scope=department.
- AC Vendor SE → tự động filter assigned_user=self + scope assets.
- AC Auditor → toàn bộ + read-only.

## 14. Performance
- Pagination 20-50/page.
- Lazy load.
- Server-side filter.

## 15. Tiêu chí nghiệm thu
- 100% DocType chính có list view + saved filters.
- Saved filters per role hoạt động.
- Bulk action test pass.
- Performance ≤ 1.5s p95 list view 5k record.
