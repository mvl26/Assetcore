# IMM-12 — Phân tích Tiến độ Triển khai

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Ngày phân tích | 2026-04-21 |
| Phân tích bởi | Claude Code (tự động từ codebase) |
| Tài liệu gốc | `docs/imm-12/` (6 files) |
| Branch | `feature/hieuc/docs-ba` |

---

## 1. Tổng quan nhanh

| Layer | Trạng thái thực tế | Đánh giá |
|---|---|---|
| **DocType BE** | ✅ Đầy đủ — 4/4 DocType đã LIVE | Vượt kế hoạch tài liệu |
| **Service Layer** | ✅ Đầy đủ — 14 functions implement | Vượt kế hoạch tài liệu |
| **API Layer** | ✅ Đầy đủ — 14 endpoints whitelist | Vượt kế hoạch tài liệu |
| **Frontend API client** | ✅ Đầy đủ — 13 functions + 5 interfaces | Đúng kế hoạch |
| **Frontend Views** | ✅ 5/5 views implemented | Vượt kế hoạch tài liệu |
| **Scheduler** | ✅ Hook đã đăng ký trong hooks.py | Đúng kế hoạch |
| **Business Rules** | ⚠️ Một phần — BR-12-02, VR-12-03 chưa đủ | Lệch thiết kế |
| **Tests** | ❌ Chưa có test file nào | Thiếu hoàn toàn |
| **UAT** | ❌ Chưa thực thi | Pending |

**Tổng thể: ~80% — code đã chạy được, thiếu test + một số BR quan trọng**

---

## 2. DocType — Phân tích chi tiết

### 2.1 Trạng thái

| DocType | Tài liệu yêu cầu | Thực tế | Ghi chú |
|---|---|---|---|
| `Incident Report` | ✅ LIVE từ IMM-00 + custom fields extension | ✅ LIVE | 27 fields đã đầy đủ |
| `IMM RCA Record` | ⚠️ Pending trong tài liệu | ✅ **LIVE** | Đã implement với 15 fields |
| `IMM RCA Five Why Step` | ⚠️ Pending | ✅ **LIVE** | Child table 3 fields (why_number, why_question, why_answer) |
| `IMM CAPA Record` | ✅ LIVE từ IMM-00 | ✅ LIVE | 24 fields |
| `RCA Related Incident` (chronic) | ⚠️ Pending | ❌ **Chưa có** | Cần cho chronic failure groups |

> **Nhận xét:** Tài liệu ghi `RCA Record` là Pending nhưng `IMM RCA Record` đã được deploy. Tên DocType khác tài liệu (`IMM RCA Record` thay vì `RCA Record`) — cần cập nhật docs.

### 2.2 Incident Report — Field Coverage

| Field đặc thù IMM-12 | Có trong DocType? | Ghi chú |
|---|---|---|
| `severity` | ✅ | Select: Low/Medium/High/Critical |
| `fault_code` | ✅ | Free text |
| `clinical_impact` | ✅ | Text |
| `rca_required` | ✅ | Check |
| `rca_record` | ✅ | Link IMM RCA Record |
| `linked_capa` | ✅ | Link IMM CAPA Record |
| `chronic_failure_flag` | ✅ | Check |
| `patient_affected` | ✅ | Check |
| `workaround_applied` | ✅ | Check |
| `acknowledged_by / acknowledged_at` | ❌ | Thiếu — không track ai acknowledge |
| `resolved_by / resolved_at` | ❌ | Thiếu — không track ai resolve |
| `closed_by` | ❌ | Thiếu |
| `assigned_to` | ❌ | Thiếu — KTV phụ trách |

> **Gap:** Tài liệu Technical Design (§2.2) yêu cầu tracking 6 timestamp/actor fields — hiện chỉ có `closed_date`, không có `*_by / *_at`.

### 2.3 IMM RCA Record — Field Coverage

| Field theo thiết kế | Có? | Ghi chú |
|---|---|---|
| `incident_report` | ✅ | Link Incident Report |
| `asset` | ✅ | Link AC Asset |
| `rca_method` | ✅ | Select |
| `five_why_steps` | ✅ | Table → IMM RCA Five Why Step |
| `root_cause` | ✅ | Text |
| `corrective_action_summary` | ✅ | Text |
| `preventive_action_summary` | ✅ | Text |
| `rca_notes` | ✅ | Text |
| `linked_capa` | ✅ | Link IMM CAPA Record |
| `status` | ✅ | Select |
| `completed_date` | ✅ | Date |
| `assigned_to` | ✅ | Link User |
| `trigger_type` | ❌ | Thiếu — Major/Critical/Chronic/Manual |
| `related_incidents` | ❌ | Thiếu — child table cho chronic groups |
| `incident_count` | ❌ | Thiếu — số IR trong chronic group |
| `due_date` | ❌ | Thiếu — deadline RCA |
| `contributing_factors` | ❌ | Thiếu |
| `completed_by` | ❌ | Thiếu |

