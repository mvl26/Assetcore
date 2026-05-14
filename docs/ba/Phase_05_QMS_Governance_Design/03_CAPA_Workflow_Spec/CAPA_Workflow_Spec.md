# CAPA WORKFLOW SPEC — ASSETCORE (v3)

> **Reconciled to v3 codebase — 2026-05-07.** CAPA chain trong code: `Incident Report` → `IMM RCA Record` → `IMM CAPA Record` (+ `Asset QA Non Conformance` cho NC độc lập). Orchestration trong `assetcore/services/imm12.py`. Tham chiếu: `docs/ba/00_RECONCILIATION_v3.md`.

**Phiên bản:** 3.0
**Owner:** QA Officer + Tech Lead

---

## 1. Mục đích

Đảm bảo **mọi sự cố / nonconformity** trên thiết bị y tế đều được:
1. **Ghi nhận** (`Incident Report` hoặc `Asset QA Non Conformance`).
2. **Phân tích root cause** (`IMM RCA Record` với 5-Why).
3. **Hành động khắc phục + phòng ngừa** (`IMM CAPA Record`).
4. **Đánh giá hiệu lực** trước khi đóng.
5. **Audit chain bất biến** qua `IMM Audit Trail` (SHA-256).

Đáp ứng:
- ISO 13485:2016 §8.5.2 (Corrective Action), §8.5.3 (Preventive Action).
- ISO 14971:2019 (Risk Management for Medical Devices).
- WHO HTM CAPA template.
- NĐ 98/2021 và TT 32/2023 (Việt Nam).

---

## 2. DocType liên quan

| DocType | Submit | Workflow | Mục đích |
|---|---|---|---|
| `Incident Report` | Yes | `IMM-12 Incident Workflow` (7 states) | Ghi nhận sự cố vận hành / lâm sàng |
| `IMM RCA Record` | Yes | `IMM-12 RCA Workflow` (4 states) | Phân tích nguyên nhân (5-Why, Fishbone) |
| `IMM RCA Five Why Step` | Child | – | Bước 5-Why |
| `IMM RCA Related Incident` | Child | – | Liên kết các sự cố cùng nguyên nhân |
| `IMM CAPA Record` | Yes | (chưa có workflow JSON; orchestration trong service) | Hành động khắc phục + phòng ngừa |
| `Asset QA Non Conformance` | Yes | (chưa workflow) | NC độc lập (commissioning, calibration fail) |
| `IMM Audit Trail` | No (immutable) | – | Hash chain SHA-256 cho tất cả CAPA action |

---

