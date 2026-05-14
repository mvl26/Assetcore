# IMM-02 — Phân tích & Thiết kế (Analysis & Design)

> **Wave 2 — Live.**

| Mục | Giá trị |
|---|---|
| Module | **IMM-02 — Thông số Kỹ thuật & Phân tích Thị trường (Tech Spec & Market Analysis)** |
| Phiên bản | 1.0.1 |
| Ngày cập nhật | 2026-05-14 |
| Owner | BA Lead + Tech Lead |
| Liên kết | [03 Diagrams](./03_Diagrams.md) · [04 Backend Design](./04_Backend_Design.md) · [05 API Specification](./05_API_Specification.md) |

---

# Phần I — Module Overview

## I.0. Khảo sát hiện trạng (As-Is)

Theo WHO Procurement Process Resource Guide và pattern truyền thống tại bệnh viện công VN trước khi triển khai AssetCore:

- **Hồ sơ kỹ thuật rời rạc**: Tech spec soạn trên Word/Excel theo từng gói thầu, không có template chuẩn → mỗi khoa phòng viết một phong cách, khó so sánh.
- **Benchmark thị trường thủ công**: KH-TC tự tra catalog hãng, không lưu lại bằng chứng so sánh ≥3 candidate; quyết định chọn model phụ thuộc kinh nghiệm cá nhân, thiếu traceability.
- **Đánh giá tương thích hạ tầng bị bỏ qua**: Điện, khí y tế, mạng, HIS/PACS/LIS thường chỉ kiểm tra sau khi thiết bị về tới kho → phát sinh chi phí cải tạo, lùi tiến độ go-live.
- **Không kiểm soát rủi ro vendor lock-in**: Không có khung đánh giá 5 chiều (Protocol, Consumable, Software, Parts, Service); bệnh viện thường bị khóa hãng cho consumable/firmware sau 3–5 năm sử dụng.
- **Versioning hồ sơ kỹ thuật**: Khi cần sửa spec đã chốt, không có cơ chế Withdraw + Reissue chính thức → spec cũ và mới lẫn lộn, không biết version nào đang dùng cho gói nào.

→ AssetCore IMM-02 chuẩn hóa toàn bộ vòng quay: từ trigger Procurement Plan → soạn requirements có template → benchmark có bằng chứng → infra check 6 domains → lock-in 5 dimensions → Lock spec → trigger IMM-03 với audit trail xuyên suốt.

*(Nguồn tham chiếu: WHO — Procurement process resource guide; phỏng vấn BA Phase_01.)*

## I.1. Pitch

IMM-02 là **specification gateway** (cổng đặc tả kỹ thuật) nằm giữa IMM-01 (Needs / Procurement Plan) và IMM-03 (Vendor Evaluation / Đấu thầu). Module chuẩn hóa:

- Soạn thông số kỹ thuật (technical requirement) cho từng thiết bị trong Procurement Plan.
- Benchmark công nghệ — so sánh ≥ 3 model trên thị trường VN + quốc tế (HTA-lite).
- Đánh giá tương thích hạ tầng — điện, khí y tế, mạng, không gian, HIS/PACS/LIS interface.
- Kiểm soát nguy cơ **vendor lock-in** — 5 chiều: Protocol, Consumable, Software, Parts, Service.
- Lock spec (Approved) trước khi mở hồ sơ đánh giá nhà cung cấp IMM-03.

**Không có Tech Spec ở trạng thái `Locked`** thì không có vendor evaluation, không có PO IMM-03.

## I.2. Vị trí trong Lifecycle

```
IMM-01 Procurement Plan (Approved)
         │
         ▼  draft_from_plan()
IMM-02 Tech Spec
   Workflow 7 states · 4 Gate · 6 VR · 6 BR
         │
         ▼  lock_spec() — on_submit
IMM-03 Vendor Evaluation + RFQ
IMM-10 Risk Register (lock-in risk)
IMM-17 Predictive (market benchmark data)
```

## I.3. Các Bên Liên Quan (Stakeholders)