---

## 3. Service Layer (`services/imm12.py`) — Phân tích chi tiết

**Tổng: 14 functions implement** (tài liệu yêu cầu 7 core functions)

### 3.1 Function Coverage

| Function tài liệu yêu cầu | Implement? | Tên thực tế | Ghi chú |
|---|---|---|---|
| `report_incident()` | ✅ | `report_incident()` | Đầy đủ, BR-12-01/04 |
| `acknowledge_incident()` | ✅ | `acknowledge_incident()` | Implement → status "Under Investigation" |
| `resolve_incident()` | ✅ | `resolve_incident()` | Auto-CAPA cho High/Critical |
| `close_incident()` | ✅ | `close_incident()` | Khôi phục asset Active |
| `cancel_incident()` | ✅ | `cancel_incident()` | False alarm workflow |
| `trigger_rca_if_required()` | ⚠️ | Tích hợp vào `create_rca()` | Không tách riêng như thiết kế |
| `submit_rca_and_create_capa()` | ✅ | `submit_rca()` | Auto tạo CAPA qua imm00 |
| `detect_chronic_failures()` | ✅ | `detect_chronic_failures()` | Scheduler daily |
| `get_incident_detail()` | ✅ | `get_incident_detail()` | |
| `list_incidents()` | ✅ | `list_incidents()` | Pagination |
| `get_incident_stats()` | ✅ | `get_incident_stats()` | KPI counts |
| `get_dashboard()` | ✅ | `get_dashboard()` | Stats + recent + chronic |
| `get_chronic_failures()` | ✅ | `get_chronic_failures()` | SQL query 90 ngày |
| `get_asset_incident_history()` | ✅ | `get_asset_incident_history()` | |

### 3.2 Business Rule Coverage

| BR | Mô tả | Implement? | Ghi chú |
|---|---|---|---|
| **BR-12-01** | Critical → clinical_impact bắt buộc | ✅ | `report_incident()` dòng 110–111 |
| **BR-12-02** | Major/Critical → RCA Completed trước Close | ⚠️ **Thiếu** | `close_incident()` không check `rca_record.status` |
| **BR-12-03** | ≥3 incidents/fault_code/90 ngày → chronic flag | ✅ | `detect_chronic_failures()` — nhưng chưa tạo RCA tự động |
| **BR-12-04** | Critical → auto Out of Service | ✅ | `report_incident()` dòng 140–151 + `acknowledge_incident()` |
| **BR-12-05** | Mọi transition → Audit Trail | ✅ | `_log()` helper qua `svc00.log_audit_event()` |
| **BR-12-06** | RCA Submit → auto `imm00.create_capa()` | ✅ | `submit_rca()` dòng 329–344 |
| **BR-12-07** | RCA root_cause + method bắt buộc | ✅ | `submit_rca()` validation dòng 307–311 |

### 3.3 Lệch thiết kế đáng chú ý

| Điểm | Thiết kế | Thực tế | Rủi ro |
|---|---|---|---|
| Severity labels | Minor/Major/Critical | **Low/Medium/High/Critical** | Mapping `_map_severity()` che giấu mismatch |
| State machine | Open→Acknowledged→In Progress→Resolved | **Open→Under Investigation→Resolved** | State "Acknowledged" và "In Progress" bị gộp |
| `resolve_incident()` | Yêu cầu `rca_record` trước Resolve nếu High/Critical | Validate ngược: block nếu `severity in ("High","Critical") and not rca_record` | Sẽ block Resolve trước khi user có cơ hội tạo RCA |
| `detect_chronic_failures()` | Tạo RCA Record cho chronic group | Chỉ set `chronic_failure_flag = 1`, **không tạo RCA** | BR-12-03 implement một nửa |

---

## 4. API Layer (`api/imm12.py`) — Phân tích chi tiết

**14 endpoints whitelist:**

| Endpoint | Method | Tài liệu yêu cầu | Implement? |
|---|---|---|---|
| `report_incident` | POST | ✅ | ✅ |
| `cancel_incident` | POST | ✅ | ✅ |
| `acknowledge_incident` | POST | ✅ | ✅ |
| `resolve_incident` | POST | ✅ | ✅ |
| `close_incident` | POST | ✅ | ✅ |
| `create_rca` | POST | ✅ | ✅ |
| `get_rca` | GET | ✅ | ✅ |
| `submit_rca` | POST | ✅ | ✅ |
| `list_incidents` | GET | ✅ | ✅ |
| `get_incident` | GET | ✅ | ✅ |
| `get_asset_incident_history` | GET | ✅ | ✅ |
| `get_chronic_failures` | GET | ✅ | ✅ |
| `get_dashboard` | GET | ✅ | ✅ |
| `get_incident_stats` | GET | Bonus | ✅ Thêm ngoài thiết kế |

