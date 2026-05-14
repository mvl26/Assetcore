# ERPNext Core — Phân tích dữ liệu gốc & Chiến lược kế thừa AssetCore

**Phiên bản:** 1.0 | **Ngày:** 2026-04-17
**Mục tiêu:** Trả lời rõ ràng: dữ liệu tài sản, PO, NCC, thực thể nền tảng lưu ở đâu trong ERPNext — và AssetCore kế thừa, đóng gói lại như thế nào thành phần mềm quản lý vòng đời tài sản hoàn chỉnh.

---

## 1. Kiến trúc dữ liệu ERPNext — Bức tranh tổng thể

ERPNext là ERP đa module. Mỗi DocType tương ứng một bảng MariaDB với quy ước `tab[DocTypeName]`.

```
ERPNext Database (MariaDB)
│
├── SETUP (Dữ liệu nền tảng)
│   ├── tabCompany          → Công ty / Bệnh viện
│   ├── tabDepartment       → Khoa, phòng ban (cây phân cấp)
│   ├── tabEmployee         → Nhân viên, KTV
│   ├── tabUser             → Tài khoản hệ thống
│   ├── tabRole             → Vai trò phân quyền
│   └── tabCurrency         → Tiền tệ
│
├── STOCK / INVENTORY (Vật tư & Kho)
│   ├── tabItem             → Danh mục vật tư / thiết bị (Model catalog)
│   ├── tabItem_Supplier    → Bảng NCC của Item (child)
│   ├── tabWarehouse        → Kho lưu trữ
│   ├── tabSerial_No        → Số serial từng đơn vị
│   ├── tabBatch            → Lô hàng
│   └── tabStock_Entry      → Phiếu nhập/xuất kho
│
├── BUYING (Mua sắm)
│   ├── tabSupplier         → Nhà cung cấp (NCC)
│   ├── tabSupplier_Group   → Nhóm NCC
│   ├── tabRequest_For_Quotation → Yêu cầu báo giá
│   ├── tabSupplier_Quotation   → Báo giá NCC
│   ├── tabPurchase_Order   → Đơn đặt hàng (PO)
│   ├── tabPurchase_Order_Item  → Chi tiết PO (child)
│   └── tabPurchase_Receipt → Phiếu nhận hàng
│
├── ACCOUNTS (Kế toán)
│   ├── tabPurchase_Invoice → Hóa đơn mua hàng
│   ├── tabPayment_Entry    → Phiếu thanh toán
│   ├── tabJournal_Entry    → Bút toán kế toán
│   └── tabCost_Center      → Trung tâm chi phí
│
└── ASSETS (Tài sản cố định)
    ├── tabAsset            → DANH SÁCH TÀI SẢN (registry trung tâm)
    ├── tabAsset_Category   → Phân loại tài sản
    ├── tabLocation         → Vị trí (cây phân cấp)
    ├── tabAsset_Movement   → Điều chuyển tài sản
    ├── tabAsset_Repair     → Sửa chữa (cơ bản)
    ├── tabAsset_Maintenance → Bảo trì (cơ bản)
    └── tabAsset_Finance_Book → Sổ khấu hao (child)
```

---

## 2. Thực thể gốc 1 — DANH SÁCH TÀI SẢN (`tabAsset`)

### Lưu ở đâu?
**Bảng:** `tabAsset` trong MariaDB
**Module:** `erpnext/assets/`
**Naming series mặc định:** `ACC-ASS-.YYYY.-`

### Tất cả field quan trọng

