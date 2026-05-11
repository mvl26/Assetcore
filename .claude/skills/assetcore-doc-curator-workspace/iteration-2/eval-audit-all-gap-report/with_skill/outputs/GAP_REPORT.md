# AssetCore — Báo cáo Gap tài liệu 17 module

- Ngày audit: 2026-05-10
- Phạm vi: 17 module IMM-01 → IMM-17
- Chuẩn so sánh: `docs/template/` (9 file: README + 02→09)
- Quy ước trạng thái: ✅ Đầy đủ · 🟡 Có nhưng thiếu · ❌ Chưa có
- Nguồn ground-truth: `docs/architecture/Ho_so_kien_truc_IMMIS.md` (line 244–278)

## 1. Bảng tổng hợp 17 module

| Module | Tên | Khối | Đợt | Owner | Số file hiện có | Cập nhật cuối | Trạng thái | Section thiếu (notable) | Khuyến nghị |
|---|---|---|---|---|---|---|---|---|---|
| IMM-01 | Đánh giá nhu cầu và dự toán | A | 2 | PTP Khối 1 + Nhóm KH-TC | 9/9 | 2026-05-08 | ✅ | — (cần verify §I.6 NĐ98 mapping, §I.5 KPI baseline) | Light-touch: review §I.6 Compliance + §I.5 KPI baseline so với WHO Needs assessment. |
| IMM-02 | Thông số kỹ thuật và phân tích thị trường | A | 2 | PTP Khối 1 + Nhóm ĐT-HĐ-NCC | 9/9 | 2026-05-08 | ✅ | — (verify cross-link IMM-03 vendor scorecard) | Light-touch: bổ sung mapping WHO Procurement guide §benchmark; cross-link IMM-03. |
| IMM-03 | Đánh giá nhà cung cấp và quyết định mua sắm | A | 2 | PTP Khối 1 + Nhóm ĐT-HĐ-NCC | 9/9 | 2026-05-08 | ✅ | — (verify §I.6 NĐ98 + §II BPMN approved vendor list) | Light-touch: kiểm tra §I.6 NĐ98/2021, §II BPMN AVL maintenance. |
| IMM-04 | Lắp đặt, định danh và kiểm tra ban đầu | B | 1 | PTP Khối 2 + Workshop/TBYT + Mạng lưới TBYT | 9/9 | 2026-05-08 | ✅ | — (mature module, có code BE Wave 1) | Maintain: đồng bộ 04_Backend_Design với DocType thật; cập nhật trace IMM-05/08/11. |
| IMM-05 | Đăng ký, cấp phép và hồ sơ | B | 1 | PTP Khối 2 + Tổ HC-QLCL | 9/9 | 2026-05-08 | ✅ | — (verify §I.6 GMDN, QĐ 3107/69/847) | Light-touch: bổ sung mapping 3 Quyết định BYT (`docs/gmdn/`). |
| IMM-06 | Đào tạo người dùng | B | 2 | PTP Khối 2 + Tổ HC-QLCL + Mạng lưới TBYT | 9/9 | 2026-05-08 | ✅ | — (verify gate competency liên kết IMM-04/08/12) | Light-touch: cross-link gate vận hành từ IMM-04/08/12. |
| IMM-07 | Theo dõi hiệu suất | C | 3 | PTP Khối 2 | 0/9 | — | ❌ | Toàn bộ 9 file (README + 02→09) | Sinh from-scratch theo §5 SKILL: ưu tiên 02 + 03 placeholder; KPI baseline ghi *(Cần khảo sát)*; tham chiếu WHO Performance + IMM-08/09/12 dữ liệu nguồn. |
| IMM-08 | Bảo trì định kỳ | C | 1 | PTP Khối 2 + Workshop/TBYT | 9/9 | 2026-05-08 | ✅ | — (mature, Wave 1 đã code) | Maintain: đồng bộ DocType `PM Work Order` (đã modified); kiểm tra workflow `imm_08_*`. |
| IMM-09 | Sửa chữa, phụ tùng và cập nhật phần mềm | C | 1 | PTP Khối 2 + Workshop/TBYT | 9/9 | 2026-05-08 | ✅ | — (mature, Wave 1 đã code) | Maintain: đồng bộ `Asset Repair`, IMM-15 spare-part trace, change control firmware. |
| IMM-10 | Hậu kiểm và tuân thủ | C | 3 | PTP Khối 2 + Tổ HC-QLCL & Risk | 0/9 | — | ❌ | Toàn bộ 9 file | Sinh from-scratch: 02 + 04 skeleton; mapping recall/FSCA + CAPA (link IMM-16); WHO Post-market + Quyết định BYT. |
| IMM-11 | Hiệu năng và hiệu chuẩn | C | 1 | PTP Khối 2 + Workshop/TBYT | 9/9 | 2026-05-08 | ✅ | — (mature, Wave 1 đã code) | Maintain: đồng bộ `IMM Asset Calibration` (đã modified); certificate hiệu lực. |
| IMM-12 | Bảo trì khắc phục | C | 1 | PTP Khối 2 + Workshop/TBYT | 9/9 | 2026-05-08 | ✅ | — (mature, Wave 1 đã code) | Maintain: kiểm tra liên kết `Incident Report` ↔ `IMM CAPA Record` ↔ IMM-09. |
| IMM-13 | Ngừng sử dụng và điều chuyển | D | 3 | PTP Khối 2 + Mạng lưới TBYT | 0/9 | — | ❌ | Toàn bộ 9 file | Sinh from-scratch: nhấn replacement review + residual risk; WHO Decommissioning; chain trạng thái Asset → IMM-14. |
| IMM-14 | Giải nhiệm thiết bị | D | 3 | PTP Khối 2 | 0/9 | — | ❌ | Toàn bộ 9 file | Sinh from-scratch: closure record cuối vòng đời, đối soát asset–kho–kế toán; WHO Decommissioning + GMDN write-off. |
| IMM-15 | Theo dõi tồn kho phụ tùng | C | 2 | PTP Khối 1 + Kho trung tâm | 9/9 | 2026-05-08 | ✅ | — (verify cấp phát theo WO IMM-09) | Light-touch: bổ sung trace cấp phát ↔ IMM-09 WO; spare demand forecast. |
| IMM-16 | Theo dõi tuân thủ | C | 2 | Tổ HC-QLCL & Risk | 9/9 | 2026-05-08 | ✅ | — (verify scorecard + management review) | Light-touch: cross-link CAPA với IMM-10 và IMM-12; đồng bộ `IMM Audit Trail` (đã modified). |
| IMM-17 | Phân tích dự đoán | C | 3 | PTP Khối 2 + Tổ HC-QLCL & Risk | 0/9 | — | ❌ | Toàn bộ 9 file | Sinh from-scratch (skeleton): model governance + what-if; phụ thuộc IMM-07/08/09/11/12 dữ liệu; tránh bịa thuật toán. |

