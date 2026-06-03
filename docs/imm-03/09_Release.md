# 09 — Hướng dẫn sử dụng & Release — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm

> ✅ Module LIVE — Wave 2. Backend và Frontend đã triển khai.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phiên bản | 0.0.2 |
| Ngày | 2026-05-27 |
| Trạng thái | LIVE — Wave 2 |
| Chính sách versioning | Tuân theo `assetcore/__init__.py = 0.0.2`; module docs đồng bộ phiên bản app. |

---

## I. Hướng dẫn sử dụng

### I.1 Giới thiệu

IMM-03 là module **Đánh giá Nhà cung cấp & Quyết định Mua sắm** trong hệ thống AssetCore. Module này giúp Bệnh viện thực hiện toàn bộ quy trình từ khi tiếp nhận Tiêu chí kỹ thuật (từ IMM-02) đến khi phát hành Quyết định mua sắm và tạo AC Purchase — theo đúng quy định của Luật Đấu thầu và ISO 13485.

**Đặc điểm nổi bật:**
- Danh sách Nhà cung cấp được Phê duyệt (AVL) quản lý theo nhóm thiết bị + hiệu lực
- Chấm điểm đa tiêu chí (kỹ thuật, thương mại, tài chính, hỗ trợ, tuân thủ)
- Tự động tạo AC Purchase khi quyết định được phê duyệt
- Bảng điểm nhà cung cấp cập nhật hàng quý

---

### I.2 Hướng dẫn theo vai trò

#### A. Cán bộ Đấu thầu – Hợp đồng – NCC (ĐT-HĐ-NCC Officer)

**Tạo hồ sơ nhà cung cấp:**

1. Đăng nhập vào AssetCore, vào menu **Khối 1 > Nhà cung cấp & Mua sắm > Nhà cung cấp**.
2. Nhấn **[+ Tạo profile]**.
3. Chọn Supplier đã có trong hệ thống (ví dụ: "Vinamed JSC").
4. Điền thông tin: Tên pháp lý, MST, Đại diện, Email, Nhóm thiết bị.
5. Nhấn tab **Chứng chỉ** → **[+ Thêm chứng chỉ]** → chọn loại (ISO 9001, ĐKLH BYT, ...) → nhập số chứng chỉ + ngày hết hạn → upload file scan.
6. Nhấn **[Lưu]**.

> **Lưu ý:** Chứng chỉ sắp hết hạn (≤ 30 ngày) hiển thị badge vàng ⚠. Hết hạn hiển thị badge đỏ. Cập nhật ngay để tránh ảnh hưởng AVL.

**Tạo hồ sơ đánh giá (Vendor Evaluation):**

Sau khi IMM-02 khóa Tiêu chí kỹ thuật, hệ thống tự động tạo phiếu đánh giá. Bạn sẽ nhận thông báo trên dashboard.

1. Mở phiếu **VE-26-xxxxx** vừa được tạo.
2. Tab **Candidates & RFQ**: Nhấn **[+ Thêm nhà cung cấp]** → chọn supplier.
   - Supplier trong AVL: hiển thị ✓ xanh.
   - Supplier ngoài AVL: hiển thị ⚠ cảnh báo → cần VP Block1 ký xác nhận trước khi nộp.
3. Thêm đủ số lượng theo phương án (Đấu thầu rộng rãi: ≥ 3 nhà cung cấp).
4. Nhấn **[Mở RFQ]** → gửi yêu cầu báo giá.
5. Nhận báo giá → nhập vào hệ thống: số báo giá, ngày báo giá, ngày hết hạn, giá, điều khoản.
6. Nhấn **[Nộp báo giá]** → trạng thái chuyển sang "Báo giá đã nhận".

**Tạo Quyết định mua sắm:**

Sau khi phiếu đánh giá được Đánh giá (Evaluated):

