# IMM-10 — Analysis & Design

| Mục | Giá trị |
|---|---|
| Module | IMM-10 — Hậu kiểm và tuân thủ |
| Đợt | 3 |
| Trạng thái | In Progress (BE chưa scaffold) |
| Cập nhật | 2026-05-10 |

---

## I. Module Overview

### I.0 — Khảo sát As-Is

Tại các bệnh viện vận hành theo mô hình truyền thống (chưa có IMMIS), hậu kiểm và xử lý cảnh báo an toàn thiết bị thường gặp các vấn đề sau:

- Thông báo recall / FSCA từ vendor hoặc Bộ Y tế đến qua **email rời rạc** hoặc công văn giấy → không có hệ thống lưu vết "ai đã đọc, đã chuyển tới khoa nào, đã xử lý xong chưa".
- Phạm vi (scope) recall xác định bằng **Excel tay** — đối chiếu lot/serial/model thủ công, sót thiết bị, không truy được lịch sử điều chuyển nội viện.
- **Disclosure 48h** tới Bộ Y tế (theo NĐ98/2021 §post-market) thường lỡ hạn vì không có timer + reminder.
- CAPA mở từ nhiều nguồn (sự cố, kiểm định fail, audit nội bộ) **không có nơi tập trung theo dõi** → CAPA "rơi", quá hạn không ai biết.
- Báo cáo Management Review hàng quý phải **gom tay** từ nhiều file Excel.

*(Khảo sát cụ thể tại BV pilot — BA bổ sung trong sprint kế tiếp.)*

### I.1 — Pitch (To-Be)

IMM-10 biến hậu kiểm thành **vòng lặp khép kín có hệ thống**: mọi cảnh báo an toàn (vendor / regulator / nội bộ) được mở thành **Compliance Case**, hệ thống tự định danh phạm vi (asset / model / lot / serial), bulk-create Work Order recall, đếm ngược timer disclosure 48h, và đóng case khi 100% asset đã xử lý + báo cáo regulatory đã phát hành. CAPA xuyên module được **tracker tập trung** — Tổ QLCL nhìn 1 dashboard biết: bao nhiêu CAPA mở, quá hạn, hiệu quả ra sao.

### I.2 — Vị trí trong Lifecycle

| Lifecycle phase (WHO HTM) | Vai trò của IMM-10 |
|---|---|
| Operation | Thu nhận tín hiệu hậu kiểm liên tục từ IMM-09/11/12 |
| Maintenance | Trigger CAPA / recall WO khi cần |
| End-of-life | Cung cấp evidence khi quyết định decommission do safety (gate cho IMM-13/14) |

Khối kiến trúc: **C. KHỐI 3 — Vận hành**. Đợt: **3**.

### I.3 — Stakeholders

| Actor | Trách nhiệm chính | Ghi chú |
|---|---|---|
| Tổ HC-QLCL & Risk | Chủ trì Compliance Case, mở CAPA tracker, báo cáo Management Review | Owner module |
| PTP Khối 2 | Phê duyệt phạm vi recall trong nội viện, điều phối Workshop | |
| Pháp chế / Văn thư | Soạn + gửi công văn disclosure Bộ Y tế trong 48h | Phối hợp |
| BGĐ | Ký công văn đối ngoại; phê duyệt waive | Approver |
| Workshop / Nhóm TBYT | Thực thi action (replace / quarantine / update software) | Thực thi |
| Mạng lưới TBYT nội viện | Stand-down asset tại khoa, xác nhận hoàn tất | Field |
| Vendor / OEM | Cung cấp danh sách lot/serial, phối hợp kỹ thuật | External |
| Cơ quan QLNN | Nhận disclosure, ban hành chỉ đạo | External |

(Trích từ `Ho_so_kien_truc_IMMIS.md` line 265–272 — vai trò Tổ HC-QLCL & Risk: IMM-05, 06, **10**, 16, 17.)

### I.4 — Scope

**In scope:**
- Quản lý Compliance Case (Recall / FSCA / PMS Signal).
- Tự định danh phạm vi từ master data (`AC Asset`, `IMM Device Model`, lot/serial).
- Bulk-create Work Order type Recall và đẩy sang IMM-08 (PM) hoặc IMM-09 (Repair) tùy action.
- Disclosure timer 48h (NĐ98/2021).
- CAPA Action Tracker — view tổng hợp xuyên module.
- Compliance dashboard hậu kiểm.