```
┌─────────────────────────────────────────────────────────────────────┐
│                     tabAsset (ERPNext)                              │
├───────────────────────┬──────────────┬──────────────────────────────┤
│ Field Name            │ Type         │ Mô tả                        │
├───────────────────────┼──────────────┼──────────────────────────────┤
│ name                  │ varchar(140) │ ID document (Primary Key)    │
│ asset_name            │ Data         │ Tên tài sản                  │
│ item_code             │ Link→Item    │ Mã vật tư (catalog model)    │
│ asset_category        │ Link→AssetCat│ Phân loại (auto từ Item)     │
│ company               │ Link→Company │ Đơn vị sở hữu               │
│ location              │ Link→Location│ Vị trí hiện tại              │
│ custodian             │ Link→Employee│ Người phụ trách              │
│ department            │ Link→Dept    │ Khoa/Phòng ban               │
│ supplier              │ Link→Supplier│ NCC (khi asset_owner=Supplier)│
│ purchase_date         │ Date         │ Ngày mua                     │
│ available_for_use_date│ Date         │ Ngày đưa vào sử dụng         │
│ gross_purchase_amount │ Currency     │ Giá trị mua ban đầu          │
│ asset_quantity        │ Int (def=1)  │ Số lượng                     │
│ status                │ Select       │ Draft/Submitted/In Maint/    │
│                       │              │ Out of Order/Sold/Scrapped   │
│ purchase_receipt      │ Link→PR      │ Phiếu nhận hàng              │
│ purchase_invoice      │ Link→PI      │ Hóa đơn mua                  │
│ maintenance_required  │ Check        │ Cần bảo trì định kỳ          │
│ is_existing_asset     │ Check        │ Tài sản đang tồn tại (import)│
│ calculate_depreciation│ Check        │ Có tính khấu hao             │
│ depreciation_method   │ Select       │ Straight Line/DDB/Manual     │
│ finance_books         │ Table        │ Sổ khấu hao (child)          │
│ insurance_*           │ —            │ Bảo hiểm tài sản             │
│ split_from            │ Link→Asset   │ Tách từ tài sản gốc          │
│ amended_from          │ Link→Asset   │ Sửa đổi từ version trước     │
├───────────────────────┼──────────────┼──────────────────────────────┤
│ docstatus             │ Int          │ 0=Draft, 1=Submit, 2=Cancel  │
│ modified              │ Datetime     │ Lần sửa gần nhất             │
│ modified_by           │ Link→User    │ Người sửa                    │
│ creation              │ Datetime     │ Ngày tạo                     │
│ owner                 │ Link→User    │ Người tạo                    │
└───────────────────────┴──────────────┴──────────────────────────────┘
```

### Vòng đời tạo Asset trong ERPNext

```
Item (is_fixed_asset=1, auto_create_assets=1)
    ↓
Purchase Order → Purchase Receipt
    ↓  (khi nhận hàng)
[Auto] tabAsset created với:
    - item_code = Purchase Receipt Item.item_code
    - gross_purchase_amount = Purchase Receipt Item.valuation_rate
    - purchase_receipt = Purchase Receipt.name
    - status = "Draft"

Sau đó Submit Asset:
    status → "Submitted"
    → Bắt đầu schedule khấu hao
```

### AssetCore kế thừa `tabAsset` như thế nào?

```
tabAsset (GIỮ NGUYÊN — KHÔNG SỬA)
    │
    ├── Thêm 16 Custom Fields (via bench migrate):
    │   custom_imm_device_model       Link → IMM Device Model
    │   custom_imm_medical_class      Select: Class I/II/III
    │   custom_imm_risk_class         Select: Low/Medium/High/Critical
    │   custom_imm_byt_reg_no         Data (Số đăng ký BYT)
    │   custom_imm_manufacturer_sn    Data (S/N nhà sản xuất)
    │   custom_imm_udi_code           Data (UDI/GMDN)
    │   custom_imm_lifecycle_status   Select: Active/Under Repair/
    │                                          Calibrating/OOS/Decommissioned
    │   custom_imm_calibration_status Select: In Tolerance/OOT/Overdue
    │   custom_imm_dept               Link → Department
    │   custom_imm_last_pm_date       Date
    │   custom_imm_next_pm_date       Date
    │   custom_imm_last_cal_date      Date
    │   custom_imm_next_cal_date      Date
    │   custom_imm_responsible_tech   Link → User
    │   custom_imm_commissioning_ref  Link → IMM Commissioning Record
    │   custom_imm_gmdn_code          Data
    │
    └── AssetCore DocTypes link về đây:
        IMM Commissioning Record  (asset field)
        IMM Asset Document        (asset_ref field)
        IMM PM Schedule           (asset field)
        IMM PM Work Order         (asset field)
        IMM CM Work Order         (asset field)
        IMM Asset Calibration     (asset field)
        IMM Incident Report       (asset field)
        IMM Audit Trail           (asset field)
```

---

## 3. Thực thể gốc 2 — NHÀ CUNG CẤP (`tabSupplier`)

### Lưu ở đâu?
**Bảng:** `tabSupplier` trong MariaDB
**Module:** `erpnext/buying/`
**Naming:** `SUP-.YYYY.-` hoặc theo tên

### Tất cả field quan trọng

