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
| BR-02-08 | CTA duyệt (Chốt / Rút / Phát hành lại) hiển thị theo cờ **server-driven** `can_lock`/`can_withdraw`/`can_reissue`; FE KHÔNG tự suy từ `workflow_state` | `get_tech_spec` derive cờ = (state-predicate ∧ capability) | Anti dead-gate / least-privilege |
| BR-02-09 | Chốt / Rút hồ sơ chỉ cho user có **capability `spec.submit`**; Phát hành lại cần `spec.create`. Thiếu quyền → `FORBIDDEN` (KHÔNG pass-through state rồi submit thành công) | `_require_spec_approver()` (guard: capability → state) ở `_lock_spec`/`_withdraw_spec`; `_reissue_spec` guard `spec.create` | NĐ98 §29 (chỉ người có thẩm quyền chốt hồ sơ mua sắm) |
| BR-02-10 | **6 transition trung gian** (Gửi rà soát · Yêu cầu chỉnh spec · Hoàn tất benchmark · Đánh giá rủi ro xong · Trình duyệt spec · Yêu cầu chỉnh risk) hiển thị thành **CTA server-driven** theo `allowed_actions` (đã lọc role). FE render 1 nút / mỗi action; KHÔNG hardcode `workflow_state ===`. Đóng bug "spec kẹt ở Draft/Reviewing/Benchmarked/Risk Assessed dù đủ quyền" (endpoint `transition_workflow` LIVE nhưng 0 nút render) | `get_tech_spec` emit `allowed_actions = spec_allowed_actions(state, roles)`; SSoT `_SPEC_VALID_TRANSITIONS` reconcile EXACT với `imm_02_spec_workflow.json` | Advertise ⟺ reachable / Anti hidden-CTA |

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

## IV.3. Server-driven CTA gating + BE role enforcement (GATE-8 / LL-FE-51)

Đặc tả cho vòng 6 (CTA duyệt hồ sơ). Đóng 2 lỗ thiết kế gốc:
1. **Dead-gate FE:** `TechSpecDetailView.vue` gate nút bằng `workflow_state === 'X'` (false-permissive: nút hiện cho MỌI user login, bấm mới lỗi).
2. **Thiếu role check BE:** `_lock_spec`/`_withdraw_spec` chỉ guard `workflow_state`, KHÔNG kiểm quyền → user thiếu quyền vẫn Lock được (pass-through state → `doc.submit()`).

### SoT — bảng CTA hợp lệ theo state (role-agnostic hint)

`_SPEC_CTA_TRANSITIONS` (đặt trong `api/imm02.py`, cạnh `_DT_TS`):

| workflow_state | allowed_transitions (CTA key) |
|---|---|
| `Pending Approval` | `["lock", "withdraw"]` |
| `Locked` | `["withdraw"]` |
| `Withdrawn` | `["reissue"]` |
| `Draft` / `Reviewing` / `Benchmarked` / `Risk Assessed` / state lạ / `None` | `[]` (`.get(state, [])` degrade an toàn) |

`allowed_transitions` là **hint hiển thị role-agnostic** (state cho phép hành động gì) — KHÔNG nới lỏng guard.

### Cờ capability (server-derive, đưa vào `get_tech_spec`)

```
allowed = _SPEC_CTA_TRANSITIONS.get(state, [])
approve = rbac.can("spec.submit")          # ("IMM Tech Spec","submit")
can_lock     = int("lock"     in allowed and approve)
can_withdraw = int("withdraw" in allowed and approve)
can_reissue  = int("reissue"  in allowed and rbac.can("spec.create"))
```

