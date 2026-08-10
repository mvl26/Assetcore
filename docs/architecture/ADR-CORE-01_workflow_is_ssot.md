# ADR-CORE-01 — Workflow engine của Frappe là SSoT trạng thái duy nhất

| Mục | Giá trị |
|---|---|
| Loại | Architecture Decision Record (cross-cutting, nền tảng) |
| Trạng thái | **Proposed** — chờ triển khai theo `PLAN_core_refinement_tasks.md` |
| Ngày | 2026-07-22 |
| Phạm vi | 22 doctype có Workflow `is_active=1` + toàn bộ `services/imm*.py` |
| **Supersede** | `ADR_status_vs_workflow_state.md` (Accepted 2026-06-02) |
| Spec gốc | `SPEC_core_refinement_frappe_native.md` §5 |

---

## Bối cảnh

ADR trước (`status` vs `workflow_state`, 2026-06-02) quyết định **KHÔNG hợp nhất**: mỗi
doctype tự tuyên bố field nào là SoT, chia làm 2 mô hình, trong đó **Mô hình 1** coi
`workflow_state` là *vestigial* cho 4 doctype vận hành Wave-1 (PM Work Order, Asset
Repair, IMM Asset Calibration, Incident Report).

Sau ~1.5 tháng vận hành quyết định đó, chi phí đã bộc lộ rõ và **đo được**:

| Hệ quả | Bằng chứng trong repo |
|---|---|
| Mỗi module phải tự đẻ bảng transition chép tay | **75 chỗ** `_VALID_TRANSITIONS` / `_ALLOWED_TRANSITIONS` trong **10 file** `services/imm*.py` |
| Phải viết invariant test dual-track để canh lệch giữa bảng chép tay và workflow json | `TestAllocationAllowedTransitions` (IMM-15 §VI.1.1), `_CYCLE_EXCEPTION_EDGES` (§VI.2.1) |
| Desync trở thành bug thật, phải vá bằng "lockstep sync" | ADR-IMM-16-05: `workflow_state` đọng `'Open'` vĩnh viễn trong khi `status` marches ⇒ phải `db.set_value` cả 2 field |
| Ghi trạng thái bỏ qua engine ⇒ bỏ qua hook/permission/Version | **84 chỗ** `frappe.db.set_value` trong `services/`; `apply_workflow` chỉ **42 chỗ / 9 file** |
| Lỗi cấu hình workflow **câm lặng**, chỉ lộ ra khi người dùng bấm nút | Bug "QTV đủ quyền vẫn không duyệt được" — 2 root cause riêng biệt (transition-role thiếu; `doc_status='1'` trên doctype non-submittable) |
| FE buộc suy diễn `status === '...'` | Phải ra luật GATE-8 / LL-FE-51 để cấm hardcode |

Nói ngắn: mô hình cũ **tắt bộ máy trạng thái của Frappe rồi tự dựng lại bộ máy đó bằng
tay ở 10 file**, và trả giá bằng một chuỗi lớp vá chồng lên nhau.

### Dữ kiện mới (đo 2026-07-22) làm đảo ngược cán cân chi phí

1. **Giá trị `status` TRÙNG KHỚP HOÀN TOÀN tên state của workflow ở 10/12 doctype**
   (PM Work Order, Asset Repair, IMM Asset Calibration, Incident Report, IMM RCA Record,
   IMM Stock Cycle Count, IMM Spare Allocation, IMM Compliance Finding, IMM Internal
   Audit, IMM Management Review). Hợp nhất vì thế là **ánh xạ 1-1**, không phải thiết kế lại.
2. **`AC Asset` đã bind workflow vào `lifecycle_status`** (`workflow_state_field =
   "lifecycle_status"` trong `ac_asset_lifecycle_workflow.json`) — tức trục đúng đã tồn tại;
   `status` chỉ là tàn dư registry.
3. **Site `miyano` có 0 record** ở PM WO / Repair / Calibration / Incident / Commissioning /
   Document / CAPA ⇒ chi phí di trú dữ liệu trên môi trường phát triển gần bằng 0.
4. 10/12 doctype đã có `status` `read_only: 1` ⇒ chỉ service ghi, người dùng không ghi.

## Quyết định

**Hợp nhất về một trục trạng thái duy nhất, do workflow engine của Frappe điều khiển.**

