> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# METRIC / DASHBOARD / ALERT ENGINE — SPEC

**Phiên bản:** 1.0
**Owner:** SA Lead + BA Lead
**Wave:** 1 (mở rộng)

---

## 1. Mục tiêu
- KPI/KRI có **owner**, **công thức**, **lineage** rõ ràng.
- Dashboard mọi role drill-down được về record nguồn.
- Alert đúng người, đúng kênh, đúng thời điểm; có escalation.

## 2. Cốt lõi DocType

### 2.1 AC Metric Definition
| Field | Mô tả |
|-------|-------|
| metric_id | `MET-W1-001` |
| metric_name | Hiển thị |
| business_owner | User |
| data_owner | User |
| description | Định nghĩa nghiệp vụ |
| formula | Plain text + JSON spec |
| source_doctype | Bảng nguồn |
| source_filter | JSON filter |
| data_lineage | Mô tả chuỗi từ event/record nguồn → công thức |
| period_grain | Day/Week/Month/Quarter/Year |
| target_value | Số mục tiêu (nếu có) |
| threshold_warning / threshold_critical | – |
| dashboard_widget_ref | Link AC Dashboard Widget (1..n) |
| state | draft / approved / deprecated |

### 2.2 AC Dashboard Snapshot
| Field | Mô tả |
|-------|-------|
| metric_id | – |
| period_from / period_to | – |
| value | – |
| dimensions | JSON (department, criticality, vendor…) |
| computed_at | Datetime |
| computed_by | system / user |
| source_records_count | Int |
| source_records_sample | JSON sample (ID list, capped) |

### 2.3 AC Dashboard Widget
| Field | Mô tả |
|-------|-------|
| widget_id, widget_type (chart/kpi/list), metric_id, role_audience, drill_down_route, layout_position |

### 2.4 AC Alert Rule
| Field | Mô tả |
|-------|-------|
| rule_id | – |
| rule_type | Schedule / Trigger event / Threshold |
| event_type / metric_id / condition | – |
| recipients | Table (user, role, channel) |
| escalation | Table (after_minutes, recipient, channel) |
| state | active/inactive |

## 3. Bộ KPI Wave 1 (baseline)

| Metric ID | Tên | Công thức tóm tắt | Source | Owner | Wave |
|-----------|-----|--------------------|--------|-------|------|
| MET-W1-001 | PM Compliance Rate | (PM completed on-time / PM due) × 100 | WO PM | Trưởng VTTBYT | 1 |
| MET-W1-002 | Calibration Compliance Rate | (Cal completed on-time / Cal due) × 100 | WO Cal | Trưởng QLCL | 1 |
| MET-W1-003 | Avg MTTR (h) | sum(repaired-failure_reported)/n | WO CM | KS BME trưởng | 1 |
| MET-W1-004 | MTBF (giờ) | sum(uptime)/n_failures | WO CM + asset | KS BME trưởng | 1 |
| MET-W1-005 | Downtime hours (tháng) | sum(downtime_minutes)/60 | WO CM | Trưởng VTTBYT | 1 |
| MET-W1-006 | License expiring 30/60/90 | count theo bucket | Document Record | Pháp chế | 1 |
| MET-W1-007 | Critical assets with no PM | count | Asset + PM Plan | Trưởng VTTBYT | 1 |
| MET-W1-008 | Open CAPA count + aging | count, days_since_open | CAPA | QMS Lead | 1.5 |
| MET-W1-009 | Recurring failures (≥3/90d) | count | WO CM | KS BME trưởng | 1 |
| MET-W1-010 | Spare parts shortage events | count | Stock + WO | Kho | 1.5 |
| MET-W1-011 | Vendor SLA breach | count | WO + Contract | Procurement | 1 |
| MET-W1-012 | Cost per asset (PM+CM) | sum(cost)/asset | WO | Trưởng VTTBYT | 1 |
| MET-W1-013 | Asset uptime (%) | (1 − downtime/operating_hours) × 100 | WO + asset | Trưởng VTTBYT | 1 |
| MET-W1-014 | Documents missing per critical asset | count | Asset + Doc inventory | QMS | 1 |
| MET-W1-015 | Adoption rate WO | WO via system / total | WO | PMO | 1 (hypercare) |
| MET-W1-016 | Recall response time | avg(disclosure_due − recall_confirmed) | Compliance Case | QMS Lead | 1.5 |
| MET-W1-017 | Audit trail completeness | events with full payload / total | LE | Auditor | 1 |
| MET-W1-018 | Stand-down assets count | count | Asset state | Trưởng VTTBYT | 1 |
| MET-W1-019 | Avg validate time after WO complete | avg | WO | QMS Officer | 1 |
| MET-W1-020 | Effectiveness fail rate CAPA | fail/total | CAPA | QMS Lead | 1.5 |
| MET-W1-021 | Time-to-assign WO Critical | avg(assigned_at − reported_at) | WO CM | KS BME trưởng | 1 |
| MET-W1-022 | Documents superseded per quarter | count | Document Record | QMS | 1.5 |
| MET-W1-023 | Inspection findings open | count | NC + Audit | QMS | 1.5 |
| MET-W1-024 | License expired & in-use | count | Doc + Asset | Compliance | 1 |
| MET-W1-025 | New asset commissioned (tháng) | count | Lifecycle Event | Trưởng VTTBYT | 1 |