- **Lock / Withdraw** → capability `spec.submit`: cả hai gọi `doc.submit()` (hoặc sửa doc đã submit) ⇒ quyền nội tại = *submit* trên `IMM Tech Spec`. Gate đúng bằng quyền vật lý mà thao tác cần → cờ = tập guard cho phép (invariant khít). DocPerm submit=1: **AssetCore Super Admin, Spec Manager**.
- **Reissue** → capability `spec.create`: tạo bản Draft mới (`copy_doc` + `insert`) ⇒ quyền nội tại = *create*. DocPerm create=1: **AssetCore Super Admin, Spec Manager, Spec User**.
- Cờ trả **int 0/1** (đồng bộ `can_approve` của IMM-05); FE coerce `Boolean()`.

> Vì sao capability chứ KHÔNG role-name: dự án theo **capability-based RBAC** (`services/shared/rbac.py`) — gate bằng tên role không tồn tại = anti-pattern *RBAC dead-gate* (fail âm thầm). Đổi quyền = sửa DocPerm ở `/app`, KHÔNG deploy code.

### INVARIANT — map ⊆ guard-permitted

Với **mọi** (state, user): cờ `get_tech_spec` advertise ⊆ tập guard thực cho phép. Không cờ nào mở hành động mà guard sẽ reject (không "hiện nút rồi bấm mới FORBIDDEN/BAD_STATE"). Giữ được vì cờ = `(action ∈ state-map) ∧ rbac.can(cap)` và guard = `rbac.can(cap) ∧ state-check`, với state-map mã hoá đúng các state mà state-check của guard pass.

### Boundaries (Always / Never)

- **Always:** derive cờ CTA server-side từ `_SPEC_CTA_TRANSITIONS` + `rbac.can(...)`; guard thứ tự **capability → state** (defense-in-depth); lỗi quyền = `ServiceError(FORBIDDEN)` → envelope HTTP-200 (in-handler cap-403, KHÔNG raise→HTTP-4xx); mọi state lạ/`None` → `[]` + 3 cờ false.
- **Never:** hardcode role-name trong guard/derive; FE gate nút bằng `workflow_state ===` trong computed CTA; advertise cờ vượt tập guard cho phép; đổi DocPerm/enum trong code path này mà không flag (Ask-first).

### ADR-IMM02-01: CTA duyệt hồ sơ — server-driven flag + capability guard

- **Status**: Accepted
- **Date**: 2026-07-09
- **Context**: `_lock_spec`/`_withdraw_spec` chỉ guard state (thiếu role check) và FE hardcode `workflow_state===` → (a) mọi user login thấy+bấm "Chốt hồ sơ"; (b) chuỗi lesson "không duyệt được dù full quyền QTV" cần đảm bảo Super Admin vẫn chốt được. Cần một nguồn phân quyền nhất quán giữa cờ hiển thị và guard BE.
- **Decision**: Đưa `allowed_transitions` + 3 cờ `can_lock/can_withdraw/can_reissue` vào `get_tech_spec`, derive từ `_SPEC_CTA_TRANSITIONS` (state) ∧ `rbac.can("spec.submit"/"spec.create")` (quyền). Guard `_lock_spec`/`_withdraw_spec` bằng `rbac.can("spec.submit")` (thứ tự capability → state); `_reissue_spec` bằng `spec.create`. FE đọc DUY NHẤT cờ server.
- **Alternatives**:
  - *Gate bằng role-name workflow (Procurement Manager…)* — loại: RBAC dead-gate anti-pattern + doc V.2 role-name đã lệch fixture; `lock_spec` không đi qua `apply_workflow` nên `allowed` role của workflow không thực sự chặn.
  - *Thêm capability mới `spec.approve`* (như IMM-05 `doc.approve`) — loại: `spec.submit`/`spec.create` auto-gen đã map đúng quyền vật lý; thêm cap → đổi `CAP_SET_VERSION` → buộc FE invalidate cache thừa.
