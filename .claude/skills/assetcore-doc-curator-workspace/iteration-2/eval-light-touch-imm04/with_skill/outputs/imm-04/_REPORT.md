# IMM-04 — Light-touch Review Report

- Ngày: 2026-05-10
- Phạm vi: `docs/imm-04/` (9 file: README + 02→09)
- Chiến lược: **light-touch / append-only** theo `light-touch-recipes.md`
- Output sandbox: `.claude/skills/assetcore-doc-curator-workspace/iteration-2/eval-light-touch-imm04/with_skill/outputs/imm-04/`
- Real `docs/imm-04/`: KHÔNG modify

---

## 1. File × Section đã chạm

| File | Section | Loại thay đổi | LOC delta |
|---|---|---|---|
| README.md | Bảng metadata (row "Cập nhật cuối") | Update giá trị ngày `2026-05-08` → `2026-05-10` (giữ nguyên tên cột) | 0 (in-place) |
| README.md | Bảng metadata (cuối bảng) | **Append** 2 row mới: `Khối kiến trúc \| B. KHỐI 2`, `Owner \| PTP Khối 2 — Workshop / Nhóm TBYT` | +2 |
| README.md | `## Tham chiếu chéo` (mới) | **Append** section mới sau `## Tham chiếu`, trước divider — link Architecture / WHO / GMDN / module liên quan / skill build | +8 |

**Tổng LOC delta**: +10 dòng (1 file chạm).

**Files KHÔNG chạm** (8 file): `02_Analysis_Design.md`, `03_Diagrams.md`, `04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md`, `07_Testing_QA.md`, `08_Deployment.md`, `09_Release.md` — đã có structure đầy đủ I/II/III + DoD; light-touch nguyên tắc *touch ít nhất có thể*.

---

## 2. Đã RESERVE không sửa (chuyển report theo cấm light-touch)

Các điểm dưới đây skill phát hiện lệch so với template/skill rule, nhưng **không tự sửa** vì rơi vào danh mục "Không đụng" của §3 SKILL.md / recipe README. User / BA quyết định.

### 2.1. README — Heading wording lệch template

- Heading hiện tại: `# IMM-04 — Tài liệu module`
- Template chuẩn (§6 SKILL.md): `# IMM-XX — <Tên module>` → `# IMM-04 — Lắp đặt, định danh và kiểm tra ban đầu` (theo `module-catalog.md` line ~12).
- **Lý do không sửa**: SKILL.md §3 liệt kê heading wording cũ là *destructive rewrite* — chỉ làm khi user yêu cầu rõ.
- **Khuyến nghị**: nếu user duyệt, đổi heading 1 lần (touch line 1 README).

### 2.2. README — Field "Module" trong bảng metadata trùng với heading

- Row `| Module | **IMM-04 — Lắp đặt (Installation / Commissioning)** |` lặp tên module dạng cũ (parenthetical English). Tên chính thức từ Architecture: "Lắp đặt, định danh và kiểm tra ban đầu".
- **Lý do không sửa**: rơi vào "Schema metadata cũ — giữ y nguyên" + "Heading wording" (BA đã chốt văn phong).
- **Khuyến nghị**: BA review wording. Nếu giữ "Installation / Commissioning" có chủ ý (gọn cho dev) thì OK.

### 2.3. README — Field "Wave" thay vì "Đợt triển khai"

- Recipe README §"KHÔNG đụng" cấm rõ: "`Wave` → `Đợt triển khai` là destructive rewrite".
- **Hành động**: giữ nguyên `Wave | 1`.
- **Khuyến nghị**: nếu user muốn Việt-hoá toàn bộ schema, thực hiện trong 1 commit riêng có user duyệt.

### 2.4. README — Section "Map cũ → Template chuẩn" và "Source docs (cũ) đã archive" có nội dung migration

- 2 section này là tri thức migration BA đã viết, không có trong template chuẩn §6.
- **Lý do không sửa/xoá**: §3 SKILL.md cấm "Thêm/xoá section ngoài template" trừ khi user yêu cầu.
- **Khuyến nghị**: giữ — section migration giúp người mới hiểu lịch sử.

