# IMM-12 — Incident & Corrective Action (CAPA) Management

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | **DRAFT** — chỉ có CAPA DocType (từ IMM-00) đã LIVE; code IMM-12 (api/services/UI) chưa implement |
| Tác giả | AssetCore Team |
| Wave | Wave 1 (Operation) |

---

## 1. Mục đích

IMM-12 quản lý vòng đời **sự cố thiết bị y tế** (Incident) và **hành động khắc phục/phòng ngừa** (CAPA — Corrective and Preventive Action) theo ISO 13485:2016 §8.5 và NĐ 98/2021 Điều 38.

Module đảm nhiệm:

- **Incident Reporting** — tiếp nhận sự cố từ khoa phòng, KTV PM/CM/Cal
- **Severity Classification** — Minor / Major / Critical theo tác động lâm sàng
- **Root Cause Analysis (RCA)** — bắt buộc với Major/Critical, cấu trúc 5-Why / Fishbone
- **CAPA Lifecycle** — Open → In Progress → Pending Verification → Closed (sử dụng `IMM CAPA Record` của IMM-00)
- **Audit Trail** — mọi state transition log qua `log_audit_event()`

**Không bao gồm:** thực hiện sửa chữa (IMM-09), bảo trì định kỳ (IMM-08), hiệu chuẩn (IMM-11), SLA Engine (delegated cho IMM-00 `get_sla_policy()`).

**Vai trò là consumer của IMM-00:** IMM-12 KHÔNG implement service riêng cho CAPA; mọi nghiệp vụ CAPA gọi qua `assetcore/services/imm00.py`.

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│                      AssetCore App                               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              IMM-00 Foundation Layer                       │  │
│  │   • IMM CAPA Record (LIVE)   • IMM Audit Trail (LIVE)      │  │
│  │   • create_capa()            • close_capa()                │  │
│  │   • log_audit_event()        • transition_asset_status()│
│  │   • check_capa_overdue() (scheduler daily)                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ▲                                   │
│                              │ consumes                          │
│  ┌───────────────────────────┴────────────────────────────────┐  │
│  │              IMM-12 Incident & CAPA (THIS MODULE)          │  │
│  │   • Incident Report DocType (✅ LIVE — cung cấp bởi IMM-00) │  │
│  │   • services/imm12.py — orchestration only (⚠️ Pending)    │  │
│  │   • api/imm12.py — REST endpoints (⚠️ Pending)             │  │
│  │   • UI: Incident List/Form, CAPA List/Form, RCA, Dashboard │  │
│  │     (⚠️ Mockup only)                                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ▲                                   │
│  ┌───────────────────────────┴────────────────────────────────┐  │
│  │   IMM-09 (Repair) — major fault → IMM-12.create_capa()     │  │
│  │   IMM-04 (Install) — NC nghiêm trọng → IMM-12.create_capa()│  │
│  │   IMM-08 (PM)      — finding lớn   → IMM-12 incident       │  │
│  │   IMM-11 (Cal)     — fail clinical → IMM-12 incident       │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 DocType đã LIVE (kế thừa từ IMM-00)

| DocType | Naming | Type | Mục đích | Trạng thái |
|---|---|---|---|---|
| `IMM CAPA Record` | `CAPA-.YYYY.-.#####` | Submittable | Hành động khắc phục/phòng ngừa theo ISO 13485:8.5 | ✅ LIVE (IMM-00) |
| `IMM Audit Trail` | `IMM-AUD-.YYYY.-.#######` | Append-only | Log bất biến SHA-256 chain | ✅ LIVE (IMM-00) |
| `Asset Lifecycle Event` | `ALE-.YYYY.-.#######` | Append-only | Sự kiện vòng đời asset | ✅ LIVE (IMM-00) |
| `Incident Report` | `IR-.YYYY.-.####` | Submittable | Sự cố thiết bị (DocType nền tảng IMM-00) | ✅ LIVE (IMM-00) |

### 3.2 DocType đề xuất bổ sung cho IMM-12

| DocType | Naming | Type | Mục đích | Trạng thái |
|---|---|---|---|---|
| `IMM Incident Report` (extension) | dùng `Incident Report` IMM-00 + custom fields | Submittable | Bổ sung field: `severity`, `rca_method`, `rca_record`, `clinical_impact`, `chronic_failure_flag` | ⚠️ Pending — đề xuất extend qua DocType extension |
| `RCA Record` | `RCA-.YYYY.-.#####` | Submittable | Phân tích nguyên nhân gốc, child table 5-Why steps | ⚠️ Pending |
| `RCA Related Incident` | child | Child | Liên kết nhiều IR vào 1 RCA (chronic failure) | ⚠️ Pending |
| `RCA Five Why Step` | child | Child | 5 bước "Why" của RCA | ⚠️ Pending |

> **Ghi chú kiến trúc:** IMM-12 v1 ưu tiên **tái sử dụng `IMM CAPA Record` của IMM-00** thay vì tạo CAPA DocType riêng. RCA Record là DocType **tách riêng** vì cần child table cấu trúc 5-Why và nhiều IR liên kết.

