# IMM-17 — Backend Design (Skeleton)

| Mục | Giá trị |
|---|---|
| Module | IMM-17 — Phân tích dự đoán |
| Trạng thái | Skeleton — chỉ liệt kê tên DocType + service + scheduler. Field, signature chi tiết sẽ scaffold trong sprint Wave 3. |
| Cập nhật | 2026-05-10 |

> Tuân thủ R-02 CLAUDE.md `ba/`: **3-tier strict** (API → Service → Controller). Không viết nghiệp vụ trong controller.

---

## 1. DocType dự kiến

| DocType | Prefix | Submittable | Naming | Mục đích |
|---|---|---|---|---|
| `AC Predictive Insight` | `AC ` | No | `PI-.YYYY.-.######` (theo BA Phase_03 §04) | Lưu output 1 lần inference / asset |
| `IMM Predictive Model` | `IMM ` | No | `field:model_name` | Đăng ký + version model |
| `IMM Predictive Run Log` | `IMM ` | No | `naming_series:` | Log mỗi lần chạy pipeline (status, duration, asset_count) |
| `IMM Predictive Feature Snapshot` (Wave 3 cuối) | `IMM ` | No | — | Lưu feature vector phục vụ replay/audit |

> Field detail (fieldname, type, mandatory) *(Thiết kế trong sprint Wave 3 — dùng skill `assetcore-doctype-designer`)*. Lưu ý sẵn:
> - `AC Predictive Insight.name` đã được BA chốt prefix `PI-` (xem `ba/Phase_03_Data_Domain_Design/04_Transactional_Records_List/Transactional_Records_List.md` line 71).
> - `AC Asset.replacement_signal` (Check, read-only) đã có trong DocType spec — IMM-17 là module SET field này (xem `DocType_Spec_Normalized.md`).

---

## 2. Workflow

IMM-17 **không** dùng Frappe Workflow JSON (không có docstatus phê duyệt cho insight). Lý do:
- `AC Predictive Insight` là output append-only của model.
- Trạng thái lifecycle (NEW → ACKED → ACTIONED / STALE) lưu qua field `acknowledged` + audit log, không qua state machine Frappe.

`IMM Predictive Model` có thể dùng workflow đơn giản (Draft → Validated → Active → Retired) — *(quyết định trong sprint Wave 3)*.

---

## 3. Service layer

`assetcore/services/imm17.py` (sẽ scaffold):

| Function | Mô tả 1 dòng | Tier |
|---|---|---|
| `run_weekly_pipeline()` | Entry point cron — gọi extract → feature → inference → persist | Service |
| `run_for_asset(asset_name)` | On-demand inference cho 1 asset | Service |
| `extract_history(asset_name)` | Pull lifecycle event + WO + calibration | Repository |
| `build_features(history)` | Tạo feature vector | Service |
| `score(features, model_version=None)` | Inference, trả failure_score + replacement_score | Service |
| `persist_insight(asset, score, factors)` | Insert `AC Predictive Insight` + audit | Service |
| `emit_replacement_signal(asset, insight)` | Tạo Lifecycle Event nếu vượt threshold | Service |
| `acknowledge_insight(insight_name, decision, reason)` | UC-17-03 — actor xác nhận | Service |
| `register_model(version, artifact_ref)` | UC-17-04 — đăng ký model mới | Service |
| `activate_model(version)` | Chuyển model sang Active | Service |
| `whatif_pm_cycle(asset, proposed_cycle_months)` | UC-17-05 — ước lượng (read-only) | Service |

> Signature chi tiết + return type *(Thiết kế trong sprint Wave 3)*.

---

## 4. Repository layer

`assetcore/repositories/predictive_repo.py` (sẽ scaffold):
- `get_lifecycle_history(asset, since)` → query `Asset Lifecycle Event`
- `get_pm_history(asset, since)` → query `PM Work Order`
- `get_repair_history(asset, since)` → query `Asset Repair`
- `get_calibration_history(asset, since)` → query `IMM Asset Calibration`
- `get_incident_history(asset, since)` → query `Incident Report`

> Read-only. Không write từ repo này. Tuân quy ước repo (có thư mục `assetcore/repositories/` đã tồn tại).

---

## 5. Hooks & Scheduler

### 5.1 Scheduler events (bổ sung vào `hooks.py` ở Wave 3)

| Tần suất | Cron | Function | Mục đích |
|---|---|---|---|
| weekly | `0 7 * * 0` (đã pre-declare trong BA workflow doc) | `assetcore.services.imm17.run_weekly_pipeline` | Tính `replacement_signal` toàn bộ asset active |
| daily | TBD | `assetcore.services.imm17.check_drift` | Kiểm tra model drift, alert nếu vượt KRI-17-01 |
| quarterly cron | `0 2 1 1,4,7,10 *` | `assetcore.services.imm17.retrain_trigger` | Trigger retrain offline (nếu enabled) |

### 5.2 Doc events
- Không cần `doc_events` cho `AC Asset` (IMM-17 *đọc* asset, không hook validate/submit).
- `AC Predictive Insight.on_insert` → call `log_audit_event` (R-04 audit hash chain).

### 5.3 Lifecycle Event types (mới, bổ sung vào `services/shared/constants.py` Wave 3)
- `replacement_signal_emitted` (đã pre-declared trong `ba/Tap_4_Workflow_Permission.txt`)
- `predictive_run_completed`
- `predictive_model_activated`
- `predictive_insight_acknowledged`

> Hằng số cụ thể *(Thiết kế trong sprint Wave 3, theo CONVENTIONS.md §3 ErrorCode/EventType)*.

---

## 6. Permission

| Role | AC Predictive Insight | IMM Predictive Model |
|---|---|---|
| IMM System Admin | Read/Write/Delete | Full |
| IMM Operations Manager | Read + Acknowledge | Read |
| IMM HTM Engineer | Read + Acknowledge + WhatIf | Read |
| IMM QA Officer | Read | Read |
| IMM Auditor | Read | Read |
| Data Scientist (custom role — Wave 3) | Read all | Full (training/deploy) |
| Vendor Engineer | Không có quyền | Không có quyền |

> Permission Query Conditions (theo R-08): nếu cần scope theo khoa, bổ sung handler `assetcore.permissions.predictive_insight_query`. *(Quyết định khi BE scaffold.)*

---

## 7. Audit Trail (R-04)

Mỗi event sau bắt buộc gọi `assetcore.utils.lifecycle.log_audit_event(...)`:
- Inference completed cho 1 asset
- Insight acknowledged
- Model activated / retired
- Threshold thay đổi (system config)

Audit record nối vào hash chain SHA-256 của asset; verify qua `verify_audit_chain(asset)`.

---

## 8. Dependencies (data layer phải sẵn sàng)

**Bắt buộc** trước khi go-live IMM-17:
- IMM-07 KPI snapshot DocType đã ship + có ≥6 tháng dữ liệu.
- IMM-08/09/11/12 đã ship Wave 1 (đã có).
- Lifecycle Event Engine ổn định, không có gap.
- Audit chain verify pass cho mẫu ≥100 asset.

**Tuỳ chọn** (Wave 3 sau):
- IoT Telemetry pipeline (INT-13 outbound + inbound endpoint).
- Vendor ML service contract đã ký.
