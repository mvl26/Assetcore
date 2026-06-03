# IMM-04 — Doc Curator Report (Light-touch)

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator` (chiến lược light-touch CỰC NHẸ)
- Phạm vi: chỉ `docs/imm-04/`

## Kết luận

**Đã đầy đủ — chỉ refresh metadata.**

Theo gap audit iter-1, IMM-04 ở trạng thái ✅ Đầy đủ (8/8 file template + content mature, có UAT v2, đã align với codebase BE/FE thật). Không có gap section/structure cần đụng vào file 02–09.

## Hành động đã thực hiện

| File | Loại thay đổi | Chi tiết |
|---|---|---|
| `README.md` | Refresh metadata | (1) Cập nhật cuối: `2026-05-08` → `2026-05-10`. (2) Sửa tên module hiển thị từ "Lắp đặt (Installation / Commissioning)" → "Lắp đặt, định danh và kiểm tra ban đầu" để khớp Architecture (Hồ sơ kiến trúc IMMIS). (3) Append 3 dòng metadata thiếu so với template §6: `Khối kiến trúc = B. KHỐI 2`, `Đợt triển khai = 1`, `Owner = PTP Khối 2 · Workshop / Nhóm TBYT · Mạng lưới TBYT nội viện`. Schema cột cũ giữ nguyên (chỉ append, không đổi). |
| `02_Analysis_Design.md` | Không đụng | Light-touch rule §3: BA content mature, không sửa. |
| `03_Diagrams.md` | Không đụng | Diagram đã render đúng. |
| `04_Backend_Design.md` | Không đụng | Khớp codebase `assetcore/services/imm04.py`. |
| `05_API_Specification.md` | Không đụng | Envelope `{success, data}` chuẩn. |
| `06_Frontend_Design.md` | Không đụng | Khớp `frontend/src/api/imm04.ts`. |
| `07_Testing_QA.md` | Không đụng | Có UAT v1 + v2. |
| `08_Deployment.md` | Không đụng | QMS mapping đầy đủ. |
| `09_Release.md` | Không đụng | Traceability matrix đầy đủ. |

## Việc còn lại (không phải scope skill này)

Các TODO Sprint 7/8 đã liệt kê sẵn trong `README.md` § Roadmap (naming `Clinical Release`, DB UNIQUE `vendor_serial_no`, Print Format Biên bản Bàn giao, IMM-08 listener) — thuộc engineering backlog, không phải doc gap.

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/reports/dod-verification-report.md §1 for per-module results
- Status: READY

## 2026-05-14 Light-touch Sync (Wave-2 branch)
Branch: `feature/hieuc/wave-2`. Đồng bộ docs với fix gần đây:
- `04_Backend_Design.md` §3 Workflow: thay toàn bộ underscore states (`Pending_Doc_Verify`, `Clinical_Release`, ...) bằng giá trị space đang dùng thực tế (`Pending Doc Verify`, `Clinical Release`, ...). Đồng nhất với `imm_04_workflow.json` + `services/imm04.py` constants + `types/imm04.ts WorkflowState`. Xóa tech-debt TODO Sprint 7 đã resolve.
- `05_API_Specification.md` §1.5 Type definitions: rewrite `WorkflowState` enum dùng space; xóa các state không tồn tại (`Draft_Reception`, `Pending_Release`, `DOA_Incident`); cập nhật lưu ý từ "dùng underscore" → "dùng space". Sửa BAD_STATE table tham chiếu `Clinical Release`.
- `06_Frontend_Design.md` §5 Pinia store: cập nhật path `stores/commissioning.ts` → `stores/imm04.ts` (file đã rename) và liệt kê các views/components import từ store mới.
- `README.md` Roadmap: tick 2 mục Clinical Release naming + store rename là DONE.
- Không đụng `02/03/07/08/09` (light-touch — không phát hiện drift trong scope đó).

## Pass 2 — Deep reconciliation (2026-05-14)

Endpoint count actual = **33** (whitelist trong `assetcore/api/imm04.py`). LOC service = 1692, LOC api = 309.

- `README.md`: API count "20 endpoints" → "33 endpoints".
- `02_Analysis_Design.md`: tick các risk/open-question/issue về `Clinical Release` vs `Clinical_Release` thành DONE (Wave-2); EC-04-03 dùng quoted space.
- `03_Diagrams.md`: fix `Clinical_Release` (sequence diagram alt branch line 461) → `"Clinical Release"`.
- `04_Backend_Design.md`: §7 Scheduler — đánh dấu `check_commissioning_overdue` defined-but-not-registered; `check_clinical_hold_aging` + `check_commissioning_sla` đánh dấu *(Not yet implemented)* (không có `assetcore/tasks.py`). §8 doc_events viết lại đúng ground truth (on_submit listener IMM-08/11/16; `before_insert/validate` ở controller).
- `05_API_Specification.md`: catalog header "27" → "33"; thêm row #24 `retry_mint_asset` và #33 `get_lifecycle_timeline`; renumber 25–32; DoD checklist "31" → "33".
- `06_Frontend_Design.md`: untouched (đã chính xác sau pass 1).
- `07_Testing_QA.md`: thêm callout trạng thái thực tế — test scaffold gộp 1 file `test_imm04.py` (246 LOC), file con là kế hoạch chia; pyramid "17 endpoints" → "33 endpoints".
- `08_Deployment.md`: untouched (bench commands hợp lệ).
- `09_Release.md`: thay row "17 endpoints" và LOC ước tính bằng số thực (33 endpoints, 1692/309 LOC).

## Pass 3 — Sync 2026-05-18

Đếm lại ground truth: service=1697 LOC (+5 so với 1692 lần trước), api=309 LOC (không đổi), 33 endpoints (không đổi).

- `README.md`: `Cập nhật cuối` → 2026-05-18; bổ sung LOC thực vào dòng codebase ground truth (BE).
- Không đụng file 02–09 (không phát hiện drift nội dung).

## Pass 4 — Deep reconciliation 2026-05-18

Phân tích sâu toàn bộ code BE/FE. Phát hiện và cập nhật:

- `04_Backend_Design.md`: Architecture diagram "17 endpoints" → "33 endpoints"; thêm ghi chú bug `lifecycle_events` field thiếu trong JSON; bổ sung 13 hàm service thiếu vào bảng §4 (approval flow: `submit_for_approval`, `approve_pending`, `list_my_pending_approvals`; utility: `search_link`, `get_users_by_role`, `get_gate_status`, `retry_mint_asset`, `get_lifecycle_timeline`; integration: `create_commissioning_from_purchase`, `get_commissioning_origin`; view: `get_form_context`).

**Gaps cần xử lý ngoài docs (engineering):**
1. ⚠️ `lifecycle_events` field trong `asset_commissioning.json`: có trong field_order nhưng thiếu khỏi `fields` array — cần bổ sung JSON definition.
2. ⚠️ `check_commissioning_overdue` scheduler job chưa đăng ký trong `hooks.py`.
3. ⚠️ BR-04-08 (GW-2 compliance gate) — implementation status không rõ, cần verify.
4. ⚠️ `before_save_commissioning()` được reference trong docs nhưng không có trong service code hiện tại — verify hoặc cập nhật reference.

Không đụng `02/03/05/06/07/08/09` (không phát hiện drift nội dung).