```
┌─────────────────────────────────────────────────────────────────────┐
│                    tabSupplier (ERPNext)                            │
├───────────────────────┬──────────────┬──────────────────────────────┤
│ Field Name            │ Type         │ Mô tả                        │
├───────────────────────┼──────────────┼──────────────────────────────┤
│ name                  │ varchar(140) │ ID (= supplier_name)         │
│ supplier_name         │ Data         │ Tên NCC (required, unique)   │
│ supplier_group        │ Link→SupGroup│ Nhóm NCC                     │
│ supplier_type         │ Select       │ Company/Individual/Partner   │
│ country               │ Link→Country │ Quốc gia                     │
│ tax_id                │ Data         │ Mã số thuế                   │
│ default_currency      │ Link→Currency│ Tiền tệ mặc định             │
│ default_price_list    │ Link→PriceL  │ Bảng giá mặc định            │
│ payment_terms         │ Link→PayTerms│ Điều khoản thanh toán        │
│ supplier_primary_addr │ Link→Address │ Địa chỉ chính                │
│ supplier_primary_cntct│ Link→Contact │ Liên hệ chính                │
│ mobile_no             │ Data (r/o)   │ SĐT (fetch từ Contact)       │
│ email_id              │ Data (r/o)   │ Email (fetch từ Contact)     │
│ accounts              │ Table        │ Party Account per company    │
│ disabled              │ Check        │ Vô hiệu hóa NCC              │
│ on_hold               │ Check        │ Tạm khóa                     │
│ hold_type             │ Select       │ All/Invoices/Payments        │
│ is_internal_supplier  │ Check        │ Nội bộ                       │
│ represents_company    │ Link→Company │ Đại diện công ty nào         │
│ language              │ Link→Language│ Ngôn ngữ                     │
│ allow_purchase_inv_   │ Check        │ Cho phép tạo PI không có PO  │
│ without_purchase_order│              │                              │
└───────────────────────┴──────────────┴──────────────────────────────┘
```

### AssetCore kế thừa `tabSupplier` như thế nào?

ERPNext `Supplier` lưu thông tin thương mại (thanh toán, địa chỉ). AssetCore cần thêm thông tin kỹ thuật y tế:

```
tabSupplier (GIỮ NGUYÊN)
    │
    └── IMM Vendor Profile (DocType mới — link về Supplier)
        ├── supplier           Link → Supplier (ERPNext)
        ├── vendor_type        Select: Manufacturer/Distributor/Service Agent
        ├── iso_13485_certified Check  (ISO quản lý thiết bị y tế)
        ├── iso_17025_certified Check  (Lab hiệu chuẩn được công nhận)
        ├── moh_registration_no Data   (Số phép BYT)
        ├── support_hotline    Data
        ├── service_contract_ref Data
        ├── contract_start/end Date
        ├── sla_response_hours Int     (Cam kết thời gian phản hồi)
        └── authorized_techs   Table   (KTV được NCC ủy quyền)
```

---

## 4. Thực thể gốc 3 — ĐƠN ĐẶT HÀNG (`tabPurchase_Order`)

### Lưu ở đâu?
**Bảng:** `tabPurchase_Order` + `tabPurchase_Order_Item` (child)
**Module:** `erpnext/buying/`
**Naming:** `PUR-ORD-.YYYY.-`

### Tất cả field quan trọng

```
┌─────────────────────────────────────────────────────────────────────┐
│                  tabPurchase_Order (ERPNext)                        │
├───────────────────────┬──────────────┬──────────────────────────────┤
│ Field Name            │ Type         │ Mô tả                        │
├───────────────────────┼──────────────┼──────────────────────────────┤
│ name                  │ varchar(140) │ Số PO (PUR-ORD-2026-00001)   │
│ supplier              │ Link→Supplier│ NCC (required, search-indexed│
│ supplier_name         │ Data (r/o)   │ Tên NCC (auto fetch)         │
│ company               │ Link→Company │ Công ty mua                  │
│ transaction_date      │ Date         │ Ngày đặt hàng                │
│ schedule_date         │ Date         │ Ngày giao hàng dự kiến       │
│ order_confirmation_no │ Data         │ Số xác nhận của NCC          │
│ order_confirmation_dt │ Date         │ Ngày xác nhận                │
│ currency              │ Link→Currency│ Tiền tệ                      │
│ conversion_rate       │ Float        │ Tỷ giá                       │
│ buying_price_list     │ Link→PriceL  │ Bảng giá                     │
│ items                 │ Table        │ → tabPurchase_Order_Item      │
│ taxes                 │ Table        │ Thuế/phí                     │
│ total_qty             │ Float (agg)  │ Tổng SL                      │
│ net_total             │ Currency     │ Tổng trước thuế              │
│ grand_total           │ Currency     │ Tổng sau thuế                │
│ supplier_address      │ Link→Address │ Địa chỉ NCC                  │
│ contact_person        │ Link→Contact │ Người liên hệ                │
│ shipping_address      │ Link→Address │ Địa chỉ giao hàng            │
│ cost_center           │ Link→CostCtr │ Trung tâm chi phí            │
│ project               │ Link→Project │ Dự án                        │
│ payment_terms_template│ Link→PayTerm │ Điều khoản thanh toán        │
│ payment_schedule      │ Table        │ Lịch thanh toán              │
│ status                │ Select       │ Draft/To Receive/To Bill/    │
│                       │              │ Completed/Cancelled/Closed   │
│ per_received          │ Float (agg)  │ % đã nhận hàng               │
│ per_billed            │ Float (agg)  │ % đã lập hóa đơn             │
│ terms                 │ Text         │ Điều khoản PO                │
│ docstatus             │ Int          │ 0/1/2                        │
└───────────────────────┴──────────────┴──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│              tabPurchase_Order_Item (Child Table)                   │
├───────────────────────┬──────────────┬──────────────────────────────┤
│ item_code             │ Link→Item    │ Mã hàng (thiết bị)           │
│ item_name             │ Data         │ Tên hàng                     │
│ description           │ Text         │ Mô tả chi tiết               │
│ qty                   │ Float        │ Số lượng                     │
│ uom                   │ Link→UOM     │ Đơn vị tính                  │
│ rate                  │ Currency     │ Đơn giá                      │
│ amount                │ Currency     │ Thành tiền                   │
│ warehouse             │ Link→Wareh   │ Kho nhận hàng                │
│ received_qty          │ Float        │ SL đã nhận (auto cập nhật)   │
│ billed_amt            │ Currency     │ Đã lập hóa đơn               │
│ cost_center           │ Link→CC      │ Trung tâm chi phí            │
│ project               │ Link→Project │ Dự án                        │
│ expected_delivery_date│ Date         │ Ngày giao dự kiến            │
└───────────────────────┴──────────────┴──────────────────────────────┘
```

