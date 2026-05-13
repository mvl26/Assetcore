# UAT Final Entry Criteria — IMM-04
# Lắp đặt, Định danh và Kiểm tra Ban đầu Thiết bị Y tế
# Hệ thống: AssetCore / IMMIS v1.0

---

**Mã tài liệu:** ASSETCORE-IMM04-UAT-ENTRY-v1.0
**Ngày đánh giá:** ____/____/2026
**Người tổng hợp:** _______________________
**Site kiểm tra:** _______________________ (URL Sandbox)

> [!CAUTION]
> UAT Final **KHÔNG ĐƯỢC PHÉP BẮT ĐẦU** cho đến khi tất cả tiêu chí bắt buộc (cột **Bắt buộc = ★**) đều ở trạng thái ✅ PASS và được ký xác nhận bởi đúng Owner.

---

## NHÓM 1 — CẤU HÌNH HỆ THỐNG

| ID | Tiêu chí | B.Buộc | Owner | Bằng chứng xác nhận | Kết quả |
|---|---|---|---|---|---|
| CFG-01 | `bench migrate` chạy thành công, không có lỗi traceback | ★ | Dev Lead | Screenshot terminal output cuối cùng của `bench migrate` | ☐ Pass ☐ Fail |
| CFG-02 | Hệ thống đang chạy đúng version `assetcore v1.0` | ★ | Dev Lead | Output `bench version` hoặc git tag `imm04-sandbox-v1` | ☐ Pass ☐ Fail |
| CFG-03 | Timezone hệ thống đặt là `Asia/Ho_Chi_Minh` | ★ | Sys Admin | System Settings → Time Zone = Asia/Ho_Chi_Minh (screenshot) | ☐ Pass ☐ Fail |
| CFG-04 | Email server đã cấu hình và gửi được test email | — | Sys Admin | Gửi test email từ menu Email Queue, xác nhận nhận được | ☐ Pass ☐ Fail |
| CFG-05 | Module `AssetCore` xuất hiện đúng trong menu điều hướng | ★ | Dev Lead | Screenshot menu sau khi login với account user thường | ☐ Pass ☐ Fail |
| CFG-06 | 3 Custom DocType có thể mở form New mà không lỗi 404 hoặc 500 | ★ | Dev Lead | Mở `/app/asset-commissioning/new`, `/app/asset-qa-non-conformance/new` | ☐ Pass ☐ Fail |
| CFG-07 | Naming series sinh ID đúng format `IMM04-26-04-00001` (có padding tháng) | ★ | Dev Lead | Tạo 3 form liên tiếp, chụp ảnh ID tự sinh | ☐ Pass ☐ Fail |
| CFG-08 | Scheduled jobs (Cronjob SLA + Hold aging) đã được đăng ký | — | Dev Lead | `bench --site X scheduled-jobs` liệt kê đủ 3 jobs | ☐ Pass ☐ Fail |

**Nhóm 1 — Tổng:** ___/8 Pass (Bắt buộc: ___/6 Pass)

---

## NHÓM 2 — DỮ LIỆU

| ID | Tiêu chí | B.Buộc | Owner | Bằng chứng xác nhận | Kết quả |
|---|---|---|---|---|---|
| DAT-01 | 5 Item mẫu (incl. 1 item có `custom_is_radiation=1`) đã tạo đủ | ★ | QA Lead | Screenshot Item List có đủ 5 items; item X-Quang tick radiation | ☐ Pass ☐ Fail |
| DAT-02 | 3 Supplier mẫu đã tạo và link với Item đúng | ★ | QA Lead | Screenshot Supplier list + 1 PO đã có Supplier liên kết | ☐ Pass ☐ Fail |
| DAT-03 | 5 Purchase Order mẫu (PO-2026-0041 → 0045) đã tạo và ở status `To Bill` | ★ | QA Lead | Screenshot PO List với 5 records đúng status | ☐ Pass ☐ Fail |
| DAT-04 | Department (Khoa/Phòng) đã tạo đủ: ICU, CĐHA, Ngoại | ★ | QA Lead | Screenshot Department List | ☐ Pass ☐ Fail |
| DAT-05 | Field `custom_is_radiation` đã xuất hiện trên form Item | ★ | Dev Lead | Mở item Máy X-Quang, thấy field radiation và giá trị = 1 | ☐ Pass ☐ Fail |
| DAT-06 | Custom fields (`custom_vendor_serial`, `custom_internal_qr`, `custom_comm_ref`) đã xuất hiện trên form Asset | ★ | Dev Lead | Mở bất kỳ Asset record, scroll tìm 3 fields trên | ☐ Pass ☐ Fail |
| DAT-07 | Danh sách chỉ tiêu Baseline Test đã được Trưởng Workshop xác nhận phù hợp thực tế | ★ | Trưởng Workshop | Email/văn bản xác nhận của Trưởng Workshop | ☐ Pass ☐ Fail |
| DAT-08 | Danh sách loại hồ sơ trong Checklist (bao gồm "Biên bản bàn giao") đã được TBYT xác nhận | ★ | PTP Khối 2 / TBYT | Email/văn bản xác nhận của Phòng TBYT | ☐ Pass ☐ Fail |

