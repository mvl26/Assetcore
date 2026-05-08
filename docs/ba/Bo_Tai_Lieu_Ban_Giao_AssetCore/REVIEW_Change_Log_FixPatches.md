> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# ASSETCORE — REVIEW CHANGE LOG & FIX PATCHES
## Review toàn diện bộ tài liệu bàn giao v1.0

**Ngày review:** 2026-05-06  
**Reviewer:** Claude — Solution Architect / Technical Lead  
**Tiêu chí phân tích:**
- **(a)** Naming không nhất quán
- **(b)** Reference đứt gãy giữa các tập
- **(c)** DocType spec chưa đủ để build Frappe
- **(d)** Workflow thiếu state/transition/guard
- **(e)** QMS artifact thiếu hoặc sai tầng

---

## PHẦN 1 — BLOCKING ISSUES
### (Phải fix trước khi IT gõ dòng code đầu tiên)

---

### ISSUE-001 ⛔ BLOCKING
**Tiêu chí:** (d) Workflow Document Record thiếu state "approved" trong DocType spec  
**Tập liên quan:** Tập 3 §3.4.9, Tập 4 §4.1.3  
**Mức độ:** BLOCKING — Frappe Workflow sẽ lỗi khi transition đến state chưa có trong Select options

**Mô tả chi tiết:**  
Tập 4 §4.1.3 định nghĩa workflow Document Record có state trung gian `approved` giữa `in_review` và `effective`:  
`in_review → approved : Approve (QMS Officer)` → `approved → effective : Set effective date reached`

Nhưng Tập 3 Table 26 (field `status` của Document Record) chỉ có:  
`draft / in_review / effective / superseded / retired / expired` — **KHÔNG có "approved"**.

Tập 3 Table 27 (workflow states table) cũng không list `approved`.

Nếu developer implement Frappe Workflow với state "approved" nhưng field `status` không có option này, Frappe sẽ báo lỗi `ValidationError: "approved" is not a valid value for status`.

**Nội dung cũ (Tập 3 Table 26):**
```
status | Status | Select | draft/in_review/effective/superseded/retired/expired
```

**Fix đề xuất (cập nhật Tập 3 Table 26 + Table 27):**
```
status | Status | Select | draft/in_review/approved/effective/superseded/retired/expired
```
Thêm dòng vào Table 27 (Workflow states của Document Record):
```
approved | 0 | QMS Officer (review only; Document Owner không edit)
```

**Lý do:** Đây là inconsistency trực tiếp giữa DocType field spec (Tập 3) và Workflow spec (Tập 4). State "approved" có lý về nghiệp vụ — phân biệt QMS Officer đã duyệt với effective date thực tế (một tài liệu có thể được duyệt trước ngày effective_from).

---

### ISSUE-002 ⛔ BLOCKING
**Tiêu chí:** (b) State `installed_failed` của Medical Asset thiếu trong Tập 1 và Tập 3  
**Tập liên quan:** Tập 1 §1.7.1, Tập 3 Table 7, Tập 4 §4.1.1  
**Mức độ:** BLOCKING — Developer đọc Tập 1 và Tập 3 sẽ không build state này

**Mô tả chi tiết:**  
Tập 4 §4.1.1 (workflow Medical Asset) có transitions rõ ràng:
- `installed → installed_failed : Initial Inspection failed (HM)`
- `installed_failed → installed_pending : Rework (BE, failure cause documented)`

Nhưng:
- Tập 1 §1.7.1 (state machine diagram): **KHÔNG có `installed_failed`**
- Tập 3 Table 7 (workflow states của Medical Asset): **KHÔNG có `installed_failed`**
- Tập 3 §3.4.8 (Initial Inspection hooks): `overall_result=fail giữ installed_failed` — có nhắc tên state nhưng không add vào state table

Developer xây state machine từ Tập 1 + Tập 3 sẽ bỏ sót state này, dẫn đến không có path xử lý khi Initial Inspection fail.

**Nội dung cũ (Tập 1 §1.7.1 state diagram):**
```mermaid
installed --> commissioned
```

**Fix đề xuất:**
1. Cập nhật Tập 1 §1.7.1 state diagram thêm:
```
installed --> installed_failed : Initial Inspection failed
installed_failed --> installed_pending : Rework ordered
```
2. Cập nhật Tập 1 §1.7.2 bảng giải thích states thêm dòng:
```
installed_failed | Kiểm tra ban đầu không đạt; thiết bị chờ rework hoặc trả nhà cung cấp
```
3. Cập nhật Tập 3 Table 7 thêm:
```
installed_failed | 0 | BE (ghi failure cause); HM (quyết định rework/return)
```
4. Cập nhật Tập 3 Table 6 (field `state` Select options) thêm `installed_failed` vào danh sách.

---

### ISSUE-003 ⛔ BLOCKING
**Tiêu chí:** (b)(c) `AC Work Order.state` field reference "(theo 1.4.3)" là sai và gây confusion  
**Tập liên quan:** Tập 3 Table 14  
**Mức độ:** BLOCKING — Developer không biết lấy WO state list từ đâu để implement field

**Mô tả chi tiết:**  
Tập 3 Table 14 (AC Work Order fields):
```
state | State | Select | (theo 1.4.3)
```
Section 1.4.3 là **Process Map IMM-08 (PM)** — không phải WO state definition.  
WO states thực sự được định nghĩa ở:
- Tập 3 Table 15 (workflow states của AC Work Order)
- Tập 4 §4.1.2 (workflow diagram)

Developer đọc reference "(theo 1.4.3)" sẽ không biết đây là section về PM process, không phải state machine. Thậm chí nếu tìm đúng section cũng không thấy danh sách state đầy đủ.

**Nội dung cũ:**
```
state | State | Select | (theo 1.4.3)
```

**Fix đề xuất:**
```
state | State | Select | planned/scheduled/in_progress/paused/completed/closed/overdue/cancelled
```
Xem định nghĩa đầy đủ tại Tập 3 Table 15 và Tập 4 §4.1.2.

---

### ISSUE-004 ⛔ BLOCKING
**Tiêu chí:** (a)(c) DocType "Maintenance Plan" có thể xung đột tên với ERPNext v15  
**Tập liên quan:** Tập 2 §2.4 (DEC-004, DEC-005), Tập 3 §3.4.5, Phụ lục B  
**Mức độ:** BLOCKING — Frappe sẽ không thể install app nếu tên DocType trùng core

