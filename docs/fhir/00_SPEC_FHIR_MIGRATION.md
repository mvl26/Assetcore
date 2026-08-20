# SPEC — Chuyển toàn bộ API AssetCore sang chuẩn HL7 FHIR R4

| | |
|---|---|
| **Mã hồ sơ** | `AC-FHIR-001` (namespace MỚI — đã grep xác nhận chưa ai dùng) |
| **Trạng thái** | 🟢 **ĐÃ DUYỆT — ĐỢT 0 ĐANG THI HÀNH** (user mở cổng 2026-08-18). Nền đã land; xem §19. |
| **Ngày lập** | 2026-08-05 |
| **Nhánh** | `feature/hieuc/core-refinement` |
| **Phiên bản chuẩn** | HL7 FHIR **R4 — 4.0.1** (normative) |
| **Quyết định phạm vi** | **Thay thế toàn bộ** (user chốt sau khi đã nghe khuyến nghị façade bổ sung) |
| **Chiều dữ liệu** | Đọc **và** ghi |
| **Động lực** | **Liên thông mở** — kết nối được với **bất kỳ** hệ thống y tế nào dùng HL7 FHIR (user làm rõ 2026-08-05, thay cho "có đối tác cụ thể"). Không có client nào được biết trước tên. |

---

## §1. GIẢ ĐỊNH ĐANG ÁP DỤNG — bác bỏ ngay nếu sai

Spec này được viết trên 8 giả định. Sai bất kỳ giả định nào ở nhóm ⛔ thì phải viết lại spec, không phải sửa mã.

| # | Giả định | Mức |
|---|---|---|
| 1 | "Sửa tất cả API theo FHIR" = **toàn bộ 527 endpoint rốt cuộc phải nằm sau bề mặt FHIR**, kể cả nghiệp vụ không có resource tương ứng (mua sắm, khấu hao, CAPA…). | ⛔ |
| 2 | Frontend Vue (**148 route**, 18 store) và app mobile (repo riêng `/home/miyano/assetcore-mobile`) **sẽ được viết lại** để tiêu thụ FHIR. Ngân sách và người cho việc này đã có. | ⛔ |
| 3 | Được phép **dual-run**: bề mặt FHIR chạy song song bề mặt cũ trong giai đoạn chuyển tiếp. Không big-bang. | ⛔ |
| 4 | Đối tác chấp nhận **R4 4.0.1**; khái niệm chỉ có ở R5 (`InventoryItem`, `DeviceAssociation`…) xử lý bằng extension. | ⛔ |
| 5 | Không đụng lõi Frappe/ERPNext (CLAUDE.md §19); FHIR dựng **trong** app `assetcore`. | ✅ chắc |
| 6 | Kiến trúc 3 tầng giữ nguyên: mapper FHIR gọi **tầng service hiện có**, không viết lại nghiệp vụ, không SQL trần (CLAUDE.md §15). | ✅ chắc |
| 7 | Mọi ghi qua FHIR vẫn phải sinh **Lifecycle Event** + audit trail (CLAUDE.md §10, §20). FHIR không được là cửa sau né workflow. | ✅ chắc |
| 8 | Tiếng Việt là ngôn ngữ hiển thị; tên resource/field FHIR giữ nguyên tiếng Anh (là danh từ riêng của chuẩn, cùng nhóm ngoại lệ với QR/PIN). | ✅ chắc |
| 9 | **AssetCore đóng vai FHIR *server*** — hệ khác gọi vào. Việc AssetCore đi *gọi* FHIR của hệ khác (vai *client*, ví dụ hút danh mục khoa phòng từ HIS) **nằm ngoài phạm vi** spec này. | ⛔ |
| 10 | Không biết trước client là ai ⇒ đích tuân thủ là **base R4 + bộ test conformance công khai**, KHÔNG phải profile riêng của một bên nào. | ✅ chắc |

---

## §2. MỤC TIÊU

**Xây gì.** Thay bề mặt API hiện tại (527 endpoint Frappe RPC, envelope `{success, data}`) bằng bề mặt RESTful HL7 FHIR R4 đầy đủ: không gian URL `/fhir/R4/...`, resource trần, `Bundle` cho tìm kiếm, `OperationOutcome` cho lỗi, `CapabilityStatement` công bố năng lực, hỗ trợ đọc + ghi.

**Vì sao.** Để **bất kỳ** hệ thống y tế nào nói được FHIR đều nối vào AssetCore mà **không cần thoả thuận riêng** — không cần ta viết adapter cho từng hệ, không cần họ đọc tài liệu riêng của ta. Đúng định hướng CLAUDE.md §14 và `docs/architecture/Ho_so_kien_truc_IMMIS.md` (hiện gắn nhãn `[ROADMAP]`, 0 dòng mã).

**Ai dùng.**
- **Chính:** một client FHIR **chưa biết tên** (HIS/EMR/PACS/LIS/kho dữ liệu/công cụ phân tích), máy-với-máy, `system/` scope. Giả định về nó: **chỉ biết base R4, chưa từng nghe tên AssetCore.**
- **Phụ:** frontend AssetCore + app mobile, sau khi viết lại.
- **Nội bộ:** đội tích hợp của bệnh viện, kiểm định viên hồ sơ thầu.

**Phép thử của mọi quyết định thiết kế trong tài liệu này:** *"Một kỹ sư tích hợp chưa từng biết AssetCore, chỉ cầm bản base R4 trong tay, có tự nối được không?"* Câu trả lời "được, nếu họ đọc IG của ta" = **trượt**.

**Thành công trông như thế nào.** §15.

---

## §3. HIỆN TRẠNG — số đo từ đĩa ngày 2026-08-05

Mọi con số dưới đây tái lập được bằng lệnh ở §11.4. **Không chép số từ tài liệu cũ** (skill `assetcore-doc` R-CD-3 ghi 467 endpoint — đã STALE, thực tế 527).

| Hạng mục | Số đo | Ghi chú |
|---|---|---|
| Endpoint whitelist | **527** | 29 file `assetcore/api/*.py` |
| DocType | **110** | 45 child · 26 submittable |
| Route frontend | **148** | 137 view |
| Workflow | **22** | state machine |
| Vai trò / năng lực | **30 / 105** | |
| OAS app mobile | **110 path** | repo riêng, đang lệch 6 path |
| Mã FHIR hiện có | **0 dòng** | 22 lần nhắc trong docs, toàn `[ROADMAP]` |

