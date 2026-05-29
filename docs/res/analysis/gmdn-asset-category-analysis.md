# Phân tích mã GMDN trong Danh mục tài sản — AssetCore

| Mục | Giá trị |
|---|---|
| Phạm vi | Mã GMDN trên 3 tầng: AC Asset Category → IMM Device Model → AC Asset |
| Module liên quan | IMM-00 (Master Data) + IMM-05/08/09/11/12/15/16 (downstream) |
| Quy chuẩn tham chiếu | ISO 15225 (GMDN), NĐ98/2021/NĐ-CP, WHO HTM Lifecycle |
| Trạng thái | Đã triển khai 3 tầng kế thừa |
| Cập nhật | 2026-05-19 |

---

## 1. Vai trò nghiệp vụ của mã GMDN

Mã GMDN (Global Medical Device Nomenclature) **không chỉ là chuỗi định danh** — đóng vai trò là *"chìa khoá gom nhóm"* (grouping key) điều hướng nhiều luồng nghiệp vụ cốt lõi của AssetCore.

### 1.1 Định tuyến PM (Preventive Maintenance) — IMM-08

PM Checklist template **không gắn theo từng Asset đơn lẻ** mà gắn theo nhóm `AC Asset Category` (đã có sẵn `default_pm_required`, `default_pm_interval_days` ở cấp category). Mọi Device Model và Asset thuộc nhóm GMDN đó **tự kế thừa** quy trình PM chuẩn.

- Asset Category định nghĩa **policy mặc định** (interval, alert, có yêu cầu PM hay không).
- Device Model override khi nhà sản xuất khuyến cáo khác (ví dụ Philips Voluson cần PM 90 ngày thay vì 180 ngày chuẩn nhóm "máy siêu âm").
- Asset thừa hưởng từ Model qua `fetch_from`.

→ Kỹ thuật viên chỉ cần thiết kế checklist 1 lần / category, không phải clone cho từng máy.

### 1.2 Recall / FSCA (Field Safety Corrective Action) — IMM-12, IMM-16

Khi có cảnh báo an toàn từ nhà sản xuất hoặc Bộ Y tế đối với một dải thiết bị (ví dụ FSCA cho mã GMDN 35304 — "Ultrasound imaging system, general purpose"):

```
Cảnh báo theo gmdn_code
   → query IMM Device Model.gmdn_code = X
       → query AC Asset.device_model IN (...models)
           → danh sách Asset cụ thể đang vận hành
               → khoá sử dụng / cách ly tức thời
```