- **Consequences**: Cờ = tập guard (invariant khít, dễ test). Không đổi CAP_SET_VERSION (dùng cap có sẵn) → FE không cần invalidate. Đánh đổi: "role duyệt" giờ = DocPerm submit trên IMM Tech Spec (Super Admin + Spec Manager), KHÔNG phải "Procurement Manager" như V.2 doc/fixture ngụ ý — nếu nghiệp vụ muốn Procurement Manager chốt, cấp DocPerm submit=1 cho role đó ở `/app` (config, không code). *(Cần khảo sát: xác nhận với chủ đầu tư ai là "người chốt hồ sơ kỹ thuật" — Spec Manager hay Procurement Manager.)*

### IV.4. Server-driven CTA cho 6 transition trung gian (Trục A / CR-WF-02-SPEC — vòng 24)

Đóng bug **"hidden-CTA-câm"**: `TechSpecDetailView.vue` chỉ có 3 nút terminal (Chốt/Rút/Phát hành lại — vòng 6). 6 transition trung gian của workflow `imm_02_spec_workflow.json` (endpoint `transition_workflow` LIVE) **KHÔNG có nút nào render** → spec kẹt ở `Draft`/`Reviewing`/`Benchmarked`/`Risk Assessed` dù user đủ quyền. Fix: đặc tả một SSoT action-tuple, role-filtered, phơi `allowed_actions` cho FE. **Mirror IMM-03 AVL** (`services/imm03.py::_AVL_VALID_TRANSITIONS` + `avl_allowed_transitions`) và **IMM-01 Needs** (FE render 1 nút/`allowed_actions`).

#### SSoT `_SPEC_VALID_TRANSITIONS` (đặt trong `services/imm02.py`)

`dict[state, list[(action, next_state, frozenset[roles])]]` — mã hoá **6 cạnh** (đã gom vai theo backfill admin-override V5 → mọi cạnh có thêm `AssetCore Super Admin` + `System Manager`). Roles của mỗi cạnh = **tập `allowed` gom-vai của group `(state, action, next_state)` trong `imm_02_spec_workflow.json`** (grounded @source, không bịa):

| state | action (nhãn VI) | next_state | roles (frozenset) |
|---|---|---|---|
| `Draft` | `Gửi rà soát` | `Reviewing` | `Spec User` + Admin* |
| `Reviewing` | `Yêu cầu chỉnh spec` | `Draft` | `Spec User`, `Needs Manager` + Admin* |
| `Reviewing` | `Hoàn tất benchmark` | `Benchmarked` | `Needs Manager` + Admin* |
| `Benchmarked` | `Đánh giá rủi ro xong` | `Risk Assessed` | `Spec Manager` + Admin* |
| `Risk Assessed` | `Trình duyệt spec` | `Pending Approval` | `Commissioning Manager` + Admin* |
| `Pending Approval` | `Yêu cầu chỉnh risk` | `Risk Assessed` | `Procurement Manager` + Admin* |

`Admin* = {AssetCore Super Admin, System Manager}`. `Locked`/`Withdrawn` (docstatus=1, terminal workflow-engine) **∉ map keys** → `spec_allowed_actions` trả `[]`.

`_SPEC_EXCEPTION_ACTIONS = {'Phê duyệt spec','Rút spec'}` — 2 cạnh rời `Pending Approval` (→ `Locked`/`Withdrawn`) **KHÔNG** vào map: đã do endpoint `lock_spec`/`withdraw_spec` + cờ `can_lock`/`can_withdraw` xử lý (vòng 6). Không đưa vào map để **KHÔNG double-render** trên action-bar.

> Lưu ý: `Yêu cầu chỉnh risk` (Pending Approval → Risk Assessed) **CÓ** trong map (là CTA trung gian, ≠ exception). Nên tại `Pending Approval`, action-bar hiện đồng thời: `[Chốt hồ sơ]` + `[Rút hồ sơ]` (từ cờ can_lock/can_withdraw) và `[Yêu cầu chỉnh risk]` (từ allowed_actions).

#### `spec_allowed_actions(workflow_state, user_roles=None) -> list[str]`