**Cơ chế định tuyến đã có sẵn** (không phải phát minh mới):
- `assetcore/hooks.py:470` — `website_route_rules = [{"from_route": "/assetcore/<path:app_path>", "to_route": "assetcore"}]` + controller `assetcore/www/assetcore.py`. Đây chính là khuôn để dựng `/fhir/<path:fhir_path>`.
- `assetcore/hooks.py:463` — `before_request` (đang dùng cho `session_guard`), là móc để cắm xác thực SMART on FHIR.

**Envelope hiện tại** — `assetcore/utils/response.py:92`: `{"success": True, "data": data}`.

---

## §4. ĐÁNH GIÁ RỦI RO — đọc trước khi duyệt

Khuyến nghị kỹ thuật ban đầu là **façade bổ sung**; user đã chọn **thay thế toàn bộ**. Spec này thi hành đúng lựa chọn đó. Bốn rủi ro dưới đây **không biến mất** vì lựa chọn, chúng chỉ được quản trị:

| # | Rủi ro | Mức | Cách quản trị trong spec này |
|---|---|---|---|
| R1 | **~41% bề mặt không có resource FHIR** (mua sắm, ngân sách, AVL, khấu hao, CAPA, đánh giá nội bộ, kho phụ tùng). Ép vào `Basic` là **hợp lệ FHIR nhưng giá trị liên thông = 0**. ⚠️ **Mục tiêu "bất kỳ hệ thống nào" biến rủi ro này thành điều chắc chắn:** khi còn một đối tác *có tên*, ta còn có thể thoả thuận để họ đọc `Basic` + extension của ta. Với một client **chưa biết tên**, xác suất đó **bằng 0 theo định nghĩa** — nó chỉ biết base R4, và base R4 không định nghĩa nghĩa của `Basic` do ta tự đặt. | 🔴 Cao → **Chắc chắn** | §7 phân loại rõ 4 chiến lược; §16 đẩy nhóm này về **Đợt 5**, sau khi phần có giá trị thật đã nối được. **Đề nghị tại cổng Đợt 5: giữ native (REST/OpenAPI) cho nhóm C thay vì ép `Basic`** — quyết định thuộc về user. |
| R2 | **Viết lại 148 route FE + toàn bộ app mobile.** Envelope biến mất, mọi store phải parse `Bundle`. Đây là hạng mục lớn nhất của cả chương trình, lớn hơn phần backend. | 🔴 Cao | §16 Đợt 6 tách riêng, có cổng riêng. Dual-run (§5) cho phép dừng lại mà không hỏng gì đang chạy. |
| R3 | **R4 thiếu `InventoryItem`/`InventoryReport`** (chỉ có từ R5) ⇒ 36 endpoint kho phụ tùng không có đích chuẩn trong R4. | 🟠 Vừa | §7 nhóm C; dùng `SupplyRequest`/`SupplyDelivery` + `Basic`, thiết kế mapper trung lập để bật R5 sau. |
| R4 | **Nợ kỹ thuật hiện có sẽ nổ ra khi lên FHIR**: hệ thống đang trả 404/409/422 **trong thân HTTP 200**; phân trang `timestamp desc` thiếu tiebreaker (`api/imm00.py:293`, sổ `AC-CR-100`) gây lặp + bỏ sót giữa 2 trang liền kề. FHIR bắt buộc status thật + phân trang ổn định. | 🟠 Vừa | Là **điều kiện tiên quyết của Đợt 0**, không phải việc phụ. Xem §15 TC-3, TC-5. |

---

## §5. CHIẾN LƯỢC

### 5.1 Bóp nghẹt dần (Strangler Fig) — không big-bang

"Thay thế toàn bộ" **không** có nghĩa là đổi 527 endpoint trong một lần. Thi hành theo mô hình bóp nghẹt dần:

```
Đợt 0        Đợt 1..5                         Đợt 6
─────────    ────────────────────────────     ──────────────
dựng nền  →  mỗi đợt bọc thêm 1 nhóm      →  chuyển consumer   →  xoá bề mặt cũ
             resource;                        (FE 148 route +
             bề mặt CŨ vẫn sống               mobile) sang FHIR
```

**Luật bất di bất dịch của giai đoạn dual-run:**
1. Bề mặt FHIR và bề mặt cũ **cùng gọi một tầng service**. Cấm fork nghiệp vụ. Một quy tắc nghiệp vụ = một nơi.
2. **Không xoá** bất kỳ endpoint cũ nào cho tới khi consumer cuối cùng của nó đã chuyển (đo bằng log, không đoán).
3. Mỗi đợt là một lát cắt **dọc** (mapper + tìm kiếm + ghi + test + hồ sơ tuân thủ), không phải lát ngang.

### 5.2 Bảy luật liên thông mở

Hệ quả trực tiếp của mục tiêu "bất kỳ hệ thống nào". Đây là **ràng buộc thiết kế bắt buộc**, không phải khuyến nghị — vi phạm luật nào thì hệ thống vẫn "có FHIR" nhưng **không ai nối được**, tức là trượt mục tiêu.

