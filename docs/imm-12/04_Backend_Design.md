# 04 — Backend Design

| Mục | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Cập nhật | 2026-05-14 |
| Trạng thái | ✅ Live — `services/imm12.py` và `api/imm12.py` đã implement |

---

## 1. Architecture Overview

```text
┌──────────────────────────────────────────────────────────┐
│  api/imm12.py   ← @frappe.whitelist() — thin wrapper     │
│  api/imm00.py   ← CAPA endpoints (✅ LIVE)                │
└──────────────────────┬───────────────────────────────────┘
                       │ no logic — delegate only
                       ▼
┌──────────────────────────────────────────────────────────┐
│  services/imm12.py  ← orchestration + IMM-12 logic       │
│  services/imm00.py  ← CAPA / audit / lifecycle (✅ LIVE)  │
└──────────────────────┬───────────────────────────────────┘
                       │ frappe.get_doc / frappe.db
                       ▼
┌──────────────────────────────────────────────────────────┐
│  DocType Controllers                                      │
│  Incident Report (`incident_report`) ✅ LIVE              │
│  IMM RCA Record (`imm_rca_record`) ✅ LIVE                │
│  IMM CAPA Record (`imm_capa_record`) ✅ LIVE              │
└──────────────────────────────────────────────────────────┘
```

**Conventions:**
- Type hints + docstring cho mọi function
- API layer: parse params → call service → `_ok()` / `_err()`
- ServiceError: `raise frappe.ValidationError("...")` — caught by `_handle()`
- Naming: `snake_case` Python, `PascalCase` DocType

---

## 2. DocTypes

### 2.1 Incident Report ✅ DocType: `incident_report`

> DocType name: `Incident Report`. DocType folder: `assetcore/assetcore/doctype/incident_report/`. Fields below reflect actual schema.

| Field | Type | Mandatory | Notes |
|---|---|---|---|
| `severity` | Select (Minor/Major/Critical) | Yes | — |
| `fault_code` | Data | No | Lookup catalog |
| `clinical_impact` | Text | Conditional | Required if Critical (BR-12-01) |
| `acknowledged_by` | Link User | No | Set on Acknowledge |
| `acknowledged_at` | Datetime | No | Auto |
| `resolved_by` | Link User | No | Set on Resolve |
| `resolved_at` | Datetime | No | Auto |
| `closed_by` | Link User | No | Set on Close |
| `closed_at` | Datetime | No | Auto |
| `linked_repair_wo` | Link / Data | No | IMM-09 (actual field name: `linked_repair_wo`) |
| `rca_record` | Link RCA Record | No | Auto when trigger |
| `rca_required` | Check | No | True if Major/Critical/Chronic |
| `linked_capa` | Link IMM CAPA Record | No | Set after RCA Submit |
| `chronic_failure_flag` | Check | No | Set by scheduler |
| `assigned_to` | Link User | No | KTV phụ trách |

**Permission Query (DocType level):**
```python
def get_permission_query_conditions(user):
    """Reporting User chỉ thấy IR của department mình."""
    if "IMM Workshop Lead" in frappe.get_roles(user):
        return ""  # see all
    dept = frappe.db.get_value("Employee", {"user_id": user}, "department")
    return f'`tabIncident Report`.`department` = "{dept}"'
```

**Indexes:**
```sql
CREATE INDEX idx_ir_asset_fault_date
  ON `tabIncident Report` (asset, fault_code, reported_at);
CREATE INDEX idx_ir_severity_status
  ON `tabIncident Report` (severity, status);
```

### 2.2 IMM RCA Record ✅ DocType: `imm_rca_record`

DocType name: `IMM RCA Record`. Child tables: `IMM RCA Five Why Step` (`imm_rca_five_why_step`) for 5-Why, `IMM RCA Related Incident` (`imm_rca_related_incident`) for chronic grouping.

Naming: `RCA-.YYYY.-.#####` · Submittable

| Field | Type | Mandatory | Notes |
|---|---|---|---|
| `asset` | Link AC Asset | Yes | — |
| `incident_report` | Link Incident Report | Yes | Primary source |
| `related_incidents` | Table (RCA Related Incident) | No | Chronic group |
| `fault_code` | Data | No | — |
| `trigger_type` | Select | Yes | Major Incident / Critical Incident / Chronic Failure / Manual |
| `incident_count` | Int | No | Chronic: COUNT in 90 days |
| `rca_method` | Select | Required before Submit | 5Why / Fishbone / Other |
| `root_cause` | Text | Required before Submit | BR-12-07 |
| `contributing_factors` | Text | No | — |
| `five_why_steps` | Table (RCA Five Why Step) | No | When method=5Why |
| `corrective_action_summary` | Text | No | Set on submit_rca (actual field: `corrective_action_summary`) |
| `preventive_action_summary` | Text | No | Set on submit_rca (actual field: `preventive_action_summary`) |
| `due_date` | Date | Yes | +7d or +14d |
| `status` | Select | Yes | RCA Required / RCA In Progress / Completed / Cancelled |
| `assigned_to` | Link User | Yes | — |
| `completed_by` | Link User | No | Set on Submit |
| `completed_date` | Date | No | Auto |
| `linked_capa` | Link IMM CAPA Record | No | Auto after Submit (BR-12-06) |

**IMM RCA Record Controller:** `assetcore/assetcore/doctype/imm_rca_record/imm_rca_record.py` ✅ EXISTS

---

## 3. Workflow — Incident Report ✅ LIVE

### States (actual — constants `services/imm12.py:37-47` + `imm_12_incident_workflow.json`)

| State | docstatus | Mô tả |
|---|---|---|
| Open | 0 | IR mới tạo |
| Acknowledged | 0 | Workshop Lead/Technician đã tiếp nhận |
| In Progress | 0 | Đang xử lý |
| Resolved | 0 | Đã giải quyết |
| RCA Required | 0 | High/Critical hoặc chronic — chờ RCA Completed trước Close |
| Closed | 0 | Final — IR đóng |
| Cancelled | 0 | False alarm |

> Internal docstring trong `services/imm12.py` đôi chỗ ghi "Under Investigation" — đây là alias lịch sử cho `In Progress`. Tên state thực tế trong code & DocType là `In Progress`.

### Transitions (actual `_VALID_TRANSITIONS` dict in service + workflow JSON)