Derive tập **nhãn ACTION** hợp lệ cho `workflow_state`, ĐÃ LỌC theo role (mirror `avl_allowed_transitions`). `user_roles=None` → trả full SoT của state (không lọc). Degrade an toàn: state lạ/terminal → `[]`. Đo được:

| state | roles user | `allowed_actions` |
|---|---|---|
| `Draft` | `Spec User` | `['Gửi rà soát']` |
| `Reviewing` | `Needs Manager` | `['Yêu cầu chỉnh spec','Hoàn tất benchmark']` |
| `Reviewing` | `Spec User` | `['Yêu cầu chỉnh spec']` (KHÔNG có `Hoàn tất benchmark`) |
| `Locked` / `Withdrawn` | bất kỳ | `[]` |

#### INVARIANT-1 — reconcile map ⇄ workflow fixture (RED khi map rỗng → GREEN sau 6 cạnh)

Test `test_spec_allowed_transitions_matches_workflow_fixture` (STATIC, parse JSON):
1. Build `wf_groups[(state, action, next_state)] = ∪ allowed` từ `imm_02_spec_workflow.json`.
2. Với **mọi** `(state, action, next_state, roles)` trong `_SPEC_VALID_TRANSITIONS`: `roles == wf_groups[(state,action,next_state)]` (khớp đủ, EXACT).
3. `{action ∀ transition workflow} − {action ∀ entry map} == _SPEC_EXCEPTION_ACTIONS` (== `{'Phê duyệt spec','Rút spec'}`).

RED-demo: map rỗng/thiếu 1 cạnh → điều kiện (3) sai (diff ⊋ 2 action) hoặc (2) KeyError → đỏ. GREEN sau khi bồi đủ 6 cạnh.

#### INVARIANT-2 — advertise ⟺ reachable (map ⊆ guard-permitted)

Vì roles trong map == `allowed` của workflow (INVARIANT-1) và `transition_workflow` áp qua **`apply_workflow` native** (Frappe enforce đúng `allowed` role của transition): với user có role, mỗi `action ∈ allowed_actions` ⟹ `transition_workflow(name, action)` **KHÔNG raise permission** + `workflow_state` đổi đúng `next_state`; user thiếu role của cạnh ⟹ action KHÔNG xuất hiện trong `allowed_actions`.

> **Phân biệt RBAC-gate ≠ business-gate:** `allowed_actions` chỉ advertise cạnh **role-reachable**. Bấm nút vẫn có thể trả `BUSINESS_RULE` (G01–G04, vd Draft→Reviewing cần ≥8 mandatory) — đó là UX đúng (thông điệp gate hướng dẫn user), KHÔNG mâu thuẫn INVARIANT-2. Test hành vi INVARIANT-2 phải dựng fixture thoả gate cho cạnh đang kiểm, hoặc assert ở mức role-permission.

#### 2 loại 403 của `transition_workflow` (DONE-gate spec-contract)

- **dispatcher-403** (guest / no-token): Frappe từ chối TRƯỚC handler (endpoint bare `@whitelist(methods=["POST"])`, không `allow_guest`).
- **in-handler cap-403** (user login thiếu role của cạnh): `apply_workflow` → `frappe.PermissionError` → `_handle` bắt → `_err(str(e), FORBIDDEN)` = **HTTP-200 + Error envelope** (KHÔNG raise→HTTP-4xx).

#### Boundaries (Always / Never)

- **Always:** roles trong `_SPEC_VALID_TRANSITIONS` = tập `allowed` gom-vai của workflow fixture (INVARIANT-1 khoá); `allowed_actions` lọc role qua `frappe.get_roles(user)`; state lạ/terminal → `[]`; FE render 1 nút/action + gate DUY NHẤT theo membership `allowed_actions`.
- **Never:** đụng file `imm_02_spec_workflow.json` (admin-override guard `test_workflow_admin_override` phải GIỮ GREEN); đưa `Phê duyệt spec`/`Rút spec` vào map (double-render với can_lock/can_withdraw); FE hardcode `workflow_state ===` để bật/tắt nút wf; bịa role không có trong fixture (RBAC dead-gate).

