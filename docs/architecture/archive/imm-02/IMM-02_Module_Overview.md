# IMM-02 — Thông số Kỹ thuật & Phân tích Thị trường (Module Overview)

> **⚠ Wave 2 Alignment** — Trước khi triển khai phải đọc `docs/WAVE2_ALIGNMENT.md`. Hiệu chỉnh khớp Wave 1 LIVE: module Frappe `AssetCore`; naming series `IMM02-…`; reuse `IMM Device Model` / `AC Asset Category` / `IMM Audit Trail`; envelope API `{success, data|error, code}`; Frappe Role `IMM HTM Engineer` / `IMM Planning Officer` / `IMM Risk Officer` / `IMM Department Head` / `IMM Board Approver`; audit trail dùng `IMM Audit Trail`; scheduler `quarterly` phải khai qua `cron` (Frappe v15 không có quarterly).

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-02 — Thông số kỹ thuật và phân tích thị trường (Tech Spec & Market Analysis) |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT — Wave 2 (chưa triển khai code) |
| Tác giả | AssetCore Team |
| Khối kiến trúc | A. KHỐI 1 — Planning & Procurement |
| QC nền | QC-IMMIS-01 |

---

## 1. Mục đích

IMM-02 là **specification gateway** giữa IMM-01 (Needs / Plan) và IMM-03 (Vendor / PO). Module chuẩn hóa:

- Soạn thông số kỹ thuật (technical requirement) cho từng device model trong Procurement Plan.
- Benchmark công nghệ — so sánh model hiện hành trên thị trường VN + quốc tế (HTA-lite).
- Đánh giá tương thích hạ tầng (điện, khí y tế, mạng, không gian, HIS/PACS interface).
- Kiểm soát nguy cơ **vendor lock-in / platform lock-in** — buộc phải có open standard khả thi hoặc lý giải nếu chấp nhận lock.
- Lock spec (Approved) trước khi mở hồ sơ vendor evaluation/đấu thầu IMM-03.

Không có **Tech Spec** ở trạng thái `Locked` (docstatus=1) thì không có vendor evaluation và không có PO IMM-03.

**Chuẩn tham chiếu:** WHO — *Health technology assessment of medical devices, 2nd ed.*; WHO — *Procurement process resource guide* (chương Specification); ISO 13485 §7.3 (Design input); GMDN; NĐ 98/2021/NĐ-CP §29; Luật Đấu thầu 22/2023 (yêu cầu HSMT mô tả tính năng kỹ thuật).

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│  Inputs                                                          │
│   • IMM-01 Procurement Plan Line (trigger draft)                 │
│   • IMM Device Model master                                      │
│   • Existing Asset baseline (IMM-04 commissioning data)          │
│   • Compliance data (IMM-10) — yêu cầu compliance bổ sung        │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│  IMM-02 — Tech Spec & Market Analysis (specification gateway)    │
│                                                                  │
│  Workflow 7 states · 4 Gate · 6 VR · 6 BR                        │
│  DocTypes:                                                       │
│   • Tech Spec               (cha — naming TS-…)                  │
│   • Tech Spec Requirement   (child — yêu cầu kỹ thuật từng dòng) │
│   • Market Benchmark        (so sánh model thị trường)           │
│   • Infra Compatibility     (đối chiếu hạ tầng)                  │
│   • Lock-in Risk Assessment (đánh giá nguy cơ khóa hãng)         │
│  API: assetcore/api/imm02.py    (≈ 14 endpoints)                 │
│  Service: assetcore/services/imm02.py                            │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│  Outputs                                                         │
│   • Tech Spec (Locked) → IMM-03 (Vendor Evaluation, RFQ, PO)     │
│   • Market Benchmark → IMM-17 (Predictive — model trend)         │
│   • Lock-in Risk → IMM-10 (Compliance & Risk Register)           │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 Primary

| DocType | Naming | Submittable | Mô tả |
|---|---|---|---|
| `IMM Tech Spec` | `TS-.YY.-.#####` | Yes | Hồ sơ kỹ thuật cha — workflow 7 state |
| `IMM Market Benchmark` | `MB-.YY.-.#####` | Yes | Phiếu so sánh model A vs B vs C — output kèm Tech Spec |
| `IMM Lock-in Risk Assessment` | `LR-.YY.-.#####` | Yes | Phiếu đánh giá lock-in — bắt buộc cho spec proprietary |

### 3.2 Child Tables