**Nhóm 2 — Tổng:** ___/8 Pass (Bắt buộc: ___/8 Pass)

---

## NHÓM 3 — WORKFLOW

| ID | Tiêu chí | B.Buộc | Owner | Bằng chứng xác nhận | Kết quả |
|---|---|---|---|---|---|
| WFL-01 | Workflow `IMM-04 Workflow` đã gắn đúng vào DocType `Asset Commissioning` | ★ | Dev Lead | Mở form Commissioning mới → thấy field `Workflow State` = Draft | ☐ Pass ☐ Fail |
| WFL-02 | Tất cả 11 states xuất hiện đúng tên trong Workflow Builder | ★ | Dev Lead | Screenshot Workflow graph đủ 11 nodes | ☐ Pass ☐ Fail |
| WFL-03 | Transition Draft → Pending_Doc_Verify hoạt động (nút đúng label) | ★ | QA Lead | Thực hiện thao tác, chụp màn hình trước/sau | ☐ Pass ☐ Fail |
| WFL-04 | Transition To_Be_Installed → Installing hoạt động | ★ | QA Lead | Thực hiện thao tác với dữ liệu TC-01 | ☐ Pass ☐ Fail |
| WFL-05 | Transition Initial_Inspection → Re_Inspection khi có Fail (VR-03b) | ★ | QA Lead | Chạy TC-04 đến bước này, chụp màn hình state change | ☐ Pass ☐ Fail |
| WFL-06 | Transition Re_Inspection → Clinical_Release sau khi đóng NC | ★ | QA Lead | Chạy TC-05 end-to-end, chụp màn hình state = Clinical_Release | ☐ Pass ☐ Fail |
| WFL-07 | Transition Clinical_Release → Submit (docstatus=1) tạo Asset | ★ | Dev Lead | Sau Submit: Asset hiện trong `/app/asset`; `final_asset` có giá trị | ☐ Pass ☐ Fail |
| WFL-08 | Transition vào `Clinical_Hold` khi thiết bị bức xạ chưa có giấy phép | ★ | QA Lead | Chạy TC-04 phần bức xạ; xác nhận state = Clinical_Hold | ☐ Pass ☐ Fail |
| WFL-09 | Không có dead-state (state không có transition nào dẫn ra) | ★ | Dev Lead | Review Workflow graph; mọi state có ít nhất 1 outgoing transition | ☐ Pass ☐ Fail |
| WFL-10 | Action button label hiển thị tiếng Việt (không phải next state code) | — | Dev Lead | Screenshot workflow buttons trên form | ☐ Pass ☐ Fail |

**Nhóm 3 — Tổng:** ___/10 Pass (Bắt buộc: ___/9 Pass)

---

## NHÓM 4 — PERMISSION