**Mô tả chi tiết:**  
ERPNext v15 có DocType **"Maintenance Plan"** trong module Manufacturing (được dùng cho kế hoạch bảo dưỡng thiết bị sản xuất). AssetCore cũng định nghĩa DocType **"Maintenance Plan"** trong module `maintenance_plan/`.

Tập 2 DEC-004/DEC-005 đã nhận diện và giải quyết xung đột với "Work Order" (→ đặt tên "AC Work Order"). Tuy nhiên **KHÔNG có quyết định tương tự cho "Maintenance Plan"**.

Tập 2 Phụ lục B note: *"Manufacturing (BOM, Work Order — trùng tên với WO của AssetCore)"* nhưng bỏ sót "Maintenance Plan".

Khi `bench install-app assetcore` trên site đã có ERPNext Manufacturing enabled, Frappe sẽ báo lỗi DocType name conflict.

**Nội dung cũ:**
```
DocType name | Maintenance Plan
```

**Fix đề xuất — [NEEDS BA DECISION]:**  
Hai lựa chọn:
- **Option A:** Đổi tên thành `AC Maintenance Plan` (nhất quán với "AC Work Order"), cập nhật toàn bộ reference trong Tập 3, Tập 4, Tập 6, Tập 7. Naming rule: `AMP-.YYYY.-.#####`.
- **Option B:** Giữ nguyên "Maintenance Plan" nhưng disable ERPNext Manufacturing module trên site (acceptable nếu bệnh viện không dùng Manufacturing). Cần ghi rõ ràng trong Deployment Runbook.

Khuyến nghị: **Option A** — nhất quán với naming convention đã có, tránh phụ thuộc vào cấu hình module.

---

### ISSUE-005 ⛔ BLOCKING
**Tiêu chí:** (d)(c) Maintenance Plan và Calibration Plan: field `active (Check)` mâu thuẫn với Frappe Workflow states  
**Tập liên quan:** Tập 3 Table 18, Table 20, Tập 4 §4.1.8  
**Mức độ:** BLOCKING — Developer không biết state của plan là workflow state hay checkbox

**Mô tả chi tiết:**  
Tập 3 Table 18 (Maintenance Plan fields): `active | Active | Check`  
Tập 3 Table 20 (Calibration Plan fields): `active | Active | Check`  

Tập 4 §4.1.8 định nghĩa workflow cho cả hai DocType:
```
draft → submitted → active → retired
active → superseded
```

**Xung đột:** Nếu dùng Frappe Workflow, state "active" được lưu trong field `workflow_state` (Frappe tự tạo) chứ không phải trong `active (Check)`. Việc có đồng thời `active (Check)` lẫn workflow state "active" dẫn đến:
- Developer không biết check nào là source of truth
- Scheduler code kiểm tra `if active == 1` sẽ sai nếu đúng ra phải check `workflow_state == "active"`
- Tập 4 §4.4 WO engine check "plan active" không clear dùng cái nào

**Nội dung cũ (Tập 3 Table 18):**
```
active | Active | Check | — | — | Có sinh WO hay không
```

**Fix đề xuất:**  
Bỏ field `active (Check)`. Thay bằng cách kiểm tra `workflow_state == "active"` trong scheduler và hooks.  
Cập nhật Tập 3 Table 18 và Table 20: xóa field `active`.  
Cập nhật Tập 4 §4.9.1 scheduler code: kiểm tra `workflow_state == "active"` thay vì `active == 1`.

Thêm bảng Workflow States vào Tập 3 §3.4.5 và §3.4.6 (tương tự Table 7 của Medical Asset):
```
draft     | 0 | BE (create)
submitted | 1 | HM (review) — Is Submittable=Yes
active    | 1 | — (HM approve bằng transition, không edit)
retired   | 2 | HM
superseded| 2 | Auto khi plan mới supersedes
```

---

### ISSUE-006 ⛔ BLOCKING
**Tiêu chí:** (c) Nhiều DocType thiếu spec đầy đủ nhưng cần thiết cho Wave 1  
**Tập liên quan:** Tập 3 §3.4.18  
**Mức độ:** BLOCKING — Dev không thể build các DocType này đúng cách

**Mô tả chi tiết:**  
Tập 3 §3.4.18 tóm tắt các DocType phụ với ghi chú: *"Dev khi build thực tế cần làm spec đầy đủ giống các DocType chính."*

Điều này có nghĩa là tài liệu bàn giao chuyển gánh nặng spec cho dev — đây là vấn đề trong context handoff.

Các DocType **cần thiết cho Wave 1** nhưng chỉ có spec tóm tắt:

| DocType | Thiếu gì | Impact |
|---|---|---|
| `Maintenance Plan Template` | Toàn bộ field spec, module, naming rule | PM auto-create không hoạt động |
| `Calibration Plan Template` | Toàn bộ field spec | Calibration auto-create không hoạt động |
| `Initial Inspection Template` | Toàn bộ field spec | Initial Inspection không có template |
| `Recall Notice` | Naming rule, Is Submittable, full fields, workflow | IMM-09 recall flow không build được |
| `Root Cause Analysis` | Module, naming rule, Is Submittable, full fields | IMM-12 CAPA flow không hoàn chỉnh |
| `Adverse Event Report` | Naming rule, Is Submittable, full fields, workflow | IMM-12 không hoàn chỉnh |
| `Service Contract` | Naming rule, full fields, workflow, permission | Medical Asset link Service Contract không có spec |
| `Work Order Type` | DocType spec (chỉ có master data values, không có DocType spec) | Link field trên AC Work Order không rõ ràng |

**Fix đề xuất:**  
Bổ sung spec đầy đủ cho từng DocType trên vào Tập 3 §3.4 (dạng sub-section mới sau §3.4.17) hoặc tạo Phụ lục H riêng "DocType Spec bổ sung Wave 1".

Mẫu spec tối thiểu cần có cho mỗi DocType:
```
Metadata: DocType name, module, naming rule, Is Submittable, Track changes
Fields: fieldname, label, fieldtype, options/link, mandatory, mô tả
Workflow states (nếu có): state, doc_status, allow_edit_roles
Permissions: role × action
Hooks: validate, on_submit, on_cancel
```

---

### ISSUE-007 ⛔ BLOCKING
**Tiêu chí:** (b) `Lifecycle Event.event_type` reference "(theo 8.x)" là broken  
**Tập liên quan:** Tập 3 Table 31  
**Mức độ:** BLOCKING — Developer không tìm được danh sách event_type để implement Select field