## 2. Phân loại tổng kết

- ✅ Đầy đủ (9/9 file, cập nhật 2026-05-08): **12 module** — IMM-01, 02, 03, 04, 05, 06, 08, 09, 11, 12, 15, 16.
- 🟡 Có nhưng thiếu: **0 module** (chưa phát hiện qua audit cấp file; cần audit cấp section ở vòng sau).
- ❌ Chưa có: **5 module** — IMM-07, IMM-10, IMM-13, IMM-14, IMM-17.

Tổng: 12 ✅ + 0 🟡 + 5 ❌ = 17 module.

> Ghi chú: audit này so ở mức **file count + README metadata**. Để phát hiện 🟡 (file có nhưng section thiếu, vd I.6 Compliance, II BPMN), cần vòng audit cấp section bằng grep heading vs template — sẽ thực hiện riêng.

## 3. Kế hoạch fill thiếu theo Đợt triển khai

Tham chiếu `Ho_so_kien_truc_IMMIS.md` line 276–278 (KHÔNG dùng P0/P1/P2).

### Đợt 1 — Wave 1 (registry, hồ sơ, PM/CM, calibration)
Module: IMM-04, 05, 08, 09, 11, 12.
- Trạng thái docs: **6/6 ✅**, không còn module thiếu.
- Hành động: **Maintain** — đồng bộ docs với code BE đã/đang sửa (xem `git status`: `pm_work_order`, `asset_repair`, `imm_asset_calibration`, `imm_audit_trail`, `incident_report`, `imm_capa_record`). Light-touch: cập nhật 04_Backend_Design + 05_API_Specification cho đúng hiện trạng.

### Đợt 2 — Wave 2 (needs, tech spec, vendor, training, spare, compliance)
Module: IMM-01, 02, 03, 06, 15, 16.
- Trạng thái docs: **6/6 ✅**, không còn module thiếu.
- Hành động: **Light-touch** — bổ sung §I.6 Compliance (NĐ98 + 3 QĐ-BYT GMDN) cho IMM-03/05; cross-link gate IMM-06 ↔ IMM-04/08/12; trace IMM-15 ↔ IMM-09 cấp phát phụ tùng.

### Đợt 3 — Wave 3 (performance, post-market, retirement, decommissioning, predictive)
Module: IMM-07, 10, 13, 14, 17.
- Trạng thái docs: **0/5**, **toàn bộ 5 module thiếu**.
- Hành động: **From-scratch** theo §5 SKILL với size budget 1100–1600 dòng/module. Thứ tự đề xuất:
  1. **IMM-13** (Ngừng sử dụng và điều chuyển) — phụ thuộc IMM-04/05 đã ổn định, dễ neo theo Asset state machine.
  2. **IMM-14** (Giải nhiệm thiết bị) — kế tiếp IMM-13, closure record cuối lifecycle.
  3. **IMM-07** (Theo dõi hiệu suất) — KPI/KRI; đầu vào từ IMM-08/09/11/12 đã chín muồi.
  4. **IMM-10** (Hậu kiểm và tuân thủ) — recall/FSCA, CAPA; cross-link IMM-16.
  5. **IMM-17** (Phân tích dự đoán) — skeleton last; phụ thuộc dữ liệu IMM-07/08/09/11/12.
- Cấm: bịa DocType field, bịa endpoint shape, bịa baseline KPI, bịa test case ID. Dùng placeholder *(Thiết kế trong sprint Wave 3)* / *(Cần khảo sát baseline)*.

## 4. Phụ chú IMM-00

`docs/imm-00/` đã có 9/9 file (README + 02→09), cập nhật 2026-05-08. **IMM-00 không nằm trong 17 module IMM-01→17** — đây là module master/foundation (cấu hình hệ thống, master data chung như Vendor, Location, Device Model, Role, Permission). Vai trò:

- Là **prerequisite** cho mọi module IMM-01→17 (master data + RBAC + audit trail nền).
- Không thuộc Đợt 1/2/3 phân loại theo Architecture line 276–278.
- Trạng thái docs: ✅ Đầy đủ — không cần fill thêm trong audit này, nhưng cần **maintain đồng bộ** với fixtures (`role.json`) và `setup/install.py` đã modify.
- Khuyến nghị: thêm 1 dòng "IMM-00 Foundation" trong `docs/README.md` index toàn cục để rõ ranh giới giữa master và 17 module nghiệp vụ.