| # | Luật | Vì sao |
|---|---|---|
| **L1** | **Base R4 trước, profile sau.** Chức năng cơ bản (đọc/tìm thiết bị, vị trí, tổ chức, công việc) phải dùng được **chỉ với base R4**. | Client không biết ta tồn tại thì không thể đọc IG của ta trước. |
| **L2** | **Mọi extension là TÙY CHỌN.** Xoá sạch extension của AssetCore khỏi một resource ⇒ phần còn lại vẫn **hợp lệ và vẫn hữu ích**. Cấm đặt dữ liệu sống-còn *chỉ* trong extension. | Client lạ sẽ bỏ qua extension nó không hiểu — đó là hành vi đúng theo chuẩn. |
| **L3** | **Tham số tìm kiếm chuẩn trước tham số riêng.** Bắt buộc có `_id` `_lastUpdated` `_count` `_sort` `identifier` `status` + các tham số chuẩn của từng resource (`Device`: `udi-di`, `serial-number`, `location`, `manufacturer`…). Tham số riêng chỉ được **thêm**, không được **thay**. | Client lạ dò tham số theo `CapabilityStatement`, chỉ biết tên chuẩn. |
| **L4** | **Ưu tiên hệ mã quốc tế công khai.** Mã nội bộ (trạng thái workflow tiếng Việt, phân loại NĐ98) luôn đi kèm `ConceptMap` sang mã chuẩn **và** `CodeableConcept.text` đọc được bằng mắt. | Client không tra được `CodeSystem` riêng của ta thì ít nhất còn đọc `text`. |
| **L5** | **Không client nào bị buộc dùng `Basic`.** Resource nhóm C chỉ phơi cho ai chủ động hỏi; không xuất hiện trong luồng đọc cơ bản, không nằm trong `_include` mặc định. | `Basic` + extension riêng = client lạ đọc được cấu trúc nhưng **không hiểu nghĩa**. |
| **L6** | **Tuân thủ do bên thứ ba chấm, không tự chấm.** Phải qua validator chính thức HL7 **và** một bộ test conformance công khai (Inferno / Touchstone). | "Chúng tôi tin là mình đúng chuẩn" không phải bằng chứng liên thông. |
| **L7** | **`CapabilityStatement` là hợp đồng duy nhất.** Client tự khám phá năng lực qua `/fhir/R4/metadata`; không được yêu cầu tài liệu ngoài luồng, không có năng lực "ẩn" không khai báo. | Đây là cách duy nhất một hệ chưa biết ta có thể tự tìm hiểu ta. |

---

## §6. KIẾN TRÚC ĐÍCH

### 6.1 Không gian URL

| Đường dẫn | Ý nghĩa |
|---|---|
| `GET /fhir/R4/metadata` | `CapabilityStatement` — công bố năng lực |
| `GET /fhir/R4/{Type}/{id}` | đọc 1 resource |
| `GET /fhir/R4/{Type}/{id}/_history/{vid}` | đọc bản phiên bản |
| `GET /fhir/R4/{Type}?param=…` | tìm kiếm → `Bundle` kiểu `searchset` |
| `POST /fhir/R4/{Type}` | tạo |
| `PUT /fhir/R4/{Type}/{id}` | cập nhật (kèm `If-Match`) |
| `PATCH /fhir/R4/{Type}/{id}` | vá (JSON Patch / FHIRPath Patch) |
| `DELETE /fhir/R4/{Type}/{id}` | xoá logic |
| `POST /fhir/R4` | giao dịch `Bundle` (transaction/batch) |
| `POST /fhir/R4/{Type}/{id}/${op}` | thao tác đặc thù (§7 nhóm B) |
| `GET /.well-known/smart-configuration` | khai báo SMART on FHIR |

Cài đặt: `hooks.py` thêm `{"from_route": "/fhir/<path:fhir_path>", "to_route": "fhir_router"}` + controller `assetcore/www/fhir_router.py` — **cùng khuôn với `/assetcore/<path:app_path>` đã chạy tốt**.

### 6.2 Hợp đồng phản hồi — điểm gãy lớn nhất so với hiện tại

| | Hiện tại | FHIR R4 |
|---|---|---|
| Thành công | `{"success": true, "data": {…}}` | **resource trần**, `Content-Type: application/fhir+json` |
| Danh sách | `{"success": true, "data": {"rows": […], "total": N}}` | `Bundle` (`type=searchset`, `total`, `link[relation=next]`) |
| Lỗi | `{"success": false, "error": "…", "code": "…", "http_status": 422}` trên **thân HTTP 200** | `OperationOutcome` + **HTTP status thật ở status line** |

⚠️ **FHIR cấm bọc resource.** `utils/response.py` **không** được dùng trên nhánh FHIR. Cần một module phản hồi riêng — và một guard test khẳng định không response FHIR nào chứa key `success` (§15 TC-3).

### 6.3 Ánh xạ mã lỗi → `OperationOutcome.issue.code`

15 mã ở `utils/response.py:43-57` ánh xạ 1-1, không mất thông tin:

| ErrorCode hiện có | HTTP | `issue.code` (R4 valueset `issue-type`) |
|---|---|---|
| `VALIDATION` | 422 | `invalid` |
| `VALIDATION_ERROR` · `INVALID_PARAMS` | 400 | `structure` |
| `BUSINESS_RULE` · `COMPLIANCE_BLOCKED` | 422 | `business-rule` |
| `UNAUTHORIZED` | 401 | `login` |
| `FORBIDDEN` | 403 | `forbidden` |
| `NOT_FOUND` | 404 | `not-found` |
| `CONFLICT` · `BAD_STATE` | 409 | `conflict` |
| `DUPLICATE` | 409 | `duplicate` |
| `PAYLOAD_TOO_LARGE` | 413 | `too-costly` |
| `RATE_LIMITED` | 429 | `throttled` |
| `INTERNAL` · `INTERNAL_ERROR` | 500 | `exception` |

Câu tiếng Việt hiện có giữ nguyên ở `issue.details.text`; `message_code` (registry `utils/messages.py`) đặt vào `issue.details.coding` với `system` riêng của AssetCore.

### 6.4 Định danh resource (`Resource.id`) — có bẫy thật

FHIR quy định `id` khớp `[A-Za-z0-9\-\.]{1,64}` và **bất biến vĩnh viễn**.

- ✅ **An toàn:** 24 DocType đặt tên theo `naming_series` + các mẫu `PM-WO-.YYYY.-.#####`, `CAL-.YYYY.-.#####`… Ví dụ `AC-ASSET-2026-76476` hợp lệ.
- ⛔ **Vi phạm — 8 DocType đặt tên từ trường tự do** (có dấu tiếng Việt, dấu cách, có thể có `/`): `ac_spare_part_stock` (`field:stock_key`) · `ac_uom` (`field:uom_name`) · `imm_compliance_rule` · `imm_critical_spare_watchlist` · `imm_sla_policy` · `imm_training_program` · `required_document_type` · `pm_task_log` (không có autoname).
- ⛔ **Bẫy thứ hai:** Frappe cho phép **đổi tên bản ghi** (rename) — FHIR thì không. Một lần rename = mọi tham chiếu ngoài trỏ sai.

**Giải pháp:** DocType mới `AC FHIR Identity` (`doctype`, `docname`, `fhir_type`, `fhir_id` bất biến, `created`), cấp id thay thế lười (lazy) cho 8 DocType vi phạm, cộng hook `on_rename` **giữ nguyên `fhir_id`** cho toàn bộ resource được phơi. Tạo DocType mới ⇒ thuộc nhóm "Hỏi trước" (§14).