| Actor | Frappe Role | Quyền chính |
|---|---|---|
| HTM Engineer | `IMM HTM Engineer` (Wave 2 mới) | Create/Write Tech Spec, soạn requirements |
| HTM Lead | `IMM HTM Engineer` (lead subset) | Review requirements, sign-off Reviewing |
| KH-TC Officer | `IMM Planning Officer` (Wave 2 mới) | Soạn Market Benchmark |
| QA Risk Team | `IMM Risk Officer` (Wave 2 mới) | Lock-in Risk Assessment + Infra Compat |
| CNTT | `IMM System Admin` (Wave 1) | Infra Compat (Network/HIS-PACS-LIS) |
| PTP Khối 1 | `IMM Department Head` (Wave 1) | Submit/Cancel, điều phối workflow |
| VP Block1 / BGĐ | `IMM Board Approver` (Wave 2 mới) | Lock / Withdraw spec |
| CMMS Admin | `IMM System Admin` (Wave 1) | Cấu hình master, override |

## I.4. Phạm Vi

**In scope:**
- Tạo Tech Spec từ Procurement Plan Line
- Quản lý requirements (manual + bulk import Excel)
- Market Benchmark ≥ 3 candidates, spec_match%, recommendation scoring
- Infra Compatibility 6 domains
- Lock-in Risk Assessment 5 dimensions
- Versioning: Withdraw + Reissue
- Lock spec → trigger IMM-03

**Out of scope:**
- Soạn HSMT (E-bidding) hoàn chỉnh → IMM-03
- Đánh giá nhà cung cấp cụ thể → IMM-03
- Kế hoạch mua sắm → IMM-01

## I.5. KPI

*(Cần workshop BA — không tự fill. Xem `_REPORT.md` mục 1.)*

## I.6. Compliance (NĐ98 / GMDN / WHO)

*(Cần workshop BA — không tự fill. Xem `_REPORT.md` mục 2.)*

## I.7. Rủi ro (Risk)

| ID | Rủi ro | Tác động | Mức | Hướng giảm thiểu |
|---|---|---|---|---|
| R-02-01 | Tech Spec soạn quá chung chung → benchmark không phân biệt được candidate | Lock-in cao, chọn nhầm model | Cao | Gate G01 yêu cầu ≥8 mandatory + 100% test_method; template Device Model seed default requirements |
| R-02-02 | Benchmark <3 candidate hoặc bịa số liệu | Vi phạm WHO HTA + NĐ98 đấu thầu | Cao | Gate G02 chặn cứng ≥3 candidate; lưu file evidence cho mỗi candidate |
| R-02-03 | Bỏ sót đánh giá tương thích hạ tầng | Phát sinh chi phí cải tạo sau go-live | Trung | Gate G03 bắt buộc 6/6 infra domains có status; CNTT bắt buộc duyệt Network/HIS-PACS-LIS |
| R-02-04 | Lock-in score được "ép" thấp để vượt G04 | Bệnh viện bị khóa hãng dài hạn | Cao | `lock_in_score` permlevel=1 chỉ QA Risk + VP Block1 thấy/sửa; mọi exception phải có mitigation_plan + evidence |
| R-02-05 | Spec đã Locked vẫn bị sửa lén | Mất traceability, vi phạm ISO 13485 §7.3.7 | Cao | BR-02-07 chặn `before_save` khi docstatus=1; mọi thay đổi phải đi đường Withdraw + Reissue (version bump) |
| R-02-06 | Withdraw + Reissue lạm dụng → version explosion | Khó audit, mất ngữ cảnh quyết định gốc | Trung | Withdraw bắt buộc nhập `withdrawal_reason`; Reissue giữ link `parent_spec` cho traceability |
| R-02-07 | KH-TC nhập benchmark từ catalog cũ / không cập nhật giá thị trường | Quyết định mua sắm lệch giá hiện hành | Trung | Quarterly scheduler nhắc refresh benchmark; field `benchmark_date` bắt buộc |

*(Risk register chi tiết với owner + due date sẽ đồng bộ sang IMM-10 sau khi spec Lock — xem §I.2.)*

## I.8. Roadmap & Đợt triển khai

Theo `Ho_so_kien_truc_IMMIS.md` §"Đợt triển khai" (line 277):

- **Đợt 1** (đã live): IMM-04, 05, 08, 09, 11, 12 — registry, hồ sơ pháp lý, PM/CM, calibration, dashboard cơ bản. *Không bao gồm IMM-02.*
- **Đợt 2** (đang triển khai — IMM-02 thuộc đợt này): IMM-01, **IMM-02**, IMM-03, IMM-06, IMM-15, IMM-16 — needs, tech spec, vendor, training, spare parts, compliance scorecard. Tiền đề: QMS đã có, dashboard nguồn tin cậy và change control đã chốt.
- **Đợt 3** (kế tiếp): IMM-07, 10, 13, 14, 17 — performance, post-market, retirement, decommissioning, predictive cockpit. IMM-02 sẽ feed dữ liệu lock-in lên IMM-10 (post-market) và benchmark history lên IMM-17 (predictive).