**Mô tả chi tiết:**  
Tập 3 Table 31 (Lifecycle Event fields):
```
event_type | Event Type | Select | (theo 8.x) | * | Loại event
```
Section "8.x" không tồn tại trong bất kỳ tập nào. Event catalog thực sự nằm ở **Tập 4 §4.3.1 (Table 7)** với 36 event types.

Developer implement Select field cần danh sách options cụ thể. Reference sai sẽ khiến dev không biết field này có bao nhiêu values, dùng format gì.

**Nội dung cũ:**
```
event_type | Event Type | Select | (theo 8.x)
```

**Fix đề xuất:**
```
event_type | Event Type | Select | need_registered/specs_approved/procurement_approved/received/installed_pending/installed/initial_inspection_passed/initial_inspection_failed/commissioned/released_for_use/first_use/pm_due/pm_completed/pm_overdue/calibration_due/calibration_completed/calibration_failed/failure_reported/repaired/recall_received/recall_initiated/adverse_event_reported/compliance_case_opened/capa_opened/capa_closed/document_effective/document_superseded/license_expiring_soon/license_expired/transferred/placed_idle/returned_to_use/retired/disposed/donated/stored_long_term/replacement_signal_emitted/imported_legacy | * | Xem đầy đủ tại Tập 4 §4.3.1
```

---

### ISSUE-008 ⛔ BLOCKING
**Tiêu chí:** (c) `AC Work Order.assigned_team` link to `HR Team` — DocType không chuẩn ERPNext v15  
**Tập liên quan:** Tập 3 Table 14  
**Mức độ:** BLOCKING — Dev không biết "HR Team" là DocType nào, không tìm thấy trong ERPNext v15

**Mô tả chi tiết:**  
Tập 3 Table 14:
```
assigned_team | Assigned Team | Link | → HR Team | — | Đội thực hiện
```
ERPNext v15 không có DocType tên "HR Team" trong core. Có thể tham chiếu đến:
- Module Projects → Team (nếu có Frappe Desk Pro)
- Custom DocType "HR Team" (nhưng không có spec nào trong tài liệu)

Không có quyết định nào trong Decision Log (DEC-001..020) giải quyết điểm này.

**Fix đề xuất — [NEEDS BA DECISION]:**  
Hai lựa chọn:
- **Option A:** Đổi thành `Link → Employee Group` (ERPNext v15 có sẵn DocType này trong HR module, dùng để nhóm nhân viên theo bộ phận/nhóm kỹ năng). Phù hợp hơn cho context bệnh viện.
- **Option B:** Tạo custom DocType `AC Service Team` với fields: team_code, team_name, members (child table → User), department, specialty. Cần spec đầy đủ.

Khuyến nghị: **Option A** nếu Employee Group đủ đáp ứng; **Option B** nếu cần track team HTM riêng biệt theo chuyên môn thiết bị.

---

## PHẦN 2 — HIGH ISSUES
### (Phải fix trước UAT)

---

### ISSUE-009 🔴 HIGH
**Tiêu chí:** (a)(c) `qms_tier` trùng lặp giữa Document Record và QMS Artifact  
**Tập liên quan:** Tập 3 Table 26 (Document Record), Table 29 (QMS Artifact), Tập 2 DEC-006

**Mô tả:**  
Document Record có field `qms_tier (Select)` và `is_qms_artifact (Check)`.  
QMS Artifact (1-1 với Document Record) cũng có field `qms_tier (Select)`.  
DEC-006 quyết định tách 2 DocType nhưng không giải quyết redundancy này.

**Vấn đề:** Nếu `Document Record.qms_tier = 'PR-SOP'` nhưng `QMS Artifact.qms_tier = 'WI-JD'` → source of truth nào đúng?  
Tập 4 §4.5.5 audit chỉ nhắc đến "QMS Artifact" nhưng `qms_tier` cũng có ở Document Record.

**Fix đề xuất:**  
Xóa field `qms_tier` khỏi Document Record. Giữ `is_qms_artifact (Check)` trên Document Record chỉ để đánh dấu. Tier thực sự chỉ lưu trên QMS Artifact.  
Cập nhật Tập 3 Table 26: bỏ dòng `qms_tier`.  
Cập nhật hooks: khi `is_qms_artifact = 1`, enforce QMS Artifact phải tồn tại với qms_tier đầy đủ.

---

### ISSUE-010 🔴 HIGH
**Tiêu chí:** (d) Initial Inspection workflow states và guard conditions thiếu trong Tập 3  
**Tập liên quan:** Tập 3 §3.4.8, Tập 4 §4.1.6, Tập 1 §1.4.1

**Mô tả:**  
Tập 4 §4.1.6 định nghĩa workflow Initial Inspection: `draft → submitted → approved → rejected → draft`.  
Tập 3 §3.4.8 (DocType spec Initial Inspection) **không có bảng workflow states** (thiếu bảng tương đương Table 7 hay Table 15 như các DocType khác).

Thêm vào đó, Tập 1 §1.4.1 dùng "pass/fail/conditional" là kết quả inspection, trong khi Tập 4 dùng "approved/rejected" là workflow state — hai hệ khái niệm không được mapping rõ ràng:
- `approved` = "HM ký duyệt" = kết quả inspection **pass**
- `rejected` = "HM từ chối" = kết quả inspection **fail**

**Fix đề xuất:**  
Bổ sung vào Tập 3 §3.4.8 bảng workflow states:
```
State    | Doc Status | Allow Edit Roles         | Guard
draft    | 0          | Biomed Engineer          | —
submitted| 0→1        | —                        | ≥1 evidence; all items completed
approved | 1          | —                        | overall_result filled; approved_by signed
rejected | 0          | Biomed Engineer (rework) | approval_date + rejection reason
```
Bổ sung guard condition cho transition `submitted → approved`:
- `overall_result` phải là `pass` hoặc `conditional`
- `approved_by` không được rỗng
- `evidence` ≥ 1 file

Bổ sung mapping rõ ràng: `approved` ↔ `overall_result=pass`, `rejected` ↔ `overall_result=fail`.

---

### ISSUE-011 🔴 HIGH
**Tiêu chí:** (c) `Calibration Plan.sop_reference` mandatory nhưng gây blocking cho migration  
**Tập liên quan:** Tập 3 Table 20  
**Cờ:** [NEEDS BA DECISION]

**Mô tả:**  
`sop_reference | SOP Reference | Link | → QMS Artifact | *` — mandatory (*)  