---

## 4. Service Functions

### 4.1 Sử dụng từ IMM-00 (không reimplement)

| Function | Module | Mô tả |
|---|---|---|
| `create_capa(asset, source_doctype, source_name, fault_severity, due_days)` | `services/imm00.py` | Tạo CAPA Record, set responsible, due_date | 
| `close_capa(capa_name, corrective_action, preventive_action, evidence)` | `services/imm00.py` | Đóng CAPA — validate root_cause + corrective_action (BR-00-08) |
| `log_audit_event(asset, event_type, actor, ref_doctype, ref_name, ...)` | `services/imm00.py` | Log mọi incident/CAPA transition |
| `transition_asset_status(asset, new_status, reason)` | `services/imm00.py` | Đổi `AC Asset.lifecycle_status` (e.g. → Out of Service khi critical) |
| `create_lifecycle_event(asset, event_type, ...)` | `services/imm00.py` | Tạo Asset Lifecycle Event |
| `check_capa_overdue()` | `services/imm00.py` | Scheduler daily — auto Overdue CAPA quá due_date (BR-00-09) |

### 4.2 Function riêng cho IMM-12 (⚠️ Pending implementation)

| Function | File (đề xuất) | Mô tả |
|---|---|---|
| `report_incident(asset, severity, fault_description, ...)` | `services/imm12.py` | Wrapper — tạo Incident Report + log audit |
| `acknowledge_incident(name, assigned_to, notes)` | `services/imm12.py` | Set status Acknowledged, log audit |
| `resolve_incident(name, resolution_notes)` | `services/imm12.py` | Set Resolved, kích hoạt RCA nếu Major/Critical |
| `trigger_rca_if_required(incident_name)` | `services/imm12.py` | Major/Critical hoặc chronic → tạo RCA Record |
| `detect_chronic_failures()` | `services/imm12.py` | Scheduler daily — phát hiện ≥3 incidents cùng fault_code/90 ngày |
| `submit_rca_and_create_capa(rca_name, ...)` | `services/imm12.py` | Submit RCA → gọi `imm00.create_capa()` với root_cause |

---

## 5. Workflow States

### 5.1 Incident Report

```
Draft ──► Open ──► Acknowledged ──► In Progress ──► Resolved ──► Closed
                                                       │
                                                       ▼ (Major/Critical or Chronic)
                                                  RCA Required ──► Closed
                                                       │
                                                       ▼
                                                  CAPA Created (via imm00.create_capa)
```

### 5.2 CAPA (kế thừa IMM-00)

```
Open ──► In Progress ──► Pending Verification ──► Closed
   │
   └── (overdue) ──► Overdue (auto via scheduler — BR-00-09)
```

### 5.3 RCA Record

```
RCA Required ──► RCA In Progress ──► Completed
                          │
                          └── (justification) ──► Cancelled
```

---

## 6. Roles & Permissions

| Role | Quyền hạn chính trong IMM-12 |
|---|---|
| Reporting User (Điều dưỡng/KTV) | Create Incident Report (Draft/Open) |
| IMM Workshop Lead | Acknowledge Incident; Create RCA; Submit RCA; Create CAPA via service |
| IMM QA Officer | Read all; Submit + Close CAPA; verify Audit Trail |
| IMM Department Head | Read incidents; nhận escalation Critical |
| IMM Operations Manager | Read all; xem dashboard; export báo cáo |
| IMM System Admin | Full CRUD |

(Roles re-use fixtures `fixtures/imm_roles.json` từ IMM-00.)

---

## 7. Business Rules

| ID | Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-12-01 | Critical incident → bắt buộc set `clinical_impact` trước Submit | `IncidentReport.validate()` | ISO 13485:7.5 |
| BR-12-02 | Major/Critical Resolved → bắt buộc tạo RCA trước khi Close | `IncidentReport.validate()` (status → Closed) | ISO 13485:8.5.2 |
| BR-12-03 | ≥3 incidents cùng `fault_code` trên cùng asset trong 90 ngày → auto RCA + chronic flag | Scheduler daily `detect_chronic_failures()` | WHO HTM §5.4 |
| BR-12-04 | Critical incident → auto `transition_asset_status(asset, "Out of Service")` | `services/imm12.report_incident()` | WHO HTM, NĐ98 |
| BR-12-05 | Mọi incident transition phải sinh `IMM Audit Trail` entry | `services/imm12.*` qua `log_audit_event()` | ISO 13485:7.5.9 |
| **BR-00-08** | CAPA `before_submit` bắt buộc có `root_cause + corrective_action + preventive_action` | `IMMCAPARecord.before_submit()` (IMM-00) | ISO 13485:8.5 |
| **BR-00-09** | CAPA quá `due_date` → auto Overdue qua scheduler daily | `check_capa_overdue()` (IMM-00) | Internal |

---

## 8. Dependencies

