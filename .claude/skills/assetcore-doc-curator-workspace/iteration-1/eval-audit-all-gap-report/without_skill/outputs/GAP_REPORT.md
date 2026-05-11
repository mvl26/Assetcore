# GAP REPORT — AssetCore IMM Documentation Audit

**Ngày audit**: 2026-05-10
**Phạm vi**: 17 module IMM-01 → IMM-17 (theo `docs/architecture/Ho_so_kien_truc_IMMIS.md`)
**Tham chiếu template**: `docs/template/` (00_README + 02..09 = 9 file/module)
**Phương pháp**: Đối chiếu sự tồn tại của thư mục `docs/imm-XX/`, sự tồn tại của 9 file chuẩn, và mức độ phủ section H2 so với template kit.

---

## 1. Tổng quan — Bảng trạng thái 17 module

Trạng thái: `OK` (đủ file + sections gần đầy đủ), `PARTIAL` (đủ file nhưng thiếu section), `MISSING` (chưa có thư mục).

| Module | Tên                                          | Khối     | Thư mục `docs/imm-XX/` | 9 file đủ? | Mức phủ section | Trạng thái |
| ------ | -------------------------------------------- | -------- | ---------------------- | ---------- | --------------- | ---------- |
| IMM-01 | Đánh giá nhu cầu và dự toán                  | Khối 1   | Có                     | Đủ         | Trung bình      | PARTIAL    |
| IMM-02 | Thông số kỹ thuật và phân tích thị trường   | Khối 1   | Có                     | Đủ         | Trung bình      | PARTIAL    |
| IMM-03 | Đánh giá NCC và quyết định mua sắm          | Khối 1   | Có                     | Đủ         | Thấp (07/08/09) | PARTIAL    |
| IMM-04 | Lắp đặt, định danh, kiểm tra ban đầu        | Khối 2   | Có                     | Đủ         | Cao             | OK         |
| IMM-05 | Đăng ký, cấp phép và hồ sơ                  | Khối 2   | Có                     | Đủ         | Cao             | OK         |
| IMM-06 | Đào tạo người dùng                           | Khối 2   | Có                     | Đủ         | Trung bình      | PARTIAL    |
| IMM-07 | Theo dõi hiệu suất                           | Khối 3   | **Không**              | —          | —               | **MISSING** |
| IMM-08 | Bảo trì định kỳ                              | Khối 3   | Có                     | Đủ         | Cao             | OK         |
| IMM-09 | Sửa chữa, phụ tùng, cập nhật phần mềm       | Khối 3   | Có                     | Đủ         | Cao             | OK         |
| IMM-10 | Hậu kiểm và tuân thủ                         | Khối 3   | **Không**              | —          | —               | **MISSING** |
| IMM-11 | Hiệu năng và hiệu chuẩn                      | Khối 3   | Có                     | Đủ         | Trung bình      | PARTIAL    |
| IMM-12 | Bảo trì khắc phục                            | Khối 3   | Có                     | Đủ         | Trung bình      | PARTIAL    |
| IMM-13 | Ngừng sử dụng và điều chuyển                | Khối 4   | **Không**              | —          | —               | **MISSING** |
| IMM-14 | Giải nhiệm thiết bị                          | Khối 4   | **Không**              | —          | —               | **MISSING** |
| IMM-15 | Theo dõi tồn kho phụ tùng                    | Khối 3   | Có                     | Đủ         | Thấp (02/07/09) | PARTIAL    |
| IMM-16 | Theo dõi tuân thủ                            | Khối 3   | Có                     | Đủ         | Thấp (03/07/09) | PARTIAL    |
| IMM-17 | Phân tích dự đoán                            | Khối 3   | **Không**              | —          | —               | **MISSING** |

> Ghi chú: Có thư mục `docs/imm-00/` (Module Overview) — không nằm trong 17 module nhưng đầy đủ 9 file, mức phủ cao. Không tính vào audit 17 module.

**Thống kê tổng**:
- 12/17 module có thư mục docs (70.6%).
- 5/17 module hoàn toàn chưa có docs: **IMM-07, IMM-10, IMM-13, IMM-14, IMM-17**.
- 0/17 module có thư mục nhưng thiếu file (mọi module đã tạo đều có đủ 9 file chuẩn 02..09 + README).
- 4/12 module hiện có đạt mức OK (gần đầy đủ section): IMM-04, 05, 08, 09.
- 8/12 module ở mức PARTIAL (một hoặc nhiều file thiếu section bắt buộc).