### ADR-IMM02-02: Surface 6 transition trung gian thành server-driven CTA (SSoT action-tuple)

- **Status**: Accepted
- **Date**: 2026-07-13
- **Context**: Vòng 6 chỉ phơi 3 CTA terminal (lock/withdraw/reissue). 6 transition trung gian có endpoint `transition_workflow` LIVE nhưng FE 0 nút → spec kẹt dù đủ quyền (bug "hidden-CTA-câm", Trục A). Cần nguồn phân quyền server-driven cho FE render nút, khít với role thực của workflow (advertise ⟺ reachable), KHÔNG đụng workflow JSON (giữ admin-override guard).
- **Decision**: Thêm SSoT `_SPEC_VALID_TRANSITIONS` (action, next_state, frozenset[roles]) + `spec_allowed_actions()` trong `services/imm02.py` (mirror IMM-03 AVL). `get_tech_spec` emit thêm key `allowed_actions` (đã lọc role). FE render 1 nút / entry, `data-testid=cta-wf-<slug>`, click → `store.transitionWorkflow(name, action)` → refetch. Reconcile INVARIANT khoá map == fixture; 2 exception action (`Phê duyệt spec`/`Rút spec`) do lock/withdraw xử lý (KHÔNG double-render).
- **Alternatives**:
  - *Hardcode `workflow_state ===` cho từng nút ở FE* — loại: dead-gate anti-pattern (nút hiện cho mọi user, bấm mới lỗi) + desync khi workflow đổi role.
  - *Thêm cạnh vào workflow JSON / gộp map với `allowed_transitions` (next-state của vòng 6)* — loại: đụng workflow JSON phá admin-override guard; `allowed_transitions` là **next-STATE** (Locked/Withdrawn/Draft) — semantic khác `allowed_actions` (nhãn action) → giữ 2 key riêng, không collide.
  - *Guard role tường minh ở `transition_workflow` như AVL (`avl_transition_target`)* — KHÔNG cần: AVL dùng `db.set_value` (bỏ qua workflow role) nên phải tự guard; IMM-02 `transition_workflow` đã đi qua `apply_workflow` (native enforce role) → reconcile INVARIANT-1 đủ đảm bảo advertise ⟺ reachable.
- **Consequences**: `allowed_actions` (action) và `allowed_transitions` (next-state, vòng 6) cùng tồn tại trên `get_tech_spec` — doc rõ 2 key khác semantic. Đổi role/transition trong fixture → phải đồng bộ map (INVARIANT-1 đỏ nếu quên). Chỉ sửa `.py` service/api → cần worker reload để live (HARD-STOP USER). Không đổi `CAP_SET_VERSION`, không migrate.

### IV.5. Đóng dead-gate persona `Spec User` + INVARIANT phủ Role Profile toàn workflow (Trục A / CR-WF-RBAC-PROFILE-COVERAGE — vòng 34)

> **Phạm vi (Boundaries):**
> - **Always (áp dụng):** đóng đúng 1 dead-gate persona ở IMM-02 (`Gửi rà soát`) bằng cách bổ sung role vào **Role Profile catalog** (SSoT), + 1 INVARIANT own-file reconcile transition-role ⊆ profile-catalog trên **cả 22 workflow**.
> - **Never (tuyệt đối không):** đụng `imm_02_spec_workflow.json` / `fixtures/workflow.json` / `_SPEC_VALID_TRANSITIONS` (giữ INV-A/B/C + `test_workflow_admin_override` GREEN); nới quyền cho base role `AssetCore System User`; đẻ persona/Role Profile mới (vẫn 8 profile).

#### Vấn đề — dead-gate persona