| Module / Component | Cần gì | Ghi chú |
|---|---|---|
| **IMM-00 Foundation** | `IMM CAPA Record`, `Incident Report`, `Asset Lifecycle Event`, `IMM Audit Trail`, `services/imm00.py` | **Bắt buộc — IMM-12 không hoạt động nếu thiếu** |
| **IMM-09 Repair** | Repair Work Order DocType; `incident_report` link field | IMM-09 gọi `imm12.report_incident()` khi major fault phát hiện trong CM |
| **IMM-04 Installation** | NC (Non-conformance) tracking | NC nghiêm trọng → `imm12.report_incident()` → CAPA |
| **IMM-08 PM** | PM Work Order finding | PM finding lớn → tạo Incident |
| **IMM-11 Calibration** | Calibration result | Cal failure clinical impact → tạo Incident |
| Frappe Framework v15 | Workflow Engine, Scheduler, Email Queue | Standard |

---

## 9. Trạng thái triển khai

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| IMM CAPA Record DocType | ✅ LIVE | Cung cấp bởi IMM-00 |
| Incident Report DocType (base) | ✅ LIVE | Cung cấp bởi IMM-00 |
| `services/imm00.py` (create_capa, close_capa, log_audit_event) | ✅ LIVE | Reuse từ IMM-00 |
| `services/imm12.py` | ⚠️ Pending | Wrapper/orchestration cho RCA + chronic detection |
| `api/imm12.py` | ⚠️ Pending | REST endpoints cho UI |
| RCA Record DocType + child tables | ⚠️ Pending | DocType riêng IMM-12 |
| Custom fields trên Incident Report (severity, rca_record, clinical_impact, chronic_failure_flag) | ⚠️ Pending | Extension via fixtures |
| Scheduler `detect_chronic_failures` | ⚠️ Pending | hooks.py daily 02:00 |
| Frontend (Incident/CAPA/RCA list + form + dashboard) | ⚠️ Pending Mockup only | Spec ở `IMM-12_UI_UX_Guide.md` |
| UAT execution | ⚠️ Pending | Script ở `IMM-12_UAT_Script.md` |

---

## 10. Liên kết với module khác

```
IMM-09 (Repair)
  • root_cause_category nghiêm trọng → imm12.report_incident()
  • → imm00.create_capa(asset, "Repair Work Order", wo_name, "Major", 30)

IMM-04 (Installation)
  • NC nghiêm trọng (commissioning fail, safety test fail)
    → imm12.report_incident(severity="Critical")
    → imm00.create_capa(...)

IMM-08 (PM) / IMM-11 (Cal)
  • Finding > threshold → tạo Incident Report
  • Major → trigger RCA → CAPA

IMM-12 → IMM-00
  • Mọi action gọi services/imm00.py — không bypass
  • Mọi state change → log_audit_event()
```

---

## 11. KPI

| KPI | Định nghĩa | Mục tiêu | Nguồn |
|---|---|---|---|
| Incident MTTR | avg(resolved_at − reported_at) | giảm theo quý | Incident Report |
| RCA On-Time Completion (%) | RCA hoàn thành trước due_date / tổng RCA | ≥ 95% | RCA Record |
| CAPA On-Time Closure (%) | CAPA Closed trước due_date / tổng CAPA | ≥ 90% | IMM CAPA Record |
| Chronic Failure Count | số asset có `chronic_failure_flag = True` | 0 | Custom field on AC Asset |
| Critical Incidents / tháng | COUNT(severity=Critical) | giảm theo quý | Incident Report |

---

## 12. Chuẩn tham chiếu

| Chuẩn | Điều khoản | Áp dụng |
|---|---|---|
| ISO 13485:2016 | §8.5.2 Corrective action; §8.5.3 Preventive action | CAPA workflow |
| ISO 13485:2016 | §8.3 Control of nonconforming product | Incident classification |
| WHO HTM Guidelines 2025 | §5.3.4, §5.4 | Incident reporting, chronic failure |
| NĐ 98/2021/NĐ-CP | Điều 38 | Báo cáo sự cố thiết bị y tế |
| MEDDEV 2.7/1 Rev 4 | Vigilance | Reporting nghiêm trọng cho cơ quan quản lý |

---

## 13. Roadmap

| Sprint | Hạng mục | Trạng thái |
|---|---|---|
| 12.1 | Custom fields extension Incident Report (severity, rca_record, clinical_impact, chronic_failure_flag) | ⚠️ Pending |
| 12.2 | RCA Record DocType + child tables (Related Incident, Five Why Step) | ⚠️ Pending |
| 12.3 | `services/imm12.py` (orchestration calling imm00) | ⚠️ Pending |
| 12.4 | `api/imm12.py` REST endpoints | ⚠️ Pending |
| 12.5 | Scheduler `detect_chronic_failures` (daily 02:00) | ⚠️ Pending |
| 12.6 | FE Incident List/Form, CAPA List/Form, RCA Form, Dashboard | ⚠️ Pending |
| 12.7 | UAT execution (TC-12-01 → TC-12-NN) | ⚠️ Pending |