Scenario migration: legacy Calibration Plan được import cho thiết bị đang vận hành, nhưng QMS Artifact (SOP calibration) chưa được số hóa/upload vào hệ thống. Validation sẽ chặn import.

**Fix đề xuất — [NEEDS BA DECISION]:**  
- **Option A (Strict):** Giữ mandatory. Bắt buộc tạo QMS Artifact SOP placeholder trước khi import Calibration Plan. Phù hợp với QMS discipline nhưng làm phức tạp migration.
- **Option B (Lenient):** Bỏ mandatory cho trường này. Thêm DQ rule soft warning: `DQ-SOFT-CAL-001: Calibration Plan không có SOP Reference`. Mục tiêu: 100% có SOP Reference trong vòng 90 ngày sau go-live.
- **Option C:** Mandatory chỉ khi `workflow_state = "active"` (không check khi draft/submitted). Implement bằng validate hook.

---

### ISSUE-012 🔴 HIGH
**Tiêu chí:** (b)(d) Medical Asset initial state sau auto-create từ Purchase Receipt không nhất quán  
**Tập liên quan:** Tập 1 §1.4.1, Tập 3 §3.3.2, Tập 4 Table 2

**Mô tả:**  
Ba nguồn nói khác nhau về initial state của Medical Asset khi auto-create:

- Tập 1 §1.4.1 process map: `PR submit → auto-create Medical Asset (state=installed_pending)` — **initial state = installed_pending**
- Tập 4 Table 2: `received → installed_pending : Open installation WO (BE)` — ngụ ý **initial state = received**
- Tập 3 §3.3.2 flowchart: `Purchase Receipt → hook auto-create → Medical Asset` — **không nêu initial state**

Mâu thuẫn: Tập 1 skip state `received`, Tập 4 có state `received` là bước trung gian.

**Fix đề xuất:**  
Chốt rõ: Medical Asset được auto-create với initial state = **`received`** (nhận hàng vật lý xác nhận qua PR). Transition `received → installed_pending` diễn ra khi BE mở Installation WO.

Cập nhật Tập 1 §1.4.1 process map:
```
PR submit → auto-create Medical Asset (state=received)
BE mở Installation WO → state=installed_pending
```
Cập nhật Tập 3 §3.3.2 flowchart: ghi rõ initial state.

---

### ISSUE-013 🔴 HIGH
**Tiêu chí:** (c) `AC Work Order.wo_type` Naming Rule có `{wo_type_short}` nhưng không có mapping  
**Tập liên quan:** Tập 3 Table 13

**Mô tả:**  
Naming rule: `WO-{wo_type_short}-.YYYY.-.#####`  
Frappe naming series không hiểu `{wo_type_short}` tự động — cần Python `autoname` function hoặc custom naming_series per wo_type. Không có bảng mapping nào định nghĩa:
```
PM           → WO-PM-2026-00001
CM           → WO-CM-2026-00001
INSPECTION   → WO-INS-2026-00001  (hay WO-INSP-?)
CALIBRATION  → WO-CAL-2026-00001
RECALL       → WO-RCL-2026-00001
RETIREMENT   → WO-RET-2026-00001
INSTALLATION → WO-INST-2026-00001 (hay WO-INS-? — trùng INSPECTION?)
```

**Fix đề xuất:**  
Thêm bảng mapping vào Tập 3 §3.5.5 (Work Order Type):

| wo_type | wo_type_short | Naming Series | Ví dụ |
|---|---|---|---|
| PM | PM | WO-PM-.YYYY.-.##### | WO-PM-2026-00001 |
| CM | CM | WO-CM-.YYYY.-.##### | WO-CM-2026-00001 |
| INSPECTION | INSP | WO-INSP-.YYYY.-.##### | WO-INSP-2026-00001 |
| CALIBRATION | CAL | WO-CAL-.YYYY.-.##### | WO-CAL-2026-00001 |
| RECALL | RCL | WO-RCL-.YYYY.-.##### | WO-RCL-2026-00001 |
| RETIREMENT | RET | WO-RET-.YYYY.-.##### | WO-RET-2026-00001 |
| INSTALLATION | INST | WO-INST-.YYYY.-.##### | WO-INST-2026-00001 |

Thêm Python autoname logic vào Tập 10 (Developer Handoff):
```python
def autoname(self):
    short = {"PM":"PM","CM":"CM","INSPECTION":"INSP","CALIBRATION":"CAL",
             "RECALL":"RCL","RETIREMENT":"RET","INSTALLATION":"INST"}
    prefix = short.get(self.wo_type, "WO")
    self.name = frappe.model.naming.make_autoname(f"WO-{prefix}-.YYYY.-.#####")
```

---

### ISSUE-014 🔴 HIGH
**Tiêu chí:** (a) "AssetCore Doctor" role không nhất quán trong permission matrix  
**Tập liên quan:** Tập 4 Table 4, Table 5, Tập 3 Table 8

**Mô tả:**  
Tập 4 Table 4 định nghĩa role "AssetCore Doctor" với description "Bác sĩ; báo cáo adverse event; xem read-only".  
Tập 4 Table 5 (permission matrix) dùng header "Doc" cho cột này — không đủ rõ ràng.  
Tập 3 Table 8 (Medical Asset permission): **không có dòng nào cho "AssetCore Doctor"**.

Hệ quả: Dev build Medical Asset permission từ Tập 3 sẽ không có Doctor trong permission matrix, dù Tập 4 nói Doctor có quyền read Medical Asset thuộc khoa của mình.

**Fix đề xuất:**  
1. Cập nhật Tập 4 Table 5 header: thêm "Doc = AssetCore Doctor" vào chú thích.
2. Cập nhật Tập 3 Table 8 (Medical Asset permissions) thêm dòng:
```
AssetCore Doctor | R | — | — | — | — | — | Asset thuộc khoa của mình (ABAC)
```
3. Cập nhật Tập 3 §3.4.8 (Initial Inspection permissions): Doctor cũng có thể cần read Initial Inspection của asset khoa mình.

---

### ISSUE-015 🔴 HIGH
**Tiêu chí:** (d) `Failure Report` có 4 states nhưng sử dụng plain Select thay vì Frappe Workflow  
**Tập liên quan:** Tập 3 Table 22, Tập 4 §4.1.7, Tập 2 DEC-011