| From | To | Trigger function | Actor | Validation |
|---|---|---|---|---|
| Open | Acknowledged | `acknowledge_incident()` | Workshop Lead, Technician | — |
| Open | In Progress | `acknowledge_incident()` (skip Acknowledged) | Workshop Lead, Technician | — |
| Open | Cancelled | `cancel_incident()` | Workshop Lead | reason required |
| Acknowledged | In Progress | (workflow action "Bắt đầu xử lý") | Workshop Lead, Technician | — |
| Acknowledged | Cancelled | `cancel_incident()` | Workshop Lead | reason required |
| In Progress | Resolved | `resolve_incident()` | Workshop Lead, Technician | resolution_notes required |
| In Progress | RCA Required | `resolve_incident()` cho High/Critical | System | severity ∈ {High, Critical} |
| In Progress | Cancelled | `cancel_incident()` | Workshop Lead | reason required |
| Resolved | Closed | `close_incident()` | Workshop Lead, QA Officer | BR-12-02: High/Critical → RCA `Completed` required |
| Resolved | In Progress | (workflow action "Mở lại điều tra") | Workshop Lead | — |
| RCA Required | Closed | `close_incident()` sau RCA `Completed` | Workshop Lead, QA Officer | — |

**RCA States:** `RCA Required` → `RCA In Progress` → `Completed` / `Cancelled`

**BR-12-04:** Critical → auto asset Out of Service on `report_incident()`. High → auto asset Out of Service on `acknowledge_incident()`.
**BR-12-02:** High/Critical Incident cannot close until linked RCA status = `Completed`.
**Asset restore:** `close_incident()` checks if asset is `Out of Service` and transitions back to `Active`.

### 3.1 SoT "incident đang mở" — Single Source of Truth (BR-12-11) ✅ LIVE

Định nghĩa DUY NHẤT cho khái niệm "incident đang mở" — mọi consumer (dashboard KPI card / donut / persona, SLA breach engine, list drill-down) PHẢI dùng chung helper này → **invariant: card count == số dòng list sau drill** (không drift).

```python
# services/imm12.py:59-74 (đã có từ round-18 — KHÔNG sửa)
INCIDENT_OPEN_STATES = (Open, Acknowledged, In Progress, RCA Required)   # POSITIVE list

def open_incident_filter(extra: dict | None = None) -> dict:
    """Trả {"status": ["in", INCIDENT_OPEN_STATES], **extra}."""
```

| State | Trong open-set? | Lý do |
|---|---|---|
| Open | ✅ | mới tạo, chưa xử lý |
| Acknowledged | ✅ | đã tiếp nhận, còn đang xử lý — **KHÔNG được bỏ sót** |
| In Progress | ✅ | đang xử lý |
| RCA Required | ✅ | chờ RCA Completed trước Close — **KHÔNG được bỏ sót** |
| Resolved | ❌ | đã rời open-set (terminal-ish) |
| Closed | ❌ | terminal |
| Cancelled | ❌ | terminal (false alarm) — dùng POSITIVE list để KHỎI vô tình đếm Cancelled là mở |

**BR-12-11 (delta vòng 21) — gắn 2 consumer còn sót vào SoT:**

1. **`get_incident_stats()` THÊM key `open_total`** = `_count(open_incident_filter())` = số incident ở MỌI state mở của SoT — KHÔNG chỉ `status == "Open"`. Trên live DB hiện tại (3 Open + 1 Acknowledged = 4 mở, 1 Closed) ⇒ `open_total == 4`, KHÔNG còn `== 3`.
2. **`get_dashboard().active_incidents`** đổi filter từ tuple cục bộ `[_STATUS_OPEN, _STATUS_INVESTIGATING]` → `open_incident_filter()` ⇒ bao trùm Acknowledged + RCA Required; số dòng (trước cắt `limit_page_length=10`) khớp `open_total`.
3. **Grep guard:** trong `get_incident_stats()` + `get_dashboard()` KHÔNG còn literal/tuple status cục bộ cho ngữ nghĩa open-set (vd inline `[_STATUS_OPEN, _STATUS_INVESTIGATING]`). Định nghĩa open-set CHỈ tồn tại ở `INCIDENT_OPEN_STATES` / `open_incident_filter()`.

**Backward-compat (BẮT BUỘC):** giữ nguyên key `open` (= count `status==Open`) và `investigating` (= count `status==In Progress`) trong `get_incident_stats()` — consumer khác đọc breakdown từng-state vẫn chạy. Vòng 21 chỉ **THÊM** `open_total`, KHÔNG xoá/đổi nghĩa key cũ.

**BR-12-11b (delta vòng 29) — KPI strip severity = open-set (gắn tile "nghiêm trọng/mức cao" vào SoT):**

Vấn đề thiết kế gốc (Self-Correction): KPI strip `IncidentListView.vue` tile *"Sự cố nghiêm trọng"* / *"Sự cố mức cao"* hiện bind `stats.critical` / `stats.high` — đây là **count GLOBAL mọi-status** (gồm Closed/Cancelled/Resolved). Khi user drill `?open=1` (hoặc `?severity=High`), bảng chỉ hiển thị dòng open-set ⇒ **mâu thuẫn thị giác strip-vs-table**: strip báo số global (vd 4 High kể cả đã đóng) trong khi bảng chỉ 2 dòng High đang mở. Strip severity phải đếm theo **cùng SoT** `open_incident_filter()` như mọi consumer khác.

1. **`get_incident_stats()` THÊM 2 key `critical_open` + `high_open`** = `_count(open_incident_filter({"severity": …}))` — DÙNG LẠI SoT `open_incident_filter()` (round-18), **KHÔNG** inline negative-list / tuple status mới. Closed/Cancelled/Resolved **bị loại** vì không nằm trong `INCIDENT_OPEN_STATES`.

```python
# services/imm12.py::get_incident_stats() — THÊM (KHÔNG xoá critical/high global)
"critical_open": _count(open_incident_filter({"severity": _SEV_CRITICAL})),
"high_open":     _count(open_incident_filter({"severity": _SEV_HIGH})),
```

> `open_incident_filter(extra)` đã hỗ trợ merge `extra` (xem `:64`): `open_incident_filter({"severity": _SEV_CRITICAL})` → `{"status": ["in", INCIDENT_OPEN_STATES], "severity": "Critical"}`. KHÔNG cần helper mới.

2. **Backward-compat (BẮT BUỘC):** GIỮ NGUYÊN `critical` (= count `severity==Critical`, mọi-status) và `high` (global) cho donut/severity_breakdown + consumer cũ. Vòng 29 chỉ **THÊM** `critical_open`/`high_open`.