### AssetCore kế thừa `tabPurchase_Order` như thế nào?

PO lưu trong ERPNext là **nguồn dữ liệu gốc**. AssetCore link về, không tái tạo:

```
tabPurchase_Order (GIỮ NGUYÊN)
    │
    └── IMM Commissioning Record:
        po_reference    Data    (Số PO để tra cứu)
        master_item     Link → Item (thiết bị trong PO)
        vendor          Link → Supplier (NCC trong PO)

        Khi tạo Commissioning Record:
        - User nhập po_reference
        - System fetch: vendor, item_code, quantity từ PO
        - Không duplicate data — chỉ reference
```

---

## 5. Thực thể gốc 4 — DANH MỤC VẬT TƯ / THIẾT BỊ (`tabItem`)

### Lưu ở đâu?
**Bảng:** `tabItem` + `tabItem_Supplier` (child) + `tabItem_Default` (child)
**Module:** `erpnext/stock/`
**Naming:** Theo `item_code` (do user định nghĩa)

### Field quan trọng cho thiết bị y tế

```
┌─────────────────────────────────────────────────────────────────────┐
│                      tabItem (ERPNext)                              │
├───────────────────────┬──────────────┬──────────────────────────────┤
│ Field Name            │ Type         │ Relevance cho AssetCore      │
├───────────────────────┼──────────────┼──────────────────────────────┤
│ item_code             │ Data (PK)    │ Mã thiết bị (unique)         │
│ item_name             │ Data         │ Tên thiết bị                 │
│ item_group            │ Link→ItmGrp  │ Nhóm thiết bị                │
│ stock_uom             │ Link→UOM     │ Đơn vị tính                  │
│ is_fixed_asset        │ Check ✅     │ Đây là tài sản cố định       │
│ auto_create_assets    │ Check ✅     │ Tự tạo Asset khi nhận hàng   │
│ is_grouped_asset      │ Check        │ Asset theo lô                │
│ asset_category        │ Link→AssetCat│ Gán loại tài sản             │
│ asset_naming_series   │ Select       │ Chuỗi đánh số cho Asset      │
│ has_serial_no         │ Check ✅     │ Theo dõi serial number       │
│ warranty_period       │ Int          │ Thời hạn bảo hành (tháng)    │
│ brand                 │ Link→Brand   │ Hãng sản xuất                │
│ description           │ Text         │ Mô tả kỹ thuật               │
│ supplier_items        │ Table        │ → tabItem_Supplier (NCC)     │
│ lead_time_days        │ Int          │ Thời gian giao hàng          │
│ min_order_qty         │ Float        │ SL đặt hàng tối thiểu        │
│ last_purchase_rate    │ Currency     │ Giá mua gần nhất             │
│ is_purchase_item      │ Check        │ Có thể mua                   │
│ disabled              │ Check        │ Vô hiệu hóa                  │
│ image                 │ Attach Image │ Ảnh thiết bị                 │
│ barcodes              │ Table        │ Barcode/QR code              │
└───────────────────────┴──────────────┴──────────────────────────────┘
```

### Item vs IMM Device Model — Phân biệt rõ ràng