| ID | Tiêu chí | B.Buộc | Owner | Bằng chứng xác nhận | Kết quả |
|---|---|---|---|---|---|
| PRM-01 | 6 Custom Role đã tồn tại trong hệ thống | ★ | CMMS Admin | Screenshot Role List filter "Custom = Yes" | ☐ Pass ☐ Fail |
| PRM-02 | 6+ User test đã được tạo và gán đúng Role (1 user/role) | ★ | CMMS Admin | Screenshot User List + Has Role list cho từng user | ☐ Pass ☐ Fail |
| PRM-03 | **[A7]** `HTM Technician` KHÔNG thấy nút Approve/Submit ở state Clinical_Release | ★ | QA Lead + QMS | Login bằng account HTM Tech, mở phiếu ở Clinical_Release, chụp màn hình không có nút | ☐ Pass ☐ Fail |
| PRM-04 | `VP Block2` thấy nút Submit ở state Clinical_Release | ★ | QA Lead | Login bằng VP Block2, thấy nút, chụp màn hình | ☐ Pass ☐ Fail |
| PRM-05 | `HTM Technician` KHÔNG thể tạo Asset trực tiếp trong /app/asset | ★ | QA Lead | Login HTM Tech, vào /app/asset, xác nhận không có nút New hoặc bị chặn | ☐ Pass ☐ Fail |
| PRM-06 | `field custom_is_radiation` trên Item bị khóa với HTM Technician | ★ | QA Lead + QMS | Login HTM Tech, mở Item có radiation=1, field không thể sửa | ☐ Pass ☐ Fail |
| PRM-07 | `penalty_amount` trong NC chỉ hiện với VP Block2 (perm level 1) | ★ | QA Lead | Login HTM Tech: field ẩn. Login VP Block2: field hiện | ☐ Pass ☐ Fail |
| PRM-08 | `CMMS Admin` KHÔNG thể Cancel phiếu đã Submit | ★ | QA Lead | Login CMMS Admin, mở phiếu đã Submit, xác nhận không có nút Cancel | ☐ Pass ☐ Fail |
| PRM-09 | `QA Risk Team` chỉ edit được field `qa_license_doc` (không sửa được field khác) | ★ | QA Lead | Login QA Risk Team, thử sửa `vendor_serial_no` → bị chặn | ☐ Pass ☐ Fail |

**Nhóm 4 — Tổng:** ___/9 Pass (Bắt buộc: ___/9 Pass)

---

## NHÓM 5 — VALIDATION

| ID | Tiêu chí | B.Buộc | Owner | Bằng chứng xác nhận | Kết quả |
|---|---|---|---|---|---|
| VAL-01 | **VR-01**: Nhập Serial trùng → lỗi đỏ tiếng Việt, không Save được | ★ | QA Lead | Chạy UT-01: screenshot lỗi + state không đổi | ☐ Pass ☐ Fail |
| VAL-02 | **VR-02**: Submit thiếu C/Q → lỗi block, không chuyển state | ★ | QA Lead | Chạy TC-02: screenshot lỗi block | ☐ Pass ☐ Fail |
| VAL-03 | **VR-03a**: Fail row không có fail_note → không Save được | ★ | QA Lead | Chạy UT-03: screenshot lỗi | ☐ Pass ☐ Fail |
| VAL-04 | **VR-03b**: Có Fail row → không chuyển sang Release, bắt buộc Re_Inspection | ★ | QA Lead | Chạy TC-04: screenshot state = Re_Inspection | ☐ Pass ☐ Fail |
| VAL-05 | **VR-04**: NC Open → block Release → lỗi đỏ tiếng Việt | ★ | QA Lead | Chạy UT-02 hoặc TC-04: screenshot lỗi VR-04 | ☐ Pass ☐ Fail |
| VAL-06 | **VR-06**: Site Checklist có Fail critical → block chuyển sang Installing | ★ | QA Lead | Chạy TC-03: screenshot block tại Site Gate | ☐ Pass ☐ Fail |
| VAL-07 | **VR-07**: Thiết bị bức xạ + không có license → auto Clinical_Hold | ★ | QA Lead | Chạy TC-04 phần bức xạ: screenshot state = Clinical_Hold | ☐ Pass ☐ Fail |
| VAL-08 | **VR-08**: Cảnh báo khi Serial < 4 ký tự (hoặc block nếu đã nâng cấp theo ISS-06) | ★ | QA Lead | Gõ "AB" vào vendor_serial_no → Toast cảnh báo hiện | ☐ Pass ☐ Fail |
| VAL-09 | Back-date: Ngày lắp đặt < ngày PO → server throw lỗi | — | QA Lead | Sửa installation_date thành ngày trước PO, lưu → lỗi hiện | ☐ Pass ☐ Fail |
| VAL-10 | Tất cả error message hiển thị tiếng Việt (không có thông báo tiếng Anh từ server) | ★ | QA Lead | Trigger từng VR-01 đến VR-08, chụp ảnh message | ☐ Pass ☐ Fail |