3. **Grep guard:** open-set severity count CHỈ sinh qua `open_incident_filter()` (1 SoT). KHÔNG literal/tuple status open-set cục bộ trong `get_incident_stats()` cho 2 key mới.

**Invariant đo được (data live: 5 incident = 3 Open + 1 Acknowledged + 1 Closed + 0 Cancelled; trong open-set: 1 Critical + 2 High):**

| Key | Giá trị | Predicate |
|---|---|---|
| `critical_open` | `== 1` | `open_incident_filter() ∧ severity==Critical` (Closed/Cancelled loại) |
| `high_open` | `== 2` | `open_incident_filter() ∧ severity==High` |
| `critical` (global, giữ) | == tổng-mọi-status | `severity==Critical` |
| `high` (global, giữ) | == tổng-mọi-status | `severity==High` |
| **bất biến** | `critical_open <= critical` ∧ `high_open <= high` | luôn đúng (open-set ⊆ all-status) |

**Hồi quy (KHÔNG đổi):** `open_total` (round-21), `closed`, `severity_breakdown` donut (ngoài scope), invariant card==drill (round-18/21). ⚠️ `chronic` ĐỔI nghĩa ở BR-12-12 vòng này (xem dưới) — không còn "đếm cờ".

---

**BR-12-12 (delta vòng 3/50) — KPI "Lặp lại (Chronic)" = nhóm LIVE rolling-window, kill tile-vs-panel divergence:**

Vấn đề thiết kế gốc (Self-Correction): `get_incident_stats()` đặt `"chronic": _count({"chronic_failure_flag": 1})` (`services/imm12.py:670`) — đếm **cờ bền vững** `chronic_failure_flag`. Cờ này do scheduler `_process_chronic_group()` (`:858-873`) set `=1` trên TỪNG incident-row thuộc cụm chronic, và **KHÔNG BAO GIỜ reset** khi cụm hết hạn 90 ngày (cờ là dấu lịch sử BR-12-03). Hậu quả:

- **Tile monotone-stale**: tile `chronic` chỉ tăng, không giảm — khi 3+ incident cũ aged-out > 90 ngày, không còn nhóm `(asset, fault_code)` nào ≥ 3 trong 90d, nhưng tile VẪN > 0 vì cờ còn nguyên trên các incident cũ.
- **Lệch đơn vị**: tile đếm **số incident-rows-có-cờ** (vd 6 row) trong khi panel ngay dưới (`get_dashboard().chronic_failures` = `get_chronic_failures()`) đếm **số nhóm `(asset, fault_code)` live** (vd 1 nhóm). 2 con số mâu thuẫn trên CÙNG 1 màn hình (`IMM12DashboardView.vue:106` tile vs `:221-234` panel).
- **Định nghĩa doc lệch**: 02 §I.5:94 (cũ "Assets có cờ = True") vs §II.7 BR-12-03:189 / get_chronic_failures (live rolling). **BA CHỐT: SoT = LIVE** (định nghĩa rolling-window là cái user/QA Officer hành động theo); cờ giữ riêng cho badge per-row + RCA grouping.

**Quyết định Core Doc:**

1. **Thêm 1 SoT count helper dùng chung** `chronic_failure_count() -> int` — phái sinh từ CHÍNH `get_chronic_failures()` (anti-drift, KHÔNG re-implement SQL):

```python
# services/imm12.py — SoT DUY NHẤT cho KPI chronic (BR-12-12)
def chronic_failure_count() -> int:
    """Số nhóm (asset, fault_code) đang chronic theo cửa sổ trượt 90 ngày live.
    CÙNG predicate get_chronic_failures() (GROUP BY HAVING >= 3) → 1 SoT, no drift."""
    return len(get_chronic_failures())
```

2. **`get_incident_stats()` đổi `chronic` sang SoT helper** — XOÁ `_count({"chronic_failure_flag": 1})`:

```python
# services/imm12.py::get_incident_stats() — THAY (KHÔNG còn đếm cờ)
"chronic": chronic_failure_count(),   # BR-12-12 LIVE — was _count({"chronic_failure_flag": 1})
```

3. **Grep guard**: trong `get_incident_stats()` KHÔNG còn `chronic_failure_flag` cho ngữ nghĩa KPI tile. Đếm chronic CHỈ sinh qua `chronic_failure_count()`/`get_chronic_failures()` (1 SoT). (Cờ `chronic_failure_flag` còn xuất hiện ở `_process_chronic_group` setter + list field cho badge per-row — đó là lifecycle riêng, KHÔNG đụng.)

4. **Invariant tile == panel (BR-12-12, đo trên 1 payload `get_dashboard()`):** `stats.chronic == len(chronic_failures)`. ⚠️ **Lưu ý cắt top-5**: `get_dashboard().chronic_failures = get_chronic_failures()[:5]` (hiển thị top-5 panel). Để invariant ĐÚNG cả khi > 5 nhóm, Core Doc CHỐT 1 trong 2 (BE chọn, ghi rõ trong test):
   - **(a) khuyến nghị:** invariant test giữ data ≤ 5 nhóm (thực tế live ~1 nhóm) ⇒ `[:5]` không cắt ⇒ `stats.chronic == len(dashboard["chronic_failures"])` đúng tự nhiên. Test assert trực tiếp trên payload.
   - **(b) nếu BE muốn invariant bền > 5 nhóm:** so `stats.chronic` với `len(get_chronic_failures())` (FULL, không cắt) trong test — vì cả `stats.chronic` lẫn panel-source cùng phái sinh từ `get_chronic_failures()`, `[:5]` chỉ là view-limit hiển thị, KHÔNG phải nguồn đếm. KHÔNG bỏ `[:5]` ở payload (giữ UX top-5 panel).

   → BE document lựa chọn trong docstring test `TestChronicSoT`.

5. **RED-prove lifecycle (BẮT BUỘC, ≥1 test):** dựng 3+ incident cùng `(asset, fault_code)` với `reported_at` aged-out > 90 ngày (cờ `chronic_failure_flag=1` set trên chúng để mô phỏng cụm cũ đã từng chronic), KHÔNG có nhóm nào ≥ 3 trong 90d hiện tại ⇒ assert `get_incident_stats()["chronic"] == 0`. Revert SoT về `_count({"chronic_failure_flag": 1})` ⇒ test FAIL (tile = 3 ≠ 0, chứng minh test bắt được stale). Restore ⇒ GREEN.