## 3. Luồng end-to-end

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                       │
│   1. Sự cố xảy ra                                                     │
│   ┌──────────────────────┐  hoặc  ┌──────────────────────────────┐    │
│   │   Incident Report     │       │ Asset QA Non Conformance     │    │
│   │   (lâm sàng/vận hành) │       │ (commissioning / cal fail)   │    │
│   └──────────┬────────────┘       └──────────┬───────────────────┘    │
│              │                                │                       │
│              ▼                                │                       │
│   2. Acknowledge → In Progress               │                       │
│   (services/imm12.acknowledge_incident)      │                       │
│              │                                │                       │
│              ▼                                │                       │
│   3. Severity assessment                     │                       │
│   (severity ≥ High → bắt buộc RCA)           │                       │
│              │                                │                       │
│              ▼                                │                       │
│   ┌──────────────────────────────┐           │                       │
│   │ Workflow → "RCA Required"    │           │                       │
│   └──────────┬───────────────────┘           │                       │
│              │                                │                       │
│              ▼                                │                       │
│   4. services/imm12.create_rca               │                       │
│   ┌──────────────────────────────┐           │                       │
│   │   IMM RCA Record (Draft)     │           │                       │
│   │   - method: 5-Why / Fishbone │           │                       │
│   │   - linked incident / NC     │◄──────────┘                       │
│   └──────────┬───────────────────┘                                   │
│              │                                                        │
│              ▼                                                        │
│   5. RCA In Progress                                                 │
│   - 5-Why steps (child table IMM RCA Five Why Step)                  │
│   - Related incidents (child IMM RCA Related Incident)               │
│   - root_cause, corrective_action, preventive_action                 │
│              │                                                        │
│              ▼                                                        │
│   6. submit_rca → Closed                                             │
│   (services/imm12.submit_rca)                                        │
│              │                                                        │
│              ▼                                                        │
│   7. Decision: cần CAPA hay không?                                   │
│   - Nếu corrective + preventive action có scope rộng                 │
│     → tạo IMM CAPA Record                                            │
│   - Nếu chỉ fix tại chỗ (1 lần) → đóng incident, không CAPA          │
│              │                                                        │
│              ▼                                                        │
│   ┌──────────────────────────────┐                                   │
│   │   IMM CAPA Record (Open)     │                                   │
│   │   - source: incident/NC/RCA  │                                   │
│   │   - severity, due_days       │                                   │
│   │   - responsible, asset       │                                   │
│   │   (services/imm00.create_capa)                                   │
│   └──────────┬───────────────────┘                                   │
│              │                                                        │
│              ▼                                                        │
│   8. CAPA Implementation                                             │
│   - Owner thực hiện corrective + preventive                          │
│   - Cron daily: services/imm00.check_capa_overdue                    │
│              │                                                        │
│              ▼                                                        │
│   9. Effectiveness Check                                             │
│   - Sau N tuần: kiểm tra recurrence                                  │
│   - Nếu fail → reopen, tạo CAPA mới (escalate)                       │
│              │                                                        │
│              ▼                                                        │
│   10. close_capa (services/imm00.close_capa)                         │
│   - Yêu cầu effectiveness_check, root_cause, corrective_action,      │
│     preventive_action đầy đủ                                         │
│   - E-signature (re-auth)                                            │
│   - log_audit_event(asset, "capa_closed", ...)                       │
│              │                                                        │
│              ▼                                                        │
│   11. Đóng incident gốc (nếu chưa)                                   │
│              │                                                        │
│              ▼                                                        │
│   ✓ Audit chain: IMM Audit Trail có chuỗi SHA-256 đầy đủ             │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. State của `IMM CAPA Record`

> Hiện tại chưa có workflow JSON; orchestration qua service. Đề xuất chuẩn hoá thành workflow:

| State | Mô tả | Action vào |
|---|---|---|
| Draft | Vừa tạo, chưa submit | (open_capa) |
| Open | Đã submit, owner bắt đầu thực hiện | (workflow submit) |
| In Progress | Đang triển khai action | – |
| Effectiveness Pending | Đã hoàn tất action, đang chờ verify hiệu lực (N tuần) | – |
| Closed | Verify hiệu lực thành công | `close_capa` (e-sig) |
| Reopened | Failed effectiveness — quay lại In Progress | – |
| Cancelled | Hủy (sai trigger) | – |

**Action label gợi ý** (chưa hard-code):
- `Bắt đầu thực hiện`, `Hoàn thành action`, `Chờ verify hiệu lực`, `Đóng CAPA`, `Mở lại CAPA`, `Hủy CAPA`.

---

## 5. Roles và quyền

| Action | Role chính | Role review | E-sig |
|---|---|---|---|
| Tạo CAPA (open) | `IMM QA Officer`, `IMM HTM Engineer` | – | – |
| Assign owner | `IMM QA Officer`, `IMM Workshop Lead` | – | – |
| Thực hiện action | `IMM Biomed Technician`, `IMM HTM Engineer`, `IMM Workshop Lead` | – | – |
| Effectiveness check | `IMM QA Officer` | `IMM Risk Officer` (nếu severity Critical/High) | – |
| Close CAPA | `IMM QA Officer` | `IMM Operations Manager` (severity Critical) | **Y** |
| Reopen CAPA | `IMM QA Officer`, `IMM Operations Manager` | – | **Y** |
| Audit read-only | `IMM Auditor`, `IMM System Admin` | – | – |

**Segregation of Duty:** CAPA submitter ≠ closer (enforce qua workflow + service validate).

---

## 6. Side effects bắt buộc

Mỗi action quan trọng phải:
1. Gọi `assetcore.utils.lifecycle.log_audit_event(asset, event_type, ref_doctype="IMM CAPA Record", ref_name=..., from_status=..., to_status=..., change_summary=...)` → ghi `IMM Audit Trail`.
2. Gọi `assetcore.utils.lifecycle.create_lifecycle_event(asset, "capa_<action>", ...)` cho timeline trên asset.
3. Verify chain trước khi close: `verify_audit_chain(asset)` không được fail.