1. Vào tab **Tổng hợp** → xem nhà cung cấp được đề xuất.
2. Nhấn **[Tạo Quyết định mua sắm →]**.
3. Chọn **Phương án mua sắm** (hệ thống tự kiểm tra tính hợp pháp).
4. Điền nhà cung cấp trúng thầu, giá trúng thầu, nguồn vốn.
5. Đính kèm hợp đồng.
6. Chuyển sang PTP Khối 1 để trình BGĐ.

---

#### B. Cán bộ KH-TC (IMM Planning Officer)

**Chấm điểm nhóm Thương mại:**

1. Mở phiếu đánh giá được phân công (nhận thông báo qua email).
2. Vào tab **Chấm điểm** → chọn nhóm **Thương mại (Commercial)**.
3. Cho điểm từ 1 đến 5 cho từng tiêu chí (giá, điều khoản thanh toán, thời gian giao hàng).
4. Hệ thống tự tính điểm có trọng số.
5. Nhấn **[Lưu điểm]**.

**Xem Dashboard:**

1. Vào **Khối 1 > Nhà cung cấp & Mua sắm > Dashboard**.
2. Chọn kỳ cần xem (ví dụ: 2026-Q2).
3. Xem 7 chỉ số KPI: thời gian đánh giá, tỷ lệ AVL, điểm trung bình NCC...

---

#### C. Kỹ sư HTM (IMM HTM Engineer)

**Chấm điểm nhóm Kỹ thuật:**

1. Nhận thông báo khi có phiếu đánh giá cần chấm điểm kỹ thuật.
2. Mở phiếu → tab **Chấm điểm** → nhóm **Kỹ thuật (Technical)**.
3. Chấm 5 tiêu chí kỹ thuật: Đáp ứng tiêu chí, Uy tín thương hiệu, Hỗ trợ địa phương...
4. Nhấn **[Lưu điểm]**.

> **Lưu ý:** Điểm kỹ thuật có trọng số 35% — quan trọng nhất trong 5 nhóm.

---

#### D. Cán bộ TCKT (IMM Finance Officer)

**Chấm điểm nhóm Tài chính:**

1. Mở phiếu đánh giá → tab **Chấm điểm** → nhóm **Tài chính (Financial)**.
2. Chấm tiêu chí: Tình hình tài chính, Sức mạnh ngân hàng...
3. Nhấn **[Lưu điểm]**.

**Ghi nhận Ký hợp đồng:**

Sau khi Quyết định được Award:

1. Mở Quyết định mua sắm **PD-26-xxxxx**.
2. Nhập **Số hợp đồng**, **Ngày ký**, đính kèm file hợp đồng.
3. Nhấn **[Ký hợp đồng]**.

---

#### E. Nhóm QA Risk (IMM Risk Officer)

**Chấm điểm nhóm Tuân thủ:**

1. Mở phiếu đánh giá → tab **Chấm điểm** → nhóm **Tuân thủ (Compliance)**.
2. Chấm tiêu chí: Chứng chỉ ISO, Lịch sử NC, Kết quả audit...
3. Nhấn **[Lưu điểm]**.

**Thực hiện Supplier Audit:**

1. Nhận thông báo Supplier Audit từ scheduler (nhà cung cấp đến hạn > 12 tháng).
2. Mở **SA-26-xxxxx**.
3. Nhập ngày audit, kiểm toán viên, loại audit (Định kỳ/Đột xuất).
4. Nhập phát hiện (findings): mức nghiêm trọng, mô tả, hành động CAPA, người chịu trách nhiệm, hạn.
5. Nhấn **[Submit Audit]**.
   - Nếu có phát hiện Critical → hệ thống tự động đình chỉ AVL và email VP Block1.

**Đình chỉ AVL:**

1. Vào **Khối 1 > Nhà cung cấp & Mua sắm > AVL**.
2. Mở AVL cần đình chỉ.
3. Nhấn **[Đình chỉ AVL]**.
4. Nhập lý do (bắt buộc, tối thiểu 20 ký tự).
5. Xác nhận.

---

#### F. Trưởng phòng KH-TC / Trưởng khoa (IMM Department Head — PTP Khối 1)

**Trình BGĐ phê duyệt:**

