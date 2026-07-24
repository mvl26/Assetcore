# ADR — `status` vs `workflow_state` (dual-track state fields)

> ## ⛔ SUPERSEDED (2026-07-22)
>
> ADR này **đã bị thay thế** bởi [`ADR-CORE-01_workflow_is_ssot.md`](ADR-CORE-01_workflow_is_ssot.md)
> — "Workflow engine của Frappe là SSoT trạng thái duy nhất".
>
> **Giữ lại làm hồ sơ lịch sử. KHÔNG dùng làm căn cứ thiết kế mới.**
>
> Lý do thay thế (chi tiết + số liệu ở ADR-CORE-01 §Bối cảnh): quyết định "không hợp nhất"
> dưới đây đã dẫn tới 75 chỗ bảng transition chép tay ở 10 file service, các invariant test
> dual-track chỉ để canh lệch, lớp vá "lockstep sync" (ADR-IMM-16-05), 84 chỗ
> `frappe.db.set_value` bỏ qua workflow engine, và bug "QTV đủ quyền vẫn không duyệt được".
>
> Hai khẳng định dưới đây cũng **sai về mặt dữ kiện** khi đo lại ngày 2026-07-22:
> - "Mô hình 1 — `workflow_state` vestigial": thực tế **cả 4 workflow của Mô hình 1 đều
>   `is_active = 1`** (`imm_08/09/11/12_*.json`) và giá trị enum `status` **trùng khớp
>   hoàn toàn** tên state của workflow ⇒ đây là **desync**, không phải "hai mô hình".
> - Bảng ADR không nhắc `AC Asset`, trong khi `ac_asset_lifecycle_workflow.json` bind
>   `workflow_state_field = "lifecycle_status"` ⇒ AC Asset có **3** trục trạng thái.

| Mục | Giá trị |
|---|---|
| Loại | Architecture Decision Record (cross-cutting) |
| Phạm vi | 10 doctype mang ĐỒNG THỜI `status` + `workflow_state` |
| Trạng thái | ~~Accepted~~ → **Superseded by ADR-CORE-01** (2026-07-22) |
| Quyết định bởi | BA + Tech Lead (Software Factory vòng 19) |
| Cập nhật | 2026-06-02 · superseded 2026-07-22 |

## Bối cảnh

10 doctype nghiệp vụ khai báo CẢ HAI field state: `status` (Select) và
`workflow_state` (Link → Workflow State). Frappe tự sinh `workflow_state` khi
một Workflow được gắn vào doctype; còn `status` là field nghiệp vụ do service
layer điều khiển. Việc tồn tại song song gây mơ hồ: FE/đối tác đọc field nào?

Khảo sát code + dữ liệu live (vòng 16–18) cho thấy **hai mô hình khác nhau**, và
một field vestigial gây lệch dữ liệu thật (Incident: `status=Acknowledged` nhưng
`workflow_state=Open`).

## Quyết định

**KHÔNG hợp nhất về một field duy nhất toàn hệ thống.** Mỗi doctype tuyên bố
RÕ field nào là **source-of-truth (SoT)** theo 2 mô hình dưới đây. FE + báo cáo +
tích hợp **chỉ được đọc field SoT**; field còn lại hoặc được giữ đồng bộ, hoặc
được coi là vestigial và KHÔNG được hiển thị.

### Mô hình 1 — `status` là SoT (doctype vận hành Wave-1)

Service drive `doc.status` qua state-machine nội bộ (`_VALID_TRANSITIONS`).
`workflow_state` **vestigial** (service không cập nhật) → KHÔNG đọc, KHÔNG hiển thị.

| Doctype | Module | SoT | `workflow_state` |
|---|---|---|---|
| Incident Report | IMM-12 | `status` | vestigial (stale) |
| PM Work Order | IMM-08 | `status` | vestigial |
| IMM Asset Calibration | IMM-11 | `status` | vestigial |
| Asset Repair | IMM-09 | `status` | vestigial |

Bằng chứng: service `imm08/09/11/12` chỉ ghi `.status` (20–31 lần/file), KHÔNG ghi
`.workflow_state`. FE các module này đã đọc đúng `status`.

### Mô hình 2 — `workflow_state` là SoT, `status` là rollup (doctype governance)

`workflow_state` là máy trạng thái chi tiết (nhiều state); `status` là tóm tắt
nghiệp vụ cấp cao, được service **giữ đồng bộ** mỗi lần chuyển state. Hai field
khác giá trị là HỢP LỆ (vd CAPA `workflow_state=Investigating` ⇒ `status=In Progress`).

| Doctype | Module | SoT | `status` (rollup) |
|---|---|---|---|
| IMM CAPA Record | IMM-16 | `workflow_state` | Open/In Progress/Closed/Overdue |
| IMM Compliance Finding | IMM-16 | `workflow_state` | rollup |
| IMM Internal Audit | IMM-16 | `workflow_state` | rollup |
| IMM Management Review | IMM-16 | `workflow_state` | rollup |
| IMM RCA Record | IMM-12 | `status` (đồng bộ) | — *(service ghi cả 2, giữ khớp)* |
| IMM Stock Cycle Count | IMM-15 | `workflow_state` | rollup |

Bằng chứng: service `imm15/imm16` ghi cả `.workflow_state` lẫn `.status`; dữ liệu
live cho thấy 35/46 CAPA có 2 field khác nhau **by design** (không phải bug).

## Hệ quả / Hành động

1. **FE rule (bắt buộc):** mỗi view đọc đúng field SoT của doctype đó. Badge/stepper
   localize từ field SoT (xem `frontend/src/constants/labels.ts`).
2. **Incident Report `workflow_state` vestigial:** chọn 1 trong 2 — (a) gỡ field khỏi
   form/UX và đánh dấu deprecated, hoặc (b) wire service cập nhật song song. Khuyến
   nghị **(a)** vì `status` đã là SoT đầy đủ và có audit trail; wiring thêm chỉ tăng
   bề mặt lỗi. Cùng lý do áp dụng cho PM WO/Calibration/Asset Repair.
3. **Tài liệu module:** mỗi `docs/imm-XX/03_Diagrams.md` / `04_Backend_Design.md`
   ghi rõ field SoT khi mô tả state machine.
4. **Test guard:** với doctype Mô hình 1, không assert `workflow_state` trong test
   workflow (nó vestigial); assert `status`. Với Mô hình 2, assert `workflow_state`.

## Không thuộc phạm vi

- Không đổi schema trong vòng này (chỉ tài liệu hoá + định hướng). Việc gỡ field
  vestigial là task riêng, cần migration cân nhắc dữ liệu cũ.
