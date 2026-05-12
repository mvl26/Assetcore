# IMM-15 — Doc Curator Light-touch Report

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator` (light-touch)
- Module: IMM-15 — Theo dõi tồn kho phụ tùng
- Khối: C. KHỐI 3 · Đợt: 2 · Owner: Kho trung tâm & Kho vận

## 1. Phạm vi đã chạm

| File | Loại thay đổi |
|---|---|
| `README.md` | Append-only metadata: thêm `Khối kiến trúc`, `Đợt triển khai`, `Owner`; cập nhật `Cập nhật cuối` 2026-05-08 → 2026-05-10. KHÔNG đổi heading, KHÔNG đổi schema cũ. |
| `02_Analysis_Design.md` | (1) Chuẩn hoá heading dấu chấm cho TẤT CẢ subsection I/II/III/IV/V (vd `I.1 Pitch` → `I.1. Pitch`). (2) Bổ sung `I.0. Khảo sát hiện trạng (As-Is)`, `I.7. Rủi ro & Giả định`, `I.8. Roadmap & Phụ thuộc`, `III.4. UC Catalog tổng hợp`. KHÔNG sửa wording body của các section đã có. |
| `_REPORT.md` | Tạo mới (file báo cáo này). |

## 2. Heading chuẩn hoá (audit ĐẶC BIỆT)

Toàn bộ 26 subsection trong file 02 đã được chuyển từ format `<roman>.<digit> <Title>` (lệch template) sang `<roman>.<digit>. <Title>` (đúng template kit `template/02_*.md`):

- I.1..I.6 (6 mục) → thêm dấu chấm
- II.1..II.6 (6 mục) → thêm dấu chấm
- III.1..III.3 (3 mục) → thêm dấu chấm
- IV.1..IV.5 (5 mục) → thêm dấu chấm
- V.1..V.5 (5 mục) → thêm dấu chấm

Hành động được phép theo `light-touch-recipes.md` §"Section đã có nhưng tên/heading lệch template — Đổi heading, giữ body".

## 3. Section bổ sung

### I.0. Khảo sát hiện trạng (As-Is)

Source: WHO HTM — *Inventory and maintenance 2025* + *Introduction to medical equipment inventory management*. Liệt kê pattern truyền thống (kho phân tán, không link WO, kiểm kê thủ công sai lệch >15%, không Watchlist, không forecast part-level). Cross-link sang §II.1 và §II.2 cho chi tiết. Kết thúc bằng placeholder `*(BA bổ sung trong sprint kế tiếp)*` cho khảo sát site cụ thể.

### I.7. Rủi ro & Giả định

Bảng 6 rủi ro (R-15-01..R-15-06) phủ rủi ro nghiệp vụ, dữ liệu, phụ thuộc, tích hợp, chất lượng dự báo, tuân thủ. Kèm 4 giả định về AC Backbone, IMM-08/09/12, IMM-16, chính sách Critical Spare site-specific.

### I.8. Roadmap & Phụ thuộc

- Đợt 2 (xác nhận theo `Ho_so_kien_truc_IMMIS.md` §"Đợt triển khai").
- 3 pha triển khai (Master & Allocation → Cycle Count & Watchlist → Forecast & ABC/XYZ).
- Phụ thuộc thượng nguồn (AC Inventory Backbone Wave 1, IMM-08/09/12) và hạ nguồn (IMM-16, IMM-17, IMM-13).
- Tham chiếu chuẩn WHO HTM Inventory 2025.

### III.4. UC Catalog tổng hợp

Bảng 8 UC (UC-01..UC-08) bao gồm 2 UC đã chi tiết (UC-01, UC-02 ở §III.2/§III.3) + 6 UC mới được liệt kê tổng quan: Watchlist breach, Emergency Override, Return, Demand Forecast, ABC/XYZ classify, Watchlist CRUD. Các UC mới đánh dấu chi tiết hoá trong sprint Wave 3 với placeholder chuẩn.

## 4. Mapping nguồn

| Section bổ sung | Source được dùng |
|---|---|
| I.0 Khảo sát | WHO — Inventory and maintenance 2025; WHO — Introduction to medical equipment inventory management |
| I.7 Rủi ro | Suy ra từ §IV.2/IV.3 (BR/VR đã có) + §V Compliance + RULE-F01..F04 |
| I.8 Roadmap | `docs/architecture/Ho_so_kien_truc_IMMIS.md` §"Đợt triển khai" + module-catalog.md |
| III.4 UC Catalog | Tổng hợp từ §III.2, §III.3, §IV.1 user stories US-15-01..US-15-05 |

## 5. KHÔNG đụng (theo light-touch)

- Heading wording cấp `## I/II/III/IV/V` — giữ nguyên.
- Pitch (I.1.), Stakeholder (I.3.), Scope (I.4.), KPI (I.5.), Compliance (I.6.) — giữ nguyên body.
- BPMN As-Is/To-Be, Decision Points, RACI, Exception Flows — giữ nguyên.
- UC-01, UC-02 detail — giữ nguyên.
- User Stories Gherkin, Business Rules, Validation Rules, Architecture Rules, Edge Cases — giữ nguyên.
- NFR Performance/Concurrency/Availability/Compliance/Scalability — giữ nguyên.
- README schema cũ (`Module | Wave | Trạng thái | Số file | Cập nhật cuối`) — chỉ APPEND 3 row mới ở cuối bảng metadata.
- Folder khác (03..09) — KHÔNG chạm.

## 6. Khuyến nghị tiếp theo (cho BA / Tech Lead)

1. README schema cũ vẫn dùng `Wave 3` trong khi metadata mới `Đợt: 2`. Đây là **mâu thuẫn** giữa schema cũ (Wave) và Architecture (Đợt). Light-touch không sửa — đề xuất user/BA quyết định: (a) giữ song song, hoặc (b) chỉnh `Wave 3 — PLANNED` thành `Wave 2` để đồng nhất. Skill KHÔNG tự đổi vì có thể ảnh hưởng release plan.
2. Heading H1 README hiện là `# IMM-15 — Tài liệu module` — lệch khuyến nghị template `# IMM-15 — Theo dõi tồn kho phụ tùng`. Theo `light-touch-recipes.md` README §"KHÔNG đụng heading wording", không tự sửa — report ở đây để BA quyết.
3. Banner cảnh báo "Wave 3 — PLANNED" trong file 02 vẫn còn — sau khi BA xác nhận Đợt 2, cần cập nhật banner và metadata `Trạng thái`/`Phiên bản`.
4. UC-03..UC-08 (mới liệt kê ở III.4) cần BA viết detail flow trong sprint kế tiếp; giữ placeholder `*(BA bổ sung trong sprint kế tiếp)*` đến lúc đó.
5. WHO citation chính xác hơn (số trang, mục) cho I.0 và I.8 — bổ sung khi BA đọc kỹ source PDF.

## 7. Checklist self-verify

- [x] README có ≥3 row metadata, có "Cập nhật cuối"
- [x] Mỗi subsection trong file 02 dùng format `<numeral>.<digit>. <Title>`
- [x] I.0, I.7, I.8, III.4 đã có
- [x] Không có placeholder `<XX>` chưa thay
- [x] Không động vào folder khác
- [x] Body section cũ giữ nguyên wording

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/dod-verification-report.md §1 for per-module results
- Status: READY
