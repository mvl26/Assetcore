# docs/res — Tài liệu nghiên cứu & làm việc nội bộ

Thư mục này chứa **tài liệu phân tích, báo cáo kiểm thử, kế hoạch triển khai và nghiên cứu nội bộ** của AssetCore. Đây **không phải** bộ tài liệu module chuẩn (xem `docs/imm-XX/`) cũng không phải tài liệu khách hàng chính thức.

> Tổ chức theo thư mục con chủ đề. Một số file được tham chiếu trực tiếp từ code/test/skill/`imm-XX` qua đường dẫn đầy đủ — nếu di chuyển, **phải** cập nhật mọi referrer.

```
docs/res/
├── reports/      # Báo cáo kiểm thử, bug, hồi quy, DoD
├── rbac/         # Phân quyền: ma trận role, redesign, audit, user-scope
├── deployment/   # Hướng dẫn deploy & log vận hành
├── design/       # Design system & UI specs FE
├── frameworks/   # Framework & chuẩn kỹ thuật (error framework, code-alignment)
├── analysis/     # Phân tích domain (GMDN)
├── guides/       # Hướng dẫn sử dụng, import, nhật ký skill
├── customer/     # Tài liệu khách hàng (docx)
├── plans/        # Kế hoạch triển khai (theo ngày)
└── agents_old/   # Định nghĩa agent cũ (legacy, untracked)
```

---

## `reports/` — Báo cáo & Kiểm thử

| File | Nội dung | Ngày |
|---|---|---|
| `assetcore-bug-report.md` | Tổng kết lỗi kiểm thử v0.0.2 | 2026-05-26 |
| `assetcore-bug-report-20260527.md` | Kiểm thử toàn diện 13 module — 32 lỗi | 2026-05-27 |
| `assetcore-regression-report-v3.md` | Báo cáo kiểm thử hồi quy v3 | 2026-05-26 |
| `AssetCore_Test_Plan_NextRound_1_Analysis.md` | Phân tích Test Plan Round #1 — **canonical ref** (skills + `test_imm00.py`) | 2026-05-25 |
| `AssetCore_Test_Plan_NextRound_1.xlsx` | Test Plan Round #1 (bảng tính nguồn) | 2026-05-25 |
| `dod-verification-report.md` | DoD Verification Report — ref bởi 13 `imm-XX/_REPORT.md` | 2026-05-11 |

## `rbac/` — Phân quyền

| File | Nội dung | Ngày |
|---|---|---|
| `role-permission-matrix-realigned.md` | Ma trận phân quyền căn lại theo hệ thống hiện hành — **bản tham chiếu** | 2026-05-25 |
| `role-redesign-module-based.md` | Thiết kế lại RBAC module-based (analysis) — ref bởi `services/shared/rbac.py` | 2026-05-19 |
| `role-visibility-audit-2026-05-13.md` | Audit FE role/visibility | 2026-05-13 |
| `user-scope-filter-analysis.md` | Phân tích lọc user thuộc AssetCore — ref bởi `permissions.py`, `hooks.py` | 2026-05-28 |
| `role-permission-matrix-nd1-v2.xlsx` | Ma trận phân quyền BV Nhi Đồng 1 v2 (nguồn khách hàng) | 2026-05-25 |

## `deployment/` — Deploy & Vận hành

| File | Nội dung | Ngày |
|---|---|---|
| `cloud-deployment-guide.md` | Hướng dẫn deploy cloud | 2026-05-13 |
| `deployment-log.md` | Log deploy & troubleshooting | 2026-05-14 |

## `design/` — Design & UX

| File | Nội dung | Ngày |
|---|---|---|
| `design-frontend.md` | Design system & UI specs FE — ref bởi `docs/README.md`, `template`, ~8 `imm-XX` | 2026-05-07 |

## `frameworks/` — Framework & Chuẩn kỹ thuật

| File | Nội dung | Ngày |
|---|---|---|
| `miyano-error-framework.md` | Đặc tả Miyano Error Framework — ref bởi `utils/messages.py` | 2026-05-20 |
| `code-alignment-plan.md` | Kế hoạch căn chỉnh code Wave 1+2+IMM-00 — ref bởi `imm-06` | 2026-05-11 |

