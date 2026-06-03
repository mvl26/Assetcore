# 06 — Frontend Design (IMM-14 Giải nhiệm thiết bị)

| Mục | Giá trị |
|---|---|
| Module | IMM-14 — Giải nhiệm thiết bị |
| Phạm vi | Sitemap + UI/UX + Cascade + Validation |
| Owner | FE Lead + UX Designer |
| Liên kết | [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) |

> Stack chuẩn AssetCore: **Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Query** (refer `.claude/skills/assetcore-fe-module/SKILL.md`). Design system tham chiếu `docs/res/design/design-frontend.md`.

---

## 1. Sitemap

```
/imm-14
├── /imm-14                    # List closure (mặc định status = active workflow states)
├── /imm-14/new                # Create closure — chọn Decommission Decision (IMM-13)
├── /imm-14/:closure_no        # Detail page (4 tab)
│   ├── tab Reconciliation     # Đối soát kho + kế toán + WO + docs
│   ├── tab Sanitization       # Checklist PII/PHI + ký DPO
│   ├── tab Documents          # Biên bản, scan, ảnh
│   └── tab Audit              # Lifecycle event + audit trail
├── /imm-14/dashboard          # Dashboard end-of-life
└── /imm-14/archived           # List asset đã decommissioned (read-only)
```

---

## 2. Trang List

- **Filter**: workflow_state, asset_no (autocomplete), năm, disposal_method, lý do (`reason_category`).
- **Cột**: Closure No, Asset No (link đến IMM-04 detail), Asset name, Workflow State (badge màu theo state), Reason, Disposal Method, Created By, Created On, Approved On.
- **Action bar**: New (HTM Engineer), Export (Auditor), Filter saved view.
- **Empty state**: "Chưa có closure record nào — bắt đầu từ Decommission Decision IMM-13".

---

## 3. Trang Create (Step Form 3 bước)

| Bước | Nội dung |
|---|---|
| 1. Pick decision | Combobox load Decommission Decisions ở state `Approved` mà chưa có closure active. Hiển thị asset_no, lý do. |
| 2. Snapshot review | Hiện asset summary (name, model, serial, location), purchase_value, book_value, lifecycle history tóm tắt. |
| 3. Confirm create | Tạo closure draft + redirect detail page tab Reconciliation |

Cascade fields: chọn `decision_no` → auto-fill `asset_no`, `reason`, `disposal_method` (cho phép user override sau).

---

## 4. Trang Detail — 4 tab

### 4.1. Tab Reconciliation

Bảng có 4 phân nhóm (collapsible card):

- **A. Work Order còn mở** (scope=`work_order`): list WO PM/CM/Calib chưa đóng. Action: "Đóng WO" (link IMM-08/09/11) hoặc "Transfer".
- **B. Phụ tùng tồn kho** (scope=`spare_stock`): list dòng IMM-15 stock. Action cho Storekeeper: chọn `decision = reuse | scrap | transfer` cho từng dòng.
- **C. Sổ tài sản** (scope=`book_value`): hiện `book_value` hiện tại, ô nhập `final_value`, ô chọn `disposal_method` (disposal/donation/sale/trade-in/internal_reassignment). Chỉ Accountant edit.
- **D. Hồ sơ pháp lý** (scope=`document`): list IMM-05 docs còn `active`. Mỗi dòng có nút "Mark archive-ready" (QLCL Officer).

Mỗi line có badge status: ⏳ pending / ✅ done / ⚠️ blocker.

### 4.2. Tab Sanitization

- Checklist 5–8 items theo template (load từ BE theo asset).
- Ô chữ ký DPO + nút "Ký xác nhận" (chỉ visible nếu user role = DPO).
- Trường note kèm timestamp.
- Nếu `asset.has_patient_data = false` → tab hiện chế độ "Không bắt buộc, vẫn nên ghi log" với template ngắn hơn.

### 4.3. Tab Documents

- Upload đa file (PDF, ảnh).
- Bảng hiện: file name, type (biên bản huỷ, biên bản giao nhận, ảnh hiện trạng, scan QĐ), uploaded by, uploaded at.
- Mỗi file mở preview inline.

### 4.4. Tab Audit

- Timeline workflow state transition.
- Bảng lifecycle event của asset (filter event của closure này).
- Liên kết `IMM Audit Trail` đầy đủ — chỉ-đọc.

### 4.5. Action bar