**Out of scope:**
- Định nghĩa Compliance Rule chung — thuộc [IMM-16](../imm-16/README.md).
- Internal Audit cycle — thuộc IMM-16.
- Quản lý hồ sơ pháp lý cấp phép — thuộc [IMM-05](../imm-05/README.md).
- Calibration fail xử lý kỹ thuật — thuộc [IMM-11](../imm-11/README.md) (IMM-10 chỉ subscribe tín hiệu).

### I.5 — KPI

| KPI | Mô tả | Baseline | Target |
|---|---|---|---|
| Disclosure on-time rate | % case disclosure tới Bộ Y tế trong 48h | *(Cần khảo sát baseline)* | ≥ 95% |
| Recall completion time | Median ngày từ open case → 100% asset xử lý | *(Cần khảo sát baseline)* | ≤ 30 ngày |
| CAPA on-time closure | % CAPA đóng đúng deadline | *(Cần khảo sát baseline)* | ≥ 90% |
| Recall scope accuracy | Sai sót sót/dư trong affected_assets | *(Cần khảo sát baseline)* | < 2% |
| Effectiveness check pass | % CAPA pass effectiveness check 30/60/90 ngày | *(Cần khảo sát baseline)* | ≥ 85% |

### I.6 — Compliance

| Quy định | Yêu cầu áp lên module | Doc tham chiếu |
|---|---|---|
| NĐ98/2021/NĐ-CP | Báo cáo sự cố trong 48h tới Bộ Y tế; lưu trữ hồ sơ post-market ≥ 5 năm | `../gmdn/Quyết định 3107_QĐ-BYT.md` |
| QĐ 69/QĐ-BYT | Phân loại thiết bị A/B/C/D — recall ưu tiên class C/D | `../gmdn/Quyết định 69_QĐ-BYT.md` |
| QĐ 847/QĐ-BYT | Mã GMDN / nomenclature — định danh phạm vi recall theo mã | `../gmdn/Quyết định 847_QĐ-BYT.md` |
| ISO 13485 §8.2.1 | Customer feedback / complaint handling | *(Tham chiếu hệ ISO của bệnh viện)* |
| ISO 13485 §8.5.2 | Corrective action — gắn CAPA chain | `../ba/Phase_05_QMS_Governance_Design/03_CAPA_Workflow_Spec/CAPA_Workflow_Spec.md` |
| ISO 14971 | Risk management cho medical device — đánh giá residual risk khi recall | *(Tham chiếu hệ ISO của bệnh viện)* |

### I.7 — Risk

| Risk | Impact | Mitigation |
|---|---|---|
| Disclosure 48h breach | Vi phạm NĐ98 | Timer + alert tự động + escalation tới BGĐ |
| Sót affected asset trong scope | Bệnh nhân tiếp tục dùng thiết bị lỗi | Định danh đa lớp (model + lot + serial + range), reconcile với lịch sử điều chuyển IMM-13 |
| CAPA "rơi" không đóng | Lặp lại sự cố | Tracker với SLA + alert + Management Review hàng quý |
| Vendor không phản hồi danh sách lot | Không xác định scope | Workflow vendor liaison + escalation |
| Effectiveness check không thực hiện | Không biết action có hiệu quả | Scheduler tự nhắc 30/60/90 ngày sau close |

*(Các risk khác BA bổ sung trong sprint kế tiếp.)*

### I.8 — Roadmap

| Giai đoạn | Phạm vi | Điều kiện |
|---|---|---|
| Wave 3 — Sprint 1 | Compliance Case core + Disclosure timer | IMM-16 đã ship Compliance Rule Engine |
| Wave 3 — Sprint 2 | Bulk Recall Work Order + scope finder | IMM-04, IMM-08, IMM-09 stable |
| Wave 3 — Sprint 3 | CAPA Action Tracker + dashboard | IMM-12 CAPA chain ổn định |
| Wave 3 — Sprint 4 | Effectiveness check + Management Review feed | IMM-16 Management Review live |

(Tham chiếu Architecture line 278 — Đợt 3 yêu cầu data lineage + chất lượng dữ liệu + cơ chế management review.)

---

## II. BPMN

### II.1 — As-Is (truyền thống)