| Child DocType | Parent | Mục đích |
|---|---|---|
| `Tech Spec Requirement` | `Tech Spec.requirements` | 1 dòng = 1 tiêu chí kỹ thuật (parameter, mandatory/optional, value/range, test_method, weight) |
| `Tech Spec Document` | `Tech Spec.documents` | Tài liệu input/output (HSMT excerpt, datasheet, diagram) |
| ~~Tech Spec Lifecycle Event~~ | — | **KHÔNG tạo child table riêng** — audit trail dùng `IMM Audit Trail` (root_doctype=IMM Tech Spec). |
| `Benchmark Candidate` | `Market Benchmark.candidates` | 1 dòng = 1 model so sánh (manufacturer, model, spec match %, price, support) |
| `Infra Compatibility Item` | `Tech Spec.infra_compat` | Mục hạ tầng (electrical, gas, network, HVAC, space, HIS/RIS interface) |
| `Lock-in Risk Item` | `Lock-in Risk Assessment.items` | Mục đánh giá: proprietary protocol, sole-source consumable, software DRM, license tie |

---

## 4. Service Functions

File dự kiến: `assetcore/services/imm02.py`

| Function | Hook / Caller | Mục đích |
|---|---|---|
| `draft_from_plan(plan, plan_item)` | API + IMM-01 trigger | Tạo Tech Spec draft từ Procurement Plan Line |
| `seed_default_requirements(doc)` | `before_insert` | Pre-fill requirements từ template `Device Model.spec_template_ref` |
| `validate_tech_spec(doc)` | `validate()` | VR-01 → VR-06 |
| `_vr01_unique_per_plan_line(doc)` | `validate()` | 1 plan line ↔ 1 Tech Spec Active |
| `_vr02_mandatory_min_count(doc)` | `validate()` | ≥ 1 mandatory requirement |
| `_vr03_test_method_present(doc)` | `validate()` | Mỗi mandatory requirement có `test_method` |
| `_vr04_benchmark_min_3(doc)` | `validate()` | ≥ 3 candidate trong Market Benchmark trước Lock |
| `_vr05_infra_completeness(doc)` | `validate()` | 6 mục hạc tầng có status (Compatible / Need Upgrade / N/A) |
| `_vr06_immutable_lifecycle_events(doc)` | `validate()` | Block sửa lifecycle |
| `validate_gate_g01(doc)` | `validate()` | G01: requirements ≥ N + đủ test_method trước Drafted → Reviewing |
| `validate_gate_g02(doc)` | `validate()` | G02: market benchmark ≥ 3 ứng viên trước Reviewing → Benchmarked |
| `validate_gate_g03(doc)` | `validate()` | G03: infra compat đầy đủ trước Benchmarked → Risk Assessed |
| `validate_gate_g04(doc)` | `before_submit()` | G04: lock-in assessment Pass / với mitigation trước Lock |
| `lock_spec(doc)` | controller `on_submit` | Set state Locked; trigger IMM-03 vendor eval seed |
| `compare_to_baseline(doc)` | service | So sánh với commissioning baseline (IMM-04) — đảm bảo upgrade thực sự |
| `check_overdue_drafts()` | scheduler `daily` | Cảnh báo PTP Khối 1 spec quá 30 ngày Draft/Reviewing |

---

## 5. Workflow States & Transitions

Workflow JSON: `assetcore/assetcore/workflow/imm_02_spec_workflow.json` — `IMM-02 Spec Workflow`.

### 5.1 States (7)

| State | doc_status | Type | Allow Edit | Gate |
|---|---|---|---|---|
| `Draft` | 0 | Success | HTM Engineer | — |
| `Reviewing` | 0 | Warning | HTM Engineer / CMMS Admin | G01 |
| `Benchmarked` | 0 | Success | KH-TC Officer | G02 |
| `Risk Assessed` | 0 | Warning | QA Risk Team | G03 |
| `Pending Approval` | 0 | Warning | PTP Khối 1 | — |
| `Locked` | 1 | Success | (read-only) | G04 (terminal positive) |
| `Withdrawn` | 1 | Danger | — | terminal negative |

### 5.2 Transition matrix (rút gọn)

| From → To | Action | Allowed Role |
|---|---|---|
| Draft → Reviewing | Gửi rà soát | HTM Engineer |
| Reviewing → Draft | Yêu cầu chỉnh | HTM Lead / KH-TC |
| Reviewing → Benchmarked | Hoàn tất benchmark | KH-TC Officer |
| Benchmarked → Risk Assessed | Hoàn tất compat + lock-in | QA Risk Team |
| Risk Assessed → Pending Approval | Trình duyệt | PTP Khối 1 |
| Pending Approval → Locked | Phê duyệt | VP Block1 / BGĐ |
| Pending Approval → Withdrawn | Rút | VP Block1 / PTP Khối 1 |
| Pending Approval → Risk Assessed | Yêu cầu chỉnh risk | VP Block1 |

---

## 6. Schedulers