6. **Badge per-row GIỮ NGUYÊN (KHÔNG regression):** `chronic_failure_flag` tiếp tục phục vụ badge *"Lặp lại"* per-row (`IncidentListView.vue:271/:317`) — đánh dấu incident *từng thuộc* cụm chronic (lifecycle BR-12-03, audit/RCA grouping). KHÔNG xoá field, KHÔNG reset cờ, KHÔNG đổi `_process_chronic_group`. Test no-regression: badge vẫn render cho incident có cờ kể cả khi tile chronic = 0.

**Invariant đo được (BR-12-12):**

| Đối tượng | Giá trị | Nguồn |
|---|---|---|
| `stats.chronic` | == số nhóm `(asset, fault_code)` live (≥3/90d) | `chronic_failure_count()` = `len(get_chronic_failures())` |
| `len(dashboard.chronic_failures)` | == `stats.chronic` (data ≤5 nhóm) hoặc == với FULL list (data >5) | `get_chronic_failures()[:5]` / FULL |
| tile sau aged-out >90d (cờ còn =1) | `== 0` (RED-prove) | nhóm live = 0 |
| badge per-row "Lặp lại" | render nếu `ir.chronic_failure_flag==1` | cờ bền vững — KHÔNG đổi |

**Hồi quy (KHÔNG đổi):** `open_total`, `critical_open`/`high_open`, `closed`, donut. Endpoint `api/imm12.py::get_incident_stats()` đã delegate service-layer (round-29) ⇒ `chronic` mới tự lộ qua endpoint, **KHÔNG đụng `api/imm12.py`**.

---

### 3.2 SoT SLA-breach LIVE predicate (BR-12-13) — kill undercount cửa-sổ-trễ-scheduler

Vấn đề thiết kế gốc (Self-Correction): `get_incident_stats()` đặt `"sla_response_breached": _count({"response_breached": 1})` + `"sla_resolution_breached": _count({"resolution_breached": 1})` (`services/imm12.py:677-678`) — đếm **cờ bền vững** `response_breached`/`resolution_breached`. 2 cờ này CHỈ do scheduler `check_incident_sla_breach()` (hourly, `:774`) hoặc write-path `acknowledge_incident`/`resolve_incident` (BR-12-08) stamp `=1`. Hậu quả **undercount cửa-sổ-trễ-scheduler**:

- Incident OPEN vừa quá `resolution_due_at` 1–59 phút, scheduler chưa tới lượt quét hourly ⇒ cờ còn `0` ⇒ tile `sla_resolution_breached` đếm thiếu incident này (vẫn đang breach THẬT). QA Officer nhìn tile thấy 0 trong khi DB có incident quá hạn chưa đóng.
- Cùng lỗi với badge per-row: `list_incidents`/`active_incidents` trả cờ thô `response_breached`/`resolution_breached` ⇒ FE badge chỉ hiện sau khi scheduler stamp, KHÔNG hiện ngay khi quá hạn.
- **Định nghĩa BA CHỐT: SoT = LIVE** — "đang vi phạm SLA" là trạng thái user/QA hành động theo NGAY (NĐ98 Điều 67 cửa sổ luật định), KHÔNG đợi scheduler. Cờ giữ riêng cho escalation idempotent-key (BR-12-09) + audit lịch sử (BR-12-08).

**Quyết định Core Doc:**

1. **Predicate SoT `sla_breach_filter(kind)`** — định nghĩa DUY NHẤT nhánh **live-overdue** (dùng lại `open_incident_filter()` → terminal Cancelled/Closed/Resolved KHÔNG vào nhánh này):

```python
# services/imm12.py — SoT predicate cho nhánh live-overdue (BR-12-13)
def sla_breach_filter(kind: str) -> dict:
    """Filter dict cho nhánh LIVE-OVERDUE của breach (kind ∈ {"response","resolution"}).

    `open_incident_filter()` ∧ `<kind>_due_at < now()` (+ kind==response: acknowledged_at unset).
    KHÔNG gồm nhánh cờ=1 (đếm tách trong sla_breach_count để né OR trong frappe.db.count).
    Terminal Cancelled/Closed/Resolved bị loại tự nhiên (không thuộc INCIDENT_OPEN_STATES) → INV-SLA-6.
    """
    now = now_datetime()
    if kind == "response":
        return open_incident_filter({
            "response_due_at": ["<", now],
            "acknowledged_at": ["is", "not set"],
        })
    return open_incident_filter({
        "resolution_due_at": ["<", now],
    })
```

2. **SoT count helper `sla_breach_count(kind)`** — phái sinh từ `sla_breach_filter`, cộng 2 nhánh mutually-exclusive (cờ=1 vs cờ=0∧live) → KHÔNG double-count:

```python
# services/imm12.py — SoT count cho KPI (BR-12-13). = (cờ=1) OR (đang-mở ∧ quá-hạn-live)
def sla_breach_count(kind: str) -> int:
    flag = "response_breached" if kind == "response" else "resolution_breached"
    flagged = frappe.db.count(_DT_INCIDENT, {flag: 1})
    live_filter = dict(sla_breach_filter(kind))
    live_filter[flag] = 0            # nhánh live CHỈ đếm cờ chưa stamp → exclusive với flagged
    live_unflagged = frappe.db.count(_DT_INCIDENT, live_filter)
    return flagged + live_unflagged
```

> **Vì sao tách 2 `count` thay vì 1 OR**: `frappe.db.count` không hỗ trợ OR ở top-level. 2 nhánh `(cờ=1)` và `(cờ=0 ∧ open ∧ overdue)` **không giao nhau** (phân biệt theo giá trị cờ) ⇒ tổng = đúng predicate `(cờ=1) OR (đang-mở ∧ quá-hạn)`. Đây là lý do `sla_breach_filter` KHÔNG nhúng nhánh cờ — giữ filter "live-overdue" thuần để `sla_breach_count` ghép `flag=0`, đồng thời per-row enrich tái dùng cùng predicate.

3. **`get_incident_stats()` đổi 2 KPI sang SoT helper** — XOÁ `_count({"response_breached":1})`/`_count({"resolution_breached":1})`:

```python
# services/imm12.py::get_incident_stats() — THAY (KHÔNG còn đếm cờ đơn lẻ)
"sla_response_breached":   sla_breach_count("response"),     # BR-12-13 LIVE
"sla_resolution_breached": sla_breach_count("resolution"),
```

4. **Per-row enrich LIVE** — `list_incidents()` + `get_dashboard().active_incidents` thêm `is_response_breached`/`is_resolution_breached` (0|1) derive từ CÙNG predicate trên từng row đã fetch (in-Python, KHÔNG query thêm per-row — đã có `response_due_at`/`resolution_due_at`/`acknowledged_at`/`status`/cờ trong field list). Helper per-row:

```python
# services/imm12.py — derive live breach 1 row (CÙNG predicate sla_breach_filter, in-Python)
def _row_is_breached(row: dict, kind: str, now) -> int:
    flag = row.get("response_breached" if kind == "response" else "resolution_breached")
    if flag:                                   # nhánh cờ=1 (lịch sử / đã stamp)
        return 1
    if row.get("status") not in INCIDENT_OPEN_STATES:   # terminal → KHÔNG live-overdue (INV-SLA-6)
        return 0
    due = row.get("response_due_at" if kind == "response" else "resolution_due_at")
    if not due or get_datetime(due) >= now:
        return 0
    if kind == "response" and row.get("acknowledged_at"):   # đã tiếp nhận → hết live response-breach
        return 0
    return 1
```

   - `list_incidents()` field list THÊM `response_due_at`, `resolution_due_at` (đã có `acknowledged_at`, cờ, status) → sau khi fetch rows, gán `row["is_response_breached"] = _row_is_breached(row, "response", now)` + `is_resolution_breached`.
   - `get_dashboard().active_incidents` field list THÊM `response_due_at`, `resolution_due_at`, `acknowledged_at` (hiện chỉ có cờ) → enrich tương tự.
   - Cờ thô `response_breached`/`resolution_breached` GIỮ trong payload (backward-compat) nhưng FE chuyển sang đọc `is_*_breached` (xem 06).

5. **Grep guard (anti-drift, 1 SoT):** trong `get_incident_stats()` KHÔNG còn `_count({"response_breached":1})` / `_count({"resolution_breached":1})` đơn lẻ cho 2 KPI. Đếm SLA-breach CHỈ sinh qua `sla_breach_count()` → `sla_breach_filter()`. Per-row live CHỈ sinh qua `_row_is_breached()` (cùng predicate). (Cờ thô còn ở write-path `acknowledge_incident`/`resolve_incident`/`check_incident_sla_breach` setter + escalation idempotent-key — lifecycle riêng BR-12-08/09, KHÔNG đụng.)

6. **Idempotent (INV-SLA-4, no double-path drift):** sau `check_incident_sla_breach()` stamp cờ, incident vừa-đếm-vì-live nay rơi vào nhánh `(cờ=1)` ⇒ `sla_breach_count` cho cùng con số (cờ=1 đếm 1, live-unflagged loại nó vì `flag=0` không match). RED-prove: gọi stats → chạy scheduler → gọi lại stats ⇒ `sla_resolution_breached` BẰNG nhau.

7. **RED-prove (BẮT BUỘC):** OPEN incident `resolution_due_at = now()−2h`, `resolution_breached=0`, scheduler chưa chạy ⇒ assert `get_incident_stats()["sla_resolution_breached"] == 1`. Revert 2 KPI về `_count({"...breached":1})` ⇒ test FAIL (0 ≠ 1, chứng minh bắt được undercount). Restore ⇒ GREEN.

**Invariant đo được (BR-12-13):**

| Đối tượng | Giá trị | Nguồn |
|---|---|---|
| `stats.sla_resolution_breached` (OPEN overdue cờ=0) | `== 1` (INV-SLA-1) | `sla_breach_count("resolution")` nhánh live |
| `stats.sla_response_breached` (OPEN unack overdue cờ=0) | `== 1` (INV-SLA-2) | `sla_breach_count("response")` nhánh live |
| `stats.sla_*_breached` (Closed/Resolved cờ=1 lịch sử) | đếm qua nhánh `cờ=1` (INV-SLA-3) | `count(<flag>=1)` |
| `stats.sla_*_breached` trước == sau scheduler | bằng nhau (INV-SLA-4) | idempotent 2-nhánh exclusive |
| `row.is_*_breached` (per-row live) | == tile (INV-SLA-5) | `_row_is_breached()` cùng predicate |
| terminal đóng-đúng-hạn cờ=0 | KHÔNG live-overdue (INV-SLA-6) | `status ∉ INCIDENT_OPEN_STATES` |

**Hồi quy (KHÔNG đổi):** `open_total`, `critical_open`/`high_open`, `chronic`, `closed`, donut. Cờ `response_breached`/`resolution_breached` write-path + escalation BR-12-08/09 KHÔNG đụng. Endpoint `api/imm12.py` delegate service-layer ⇒ 2 KPI + field enrich mới tự lộ qua endpoint, **KHÔNG đụng `api/imm12.py`** (verify delegate verbatim).

---

## 4. Service Layer — `services/imm12.py` ✅ LIVE

### 4.1 Public functions (actual signatures)