### 6.5 Phiên bản & tương tranh

`meta.versionId` ← bộ đếm sửa đổi; `meta.lastUpdated` ← `modified`. Trả `ETag: W/"<versionId>"`. `PUT` kèm `If-Match` lệch ⇒ **412 Precondition Failed** (ánh xạ từ `TimestampMismatchError` của Frappe). Không có `If-Match` trên `PUT` ⇒ từ chối bằng **428 Precondition Required** đối với resource nhạy cảm.

### 6.6 Bảo mật — SMART on FHIR

- Backend Services Authorization (`client_credentials` + JWT assertion), tận dụng OAuth2 sẵn có của Frappe.
- Scope `system/Device.read`, `system/Task.write`… ánh xạ về **105 capability** hiện có; **không** tạo hệ phân quyền thứ hai.
- `before_request` (`hooks.py:463`) là nơi cắm — cùng chỗ `session_guard` đang nâng 403→401.
- **Cách ly nhà cung cấp giữ nguyên**: `apply_vendor_scope` phải áp ở tầng tìm kiếm FHIR. Lưu ý lỗi đã biết `AC-CR-96` (`services/shared/scope.py:172-175` **gán** thay vì **giao** `filters['asset']`) — lên FHIR sẽ thành lỗ rò dữ liệu liên tổ chức, phải sửa trong Đợt 0.

---

## §7. BẢN ĐỒ 527 ENDPOINT → FHIR

Bốn chiến lược:

| | Chiến lược | Giá trị liên thông |
|---|---|---|
| **A** | Resource FHIR R4 gốc | ⭐⭐⭐ client lạ đọc được ngay, **không cần thoả thuận trước** |
| **B** | Thao tác `$operation` trên resource nhóm A (cho động từ không phải CRUD: `$start`, `$complete`, `$decommission`) | ⭐⭐⭐ |
| **C** | `Basic` + `StructureDefinition` + extension riêng | ⭐ hợp lệ FHIR, nhưng **client chưa biết AssetCore thì đọc được cấu trúc mà không hiểu nghĩa** |
| **D** | Nằm ngoài không gian resource (hạ tầng: xác thực, tài liệu API, layout) | n/a |