**Mô tả:**  
DEC-011: *"Dùng Frappe Workflow thay vì state field thủ công cho mọi DocType có lifecycle ≥ 4 trạng thái"*  
Failure Report có 4 states: `open / in_triage / wo_created / closed` → phải dùng Frappe Workflow theo DEC-011.  
Nhưng Tập 3 Table 22 implement là `status | Select` plain field — vi phạm DEC-011.

**Fix đề xuất:**  
1. Đổi `status (Select)` thành workflow-controlled state.
2. Thêm bảng workflow states vào Tập 3 §3.4.7:
```
State       | Doc Status | Allow Edit Roles     | Guard
open        | 0          | Any (auto-create)    | medical_asset, severity, description filled
in_triage   | 0          | Biomed Engineer      | —
wo_created  | 0→1        | Biomed Engineer (submit) | resulting_wo không rỗng
closed      | 1          | HTM Manager          | CM WO state=closed; reason_code filled
```

---

### ISSUE-016 🔴 HIGH
**Tiêu chí:** (c) `Medical Asset.state` field không có danh sách đầy đủ states cho dev implement  
**Tập liên quan:** Tập 3 Table 6

**Mô tả:**  
```
state | Lifecycle State | Select | (theo 1.7.2) | *
```
Reference "(theo 1.7.2)" chỉ đến bảng giải thích state trong Tập 1 §1.7.2, nhưng bảng đó không liệt kê state list dạng code.

Developer implement Frappe DocType cần danh sách options chính xác trong field definition, không thể để reference mở như vậy. Đặc biệt quan trọng vì `installed_failed` bị thiếu (ISSUE-002).

**Fix đề xuất:**  
Cập nhật Tập 3 Table 6:
```
state | Lifecycle State | Select | need_registered/specs_approved/procurement_approved/received/installed_pending/installed/installed_failed/commissioned/released_for_use/in_use/in_repair/out_of_service/idle/transferred/retired/disposed/donated/stored_long_term | *
```

---

### ISSUE-017 🔴 HIGH
**Tiêu chí:** (c) Module folder "corrective" của Failure Report không có trong app structure  
**Tập liên quan:** Tập 3 §3.4.7, Tập 2 §2.3.1

**Mô tả:**  
Tập 3 §3.4.7: `module | corrective` cho Failure Report.  
Tập 2 §2.3.1 app folder structure không có sub-folder `corrective/`:
```
assetcore/
├── asset_registry/
├── lifecycle/
├── work_order/
├── maintenance_plan/
├── calibration/
├── document_qms/
├── compliance/
├── capa/
├── audit/
├── metric/
```
`corrective/` **không có trong danh sách**. Developer sẽ không biết đặt Failure Report vào đâu.

**Fix đề xuất:**  
Hai lựa chọn:
- **Option A:** Đổi module của Failure Report thành `work_order` (cùng nhóm với AC Work Order, vì FR triggers CM WO). Cập nhật Tập 3 §3.4.7.
- **Option B:** Thêm `corrective/` vào app structure trong Tập 2 §2.3.1 và định nghĩa rõ scope của sub-module này (Failure Report, Adverse Event Report, Software Update Record).

---

## PHẦN 3 — MEDIUM ISSUES
### (Phải fix trước go-live)

---

### ISSUE-018 🟡 MEDIUM
**Tiêu chí:** (b) Decision Log có nguy cơ drift giữa Tập 2 §2.4 và Phụ lục D

**Mô tả:**  
Phụ lục D.1 nói "không lặp lại quyết định DEC-001..020 ở Tập 2". Nhưng khi có thay đổi DEC, không có cơ chế bắt buộc cập nhật đồng bộ giữa Tập 2 và Phụ lục D. Phụ lục D.2 (decisions cấp dự án bổ sung) cũng có thể không được update trong Tập 2.

**Fix đề xuất:**  
Cập nhật Tập 0 §0.5.3 và §0.8.2: thêm rule "Khi thêm hoặc sửa DEC, phải cập nhật CẢ Tập 2 §2.4 VÀ Phụ lục D trong cùng PR". Phụ lục D chỉ là index, không phải nguồn sự thật — nguồn sự thật là Tập 2.

---

### ISSUE-019 🟡 MEDIUM
**Tiêu chí:** (c) `Compliance Record` scheduler dùng `frappe.db.set_value()` → bypass hooks → không sinh audit  
**Tập liên quan:** Tập 3 §3.4.12, Tập 4 §4.9.1

**Mô tả:**  
`compliance_status_updater` job dùng `frappe.db.set_value()` để cập nhật status Compliance Record. `frappe.db.set_value()` bypass tất cả hooks (validate, on_update) → không sinh Asset Audit Log entry cho thay đổi status compliance.

Đây là vi phạm nguyên tắc audit trail (Tập 0 §0.1.7 tiêu chí 7: "Audit trail bao phủ 100% hành động").

**Fix đề xuất:**  
Cập nhật Tập 4 §4.9.1 compliance_status_updater:  
Thay vì `frappe.db.set_value()`, dùng:
```python
doc = frappe.get_doc("Compliance Record", name)
old_status = doc.status
doc.status = new_status
doc.save(ignore_permissions=True)
# Trigger audit manually:
insert_audit_entry({...before: old_status, after: new_status, actor: "scheduler"})
```

---

### ISSUE-020 🟡 MEDIUM
**Tiêu chí:** (d) CAPA Case state "reopened" sau docstatus=1 cần hướng dẫn Frappe cụ thể  
**Tập liên quan:** Tập 3 Table 36, Tập 4 §4.1.4

**Mô tả:**  
CAPA Case Is Submittable=Yes. State "closed" → docstatus=1 (Submitted). Tập 4 §4.1.4 có transition `awaiting_eff_check → reopened` (khi Effectiveness Check fail).

Trong Frappe, một document đã docstatus=1 muốn chuyển sang state mới thì phải Amend (tạo bản sửa đổi với docstatus=0). Nhưng tài liệu không giải thích cơ chế này.

**Fix đề xuất:**  
Cập nhật Tập 4 §4.6.3 (CAPA engine): Bổ sung hướng dẫn:
*"Khi Effectiveness Check fail và cần reopen CAPA: dùng Frappe Amend để tạo CAPA Case mới (suffix -1, -2...) với liên kết đến CAPA Case gốc. KHÔNG dùng Frappe Workflow transition từ closed về reopened trực tiếp vì docstatus=1 là immutable trong Frappe chuẩn."*

Thêm field vào CAPA Case: `amended_from | Link | → CAPA Case` (auto-set bởi Frappe Amend mechanism).

---

