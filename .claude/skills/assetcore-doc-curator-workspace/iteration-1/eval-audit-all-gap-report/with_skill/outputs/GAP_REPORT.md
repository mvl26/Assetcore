# AssetCore — Báo cáo Gap tài liệu 17 module IMM

- **Ngày audit**: 2026-05-10
- **Phạm vi**: 17 module IMM-01 → IMM-17
- **Chuẩn so sánh**: `docs/template/` (9 file: README + 02–09) — section bắt buộc theo `MIGRATION_GUIDE.md` và light-touch recipes
- **Phương pháp**: kiểm tra tồn tại 9 file mỗi module + parse heading file 02 (Analysis & Design) — file lõi nhất; sample file khác bằng line count để xác định "đầy đủ vs khung rỗng"
- **Quy ước trạng thái**:
  - ✅ Đầy đủ — đủ 9 file, content >250 dòng/file, đủ section I.0–I.8 + II + III + IV + V
  - 🟡 Có nhưng thiếu — đủ 9 file nhưng thiếu vài section bắt buộc hoặc heading lệch template
  - ❌ Chưa có — không tồn tại folder `docs/imm-XX/`

---

## 1. Bảng tổng hợp 17 module

| Module | Tên (chính thức) | Khối | Đợt | Trạng thái docs | File thiếu | Section thiếu (notable) | Khuyến nghị |
|---|---|---|---|---|---|---|---|
| IMM-01 | Đánh giá nhu cầu và dự toán | A. KHỐI 1 | 2 | 🟡 Có nhưng thiếu | — | 02: thiếu I.0 Khảo sát As-Is, I.7 Risk, I.8 Roadmap, II.6 Process metrics, II.9 As-Is vs To-Be, III.4 UC relationships, V NFR table | Light-touch: thêm I.0, I.7, I.8 từ Architecture; bổ sung V NFR |
| IMM-02 | Thông số kỹ thuật và phân tích thị trường | A. KHỐI 1 | 2 | 🟡 Có nhưng thiếu | — | 02: thiếu I.5 KPI, I.6 Compliance, I.7 Risk, I.8 Roadmap, III.1 UC Diagram, III.2 Actor catalog, IV.3 State Machine, V NFR | Bổ sung lớn — sprint riêng cho I.5/I.6/V (KPI từ WHO Procurement, Compliance từ NĐ98) |
| IMM-03 | Đánh giá nhà cung cấp và quyết định mua sắm | A. KHỐI 1 | 2 | 🟡 Có nhưng thiếu | — | 02: thiếu I.0 Khảo sát, I.7 Risk, I.8 Roadmap, II.6 Process metrics | Light-touch: thêm I.0/I.7/I.8 |
| IMM-04 | Lắp đặt, định danh và kiểm tra ban đầu | B. KHỐI 2 | 1 | ✅ Đầy đủ | — | (đầy đủ I.0–I.8 + II.2–II.10 + III.1–III.5 + IV + V) | Giữ nguyên; cập nhật trường "Cập nhật" trong README |
| IMM-05 | Đăng ký, cấp phép và hồ sơ | B. KHỐI 2 | 1 | ✅ Đầy đủ | — | (đầy đủ tương tự IMM-04) | Giữ nguyên |
| IMM-06 | Đào tạo người dùng | B. KHỐI 2 | 2 | 🟡 Có nhưng thiếu | — | 02: thiếu I.5 KPI, I.6 Compliance, I.7 Risk, I.8 Roadmap, III.1 UC Diagram, III.2 Actor catalog, IV.3 State Machine, V NFR | Bổ sung lớn — KPI training (WHO HTM Performance), V NFR |
| IMM-07 | Theo dõi hiệu suất | C. KHỐI 3 | 3 | ❌ Chưa có | Toàn bộ 9 file | Toàn bộ | Sinh from-scratch theo §5 SKILL — nguồn WHO Performance + Architecture line 244–260 |
| IMM-08 | Bảo trì định kỳ | C. KHỐI 3 | 1 | 🟡 Có nhưng thiếu | — | 02: thiếu II.6 Process metrics, II.9 As-Is vs To-Be, III.4 UC relationships, III.5 chỉ có 1 phần, V.5–V.6 lệch tên | Light-touch: thêm II.6, II.9, III.4 |
| IMM-09 | Sửa chữa, phụ tùng và cập nhật phần mềm | C. KHỐI 3 | 1 | 🟡 Có nhưng thiếu | — | 02: tương tự IMM-08 — thiếu II.6, II.9, III.4 | Light-touch: thêm II.6, II.9, III.4 |
| IMM-10 | Hậu kiểm và tuân thủ | C. KHỐI 3 | 3 | ❌ Chưa có | Toàn bộ 9 file | Toàn bộ | Sinh from-scratch — nguồn WHO Post-market + NĐ98; phụ thuộc IMM-16 |
| IMM-11 | Hiệu năng và hiệu chuẩn | C. KHỐI 3 | 1 | 🟡 Có nhưng thiếu | — | 02: thiếu I.0, II.6, II.8 Exception flow, II.9, II.10, III.1 UC Diagram, III.2 Actor catalog, III.4, IV.4 Input-Output, V.4–V.6 | Bổ sung trung — III.1, III.2, V.4–V.6 từ template |
| IMM-12 | Bảo trì khắc phục | C. KHỐI 3 | 1 | 🟡 Có nhưng thiếu | — | 02: thiếu I.0, II.6, II.8, II.9, II.10, III.1, III.2, III.4, IV.4, V.4–V.6 | Bổ sung trung — đồng nhất với IMM-11 |
| IMM-13 | Ngừng sử dụng và điều chuyển | D. KHỐI 4 | 3 | ❌ Chưa có | Toàn bộ 9 file | Toàn bộ | Sinh from-scratch — nguồn WHO Decommissioning; gate với IMM-14 |
| IMM-14 | Giải nhiệm thiết bị | D. KHỐI 4 | 3 | ❌ Chưa có | Toàn bộ 9 file | Toàn bộ | Sinh from-scratch — đối soát kho/kế toán; phối hợp IMM-13 |
| IMM-15 | Theo dõi tồn kho phụ tùng | C. KHỐI 3 | 2 | 🟡 Có nhưng thiếu | — | 02: heading dùng dấu cách thay vì dấu chấm (`I.1 Pitch` thay `I.1. Pitch`) — lệch template; thiếu I.0 Khảo sát, I.7 Risk, I.8 Roadmap, III.4 UC relationships | Light-touch: chuẩn hóa heading sang dấu chấm + thêm I.0/I.7/I.8 |
| IMM-16 | Theo dõi tuân thủ | C. KHỐI 3 | 2 | 🟡 Có nhưng thiếu | — | 02: thiếu I.0, I.7, I.8, II.7 RACI section riêng (gộp vào II.5), III.1 UC Diagram, III.3 Actor catalog, IV State Machine cho Audit, V.6 Mở rộng | Light-touch: thêm I.0/I.7/I.8 + III.1/III.3 |
| IMM-17 | Phân tích dự đoán | C. KHỐI 3 | 3 | ❌ Chưa có | Toàn bộ 9 file | Toàn bộ | Sinh from-scratch — phụ thuộc dữ liệu IMM-07/08/09; defer sau wave 2 |

