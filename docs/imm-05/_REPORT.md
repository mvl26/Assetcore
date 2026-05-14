# IMM-05 — Báo cáo Light-touch Curation

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator`
- Chiến lược: **Light-touch CỰC NHẸ** (theo gap audit iter-1: IMM-05 ✅ Đầy đủ)

## 1. Trạng thái

IMM-05 đã **đầy đủ** 9 file (README + 02–09) theo template chuẩn v4.1+. Không cần sinh mới hay rewrite.

## 2. Thay đổi đã thực hiện

| File | Thay đổi |
|---|---|
| `README.md` | Cập nhật `Cập nhật cuối` 2026-05-08 → **2026-05-10**. Append 3 dòng metadata thiếu: `Khối kiến trúc = B. KHỐI 2`, `Đợt triển khai = 1`, `Owner = PTP Khối 2 · Tổ HC-QLCL`. Giữ nguyên schema cột cũ (Module/Wave/Trạng thái/Số file/Cập nhật cuối) — không đổi tên cột. |
| `02_Analysis_Design.md` … `09_Release.md` | **Không chạm** (light-touch). |

## 3. Quan sát (KHÔNG tự sửa — báo để user quyết)

- **Tên module lệch giữa nguồn**: README hiện ghi *"Hồ sơ thiết bị (Asset Documents)"* trong khi user prompt và Architecture (`Ho_so_kien_truc_IMMIS.md`) dùng *"Đăng ký, cấp phép và hồ sơ"*. Theo light-touch (§3 — không sửa heading wording cũ khi không có yêu cầu rõ ràng), giữ nguyên. Khuyến nghị BA quyết: hợp nhất tên module trong toàn bộ 9 file IMM-05 + Architecture + fixtures.
- **Roadmap còn 3 mục `[ ]` chưa tick** ở README (07/08/09) trong khi 3 file đó đã tồn tại và bảng map đánh ✅. Có thể là legacy roadmap chưa cập nhật. Khuyến nghị tick `[x]` 3 mục này hoặc xoá khi BA xác nhận content 3 file đã đạt.
- **Field `Wave`** trong metadata cũ vs `Đợt triển khai` mới: hiện cùng có cả 2 (Wave=1, Đợt=1) — đồng nghĩa nhưng trùng lặp. Để user/BA quyết đơn nhất hoá.

## 4. Việc còn lại

Không có. Module sẵn sàng cho assetcore-be-module / assetcore-fe-module sử dụng làm input.

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/dod-verification-report.md §1 for per-module results
- Status: READY

## 2026-05-14 Light-touch Sync (Wave-2 branch)
- `02_Analysis_Design.md`: replace tất cả `Pending_Review` (underscore) → `Pending Review` (space) — đồng bộ ground truth `services/imm05.py:DocState.PENDING_REVIEW = "Pending Review"` và `imm_05_document_workflow.json`.
- `05_API_Specification.md`: rewrite `DocumentWorkflowState` enum dùng space; fix 2 step description (`approve_document` / `reject_document`) tham chiếu state.
- `06_Frontend_Design.md`: fix `DocState`/`BADGE_MAP`/`pendingReviewDocs` filter dùng space; rename mọi reference store `imm05Store.ts` → `imm05.ts` (file thực tế).
- Không đụng `04_Backend_Design.md` (đã đúng — dùng "Pending Review" space).
- Không đụng `03/07/08/09` (light-touch).

## Pass 2 — Deep reconciliation (2026-05-14)

Endpoint count actual = **15** (whitelist `assetcore/api/imm05.py` — pass 1 sai khi đếm 14). LOC service = 561, LOC api = 151. Catalog thiếu `submit_for_review`.

- `README.md`: "14 endpoints" → "15 endpoints".
- `02_Analysis_Design.md`: BR-05-04 đổi `Clinical_Release` → `"Clinical Release"`.
- `04_Backend_Design.md`: §7 Scheduler — sửa file path `assetcore/tasks.py` → `assetcore/services/imm05.py`; chỉ rõ `check_document_expiry` là job duy nhất đăng ký; đánh dấu `update_asset_completeness` + `check_overdue_document_requests` *(Not yet implemented)*. §8.2 doc_events viết lại đúng ground truth (`Asset Document.on_update` → `imm16.eval_imm05_realtime`, không có entry IMM-05 riêng).
- `05_API_Specification.md`: catalog thêm hàng #5 `submit_for_review`; renumber 6–15; thêm spec §2.4b `submit_for_review`; DoD "14 endpoints" → "15 endpoints".
- `06_Frontend_Design.md`: untouched (đã đúng sau pass 1).
- `07_Testing_QA.md`: thêm callout — service layer đã có (561 LOC); test scaffold gộp 1 file `test_imm05.py` (237 LOC); pyramid "14 endpoints" → "15 endpoints".
- `08_Deployment.md`: sửa 4 chỗ `assetcore.tasks.check_document_expiry`/`update_asset_completeness` → namespace thực `assetcore.services.imm05.*` hoặc đánh dấu chưa wire.
- `09_Release.md`: row endpoint 14 → 15 (kèm tên hàm thực); LOC thay đổi từ ước tính sang con số thật; thêm row `Scheduler thực tế = 1`.
- `03_Diagrams.md`: untouched (đã dùng "Pending Review" space sau pass 1).
