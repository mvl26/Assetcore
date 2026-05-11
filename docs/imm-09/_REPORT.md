# IMM-09 — Doc Curator Report (Light-touch)

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator`
- Chiến lược: Light-touch (append-only, không rewrite)
- Module: IMM-09 — Sửa chữa, phụ tùng và cập nhật phần mềm
- Khối: C. KHỐI 3 · Đợt: 1 · Owner: PTP Khối 2 · Workshop / Nhóm TBYT

---

## 1. Gap audit (trước khi sửa)

| Section | Template chuẩn | Trạng thái IMM-09 | Hành động |
|---|---|---|---|
| README — Khối kiến trúc | Có | ❌ Thiếu row | Append |
| README — Đợt triển khai | Có | ❌ Thiếu row | Append |
| README — Owner | Có | ❌ Thiếu row | Append |
| README — Cập nhật cuối | Có | 🟡 2026-05-08 | Update → 2026-05-10 |
| 02 §II.6 Process metrics | Có | ❌ Thiếu | Bổ sung (theo WHO CMMS) |
| 02 §II.9 So sánh As-Is vs To-Be | Có | ❌ Thiếu | Bổ sung |
| 02 §III.4 Use Case relationships | Có | ❌ Thiếu | Bổ sung |
| 02 §I.1 Pitch | — | ✅ Đã viết kỹ | KHÔNG đụng |
| 02 §I.3 Stakeholders | — | ✅ Đã viết kỹ | KHÔNG đụng |
| 02 §I.5 KPI | — | ✅ Đã viết kỹ | KHÔNG đụng |
| 04 Workflow | — | ✅ Stable | KHÔNG đụng |

---

## 2. File đã chạm

| File | Loại thay đổi | Section thêm |
|---|---|---|
| `README.md` | Update + Append | +3 row metadata (Khối / Đợt / Owner); update `Cập nhật cuối` |
| `02_Analysis_Design.md` | Append section | +§II.6 Process metrics · +§II.9 As-Is vs To-Be · +§III.4 UC relationships |
| `_REPORT.md` | Tạo mới | (file này) |

KHÔNG chạm: `03_Diagrams.md`, `04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md`, `07_Testing_QA.md`, `08_Deployment.md`, `09_Release.md`.

KHÔNG chạm Pitch / Stakeholder / KPI / Workflow (per user constraint).

---

## 3. Source mapping cho section mới

| Section | Source ưu tiên | Áp dụng |
|---|---|---|
| §II.6 Process metrics | WHO HTM — *CMMS* chapter (MTTR, SLA, audit-readiness) | MTTR theo asset_class · SLA % · repeat failure rate · spare parts traceability · audit-readiness · FCR coverage |
| §II.9 As-Is vs To-Be | WHO HTM CMMS + ground truth từ `services/imm09.py` (BR-09-01..05) | 12 khía cạnh: tạo WO, phân công, vật tư, firmware, checklist, MTTR, SLA, repeat failure, asset status, audit, báo cáo, NĐ98 |
| §III.4 UC relationships | UC catalog hiện có (III.1, III.3, III.5) + Business Rules (IV.2) | 8 `<<include>>` + 4 `<<extend>>` |

---

## 4. Placeholder còn lại (cần BA / khảo sát fill)

- §II.6 MTTR baseline class B/C: `*(Cần khảo sát baseline)*`
- §II.6 % SLA compliance baseline: `*(Cần khảo sát baseline)*`

---

## 5. Cảnh báo lệch template (KHÔNG tự sửa — báo để BA quyết)

- **Heading wording cũ**: `# IMM-09 — Tài liệu module` (README.md line 1) — template gợi ý `# IMM-09 — <Tên module>`. Theo light-touch rules (recipe README "KHÔNG đụng heading wording"), giữ nguyên. Nếu BA muốn rename → cần task riêng.
- **README schema cũ** (`Module | Wave | Trạng thái | Số file | Cập nhật cuối`): giữ y nguyên 5 row đầu, chỉ APPEND 3 row mới ở cuối — đúng quy tắc append-only.
- **Section II.1 (Phân biệt 3 khái niệm)** không có trong file hiện tại. Template có (optional). Không tự thêm vì không nằm trong scope task.

---

## 6. Checklist self-check

- [x] Heading wording cũ — không đổi
- [x] README schema cũ — không đổi tên cột, chỉ append
- [x] Pitch / Stakeholder / KPI / Workflow — không đụng
- [x] Folder khác (imm-08, imm-04, ...) — không chạm
- [x] Section mới có content thực, không bịa số liệu (placeholder rõ ràng)
- [x] Link nội bộ trong README vẫn trỏ đúng file thật
- [x] File _REPORT.md tạo trong scope `docs/imm-09/`