### ISSUE-021 🟡 MEDIUM
**Tiêu chí:** (e) QMS Artifact Matrix Tập 1 §1.8 thiếu mapping cụ thể đến artifact codes  
**Tập liên quan:** Tập 1 §1.8.2

**Mô tả:**  
Tập 1 §1.8.2 "Ma trận QMS × Module" chỉ mô tả nguyên tắc, không cung cấp bảng mapping cụ thể với document codes. Dev và QMS Officer không có danh sách tài liệu QMS cần tạo cho Wave 1.

**Fix đề xuất:**  
Bổ sung bảng mapping cụ thể vào Tập 1 §1.8.2 (hoặc Phụ lục QMS):

| Module | Tầng 1 (QC) | Tầng 2 (PR/SOP) | Tầng 3 (WI/JD) | Tầng 4 (BM/HS) |
|---|---|---|---|---|
| IMM-04 | QC-HTM-001 (Chính sách quản lý TTBYT) | SOP-INST-001 (Lắp đặt thiết bị) | WI-INST-001 (Quy trình gắn QR) | BM-INSPECT-001 (Biểu mẫu Initial Inspection) |
| IMM-05 | QC-HTM-001 | SOP-DOC-001 (Kiểm soát hồ sơ pháp lý) | WI-LIC-001 (Hướng dẫn upload giấy phép) | BM-COMP-001 (Compliance checklist) |
| IMM-08 | QC-HTM-001 | SOP-PM-001 (Quy trình PM tổng quát) | WI-PM-{device_type} (theo từng loại thiết bị) | BM-PM-001 (PM report form) |
| IMM-09 | QC-HTM-001 | SOP-CM-001 (Quy trình CM / Failure Report) | WI-CM-001 (Hướng dẫn chẩn đoán hỏng hóc) | BM-FR-001 (Failure Report form), BM-CM-001 (CM report) |
| IMM-11 | QC-HTM-001 | SOP-CAL-001 (Quy trình hiệu chuẩn) | WI-CAL-{device_type} | BM-CAL-001 (Calibration record) |
| IMM-12 | QC-HTM-001 | SOP-CAPA-001 (Quy trình CAPA) | WI-RCA-001 (Hướng dẫn 5 Whys/Fishbone) | BM-CAPA-001 (CAPA form), BM-EFF-001 (Effectiveness Check form) |

---

### ISSUE-022 🟡 MEDIUM
**Tiêu chí:** (c) `Document Record.files` mandatory (`*`) gây vấn đề cho migration legacy records  
**Tập liên quan:** Tập 3 Table 26  
**Cờ:** [NEEDS BA DECISION]

**Mô tả:**  
`files | Files | Table | → Document File | *` — mandatory child table.  
Scenario: khi import legacy Document Record (hợp đồng cũ đã hết hạn, SOP cũ đã superseded), file vật lý có thể chưa scan. Validation sẽ chặn import.

**Fix đề xuất — [NEEDS BA DECISION]:**  
- **Option A:** Giữ mandatory. Mọi Document Record phải có ≥1 file đính kèm kể cả khi import.
- **Option B:** Bỏ mandatory. Thêm DQ rule: `DQ-SOFT-DOC-001: Document Record status=effective/superseded không có file đính kèm`. Warning, không block.
- **Option C:** Mandatory chỉ khi `status = effective`. Enforce bằng `before_submit` hook, không phải field mandatory.

---

### ISSUE-023 🟡 MEDIUM
**Tiêu chí:** (a) Calibration type "kiểm định phương tiện đo" chưa có value riêng  
**Tập liên quan:** Tập 3 Table 20, Tập 1 §1.4.5

**Mô tả:**  
Tập 3 Table 20: `calibration_type | Select | internal/external/regulatory/safety`  
Tập 1 §1.4.5 nhắc đến "kiểm định an toàn bức xạ" (→ `safety`) và "kiểm định phương tiện đo" (→ chưa có value riêng, hiện phải dùng `regulatory`).

Pháp lý Việt Nam phân biệt rõ hai loại: kiểm định an toàn bức xạ (Bộ KHCN) vs kiểm định phương tiện đo (Tổng cục TCĐLCL). Report và compliance tracking cần phân biệt.

**Fix đề xuất:**  
Cập nhật Tập 3 Table 20:
```
calibration_type | Select | internal/external/regulatory/safety_radiation/metrology
```
Giải thích:
- `safety_radiation`: Kiểm định an toàn bức xạ (theo Luật Năng lượng nguyên tử)
- `metrology`: Kiểm định phương tiện đo (theo Luật Đo lường)
- `regulatory`: Loại khác theo yêu cầu cơ quan quản lý

---

## PHẦN 4 — LOW ISSUES
### (Fix theo lịch thông thường)

---

### ISSUE-024 🟢 LOW
**Tiêu chí:** (a) "HC" dùng trong SLA matrix không được định nghĩa trong Glossary  
**Tập liên quan:** Tập 4 Table 9, Tập 0 §0.2

**Mô tả:**  
Tập 4 Table 9: `1h (HC) / 2h (out HC)` — "HC" = Hành Chính (giờ hành chính) nhưng không có trong Glossary Tập 0.  
Trong bối cảnh bệnh viện, "HC" có thể hiểu nhầm là "Hospital Core" hoặc thuật ngữ khác.

**Fix đề xuất:**  
Thêm vào Tập 0 §0.2.3 (Thuật ngữ ERPNext/Frappe):
```
HC | Hành Chính (giờ) | Giờ hành chính: 08:00–17:00, thứ Hai–Thứ Sáu theo lịch bệnh viện.
out HC | Ngoài giờ hành chính | Bao gồm buổi tối, cuối tuần, ngày lễ.
```
Cập nhật Tập 4 Table 9: dùng "giờ HC" thay vì "HC" cho rõ ràng.

---

### ISSUE-025 🟢 LOW
**Tiêu chí:** (b) Phụ lục D.2 "Decisions cấp dự án bổ sung" để trống không có nội dung  
**Tập liên quan:** Phụ lục D §D.2

**Mô tả:**  
Phụ lục D.2 tồn tại như section nhưng không có nội dung decision nào. Trong khi đó có nhiều quyết định cấp dự án quan trọng chưa được ghi (ví dụ: ISSUE-004, ISSUE-008 cần quyết định).