### 2.5. 02_Analysis_Design.md — Phần I.0 Khảo sát rất ngắn

- I.0 line 16–22, ngắn (~6 line).
- **Lý do không bổ sung**: light-touch §"Pitch / Stakeholder / KPI đã viết kỹ — chỉ sửa chính tả". I.0 không nằm trong "Bổ sung an toàn" của recipe 02 (chỉ cho I.5/I.6/I.7).
- **Khuyến nghị**: BA bổ sung khi có interview note As-Is bệnh viện thật.

### 2.6. 02 §I.7 Risk có ≥10 dòng — không thiếu, không bổ sung

- Recipe cho phép thêm placeholder *(BA bổ sung trong sprint kế tiếp)* khi I.7 trống. Nhưng I.7 đã có content (line 104–123) → KHÔNG đụng.

### 2.7. 02 §I.6 Compliance đã có 1 bảng — không bổ sung row

- Recipe cho phép thêm 1 dòng NĐ98 + 1 dòng GMDN nếu thiếu. Skill chỉ verify line 94–103 — nếu BA đã có 1 dòng NĐ98, KHÔNG ghi đè.
- **Khuyến nghị**: user verify đủ 2 dòng NĐ98 + GMDN cho IMM-04 (module chạm định danh thiết bị → bắt buộc map GMDN, theo `source-map.md` §Source 2).

### 2.8. 04_Backend_Design.md — DocType field list đã có

- Recipe 04 §"Không đụng": "DocType field list nếu code đã build — đó là source of truth, chỉ verify".
- File 04 line 54+ liệt kê `Asset Commissioning` field. Không kiểm chéo với code thật trong session này (out-of-scope light-touch).
- **Khuyến nghị**: chạy `assetcore-module-audit` để cross-check DocType ↔ JSON thật.

### 2.9. 05_API_Specification.md — Endpoint shape

- Recipe 05 §"Không đụng": "Tên endpoint, request/response shape — phải match code thật".
- File 05 đã có §0 Catalog + §1 Envelope + §2 Endpoint chi tiết. Không kiểm chéo với `assetcore/api/imm04.py` trong session này.
- **Khuyến nghị**: BE engineer review periodic.

### 2.10. 07_Testing_QA.md / 08_Deployment.md / 09_Release.md — Heading dạng cũ `# IMM-04 —`

- 3 file này có heading `# IMM-04 — Kiểm thử & An ninh ...` thay vì `# 07 — Testing & QA` theo template `00_README.md` (numeric prefix).
- **Lý do không sửa**: §3 SKILL.md cấm đổi heading wording — destructive rewrite. Đối lập với 02/03/04/05/06 đã có heading numeric (`# 02 — ...`). Inconsistency là BA cố ý hay legacy?
- **Khuyến nghị**: user quyết định — chuẩn hoá heading 7/8/9 sang numeric prefix HOẶC đổi 2/3/4/5/6 sang dạng `# IMM-04 — ...`. Cả 2 đều cần user duyệt.

### 2.11. Roadmap README có 4 task hở — không phải responsibility của doc-curator

- Item Sprint 7/8 trong "Roadmap chuẩn hóa" là task code (UNIQUE constraint, Print Format, listener IMM-08).
- **Lý do không đụng**: skill này CHỈ làm `.md`, không trigger code task. Tracking thuộc về BA/Tech Lead.

---

## 3. Tóm tắt

- **Touched**: 1 file (`README.md`), +10 LOC, 0 LOC removed.
- **Reserved (report-only)**: 11 mục — 5 về README/heading wording, 4 về content BA đã chốt, 2 về cross-check code (out-of-scope light-touch).
- **Quy tắc vàng đã tuân thủ**: KHÔNG đổi schema metadata cũ; KHÔNG đổi heading wording; KHÔNG sửa Pitch/Stakeholder/KPI; APPEND row mới ở cuối bảng; thêm section "Tham chiếu chéo" mới (an toàn — recipe README liệt kê là "Bổ sung an toàn").