Transition `Gửi rà soát` (`Draft → Reviewing`) trong `imm_02_spec_workflow.json` được gate **sole non-admin** trên role **`Spec User`** (+ `AssetCore Super Admin`, `System Manager` do backfill admin-override). **KHÔNG Role Profile nào** trong `ROLE_PROFILE_CATALOG` (`setup/role_profile_catalog.py`) cấp `Spec User` → trong thực tế **chỉ Super Admin / System Manager** chuyển được `Draft → Reviewing`. Persona chủ-đích soạn spec (**Trưởng phòng VT-TTBYT**, hiện có `Spec Manager` + `Needs Manager` + `Commissioning Manager` + `Procurement Manager`) **không** đẩy được spec đi rà soát dù DocPerm cho tạo/sửa Draft → **dead-gate** (advertise một cạnh mà persona nghiệp vụ không bao giờ reachable).

**Grounding coverage (scan thật 22 workflow ⇄ catalog):** `Spec User` là **role UNCOVERED DUY NHẤT** trên toàn bộ 22 workflow — xuất hiện ở **2** transition IMM-02: `Gửi rà soát` (sole non-admin) và `Yêu cầu chỉnh spec` (`Reviewing→Draft`, co-list `Needs Manager`). Mọi role gated khác ∈ (∪ `roles_for_profile`) ∪ Admin ∪ `Vendor Engineer`. `Vendor Engineer` (EXCEPTION — NCC ngoài, cố ý KHÔNG thuộc profile nội bộ) xuất hiện ở **3** transition IMM-04, **cả 3 đều co-list `PM User`** (profile-backed) → không sole-gate → reachable bởi nhân sự BV.

#### Quyết định — bổ sung `Spec User` vào Role Profile "Trưởng phòng VT-TTBYT" (KHÔNG re-gate workflow)

Fix = **catalog-only** (delta 1 dòng trong `role_profile_catalog.py`):

```python
"Trưởng phòng VT-TTBYT": [
    "Commissioning Manager", "Needs Manager",
    "Procurement Manager", "Spec Manager", "Spec User",   # + Spec User (CR round 34)
],
```

Vì sao chọn hướng này (không re-gate `imm_02_spec_workflow.json`):