---

## 2. Module thiếu HOÀN TOÀN docs (MISSING)

Cần khởi tạo thư mục mới `docs/imm-XX/` và toàn bộ 9 file theo template (`docs/template/00_README.md`, `02_Analysis_Design.md` ... `09_Release.md`).

| Module | Tên                            | Khối | Cần tạo                                                              | Ghi chú ưu tiên                                                                  |
| ------ | ------------------------------ | ---- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| IMM-07 | Theo dõi hiệu suất             | C    | README + 02..09 (9 file)                                             | Là nguồn KPI cho IMM-08/12/16; nên ưu tiên ngay sau Wave-1.                      |
| IMM-10 | Hậu kiểm và tuân thủ           | C    | README + 02..09 (9 file)                                             | Liên quan recall/FSCA/CAPA — ràng buộc compliance NĐ98.                         |
| IMM-13 | Ngừng sử dụng và điều chuyển  | D    | README + 02..09 (9 file)                                             | Khối 4 (End-of-Life) chưa có module nào có docs.                                |
| IMM-14 | Giải nhiệm thiết bị            | D    | README + 02..09 (9 file)                                             | Đóng vòng đời asset — cần cùng IMM-13.                                           |
| IMM-17 | Phân tích dự đoán              | C    | README + 02..09 (9 file)                                             | Phụ thuộc IMM-07/08/09/11/12/15; có thể defer sau khi data layer ổn.            |

---

## 3. Module có thư mục nhưng thiếu file (PARTIAL — file-level)

**Không có module nào trong nhóm này.** Tất cả 12 module đã tạo đều có đủ 9 file chuẩn (README + 02_Analysis_Design + 03_Diagrams + 04_Backend_Design + 05_API_Specification + 06_Frontend_Design + 07_Testing_QA + 08_Deployment + 09_Release).

---

## 4. Module có file nhưng thiếu section bắt buộc (PARTIAL — section-level)

Mức độ phủ section được đánh giá bằng cách so sánh số H2 hiện có với số H2 yêu cầu trong template. Các file nêu dưới đây là các file có số section thấp đáng kể (≤ 60% so với template chuẩn) hoặc thiếu một Phần (Phần I/II/III…) hoàn toàn.

### 4.1 IMM-01 — Đánh giá nhu cầu và dự toán

| File                  | H2 hiện có | H2 template (xấp xỉ) | Section thiếu nổi bật                                                                                  |
| --------------------- | ---------- | -------------------- | ------------------------------------------------------------------------------------------------------ |
| 02_Analysis_Design.md | 19         | ~28                  | Thiếu chi tiết Phần III (UC relationships, UC↔Sequence mapping), Phần V (NFR Compliance/Maintainability). |
| 03_Diagrams.md        | 5          | ~28                  | Thiếu hầu hết Phần II (Class), Phần III (Sequence), Phần IV (Communication), Phần V (Package).         |
| 04_Backend_Design.md  | 7          | 11                   | Thiếu §6 Audit Trail, §7 Background jobs, §8 Integration, §9 Migration.                                |
| 05_API_Specification.md | 6        | 8                    | Thiếu §3 List/Query, §4 Webhook, §5 Versioning, §6 Rate limit, §7 Smoke test playbook.                 |
| 06_Frontend_Design.md | 4          | 12                   | Thiếu §3.c archetype, §4 Custom components, §6b API call pattern, §6c TS types, §7d Linked fields, §7e Input tight, §9 A11y, §10 Print spec. |

### 4.2 IMM-02 — Thông số kỹ thuật và phân tích thị trường

| File              | H2 hiện có | H2 template | Section thiếu nổi bật                                                                |
| ----------------- | ---------- | ----------- | ------------------------------------------------------------------------------------ |
| 02_Analysis_Design.md | 16     | ~28         | Thiếu Phần II decision points/RACI/exception flow, Phần III UC relationships, Phần V Compliance. |
| 03_Diagrams.md    | 3          | ~28         | Chỉ có 3 Sequence diagrams (SD-01..03); thiếu toàn bộ ERD, Class, Communication, Package. |
| 06_Frontend_Design.md | 14     | 12 (gần đủ; nội dung cần kiểm tra chiều sâu)| Cần verify §6c TS types, §7d Linked fields, §7e Input tight có đủ dữ liệu module. |