| Trục | Vai trò | Ai được ghi |
|---|---|---|
| `docstatus` | Tính bất biến (Draft / Submitted / Cancelled) | core, qua `submit()` / `cancel()` |
| `workflow_state` (hoặc field khai trong `workflow_state_field`, vd `lifecycle_status` của AC Asset) | **SSoT nghiệp vụ** | **CHỈ** `frappe.model.workflow.apply_workflow` |
| `status` | **Dẫn xuất, read-only** — rollup phục vụ FE/report/OAS/mobile | controller tính lại, không ai set tay |

Quy tắc thi hành:

1. **Một đường ghi duy nhất.** Mọi service chuyển trạng thái qua helper chung
   `assetcore.services.shared.state.transition(doc, action)` → gọi `apply_workflow`.
   Cấm `doc.status = ...` và `frappe.db.set_value(dt, name, "status", ...)`.
2. **`allowed_transitions` sinh từ engine** (`frappe.model.workflow.get_transitions`),
   gate thêm theo capability. **Xoá** 75 chỗ bảng transition chép tay và các invariant
   test dual-track đi kèm — chúng tồn tại chỉ để canh sự lệch mà quyết định này loại bỏ.
3. **`status` KHÔNG bị xoá.** Giữ nguyên tên field + nguyên enum hiện tại, chuyển thành
   dẫn xuất read-only. Đây là điều kiện khiến hợp nhất không làm vỡ FE / OpenAPI /
   mobile contract / test hiện có.
4. **Hai ngoại lệ rollup có chủ đích** (vocabulary khác workflow, giữ nguyên bản chất rollup):
   - `IMM CAPA Record.status` ∈ {Open, In Progress, Pending Verification, Closed, Overdue}
     ← ánh xạ từ 7 state workflow.
   - `AC Asset.status` (legacy registry) ← ánh xạ từ `lifecycle_status`.
   Ánh xạ khai báo **một chỗ** trong `services/shared/state.py`, có test phủ toàn bộ state.
5. **Doctype có `status` nhưng chưa có workflow** (14 cái, vd `Asset Transfer`,
   `Firmware Change Request`, `PM Schedule`, `IMM Recall Notice`): hoặc gắn workflow, hoặc
   tuyên bố `status` là derived + khoá `read_only: 1`. Không được để trục ghi-tay thứ hai.

## Hệ quả

**Tích cực**
- Cấu hình workflow sai không còn câm: engine ném lỗi tại chỗ, và static guard bắt trước khi lên môi trường.
- RBAC duyệt do transition của workflow quyết định — một nguồn, khớp với `backfill_workflow_admin`.
- Miễn phí: `Workflow Action` (hộp thư duyệt), lịch sử chuyển trạng thái, Version/audit, permission.
- Xoá được ~75 chỗ bảng chép tay + các invariant test dual-track ⇒ giảm bề mặt bug.

**Tiêu cực / rủi ro**
- Đụng 10 file service đang chạy thật ⇒ phải cắt **từng module một**, mỗi module có test hồi quy riêng.
- Cần patch backfill `workflow_state = status` cho site khách đã có dữ liệu (site dev = 0 record).
- Sửa `services/*.py` ⇒ cần USER reload gunicorn `--preload` mới thấy trên HTTP live.

**Không thuộc phạm vi**
- Không đổi tên field, không xoá field, không đổi giá trị enum ⇒ OpenAPI baseline không đổi.
- Không tái dùng master ERPNext.

## Kiểm chứng (test guard)

- `tests/test_state_axis_invariant.py` (static, có test tự-cắn):
  - doctype có workflow `is_active=1` ⇒ field SSoT của nó **không** có trục ghi-tay song song;
  - `status` của các doctype đó phải `read_only: 1`;
  - grep-guard: `frappe.db.set_value(... "status" ...)` chỉ được xuất hiện trong danh sách
    trắng đang thu hẹp dần, đạt **0** khi Phase 2 đóng.
- Test hồi quy per-module: chuyển trạng thái qua `transition()` cho ra đúng `workflow_state`,
  `status` và `docstatus`.

## Tham chiếu

- Bị thay thế: `ADR_status_vs_workflow_state.md`
- Bị ảnh hưởng (cần cập nhật khi cắt từng module): ADR-IMM-15-08, ADR-IMM-15-10, ADR-IMM-16-05
- Spec: `SPEC_core_refinement_frappe_native.md` · Kế hoạch: `PLAN_core_refinement_tasks.md`