1. Nhận thông báo Quyết định mua sắm cần trình.
2. Mở **PD-26-xxxxx** → kiểm tra đầy đủ thông tin.
3. Xác nhận envelope check (% ngân sách đã dùng).
4. Nhấn **[Trình BGĐ]** → trạng thái chuyển "Chờ phê duyệt".

---

#### G. Phó Giám đốc / Ban Giám đốc (IMM Board Approver — VP Block1)

**Phê duyệt AVL:**

1. Nhận thông báo AVL cần phê duyệt.
2. Mở AVL → kiểm tra nhà cung cấp, nhóm thiết bị, hiệu lực.
3. Đính kèm tài liệu phê duyệt.
4. Nhấn **[Phê duyệt AVL]**.

**Award Quyết định mua sắm:**

1. Nhận thông báo Quyết định đang "Chờ phê duyệt".
2. Mở **PD-26-xxxxx** → kiểm tra:
   - Nhà cung cấp trúng thầu và điểm đánh giá
   - Giá trúng thầu và % ngân sách
   - Nguồn vốn và chứng từ
   - Hợp đồng đính kèm
3. Nhấn **[Awarded ✓]** → xuất hiện hộp thoại xác nhận:
   - Nhà cung cấp: Vinamed JSC
   - Giá: 2.000.000.000 đồng (80% ngân sách)
   - Nguồn vốn: NSNN
4. Xác nhận → hệ thống tạo AC Purchase tự động.
5. Toast thông báo "Awarded — AC Purchase AC-PUR-2026-00112 đã tạo".

---

### I.3 Từ điển trạng thái

**Vendor Evaluation:**

| Trạng thái | Ý nghĩa |
|---|---|
| Draft | Phiếu mới tạo, chưa mở RFQ |
| Open RFQ | Đã gửi yêu cầu báo giá cho nhà cung cấp |
| Báo giá đã nhận | Đủ báo giá hợp lệ |
| Đã đánh giá | Chấm điểm đủ 5 nhóm, đã submit |
| Đã huỷ | Huỷ bỏ |

**Procurement Decision:**

| Trạng thái | Ý nghĩa |
|---|---|
| Draft | Quyết định mới tạo |
| Method Selected | Đã chọn phương án mua sắm |
| Negotiation | Đang thương lượng |
| Award Recommended | ĐT-HĐ-NCC đề xuất nhà cung cấp |
| Pending Approval | Chờ BGĐ phê duyệt |
| Awarded | BGĐ đã phê duyệt — AC Purchase đã tạo |
| Contract Signed | Đã ký hợp đồng |
| PO Issued | Đã phát hành AC Purchase |
| Cancelled | Đã huỷ |

**AVL (Danh sách NCC được phê duyệt):**

| Trạng thái | Ý nghĩa |
|---|---|
| ✓ Approved (xanh) | Được phê duyệt, trong hiệu lực |
| ⚠ Conditional (vàng) | Phê duyệt có điều kiện |
| 🚫 Suspended (đỏ) | Đình chỉ — không được dùng |
| Expired (xám) | Hết hạn — cần gia hạn |

---

### I.4 FAQ

**Q1: Tôi không thấy nút "Tạo hồ sơ nhà cung cấp" — tại sao?**

A: Nút này chỉ hiển thị với vai trò **ĐT-HĐ-NCC Officer (IMM Procurement Officer)**. Nếu bạn cần tạo, liên hệ CMMS Admin để được cấp quyền.

---

**Q2: Tôi thêm nhà cung cấp vào phiếu đánh giá và thấy cảnh báo "Vendor ngoài AVL". Có phải xóa đi không?**

A: Không cần xóa. Cảnh báo chỉ nhắc nhở rằng nhà cung cấp này chưa có trong Danh sách được Phê duyệt (AVL) cho danh mục thiết bị này. Bạn vẫn có thể giữ nhà cung cấp đó, nhưng cần **VP Block1 ký xác nhận** vào trường "Sign-off non-AVL" trước khi nộp phiếu. Nếu thiếu, hệ thống sẽ không cho Submit.

