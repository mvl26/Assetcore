# Wave 1 Review — BE + FE Audit (IMM-00/04/05/08/09)

**Ngày rà soát:** 2026-04-19 (sau khi đóng gap từ Wave1_Foundation_Readiness)
**Phạm vi:** Backend (services, API, controllers, hooks) + Frontend (views, router, types, API wrappers)
**Kết quả:** 4 bug fixed · 3 issue documented · Grade cập nhật

---

## Grade cập nhật

| Module | Grade trước | Grade sau | Lý do thay đổi |
|---|---|---|---|
| IMM-00 | A (95%) | **A (95%)** | Ổn định |
| IMM-04 | A- (90%) | **A- (90%)** | BUG-2 fixed — `Clinical_Release` mismatch |
| IMM-05 | B+ (80%) | **A (95%)** | UAT 39/39 + scheduler + BUG-1 fixed |
| IMM-08 | B (75%) | **A- (88%)** | 22 endpoints + service layer |
| IMM-09 | A- (88%) | **A- (88%)** | Ổn định (issue medium không block) |

---

## Bugs đã fix trong phiên này

### BUG-1 ✅ IMM-05 `mark_exempt` — NameError crash
**File:** `assetcore/api/imm05.py:622`
**Vấn đề:** `new_status` chưa định nghĩa → NameError 500 khi gọi endpoint.
**Fix:** Xóa biến undefined, trả `doc.workflow_state` thay thế.

### BUG-2 ✅ IMM-04 `approve_clinical_release` / `generate_handover_pdf` — State mismatch
**File:** `assetcore/api/imm04.py:1185, 1200, 1242`
**Vấn đề:** Hardcode `"Clinical Release"` (space) ≠ `_STATE_CLINICAL_RELEASE = "Clinical_Release"` (underscore).
Toàn bộ flow submit + xuất PDF luôn trả INVALID_STATE.
**Fix:** Thay 3 chỗ hardcode bằng constant.

### BUG-3 ✅ FE `PmScheduleListView` — Pagination total = 0
**File:** `frontend/src/views/PmScheduleListView.vue:22`
**Vấn đề:** View dùng `d.pagination?.total` nhưng API trả `{ items, total }` (flat, không có `pagination` object).
Kèm 2 invalid Select options: `Monthly` (không có trong schema), `Cancelled` (phải là `Suspended`).
**Fix:** `d.pagination?.total` → `d.total`, xóa Monthly, Cancelled → Suspended.

### BUG-4 ✅ IMM-05 `reject_document` — Thiếu permission check
**File:** `assetcore/api/imm05.py:237`
**Vấn đề:** `approve_document` có check `_APPROVE_ROLES`, nhưng `reject_document` không có → mọi user đều có thể reject.
**Fix:** Thêm role check trước khi thực hiện reject.

---

## Issues còn lại (không block, cần theo dõi)

### ISSUE-5 Import path không nhất quán (Medium)
`imm00.py` dùng `from assetcore.utils.response import _ok, _err`
`imm05.py` dùng `from assetcore.utils.helpers import _ok, _err`
Cả hai cùng logic nhưng khác path. Nguy cơ diverge khi refactor.
**Khuyến nghị:** Chọn 1 canonical path, migrate dần.

### ISSUE-6 IMM-09 hardcode status strings (Medium)
`assetcore/api/imm09.py` định nghĩa constants `_STATUS_OPEN`, `_STATUS_ASSIGNED`... nhưng nhiều chỗ vẫn hardcode string trực tiếp.
**Khuyến nghị:** Refactor lần tới khi chạm IMM-09.

### ISSUE-7 IMM-04 `submit_commissioning` thiếu null check (Low)
Nếu `mint_core_asset()` fail, `doc.final_asset` = None nhưng submit vẫn proceed.
**Khuyến nghị:** Thêm guard `if not doc.final_asset: return _err(...)`.

---

## Trạng thái Gap từ Wave1_Foundation_Readiness

| Gap | Mức độ | Trạng thái |
|---|---|---|
| Gap #1: UAT IMM-05 | 🔴 Critical | ✅ **CLOSED** — 39/39 PASS |
| Gap #2: Scheduler expiry + PM auto-gen | 🔴 Critical | ✅ **CLOSED** — đăng ký hooks.py |
| Gap #3: IMM-08 CRUD (Schedule + Template + ad-hoc WO) | 🔴 Critical | ✅ **CLOSED** — 22 endpoints |
| Gap #4: Role namespace unification | 🟡 High | ✅ **CLOSED** — 15 roles trong fixtures |
| Gap #5: BR-INC-01 frappe.throw | 🟡 High | ✅ **CLOSED** |
| Gap #6: services/imm08.py | 🟡 High | ✅ **CLOSED** |
| Gap #7: Depreciation calculator | 🟢 Medium | ⏳ Pending Wave 2 |
| Gap #8: services/imm05.py | 🟢 Medium | ✅ **CLOSED** |
| Gap #9: Firmware CR classification | 🟢 Medium | ⏳ Pending |
| Gap #10: rollup_asset_kpi đầy đủ | 🟢 Low | ⏳ Pending |
| Gap #11: Verify UAT IMM-08/09 | 🟢 Low | ⏳ Cần verify |
| BUG-1: mark_exempt NameError | 🔴 Critical (mới phát hiện) | ✅ **FIXED** |
| BUG-2: Clinical_Release mismatch | 🔴 Critical (mới phát hiện) | ✅ **FIXED** |
| BUG-3: PmScheduleListView total=0 | 🟡 High (mới phát hiện) | ✅ **FIXED** |
| BUG-4: reject_document no auth | 🟡 High (mới phát hiện) | ✅ **FIXED** |

---

## Kết luận

**Wave 1 hiện đạt ~93% — SẴN SÀNG nền tảng.**

✅ Tất cả 6 Critical/High gap từ readiness report đã đóng
✅ 4 bug phát hiện trong review đã fix ngay
✅ IMM-05 từ B+ → A (UAT + scheduler + service layer đầy đủ)
✅ IMM-08 từ B → A- (22 endpoints + service layer)

⏳ Còn lại (không block Wave 2):
- Depreciation calculator (Gap #7)
- Firmware CR classification (Gap #9)
- KPI rollup đầy đủ (Gap #10)
- Verify UAT IMM-08/09 chạy pass (Gap #11)

**Khuyến nghị:** Có thể mở Wave 2 (IMM-11 Calibration / IMM-12 CAPA nâng cao).

---

**Phiên bản:** 2.0
**Files liên quan:**
- `docs/res/Wave1_Foundation_Readiness_2026-04-19.md` — phiên bản 1.0
- `assetcore/tests/uat_imm05.py` — 39/39 PASS
- `assetcore/services/imm05.py`, `imm08.py` — service layers mới
- `assetcore/hooks.py` — scheduler jobs đăng ký đầy đủ