**Phụ thuộc upstream**: IMM-01 phải Approved Procurement Plan trước khi `draft_from_plan()` chạy được.
**Phụ thuộc downstream**: IMM-03 (vendor evaluation), IMM-10 (lock-in risk register), IMM-17 (market benchmark dataset) — tất cả nhận event `imm02_spec_locked`.

**Owner triển khai** (theo Architecture line 265, 268):
- PTP phụ trách Khối 1 — điều phối kế hoạch, tài chính, đấu thầu, hợp đồng.
- Nhóm KH-TC / ĐT-HĐ-NCC — soạn thông số kỹ thuật, benchmark, vendor evaluation.

---

# Phần II — BPMN (Mô tả Quy trình)

## II.1. Swimlane Process

```
HTM Engineer          KH-TC Officer         QA Risk Team          VP Block1
     │                     │                     │                    │
     │                     │                     │                    │
①  Nhận trigger từ      │                     │                    │
   IMM-01 Plan Approved  │                     │                    │
     │                     │                     │                    │
②  draft_from_plan()    │                     │                    │
   Tech Spec = Draft     │                     │                    │
     │                     │                     │                    │
③  Soạn requirements    │                     │                    │
   (manual/import)       │                     │                    │
     │                     │                     │                    │
④  Gửi rà soát [G01]   │                     │                    │
   → Reviewing           │                     │                    │
     │                     │                     │                    │
     ├──────────────────►  │                     │                    │
     │              ⑤  Nhập benchmark         │                    │
     │                 ≥3 candidate           │                    │
     │                     │                     │                    │
     │              ⑥  Hoàn tất benchmark [G02]                   │
     │                 → Benchmarked          │                    │
     │                     │                     │                    │
     │                     ├──────────────────►  │                    │
     │                     │              ⑦  Đánh giá Infra     │
     │                     │                 Compat (6 domains) │
     │                     │                     │                    │
     │                     │              ⑧  Lock-in Assessment │
     │                     │                 5 dimensions       │
     │                     │                     │                    │
     │                     │              ⑨  Trình duyệt [G03] │
     │                     │                 → Risk Assessed    │
     │                     │                     │                    │
     │                     │                     ├──────────────────► │
     │                     │                     │             ⑩ Phê duyệt [G04]
     │                     │                     │                → Locked
     │                     │                     │                    │
     ◄───────────────────────────────────────────────────────────────
     │
⑪  Tech Spec Locked
   → Trigger IMM-03
   → Register IMM-10
```

## II.2. Decision Points

| Gate | Condition | Result khi fail |
|---|---|---|
| G01 | ≥ 8 mandatory requirements, 100% có test_method | Block Draft → Reviewing |
| G02 | ≥ 3 benchmark candidates với spec_match_pct + price + support | Block Reviewing → Benchmarked |
| G03 | 6/6 infra domains có status đánh giá | Block Benchmarked → Risk Assessed |
| G04 | lock_in_score ≤ threshold OR mitigation_plan + evidence | Block Pending Approval → Locked |

## II.3. Exception Flows

| Tình huống | Xử lý |
|---|---|
| Spec cần sửa sau Lock | Withdraw → Reissue (version bump: 1.0 → 2.0) |
| HTM Engineer từ chối requirements → quay Draft | Transition: Reviewing → Draft (Yêu cầu chỉnh) |
| Infra Need Major Upgrade → block procurement | Infra item status = Need Major Upgrade → cảnh báo; tạo IMM-04 Prep Item |
| Lock-in score cao nhưng không có lựa chọn khác | Ghi mitigation_plan + mitigation_evidence → VP Block1 duyệt exception |

## II.4. RACI Matrix

| Hoạt động | HTM Eng | KH-TC | QA Risk | CNTT | PTP K1 | VP Block1 |
|---|---|---|---|---|---|---|
| Tạo/soạn Tech Spec | R+A | I | I | — | C | I |
| Market Benchmark | I | R+A | C | — | C | I |
| Infra Compat | C | C | R | A (Network) | C | I |
| Lock-in Risk | C | C | R+A | — | C | I |
| Lock spec | I | I | I | — | R | A |
| Withdraw/Reissue | R | C | C | — | C | A |