### 4.3 IMM-03 — Đánh giá NCC và quyết định mua sắm

| File                  | H2 hiện có | H2 template | Section thiếu nổi bật                                                                  |
| --------------------- | ---------- | ----------- | ---------------------------------------------------------------------------------------- |
| 03_Diagrams.md        | 5          | ~28         | Thiếu Class Diagram, Sequence chi tiết, Communication, Package.                          |
| 04_Backend_Design.md  | 10         | 11          | Cần kiểm tra §4b Repository Layer + §9 Migration & Patch.                                |
| 05_API_Specification.md | 10        | 8           | Có (>=template) nhưng cần đối chiếu cấu trúc § chuẩn.                                    |
| 06_Frontend_Design.md | 6          | 12          | Thiếu §3.c archetype, §6b API pattern, §6c TS types, §7d/7e, §9 A11y, §10 Print.        |
| 07_Testing_QA.md      | 3          | ~28         | Chỉ có Phần I/II/III ở cấp top — thiếu toàn bộ I.1..I.12, II.1..II.5, III.1..III.11.    |
| 08_Deployment.md      | 2          | 21          | Chỉ có Phần I/II top-level — thiếu I.1..I.10 (pre-deploy/smoke/rollback…), II.1..II.9.   |
| 09_Release.md         | 3          | 28          | Chỉ có Phần I/II/III top-level — thiếu User Guide subsections, Release Notes subsections, Traceability matrix. |

### 4.4 IMM-06 — Đào tạo người dùng

| File              | H2 hiện có | H2 template | Section thiếu nổi bật                                                              |
| ----------------- | ---------- | ----------- | ---------------------------------------------------------------------------------- |
| 02_Analysis_Design.md | 10     | ~28         | Thiếu nhiều subsection Phần I (KPI, Compliance, Risk), Phần II (RACI, Exception). |
| 03_Diagrams.md    | 5          | ~28         | Thiếu hầu hết Class/Sequence/Communication/Package.                               |
| 04_Backend_Design.md | 9       | 11          | Thiếu §7 Background jobs, §8 Integration.                                          |
| 05_API_Specification.md | 5     | 8           | Thiếu §3 List, §4 Webhook, §5 Versioning, §6 Rate limit, §7 Smoke.                |
| 06_Frontend_Design.md | 6      | 12          | Thiếu §3.c archetype, §6b API pattern, §6c TS types, §7d/7e, §9 A11y.            |

### 4.5 IMM-11 — Hiệu năng và hiệu chuẩn

| File              | H2 hiện có | H2 template | Section thiếu nổi bật                                                              |
| ----------------- | ---------- | ----------- | ---------------------------------------------------------------------------------- |
| 02_Analysis_Design.md | 24     | ~28         | Cần đối chiếu Phần V Compliance đầy đủ (HTM/NĐ98 calibration certificate).        |
| 03_Diagrams.md    | 12         | ~28         | Thiếu Class, Communication, Package diagrams.                                      |
| 05_API_Specification.md | 5     | 8           | Thiếu §4 Webhook, §5 Versioning, §6 Rate limit, §7 Smoke test.                    |
| 06_Frontend_Design.md | 11     | 12          | Cần kiểm tra §10 Print spec (certificate hiệu chuẩn — bắt buộc với hiệu chuẩn).   |

### 4.6 IMM-12 — Bảo trì khắc phục

| File              | H2 hiện có | H2 template | Section thiếu nổi bật                                                              |
| ----------------- | ---------- | ----------- | ---------------------------------------------------------------------------------- |
| 03_Diagrams.md    | 10         | ~28         | Thiếu Class, Communication, Package diagrams; cần Sequence cho RCA flow.          |
| 04_Backend_Design.md | 10      | 11          | Cần kiểm tra §4b Repository, §9 Migration.                                          |
| 05_API_Specification.md | 5     | 8           | Thiếu §4 Webhook (escalation event), §5 Versioning, §6 Rate limit, §7 Smoke.      |
| 06_Frontend_Design.md | 9      | 12          | Thiếu §3.c archetype, §6c TS types, §10 Print.                                     |