```
ERPNext Item                      IMM Device Model (AssetCore)
════════════════                  ════════════════════════════
Mục đích: Quản lý vật tư/        Mục đích: Catalog kỹ thuật thiết
          hàng hóa để mua bán              bị y tế

Chứa: Mã hàng, giá, kho,        Chứa: GMDN code, Class I/II/III,
      NCC, bảo hành                       PM interval, Cal interval,
                                          service manual, IFU, firmware

Quan hệ: 1 Item = 1 loại        Quan hệ: 1 Device Model = 1 loại
          hàng hóa                         thiết bị y tế cụ thể

Dùng trong: PO, PR, Invoice      Dùng trong: Commissioning, PM
                                             Schedule, Calibration

Kế thừa: IMM Device Model        Link về: Item (item_code field)
          link về Item
```

---

## 6. Thực thể gốc 5 — PHIẾU NHẬN HÀNG & CHUỖI MUA SẮM

### Luồng dữ liệu đầy đủ từ Procurement → Asset

```
BƯỚC 1: Lập kế hoạch mua sắm
tabRequest_For_Quotation  ← Yêu cầu báo giá (RFQ)
    ↓ gửi cho NCC
tabSupplier_Quotation     ← Báo giá từ NCC

BƯỚC 2: Đặt hàng
tabPurchase_Order         ← PO được duyệt
    fields: supplier, items(item_code, qty, rate), company
    ↓

BƯỚC 3: Nhận hàng
tabPurchase_Receipt       ← Phiếu nhận hàng (GRN)
    fields: supplier, purchase_order, items
    ↓ (nếu Item.auto_create_assets = 1)
[Auto] tabAsset CREATED   ← Tài sản được tạo tự động!
    - item_code     = from PO item
    - purchase_receipt = Purchase Receipt.name
    - gross_purchase_amount = valuation_rate
    - status = "Draft"

BƯỚC 4: Thanh toán
tabPurchase_Invoice       ← Hóa đơn NCC
    link → Purchase Order, Purchase Receipt
    ↓
tabPayment_Entry          ← Phiếu chi thanh toán
    link → Purchase Invoice

BƯỚC 5: Đưa vào sử dụng (AssetCore)
IMM Commissioning Record  ← Lắp đặt, kiểm tra ban đầu
    po_reference = Purchase Order.name
    → Approve → Final Asset (Submit tabAsset)
    → Thêm custom fields (class, risk, serial, device model...)
```

---

## 7. Thực thể gốc 6 — TỔ CHỨC & NHÂN SỰ

### `tabCompany` — Bệnh viện / Đơn vị sở hữu

```
tabCompany
├── company_name          "Bệnh viện Nhi Đồng 1"
├── abbr                  "NDIH1"
├── default_currency      "VND"
├── country               "Vietnam"
├── cost_center           → tabCost_Center (phòng/khoa)
├── accumulated_depreciation_account → Tài khoản khấu hao lũy kế
├── depreciation_expense_account     → Chi phí khấu hao
├── capital_work_in_progress_account → CWIP (lắp đặt chưa hoàn thành)
└── disposal_account                 → Thanh lý tài sản
```

### `tabDepartment` — Khoa, Phòng ban (Cây phân cấp)

```
tabDepartment (Tree DocType — lưu lft/rgt cho nested set)
├── department_name       "Khoa Hồi Sức Cấp Cứu"
├── parent_department     → Department (cha)
├── company               → Company
├── is_group              1/0 (có phải nhóm không)
└── disabled              1/0

Cây ví dụ:
Bệnh viện Nhi Đồng 1 (is_group=1)
├── Khối Lâm sàng (is_group=1)
│   ├── Khoa HSCC
│   ├── Khoa Nội
│   └── Khoa Ngoại
├── Khối Cận lâm sàng (is_group=1)
│   ├── Khoa Xét nghiệm
│   └── Khoa CĐHA
└── Phòng VTBYT (is_group=1)
    ├── Workshop HTM
    └── Kho trung tâm
```

### `tabEmployee` — Nhân viên, KTV

```
tabEmployee
├── employee_name         "Nguyễn Văn A"
├── user_id               Link → tabUser (tài khoản đăng nhập)
├── department            Link → tabDepartment
├── designation           Link → Designation ("Kỹ thuật viên TBYT")
├── reports_to            Link → Employee (quản lý trực tiếp)
├── company               Link → Company
├── status                Active / Left
├── cell_number           SĐT
├── company_email         Email công ty
└── date_of_joining       Ngày vào làm
```

### `tabUser` — Tài khoản hệ thống

```
tabUser
├── email                 "ktv.nguyenvana@benhvien.vn" (Primary Key thực tế)
├── full_name             "Nguyễn Văn A"
├── enabled               1/0
├── roles                 Table → tabUser_Role
│   ├── Role: IMM Technician
│   ├── Role: IMM Document Officer
│   └── ...
├── user_type             "System User"
└── last_active           Datetime (theo dõi hoạt động)
```