---

## 7. Scheduler & alerts

| Tần suất | Job | Hành động |
|---|---|---|
| Daily 06:00 | `assetcore.services.imm00.check_capa_overdue` | Quét CAPA chưa đóng > `due_days`, gửi email + ghi `Expiry Alert Log` |
| Daily 07:00 | `assetcore.services.imm12.detect_chronic_failures` | Phát hiện thiết bị có ≥ N incident trong M ngày → đề xuất tạo CAPA |
| Weekly | – | Báo cáo CAPA theo dept gửi Operations Manager (chưa hard-code, đề xuất) |
| Monthly | KPI rollup | Tỷ lệ CAPA đóng đúng hạn vào dashboard |

---

## 8. KPI / metric (gắn vào `services/imm00.rollup_asset_kpi` + `api/dashboard`)

| KPI | Công thức | Target |
|---|---|---|
| % CAPA đóng đúng hạn | `closed_on_time / total_closed` | ≥ 90% |
| Số CAPA mở > 30 ngày | count | < 5 (tổng toàn hospital) |
| Tỷ lệ recurrence (effectiveness fail) | `reopened / total_closed` | < 5% |
| Time-to-CAPA (from incident → CAPA open) | avg days | ≤ 7 ngày cho severity High |
| % incident có RCA (severity High+) | `rca_count / high_severity_incident` | ≥ 95% |

---

## 9. Linkage matrix

| Source DocType | Tạo CAPA khi | Service hook |
|---|---|---|
| `Incident Report` (severity ≥ High) | RCA hoàn tất, recommend CAPA | `services/imm12.submit_rca` |
| `IMM Asset Calibration` (Failed) | Tự động khi calibration fail | `services/imm11.*` (đề xuất, chưa hard-code) |
| `Asset QA Non Conformance` | Owner quyết định cần CAPA | `services/imm00.create_capa` |
| `Asset Commissioning` (Non Conformance) | Bắt buộc nếu severity ≥ High | service IMM-04 |
| `IMM Supplier Audit` (Audit Finding) | Findings dạng Major | (đề xuất qua imm03) |

---

## 10. ISO 14971 Risk Management integration

Cho mỗi CAPA gắn với hazard / harm:
- Field `risk_class` trên CAPA (1/2a/2b/3 theo NĐ 98/2021).
- Cross-link tới `IMM Lock-in Risk Assessment` nếu có (vendor lock-in).
- Owner: `IMM Risk Officer` review cho CAPA severity Critical.
- Audit log gồm `severity`, `risk_class`, `clinical_impact`, `patient_affected`, `patient_impact_description` (lấy từ `Incident Report`).

---

## 11. Checklist "Definition of Done" CAPA

Khi đóng CAPA phải:
- [ ] `root_cause` không rỗng, link `IMM RCA Record`.
- [ ] `corrective_action` cụ thể với owner + deadline đã hoàn tất.
- [ ] `preventive_action` cụ thể (≠ corrective_action).
- [ ] `effectiveness_check` documented với evidence (ngày check, kết quả).
- [ ] Không có recurrence trong cửa sổ verify.
- [ ] E-signature từ `IMM QA Officer`.
- [ ] `verify_audit_chain(asset)` pass.
- [ ] Lifecycle event `capa_closed` được publish.
- [ ] Liên kết các DocType nguồn (incident, NC, calibration record) đã set `linked_capa`.

---

## 12. Tham chiếu
- Service code: `assetcore/services/imm00.py` (CAPA CRUD), `assetcore/services/imm12.py` (orchestration incident → RCA → CAPA).
- DocType JSON: `assetcore/assetcore/doctype/imm_capa_record/`, `imm_rca_record/`, `incident_report/`, `asset_qa_non_conformance/`.
- Audit utils: `assetcore/utils/lifecycle.py`.
- Workflow JSON: `imm_12_incident_workflow.json`, `imm_12_rca_workflow.json`.
- API: `api/imm12.*` + `api/imm00.list_capas / open_capa / close_capa_record / list_overdue_capas`.

---

## 13. Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| QA Officer |  | 2026-05-07 |
| Tech Lead |  | 2026-05-07 |
| Risk Officer |  | 2026-05-07 |