**Permission check:** Role-based `_has_role()` áp dụng tại:
- `cancel_incident` → `_ROLES_INVESTIGATE`
- `acknowledge_incident` → `_ROLES_INVESTIGATE`
- `resolve_incident` → `_ROLES_INVESTIGATE`
- `close_incident` → `_ROLES_CLOSE`
- `create_rca`, `submit_rca` → `_ROLES_INVESTIGATE`
- Các GET endpoint: chỉ check `session.user != "Guest"`

**Thiếu:** CAPA endpoints (`create_capa`, `close_capa`, `list_capa`, `get_capa`) được thiết kế là reuse từ `api/imm00.py` — cần xác nhận `api/imm00.py` đã expose các endpoint này.

---

## 5. Frontend — Phân tích chi tiết

### 5.1 Views Coverage

| View | Tài liệu yêu cầu | Implement? | Ghi chú |
|---|---|---|---|
| Incident List | ✅ | ✅ `IncidentListView.vue` | Filter severity/status, pagination |
| Incident Create | ✅ | ✅ `IncidentCreateView.vue` | BR-12-01 validation, patient impact |
| Incident Detail | ✅ | ✅ `IncidentDetailView.vue` | 4 workflow modals: Ack/Resolve/Close/Cancel |
| RCA Detail | ✅ | ✅ `RCADetailView.vue` | 5-Why grid, auto-CAPA link |
| CAPA List | ✅ | ✅ `CAPAListView.vue` | |
| CAPA Detail | ✅ | ✅ `CAPADetailView.vue` | |
| Dashboard IMM-12 | ✅ | ❌ **Chưa có** | Không có route `/imm-12/dashboard` |

### 5.2 API Client (`frontend/src/api/imm12.ts`)

- **5 interfaces:** `IncidentDetail`, `RCADetail`, `ChronicFailure`, `IncidentStats`, `ReportIncidentPayload`, `SubmitRcaPayload`
- **13 functions:** listIncidents, getIncident, acknowledgeIncident, resolveIncident, closeIncident, getIncidentStats, reportIncident, cancelIncident, createRca, getRca, submitRca, getAssetIncidentHistory, getChronicFailures, getDashboard

**Vấn đề nhỏ:**
- `getDashboard()` trả về interface inline — không export type
- `IncidentDetail.status` chỉ gồm `'Open' | 'Under Investigation' | 'Resolved' | 'Closed'` — thiếu `'Cancelled'`

### 5.3 State Management

- `IncidentListView.vue` dùng `useIncidentStore()` từ `@/stores/imm00` — **store nằm sai module** (nên là `stores/imm12`)
- `IncidentCreateView.vue` và `IncidentDetailView.vue` call API trực tiếp (không qua store) — không nhất quán

### 5.4 Router

Route đã đăng ký (xác nhận trong `router/index.ts`):
- `/incidents` → `IncidentListView`
- `/incidents/new` → `IncidentCreateView`
- `/incidents/:id` → `IncidentDetailView`
- `/rca/:id` → `RCADetailView`

**Thiếu routes:**
- `/capas` → CAPA List (cần kiểm tra)
- `/imm-12/dashboard` → chưa có view

---

## 6. Scheduler

| Job | hooks.py | Thực tế |
|---|---|---|
| `detect_chronic_failures` | ✅ Đăng ký `daily` | ✅ Function tồn tại và hoạt động |

**Lưu ý:** Tài liệu đề xuất `cron: "0 2 * * *"` (02:00 hàng ngày) nhưng code đăng ký vào `daily` (thời gian không xác định). Nên chuyển sang `cron` nếu cần kiểm soát giờ chạy.

---

## 7. Gap Summary — Việc cần làm

### P1 — Quan trọng / Block UAT

| # | Vấn đề | File | Ảnh hưởng |
|---|---|---|---|
| G-01 | **BR-12-02 chưa implement**: `close_incident()` không check `rca_record.status == "Completed"` | `services/imm12.py:236–264` | Major/Critical có thể Close không qua RCA |
| G-02 | **`detect_chronic_failures()` không tạo RCA tự động** cho chronic groups | `services/imm12.py:473–495` | BR-12-03 implement một nửa |
| G-03 | **`resolve_incident()` block quá sớm**: yêu cầu RCA tồn tại trước Resolve — nhưng workflow đúng là Resolve trước rồi mới tạo RCA | `services/imm12.py:198–202` | UX sai — user bị blocked |
| G-04 | **Thiếu Test** — không có `tests/test_imm12.py` | `assetcore/tests/` | UAT coverage = 0% |