**Nhóm 5 — Tổng:** ___/10 Pass (Bắt buộc: ___/9 Pass)

---

## NHÓM 6 — AUDIT TRAIL

| ID | Tiêu chí | B.Buộc | Owner | Bằng chứng xác nhận | Kết quả |
|---|---|---|---|---|---|
| AUD-01 | `track_changes=1` ghi lại mọi thay đổi field trên Commissioning | ★ | Dev Lead | Sửa 1 field, mở "Version History", thấy before/after | ☐ Pass ☐ Fail |
| AUD-02 | `track_views=1` ghi lại mỗi lần user mở form | — | Dev Lead | Mở form 3 lần với 3 user khác nhau, kiểm tra View log | ☐ Pass ☐ Fail |
| AUD-03 | Log chuyển state ghi đúng: from_state, to_state, actor, timestamp | ★ | Dev Lead | Chuyển vài state, mở Document Timeline, xác nhận đủ 4 field | ☐ Pass ☐ Fail |
| AUD-04 | Field `final_asset` chỉ được ghi bởi System (không user nào sửa tay được) | ★ | QA Lead | Login với tất cả role, thử sửa final_asset → read-only hoàn toàn | ☐ Pass ☐ Fail |
| AUD-05 | Phiếu đã Submit (`docstatus=1`) không thể sửa bởi bất kỳ user nào (kể cả Admin) | ★ | QA Lead + QMS | Submit 1 phiếu, login Admin, thử Edit → tất cả field read-only | ☐ Pass ☐ Fail |
| AUD-06 | Amend tạo phiên bản mới và giữ link về phiên bản cũ | ★ | QA Lead | Amend 1 phiếu đã Cancel, xác nhận `amended_from` có giá trị | ☐ Pass ☐ Fail |
| AUD-07 | Amend yêu cầu điền `amend_reason` bắt buộc | ★ | QA Lead | Amend phiếu, bỏ trống amend_reason, bấm Save → lỗi bắt buộc | ☐ Pass ☐ Fail |
| AUD-08 | Event `imm04.release.approved` xuất hiện trong browser console sau Submit | — | Dev Lead | F12 → Console, Submit phiếu, thấy event payload JSON | ☐ Pass ☐ Fail |

**Nhóm 6 — Tổng:** ___/8 Pass (Bắt buộc: ___/6 Pass)

---

## NHÓM 7 — BÁO CÁO

| ID | Tiêu chí | B.Buộc | Owner | Bằng chứng xác nhận | Kết quả |
|---|---|---|---|---|---|
| RPT-01 | List View `Asset Commissioning` có filter theo `workflow_state` | ★ | Dev Lead | Mở List View, filter = Clinical_Hold → hiện đúng danh sách | ☐ Pass ☐ Fail |
| RPT-02 | List View `Asset QA NC` có column `ref_commissioning` (ISS-09) | ★ | Dev Lead | Screenshot List View NC có column link về phiếu gốc | ☐ Pass ☐ Fail |
| RPT-03 | API `get_dashboard_stats` trả đúng JSON với 3 metrics | — | Dev Lead | Call `/api/method/assetcore.api.get_dashboard_stats` → response OK | ☐ Pass ☐ Fail |
| RPT-04 | API `get_commissioning_by_barcode` tìm đúng phiếu theo QR | — | Dev Lead | Call API với `qr_code=BV-ICU-2026-001` → trả đúng record | ☐ Pass ☐ Fail |
| RPT-05 | Drill-down: click `custom_comm_ref` từ Asset → về phiếu Commissioning gốc | ★ | QA Lead | Mở Asset được Mint, click field custom_comm_ref → đúng phiếu | ☐ Pass ☐ Fail |

**Nhóm 7 — Tổng:** ___/5 Pass (Bắt buộc: ___/3 Pass)

---

## NHÓM 8 — TÀI LIỆU HƯỚNG DẪN