Đây là lý do `gmdn_code` phải **unique tại Category** (`_validate_gmdn_unique` ở [ac_asset_category.py:47-59](../../assetcore/assetcore/doctype/ac_asset_category/ac_asset_category.py#L47-L59)) — tránh hai category cùng GMDN gây ambiguity khi truy vết ngược.

### 1.3 KPI và phân tích hiệu năng — IMM-17

Các chỉ số quản trị nhóm theo Asset Category / GMDN, không nhóm theo Asset rời:

| KPI | Công thức gom nhóm |
|---|---|
| MTBF (Mean Time Between Failures) | Aggregate theo `gmdn_code` trên tập Asset cùng nhóm |
| MTTR (Mean Time To Repair) | Trung bình `Repair.duration` group by `Device Model.asset_category` |
| Downtime ratio | `OUT_OF_SERVICE_hours / TOTAL_hours` per GMDN |
| PM Compliance | `(PM hoàn thành đúng hạn / PM scheduled)` per category |

→ Lãnh đạo so sánh "Máy siêu âm tổng quát" vs "Máy siêu âm tim mạch" về độ tin cậy / chi phí — quyết định mua sắm thay thế.

### 1.4 Tiêu chuẩn hoá vật tư thay thế — IMM-15

Spare parts trên `IMM Device Spare Part` (child table của Device Model) có thể được liên kết với một hoặc nhiều nhóm GMDN. Khi mở Work Order sửa chữa (IMM-09), hệ thống gợi ý phụ tùng theo:
1. Spare list của chính Device Model (chính xác nhất)
2. Spare khả dụng cho các Device Model **cùng `gmdn_code`** (cross-model substitution)

### 1.5 Tuân thủ NĐ98 — IMM-05, IMM-16

NĐ98/2021 yêu cầu phân loại thiết bị y tế A/B/C/D. GMDN hỗ trợ:
- Mapping tự động `gmdn_code` ↔ `medical_device_class` qua bảng tra cứu BYT.
- Trường `has_radiation` trên Category drive yêu cầu giấy phép X-quang.
- Trường `registration_required` trên Device Model gate IMM-05 Asset Registration.

---

## 2. Mô hình kế thừa 3 tầng (Data Model)

### 2.1 Sơ đồ tầng

```
┌─────────────────────────────────────────────────────────┐
│ AC Asset Category (IMM-00)          ← SOURCE OF TRUTH   │
│ - category_code  (unique, set_only_once)                │
│ - gmdn_code      (unique)            ← khoá nghiệp vụ   │
│ - gmdn_term                                             │
│ - default_pm_required / interval                        │
│ - default_calibration_required / interval               │
│ - has_radiation                                         │
└──────────────────────┬──────────────────────────────────┘
                       │ (1:N) — autoload bằng controller
                       ▼
┌─────────────────────────────────────────────────────────┐
│ IMM Device Model (IMM-00)                               │
│ - asset_category   (Link → AC Asset Category, reqd)     │
│ - gmdn_code        (inherit nếu blank, có thể override) │
│ - gmdn_term        (inherit nếu blank)                  │
│ - medical_device_class                                  │
│ - pm_interval_days / calibration_interval_days          │
└──────────────────────┬──────────────────────────────────┘
                       │ (1:N) — autoload bằng fetch_from
                       ▼
┌─────────────────────────────────────────────────────────┐
│ AC Asset (IMM-05)                                       │
│ - device_model     (Link → IMM Device Model)            │
│ - gmdn_code        (fetch_from device_model.gmdn_code)  │
│ - gmdn_status                                           │
│ - serial_no        (unique)                             │
│ - asset_category   (denormalized cho query)             │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Cơ chế kế thừa thực tế trong code

**Tầng 2 (Device Model ← Category)** — controller [imm_device_model.py:46-57](../../assetcore/assetcore/doctype/imm_device_model/imm_device_model.py#L46-L57):

```python
# Pseudo từ code thực tế
cat = frappe.db.get_value(
    "AC Asset Category", self.asset_category,
    ["gmdn_code", "gmdn_term"], as_dict=True
)
if not self.gmdn_code and cat.get("gmdn_code"):
    self.gmdn_code = cat["gmdn_code"]
if not self.gmdn_term and cat.get("gmdn_term"):
    self.gmdn_term = cat["gmdn_term"]
```

→ **Override-able + cascade có kiểm soát (P3 Hybrid, 2026-05-19)**: controller `validate()` đặt cờ `gmdn_inherited` (Check, default 1) trên Device Model:

- `gmdn_code` rỗng hoặc `== Category.gmdn_code` → `gmdn_inherited = 1` (kế thừa).
- `gmdn_code` khác `Category.gmdn_code` → `gmdn_inherited = 0` (override cố ý).

Khi `AC Asset Category.gmdn_code` đổi (`ACAssetCategory.on_update` + `has_value_changed`), service `cascade_category_gmdn()` lan truyền:

1. CHỈ cập nhật Model `gmdn_inherited = 1` → đổi `gmdn_code` theo Category.
2. Model `gmdn_inherited = 0` được **giữ nguyên** (không bị đè) và ghi log danh sách bị bỏ qua.
3. Mỗi Model được cascade → re-sync `AC Asset.gmdn_code` của Model đó qua `resync_assets_gmdn_from_model()`.
4. Mỗi Asset thực sự đổi giá trị → ghi 1 dòng `IMM Audit Trail` (`event_type="System"`, `change_summary` mô tả from→to). Idempotent: giá trị đã đúng → không ghi audit thừa.

→ Khác hành vi cũ ("override KHÔNG re-sync, drift vĩnh viễn"): nay single source of truth được duy trì cho nhánh kế thừa, đồng thời TÔN TRỌNG override cố ý. Ref: [docs/res/plans/2026-05-19-gmdn-code-sync-strategy.md](plans/2026-05-19-gmdn-code-sync-strategy.md) §5.1 P3, §6 C1–C7.

> **Lưu ý phạm vi**: P3 chỉ là *cơ chế chống drift tương lai*. Không sửa giá trị `gmdn_code` hiện tại (đang là dữ liệu rác — blocker §8 của plan doc). Patch `v3_1/009_set_gmdn_inherited_flag` CHỈ set cờ `gmdn_inherited` cho Model cũ, KHÔNG đụng `gmdn_code`.

**Tầng 3 (Asset ← Device Model)** — kết hợp 2 cơ chế:

1. `fetch_from: device_model.gmdn_code` ở [ac_asset.json:308-309](../../assetcore/assetcore/doctype/ac_asset/ac_asset.json#L308-L309) — auto-fetch khi chọn Device Model trên UI.
2. Controller fallback [ac_asset.py:141-147](../../assetcore/assetcore/doctype/ac_asset/ac_asset.py#L141-L147) — nếu `fetch_from` không trigger (ví dụ import bulk), force inherit:

```python
def _inherit_gmdn_from_device_model(self) -> None:
    if self.gmdn_code or not self.device_model:
        return
    code = frappe.db.get_value("IMM Device Model", self.device_model, "gmdn_code")
    if code:
        self.gmdn_code = code
```

→ **Đảm bảo Asset luôn có gmdn_code** dù tạo qua UI, API, hay import wizard.

### 2.3 Vì sao tách 3 tầng (không nhập GMDN thẳng vào Asset)

| Câu hỏi | Trả lời |
|---|---|
| Tại sao không bỏ Asset Category, chỉ giữ Device Model? | Category là **policy layer** (PM/calibration default, khấu hao, has_radiation). 200 model cùng "máy siêu âm" share 1 policy — sửa 1 lần thay vì 200. |
| Tại sao Device Model giữ GMDN riêng (không hard-link)? | Cùng category nhưng dòng máy khác hãng đôi khi có **GMDN sub-term** chi tiết hơn (ví dụ Voluson E10 vs Voluson P8 — cùng GMDN parent nhưng EMDN khác). |
| Tại sao Asset cũng có gmdn_code (denormalize)? | Query KPI / recall **không cần JOIN 3 bảng** — index trực tiếp trên `AC Asset.gmdn_code`. Trade-off chấp nhận được vì update GMDN là sự kiện hiếm (gần như immutable sau cấu hình ban đầu). |

---

## 3. Quan hệ với các module nghiệp vụ

| Module | Cách sử dụng `gmdn_code` |
|---|---|
| IMM-05 Registration | Validate `registration_required` từ Device Model (kế thừa qua category) |
| IMM-08 PM | Auto-create PM Schedule từ `default_pm_interval_days` của Category |
| IMM-09 Repair | Gợi ý spare parts trong tập Device Model cùng GMDN |
| IMM-11 Calibration | Mandatory cho category `default_calibration_required = 1` (typically Class B/C/D) |
| IMM-12 Incident | Group incident theo GMDN để phát hiện cluster failure → trigger FSCA |
| IMM-15 Spare Inventory | Cross-model spare substitution trong cùng GMDN |
| IMM-16 QMS / CAPA | CAPA scope = mọi Asset cùng GMDN khi root cause là design defect |
| IMM-17 Reporting | Trục báo cáo chính: KPI per GMDN/Category |

---

## 4. Quy tắc thiết kế (Design Rules)

### 4.1 Bắt buộc

- ✅ `AC Asset Category.gmdn_code` là **unique** — KHÔNG cho phép 2 category cùng GMDN.
- ✅ `AC Asset Category.category_code` là `set_only_once` — không đổi sau khi tạo (đảm bảo audit trail nhất quán).
- ✅ Mọi `AC Asset` mới phải resolve được `gmdn_code` qua Device Model (controller fallback đảm bảo).
- ✅ Mọi report KPI nhóm thiết bị phải group bằng `gmdn_code` HOẶC `asset_category` — không nhóm bằng `device_model` (granularity sai).

### 4.2 Cấm

- ❌ KHÔNG hardcode GMDN trong service layer — luôn đọc từ Category/Model.
- ❌ KHÔNG cho phép Asset có `device_model` blank — Device Model là contract chứa GMDN.
- ❌ KHÔNG sửa GMDN sau khi Asset đã có Work Order — sẽ break truy vết lịch sử (cần workflow change request riêng nếu thực sự cần).
- ❌ KHÔNG dùng GMDN làm key tra cứu trực tiếp ở FE — luôn qua `asset_category` để có thông tin policy đi kèm.

---

## 5. Vấn đề mở / cần khảo sát thêm

1. **GMDN-NĐ98 class mapping table**: hiện `medical_device_class` nhập tay trên Device Model. Tương lai cần bảng tra cứu GMDN→Class A/B/C/D để auto-fill (giảm sai sót).
2. **EMDN expansion**: `IMM Device Model.emdn_code` đã có trường nhưng chưa có nguồn dữ liệu chuẩn EU EMDN — chờ BYT công bố mapping VN.
3. **GMDN versioning**: GMDN Agency phát hành CTS (Code Term Synonym) update hàng quý — cần job đồng bộ định kỳ (chưa triển khai).
4. **Cross-vendor spare substitution**: hiện chỉ gợi ý spare cùng GMDN, chưa cảnh báo về compatibility (ví dụ đầu dò Philips không lắp được vào GE dù cùng GMDN) — cần thêm trường `oem_compatibility` trên spare part.

---

---

## 6. Phân tích phê bình — Bộ lọc "GMDN" và `gmdn_status` trên trang `/assets`

### 6.1 Hiện trạng thực tế (as-implemented 2026-05-19)

**FE — [AssetListView.vue](../../frontend/src/views/asset/AssetListView.vue):**

- Dropdown filter "GMDN" — 2 lựa chọn duy nhất:
  - `In Use` → "Đang sử dụng"
  - `Not Use` → "Không sử dụng"
- Cột bảng tên "GMDN" — render chip màu xanh/xám theo `gmdn_status`, KHÔNG hiển thị `gmdn_code` hay `gmdn_term`.
- Tooltip / mô tả — không có.

**BE — [services/imm00.py:223-275](../../assetcore/services/imm00.py#L223-L275):**

```python
_GMDN_STATUS_ACTIVE   = "In Use"
_GMDN_STATUS_INACTIVE = "Not Use"
_GMDN_BLOCKED_LIFECYCLE = (OUT_OF_SERVICE, DECOMMISSIONED)

def update_gmdn_status(asset_name, gmdn_status, reason):
    # raise nếu cố set "In Use" khi lifecycle ∈ {Out of Service, Decommissioned}
    # raise nếu reason < 5 ký tự
    # ghi audit event_type="State Change"

def toggle_gmdn_status_via_qr(asset_name):
    # clinical user scan QR điện thoại → toggle giá trị, reason = "Quét QR @ <timestamp>"
```

**Schema — [ac_asset.json:313-322](../../assetcore/assetcore/doctype/ac_asset/ac_asset.json#L313-L322):**

```json
{
  "fieldname": "gmdn_status",
  "fieldtype": "Select",
  "options": "In Use\nNot Use",
  "default": "Not Use",
  "read_only": 1,
  "search_index": 1
}
```

### 6.2 Các vấn đề (tại sao "chưa đúng thực tế và không dùng được")

#### Vấn đề 1 — Tên field gây hiểu lầm nghiêm trọng (semantic collision)

`gmdn_status` **không phải** là status của *mã GMDN*. Theo GMDN Agency (ISO 15225), status hợp lệ của một GMDN code là:

| GMDN code status (chuẩn ISO 15225) | Ý nghĩa |
|---|---|
| `Active` | Mã GMDN đang được sử dụng |
| `Obsolete` | Mã đã bị thay thế (replaced by newer term) |
| `Replaced` | Có mã thay thế chính thức |
| `Pending` | Đang trong quy trình đánh giá |

Trong AssetCore hiện tại, "gmdn_status = In Use / Not Use" thực ra mô tả **trạng thái sử dụng lâm sàng của Asset cá thể** — không liên quan gì tới GMDN nomenclature. Người dùng đọc field name sẽ hiểu sai.

#### Vấn đề 2 — Trùng lặp ngữ nghĩa 100% với `lifecycle_status`

`lifecycle_status` đã có 6 giá trị bao trùm trạng thái sử dụng:

| lifecycle_status | Đang dùng được? |
|---|---|
| Commissioned | Có |
| Active | Có |
| Under Repair | Không |
| Calibrating | Không |
| Out of Service | Không |
| Decommissioned | Không |

Logic BE đã enforce: `gmdn_status = "In Use"` bị **chặn cứng** khi `lifecycle_status ∈ {Out of Service, Decommissioned}` ([imm00.py:245-246](../../assetcore/services/imm00.py#L245-L246)). Tức là `gmdn_status` là **proper subset** của `lifecycle_status` — không bổ sung thông tin mới, chỉ duplicate.

#### Vấn đề 3 — Filter UI thiếu cái cần, thừa cái không dùng

| Filter | Có giá trị nghiệp vụ? | Hiện trạng |
|---|---|---|
| Lọc theo `gmdn_status` (In/Not Use) | ❌ Không — đã có lifecycle filter | ✅ Có (thừa) |
| Lọc theo `gmdn_code` (mã thật) | ✅ Có — recall, FSCA, KPI | ❌ Không có |
| Lọc theo `gmdn_term` (tên thuật ngữ) | ✅ Có — search by domain term | ❌ Không có |
| Search GMDN trong ô search chính | ✅ Có | ❌ Search chỉ cover name/code/serial |

**Use case bị bỏ lỡ**: BA mở `/assets` rồi nói "lọc cho tôi tất cả máy siêu âm mã GMDN 35304" → KHÔNG làm được trên UI hiện tại. Buộc phải lọc qua `asset_category` (giả định mapping 1:1) — không đúng khi 1 category có thể chứa nhiều GMDN subcode.

#### Vấn đề 4 — Cột bảng "GMDN" hiển thị sai cái

Header cột là "GMDN" → user mong đợi xem **mã GMDN** (số 5 chữ số, ví dụ `35304`) hoặc **term** ("Ultrasound imaging system, general purpose"). Thực tế hiển thị một chip **In Use / Not Use** — vô nghĩa với người làm việc với GMDN nomenclature thật.

Trong khi đó, field `gmdn_code` **đã có** trên Asset (fetch_from device_model) — nhưng **không bao giờ được render** trên list view.

#### Vấn đề 5 — Default `"Not Use"` cứng → dashboard sai từ ngày đầu

Schema khai báo `default: "Not Use"`. Mọi Asset mới tạo (qua UI, API, import wizard) đều bắt đầu với `gmdn_status = "Not Use"`. Nếu KPI dashboard "% thiết bị đang sử dụng" group by `gmdn_status` → tất cả Asset mới bị đếm sai về phía "không dùng" cho tới khi có người scan QR / update thủ công.

Bằng chứng: có 2 patch script đã phải sửa retro:
- [scripts/fix_asset_gmdn.py](../../assetcore/scripts/fix_asset_gmdn.py) — set tất cả về `"In Use"`
- [scripts/fix_master_display_names.py:69-72](../../assetcore/scripts/fix_master_display_names.py#L69-L72) — sửa `"Not Use"` thành `"Active"` (giá trị KHÔNG hợp lệ theo schema!) — chứng tỏ ngay developer cũng confuse semantic.

#### Vấn đề 6 — Pattern QR toggle dùng sai field

Function `toggle_gmdn_status_via_qr` cho phép clinical user **quét QR trên điện thoại → flip on/off Asset**. Đây là use case **"clinical check-in/check-out"** hợp lý cho quản lý mượn-trả thiết bị di động (máy đo huyết áp, máy ECG cầm tay).

Nhưng tên field là `gmdn_status` — hoàn toàn lệch ngữ cảnh. Đáng lẽ phải là một field riêng như `clinical_availability` / `in_use_now` / `checkout_state`, KHÔNG trộn vào trục GMDN nomenclature.

#### Vấn đề 7 — Audit log mix trục, khó phân tích

Khi gọi `update_gmdn_status`, audit ghi `event_type="State Change"` ([imm00.py:255](../../assetcore/services/imm00.py#L255)) — đè cùng kênh với lifecycle state change. Hệ quả:
- Query audit timeline của Asset không tách được "lifecycle change" vs "availability toggle".
- Report tần suất check-in/out (đáng lẽ tách kênh) bị nhiễu bởi lifecycle event.

#### Vấn đề 8 — `gmdn_code` trên Asset đang denormalize sai chỗ

`AC Asset.gmdn_code` fetch từ `device_model.gmdn_code` — nhưng nếu user **sửa GMDN trên Device Model** sau khi Asset đã được commissioned thì sao? Không có hook đồng bộ ngược — Asset cũ giữ giá trị cũ. Đây là silent data drift, không có audit.

Tương tự nếu user **đổi `device_model`** trên Asset — `gmdn_code` không tự cập nhật trừ khi blank (logic `_inherit_gmdn_from_device_model` chỉ chạy khi `gmdn_code` falsy).

### 6.3 Quyết định thiết kế (chốt 2026-05-19)

**Bỏ hoàn toàn `gmdn_status`. Thiết bị được lọc và quản lý theo `gmdn_code` (kế thừa từ Asset Category).**

Lý do chốt:
- `gmdn_status` (In Use / Not Use) là **subset của `lifecycle_status`** — không bổ sung thông tin nghiệp vụ.
- Concern "QR check-in/check-out lâm sàng" **không thuộc trục GMDN** — nếu cần, sẽ làm thành tính năng riêng (`clinical_availability`) ở backlog, KHÔNG sửa chữa field `gmdn_status` hiện tại.
- Trục lọc nghiệp vụ đúng = `gmdn_code` của Asset Category — đảm bảo recall, KPI, spare substitution chạy đúng.
- Loại bỏ kỹ thuật debt: 2 fix-script ([fix_asset_gmdn.py](../../assetcore/scripts/fix_asset_gmdn.py), [fix_master_display_names.py](../../assetcore/scripts/fix_master_display_names.py)) đã chứng tỏ field này gây nhầm lẫn ngay cả với dev.

### 6.4 Phạm vi thay đổi

| Layer | Item | Hành động |
|---|---|---|
| Schema | `AC Asset.gmdn_status` (Select field) | **DROP** — qua patch `008_drop_gmdn_status` |
| Schema | `AC Asset.gmdn_code` | **GIỮ** — đã fetch_from `device_model.gmdn_code` |
| Service | `services/imm00.py::update_gmdn_status` | **DELETE** |
| Service | `services/imm00.py::toggle_gmdn_status_via_qr` | **DELETE** |
| Service | constants `_GMDN_STATUS_ACTIVE/INACTIVE/BLOCKED_LIFECYCLE` | **DELETE** |
| API | `api/imm00.py::update_gmdn_status` (whitelist) | **DELETE** |
| API | `api/imm00.py::toggle_gmdn_status` (whitelist) | **DELETE** |
| API | `api/imm00.py::list_assets` param `gmdn_status` | **DELETE** |
| API | `api/imm00.py::list_assets` param `gmdn_code` | **ADD** — filter mới |
| API | `api/imm00.py::list_assets` `or_filters` search | **EXTEND** — thêm `gmdn_code`, `gmdn_term` |
| FE types | `GmdnStatus` type, `gmdn_status?` properties | **DELETE** |
| FE api | `updateGmdnStatus`, `toggleGmdnStatus` | **DELETE** |
| FE store | `GMDN_OPTIONS`, `GMDN_STATUS_LABEL`, `updateGmdn` | **DELETE** |
| FE list | dropdown "GMDN" (status) | **DELETE** |
| FE list | dropdown "GMDN Code" mới | **ADD** — autocomplete từ Asset Category |
| FE list | cột "GMDN" (chip status) | **REWRITE** — hiển thị `gmdn_code` + tooltip `gmdn_term` |
| FE detail | modal đổi GMDN Status | **DELETE** |
| FE detail | section hiển thị GMDN | **KEEP** — readonly `gmdn_code`/`gmdn_term` |
| FE QR scan | `QRScanView.vue` (toggle gmdn) | **REPURPOSE** — quét QR → mở Asset detail (không toggle) |
| Scripts | `scripts/fix_asset_gmdn.py` | **DELETE** |
| Scripts | `scripts/fix_master_display_names.py` block gmdn | **CLEAN** |
| Scripts | `scripts/cleanup_and_seed_assets.py` gmdn_status keys | **CLEAN** |
| Scripts | `scripts/audit_master_data.py` gmdn_status field | **CLEAN** |

### 6.5 Plan triển khai

Plan chi tiết theo TDD step-by-step → xem [docs/superpowers/plans/2026-05-19-drop-gmdn-status.md](../superpowers/plans/2026-05-19-drop-gmdn-status.md).

Tóm tắt:
1. **BE first** — viết test cho list_assets với filter `gmdn_code` (failing) → drop service/API GMDN status → add gmdn_code filter + search extend → patch drop column → schema sync.
2. **FE second** — drop types/api/store → rewrite AssetListView (filter + column) → AssetDetailView readonly → repurpose QRScanView.
3. **Cleanup** — scripts + docs imm-00 + final smoke test trên `/assets`.

---

## 7. Tham chiếu chéo

- Source code:
  - [ac_asset_category.json](../../assetcore/assetcore/doctype/ac_asset_category/ac_asset_category.json) — schema tầng 1
  - [ac_asset_category.py](../../assetcore/assetcore/doctype/ac_asset_category/ac_asset_category.py) — validator GMDN unique
  - [imm_device_model.json](../../assetcore/assetcore/doctype/imm_device_model/imm_device_model.json) — schema tầng 2
  - [imm_device_model.py](../../assetcore/assetcore/doctype/imm_device_model/imm_device_model.py) — controller kế thừa từ category
  - [ac_asset.json](../../assetcore/assetcore/doctype/ac_asset/ac_asset.json) — schema tầng 3 + fetch_from
  - [ac_asset.py](../../assetcore/assetcore/doctype/ac_asset/ac_asset.py) — controller fallback inherit
- Docs:
  - [docs/imm-00/](../imm-00/) — Module Master Data
  - [docs/gmdn/Quyết định 3107_QĐ-BYT.md](../gmdn/Quyết%20định%203107_QĐ-BYT.md)
  - [docs/gmdn/Quyết định 69_QĐ-BYT.md](../gmdn/Quyết%20định%2069_QĐ-BYT.md)
  - [docs/gmdn/Quyết định 847_QĐ-BYT.md](../gmdn/Quyết%20định%20847_QĐ-BYT.md)
- Regulation: NĐ98/2021/NĐ-CP — Quản lý trang thiết bị y tế
- Standard: ISO 15225:2010 — Medical devices — Quality management — Medical device nomenclature data structure