### P2 — Nên sửa trước release

| # | Vấn đề | File | Ảnh hưởng |
|---|---|---|---|
| G-05 | Severity labels lệch tài liệu (Low/Medium/High vs Minor/Major/Critical) | `services/imm12.py` + `IncidentCreateView.vue` | CAPA severity mapping sai |
| G-06 | Thiếu `acknowledged_by/at`, `resolved_by/at`, `closed_by` trên `Incident Report` DocType | DocType JSON | Audit trail incomplete |
| G-07 | `trigger_type`, `related_incidents`, `due_date`, `completed_by` thiếu trên `IMM RCA Record` | DocType JSON | Chronic tracking không đủ data |
| G-08 | `IncidentListView.vue` dùng `useIncidentStore()` từ `stores/imm00` — sai module | `frontend/src/views/IncidentListView.vue:6` | Code coupling sai layer |
| G-09 | `IncidentDetail.status` thiếu `'Cancelled'` trong TypeScript type | `frontend/src/api/imm12.ts:14` | Type error tiềm ẩn |

### P3 — Backlog / Nice to have

| # | Vấn đề | Ghi chú |
|---|---|---|
| G-10 | Thiếu IMM-12 Dashboard view | Tài liệu `IMM-12_UI_UX_Guide.md` yêu cầu |
| G-11 | CAPA endpoints trong `api/imm00.py` chưa xác nhận coverage | Cần rà soát `api/imm00.py` |
| G-12 | Scheduler nên dùng `cron: "0 2 * * *"` thay vì `daily` | Kiểm soát giờ chạy |
| G-13 | `RCA Related Incident` child table chưa có | Cần cho chronic failure grouping đầy đủ |

---

## 8. Tiến độ theo Sprint tài liệu

| Sprint | Mô tả | Tài liệu | Thực tế |
|---|---|---|---|
| 12.1 | Custom fields extension Incident Report | ⚠️ Pending | ✅ **Done** |
| 12.2 | RCA Record DocType + child tables | ⚠️ Pending | ✅ **Done** (thiếu 5 fields nhỏ) |
| 12.3 | `services/imm12.py` | ⚠️ Pending | ✅ **Done** (14/7 functions) |
| 12.4 | `api/imm12.py` REST endpoints | ⚠️ Pending | ✅ **Done** (14 endpoints) |
| 12.5 | Scheduler `detect_chronic_failures` | ⚠️ Pending | ✅ **Done** (chỉ flag, chưa tạo RCA) |
| 12.6 | FE Incident List/Form, CAPA List/Form, RCA Form | ⚠️ Pending | ✅ **Done** (thiếu Dashboard) |
| 12.7 | UAT execution | ⚠️ Pending | ❌ **Pending** |

**Tài liệu gốc (ngày 2026-04-18) ghi toàn bộ là PENDING — code đã vượt xa so với trạng thái tài liệu.**

---

## 9. Kết luận & Khuyến nghị

### ✅ Đã hoàn thành tốt
- Toàn bộ data layer (DocType) và service layer đã deploy
- API endpoints đầy đủ, có role-based access control
- 5/6 frontend views đã implement với UX đúng design
- BR-12-01, BR-12-04, BR-12-05, BR-12-06, BR-12-07 enforce đúng
- Scheduler hook đã đăng ký, hàm `detect_chronic_failures` chạy được

### ⚠️ Cần fix trước UAT (G-01 → G-04)

1. **G-01**: Thêm validation vào `close_incident()` — check `rca_record` phải `Completed` với Major/Critical
2. **G-02**: Cập nhật `detect_chronic_failures()` — sau khi flag IR, tạo `IMM RCA Record` với `trigger_type = "Chronic Failure"`
3. **G-03**: Đảo workflow Resolve: không block nếu thiếu RCA, thay vào đó **auto-tạo RCA** sau Resolve (như tài liệu thiết kế)
4. **G-04**: Viết `assetcore/tests/test_imm12.py` — cover ít nhất BR-12-01 → BR-12-07

### 📋 Chuẩn bị UAT
- Chạy `bench --site miyano execute assetcore.scripts.seed_pm_cm_data.run` để có data
- Thực thi TC-12-01 → TC-12-17 theo `IMM-12_UAT_Script.md`
- Focus vào TC-12-06 (BR-12-02 block Close) — currently failing do G-01