```
Vendor email recall → Văn thư BV → in giấy → chuyển VTTBYT
   → tra Excel master → list asset → email khoa → Excel tracker
   → Pháp chế soạn công văn (thường > 48h) → gửi BYT
   → khoa báo lại Excel khi xong → tổng hợp tay tháng/quý
```

Vấn đề: rời rạc, không có timer, dễ sót, không reproducible.

### II.2 — To-Be (IMM-10)

```
[Trigger: vendor / regulator / internal signal]
   ↓
[1] Open Compliance Case (Recall / FSCA / PMS)
       - severity, source, scope_criteria, action_required
   ↓
[2] Auto-find scope: query AC Asset by (model, lot_range, serial_range, mfg_date)
       - sinh affected_assets child table
   ↓
[3] Disclosure timer start (48h) — chỉ với recall regulatory-grade
   ↓
[4] Notify pháp chế → soạn công văn (template) → gửi BYT
       - log disclosure_log
   ↓
[5] Notify nội bộ: BGĐ, Trưởng khoa, Workshop
       - bulk stand-down (workflow_state asset → "Standby")
   ↓
[6] Bulk-create WO Recall (1 WO / asset)
       - đẩy vào IMM-08 (PM type=Recall) hoặc IMM-09 (Repair) tuỳ action
   ↓
[7] Track completion %  (tự cập nhật khi WO close)
   ↓
[8] Verify all assets resolved → đóng case
   ↓
[9] CAPA preventive (rà soát tiếp nhận, đào tạo, contract)
       → mở CAPA Record, link case
   ↓
[10] Effectiveness check 30/60/90 ngày sau close
   ↓
[11] Management Review entry tự sinh sang IMM-16
```

(Process tham chiếu `../ba/Phase_05_QMS_Governance_Design/05_Recall_FSCA_Workflow/Recall_FSCA_Workflow.md` §3 — đã được Việt hoá cho ngữ cảnh BV.)

---

## III. Use Case

### III.1 — Actor list

- **U1 — Compliance Officer (Tổ HC-QLCL):** primary actor.
- **U2 — Workshop Lead:** thực thi recall action.
- **U3 — Pháp chế:** disclosure regulator.
- **U4 — Trưởng khoa:** xác nhận stand-down tại khoa.
- **U5 — BGĐ:** phê duyệt waive / phê duyệt close.
- **U6 — Vendor (external):** cung cấp lot list, hỗ trợ kỹ thuật.
- **S1 — System scheduler:** nhắc disclosure timer, effectiveness check.
- **S2 — IMM-16 engine:** đẩy compliance finding sang IMM-10 nếu liên quan post-market.

### III.2 — UC table

| UC ID | Tên | Primary actor |
|---|---|---|
| UC-10-01 | Mở Compliance Case từ vendor recall | U1 |
| UC-10-02 | Mở Compliance Case từ FSCA regulator | U1 |
| UC-10-03 | Mở Compliance Case từ tín hiệu PMS nội bộ (chronic failure) | U1 / S2 |
| UC-10-04 | Định danh phạm vi (auto scope) | U1 |
| UC-10-05 | Disclosure tới Bộ Y tế trong 48h | U3 |
| UC-10-06 | Bulk-create Work Order Recall | U1 |
| UC-10-07 | Stand-down asset tại khoa | U4 |
| UC-10-08 | Đóng Compliance Case | U1 + U5 |
| UC-10-09 | Theo dõi CAPA tracker xuyên module | U1 |
| UC-10-10 | Effectiveness check 30/60/90 ngày | S1 + U1 |
| UC-10-11 | Sinh Management Review entry | U1 → IMM-16 |
| UC-10-12 | View Compliance dashboard | U1 / BGĐ / PTP Khối 2 |

### III.3 — UC detail (tiêu biểu)

#### UC-10-04 — Định danh phạm vi

- **Actor:** Compliance Officer
- **Pre-condition:** Compliance Case đã ở state `Scope Identification`; có ít nhất 1 trong (model, lot_range, serial_range, mfg_date_range).
- **Main flow:**
  1. Officer nhập tiêu chí scope.
  2. Service `imm10.find_scope(case)` query `AC Asset` theo tiêu chí + lịch sử điều chuyển từ `Asset Transfer`.
  3. Hệ thống trả danh sách asset → fill `affected_assets` child table.
  4. Officer review — có thể manual add/remove (audit log).
  5. Submit → state chuyển sang `Disclosure Pending` (nếu regulatory) hoặc `Action Pending`.