**Phụ chú IMM-00 (master/foundation, không nằm trong 17)**: ✅ Đầy đủ 9 file, content lớn nhất (4979 dòng tổng). Giữ nguyên — chỉ cập nhật cross-link khi sinh module thiếu.

---

## 2. Phân loại tổng kết

### 2.1 ✅ Đầy đủ (2 module)
- **IMM-04** — Lắp đặt, định danh và kiểm tra ban đầu
- **IMM-05** — Đăng ký, cấp phép và hồ sơ

(Đây là 2 module đợt 1, được BA viết kỹ làm reference cho các module khác)

### 2.2 🟡 Có nhưng thiếu (10 module)
- **Light-touch nhẹ** (chỉ thêm I.0/I.7/I.8 + vài table): IMM-01, IMM-03, IMM-08, IMM-09, IMM-15, IMM-16
- **Light-touch trung bình** (thêm UC Diagram + Actor catalog + V NFR): IMM-11, IMM-12
- **Bổ sung lớn** (thiếu I.5 KPI, I.6 Compliance, V NFR — cần workshop BA): IMM-02, IMM-06

### 2.3 ❌ Chưa có folder (5 module)
- **Đợt 3 — Operation/Performance**: IMM-07, IMM-10, IMM-17
- **Đợt 3 — End-of-life**: IMM-13, IMM-14