| ID | Tiêu chí | B.Buộc | Owner | Bằng chứng xác nhận | Kết quả |
|---|---|---|---|---|---|
| DOC-01 | UAT Script (`IMM-04_UAT_Script.md`) đã in và phát cho từng actor | ★ | PM | Danh sách phát tài liệu có chữ ký nhận | ☐ Pass ☐ Fail |
| DOC-02 | Master Test Data đã được load vào Sandbox (5 PO + Item + Supplier) | ★ | QA Lead | Screenshot data có đủ theo `IMM-04_Master_Test_Data.md` | ☐ Pass ☐ Fail |
| DOC-03 | User accounts test đã được cấp phát và người dùng đã login thử thành công | ★ | CMMS Admin | 6 user đã login ít nhất 1 lần, xác nhận password OK | ☐ Pass ☐ Fail |
| DOC-04 | Tất cả Critical + Major issues từ CRP đã được close (ISS-01 đến ISS-13) | ★ | Dev Lead + QA | `IMM-04_Issue_Triage.md` — Fix-Now List: 13/13 items ✅ | ☐ Pass ☐ Fail |
| DOC-05 | Agenda UAT Final (thời gian, địa điểm, danh sách tham dự) đã được confirm | ★ | PM | Email confirm đã gửi và nhận reply từ ít nhất 5/9 stakeholders | ☐ Pass ☐ Fail |
| DOC-06 | Tài liệu hướng dẫn nhanh 1-pager cho KTV HTM đã sẵn sàng | — | PM | File 1-pager KTV_HTM_Guide.pdf tồn tại | ☐ Pass ☐ Fail |
| DOC-07 | Sandbox URL chạy ổn định 24h liên tục trước UAT | ★ | Sys Admin | Kiểm tra uptime monitoring; không downtime trong 24h | ☐ Pass ☐ Fail |

**Nhóm 8 — Tổng:** ___/7 Pass (Bắt buộc: ___/6 Pass)

---

## UAT READINESS SCORECARD

### Bảng tổng hợp

| Nhóm | Tổng Tiêu chí | Bắt buộc (★) | Pass Thực tế | Pass Bắt buộc | % Bắt buộc |
|---|---|---|---|---|---|
| 1. Cấu hình Hệ thống | 8 | 6 | ___ | ___ | __% |
| 2. Dữ liệu | 8 | 8 | ___ | ___ | __% |
| 3. Workflow | 10 | 9 | ___ | ___ | __% |
| 4. Permission | 9 | 9 | ___ | ___ | __% |
| 5. Validation | 10 | 9 | ___ | ___ | __% |
| 6. Audit Trail | 8 | 6 | ___ | ___ | __% |
| 7. Báo cáo | 5 | 3 | ___ | ___ | __% |
| 8. Tài liệu HD | 7 | 6 | ___ | ___ | __% |
| **TỔNG** | **65** | **56** | **___** | **___** | **__%** |

### Thang đánh giá Readiness

| Điểm | Kết luận | Hành động |
|---|---|---|
| Bắt buộc **56/56** (100%) | ✅ **SẴN SÀNG UAT** | Tiến hành UAT theo lịch |
| Bắt buộc **50–55/56** (89–98%) | ⚠️ **SẴN SÀNG CÓ ĐIỀU KIỆN** | Fix items còn thiếu trong 24h; UAT delayed tối đa 1 ngày |
| Bắt buộc **< 50/56** (< 89%) | ❌ **CHƯA SẴN SÀNG** | Dừng lại; fix và đánh giá lại sau 3 ngày |

### Tổng điểm hiện tại

```
Tiêu chí Bắt buộc đã Pass:  ___/56  (__%)
Tiêu chí Không bắt buộc Pass: ___/9   (__%)
Tổng Pass:                   ___/65  (__%)

Kết luận: ☐ SẴN SÀNG   ☐ CÓ ĐIỀU KIỆN   ☐ CHƯA SẴN SÀNG
```

---

## BẢNG KÝ GATE-KEEPER

*Tất cả 4 người ký đồng thuận trước khi UAT Final được phép khởi động.*

| Vai trò | Ký nhận | Ghi chú | Ngày |
|---|---|---|---|
| **Dev Lead** — xác nhận kỹ thuật sẵn sàng | | | |
| **QA Lead** — xác nhận test nội bộ pass | | | |
| **QMS Reviewer** — xác nhận kiểm soát chất lượng đủ | | | |
| **PM** — xác nhận logistics và tài liệu đủ | | | |

---

*Tài liệu lưu tại: `docs/compliance/IMM-04_UAT_Entry_Criteria.md`*
*Phiên bản kiểm soát theo git — không được sửa sau khi đã ký.*
