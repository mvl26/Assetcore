# IMM-11 — Doc Curator Light-touch Report

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator` (light-touch)
- Phạm vi: 1 module = IMM-11 (Hiệu năng và hiệu chuẩn)
- Khối: C. KHỐI 3 · Đợt: 1 · Owner: PTP Khối 2 · Workshop / Nhóm TBYT
- Gap mức độ: TRUNG (đã có 8 file template + deployment, thiếu một số section bắt buộc theo template v4.1)

## 1. File × Section đã chạm

| File | Section | Hành động | Nguồn content |
|---|---|---|---|
| `README.md` | Bảng metadata (rows mới) | **Append-only** — thêm `Khối kiến trúc`, `Đợt triển khai`, `Owner`, `Tên đầy đủ`. Update `Cập nhật cuối` 2026-05-08 → 2026-05-10. KHÔNG đổi heading. KHÔNG đổi tên cột schema cũ. | User input + Architecture |
| `02_Analysis_Design.md` | §I.0 Khảo sát hiện trạng | **Tạo mới** — 3 đoạn (As-Is bệnh viện VN + WHO HTM Inspection/Calibration framework + ghi chú baseline) | WHO `Medical equipment maintenance programme overview` ch.6.1 + Glossary "Calibration" |
| `02_Analysis_Design.md` | §II.6 Process metrics | **Tạo mới** — bảng 5 metric (time-to-assignment, on-time rate, cert lead time, first-time pass, CAPA closure) | Suy ra từ KPI I.5 + WHO HTM Performance |
| `02_Analysis_Design.md` | §II.8 Exception flow | **Tạo mới** — 3 exception (cert sai format, lab mất ISO, concurrent edit) | Light-touch skeleton, một số mục đánh `*(BA bổ sung)*` |
| `02_Analysis_Design.md` | §II.9 So sánh As-Is vs To-Be | **Tạo mới** — bảng 6 khía cạnh | Tổng hợp từ I.0 + II.2/II.4 hiện có |
| `02_Analysis_Design.md` | §II.10 Activity diagram per UC | **Tạo skeleton** — placeholder, refer file 03 §III để vẽ chi tiết | Không bịa diagram |
| `02_Analysis_Design.md` | §III.1.b Use Case phân rã | **Tạo mới** — 3 nhóm chức năng (Planning, Execution, Post-result) | Phân nhóm từ III.1.a hiện có |
| `02_Analysis_Design.md` | §III.2 Actor catalog | **Tạo mới** — bảng 9 actor (6 user + 1 external + 2 system) | Architecture + I.3 Stakeholders hiện có |
| `02_Analysis_Design.md` | §III.4 Use Case relationships | **Tạo mới** — 2 bảng include + extend | Suy từ UC diagram III.1.a |
| `02_Analysis_Design.md` | §III.5 UC ↔ US mapping | **Tạo skeleton** — 2 row hiện có + ghi chú BA bổ sung | Light-touch |
| `02_Analysis_Design.md` | §IV.4 Input — Output | **Tạo mới** — 3 mục (a) Input fields + cascade, (b) Output DocType, (c) Notification/side effect | Codebase ground truth (BE đã live) + Architecture |
| `02_Analysis_Design.md` | §V.4 Khả mở rộng | **Tạo mới** — bảng 4 metric (concurrent, dataset, multi-site, scheduler throughput) | Template v4.1 + suy từ V.1 |
| `02_Analysis_Design.md` | §V.5 Khả dụng UX | **Tạo mới** — WCAG, browser, ngôn ngữ, responsive, onboarding | Template v4.1 |
| `02_Analysis_Design.md` | §V.6 Bảo trì | **Tạo mới** — coverage, lint, tech debt, onboarding | CONVENTIONS §6 |

## 2. Không đụng (theo light-touch)

- KHÔNG sửa heading `# IMM-11 — Tài liệu module` (giữ wording cũ — nếu BA muốn đổi sang "Hiệu năng và hiệu chuẩn" cần user duyệt rõ).
- KHÔNG sửa schema metadata cũ (`Module | Wave | Trạng thái | Số file | Cập nhật cuối`) — chỉ append rows mới.
- KHÔNG sửa Pitch (I.1), Stakeholder (I.3), KPI (I.5), Compliance (I.6), Risk (I.7), Roadmap (I.8) hiện có.
- KHÔNG sửa II.2 As-Is, II.3 Pain points, II.4 To-Be BPMN, II.5 Decision points, II.7 RACI hiện có.
- KHÔNG sửa III.1.a UC diagram tổng quát, III.3 UC specs (UC-05, UC-06), IV.1 User Stories, IV.2 Business Rules, IV.3 State machine, IV.5 Edge cases hiện có.
- KHÔNG sửa V.1 Hiệu năng, V.2 Bảo mật, V.3 Khả dụng, V.7 Tuân thủ hiện có.
- KHÔNG chạm folder khác ngoài `docs/imm-11/`.

## 3. Việc còn lại (placeholder cần BA fill)

- §I.0 — baseline khảo sát site khách hàng (số % chưa cảnh báo, số % cert không truy xuất).
- §II.8 EF-02 — playbook xử lý lab mất ISO 17025 trong khi giữ thiết bị.
- §II.10 — vẽ Activity diagram chi tiết trong `03_Diagrams.md` §III cho UC-05/06/08/09.
- §III.5 — fill mapping đầy đủ UC ↔ US (hiện chỉ có 2/12 UC).
- DoD §V — review bởi BA Lead + Tech Lead + QMS Officer.

## 4. Mapping với 4 source

| Section | Source được dùng |
|---|---|
| I.0 | WHO `Medical equipment maintenance programme overview` ch.6.1 + Glossary |
| II.6, II.9 | Architecture `Ho_so_kien_truc_IMMIS.md` + WHO HTM Performance |
| III.2 | Architecture §"Vai trò triển khai" + I.3 hiện có |
| IV.4 | Codebase ground truth (`services/imm11.py`, DocType JSON đã live) |
| V.4–V.6 | `docs/template/02_Analysis_Design.md` v4.1 + CONVENTIONS §6 |

---

*Light-touch nguyên tắc: thêm heading + skeleton placeholder cho phần thiếu data, KHÔNG bịa nội dung. KHÔNG chạm folder khác.*