### 4.7 IMM-15 — Theo dõi tồn kho phụ tùng

| File              | H2 hiện có | H2 template | Section thiếu nổi bật                                                                          |
| ----------------- | ---------- | ----------- | ---------------------------------------------------------------------------------------------- |
| 02_Analysis_Design.md | 5      | ~28         | Chỉ có 5 H2 cấp I-V — thiếu toàn bộ subsection I.0..I.8, II.1..II.10, III.1..III.6, IV/V.    |
| 03_Diagrams.md    | 5          | ~28         | Thiếu Class, Sequence, Communication, Package; cần ERD chi tiết với tồn kho.                  |
| 04_Backend_Design.md | 9       | 11          | Cần verify §6 Audit, §7 Scheduler (auto-reorder?), §9 Migration.                                |
| 05_API_Specification.md | 8     | 8           | Đủ count nhưng cần đối chiếu cấu trúc.                                                          |
| 07_Testing_QA.md  | 5          | ~28         | Chỉ có 5 H2 — thiếu hầu hết I.1..I.12, II.1..II.5, III.1..III.11.                              |
| 08_Deployment.md  | 10         | 21          | Thiếu I.2b Env config, I.5 Schema migration risk, I.7 Rollback, I.8 Communication, I.9 Monitoring, II.6/II.7/II.8 Audit/Training/Risk. |
| 09_Release.md     | 7          | 28          | Thiếu hầu hết User Guide (I.1..I.10), Release Notes subsections, Traceability matrix III.1..III.7. |

### 4.8 IMM-16 — Theo dõi tuân thủ

| File              | H2 hiện có | H2 template | Section thiếu nổi bật                                                              |
| ----------------- | ---------- | ----------- | ---------------------------------------------------------------------------------- |
| 03_Diagrams.md    | 3          | ~28         | Chỉ có 3 H2 (Sequence III.1..III.3) — thiếu toàn bộ ERD, Class, Communication, Package. |
| 05_API_Specification.md | 7     | 8           | Cần verify §6 Rate limit, §7 Smoke test playbook.                                  |
| 06_Frontend_Design.md | 8      | 12          | Thiếu §3.c archetype, §6c TS types, §7d/7e, §10 Print (audit report PDF).         |
| 07_Testing_QA.md  | 8          | ~28         | Thiếu nhiều subsection I.1..I.12, II.1..II.5, III.1..III.11.                      |
| 09_Release.md     | 8          | 28          | Thiếu nhiều User Guide subsections, Release Notes detailed, Traceability matrix.  |

---

## 5. Section "BẮT BUỘC" (theo template DoD) — đối chiếu nhanh

Các section dưới đây xuất hiện trong DoD của template, cần có ở **mọi** module:

### 5.1 File 02_Analysis_Design — bắt buộc
- I.5 KPI mục tiêu
- I.6 Ràng buộc Compliance (HTM/NĐ98)
- II.7 RACI matrix
- III.3 Use Case Specifications
- IV.1 User Stories & Acceptance Criteria
- IV.3 State Machine
- V.7 Compliance NFR

→ Modules có rủi ro thiếu (H2 < 20): IMM-06 (10), IMM-15 (5).

### 5.2 File 04_Backend_Design — bắt buộc
- §2 Domain Model — DocType
- §4 Service Layer
- §4b Repository Layer
- §5 API Layer
- §6 Audit Trail (CLAUDE.md §5 mandates audit trail)
- §10 Non-functional

→ Modules có rủi ro thiếu (H2 < 10): IMM-01 (7), IMM-06 (9), IMM-15 (9).

### 5.3 File 05_API_Specification — bắt buộc
- §0 API Catalog
- §2 Endpoint detailed spec
- §7 Smoke test playbook

→ Modules có rủi ro thiếu (H2 < 7): IMM-01 (6), IMM-06 (5), IMM-08 (5), IMM-11 (5), IMM-12 (5).