Tất cả đều thuộc **Đợt 3** trong roadmap Architecture (line 276–278). Khớp đúng kỳ vọng skill `module-catalog.md`.

---

## 3. Kế hoạch fill thiếu (sprint plan)

### Sprint 1 (1 tuần) — Light-touch nhẹ
**Mục tiêu**: Đồng bộ 6 module có doc gần đủ về template chuẩn.
- IMM-01, IMM-03, IMM-08, IMM-09, IMM-15, IMM-16
- Tác vụ mỗi module: thêm I.0 Khảo sát hiện trạng (từ WHO HTM tương ứng), I.7 Risk + I.8 Roadmap (từ Architecture line 276–278), II.6 Process metrics, II.9 As-Is vs To-Be table
- IMM-15: chuẩn hóa heading dấu chấm
- IMM-16: thêm III.1 UC Diagram + III.3 Actor catalog
- **Output**: ~30–50 dòng thêm mỗi file 02

### Sprint 2 (1 tuần) — Light-touch trung
**Mục tiêu**: Hoàn thiện 2 module calibration/corrective.
- IMM-11, IMM-12
- Tác vụ: thêm III.1 UC Diagram (Mermaid), III.2 Actor catalog (5–7 actor), II.10 Activity diagram cho UC chính, IV.4 Input-Output, V.4–V.6 NFR (mở rộng/UX/bảo trì)
- **Output**: ~80–150 dòng thêm mỗi file 02 + cập nhật 03 Diagrams

### Sprint 3 (2 tuần) — Bổ sung lớn (cần workshop BA)
**Mục tiêu**: Hoàn thiện 2 module planning yếu.
- IMM-02, IMM-06
- Tác vụ:
  - I.5 KPI: workshop với BA + Procurement / HR-Training để chốt KPI baseline (placeholder `*(Cần khảo sát baseline)*` trước khi có số thật)
  - I.6 Compliance: map NĐ98 + GMDN (IMM-02 gắn với phân loại thiết bị; IMM-06 gắn với competency theo TT/QĐ-BYT về đào tạo)
  - V NFR table đầy đủ 5–7 dòng
  - III.1 UC Diagram + III.2 Actor catalog
- **Output**: 200+ dòng thêm mỗi file 02 + cập nhật 05/06/07

### Sprint 4 (2–3 tuần) — Sinh from-scratch Đợt 3 (D + C cuối)
**Mục tiêu**: Tạo 5 module folder mới theo §5 SKILL.
- **Sprint 4a (1 tuần)**: IMM-13, IMM-14 (End-of-life — quan trọng cho audit cuối vòng đời)
  - Source: WHO Decommissioning; Architecture line 244–260; gate workflow với IMM-04/05
- **Sprint 4b (1 tuần)**: IMM-07, IMM-10 (Performance + Post-market — cần dữ liệu IMM-08/09 đã chạy)
  - Source: WHO Performance, WHO Post-market, NĐ98 hậu mại
- **Sprint 4c (1 tuần — defer)**: IMM-17 (Predictive — chờ data lake từ IMM-07/08/09 sau Wave 2)
- **Output**: 9 file × 5 module = 45 file mới. Mỗi file dùng template + placeholder `*(Sprint Wave X — sau khi BE scaffold)*` cho phần chưa đủ data