### `tabLocation` — Vị trí vật lý (Cây phân cấp)

```
tabLocation (Tree DocType)
├── location_name         "Phòng Hồi Sức A3"
├── parent_location       → Location (cha)
├── is_group              1/0
├── latitude / longitude  GPS coordinates
├── area                  Diện tích (m²)
└── location (Geolocation) Bản đồ GeoJSON

Cây ví dụ:
BV Nhi Đồng 1 Compound (is_group=1)
├── Tòa A (is_group=1)
│   ├── Tầng 1 (is_group=1)
│   │   ├── Khoa HSCC - Phòng 1A
│   │   └── Khoa HSCC - Phòng 1B
│   └── Tầng 2 (is_group=1)
│       └── Khoa Nội - Phòng 2A
└── Khu Workshop HTM
    ├── Workshop chính
    └── Kho phụ tùng
```

---

## 8. Thực thể gốc 7 — KẾ TOÁN TÀI SẢN

### Luồng kế toán ERPNext khi mua tài sản

```
Purchase Invoice submitted
    ↓ (debit Expense/Asset account)
tabJournal_Entry created (auto)
    Debit:  Capital Work In Progress (CWIP) Account
    Credit: Accounts Payable

Payment Entry submitted
    Debit:  Accounts Payable
    Credit: Bank Account

Asset submitted + depreciation enabled
    ↓ (monthly)
tabJournal_Entry (depreciation)
    Debit:  Depreciation Expense Account
    Credit: Accumulated Depreciation Account

Asset scrapped/sold
    ↓
tabJournal_Entry (disposal)
    Debit:  Accumulated Depreciation + Disposal Account
    Credit: Asset Account
```

### AssetCore không chạm vào kế toán

Theo RULE-F01 và kiến trúc hệ thống:
- AssetCore **không tạo Journal Entry**
- AssetCore **không override kế toán ERPNext**
- AssetCore chỉ **đọc** financial data khi cần hiển thị (book value, purchase amount)
- Mọi giao dịch tài chính vẫn qua ERPNext Accounts module

---

## 9. Toàn bộ sơ đồ kế thừa AssetCore ← ERPNext