R=Responsible A=Accountable C=Consulted I=Informed

---

# Phần III — Use Cases

## UC-01: Tạo Tech Spec Từ Procurement Plan

| Thuộc tính | Giá trị |
|---|---|
| UC ID | UC-IMM02-01 |
| Actor | HTM Engineer, KH-TC Officer |
| Pre-condition | IMM-01 Procurement Plan Approved, plan_item có device_model_ref |
| Post-condition | Tech Spec ở trạng thái Draft, link plan_line được set |

**Main Flow:**

| Step | Actor | Action |
|---|---|---|
| 1 | KH-TC | Mở Procurement Plan → click "Generate Tech Spec Drafts" |
| 2 | System | Gọi `draft_from_plan(plan, plan_lines)` |
| 3 | System | Kiểm tra VR-02-01: 1 plan_line ↔ 1 Active Tech Spec |
| 4 | System | Tạo Tech Spec với device_model_ref, quantity từ plan_item |
| 5 | System | Gọi `seed_default_requirements()` nếu Device Model có spec_template_ref |
| 6 | System | Ghi `IMM Audit Trail` event "Draft Created" |
| 7 | System | Trả về list TS names đã tạo |

**Alternate Flows:**
- 3a: Plan line đã có Active Tech Spec → throw `ServiceError(DUPLICATE, "VR-02-01: plan_line đã có Tech Spec active")`

## UC-02: Soạn Requirements

| Thuộc tính | Giá trị |
|---|---|
| UC ID | UC-IMM02-02 |
| Actor | HTM Engineer |
| Pre-condition | Tech Spec ở Draft hoặc Reviewing |

**Main Flow:**

| Step | Actor | Action |
|---|---|---|
| 1 | HTM Engineer | Mở Tech Spec → Tab "Yêu cầu KT" |
| 2 | HTM Engineer | Thêm requirements: group, parameter, value_or_range, is_mandatory, test_method |
| 3 | System | Validate VR-02-02 (≥ 1 mandatory), VR-02-03 (mandatory có test_method) |
| 4 | HTM Engineer | Click "Gửi rà soát" (Gate G01) |
| 5 | System | Kiểm tra G01: ≥ 8 mandatory + 100% test_method |
| 6 | System | Transition Draft → Reviewing; ghi audit trail |

## UC-03: Market Benchmark

| Thuộc tính | Giá trị |
|---|---|
| UC ID | UC-IMM02-03 |
| Actor | KH-TC Officer |
| Pre-condition | Tech Spec ở Reviewing |

**Main Flow:**

| Step | Actor | Action |
|---|---|---|
| 1 | KH-TC | Mở Tech Spec → Tab "Benchmark" |
| 2 | KH-TC | Tạo Market Benchmark, nhập ≥ 3 candidates (manufacturer, model, spec_match_pct, price, support_tier) |
| 3 | System | Auto-compute spec_match_pct và recommendation_score |
| 4 | System | Set recommended_candidate = candidate có score cao nhất |
| 5 | KH-TC | Click "Hoàn tất benchmark" (Gate G02) |
| 6 | System | Kiểm tra G02: candidate_count ≥ 3 |
| 7 | System | Transition Reviewing → Benchmarked |

## UC-04: Infra Compatibility + Lock-in Risk

| Thuộc tính | Giá trị |
|---|---|
| UC ID | UC-IMM02-04 |
| Actor | QA Risk Team, CNTT |
| Pre-condition | Tech Spec ở Benchmarked |

**Main Flow:**

| Step | Actor | Action |
|---|---|---|
| 1 | QA Risk | Điền 6 mục Infra Compat: Electrical, Medical Gas, Network/IT, HIS-PACS-LIS, HVAC, Space-Layout |
| 2 | CNTT | Điền Network/IT + HIS-PACS-LIS status |
| 3 | QA Risk | Tạo Lock-in Risk Assessment, điền 5 dimensions (Protocol, Consumable, Software, Parts, Service) |
| 4 | System | Auto-compute lock_in_score = weighted sum |
| 5 | QA Risk | Click "Trình duyệt" (Gate G03) |
| 6 | System | Kiểm tra G03: 6/6 mục infra có status |
| 7 | System | Transition Benchmarked → Risk Assessed |

## UC-05: Lock Spec

| Thuộc tính | Giá trị |
|---|---|
| UC ID | UC-IMM02-05 |
| Actor | PTP Khối 1, VP Block1 |
| Pre-condition | Tech Spec ở Pending Approval |