### 5.4 File 06_Frontend_Design — bắt buộc
- §1 Sitemap/Route map
- §5 Pinia store
- §6 Vue Query keys
- §7 Quy tắc ngôn ngữ FE
- §7d Linked/Cascade fields
- §7e Input tight
- §9 Accessibility checklist

→ Modules có rủi ro thiếu (H2 < 8): IMM-01 (4), IMM-03 (6), IMM-06 (6), IMM-15 (6) — phần lớn thiếu §6b/§6c/§7d/§7e/§9.

### 5.5 File 07_Testing_QA — bắt buộc
- I.2 Unit test Service
- I.4 Integration test DocType
- I.5 Workflow test
- I.6 Audit chain integrity
- II Phần UAT (II.4 Test scenarios)
- III Phần Security review (III.1 RBAC, III.6 Vendor isolation, III.11 Sign-off)

→ Modules có rủi ro thiếu (H2 < 15): IMM-01 (14), IMM-02 (11), IMM-03 (3), IMM-15 (5), IMM-16 (8).

### 5.6 File 08_Deployment — bắt buộc
- I.1 Pre-deployment checklist
- I.4 Deploy sequence
- I.6 Smoke test sau deploy
- I.7 Rollback plan
- II.2 Trace yêu cầu pháp lý
- II.5 Traceability compliance → code
- II.9 Sign-off

→ Modules có rủi ro thiếu (H2 < 15): IMM-03 (2), IMM-15 (10).

### 5.7 File 09_Release — bắt buộc
- I.4 Quy trình chính (User Guide)
- I.5 Thao tác per role
- II.1 Tóm tắt + II.2 Tính năng mới
- III.2 Traceability Matrix chính

→ Modules có rủi ro thiếu (H2 < 15): IMM-03 (3), IMM-15 (7), IMM-16 (8).

---

## 6. Tổng hợp ưu tiên xử lý

### Ưu tiên P0 — Tạo mới hoàn toàn (5 module)
1. **IMM-07** — Theo dõi hiệu suất (cần cho KPI cross-module)
2. **IMM-10** — Hậu kiểm và tuân thủ (compliance NĐ98)
3. **IMM-13** — Ngừng sử dụng và điều chuyển (Khối 4)
4. **IMM-14** — Giải nhiệm thiết bị (Khối 4)
5. **IMM-17** — Phân tích dự đoán (có thể defer)

### Ưu tiên P1 — Bổ sung nặng (sửa nhiều file thiếu phần lớn section)
1. **IMM-03** — 03/06/07/08/09 đều thiếu rất nhiều subsection.
2. **IMM-15** — 02/03/07/08/09 ở mức thấp.
3. **IMM-16** — 03/07/09 ở mức thấp.

### Ưu tiên P2 — Bổ sung trung bình (1–3 file thiếu section)
1. **IMM-01** — 03/04/05/06 cần bổ sung subsection.
2. **IMM-02** — 03 (Diagrams) thiếu toàn bộ Class/Communication/Package.
3. **IMM-06** — 02/03/05/06 cần bổ sung subsection.
4. **IMM-11** — 03/05 cần bổ sung subsection.
5. **IMM-12** — 03/05/06 cần bổ sung subsection.

### Đạt OK (chỉ cần spot-check)
- **IMM-04, IMM-05, IMM-08, IMM-09** — có đủ file và mức phủ section gần template.

---

## 7. Khuyến nghị quy trình

1. Chạy lại audit này định kỳ (sau mỗi sprint) bằng script đếm H2 đối chiếu template để theo dõi delta.
2. Khi tạo module mới: copy nguyên `docs/template/` → `docs/imm-XX/` rồi điền — tránh trường hợp như IMM-15/IMM-03 chỉ có cấp Phần I/II/III mà không phá xuống subsection.
3. Khi review PR feature: bắt buộc cập nhật ít nhất file 02 (UC/AC) + 04 (Backend) + 05 (API) + 09 (Release Notes) cho module bị động chạm.
4. DoD release Wave-1 chỉ chấp nhận khi 6 module Wave-1 (IMM-04/05/08/09/11/12) đều đạt OK ở 9/9 file — hiện 4/6 đạt (IMM-04/05/08/09), còn IMM-11/12 ở PARTIAL.

---

*Hết báo cáo.*