### Sprint 5 — Đồng bộ index & cross-reference
- Cập nhật `docs/README.md` (global index) với bảng 17 module + trạng thái mới
- Cập nhật mỗi `docs/imm-XX/README.md`: trường "Cập nhật" + cross-reference đầy đủ Architecture/WHO/GMDN
- Cập nhật `MIGRATION_GUIDE.md` nếu phát hiện pattern mới
- Cross-link với 4 source: GMDN, WHO HTM, `Ho_so_kien_truc_IMMIS.md`, template kit

---

## 4. Cross-check với template `docs/template/`

Template kit gồm 12 file: `00_README.md`, `01_Architecture.md`, `02_Analysis_Design.md`, `03_Diagrams.md`, `04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md`, `07_Testing_QA.md`, `08_Deployment.md`, `09_Release.md`, `10_Project_Management.md`, `MIGRATION_GUIDE.md`.

Tiêu chí "đầy đủ" cho 1 module (theo `00_README.md` template):
1. **README.md** — bảng metadata 5 dòng (Khối, Đợt, Owner, Trạng thái, Cập nhật) + link 8 file con
2. **02_Analysis_Design.md** — đủ I.0–I.8 (Khảo sát, Pitch, Lifecycle, Stakeholders, Scope, KPI, Compliance, Risk, Roadmap) + II.1–II.10 (BPMN As-Is/To-Be, Pain points, Decision, Process metrics, RACI, Exception, So sánh, Activity) + III.1–III.5 (UC Diagram, Actor catalog, UC Spec, UC relationships, UC↔US mapping) + IV.1–IV.5 (User Stories, Business Rules, State Machine, Input-Output, Edge cases) + V.1–V.7 (NFR Hiệu năng/Bảo mật/Khả dụng/Mở rộng/UX/Bảo trì/Tuân thủ)
3. **03 → 09** — heading chuẩn template, content thực thi (không placeholder rỗng)

**Lưu ý**: file `01_Architecture.md` và `10_Project_Management.md` là **shared docs** ở cấp project (không per-module). Đó là lý do bộ doc per-module chỉ có 8 file 02–09 + README.

**Phát hiện**:
- IMM-04, IMM-05 là 2 module duy nhất khớp 100% template.
- IMM-15 dùng style heading khác (dấu cách) — cần chuẩn hóa.
- 5 module ❌ chưa có folder → bắt buộc sinh from-scratch theo §5 SKILL, KHÔNG bịa DocType/API.

---

## 5. Rủi ro & lưu ý

- **Không bịa số liệu**: KPI baseline cho IMM-02/06/07/10/17 chưa có khảo sát thực tế — luôn dùng `*(Cần khảo sát baseline)*`.
- **Phụ thuộc chéo**: IMM-17 (Predictive) cần data từ IMM-07/08/09 chạy ≥6 tháng → defer doc-fill chi tiết đến Wave 3.
- **Compliance**: IMM-13/14 (Decommissioning) phải map đúng NĐ98 §32–34 (thanh lý) + QĐ phân loại GMDN — cross-check `docs/gmdn/` trước khi viết I.6.
- **Authority**: Không tự ý thay đổi Pitch/Stakeholder/Owner của các module 🟡 — phải qua BA review (nguyên tắc light-touch §3 SKILL).

---

## 6. Tổng kết số liệu

| Chỉ số | Giá trị |
|---|---|
| Tổng module IMM | 17 |
| ✅ Đầy đủ | 2 (12%) |
| 🟡 Có nhưng thiếu | 10 (59%) |
| ❌ Chưa có folder | 5 (29%) |
| File md hiện có (12 module + IMM-00) | 117 file |
| File md cần sinh mới (5 module × 9 file) | 45 file |
| Sprint dự kiến để hoàn thiện | 5 sprint (~7–8 tuần) |
| Module ưu tiên cao (đợt 1 chưa chuẩn) | IMM-08, 09, 11, 12 (light-touch sprint 1–2) |
| Module ưu tiên cao (đợt 3 chưa có) | IMM-13, 14 (sprint 4a — end-of-life audit) |

---

*Báo cáo này tuân thủ §3 SKILL light-touch — KHÔNG sinh file mới trong `docs/imm-XX/` trong lượt này. Output duy nhất là file GAP_REPORT.md trong workspace skill.*