## `analysis/` — Phân tích domain

| File | Nội dung | Ngày |
|---|---|---|
| `gmdn-asset-category-analysis.md` | Phân tích mã GMDN trong danh mục tài sản — ref bởi `imm-00` (×11) + patch | 2026-05-19 |

## `guides/` — Hướng dẫn & Chiến lược

| File | Nội dung | Ngày |
|---|---|---|
| `usage-guide.md` | Hướng dẫn sử dụng (user flow guide) | 2026-05-11 |
| `import-strategy.md` | Chiến lược import dữ liệu hàng loạt — ref bởi `assetcore-import` skill | 2026-05-18 |
| `skill-updates-2026-05-27.md` | Nhật ký cập nhật skill | 2026-05-27 |

## `customer/` — Tài liệu khách hàng (docx)

| File | Nội dung |
|---|---|
| `customer-chuc-nang-assetcore-v1.0.docx` | Tài liệu chức năng AssetCore v1.0 |
| `customer-tai-lieu-giao-tiep-ky-thuat.docx` | Tài liệu giao tiếp kỹ thuật (phòng CNTT) |

> Tài liệu khách hàng phải tuân `CONVENTIONS.md §34` (verify-before-claim) trước khi gửi.

## `plans/` — Kế hoạch triển khai (theo ngày)

| File | Nội dung |
|---|---|
| `2026-05-19-drop-gmdn-status.md` | Bỏ `gmdn_status`, lọc theo `gmdn_code` |
| `2026-05-19-gmdn-code-sync-strategy.md` | Đồng bộ GMDN code: Category → Model → Asset |
| `2026-05-19-rbac-module-role-redesign.md` | Plan triển khai RBAC module-based |
| `2026-05-20-notification-error-standardization.md` | Chuẩn hoá Notification & Error (GĐ 1) |
| `2026-05-20-notification-error-standardization-phase2.md` | Chuẩn hoá Notification & Error (GĐ 2) |

## `agents_old/` — Định nghĩa agent cũ (legacy)

Snapshot 4 file `.agent.md` từ 2026-05-11. **Chưa track git**; giữ lại làm tham khảo. Bản agent đang dùng được đăng ký ở nơi khác.

---

## Lịch sử dọn dẹp

### 2026-05-29 (b) — Tổ chức theo thư mục con
Toàn bộ file gom vào 8 thư mục con chủ đề (`reports/`, `rbac/`, `deployment/`, `design/`, `frameworks/`, `analysis/`, `guides/`, `customer/`). Đã cập nhật ~60 tham chiếu đường dẫn trong `docs/imm-XX/`, `docs/template/`, `.claude/skills/`, và code (`.py`). Sửa 1 link tương đối hỏng sẵn trong `plans/2026-05-19-drop-gmdn-status.md`.

### 2026-05-29 (a) — Xóa & chuẩn hoá tên
**Đã xóa (superseded / không phải tài liệu):**
- `BUG_REPORT_AssetCore_27052026.md` (v1) → thay bởi `reports/assetcore-bug-report-20260527.md`
- `role-permission-matrix-generalized.md` → thay bởi bản realigned
- `gen_spec.py`, `gen_spec_v2.py` → script sinh spec một lần, không phải tài liệu

**Đã đổi tên (chuẩn hoá kebab-case):**
- `BUG_REPORT_AssetCore_v2_27052026.md` → `assetcore-bug-report-20260527.md`
- `Ma tran phan quyen Role version 2.xlsx` → `role-permission-matrix-nd1-v2.xlsx`
- `miyano_error_framework.md` → `miyano-error-framework.md`
- `Các chức năng Assetcore v1.0.docx` → `customer-chuc-nang-assetcore-v1.0.docx`
- `Tài liệu giao tiếp kỹ thuật (đã chỉnh sửa).docx` → `customer-tai-lieu-giao-tiep-ky-thuat.docx`