**Fix đề xuất:**  
Sau khi BA/SA giải quyết các [NEEDS BA DECISION] issues, ghi kết quả vào Phụ lục D.2 với format chuẩn DEC.  
Tối thiểu cần thêm:
- PD-001: Quyết định về naming "Maintenance Plan" vs "AC Maintenance Plan" (từ ISSUE-004)
- PD-002: Quyết định về "HR Team" vs "Employee Group" vs "AC Service Team" (từ ISSUE-008)
- PD-003: Quyết định về sop_reference mandatory trong Calibration Plan (từ ISSUE-011)

---

### ISSUE-026 🟢 LOW
**Tiêu chí:** (b) Phụ lục E "Open Questions Register" trống trong Final Draft  
**Tập liên quan:** Phụ lục E

**Mô tả:**  
Phụ lục E.1 (Open Questions) trống hoàn toàn trong v1.0 Final Draft. Với 8 BLOCKING issues và nhiều [NEEDS BA DECISION] points, việc Open Questions trống là dấu hiệu các câu hỏi này chưa được raise chính thức.

**Fix đề xuất:**  
Populate Phụ lục E.1 với tối thiểu:
```
Q-001 | Maintenance Plan có cần tiền tố "AC " không? | BA + SA | 2026-05-10 | Mở
Q-002 | HR Team là DocType nào trong ERPNext v15? | Tech Lead | 2026-05-10 | Mở  
Q-003 | sop_reference trong Calibration Plan có mandatory không? | BA + QMS | 2026-05-10 | Mở
Q-004 | Document Record.files có mandatory không cho migration? | BA + PO | 2026-05-10 | Mở
Q-005 | CAPA reopen: Amend hay custom state? | Tech Lead + SA | 2026-05-10 | Mở
```

---

## PHẦN 5 — CHANGE LOG TỔNG HỢP

| # | Tập | Section | Tiêu chí | Vấn đề | Nội dung cũ (tóm tắt) | Fix / Nội dung mới (tóm tắt) | Mức độ | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| 001 | T3, T4 | T3 Table 26, 27; T4 §4.1.3 | (d) | Document Record thiếu state "approved" | `status Select: draft/in_review/effective/…` (không có approved) | Thêm `approved` vào Select options + Workflow state table | ⛔ BLOCKING | OPEN |
| 002 | T1, T3, T4 | T1 §1.7.1; T3 Table 7; T4 §4.1.1 | (b) | `installed_failed` thiếu trong T1 và T3 | State diagram T1 không có; T3 Table 7 không có | Thêm vào T1 §1.7.1 diagram, §1.7.2 bảng; T3 Table 7, Table 6 field options | ⛔ BLOCKING | OPEN |
| 003 | T3 | Table 14 (AC Work Order field state) | (b)(c) | Reference "(theo 1.4.3)" sai | `state \| Select \| (theo 1.4.3)` | `state \| Select \| planned/scheduled/in_progress/…` (liệt kê đầy đủ) | ⛔ BLOCKING | OPEN |
| 004 | T2, T3 | T2 DEC log; T3 §3.4.5 | (a)(c) | "Maintenance Plan" có thể trùng tên ERPNext core | `DocType name: Maintenance Plan` | [NEEDS BA DECISION]: đổi thành "AC Maintenance Plan" hoặc disable Manufacturing | ⛔ BLOCKING | NEEDS BA DECISION |
| 005 | T3, T4 | T3 Table 18, 20; T4 §4.1.8 | (d)(c) | field `active (Check)` mâu thuẫn với workflow state "active" | `active \| Active \| Check` + workflow states `draft/submitted/active/retired` | Bỏ field `active (Check)`; dùng `workflow_state == "active"` trong scheduler | ⛔ BLOCKING | OPEN |
| 006 | T3 | §3.4.18 | (c) | 8 DocType Wave 1 chỉ có spec tóm tắt | "Dev cần làm spec đầy đủ" | Bổ sung spec đầy đủ: MPTemplate, CPTemplate, IITemplate, Recall Notice, RCA, AER, Service Contract, Work Order Type | ⛔ BLOCKING | OPEN |
| 007 | T3 | Table 31 (Lifecycle Event fields) | (b) | event_type reference "(theo 8.x)" broken | `event_type \| Select \| (theo 8.x)` | Liệt kê 36 event types đầy đủ; reference Tập 4 §4.3.1 | ⛔ BLOCKING | OPEN |
| 008 | T3 | Table 14 (AC Work Order) | (c) | `assigned_team` link → "HR Team" không tồn tại ERPNext v15 | `Link \| → HR Team` | [NEEDS BA DECISION]: đổi → Employee Group hoặc tạo AC Service Team | ⛔ BLOCKING | NEEDS BA DECISION |
| 009 | T3 | Table 26 (Doc Record), Table 29 (QMS Artifact) | (a)(c) | `qms_tier` trùng lặp ở cả 2 DocType | Cả hai đều có `qms_tier` field | Xóa `qms_tier` khỏi Document Record; giữ ở QMS Artifact | 🔴 HIGH | OPEN |
| 010 | T3, T4, T1 | T3 §3.4.8; T4 §4.1.6; T1 §1.4.1 | (d) | Initial Inspection thiếu workflow table và guard conditions | Không có workflow state table trong T3 | Bổ sung bảng states + guard conditions; mapping pass/fail ↔ approved/rejected | 🔴 HIGH | OPEN |
| 011 | T3 | Table 20 (Calibration Plan) | (c) | `sop_reference` mandatory blocking migration | `sop_reference \| * (mandatory)` | [NEEDS BA DECISION]: giữ mandatory / relax / validate tại submit | 🔴 HIGH | NEEDS BA DECISION |
| 012 | T1, T3, T4 | T1 §1.4.1; T3 §3.3.2; T4 Table 2 | (b)(d) | Initial state Medical Asset không nhất quán | T1 nói "installed_pending", T4 có state "received" trung gian | Chốt initial state = `received`; cập nhật T1 process map và T3 flowchart | 🔴 HIGH | OPEN |
| 013 | T3 | Table 13 (AC Work Order naming) | (c) | `{wo_type_short}` không có mapping | `WO-{wo_type_short}-.YYYY.-.#####` | Thêm bảng mapping wo_type → short code + Python autoname function | 🔴 HIGH | OPEN |
| 014 | T3, T4 | T3 Table 8; T4 Table 4, 5 | (a) | "AssetCore Doctor" thiếu trong Medical Asset permission | Không có dòng Doctor trong T3 Table 8 | Thêm "AssetCore Doctor" vào T3 Table 8; cập nhật T4 Table 5 header | 🔴 HIGH | OPEN |
| 015 | T3, T4, T2 | T3 Table 22; T4 §4.1.7; T2 DEC-011 | (d) | Failure Report dùng plain Select vi phạm DEC-011 | `status \| Select` plain field | Chuyển sang Frappe Workflow; bổ sung workflow state table | 🔴 HIGH | OPEN |
| 016 | T3 | Table 6 (Medical Asset fields) | (c) | `state` field không có danh sách đầy đủ | `state \| Select \| (theo 1.7.2)` | Liệt kê đầy đủ 18 states trong field definition | 🔴 HIGH | OPEN |
| 017 | T2, T3 | T2 §2.3.1; T3 §3.4.7 | (c) | Module "corrective" không có trong app folder structure | `module: corrective` (không có trong T2 folders) | Đổi thành `work_order` hoặc thêm `corrective/` vào T2 §2.3.1 | 🔴 HIGH | OPEN |
| 018 | T2, PL | T2 §2.4; Phụ lục D | (b) | Decision Log có nguy cơ drift giữa T2 và Phụ lục D | Không có cơ chế sync | Thêm rule vào T0 §0.5.3: cập nhật cả 2 nơi trong cùng PR | 🟡 MEDIUM | OPEN |
| 019 | T3, T4 | T3 §3.4.12; T4 §4.9.1 | (c) | Compliance status update dùng db.set_value() bypass hooks | `frappe.db.set_value()` trong scheduler | Dùng `doc.save()` + manual audit insert | 🟡 MEDIUM | OPEN |
| 020 | T3, T4 | T3 Table 36; T4 §4.1.4 | (d) | CAPA "reopened" sau closed=docstatus=1 chưa có hướng dẫn Frappe | Workflow có transition closed→reopened nhưng không giải thích cơ chế | Dùng Amend mechanism; thêm field `amended_from` | 🟡 MEDIUM | OPEN |
| 021 | T1 | §1.8.2 | (e) | QMS Artifact Matrix thiếu mapping cụ thể đến document codes | Ma trận chỉ có nguyên tắc | Bổ sung bảng mapping module × tầng × document code cụ thể | 🟡 MEDIUM | OPEN |
| 022 | T3 | Table 26 (Doc Record `files`) | (c) | `files` mandatory blocking migration | `files \| * (mandatory)` | [NEEDS BA DECISION]: mandatory / soft warning / mandatory tại submit | 🟡 MEDIUM | NEEDS BA DECISION |
| 023 | T3, T1 | T3 Table 20; T1 §1.4.5 | (a) | "Kiểm định phương tiện đo" chưa có value riêng trong calibration_type | `internal/external/regulatory/safety` | Thêm `metrology` và `safety_radiation` | 🟡 MEDIUM | OPEN |
| 024 | T4 | Table 9 | (a) | "HC" không có trong Glossary | `1h (HC) / 2h (out HC)` | Thêm định nghĩa HC vào T0 §0.2; dùng "giờ HC" cho rõ ràng | 🟢 LOW | OPEN |
| 025 | PL | Phụ lục D §D.2 | (b) | Decisions bổ sung trống | Section D.2 không có nội dung | Thêm PD-001..PD-003 sau khi BA quyết định | 🟢 LOW | OPEN |
| 026 | PL | Phụ lục E | (b) | Open Questions Register trống trong Final Draft | E.1 trống | Populate với Q-001..Q-005 tối thiểu | 🟢 LOW | OPEN |