**Main Flow:**

| Step | Actor | Action |
|---|---|---|
| 1 | PTP K1 | Transition Risk Assessed → Pending Approval |
| 2 | VP Block1 | Review Tech Spec toàn bộ |
| 3 | System | Kiểm tra G04: lock_in_score ≤ threshold OR mitigation_plan |
| 4 | VP Block1 | Click "Phê duyệt" → Lock spec |
| 5 | System | `lock_spec()`: docstatus=1, state=Locked |
| 6 | System | Publish `imm02_spec_locked` → IMM-03 listener |
| 7 | System | Ghi audit trail "Locked" |

## UC-06: Withdraw + Reissue

| Thuộc tính | Giá trị |
|---|---|
| UC ID | UC-IMM02-06 |
| Actor | VP Block1, HTM Engineer |
| Pre-condition | Tech Spec ở Locked |

**Main Flow:**

| Step | Actor | Action |
|---|---|---|
| 1 | VP Block1 | Click "Rút" → nhập withdrawal_reason |
| 2 | System | Transition Locked → Withdrawn; `withdraw_spec()` |
| 3 | HTM Engineer | Click "Reissue" |
| 4 | System | `reissue()`: copy_doc, parent_spec = spec.name, version bump, state = Draft |
| 5 | HTM Engineer | Chỉnh sửa requirements → submit lại từ đầu |

---

# Phần IV — Functional Specifications

## IV.1. User Stories (Business Rules Table)

| BR ID | Rule | Enforce at | Chuẩn |
|---|---|---|---|
| BR-02-01 | 1 Procurement Plan Line ↔ 1 Tech Spec Active | `_vr01_unique_per_plan_line` | Traceability |
| BR-02-02 | ≥ 8 mandatory requirements trước Reviewing | G01: `validate_gate_g01` | WHO Procurement Spec §3.4 |
| BR-02-03 | Mandatory requirement phải có test_method | `_vr03_test_method_present` | ISO 13485 §7.3.3 |
| BR-02-04 | ≥ 3 benchmark candidates | G02: `validate_gate_g02` | WHO HTA §4.2 |
| BR-02-05 | 6/6 infra domains phải đánh giá | G03: `validate_gate_g03` | WHO HTM §4 |
| BR-02-06 | Lock-in score ≤ threshold hoặc có mitigation | G04: `validate_gate_g04` | NĐ 98 §29 |
| BR-02-07 | Locked spec không sửa; phải Withdraw + Reissue | `before_save` check docstatus=1 | ISO 13485 §7.3.7 |

## IV.2. State Machine

```
        Gửi rà soát [G01]
Draft ─────────────────────► Reviewing
  ▲                               │ Hoàn tất benchmark [G02]
  │ Yêu cầu chỉnh                ▼
  │                          Benchmarked
  │                               │ Hoàn tất compat + lock-in [G03]
  │                               ▼
  │                         Risk Assessed
  │                               │ Trình duyệt
  │                               ▼
  │                       Pending Approval
  │                          │         │
  │                Phê duyệt [G04]   Rút
  │                          ▼         ▼
  └─────────────────────── Locked  Withdrawn ─► (Reissue → Draft v2)
```

---

# Phần V — Non-Functional Requirements

| ID | Thuộc tính | Yêu cầu | Cách đo |
|---|---|---|---|
| NFR-02-01 | Performance | `list_tech_specs` p95 < 1.5s, 50 concurrent | k6 load test |
| NFR-02-02 | Performance | `draft_from_plan` 10 lines < 5s | Frappe benchmark |
| NFR-02-03 | Bulk import | Excel 100 rows < 10s | k6 |
| NFR-02-04 | Availability | 99.5% trong giờ hành chính | Uptime monitoring |
| NFR-02-05 | Security | Permlevel 1 fields (lock_in_score) chỉ QA Risk + VP Block1 | Automated perm test |
| NFR-02-06 | Auditability | Mọi state transition ghi `IMM Audit Trail` trong 500ms | Log verify |
| NFR-02-07 | Immutability | Locked spec không sửa được — 0 bypass cases | Unit test |
| NFR-02-08 | Localization | 100% label tiếng Việt; tất cả error message tiếng Việt | UI review |
| NFR-02-09 | Compliance | Traceability plan_line → spec → lock-in → IMM-03 | Audit trail verify |
| NFR-02-10 | Scalability | 200 Tech Spec concurrent users không degrade | Load test |