---

**Q3: Tôi cố tạo AC Purchase cho thiết bị y tế nhưng bị lỗi "VR-03-08: phải đi qua IMM-03". Phải làm sao?**

A: Đây là gate bắt buộc theo quy trình mua sắm TBYT. Bạn cần:
1. Hoàn tất quy trình IMM-03: Vendor Evaluation → Procurement Decision → Awarded.
2. Khi VP Block1 Award, AC Purchase sẽ **tự động tạo** — không cần tạo thủ công.

---

**Q4: Giá trúng thầu hiển thị "***" — tôi không xem được?**

A: Trường giá trúng thầu được bảo vệ ở cấp độ phân quyền cao. Chỉ các vai trò **KH-TC, TCKT, PTP Khối 1, VP Block1, CMMS Admin** mới xem được. Liên hệ CMMS Admin nếu bạn cần quyền truy cập.

---

**Q5: AVL đến hạn nhưng tôi không nhận được email cảnh báo?**

A: Hệ thống gửi cảnh báo tự động 60 ngày và 30 ngày trước hết hạn, qua scheduler chạy hàng ngày. Kiểm tra:
- Email trong spam/junk folder
- Địa chỉ email tài khoản còn đúng không
- Liên hệ CMMS Admin để kiểm tra scheduler job logs

---

### I.5 Phím tắt & Tips

| Tình huống | Cách nhanh |
|---|---|
| Tìm nhà cung cấp theo nhóm | Filter "Nhóm thiết bị" trên Vendor Profile List |
| Xem AVL sắp hết hạn | Filter "AVL Status = Approved" + sort by "valid_to" ASC |
| Xuất Decision thành PDF | Nút [Xuất PDF] trên DecisionDetail sau khi Awarded |
| Xem lịch sử AC Purchase từ Decision | Tab "AC Purchase" xuất hiện sau khi Awarded |
| So sánh 3 nhà cung cấp nhanh | Tab "Tổng hợp" trên EvaluationDetail |

---

### I.6 Liên hệ hỗ trợ

| Vấn đề | Liên hệ |
|---|---|
| Quyền truy cập, cấu hình | CMMS Admin — `cmms.admin@hospital.vn` |
| Quy trình nghiệp vụ mua sắm | Phòng KH-TC — `kh.tc@hospital.vn` |
| Lỗi kỹ thuật, bug | IT Support — `it.support@hospital.vn` |
| Câu hỏi về AVL, audit NCC | Phòng QA Risk — `qa.risk@hospital.vn` |

---

## II. Release Notes — v1.0.0

> Dự kiến release khi Wave 2 hoàn thành triển khai.

### II.0. Commit History (Wave 2)

| Commit | Tiêu đề | Phạm vi IMM-03 |
|---|---|---|
| `810179e` | feat (BE+FE): add module 1,2,3, update UI dashboard (/launcher) | Khởi tạo IMM-03: 11 DocType, 3 Workflow, `services/imm03.py` (496 LOC), `api/imm03.py` (379 LOC), patch `v3_1.003_install_imm03.py`, FE views `imm03/AvlListView`, `imm03/DecisionListView`, `imm03/DecisionDetailView`, `imm03/VendorEvalListView`, `imm03/VendorEvalDetailView` + `stores/imm03.ts`, `types/imm03.ts`, `api/imm03.ts` |
| `0b22048` | feat: add depreciation, PO, UOM and update sidebar | AC Purchase DocType + child tables (target cho `imm_procurement_decision` custom field) |
| `66d9f81` | refactor: update module workflows and fix procurement issues | Tinh chỉnh 3 Workflow JSON; fix workflow upsert |
| `82a9607` | fix (FE): Modal create new needs-requests, UI sidebar, add filter for imm-1,2,3 | FE filter cho list view IMM-03 |
| `33a9668` | refactor: restructure FE/BE folders and update UI forms | Move views: `frontend/src/views/imm03/*` → `frontend/src/views/procurement/*` |
| `d56c0cd` | fix: resolve Wave 1 & 2 bugs and enhance AI agents | Bug fixes IMM-03 service/API |
| `fce3655` | fix(FE): update fullname user and list view some page | FE polish |
| `4a3ad1c` | fix: resolve all conflicts and sync Wave 2 with global formatters | Wave 2 sync (final) |