| Function | Returns | Logic Owner | Notes |
|---|---|---|---|
| `report_incident(asset, incident_type, severity, description, *, fault_code, ...)` | `dict {name, status, severity}` | IMM-12 | BR-12-01 Critical→clinical_impact; BR-12-04 Critical→OOS |
| `acknowledge_incident(name, notes, assigned_to)` | `dict {name, status}` | IMM-12 | Open→Acknowledged (D3); High→OOS |
| `resolve_incident(name, resolution_notes, root_cause)` | `dict {name, status, rca_created}` | IMM-12 | auto-create RCA for High/Critical |
| `close_incident(name, verification_notes)` | `dict {name, status, closed_date}` | IMM-12 | BR-12-02 RCA Completed check; restore asset Active |
| `cancel_incident(name, reason)` | `dict {name, status}` | IMM-12 | reason required |
| `create_rca(incident_name, rca_method)` | `dict {name, status, due_date}` | IMM-12 | Idempotent: 409 if RCA exists |
| `get_rca(name)` | `dict` | IMM-12 | includes `incident_severity` |
| `submit_rca(name, root_cause, corrective_action, preventive_action, five_why_steps, rca_notes)` | `dict {name, status, linked_capa}` | IMM-12 | BR-12-06: auto `create_capa()` via IMM-00 |
| `list_incidents(status, severity, asset, page, page_size)` | `dict {pagination, items}` | IMM-12 | — |
| `get_incident_detail(name)` | `dict` | IMM-12 | includes `allowed_transitions` + nested `rca` |
| `get_incident_stats()` | `dict` | IMM-12 | counts per status + severity **+ `open_total` = count(`open_incident_filter()`) (BR-12-11 SoT card-count) + `critical_open`/`high_open` = count(`open_incident_filter()∧severity`) (BR-12-11b KPI-strip open-set) + `chronic` = `chronic_failure_count()` (BR-12-12 LIVE rolling-window nhóm, KHÔNG cờ stale) + `sla_response_breached` = `sla_breach_count("response")` + `sla_resolution_breached` = `sla_breach_count("resolution")`** (BR-12-13 LIVE predicate — KHÔNG còn `_count(response_breached=1)`/`_count(resolution_breached=1)` đơn lẻ) |
| `get_asset_incident_history(asset, limit)` | `dict {asset, items}` | IMM-12 | — |
| `chronic_failure_count()` | `int` | IMM-12 | **BR-12-12 SoT helper** — `len(get_chronic_failures())` (CÙNG predicate: GROUP BY (asset, fault_code) HAVING ≥ 3 trong 90d, `status != Cancelled`). Nguồn DUY NHẤT cho `stats.chronic`. Implement = `return len(get_chronic_failures())` (KHÔNG re-implement SQL — 1 SoT predicate) |
| `get_chronic_failures()` | `list` | IMM-12 | SQL GROUP BY (asset, fault_code), HAVING ≥ 3 |
| `sla_breach_filter(kind)` | `dict` (filter) | IMM-12 | **BR-12-13 SoT predicate** — `kind ∈ {"response","resolution"}`. Trả filter dict cho nhánh **live-overdue** (`open_incident_filter()` ∧ `<kind>_due_at < now()` ∧ — chỉ response — `acknowledged_at` is not set). KHÔNG bao gồm nhánh cờ=1 (đếm tách qua `sla_breach_count` để tránh OR trong `frappe.db.count`). Nguồn DUY NHẤT định nghĩa "live-overdue" cho cả count lẫn per-row enrich |
| `sla_breach_count(kind)` | `int` | IMM-12 | **BR-12-13 SoT count** — `count(<kind>_breached=1)` + `count(sla_breach_filter(kind) ∧ <kind>_breached=0)`. 2 nhánh mutually-exclusive (cờ=1 vs cờ=0) ⇒ cộng KHÔNG double-count. = predicate `(cờ=1) OR (đang-mở ∧ quá-hạn-live)`. Nguồn DUY NHẤT cho `stats.sla_response_breached`/`sla_resolution_breached` |
| `get_dashboard()` | `dict {stats, active_incidents, open_rcas, chronic_failures}` | IMM-12 | **`active_incidents` filter = `open_incident_filter()` (BR-12-11) — KHÔNG tuple cục bộ `[Open, In Progress]`; bao trùm Acknowledged + RCA Required; số dòng (trước cắt limit 10) == `stats.open_total`. INVARIANT (BR-12-12): `stats.chronic == len(chronic_failures)` trên cùng payload (cả hai phái sinh từ `get_chronic_failures()`) — tile == panel, KHÔNG drift. ⚠️ `chronic_failures` field giữ `[:5]` để hiển thị top-5, nhưng `stats.chronic` đếm FULL `len(get_chronic_failures())`; nếu > 5 nhóm thì invariant test so `stats.chronic` với FULL list KHÔNG bị cắt — xem §test note `04` dưới.** |
| `detect_chronic_failures()` | `dict {flagged, rca_created, groups}` | Scheduler | BR-12-03: flag + auto RCA Chronic |

**Note:** Function `submit_rca_and_create_capa` does **not** exist — actual name is `submit_rca`. Field `fault_description` does **not** exist — actual field is `description`.

### 4.2 Key implementation notes

- `report_incident` signature: `(asset, incident_type, severity, description, *, fault_code, workaround_applied, clinical_impact, patient_affected, patient_impact_description, immediate_action, linked_repair_wo, reported_by)` — returns `dict`, NOT `str`.
- DocType name used: `"Incident Report"` (constant `_DT_INCIDENT`).
- RCA DocType name: `"IMM RCA Record"` (constant `_DT_RCA`). **NOT** `"RCA Record"`.
- CAPA DocType name: `"IMM CAPA Record"` (constant `_DT_CAPA`).
- Chronic detection: `_CHRONIC_WINDOW_DAYS=90`, `_CHRONIC_MIN_COUNT=3`, `_RCA_DUE_MAJOR=7`, `_RCA_DUE_CHRONIC=14`.
- `submit_rca` writes fields: `root_cause`, `corrective_action_summary`, `preventive_action_summary`, `rca_notes`, `completed_by`, `completed_date`, `linked_capa`.
- Auto-CAPA on `submit_rca` via `svc00.create_capa()` — sets `linked_capa` on both RCA and Incident.
- `_auto_create_capa()` is a fallback on `resolve_incident()` for High/Critical without RCA flow.

---

## 5. API Layer — `api/imm12.py` ✅ LIVE

Imports from `assetcore.utils.response` (`_ok`, `_err`). Role check via `_has_role(*roles)`.

**Roles constants:**
- `_ROLES_INVESTIGATE = {"IMM Workshop Lead", "IMM Technician", "IMM QA Officer", "System Manager"}`
- `_ROLES_CLOSE = {"IMM Workshop Lead", "IMM QA Officer", "System Manager"}`

**Actual @frappe.whitelist endpoints:**

| Function | Method | Role guard |
|---|---|---|
| `report_incident(asset, incident_type, severity, description, fault_code, ...)` | POST | session.user != Guest |
| `cancel_incident(name, reason)` | POST | ROLES_INVESTIGATE |
| `create_rca(incident_name, rca_method)` | POST | ROLES_INVESTIGATE |
| `get_rca(name)` | GET | authenticated |
| `submit_rca(name, root_cause, corrective_action, preventive_action, five_why_steps, rca_notes)` | POST | ROLES_INVESTIGATE |
| `get_asset_incident_history(asset, limit)` | GET | authenticated |
| `get_chronic_failures()` | GET | authenticated |
| `get_dashboard()` | GET | authenticated |
| `list_incidents(status, severity, asset, open, page, page_size)` | GET | authenticated | `open=1` áp SoT `open_incident_filter()` cho drill (status đơn lẻ ưu tiên hơn open) |
| `get_incident(name)` | GET | authenticated |
| `acknowledge_incident(name, notes, assigned_to)` | POST | ROLES_INVESTIGATE |
| `resolve_incident(name, resolution_notes, root_cause)` | POST | ROLES_INVESTIGATE |
| `close_incident(name, verification_notes)` | POST | ROLES_CLOSE |
| `get_incident_stats()` | GET | authenticated | trả service-layer shape (gồm `open_total`) — xem Self-Correction dưới |