| File API | # | Nghiệp vụ | Resource R4 đích | Nhóm |
|---|---|---|---|---|
| `imm00.py` | 117 | nền tảng, dữ liệu chủ, sự kiện vòng đời, liên kết | `Device` `Location` `Organization` `Provenance` `AuditEvent` `List` | A/B + C |
| `imm05.py` | 16 | đăng ký thiết bị | **`Device`** (lõi — đã sẵn `udi_code`, `gmdn_code`, `manufacturer_sn`, `medical_device_class`) | **A** |
| `imm04.py` | 34 | lắp đặt, nghiệm thu | `Task` + `QuestionnaireResponse` (biểu kiểm) + `Provenance` | **A/B** |
| `imm08.py` | 26 | bảo trì định kỳ | `Task` + `Schedule`/`Appointment` (lịch) | **A/B** |
| `imm09.py` | 14 | sửa chữa | `Task` | **A/B** |
| `imm11.py` | 19 | hiệu chuẩn | `Task` + `Observation` (kết quả đo) + `DocumentReference` (chứng chỉ) | **A/B** |
| `imm12.py` | 21 | khắc phục, sự cố | `Task` + `DetectedIssue` | **A/B** |
| `imm14.py` | 4 | thanh lý | `Task` + `Device.status` | **A/B** |
| `user.py` | 15 | người dùng, kỹ thuật viên | `Practitioner` `PractitionerRole` `Group` | **A** |
| `files.py` | 1 | tệp đính kèm | `Binary` + `DocumentReference` | **A** |
| `notifications.py` | 3 | thông báo | `Communication` `Subscription` | **A** |
| `dashboard.py` | 4 | thẻ KPI | `Measure` + `MeasureReport` | **A** |
| `import_data.py` | 6 | nhập hàng loạt | `Bundle` transaction + `$import` | **A/B** |
| `imm01.py` | 22 | nhu cầu thiết bị | `DeviceRequest` *(vừa khớp)* + `Basic` | A/**C** |
| `imm02.py` | 16 | nhà cung cấp, hợp đồng | `Organization` `Contract` + `Basic` | A/**C** |
| `imm03.py` | 25 | kế hoạch, ngân sách, AVL, chấm điểm | `MeasureReport` + **`Basic`** | **C** |
| `imm06.py` | 28 | đào tạo, bàn giao | **`Basic`** (FHIR không có resource đào tạo kỹ thuật) | **C** |
| `imm15.py` | 24 | tài liệu QMS, rủi ro | `DocumentReference` `Composition` `RiskAssessment` + `Basic` | A/**C** |
| `imm16.py` | 53 | CAPA, đánh giá nội bộ, xem xét lãnh đạo | `Task` (hành động CAPA) `DetectedIssue` (sự không phù hợp) `Composition` (biên bản) + **`Basic`** | A/**C** |
| `inventory.py` | 36 | kho phụ tùng | `SupplyRequest` `SupplyDelivery` + **`Basic`** ⚠️ R4 thiếu `InventoryItem` | **C** |
| `purchase.py` | 13 | mua sắm | `SupplyRequest` `Contract` `ChargeItem` | **C** |
| `imm10.py` | 1 | móc nối | — | C |
| `auth.py` | 9 | đăng nhập | **thay bằng SMART on FHIR / OAuth2** | **D** |
| `openapi.py` | 11 | tài liệu API | **thay bằng `CapabilityStatement` + `StructureDefinition`** | **D** |
| `layout.py` | 7 | cấu hình giao diện | nội bộ ứng dụng — giữ ngoài FHIR | **D** |
| `connections.py` · `session_guard.py` | 2 | hạ tầng | giữ ngoài FHIR | **D** |

**Phân bổ ước lượng: A/B ≈ 210 endpoint (40%) · C ≈ 217 (41%) · D ≈ 29 (6%) · còn lại thay thế bằng hạ tầng chuẩn.** Con số chính xác chốt từng module ở Đợt 0.

> 🔴 **Điểm cần user quyết lại ở cổng Đợt 5:** 217 endpoint nhóm C sau khi lên `Basic` vẫn **không** giúp một hệ ngoài đọc được nghiệp vụ mua sắm/QMS của ta — nó nhận về một `Basic` có `code` do ta tự đặt, không nằm trong bất kỳ từ điển nào nó biết. Với mục tiêu "**bất kỳ hệ thống nào**", điều này không còn là rủi ro mà là **hệ quả tất yếu**: chi phí có thật, lợi ích bằng 0. Spec vẫn giữ chúng trong phạm vi vì user đã chốt "thay thế toàn bộ" — nhưng **đề nghị giữ native cho nhóm C**, quyết tại cổng đó với dữ liệu thực tế từ Đợt 1–4.

---

## §8. THUẬT NGỮ & MÃ HOÁ

| Khái niệm | Nguồn mã | Việc phải làm |
|---|---|---|
| Loại thiết bị | **GMDN** (`ac_asset.gmdn_code` đã có) | Xuất `CodeSystem`/`ValueSet`. ⚠️ GMDN Agency thu phí license — xem §17 Q4 |
| Định danh thiết bị | **UDI-DI** (`ac_asset.udi_code`) | `Device.udiCarrier.issuer` (GS1/HIBCC/ICCBBA) — cardinality nới lỏng trong R4, **nhưng thiếu thì client không biết giải mã theo hệ nào** ⇒ coi như bắt buộc với ta. Hiện **chưa có trường nguồn**. Kèm tham số tìm kiếm chuẩn `udi-di` (L3). *Xác minh lại cardinality với bản R4 công bố khi dựng profile.* |
| Phân loại rủi ro | `medical_device_class`, `risk_classification` (NĐ98: A/B/C/D) | `CodeSystem` riêng của Việt Nam + `ConceptMap` sang phân loại quốc tế |
| Số đăng ký lưu hành | `byt_reg_no`, `byt_reg_expiry` | `Device.identifier` + extension |
| Trạng thái nghiệp vụ | 22 workflow, nhãn tiếng Việt | `ConceptMap` sang các valueset bắt buộc của FHIR (`Device.status` chỉ có `active\|inactive\|entered-in-error\|unknown` — hẹp hơn vòng đời thật của ta ⇒ trạng thái chi tiết đi vào extension) |

---

## §9. GHI DỮ LIỆU — ràng buộc bắt buộc

1. **Không cửa sau.** `POST`/`PUT`/`PATCH` FHIR **phải** đi qua đúng state machine của 22 workflow, dùng `allowed_transitions` — cấm `doc.save()` trần, cấm ghi cứng so sánh `status === '…'` (GATE-8/LL-FE-51).
2. **Sinh sự kiện.** Mỗi ghi thành công sinh đúng **1 Lifecycle Event**, phơi ra ngoài dưới dạng `Provenance` (CLAUDE.md §10).
3. **Bất biến phép.** `POST` lặp phải chống trùng — cần DocType `Mobile Idempotency Log` (hiện **chưa tạo**, đang chạy tạm bằng cache TTL 24h; là blocker #10 trong STATE). FHIR dùng chung cơ chế này.
4. **Giao dịch.** `Bundle` kiểu `transaction` phải nguyên tử: một entry hỏng ⇒ rollback toàn bộ, trả `OperationOutcome` chỉ đúng `entry.fullUrl` gây lỗi.
5. **Tương tranh.** `If-Match` bắt buộc trên `PUT` resource nhạy cảm (§6.5).
6. **`permlevel`.** Nhắc lại lỗi đã gặp: trường có `permlevel:N` mà không có DocPerm tương ứng sẽ bị **strip câm** khi save. Mapper ghi phải có test khẳng định giá trị thực sự vào DB, không tin phản hồi 200.

---

## §10. CẤU TRÚC THƯ MỤC ĐÍCH

```
assetcore/
  fhir/
    __init__.py
    router.py              # điều phối: đường dẫn → interaction → mapper
    dispatch.py            # bảng định tuyến (Type, interaction) → handler
    response.py            # trả resource TRẦN + OperationOutcome (KHÔNG dùng utils/response.py)
    search/
      params.py            # _id _lastUpdated _count _sort _include _revinclude, chained
      paging.py            # Bundle.link next/prev — BẮT BUỘC sort có tiebreaker
    mappers/
      device.py            # AC Asset          ⇄ Device
      device_definition.py # Device Model      ⇄ DeviceDefinition
      location.py          # AC Location       ⇄ Location
      organization.py      # AC Supplier/Khoa  ⇄ Organization
      practitioner.py      # User/KTV          ⇄ Practitioner, PractitionerRole
      task.py              # PM/CM/hiệu chuẩn  ⇄ Task
      provenance.py        # Lifecycle Event   ⇄ Provenance, AuditEvent
      observation.py       # phép đo hiệu chuẩn⇄ Observation
      document_reference.py
      basic/               # nhóm C — mỗi hồ sơ 1 profile
    terminology/
      code_systems.py      # GMDN, NĐ98, trạng thái workflow VN
      concept_maps.py
    conformance/
      capability.py        # sinh CapabilityStatement TỪ bảng dispatch (không viết tay)
      profiles/            # StructureDefinition (.json)
    security/
      smart.py             # scope FHIR ⇄ 105 capability
  www/
    fhir_router.py         # điểm vào — khuôn giống www/assetcore.py
tests/
  fhir/
    test_device_mapper.py  # golden file
    test_search_paging.py  # bất biến: 2 trang liền kề rời rạc
    test_no_envelope.py    # guard: 0 response FHIR chứa key "success"
    test_capability_parity.py  # CapabilityStatement ⇄ bảng dispatch khớp tuyệt đối
docs/fhir/
  00_SPEC_FHIR_MIGRATION.md   # ← file này
  01_IG_ASSETCORE/            # Implementation Guide
```

---

## §11. LỆNH

### 11.1 Chạy & kiểm thử
```bash
bench start                                              # site: miyano
bench --site miyano run-tests --app assetcore            # timeout tool ≥ 600000ms (HARD-STOP)
bench --site miyano run-tests --module assetcore.tests.fhir.test_device_mapper
```

### 11.2 Frontend
```bash
cd frontend && npx vitest run          # hiện: 400 file / 3993 test, 0 đỏ
cd frontend && npx vue-tsc --noEmit    # hiện: 0 lỗi
cd frontend && npm run build           # ⚠️ emptyOutDir — build là deploy live
```

### 11.3 Xác thực tuân thủ FHIR *(công cụ mới — thuộc nhóm "Hỏi trước", §14)*
```bash
java -jar validator_cli.jar out/*.json -version 4.0.1 -ig docs/fhir/01_IG_ASSETCORE
curl -sH 'Accept: application/fhir+json' localhost:8000/fhir/R4/metadata | jq .
```

### 11.4 Tái lập số đo của §3
```bash
grep -h "@frappe.whitelist" assetcore/api/*.py | wc -l          # 527
ls assetcore/assetcore/doctype/ | wc -l                          # 112 thư mục / 110 DocType
grep -rhoE "AC-FHIR-[0-9]{3}" docs/ | sort -u | tail -1          # cấp số kế tiếp
```

---

## §12. QUY CÁCH MÃ

Mapper **không** chứa nghiệp vụ và **không** truy vấn thẳng DB — chỉ dịch hình dạng dữ liệu. Nghiệp vụ ở tầng service (CLAUDE.md §15).

```python
"""Ánh xạ AC Asset ⇄ FHIR R4 Device.

Tham chiếu: https://hl7.org/fhir/R4/device.html
Nghiệp vụ nằm ở assetcore.services.imm05 — module này CHỈ dịch hình dạng.
"""
from typing import Any

from assetcore.fhir.terminology.code_systems import SYS_GMDN, SYS_UDI_ISSUER
from assetcore.services import imm05


def to_fhir(doc: dict[str, Any]) -> dict[str, Any]:
    """Dịch một bản ghi AC Asset sang resource Device (R4 4.0.1).

    Args:
        doc: bản ghi AC Asset dạng dict, lấy qua tầng service.

    Returns:
        Resource Device dưới dạng dict — TRẦN, không bọc envelope.
    """
    resource: dict[str, Any] = {
        "resourceType": "Device",
        "id": fhir_id_for("AC Asset", doc["name"]),
        "meta": {
            "versionId": str(doc["_version"]),
            "lastUpdated": to_instant(doc["modified"]),
            "profile": ["http://assetcore.vn/fhir/StructureDefinition/ac-device"],
        },
        "identifier": [{"system": SYS_ASSET_CODE, "value": doc["asset_code"]}],
        "status": _map_status(doc["lifecycle_status"]),
        "serialNumber": doc.get("manufacturer_sn"),
    }
    if doc.get("udi_code"):
        resource["udiCarrier"] = [{
            "deviceIdentifier": doc["udi_code"],
            "issuer": SYS_UDI_ISSUER,   # ⚠️ chưa có trường nguồn — xem §17 Q3
        }]
    if doc.get("gmdn_code"):
        resource["type"] = {"coding": [{"system": SYS_GMDN, "code": doc["gmdn_code"]}]}
    return resource
```

**Quy ước:** type hint cho mọi hàm · docstring bắt buộc, có link tới trang chuẩn của resource · tên hàm theo domain (`to_fhir` / `from_fhir`) · mọi giá trị mã hoá cứng đi qua `terminology/` · **cấm** `import utils.response` trong bất kỳ file nào dưới `assetcore/fhir/`.

---

## §13. CHIẾN LƯỢC KIỂM THỬ

TDD bắt buộc (CLAUDE.md §17): test đỏ trước, mã sau.

| Tầng | Nội dung | Công cụ |
|---|---|---|
| Mapper | golden file mỗi resource: dict DocType vào → JSON FHIR ra, so khớp từng byte | `bench run-tests` |
| Tuân thủ | mọi resource mẫu qua **validator chính thức HL7**, 0 error | `validator_cli.jar` |
| Đồng bộ năng lực | `CapabilityStatement` khai đúng bằng bảng dispatch — không thừa, không thiếu | test parity (khuôn `uiAuditDocParity` đã có trong repo) |
| Không envelope | quét mọi route FHIR: 0 response chứa key `success`/`data` | guard test |
| Mã trạng thái | 404/409/422 phải ở **status line**, không ở thân 200 | test integration |
| Phân trang | timestamp trùng ⇒ 2 trang liền kề **rời rạc** (không lặp, không sót) | test bất biến |
| Ghi | mỗi ghi sinh đúng 1 Lifecycle Event; giá trị thật vào DB (bẫy `permlevel` strip câm) | test service |
| Phân quyền | persona Vendor Engineer không thấy thiết bị ngoài phạm vi qua bề mặt FHIR | test RBAC |
| Liên thông | **bộ test conformance công khai** (Inferno / Touchstone) — bên thứ ba chấm, luật L6 | báo cáo công cụ |
| Liên thông | phiên kết nối với **một client FHIR không do ta viết**, chỉ dùng `/metadata` để tự khám phá | thủ công + biên bản |
| Liên thông | **bản đã lọc sạch extension** vẫn hợp lệ + vẫn hữu ích (luật L2) | validator trên bản lọc |

---

## §14. RANH GIỚI

**LUÔN LÀM**
- Mapper gọi tầng service; nghiệp vụ chỉ tồn tại một nơi.
- Mọi ghi sinh Lifecycle Event + audit trail.
- Chạy validator chính thức trước khi tuyên bố "đạt chuẩn FHIR".
- Đo từ đĩa; mọi con số trong tài liệu kèm lệnh tái lập.
- Cấp số hiệu theo `AC-FHIR-###`, grep trước khi cấp.

**HỎI TRƯỚC**
- Thêm phụ thuộc (`fhir.resources`, `validator_cli.jar`).
- Tạo DocType mới (`AC FHIR Identity`, `Mobile Idempotency Log`).
- Sửa `utils/response.py` hoặc bất kỳ endpoint cũ nào đang có consumer.
- `bench migrate` / chạy patch.
- Đụng repo `/home/miyano/assetcore-mobile` (repo khác).
- Công bố `CapabilityStatement` ra ngoài.

**KHÔNG BAO GIỜ**
- `git commit` / `push` khi user chưa yêu cầu.
- `bench migrate` (HARD-STOP thường trực).
- Sửa lõi Frappe/ERPNext.
- Bọc envelope quanh resource FHIR.
- Bịa resource không có trong R4 (chỉ được dùng `Basic` + extension).
- Xoá endpoint cũ trước khi consumer cuối cùng đã chuyển.
- Tuyên bố "FHIR compliant" khi chưa qua validator chính thức.

---

## §15. TIÊU CHÍ HOÀN THÀNH — kiểm chứng được

| # | Tiêu chí | Cách đo |
|---|---|---|
| TC-1 | `GET /fhir/R4/metadata` trả `CapabilityStatement` hợp lệ | validator: 0 error |
| TC-2 | Mọi resource sinh ra đạt R4 4.0.1 | validator: 0 error, warning nằm trong allowlist có ghi lý do |
| TC-3 | 0 response FHIR chứa key `success` hoặc `data` bọc ngoài | guard test |
| TC-4 | Mã lỗi ở status line, không ở thân 200 | `curl -i` khẳng định 404/409/422 |
| TC-5 | Phân trang ổn định khi timestamp trùng | test bất biến 2 trang rời rạc |
| TC-6 | Mỗi ghi FHIR sinh đúng 1 Lifecycle Event, truy được qua `Provenance?target=` | test integration |
| TC-7 | Cách ly nhà cung cấp giữ nguyên qua FHIR | test persona Vendor Engineer |
| TC-8 | `CapabilityStatement` ⇄ bảng dispatch khớp tuyệt đối | test parity |
| TC-9 | **Client lạ nối được** — một client FHIR bên thứ ba (không do ta viết, không đọc IG của ta) đọc được danh mục thiết bị chỉ từ `/metadata` | biên bản phiên kết nối |
| TC-10 | `bench run-tests` xanh · `npx vitest run` xanh · `vue-tsc` 0 lỗi | chạy thật, dán output |
| TC-11 | *(Đợt 6)* 0 consumer còn gọi endpoint cũ | log 30 ngày |
| **TC-12** | **Luật L2 — xoá extension vẫn dùng được:** lọc bỏ toàn bộ `extension` của AssetCore khỏi mọi resource mẫu ⇒ vẫn hợp lệ R4 **và** vẫn còn đủ trường để định danh + định vị + biết trạng thái thiết bị | test tự động chạy validator trên bản đã lọc |
| **TC-13** | **Luật L6 — bên thứ ba chấm:** qua bộ test conformance công khai (Inferno / Touchstone) | báo cáo của công cụ, không phải tự khai |
| **TC-14** | **Luật L3 — tham số chuẩn:** mọi tham số tìm kiếm chuẩn mà `CapabilityStatement` khai đều chạy thật; 0 tham số riêng nào *thay thế* tham số chuẩn | test parity |

---

## §16. KẾ HOẠCH ĐỢT

| Đợt | Nội dung | Endpoint | Cổng duyệt |
|---|---|---|---|
| **0** | Nền: router, hợp đồng không-envelope, `OperationOutcome`, `CapabilityStatement` sinh tự động, `AC FHIR Identity`, SMART auth, harness validator. **Kèm 3 việc bắt buộc trả nợ:** sửa 404/409/422-trên-200 · tiebreaker phân trang (`api/imm00.py:293`) · lỗ `apply_vendor_scope` (`scope.py:172-175`) | 0 | Kiến trúc + phụ thuộc |
| **1** | `Device` `DeviceDefinition` `Location` `Organization` `Practitioner` `PractitionerRole` — đọc + ghi. **Kèm trọn bộ tham số tìm kiếm chuẩn (L3)** — không phải làm sau. | ~90 | **TC-9 + TC-13**: client lạ đọc được thiết bị chỉ từ `/metadata` |
| **2** | `Task` (PM · sửa chữa · hiệu chuẩn · khắc phục) + `$operation` + `Schedule` + **Bulk Data `$export`** (client lạ cần đồng bộ trọn bộ, không chỉ đọc lẻ) | ~80 | |
| **3** | `Provenance` `AuditEvent` `Observation` `DocumentReference` `Binary` | ~40 | |
| **4** | `Questionnaire`/`QuestionnaireResponse` (biểu kiểm) `Composition` (biên bản) `DetectedIssue` `RiskAssessment` `Measure`/`MeasureReport` `Communication`/`Subscription` | ~60 | |
| **5** | Nhóm C — `Basic` + profile cho mua sắm/kế hoạch/đào tạo/kho/QMS | ~217 | 🔴 **Quyết lại**: ép `Basic` hay giữ native (xem R1) |
| **6** | Chuyển consumer: viết lại **148 route FE** + app mobile → rồi mới xoá bề mặt cũ | — | 🔴 Hạng mục lớn nhất — cổng riêng |

**Về khối lượng:** Đợt 0–4 là công việc backend có biên rõ ràng. **Đợt 5 và 6 cộng lại lớn hơn Đợt 0–4**. Đề nghị chỉ cam kết Đợt 0–1 trước, đo tốc độ thật, rồi mới ước lượng phần còn lại — thay vì cam kết một con số bây giờ mà không có cơ sở.

---

## §17. CÂU HỎI CHẶN — cần user trả lời trước khi bắt đầu Đợt 0

| # | Câu hỏi | Vì sao chặn |
|---|---|---|
| ~~Q1~~ | ~~Đối tác cụ thể là hệ nào?~~ → **ĐÃ TRẢ LỜI 2026-08-05: không có đối tác cụ thể. Mục tiêu là nối được với *bất kỳ* hệ nào dùng FHIR.** ⇒ đích tuân thủ chuyển từ "profile của đối tác X" sang "**base R4 + bộ test công khai**"; sinh ra 7 luật ở §5.2. | ✅ đóng |
| **Q1′** | *(thay Q1)* AssetCore có cần đóng thêm vai **client** (đi gọi FHIR của hệ khác, ví dụ hút danh mục khoa phòng/nhân sự từ HIS) không? Spec hiện **chỉ làm server** (giả định #9). | Nếu có, phải thêm hẳn một lớp nữa: đăng ký endpoint ngoài, ánh xạ ngược, xử lý xung đột dữ liệu hai chiều |
| **Q2** | Có phải tuân IG quốc gia nào không? Việt Nam **chưa có IG FHIR chính thức** ⇒ mặc định dùng base R4 + IG riêng của AssetCore (chỉ để **mô tả**, không bắt client đọc — luật L1). Đúng chưa? | Quyết định nội dung `docs/fhir/01_IG_ASSETCORE/` |
| **Q3** | `udi_code` hiện là văn bản tự do. Cơ quan cấp UDI là **GS1** hay **HIBCC**? | `Device.udiCarrier.issuer` bắt buộc; hiện chưa có trường nguồn |
| **Q4** | Có license **GMDN** để phát hành `CodeSystem` không? Nếu không, chỉ được dùng mã, **không được** tái phát hành định nghĩa. | Rủi ro pháp lý khi công bố terminology |
| **Q5** | Đợt 6 (viết lại 148 route FE + app mobile) do ai làm, mốc nào? App mobile ở repo khác. | Không có câu trả lời thì "thay thế toàn bộ" dừng ở Đợt 5 và hệ thống sống vĩnh viễn với hai bề mặt |
| **Q6** | ~~Đối tác có tiêu thụ nhóm C không?~~ → **câu hỏi này đã tự trả lời khi Q1 đóng:** client chưa biết tên **không thể** hiểu `Basic` + extension riêng của ta (xem R1). Câu còn lại là câu **quyết định**, không phải câu hỏi thông tin: **có chấp nhận chi ~217 endpoint để đổi lấy giá trị liên thông bằng 0 không?** | Quyết ở cổng Đợt 5. Đề nghị: giữ native cho nhóm C. |

---

## §18. LỊCH SỬ

| Ngày | Việc |
|---|---|
| 2026-08-05 | Lập spec. Đã đo hiện trạng từ đĩa; đã xác minh cơ chế định tuyến (`hooks.py:470`), envelope (`utils/response.py:92`), 15 mã lỗi, 8 DocType có tên không hợp lệ làm FHIR `id`. Chờ user duyệt. |
| 2026-08-05 (bổ sung) | **Động lực làm rõ: liên thông MỞ với bất kỳ hệ nào, không có đối tác cụ thể.** Hệ quả đã áp vào spec: đóng Q1, mở Q1′ (vai client?) · thêm giả định #9/#10 · thêm **§5.2 bảy luật liên thông mở** · nâng R1 từ "rủi ro cao" lên "chắc chắn" kèm đề nghị giữ native cho nhóm C · Q6 chuyển từ câu hỏi thông tin sang câu hỏi quyết định · Đợt 1 gánh thêm trọn bộ tham số tìm kiếm chuẩn, Đợt 2 thêm Bulk `$export` · thêm TC-12/13/14 · TC-9 đổi từ "đối tác ký biên bản" sang "**client lạ nối được**". |

---

## §19. NHẬT KÝ THI HÀNH

### Đợt 0 — nền (2026-08-18) · phần KHÔNG cần cổng duyệt

| Thành phần | File | Ghi chú |
|---|---|---|
| Gói FHIR | `assetcore/fhir/__init__.py` | ranh giới: cấm `import utils.response` |
| Từ điển mã | `fhir/terminology/code_systems.py` | `SYS_UDI_ISSUER = None` — **chưa chốt Q3**, mapper không được bịa |
| Hợp đồng phản hồi | `fhir/response.py` | resource trần · `OperationOutcome` · **status ở status line** · `Bundle searchset` |
| Bảng dispatch | `fhir/dispatch.py` | SSoT; `register()` chặn type trùng + tương tác ngoài R4 |
| Bản khai năng lực | `fhir/conformance/capability.py` | **SINH** từ dispatch, không viết tay |
| Phân trang | `fhir/search/paging.py` | `order_by()` **luôn** kèm tiebreaker `name` |
| Điều phối | `fhir/router.py` + `www/fhir_router.py` + `hooks.py` | khuôn giống `/assetcore/<path>` đã chạy tốt |

**Guard (đặt ở `tests/guards/` — xem sai khác #1):**
`test_fhir_no_envelope.py` (4 TC) · `test_fhir_capability_parity.py` (5 TC).
**4 phép thử âm tính đều ĐỎ đúng luật:** mapper import `utils/response` · mã dựng khoá `success` · `CapabilityStatement` khai type không có trong dispatch · khai tương tác ngoài valueset R4.

**Bằng chứng:** `bench run-tests --app assetcore` = `Ran 4787` — **0 lỗi mới** (7 lỗi còn lại đều có từ trước đợt này).

#### Sai khác có chủ ý so với §10

1. **Guard đặt ở `tests/guards/`, không phải `tests/fhir/`.** §10 viết trước đợt chuẩn hoá cấu trúc; quy ước hiện hành (skill `assetcore-structure`) đặt **mọi** test đọc đĩa/parity vào `tests/guards/`. `tests/fhir/` vẫn dành cho **golden-file test của mapper** ở Đợt 1.
2. **Chưa tạo `AC FHIR Identity`, chưa thêm phụ thuộc, chưa cắm SMART auth** — cả ba nằm trong §14 "HỎI TRƯỚC" và cần `bench migrate` (HARD-STOP). Đợt 0 vì thế land phần nền không cần cổng; phần còn lại chờ user.

#### 🔴 Đính chính số đo nợ 3-tier

Sổ nợ công bố **607** ngày 2026-08-14 đo bằng **regex trên văn bản** nên đếm cả chú thích —
`api/imm11.py:6` có đúng dòng `# KHÔNG gọi frappe.db.* hay frappe.get_doc trực tiếp`
(một lời nhắc TUÂN THỦ) và bị tính thành vi phạm.

**Nợ thật đo lại bằng AST: 510.** `imm11.py` và `imm14.py` **vốn đã sạch**.
Đây là **cùng class-of-bug** với guard FHIR no-envelope phát hiện cùng ngày:
*guard soi văn bản không phân biệt được "mã vi phạm" với "câu văn nói về vi phạm".*
Cả hai guard nay đếm bằng AST.

Đã trả 3 nợ thật rẻ nhất trong cùng đợt (đúng yêu cầu "phần nào không thuộc api thì đẩy sang services"):

| Nợ | Chuyển thành | Còn lại |
|---|---|---|
| `api/imm10.py:81` `frappe.db.exists` | `services/imm10.asset_exists()` | |
| `api/imm15.py:281,284` 2× `frappe.db.get_value` cùng 1 hàng | `services/imm15.get_spare_part_display()` — gộp còn **1** truy vấn | |
| | | **510 → 507**, file vi phạm **17 → 15** |