### II.1 Tóm tắt

IMM-03 v1.0.0 bổ sung toàn bộ chức năng **Đánh giá Nhà cung cấp & Quyết định Mua sắm** vào AssetCore, hoàn thiện vòng lặp từ Tiêu chí kỹ thuật (IMM-02) đến AC Purchase, đảm bảo tuân thủ Luật Đấu thầu 22/2023 và ISO 13485 §7.4.

### II.2 Tính năng mới

| # | Tính năng | Mô tả |
|---|---|---|
| F-01 | Hồ sơ nhà cung cấp mở rộng | Custom fields trên AC Supplier: AVL status, chứng chỉ pháp lý, điểm tổng hợp |
| F-02 | Quản lý AVL theo danh mục | IMM AVL Entry với workflow Draft → Approved → Suspended → Expired; auto-expiry scheduler |
| F-03 | Chấm điểm đa tiêu chí | 5 nhóm tiêu chí (35/25/10/15/15%); chấm điểm phân vai (HTM/KH-TC/TCKT/QA); auto-compute weighted_score |
| F-04 | Procurement Decision 9 states | Hỗ trợ 5 phương án mua sắm; validate hợp pháp tự động (G04) |
| F-05 | Mint AC Purchase tự động | Award Decision → tạo AC Purchase với full link bidirectional |
| F-06 | Vendor Scorecard quarterly | Tổng hợp KPI từ IMM-04/09/15/10; radar chart 5 chiều |
| F-07 | Supplier Audit định kỳ | 12 tháng auto-task; findings + CAPA; Critical → auto Suspend AVL |
| F-08 | Dashboard 7 KPI | Lead time, AVL coverage, avg score, pick rate, audit rate, NC rate, cost saving |
| F-09 | Gate PO TBYT (VR-03-08) | AC Purchase TBYT bắt buộc có IMM Procurement Decision |

### II.3 Cải tiến so với quy trình cũ

| Trước | Sau |
|---|---|
| Đánh giá NCC thủ công (Excel) | Chấm điểm online, auto weighted-score |
| Không có AVL chính thức | AVL với hiệu lực, cảnh báo tự động |
| PO tạo trực tiếp, không kiểm soát | PO chỉ được tạo từ Decision Awarded |
| Scorecard NCC không tồn tại | Scorecard quarterly, radar 5 chiều |
| Không có audit trail mua sắm | IMM Audit Trail bất biến toàn quy trình |

### II.4 Breaking Changes

- `AC Purchase` với item TBYT **bắt buộc** có field `imm_procurement_decision` từ v1.0.0. PO tạo thủ công cho TBYT sẽ bị block.
- Vendor master `AC Supplier` được bổ sung fields IMM — không ảnh hưởng dữ liệu hiện có (fields thêm, không sửa).

### II.5 Known Issues (v1.0.0)

| Issue | Mô tả | Dự kiến fix |
|---|---|---|
| KI-01 | Scorecard quarterly chưa hỗ trợ export Excel | v1.1.0 |
| KI-02 | AVL timeline widget chưa hỗ trợ responsive mobile | v1.1.0 |
| KI-03 | Decision PDF export chưa có chữ ký số | v1.2.0 |

### II.6 Downtime

- Dự kiến downtime: 30–60 phút trong maintenance window
- Thực hiện ngoài giờ cao điểm (8:00–10:00 sáng)

### II.7 Tương thích

| Component | Version |
|---|---|
| AssetCore Wave 1 | Bắt buộc (AC Supplier, AC Purchase, IMM Audit Trail) |
| IMM-01 (Plan) | Bắt buộc (plan_ref + budget envelope) |
| IMM-02 (Tech Spec) | Bắt buộc (spec_locked event) |
| IMM-04 (Commissioning) | Tùy chọn (scorecard Delivery KPI) |
| IMM-09 (Repair) | Tùy chọn (scorecard Aftersales KPI) |
| IMM-15 (Spare Parts) | Tùy chọn (scorecard Spare KPI) |