> **⚠️ SELF-CORRECTION (BR-12-11) — api-layer `get_incident_stats` divergence:** endpoint `api/imm12.py::get_incident_stats()` hiện re-implement cục bộ với alias chết `"Under Investigation"` + inline open-set tuple `["Open","Under Investigation"]` (đếm 0 trên data thật, vi phạm SoT + CLAUDE.md §15). Core Doc CHỐT: endpoint PHẢI `return handle(svc_stats)` (delegate `services/imm12.py::get_incident_stats`) ⇒ trả CÙNG shape với `get_dashboard().stats` (gồm `open_total`, `total`, severity, `sla_*`). Chi tiết: `05_API §11.6`.

---

## 6. Audit Trail

| Event | Trigger | `event_type` | Actor |
|---|---|---|---|
| IR created (Minor) | `report_incident()` | `incident_reported` | session.user |
| IR created (Critical) | `report_incident()` + asset transition | `incident_reported_critical` | session.user |
| IR Acknowledged | `acknowledge_incident()` | `incident_acknowledged` | Workshop Lead |
| IR Resolved | `resolve_incident()` | `incident_resolved` | Workshop Lead / KTV |
| IR Closed | `close_incident()` | `incident_closed` | Workshop Lead |
| RCA Completed + CAPA created | `submit_rca()` | `rca_completed` | QA Officer |
| Chronic failure detected | `detect_chronic_failures()` | `chronic_failure_detected` | Administrator (scheduler) |
| SLA breach detected | `check_incident_sla_breach()` | `Incident` (`change_summary="SLA breach (...) phát hiện bởi scheduler"`) | Administrator (scheduler) |
| SLA breach escalated | `check_incident_sla_breach()` | `Incident` (`change_summary="SLA breach escalated → <recipients>"`) | Administrator (scheduler) |

> **2 audit entry tách bạch (BR-12-05 + BR-12-09):** entry *phát hiện* (set cờ) đã có từ trước; khi escalate bắn notification thì GHI THÊM entry *escalated* — KHÔNG thay thế entry phát hiện. Nếu incident không có recipient nào → chỉ ghi entry phát hiện (không ghi entry escalated, không bắn rỗng).

Tất cả gọi `imm00.log_audit_event()` → SHA-256 hash chain (NĐ98/ISO 13485).

---

## 7. Scheduler ✅ LIVE

| Job | Cron | Function | Logic |
|---|---|---|---|
| Chronic failure detection | Daily | `imm12.detect_chronic_failures` | BR-12-03: ≥3 same (asset, fault_code) in 90d — returns `{flagged, rca_created, groups}` |
| CAPA overdue check | Daily | `imm00.check_capa_overdue` | ✅ LIVE — BR-00-09 |
| Incident SLA breach + escalation | Hourly | `imm12.check_incident_sla_breach` | BR-12-08 (set cờ) **+ BR-12-09 escalation** (bắn notification 0→1) **+ BR-12-10** (NĐ98 gate Critical/High) — returns `{response_breached, resolution_breached, escalated}` |

**Registration thực tế trong `assetcore/hooks.py`:**
```python
scheduler_events = {
    "daily": [
        "assetcore.services.imm00.check_capa_overdue",
        # ...
        "assetcore.services.imm12.detect_chronic_failures",
        # ...
    ],
}
```

**Vòng 3 — Notification E3 (Incident created):** `hooks.py::doc_events["Incident Report"]["after_insert"] = "assetcore.services.notifications.notify_incident_created"` — khi Incident vừa tạo → báo người phụ trách (`assigned_to`, fallback `reported_by`) qua Notification Log + email (per-user toggle). Audit = Notification Log (core). Spec đầy đủ: `docs/imm-00/04_Backend_Design.md §III.1b-2`.

### 7.1 SLA breach escalation engine (BR-12-09 / BR-12-10) — design SAU fix

> **ROOT CAUSE (Self-Correction):** `check_incident_sla_breach` (hourly, `imm12.py`) hiện set `response_breached`/`resolution_breached=1` + `_log()` audit nhưng **KHÔNG bắn notification nào** — incident quá hạn chìm vào log câm. Reference impl đã có ở IMM-09: `notifications.run_sla_breach_scan()` (state-change 0→1 + `_dispatch`). IMM-12 phải áp cùng pattern, KHÔNG đổi hành vi IMM-09.

**Recipient resolution (SSoT, không hardcode role) — hàm mới `_incident_sla_recipients(incident: dict, severity: str) -> list[str]`:**

Recipient = union (dedupe, loại `Administrator` + empty) của:

| Nguồn | Field / SSoT | Ghi chú |
|---|---|---|
| Người phụ trách incident | `incident["assigned_to"]` | primary; nếu trống → fallback `incident["reported_by"]` (Incident Report KHÔNG có field `supervisor` — khác WO; xác minh trên `incident_report.json`) |
| Escalation L1 từ policy | `policy["escalation_l1_user"]` | `get_sla_policy(_severity_to_sla_priority(severity))` đã trả field này (imm00.py:251) — TRƯỚC fix imm12 CHƯA dùng |
| Escalation L2 từ policy | `policy["escalation_l2_user"]` | như trên |
| **NĐ98 gate (BR-12-10)** | `notify_roles.QA_OFFICER` + `notify_roles.OPS_MANAGER` → `get_users_with_role(...)` | CHỈ khi `severity ∈ {Critical, High}`; thêm KỂ CẢ khi policy không set escalation_l*_user |

- Role-name lấy từ **`services/shared/notify_roles.py`** (anti RBAC-dead-gate) — KHÔNG literal trong imm12. Cần **bổ sung block escalation incident** vào notify_roles (xem dưới).
- `_incident_sla_recipients` trả `[]` ⇒ caller set cờ + ghi entry phát hiện như cũ, **KHÔNG** bắn, KHÔNG ghi entry escalated, KHÔNG crash.

**notify_roles SSoT — bổ sung (delta cho `services/shared/notify_roles.py`):**
```python
# Người nhận escalation SLA của Incident (IMM-12) — NĐ98 gate cho Critical/High.
INCIDENT_ESCALATION_QA: list[str] = QA_OFFICER      # ["Compliance Manager"]
INCIDENT_ESCALATION_OPS: list[str] = OPS_MANAGER    # ["Maintenance Manager"]
# → thêm cả 2 vào ALL_NOTIFY_ROLES (guard test test_notify_roles_exist phủ tự động).
```
> Tái dùng role THẬT đã khai báo (`QA_OFFICER`/`OPS_MANAGER`) — không sinh role-name mới. ALL_NOTIFY_ROLES đã chứa các role này nên guard `test_tc_r21_01` vẫn xanh; alias khai báo riêng để escalation incident có điểm cấu hình độc lập (đúng pattern `CAPA_ESCALATION_MANAGER`).