```
╔══════════════════════════════════════════════════════════════════════╗
║          ERPNext (NỀN TẢNG — GIỮ NGUYÊN HOÀN TOÀN)                 ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  SETUP         STOCK           BUYING          ACCOUNTS   ASSETS    ║
║  ────────      ──────────      ──────────      ────────   ────────  ║
║  Company       Item            Supplier        Purch.Inv  Asset     ║
║  Department    Serial No       Supplier Group  Pay.Entry  Asset Cat ║
║  Employee      Warehouse       Purchase Order  Journal    Location  ║
║  User          Stock Entry     Purch.Receipt   Entry      Asset Mvmt║
║  Role          Batch           Supp.Quotation  Cost Ctr   Asset Rep ║
║                Item Supplier   RFQ             Account    Asset Mnt ║
╚══════════════════════════════════════════════════════════════════════╝
         │               │              │              │
         │ Link/Reference│              │              │
         ▼               ▼              ▼              ▼
╔══════════════════════════════════════════════════════════════════════╗
║         AssetCore EXTENSION LAYER (EXTEND — KHÔNG MODIFY)           ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  MASTER DATA                                                         ║
║  ─────────────────────────────────────────────────────────────────  ║
║  IMM Device Model        ←─── link ── Item (is_fixed_asset=1)       ║
║  IMM Vendor Profile      ←─── link ── Supplier                      ║
║  IMM Location Ext        ←─── link ── Location                      ║
║  IMM SLA Policy          (standalone)                                ║
║  IMM Audit Trail         ←─── link ── Asset                         ║
║  IMM CAPA Record         ←─── link ── Asset                         ║
║                                                                      ║
║  DEPLOYMENT (Wave 1 ✅)                                              ║
║  ─────────────────────────────────────────────────────────────────  ║
║  IMM Commissioning Rec   ←─── link ── Asset, Supplier, PO           ║
║  IMM Asset Document      ←─── link ── Asset                         ║
║  IMM Document Request    ←─── link ── Asset, IMM Asset Document      ║
║  IMM Expiry Alert Log    ←─── link ── IMM Asset Document             ║
║  IMM QA Non-Conformance  ←─── link ── IMM Commissioning Record       ║
║                                                                      ║
║  OPERATIONS (Wave 1 ❌ chưa code)                                    ║
║  ─────────────────────────────────────────────────────────────────  ║
║  IMM PM Schedule         ←─── link ── Asset, IMM Device Model       ║
║  IMM PM Work Order       ←─── link ── Asset, IMM PM Schedule         ║
║  IMM CM Work Order       ←─── extend ─ Asset Repair (ERPNext)        ║
║  IMM Calibration Schedule←─── link ── Asset, IMM Device Model       ║
║  IMM Asset Calibration   ←─── link ── Asset, IMM Cal Schedule       ║
║  IMM Incident Report     ←─── link ── Asset, IMM SLA Policy         ║
║  IMM RCA Record          ←─── link ── Asset, IMM Incident Report     ║
║                                                                      ║
║  Asset (16 Custom Fields) ← bench migrate custom fields             ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 10. Mapping dữ liệu theo nghiệp vụ bệnh viện

### Kịch bản 1: Mua máy thở mới

| Bước | Module | DocType | Dữ liệu lưu |
|---|---|---|---|
| 1. Lập PR mua | Buying | Purchase Order | Supplier=Drager, Item=MAQ-001 (Máy thở Savina), qty=2, price=450M |
| 2. Nhận máy | Stock | Purchase Receipt | GRN-2026-001, ref→PO, qty nhận=2 |
| 3. Tạo Asset | Assets | **Asset** | ACC-ASS-2026-0001, item=MAQ-001, purchase=450M, status=Draft |
| 4. Lắp đặt | AssetCore | IMM Commissioning Record | IMM04-26-05-00001, po_ref=PO-001, vendor=Drager, serial=SV-12345 |
| 5. Kiểm tra | AssetCore | IMM Commissioning Checklist | 32 hạng mục pass/fail |
| 6. Release | AssetCore | IMM Commissioning Record | status=Clinical_Release, final_asset=ACC-ASS-2026-0001 |
| 7. PM Schedule | AssetCore | IMM PM Schedule | PMS-2026-00001, asset=ACC-ASS-2026-0001, interval=90 ngày |
| 8. Cal Schedule | AssetCore | IMM Calibration Schedule | CAL-SCH-2026-00001, asset=..., interval=365 ngày |

### Kịch bản 2: Máy siêu âm hỏng lúc 3 giờ sáng

| Bước | Module | DocType | Dữ liệu lưu |
|---|---|---|---|
| 1. Báo hỏng | AssetCore | IMM Incident Report | IR-2026-00045, asset=ACC-ASS-2026-0012, severity=P1, reporter=KD.Ngoai |
| 2. SLA tính | AssetCore | IMM SLA Policy | response=30 phút, resolution=4 giờ |
| 3. Tạo CM WO | AssetCore | IMM CM Work Order | WO-CM-2026-00012, fault_code=EC-001 |
| 4. Ghi parts | AssetCore | IMM Spare Parts Used | part=PROBE-GE-001, qty=1, cost=15M |
| 5. Complete | AssetCore | IMM CM Work Order | status=Completed, mttr_hours=3.5 |
| 6. SLA log | AssetCore | IMM SLA Compliance Log | sla_met=1, actual=3.5h, target=4h |
| 7. Update Asset | ERPNext | **Asset** | custom_imm_lifecycle_status=Active |

---

## 11. Quy tắc nhất quán dữ liệu

### 11.1 Single Source of Truth

| Dữ liệu | Nguồn duy nhất | AssetCore làm gì |
|---|---|---|
| Thông tin NCC (tên, địa chỉ, email) | `tabSupplier` | Chỉ đọc, link về |
| Thông tin PO (số PO, giá, ngày) | `tabPurchase_Order` | Chỉ đọc, link về |
| Giá trị tài sản (book value) | `tabAsset` | Chỉ đọc |
| Số serial vật lý | `tabSerial_No` (ERPNext) | Link về + duplicate vào `custom_imm_manufacturer_sn` cho search |
| Phòng ban | `tabDepartment` | Dùng trực tiếp |
| Vị trí | `tabLocation` | Dùng trực tiếp + IMM Location Ext mở rộng |
| Tài khoản người dùng | `tabUser` | Dùng trực tiếp, không duplicate |

### 11.2 Không Duplicate Data

```python
# SAI — duplicate dữ liệu NCC vào AssetCore DocType
class IMMCommissioningRecord(Document):
    vendor_name = "Drager Vietnam"      # ❌ đã có trong tabSupplier
    vendor_address = "Hà Nội"           # ❌ đã có trong tabAddress
    vendor_tax_id = "123456789"         # ❌ đã có trong tabSupplier

# ĐÚNG — chỉ link, fetch khi cần hiển thị
class IMMCommissioningRecord(Document):
    vendor = "Drager-Vietnam"           # ✅ Link → Supplier
    # Frappe fetch supplier_name từ tabSupplier khi load form