---

## III. Traceability Matrix

| Req ID | Loại | Mô tả | Tài liệu gốc | Design | Code | Test ID | UAT ID | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| FR-03-01 | FR | Vendor Profile extension AC Supplier | IMM-03_Functional_Specs §4 | 04_Backend §IV.1 | `imm03.create_vendor_profile` | TestImm03API.test_create_vendor_profile_ok | UAT-IMM03-01 | PLANNED |
| FR-03-02 | FR | AVL Entry per category 1–3 năm | IMM-03_Functional_Specs §4 | 04_Backend §II.3 | `imm03.create_avl_entry` + `activate_avl` | TestImm03GateChecks | UAT-IMM03-02 | PLANNED |
| FR-03-03 | FR | Auto-seed Eval từ imm02_spec_locked | IMM-03_Functional_Specs §4 | 04_Backend §V | `seed_evaluation_from_spec` | TestImm03FullFlow | UAT-IMM03-04 | PLANNED |
| FR-03-04 | FR | Add candidate + AVL check | IMM-03_Functional_Specs §4 | 04_Backend §V | `add_vendor_to_evaluation` + `_vr02_avl_check` | TestImm03ValidationRules.test_vr02 | UAT-IMM03-05 | PLANNED |
| FR-03-05 | FR | RFQ → Quotation Received với validity check | IMM-03_Functional_Specs §4 | 04_Backend §V | `_vr03_quotation_validity` + `_validate_gate_g02` | TestImm03ValidationRules.test_vr03 | UAT-IMM03-06 | PLANNED |
| FR-03-06 | FR | 5-group criteria chấm điểm có trọng số | IMM-03_Functional_Specs §4 | 04_Backend §V | `compute_eval_score` | TestImm03ScoringAlgorithm | UAT-IMM03-07 | PLANNED |
| FR-03-07 | FR | Recommended vendor auto-compute | IMM-03_Functional_Specs §4 | 04_Backend §V | `compute_eval_score` (sort + recommend) | TestImm03ScoringAlgorithm.test_sort | UAT-IMM03-07 | PLANNED |
| FR-03-08 | FR | Decision 5 phương án mua sắm | IMM-03_Functional_Specs §4 | 04_Backend §VII.2 | `create_decision` | TestImm03WorkflowTransitions | UAT-IMM03-08 | PLANNED |
| FR-03-09 | FR | Validate phương án hợp pháp (G04) | IMM-03_Functional_Specs §4 | 04_Backend §V | `_validate_gate_g04` | TestImm03GateChecks.test_gate_g04 | UAT-IMM03-08 | PLANNED |
| FR-03-10 | FR | Mint AC Purchase khi Awarded | IMM-03_Functional_Specs §4 | 04_Backend §V | `award_decision` | TestImm03FullFlow.test_full_flow | UAT-IMM03-09 | PLANNED |
| FR-03-11 | FR | Cập nhật Plan Line status = Awarded | IMM-03_Functional_Specs §4 | 04_Backend §V | `award_decision` | TestImm03AuditTrail | UAT-IMM03-09 | PLANNED |
| FR-03-12 | FR | Workflow 3 loại (Eval/Decision/AVL) | IMM-03_Functional_Specs §4 | 04_Backend §VII | workflow JSON files | TestImm03WorkflowTransitions | UAT-IMM03-02..09 | PLANNED |
| FR-03-13 | FR | Audit trail bất biến | IMM-03_Functional_Specs §4 | 04_Backend §V | `_vr06_immutable_lifecycle_events` | TestImm03AuditTrail.test_immutable | UAT-IMM03-09 | PLANNED |
| FR-03-14 | FR | Vendor Scorecard quarterly | IMM-03_Functional_Specs §4 | 04_Backend §VIII | `update_vendor_scorecard` | TestImm03ScorecardScheduler | UAT-IMM03-11 | PLANNED |
| FR-03-15 | FR | Supplier Audit periodic 12 tháng | IMM-03_Functional_Specs §4 | 04_Backend §VIII | `check_audit_due` | TestImm03FullFlow | UAT-IMM03-12 | PLANNED |
| FR-03-16 | FR | AVL expiry auto + cảnh báo 60/30d | IMM-03_Functional_Specs §4 | 04_Backend §VIII | `check_avl_expiry` | TestImm03FullFlow.test_avl_lifecycle | UAT-IMM03-03 | PLANNED |
| FR-03-17 | FR | Dashboard 7 KPI | IMM-03_Functional_Specs §4 | 05_API §3.15 | `dashboard_kpis` | TestImm03API.test_dashboard | — | PLANNED |
| BR-03-01 | BR | 1 Spec ↔ 1 Decision Awarded | IMM-03_Module_Overview §8 | 04_Backend §V | `_vr07_unique_decision_per_spec` | TestImm03ValidationRules.test_vr07 | UAT-IMM03-09 | PLANNED |
| BR-03-08 | BR | PO TBYT phải qua Decision | IMM-03_Module_Overview §8 | 04_Backend §V | `validate_ac_purchase_imm_link` | TestImm03AcPurchaseGate | UAT-IMM03-10 | PLANNED |
| VR-03-01 | VR | Min candidate phù hợp method | IMM-03_Technical_Design §5 | 04_Backend §V | `_vr01_min_candidates` | TestImm03ValidationRules.test_vr01 | UAT-IMM03-05 | PLANNED |
| VR-03-02 | VR | Non-AVL cần sign-off | IMM-03_Technical_Design §5 | 04_Backend §V | `_vr02_avl_check` | TestImm03ValidationRules.test_vr02 | UAT-IMM03-05 | PLANNED |
| VR-03-03 | VR | Quotation validity | IMM-03_Technical_Design §5 | 04_Backend §V | `_vr03_quotation_validity` | TestImm03ValidationRules.test_vr03 | UAT-IMM03-06 | PLANNED |
| VR-03-04 | VR | Envelope ≤ 105% | IMM-03_Technical_Design §5 | 04_Backend §V | `_vr04_decision_within_envelope` | TestImm03ValidationRules.test_vr04 | UAT-IMM03-08 | PLANNED |
| VR-03-05 | VR | Winner có AVL Active | IMM-03_Technical_Design §5 | 04_Backend §V | `_vr05_avl_active_required` | TestImm03ValidationRules.test_vr05 | UAT-IMM03-09 | PLANNED |
| NFR-03-01 | NFR | Load vendor list 5000 < 2s | IMM-03_Functional_Specs §5 | 04_Backend §IX | DB indexes | Performance test | — | PLANNED |
| NFR-03-02 | NFR | Mint PO < 3s | IMM-03_Functional_Specs §5 | 04_Backend §V | `award_decision` | Performance test | UAT-IMM03-09 | PLANNED |
| NFR-03-06 | NFR | Scorecard idempotent | IMM-03_Functional_Specs §5 | 04_Backend §V | `update_vendor_scorecard` | TestImm03ScorecardScheduler | UAT-IMM03-11 | PLANNED |

### III.1 Coverage Summary

| Loại | Tổng | Có test | Có UAT | Coverage |
|---|---|---|---|---|
| Functional Requirements (FR) | 18 | 17 | 12 | 94% |
| Business Rules (BR) | 8 | 8 | 8 | 100% |
| Validation Rules (VR) | 7 | 7 | 6 | 100% |
| Gates | 5 | 5 | 5 | 100% |
| Non-Functional (NFR) | 6 | 3 | 1 | 50% |

### III.2 Quy ước cập nhật Traceability

- Khi implement xong một function: cập nhật cột "Code" với tên function/file
- Khi test pass: cập nhật "Test ID" với class.method
- Khi UAT pass: đổi "Trạng thái" từ PLANNED → PASS
- Khi release: đổi PASS → RELEASED + ghi version