**Content (tiếng Việt, phân biệt 2 loại breach) — dựng trong `check_incident_sla_breach`:**

| Loại | Trigger | Subject | Message (HTML) |
|---|---|---|---|
| response-breach | `response_breached 0→1` | `VI PHẠM SLA (tiếp nhận): Sự cố <name>` | `Sự cố <b><name></b> trên thiết bị <b><asset_name></b> CHƯA được tiếp nhận và đã quá hạn <b><N> giờ</b> (hạn tiếp nhận: <response_due_at>). Mức độ: <severity VI>. Vui lòng tiếp nhận khẩn.` |
| resolution-breach | `resolution_breached 0→1` | `VI PHẠM SLA (xử lý): Sự cố <name>` | `Sự cố <b><name></b> trên thiết bị <b><asset_name></b> CHƯA được đóng và đã quá hạn xử lý <b><N> giờ</b> (hạn xử lý: <resolution_due_at>). Mức độ: <severity VI>. Vui lòng xử lý khẩn.` |

- `<N>` = số giờ quá hạn = `round((now - due_at).total_seconds()/3600, 1)`.
- `<asset_name>` enrich qua `_enrich_asset_names` / `frappe.db.get_value("AC Asset", asset, "asset_name")`; `<severity VI>` qua map VI đã có (vd `_SEVERITY_VI`).
- Bắn qua `notifications._dispatch(recipients, subject, message, doc_like)` với `doc_like = frappe._dict(doctype=_DT_INCIDENT, name=incident["name"])` → in-app (Notification Log) + email per-user toggle + deep-link. **1 notification / 1 loại breach** (nếu cả 2 cờ cùng 0→1 trong 1 lần quét ⇒ 2 notification, mỗi loại 1).

**Idempotency (anti-spam — chính cờ làm khoá):**
- Khoá = `response_breached` / `resolution_breached` (Check trên `Incident Report`, bền vững DB).
- Trong vòng quét, mỗi loại CHỈ bắn khi cờ tương ứng đang `0` VÀ điều kiện quá hạn đúng ⇒ set `1` + bắn ĐÚNG 1 lần (set cờ và bắn trong cùng nhánh).
- Lần quét kế: cờ đã `=1` ⇒ nhánh không vào ⇒ KHÔNG bắn lại. **Sweep 2 lần liên tiếp ⇒ tổng số notification không đổi** (TC bắt buộc).
- KHÔNG dùng Notification Log dedupe cho breach (cờ DB rẻ & chắc hơn) — khớp pattern IMM-09 §III.1b-6.

**Audit (BR-12-05, KHÔNG thay thế):**
- Giữ nguyên `_log(... "SLA breach (<kinds>) phát hiện bởi scheduler" ...)` (entry phát hiện hiện có).
- Sau khi `_dispatch` thành công cho ≥1 recipient → ghi THÊM `_log(... f"SLA breach escalated → {', '.join(recipients)}" ...)`.

**Per-incident an toàn (batch resilience):**
- Vòng `for row in candidates` bọc `try/except` mỗi incident: lỗi (thiếu policy / recipient resolve fail) → `frappe.log_error` + `continue`, KHÔNG dừng batch, KHÔNG rollback các incident đã xử lý.
- `frappe.db.commit()` 1 lần cuối batch nếu có thay đổi (giữ như hiện tại).

**Return value (mở rộng, không breaking):** `{"response_breached": int, "resolution_breached": int, "escalated": int}` — `escalated` = số incident đã bắn ≥1 notification.

**Regression guard:** KHÔNG đụng `notifications.run_sla_breach_scan()` (Asset Repair / IMM-09). Tái dùng `_dispatch` + `get_users_with_role` từ `notifications.py` qua import (lazy import trong imm12 để tránh circular).

> `check_capa_overdue` và `detect_chronic_failures` đăng ký trong `scheduler_events.daily` (không phải cron riêng) — Frappe sẽ chạy 1 lần/ngày tại khung scheduler tick mặc định.

---

## 8. Integration Points

| System | Direction | Method | Notes |
|---|---|---|---|
| IMM-00 Foundation | Outbound (call) | Python import | CAPA, Audit, Lifecycle |
| IMM-09 Repair | Link | DocType Link field | `repair_wo` on Incident Report |
| IMM-13 Risk Register | Event | Webhook (Sprint 12.5) | `chronic.detected` event |
| Email (Frappe) | Outbound | `frappe.sendmail()` | Critical alert + CAPA overdue |
| IMM-15 Vigilance | Event | Webhook (Sprint 12.5) | `incident.created` event |

---

## 9. Non-Functional

| Category | Requirement | Implementation |
|---|---|---|
| Idempotency | `acknowledge/resolve/close`: repeat call → return current state | Check status before transition |
| Concurrency | No double-acknowledge | DB-level status check + ValidationError |
| Chronic detection | Idempotent | Guard: `frappe.db.exists("IMM RCA Record", {status in ["RCA Required", "RCA In Progress"]})` |
| Logging | All errors logged to Frappe error log | `frappe.log_error()` in `_handle()` |
| Performance | List query < 500ms p95 | Index on `(asset, fault_code, reported_at)` + `(severity, status)` |

---

## DoD — File 04 hoàn chỉnh

- [x] Architecture overview (3-tier với LIVE/Pending rõ)
- [x] DocType: Incident Report custom fields + indexes + permission query
- [x] DocType: RCA Record full field table
- [x] Workflow states + transitions table
- [x] Service layer: function signatures + `report_incident` full code
- [x] Service layer: `detect_chronic_failures` full code (SQL + idempotency)
- [x] API layer: `_handle` pattern + 5 endpoints
- [x] Audit trail table (7 events)
- [x] Scheduler table + hooks.py registration
- [x] Integration points table
- [x] Non-functional (idempotency, concurrency, logging)
- [x] ✅ `services/imm12.py` — fully implemented
- [x] ✅ `api/imm12.py` — 14 endpoints live
- [x] ✅ DocType JSONs: incident_report, imm_rca_record, imm_capa_record, imm_rca_five_why_step, imm_rca_related_incident
- [ ] Reviewed bởi BE Lead