| Job | Tần suất | Logic | Recipient |
|---|---|---|---|
| `imm02.check_overdue_drafts` | Daily | Spec docstatus=0, > 30d Draft/Reviewing | PTP Khối 1 |
| `imm02.benchmark_freshness_alert` | Weekly | Benchmark > 6 tháng được dùng cho spec mới → cảnh báo | KH-TC Officer |
| `imm02.compatibility_recheck` | cron `0 3 1 1,4,7,10 *` (1/4/7/10 hàng năm) | Tự động re-eval Infra Compat khi master infra config đổi | IMM HTM Engineer |

---

## 7. Roles & Permissions

| Role (Frappe) | Tổ chức tương ứng | Quyền chính |
|---|---|---|
| `IMM HTM Engineer` *(Wave 2 mới)* | Nhóm HTM | Create/Read/Write Tech Spec; soạn requirements |
| `IMM HTM Engineer` (lead subset) | HTM Lead | Approve requirements; chuyển Reviewing |
| `IMM Planning Officer` *(Wave 2 mới)* | KH-TC Officer | Read/Write Market Benchmark |
| `IMM Risk Officer` *(Wave 2 mới)* | QA Risk Team | Read/Write Lock-in Risk + Infra Compat |
| `IMM System Admin` (đã có Wave 1) | CNTT (mảng mạng/HIS) | Read/Write Infra Compat (Network/HIS-PACS-LIS) |
| `IMM Department Head` (đã có Wave 1) | PTP Khối 1 | Submit / Cancel |
| `IMM Board Approver` *(Wave 2 mới)* | VP Block1 / BGĐ | Lock / Withdraw |
| `IMM System Admin` | CMMS Admin | Full |

---

## 8. Business Rules

| BR ID | Rule | Enforce | Chuẩn |
|---|---|---|---|
| BR-02-01 | 1 Procurement Plan Line ↔ 1 Tech Spec Active | `_vr01_unique_per_plan_line` | Traceability |
| BR-02-02 (G01) | ≥ N (default 8) mandatory requirements + 100% test_method | `validate_gate_g01` | WHO Procurement Spec §3.4 |
| BR-02-03 (G02) | ≥ 3 benchmark candidates với spec_match_pct + price + support | `validate_gate_g02` | HTA |
| BR-02-04 (G03) | 6/6 mục hạ tầng có status đánh giá | `validate_gate_g03` | WHO HTM §4 |
| BR-02-05 (G04) | Lock-in Risk Score ≤ ngưỡng hoặc có mitigation phê duyệt | `validate_gate_g04` | NĐ 98 §29; chống lock-in |
| BR-02-06 | Spec Locked không sửa được trừ khi Withdrawn + Reissue | controller `before_save` | ISO 13485 §7.3.7 |

---

## 9. Dependencies

| Module | Quan hệ | Cơ chế |
|---|---|---|
| IMM-01 | INPUT | Procurement Plan Line trigger draft; spec lock cập nhật `Procurement Plan Line.status=In Procurement` |
| IMM Device Model | INPUT | spec_template_ref + tham số kỹ thuật mặc định |
| IMM-04 | INPUT | Baseline commissioning data dùng cho `compare_to_baseline` |
| IMM-10 | INPUT/OUTPUT | Compliance gap → bắt buộc requirement bổ sung; lock-in risk → register |
| IMM-03 | OUTPUT | Locked Tech Spec → trigger vendor eval & RFQ |
| IMM-17 | OUTPUT | Market Benchmark → input model trend predictive |

---

## 10. KPI / Dashboard

KPI-DASH-IMMIS-02:

| KPI | Công thức | Mục tiêu |
|---|---|---|
| Lead time Draft → Locked | avg(lock_date − draft_date) | < 30 ngày |
| % Spec đủ ≥ 3 benchmark | spec_with_3+_candidates / total_locked | 100% |
| Avg lock-in risk score | avg(lock_in_score) | ≤ 2.5/5 |
| Spec rework rate | spec_returned_to_draft / total_drafted | < 20% |
| % spec re-use template | spec_with_template_ref / total | ≥ 70% |
| Backlog Draft > 30d | count | giảm dần |

---

## 11. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| 3 DocType + 6 child | 📐 DESIGN | — |
| Workflow 7 states | 📐 DESIGN | — |
| API ≈ 14 endpoints | 📐 DESIGN | — |
| Service layer | 📐 DESIGN | — |
| 6 VR + 4 Gates | 📐 DESIGN | — |
| Spec template engine | 📐 DESIGN | Re-use từ Device Model |
| Dashboard | 📐 DESIGN | — |

---

## 12. Tài liệu liên quan

- `IMM-02_Functional_Specs.md`
- `IMM-02_Technical_Design.md`
- `IMM-02_API_Interface.md`
- `IMM-02_UAT_Script.md`
- `IMM-02_UI_UX_Guide.md`

*End of Module Overview v0.1.0 — IMM-02*