- **Alt flow (sót lịch sử):** asset đã decommission (IMM-14) — vẫn liệt kê với cờ `historical=true` để báo cáo.
- **Post-condition:** scope đóng băng (immutable sau submit); thay đổi phải mở case con.

*(Các UC còn lại — BA bổ sung trong sprint kế tiếp.)*

---

## IV. Functional / Business Rules

### IV.1 — User stories

- **US-10-01:** Là Compliance Officer, tôi muốn mở Compliance Case từ email vendor để hệ thống ghi vết và tự đếm 48h.
- **US-10-02:** Là Compliance Officer, tôi muốn auto-find affected assets để không phải tra Excel tay.
- **US-10-03:** Là Pháp chế, tôi muốn template công văn disclosure tự fill thông tin case.
- **US-10-04:** Là Workshop Lead, tôi muốn nhận bulk Work Order Recall với danh sách asset rõ ràng.
- **US-10-05:** Là BGĐ, tôi muốn dashboard 1 trang biết: recall đang xử lý, % hoàn thành, CAPA quá hạn.
- **US-10-06:** Là Compliance Officer, tôi muốn được nhắc effectiveness check tự động 30/60/90 ngày sau case close.

### IV.2 — Business Rules

- **BR-10-01:** Compliance Case `severity=Critical` PHẢI có disclosure_required=true và timer 48h tự kích hoạt khi state → `Disclosure Pending`.
- **BR-10-02:** Không submit case nếu `affected_assets` rỗng và `scope_criteria` non-empty (force re-run scope finder).
- **BR-10-03:** Bulk WO chỉ tạo khi case state = `Action Pending` và đã có vendor confirm scope.
- **BR-10-04:** Đóng case yêu cầu: 100% affected assets có WO state = `Closed` HOẶC được đánh dấu `waived` (cần BGĐ approval).
- **BR-10-05:** Disclosure timer breach → escalation tự động: notify BGĐ + create finding sang IMM-16 (compliance NC).
- **BR-10-06:** CAPA preventive bắt buộc cho case `severity ≥ High`; case không đóng được nếu CAPA chưa `In Progress`.
- **BR-10-07:** Effectiveness check 30/60/90 ngày — scheduler tự tạo task; không thực hiện trong 14 ngày → flag quá hạn lên dashboard.
- **BR-10-08:** Mỗi action trên Compliance Case ghi vào `IMM Audit Trail` (hash chain SHA-256).

### IV.3 — Validation Rules

- **VR-10-01:** `disclosure_due_at = recall_confirmed_at + 48h` (UTC, không tính ngày lễ — theo NĐ98).
- **VR-10-02:** `case_no` autoname format `CC-{YYYY}-{####}` *(Naming series cụ thể — Sprint Wave 3.)*
- **VR-10-03:** `severity` enum: `Low`, `Medium`, `High`, `Critical`.
- **VR-10-04:** `case_type` enum: `Recall`, `FSCA`, `PMS Signal`.
- **VR-10-05:** Source phải có ít nhất 1 ref hợp lệ: `vendor_notice_no`, `regulator_doc_no`, hoặc `internal_signal_ref` (link IMM-09/11/12).

---

## V. NFR

| Nhóm | Yêu cầu | Mục tiêu |
|---|---|---|
| Performance | Auto-scope query trên 100k asset | < 5s |
| Performance | Bulk-create 100 WO | < 30s (async job) |
| Reliability | Disclosure timer accuracy | sai số < 1 phút |
| Auditability | Mọi action ghi `IMM Audit Trail`; verify hash chain pass | 100% |
| Security | Compliance Case chỉ Tổ HC-QLCL + BGĐ + PTP Khối 2 đọc; vendor không thấy case khác | Permission gate (refer CONVENTIONS §5) |
| Usability | Officer mở case + run scope < 5 phút | UAT pass |
| Compliance | Disclosure on-time ≥ 95% | KPI monitoring |
| Data retention | Case + audit trail giữ ≥ 5 năm (NĐ98) | Backup policy |

---

*Cập nhật: 2026-05-10. Trạng thái: planning — chờ BE scaffold Sprint Wave 3.*