---

## PHẦN 6 — TÓM TẮT ĐIỀU HÀNH

### Thống kê issues

| Mức độ | Số lượng | Phải xong trước |
|---|---|---|
| ⛔ BLOCKING | 8 | IT bắt đầu build bất kỳ DocType nào |
| 🔴 HIGH | 9 | UAT signoff |
| 🟡 MEDIUM | 5 | Go-live production |
| 🟢 LOW | 3 | Sprint 2 trở đi |
| **Tổng** | **25** | — |

### Issues cần BA/BA quyết định trước khi sửa

| Issue | Quyết định cần | Deadline đề xuất |
|---|---|---|
| ISSUE-004 | "Maintenance Plan" hay "AC Maintenance Plan"? | Sprint planning ngày đầu |
| ISSUE-008 | `assigned_team`: Employee Group hay custom AC Service Team? | Sprint planning ngày đầu |
| ISSUE-011 | `sop_reference` trong Calibration Plan: mandatory hay optional? | Sprint 1 day 3 |
| ISSUE-022 | `Document Record.files`: mandatory hay soft-validate? | Sprint 1 day 3 |

### Lộ trình fix đề xuất

**Tuần 1 (trước Sprint 1):**
1. Họp BA + SA + Tech Lead: resolve 4 [NEEDS BA DECISION] (1 ngày)
2. Cập nhật Tập 3 Table 6, 14, 26, 27 (ISSUE-001, 002, 003, 007, 016) — SA/Tech Lead (2 ngày)
3. Cập nhật Tập 4 §4.1.8 về Maintenance/Calibration Plan workflow (ISSUE-005) — SA (1 ngày)
4. Viết spec đầy đủ cho 8 DocType thiếu (ISSUE-006) — Tech Lead + BA (2 ngày)

**Sprint 1 song song với build:**
5. Fix ISSUE-009, 010, 012, 013, 014, 015, 017 (HIGH issues)

**Trước UAT:**
6. Fix tất cả MEDIUM và LOW issues

### Điểm mạnh của bộ tài liệu

Dù có các issues trên, bộ tài liệu v1.0 đạt chất lượng **cao hơn mức bình thường** cho giai đoạn này:
- Kiến trúc logic đúng đắn, tuân thủ WHO IMMIS, DEC-001..020 rõ ràng và có lý
- ERD đầy đủ theo module Wave 1, mapping ERPNext ↔ AssetCore chuẩn
- Lifecycle Event Engine và Audit chain well-designed
- Permission RBAC + ABAC đúng hướng
- Metric/Dashboard engine có lineage design tốt
- DoR/DoD chuẩn, QMS artifact framework đủ tầng

Các BLOCKING issues chủ yếu là **thiếu nhất quán giữa các tập** chứ không phải lỗi thiết kế nghiệp vụ. Fix là cập nhật chéo, không phải thiết kế lại.

---

*Change Log này là tài liệu sống. Khi issue được fix, cập nhật cột "Trạng thái" thành FIXED + version tài liệu và ngày fix. Không xóa issue đã fix khỏi log — giữ để audit trail.*

*Phiên bản Change Log: 1.0 — 2026-05-06*
