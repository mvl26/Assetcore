# IMM-01 — Doc Curator Light-Touch Report

- Ngày chạm: 2026-05-10
- Skill: `assetcore-doc-curator` — chế độ light-touch
- Phạm vi: chỉ `docs/imm-01/` — không đụng module khác

## Files đã chạm

| File | Hành động | Section |
|---|---|---|
| `README.md` | append metadata + update | Bảng metadata: thêm 3 dòng mới `Khối kiến trúc = A. KHỐI 1`, `Đợt triển khai = 2`, `Owner = PTP Khối 1 · Nhóm KH-TC`; cập nhật `Cập nhật cuối` từ `2026-05-08` → `2026-05-10`. Heading `# IMM-01 — Tài liệu module` giữ nguyên. |
| `02_Analysis_Design.md` | bổ sung 3 section mới | I.0 Khảo sát hiện trạng (As-Is) — kéo từ WHO HTM *Needs assessment for medical devices* + Architecture line 244, 265, 268. I.7 Rủi ro & Biện pháp giảm thiểu — 8 risk dựa Pain points §II.2 + VR/G hiện có. I.8 Roadmap & Đợt triển khai — kéo Architecture line 276–278. |

## Sections KHÔNG chạm (theo light-touch rule §3 SKILL)

- I.1 Pitch — giữ nguyên.
- I.2 Vị trí trong WHO HTM lifecycle — giữ nguyên.
- I.3 Stakeholders & Actors — giữ nguyên (KHÔNG chạm dù gap audit có thể đề xuất chỉnh).
- I.4 Scope, I.5 KPI, I.6 Compliance — giữ nguyên.
- Phần II BPMN, III Use Case, IV Functional, V NFR — giữ nguyên hoàn toàn.
- Heading `# 02 — Phân tích thiết kế nghiệp vụ — IMM-01 Đánh giá Nhu cầu & Dự toán` — giữ nguyên wording.
- Heading `# IMM-01 — Tài liệu module` ở README — giữ nguyên.
- Toàn bộ `03_*.md`, `04_*.md`, `05_*.md`, `06_*.md`, `07_*.md`, `08_*.md`, `09_*.md` — KHÔNG chạm.

## Reserved items (cần user / BA quyết)

- README hiện dùng schema cũ với cột `Wave` thay vì `Đợt triển khai`, và `Trạng thái` thay vì `Trạng thái docs`. Light-touch rule cấm đổi tên cột → đã append cột mới chứ không thay thế. **Đề xuất user**: thống nhất schema (giữ song song hay chuẩn hoá thành 5 cột template chuẩn).
- Header file 02 dòng `> ⚠️ Module PLANNED — Wave 2. Chưa triển khai.` mâu thuẫn với README ghi `Wave 2 — Live ✅`. Light-touch không tự fix văn phong → **đề xuất user** xác nhận và remove dòng cảnh báo PLANNED.
- I.7 RSK-01-08 nhắc đào tạo role mới qua IMM-06 — verify khi IMM-06 BE/FE đầy đủ.
- I.8 chỉ mục Đợt 3 cho IMM-07/10/13/14/17 sẽ refine khi 5 module thiếu docs được sinh.

## Source mapping đã sử dụng

| Section mới | Source |
|---|---|
| I.0 As-Is | WHO HTM *Needs assessment for medical devices* (chương 2); Architecture line 244 (tên + scope IMM-01), line 265 (PTP Khối 1), line 268 (Nhóm KH-TC); QC-IMMIS-01 (Architecture §"Mã QC nền") |
| I.7 Risk | Pain points §II.2 (đã có), VR-01-01..06 + G01..G05 (đã có) — tổng hợp lại không bịa thêm constants |
| I.8 Roadmap | Architecture line 276–278 (Đợt 1/2/3 nguyên văn); §I.4 Dependencies (đã có) |

## Checklist light-touch

- [x] Không rewrite content cũ
- [x] Không đổi heading wording
- [x] Không đổi tên cột metadata cũ — chỉ append
- [x] Không chạm Pitch / Stakeholder / KPI
- [x] Không tạo file ngoài scope (chỉ `_REPORT.md` trong `docs/imm-01/`)
- [x] Mọi section mới có source thật, không bịa số liệu

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/dod-verification-report.md §1 for per-module results
- Status: READY