- **Submit for Approval** — visible khi state Reconciling và đủ 7 mục (BR-14-01).
- **Approve** — visible cho Department Head khi state Pending Approval.
- **Send back** — visible cho Department Head khi state Pending Approval.
- **Request Rollback** — visible khi state Closed và còn trong window.
- **Confirm Rollback** — visible cho Accountant khi state Rollback Requested.
- **Print Closure Report** — visible mọi state ≥ Pending Approval (PDF cho audit).

Disable action với guard tooltip giải thích lý do (vd "Còn 2 WO chưa đóng").

---

## 5. Pinia store (skeleton)

```typescript
// frontend/src/stores/imm14.ts (gợi ý — chốt sprint W3-2)
export const useClosureStore = defineStore('imm14_closure', {
  state: () => ({
    current: null as Closure | null,
    list: [] as Closure[],
    filters: { /* ... */ },
  }),
  actions: {
    async createFromDecision(decisionNo: string) { /* call api/imm14.ts */ },
    async finalize(closureNo: string) { /* ... */ },
    async requestRollback(closureNo: string, reason: string) { /* ... */ },
  },
});
```

API client: `frontend/src/api/imm14.ts` — wrap `frappe.call` theo pattern `assetcore-fe-module`.

TanStack Query keys:

- `['imm14', 'list', filters]`
- `['imm14', 'detail', closureNo]`
- `['imm14', 'dashboard', period]`

Invalidate khi mutate (finalize, rollback, sanitization sign).

---

## 6. Validation rules (FE-side, mirror BE BR)

| BR | Hiển thị |
|---|---|
| BR-14-01 (7 mục) | Action "Submit for Approval" disabled + tooltip checklist còn thiếu |
| BR-14-02 (SoD) | Action "Approve" hidden nếu `current_user = created_by` |
| BR-14-04 (rollback window) | Action "Request Rollback" disabled nếu quá window, tooltip ngày hết hạn |
| BR-14-05 (sanitization) | Tab Sanitization có badge ❗ nếu `has_patient_data` và chưa ký |
| BR-14-06 (asset lock) | Trang IMM-04 cho asset `decommissioned` ẩn nút Edit |
| BR-14-08 (phụ tùng) | Mục B reconciliation có badge ⚠️ nếu còn dòng pending |

Mọi validation FE chỉ là UX — BE phải re-validate (defense in depth).

---

## 7. Cascade fields

| Field cha | Field con auto | Nguồn |
|---|---|---|
| `decision_no` | `asset_no`, `reason`, `disposal_method` (initial) | IMM-13 Decommission Decision |
| `asset_no` | `gmdn_classification`, `has_patient_data`, `book_value`, `purchase_value` | AC Asset |
| `disposal_method` | template `Sanitization Item` (default) | Theo classification + method |
| `scope` (line) | required role (read/edit) | Permission map |

---

## 8. Dashboard (`/imm-14/dashboard`)

Card / chart:

- KPI card: số closure trong năm, % đầy đủ 7 mục, thời gian đóng trung bình, % rollback.
- Bar chart: số asset giải nhiệm theo tháng (tách theo disposal_method).
- Pie chart: lý do giải nhiệm (recall, end-of-life, repair-not-economical, donation, replaced).
- Table: top 10 asset có chi phí giải nhiệm cao nhất.
- Filter: năm, khoa, model.

Refer cách dashboard IMM-08 / IMM-12 đã implement (chia sẻ component).

---

## 9. Print Format — Closure Report

Template PDF: trang A4, header bệnh viện, 7 section khớp 7 mục bắt buộc + chữ ký 5 chỗ (HTM, Storekeeper, Accountant, DPO, Department Head). Footer: closure_no + watermark "AUDIT EVIDENCE — IMM-14".

Format file: `assetcore/print_format/imm_14_closure_report.json` *(scaffold sprint W3-3.)*

---

## 10. UX rules (must)

- Mọi action không thể đảo ngược (Approve, Confirm Rollback) → modal xác nhận 2 bước (text typing tên closure_no).
- Mọi error code BE → toast với message i18n + nút "Xem chi tiết" mở console log.
- Field tiền tệ format VND (1.000.000 đ), DPO sign timestamp format `dd/MM/yyyy HH:mm`.
- Empty list / loading / error states đầy đủ — không bao giờ trắng tinh.

---

*Hết file 06. Wireframe / mockup chi tiết sẽ vẽ trên Figma trong sprint W3-2 (refer `docs/ba/Phase_06_UX_Screen_Dashboard_Design`).*