1. **Boundary đã chốt** (§IV.4, dòng "Never đụng `imm_02_spec_workflow.json`") — re-gate JSON phá admin-override guard + đòi tri-sync source⇄fixtures⇄DB. Catalog-only chỉ chạm 1 file + 1 sync idempotent.
2. **`Spec User` là role thiết kế có chủ đích, không phải rác:** DocPerm IMM Tech Spec 2-tier — `Spec User` (create=1, write=1, **submit=0** — người soạn Draft) vs `Spec Manager` (create/write/**submit=1** — cấp chốt docstatus). `Spec User` còn nằm ở DocPerm 10 doctype con (tech_spec_requirement, benchmark_candidate, imm_market_benchmark…). Nó chỉ **bị bỏ sót khỏi mọi profile** — lỗi coverage, không phải role thừa. Home đúng của nó = profile của phòng sở hữu IMM-02 (VT-TTBYT).
3. **Zero blast-radius:** `_SPEC_VALID_TRANSITIONS`/workflow JSON/`allow_edit`(Draft/Reviewing = `Spec User`) đều **giữ nguyên** → khi persona VT-TTBYT có `Spec User` thì tạo Draft + G01 add-requirement (allow_edit khớp) + `Gửi rà soát` (transition-gate khớp) đều thông cùng 1 role. Test cũ (`test_imm02` 593–604, INV-A/B/C) **không đỏ**.

> Footnote SoT table §IV.4: hàng `Gửi rà soát | Spec User + Admin*` **không đổi**; kể từ CR vòng 34, `Spec User` đã **profile-backed** qua "Trưởng phòng VT-TTBYT" → hàng này **không còn là dead-gate**.

#### INVARIANT own-file mới (RED-trước → GREEN-sau)

File RIÊNG `assetcore/tests/test_workflow_role_profile_coverage.py` (FILE-driven — glob source JSON + đọc `ROLE_PROFILE_CATALOG`, mirror helper `_transition_groups` của `test_workflows.py`). 2 assert:

- **INV-COV (coverage):** với **mọi** transition trong **22** source workflow JSON, mọi `allowed` role **non-admin** PHẢI ∈ `ALLOWED = (∪ roles_for_profile(p) ∀ p ∈ ROLE_PROFILE_CATALOG) ∪ {AssetCore Super Admin, System Manager} ∪ EXCEPTION_ROLES`, với `EXCEPTION_ROLES = frozenset({"Vendor Engineer"})`. **RED-trước:** `Spec User ∉ ALLOWED` → assert liệt kê `{Spec User}`. **GREEN-sau:** thêm `Spec User` vào catalog → `Spec User ∈ ∪roles_for_profile` → tập uncovered rỗng.
- **INV-EXC-REACH (EXCEPTION không thành dead-gate thật):** mọi **transition-group** `(state, action, next_state)` mà tập `allowed` **giao** `EXCEPTION_ROLES` PHẢI đồng thời chứa ≥1 role profile-backed (∈ `∪roles_for_profile`). Assert **KHÔNG group nào sole-gated bằng EXCEPTION role**. Thực tế: 3 group IMM-04 gating `Vendor Engineer` đều co-list `PM User` → GREEN. (Guard này chặn việc "biến EXCEPTION thành cửa hậu chết": nếu ai đó thêm 1 cạnh chỉ Vendor Engineer → RED.)

> **Vì sao dùng EXCEPTION thay vì nhét `Vendor Engineer` vào profile:** `Vendor Engineer` là role NCC bên ngoài (row-level vendor isolation), **cố ý** không gán cho persona nội bộ nào (không phải nhân sự BV). Nếu ép vào profile sẽ sai mô hình quyền. Thay vào đó whitelist tường minh trong `EXCEPTION_ROLES` + guard reachability (INV-EXC-REACH) để nó không âm thầm thành dead-gate.

#### Hành vi BE integration (acceptance — RED/GREEN)

| Bối cảnh | Trước fix (RED) | Sau fix (GREEN) |
|---|---|---|
| User non-admin có profile **Trưởng phòng VT-TTBYT**, tạo IMM Tech Spec Draft đủ 8 spec-line (G01), gọi `transition_workflow(name, 'Gửi rà soát')` | **Chặn.** Guard `spec_allowed_actions('Draft', roles)` role-filtered = `[]` (user chưa có `Spec User`) → in-handler **HTTP-200 + Error envelope `BAD_STATE`** (ValidationError-family). *(Nếu test gọi thẳng `apply_workflow` bỏ guard → Frappe `PermissionError`.)* | **Thành công.** User đã có `Spec User` (qua profile) → guard trả `['Gửi rà soát']` → `apply_workflow` (native enforce `allowed`) chuyển state → `workflow_state == 'Reviewing'`. |
| Base role **`AssetCore System User`** (không role spec), gọi `Gửi rà soát` | **Chặn** (BAD_STATE / PermissionError) | **VẪN chặn** — base role không nằm trong bất kỳ gate của cạnh này. Dead-gate đóng **đúng cho persona chủ-đích**, KHÔNG mở-toang. |

Ranh giới 2 loại 403 (DONE-gate spec-contract, §IV.4): (a) **dispatcher-403** guest/no-token — Frappe từ chối trước handler; (b) **in-handler cap-403 / BAD_STATE** — user login thiếu role → HTTP-200 + Error envelope (KHÔNG raise→4xx). Lỗi nghiệp vụ luôn về qua envelope, không status-line 4xx.

#### Triển khai (sync live — KHÔNG bench migrate)

Catalog là SSoT; đẩy xuống Role Profile DocType + re-sync `user.roles` bằng setup idempotent:

```
bench --site miyano execute assetcore.setup.setup_role_profiles.run
```

`seed_assetcore_role_profiles()` ép `update_all_users` chạy ĐỒNG BỘ (flag `in_install`) → user mang profile "Trưởng phòng VT-TTBYT" nhận thêm `Spec User` ngay, không phụ thuộc Redis, **không `bench migrate`**. Idempotent: chạy lại = `unchanged`.

#### Regression phải giữ GREEN

- INV-A/INV-B (`test_workflows.py`): admin-override — Super Admin vẫn `Draft→Reviewing`. Workflow JSON **không đổi** → GREEN.
- INV-C (source⇄fixtures parity): **không đổi** JSON/fixtures → GREEN.
- `test_imm02.py` 593–604 (`spec_allowed_actions` với `{Spec User}`): `_SPEC_VALID_TRANSITIONS` **không đổi** → GREEN.
- `test_role_profiles.py`: `len(PROFILE_NAMES)==8` giữ; role-set assert chỉ hardcode `_TECH`/`_STORE` (dynamic `roles_for_profile`), KHÔNG hardcode VT-TTBYT → thêm `Spec User` an toàn → GREEN.
- `test_spec_valid_transitions_reconciles_workflow_json` (INVARIANT-1 §IV.4): map ⇄ JSON **không đổi** → GREEN.

### ADR-IMM02-03: Đóng dead-gate persona bằng Role Profile catalog + INVARIANT coverage (không re-gate workflow)

- **Status**: Accepted
- **Date**: 2026-07-14
- **Context**: `Gửi rà soát` (Draft→Reviewing) sole non-admin gate = `Spec User`, nhưng `Spec User` không thuộc bất kỳ Role Profile nào → chỉ admin duyệt được (dead-gate persona chủ-đích). Cần đảm bảo mọi role gated trong workflow đều assignable qua profile (trừ EXCEPTION có chủ đích), và có test chốt bất-biến này cho **cả 22 workflow** để chống tái phát.
- **Decision**: Bổ sung `Spec User` vào `ROLE_PROFILE_CATALOG["Trưởng phòng VT-TTBYT"]` (catalog-only) + thêm file test own-file `test_workflow_role_profile_coverage.py` với INV-COV (role ⊆ profile∪admin∪EXCEPTION) và INV-EXC-REACH (EXCEPTION không sole-gate). Sync live bằng `setup_role_profiles.run` (idempotent, không migrate).
- **Alternatives**:
  - *Re-gate `Gửi rà soát` từ `Spec User` → `Spec Manager` trong `imm_02_spec_workflow.json`* — **loại**: vi phạm Boundary §IV.4 (Never đụng workflow JSON), phá admin-override guard, đòi tri-sync source⇄fixtures⇄DB, và còn buộc đổi cả `allow_edit` Draft/Reviewing + `_SPEC_VALID_TRANSITIONS` + test 593–604 → blast-radius lớn.
  - *Đẻ profile mới "Cán bộ vật tư" (bộ *User roles: Needs User, Spec User…)* — **loại** (ở CR này): thêm persona thứ 9 → phá `len(PROFILE_NAMES)==8` + đòi FE `personas.ts`; để `[ROADMAP]` nếu sau này cần tách cấp nhân viên soạn spec khỏi trưởng phòng.
  - *Nhét `Vendor Engineer` vào 1 profile để "cover"* — **loại**: sai mô hình (role NCC ngoài, vendor isolation) → dùng `EXCEPTION_ROLES` + guard reachability thay thế.
- **Consequences**: Profile "Trưởng phòng VT-TTBYT" nay gồm 5 domain role (+ base) — 1 persona lái trọn lifecycle IMM-02. `Spec User` hết orphan. Mọi workflow mới thêm role gated PHẢI cập nhật catalog HOẶC `EXCEPTION_ROLES` nếu không INV-COV đỏ (đúng ý đồ — buộc quyết định coverage tường minh). Không đổi `CAP_SET_VERSION`, không migrate.

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