(25 KPI baseline Wave 1 — sẽ mở rộng Wave 2 lên ~50, Wave 3 lên ~80.)

## 4. Snapshot strategy

- Daily snapshot cho metric high-volatility (MET-W1-005, 011, 015).
- Weekly snapshot cho metric trung bình.
- Monthly snapshot bắt buộc cho mọi metric — phục vụ trend.
- Snapshot lưu vào `AC Dashboard Snapshot` để truy lịch sử.
- Drill-down từ snapshot quay về record nguồn qua `source_records_sample` + filter saved.

## 5. Drill-down navigation

Mỗi widget có route:
- KPI summary → list filtered → record detail → Lifecycle Event timeline.
- Ví dụ: `MET-W1-001 PM Compliance` → list WO PM completed late → WO detail → Lifecycle Event của asset.

## 6. Alert engine

### 6.1 Rule types
- **Schedule**: cron (license expiry, PM due).
- **Event-based**: dispatch khi LE xuất hiện (ví dụ `wo_breach_sla`).
- **Threshold**: snapshot vượt threshold (ví dụ Open CAPA > 50).

### 6.2 Channels
- Email (Frappe Email Queue).
- In-app notification.
- SMS (Wave 1.5 — tích hợp gateway nội bộ).
- Webhook outbound.

### 6.3 Escalation
- Mỗi rule có 0..N tầng escalation, mỗi tầng có timeout.
- Nếu recipient cấp 1 ack → dừng; nếu không → cấp 2.

## 7. Performance

- Snapshot job chạy nền; không block UI.
- Heavy queries dùng materialized view hoặc aggregated table.
- Dashboard target render ≤ 2s p95.

## 8. Permission
- Mỗi widget có `role_audience`.
- Field-level: số tài chính chỉ cho Trưởng KTTC + BGĐ.
- Drill-down vẫn enforce User Permission của record nguồn.

## 9. API
- `assetcore.metrics.compute(metric_id, period)`
- `assetcore.metrics.list_for_role(role)`
- `assetcore.metrics.snapshot_replay(metric_id, period)`

## 10. Tiêu chí nghiệm thu Wave 1
- 25 KPI hoạt động.
- 100% widget có drill-down về record nguồn.
- Snapshot daily + monthly chạy đúng giờ.
- Alert rule baseline (≥ 30 rule) hoạt động.
- Dashboard role-based: BGĐ, Trưởng VTTBYT, QMS, KS BME, KTV, Pháp chế.