```

### 11.3 Khi nào dùng Custom Field vs DocType mới

| Trường hợp | Giải pháp |
|---|---|
| Thêm 1-3 field vào ERPNext core DocType | **Custom Field** (không tạo DocType) |
| Cần workflow riêng, submittable | **DocType mới** link về core |
| Cần child table với nhiều rows | **Child Table DocType** mới |
| Cần lưu lịch sử (immutable log) | **DocType mới** với in_list_view, không có Delete permission |
| Mở rộng thông tin 1:1 với core DocType | **DocType mới** có Link field về core (như IMM Vendor Profile → Supplier) |

---

## 12. Checklist triển khai — Thứ tự setup ERPNext cho AssetCore

```
Phase 1: ERPNext Base Setup
  □ Tạo Company: "Bệnh viện Nhi Đồng 1"
  □ Import Department tree (Khối Lâm sàng → Khoa)
  □ Import Location tree (Tòa nhà → Tầng → Phòng)
  □ Tạo Asset Category:
      □ Thiết bị hình ảnh (Imaging)
      □ Thiết bị theo dõi (Monitoring)
      □ Thiết bị thở (Respiratory)
      □ Thiết bị phòng mổ (OR Equipment)
      □ Thiết bị xét nghiệm (Lab Equipment)
      □ Thiết bị đo lường (Measuring/Calibration)
  □ Tạo Supplier cho từng NCC/hãng
  □ Tạo Item với is_fixed_asset=1 cho từng loại thiết bị

Phase 2: AssetCore Custom Fields
  □ bench migrate (add 16 custom fields to tabAsset)
  □ Verify fields xuất hiện trong Asset form

Phase 3: AssetCore Master Data
  □ Tạo IMM Device Model cho từng loại TBYT
  □ Tạo IMM Vendor Profile cho từng NCC
  □ Tạo IMM Location Ext cho các khoa
  □ Tạo IMM SLA Policy (P1/P2/P3/P4)

Phase 4: Import tài sản hiện có
  □ Tạo Asset với is_existing_asset=1
  □ Điền custom fields (device model, class, serial, ...)
  □ Set custom_imm_lifecycle_status = Active
  □ Import IMM Asset Document (hồ sơ hiện có)

Phase 5: Activate Operations
  □ Tạo IMM PM Schedule cho toàn bộ tài sản Active
  □ Tạo IMM Calibration Schedule cho measuring devices
  □ Activate daily scheduler jobs
```

---

## 13. Database Query Examples

Truy vấn dữ liệu đúng cách trong AssetCore (frappe.db, không dùng raw SQL):

```python
# Lấy danh sách tài sản theo khoa
assets = frappe.get_list(
    "Asset",
    filters={
        "custom_imm_dept": "Khoa HSCC",
        "custom_imm_lifecycle_status": "Active",
        "docstatus": 1
    },
    fields=["name", "asset_name", "custom_imm_device_model",
            "custom_imm_risk_class", "custom_imm_next_pm_date"]
)

# Lấy thông tin NCC từ PO
po = frappe.get_doc("Purchase Order", po_name)
supplier_name = po.supplier_name  # Frappe tự fetch từ tabSupplier

# Kiểm tra tài sản có hồ sơ đầy đủ không
docs = frappe.get_list(
    "Asset Document",  # IMM Asset Document
    filters={"asset_ref": asset_name, "workflow_state": "Active"},
    fields=["doc_category", "doc_type_detail", "expiry_date"]
)

# Tạo Audit Trail (append-only)
frappe.get_doc({
    "doctype": "IMM Audit Trail",
    "asset": asset_name,
    "source_doctype": "IMM PM Work Order",
    "source_name": wo_name,
    "event_type": "State Change",
    "from_status": "In Progress",
    "to_status": "Completed",
    "actor": frappe.session.user,
    "event_timestamp": now_datetime()
}).insert(ignore_permissions=True)
```

---

## 14. Kết luận — AssetCore là gì so với ERPNext?

```
ERPNext thuần                     AssetCore = ERPNext + Extension
═══════════════                   ═══════════════════════════════
• Quản lý tài chính               • Quản lý vòng đời vận hành
• Khấu hao tài sản                • PM / CM / Calibration / Incident
• Mua sắm (PO/PR/PI)             • Commissioning & Acceptance
• Kho vật tư                      • Document Control (NĐ98)
• Kế toán bút toán                • QMS: CAPA, RCA, Audit Trail
• Phân quyền cơ bản              • SLA, MTTR, KPI Dashboard
• Không có workflow HTM           • Full HTM workflow (WHO)
• Không có regulatory compliance  • ISO 13485, NĐ98, WHO HTM

CHIẾN LƯỢC: Đóng gói ERPNext + AssetCore thành 1 Docker image
             → 1 URL, 1 login, 1 database, UI nhất quán
             → AssetCore app là Frappe app mount lên ERPNext
             → End user không nhìn thấy "ERPNext" — chỉ thấy AssetCore
```
