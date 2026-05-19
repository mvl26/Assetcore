# IMM-00 — Phát hành (User Guide + Release Notes + Traceability)

| Mục | Giá trị |
|---|---|
| Module | **IMM-00 — Master / Cross-cutting Foundation** |
| Phiên bản | 4.2.0 |
| Ngày phát hành | 2026-05-14 |
| Owner | PM + BA + Tech Writer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [08 Deployment](./08_Deployment.md) · [Module Overview](./IMM-00_Module_Overview.md) |

> **Vai trò đặc biệt:** IMM-00 là module nền tảng — không phải module nghiệp vụ độc lập. User Guide tập trung vào **System Admin** (thiết lập hệ thống) và **Module Owner** (quản trị dữ liệu master). Người dùng cuối tham khảo hướng dẫn của module cụ thể (IMM-01 → IMM-17).

---

# Phần I — Hướng Dẫn Sử Dụng (Dành cho System Admin)

> **Ngôn ngữ**: Tiếng Việt 100%. Không dùng mã kỹ thuật cho người dùng cuối.

## I.1. Giới Thiệu

Module **Nền tảng (IMM-00)** là lớp hạ tầng của toàn hệ thống AssetCore. Module này không có giao diện nghiệp vụ trực tiếp cho người dùng cuối — thay vào đó, nó cung cấp:

- **Dữ liệu gốc (Master Data):** Thiết bị, Nhà cung cấp, Địa điểm, Khoa phòng, Danh mục thiết bị
- **Hạ tầng quản trị:** Chính sách SLA, Vết kiểm toán (Audit Trail), Hồ sơ CAPA, Sự kiện vòng đời thiết bị
- **Phân quyền hệ thống:** 8 vai trò xuyên suốt tất cả module
- **Kho vật tư (v4):** Kho hàng, Phụ tùng, Tồn kho, Phiếu xuất nhập

**System Admin cần thiết lập IMM-00 trước khi bàn giao cho bất kỳ module nào.**

**Trước khi bắt đầu, bạn cần:**
- Tài khoản AssetCore với vai trò **IMM System Admin**
- Trình duyệt Chrome hoặc Edge phiên bản mới nhất
- Quyền truy cập SSH vào máy chủ (cho cài đặt ban đầu)
- Đã hoàn thành cài đặt theo `08_Deployment.md`

---

## I.2. Nhận Biết Màn Hình Admin

Màn hình Admin gồm 3 khu vực:

```
┌─────────────────────────────────────────────────────┐
│  ① Thanh trên (Topbar) — Tìm kiếm, thông báo       │
├──────────┬──────────────────────────────────────────┤
│          │  ③ Vùng nội dung chính                   │
│ ②       │  (Danh sách / Form / Dashboard / Config)  │
│ Sidebar  │                                           │
│ (menu)   │                                           │
└──────────┴──────────────────────────────────────────┘
```

- **① Topbar**: Tìm kiếm nhanh (`Ctrl+K`), chuông thông báo hệ thống, thông tin tài khoản Admin.
- **② Sidebar**: Vào **"Cài đặt"** hoặc **"AssetCore Settings"** để thấy menu Admin.
- **③ Vùng chính**: Form nhập liệu master data, danh sách thiết bị, cấu hình SLA.

---

## I.3. Các Vai Trò Quản Trị IMM-00

| Vai trò | Nhiệm vụ trong IMM-00 |
|---|---|
| **IMM System Admin** | Cài đặt ban đầu, phân quyền, load fixture, cấu hình scheduler, thiết lập email |
| **IMM Department Head** | Duyệt yêu cầu master data mới (Địa điểm mới, Danh mục mới) |
| **IMM Operations Manager** | Cấu hình SLA Policy, theo dõi KPI tổng hợp toàn hệ thống |
| **IMM Document Officer** | Quản lý tài liệu QMS, cấu hình audit retention |
| **IMM QA Officer** | Mở và theo dõi CAPA, xác minh audit chain |
| **IMM Storekeeper** | Nhập liệu kho, tồn kho ban đầu, quản lý phụ tùng |

---

## I.4. Quy Trình Thiết Lập Ban Đầu

```
① Cài đặt hệ thống (Server Admin)
      │  bench get-app / bench install-app assetcore
      ▼
② Load Fixtures & Roles
      │  bench --site [site] migrate
      │  bench --site [site] execute assetcore.setup.load_fixtures
      ▼
③ Nhập Master Data — Địa điểm & Khoa phòng
      │  (IMM System Admin làm trên giao diện)
      ▼
④ Nhập Master Data — Nhà cung cấp & Danh mục thiết bị
      │
      ▼
⑤ Nhập Master Data — Thiết bị (AC Asset)
      │
      ▼
⑥ Cấu hình Chính sách SLA
      │
      ▼
⑦ Phân quyền người dùng
      │
      ▼
⑧ Kiểm tra Smoke Test (13 điểm — xem 08_Deployment.md §V.1)
      │
      ▼
⑨ Bàn giao cho các module nghiệp vụ (IMM-01 → IMM-17)
```

---

## I.5. Thao Tác Chi Tiết Theo Vai Trò

### a. System Admin — Thiết lập ban đầu

#### Bước 1: Nhập Địa điểm (AC Location)

**Khi nào làm?** Trước khi nhập bất kỳ thiết bị nào.

**Các bước:**
1. Vào **AssetCore → Master Data → Địa điểm**
2. Bấm **"Tạo mới"**
3. Điền các trường bắt buộc:
   - **Mã địa điểm** (ví dụ: `LOC-ICU-01`) — không thay đổi được sau khi lưu
   - **Tên địa điểm** (ví dụ: `Phòng ICU - Tầng 3`)
   - **Loại địa điểm**: Phòng / Tầng / Tòa nhà / Khu vực ngoài trời
   - **Tòa nhà** (tùy chọn)
4. Bấm **"Lưu"**

> **Lưu ý:** Tạo Địa điểm theo thứ tự từ tổng quát đến cụ thể (Tòa nhà → Tầng → Phòng). Hệ thống hỗ trợ cấu trúc cây (tree).

---

#### Bước 2: Nhập Khoa phòng (AC Department)

1. Vào **AssetCore → Master Data → Khoa phòng**
2. Bấm **"Tạo mới"**
3. Điền:
   - **Mã khoa** (ví dụ: `DEPT-ICU`)
   - **Tên khoa** (ví dụ: `Khoa Hồi sức tích cực`)
   - **Địa điểm mặc định** (chọn từ danh sách đã tạo ở Bước 1)
   - **Trưởng khoa** (chọn tài khoản người dùng)
4. Bấm **"Lưu"**

---

#### Bước 3: Nhập Nhà cung cấp (AC Supplier)

1. Vào **AssetCore → Master Data → Nhà cung cấp**
2. Bấm **"Tạo mới"**
3. Điền:
   - **Mã nhà cung cấp** (ví dụ: `SUP-PHILIPS-01`)
   - **Tên công ty**
   - **Loại**: Nhà sản xuất / Đại lý / Đơn vị dịch vụ
   - **Quốc gia**, **SĐT**, **Email liên hệ**
   - **Ngày hết hạn hợp đồng** (nếu có)
4. Bấm **"Lưu"**

---

#### Bước 4: Nhập Danh mục thiết bị (AC Asset Category)

1. Vào **AssetCore → Master Data → Danh mục thiết bị**
2. Bấm **"Tạo mới"**
3. Điền:
   - **Mã danh mục** (ví dụ: `CAT-MONITOR`)
   - **Tên danh mục** (ví dụ: `Màn hình theo dõi bệnh nhân`)
   - **Lớp rủi ro**: Class I / Class II / Class III (theo NĐ 98/2021)
   - **Chu kỳ PM mặc định** (ngày — ví dụ: 180)
   - **Chu kỳ hiệu chuẩn** (ngày — nếu áp dụng)
4. Bấm **"Lưu"**

---

#### Bước 5: Nhập Thiết bị (AC Asset)

> **Quan trọng:** Đây là dữ liệu cốt lõi nhất. Mỗi thiết bị vật lý = 1 bản ghi AC Asset với số serial riêng.

1. Vào **AssetCore → Thiết bị → Danh sách thiết bị**
2. Bấm **"Tạo mới"**
3. Điền các trường bắt buộc:
   - **Tên thiết bị** (ví dụ: `Monitor-ICU-05`)
   - **Danh mục** (chọn từ Bước 4)
   - **Số serial** — bắt buộc, unique toàn hệ thống
   - **Nhà sản xuất / Nhà cung cấp**
   - **Địa điểm hiện tại** (chọn từ Bước 1)
   - **Khoa phòng phụ trách** (chọn từ Bước 2)
   - **Trạng thái**: Active / Under Maintenance / Out of Service / Retired / In Storage
4. Điền các trường khuyến nghị:
   - **Model thiết bị** (GMDN code nếu có)
   - **Ngày mua**, **Ngày lắp đặt**
   - **Giá trị tài sản** (VND)
5. Bấm **"Lưu"**

> **Nhập hàng loạt:** Dùng tính năng **Import** (Data Import Tool) với file CSV. Template tải tại `AssetCore → Tools → Import → AC Asset`.

---

### b. Operations Manager — Cấu hình SLA

**Khi nào làm?** Sau khi đã có đầy đủ Danh mục thiết bị. SLA phải được cấu hình trước khi các module PM (IMM-08), Sửa chữa (IMM-09), Hiệu chuẩn (IMM-11) đi vào hoạt động.

**Cấu hình SLA mặc định đã có (từ fixture):**

| Loại thiết bị | Mức ưu tiên | SLA (giờ) |
|---|---|---|
| Class III | Khẩn cấp | 4 |
| Class III | Cao | 8 |
| Class III | Trung bình | 24 |
| Class II | Khẩn cấp | 8 |
| Class II | Cao | 24 |
| Class II | Trung bình | 72 |
| Class I | Bất kỳ | 120 |

**Tùy chỉnh SLA:**
1. Vào **AssetCore → Cấu hình → Chính sách SLA**
2. Mở chính sách cần chỉnh hoặc tạo mới
3. Chọn **Danh mục thiết bị** (hoặc để trống = áp dụng chung)
4. Điền thời gian (giờ) cho từng mức ưu tiên
5. Bấm **"Kích hoạt"** → chính sách có hiệu lực ngay

---

### c. System Admin — Phân quyền người dùng

**Gán vai trò cho nhân viên:**
1. Vào **Settings → User Management → Users**
2. Tìm tài khoản người dùng
3. Vào tab **Roles**
4. Tích chọn vai trò phù hợp từ danh sách 8 vai trò IMM:
   - `IMM System Admin`
   - `IMM Department Head`
   - `IMM Operations Manager`
   - `IMM Workshop Lead`
   - `IMM Technician`
   - `IMM Document Officer`
   - `IMM Storekeeper`
   - `IMM QA Officer`
5. Bấm **"Lưu"**

> **Nguyên tắc phân quyền tối thiểu (least privilege):** Chỉ gán vai trò cần thiết. Kỹ thuật viên không cần `IMM System Admin`. Trưởng xưởng không cần `IMM QA Officer`.

---

### d. Storekeeper — Thiết lập Kho vật tư (v4)

**Thiết lập Kho (AC Warehouse):**
1. Vào **AssetCore → Kho vật tư → Kho hàng**
2. Bấm **"Tạo mới"** → điền Mã kho, Tên kho, Địa điểm
3. Lưu

**Nhập Phụ tùng ban đầu (AC Spare Part):**
1. Vào **AssetCore → Kho vật tư → Phụ tùng**
2. Tạo từng phụ tùng: Mã SKU, Tên, Đơn vị tính, Nhà cung cấp, Min stock
3. Sau khi tạo phụ tùng → vào **Tồn kho** → thêm tồn kho ban đầu với lý do `Nhập kho ban đầu`

---

### e. QA Officer — Theo dõi Audit Trail & CAPA

**Xem Vết kiểm toán (IMM Audit Trail):**
1. Vào **AssetCore → Quản trị → Vết kiểm toán**
2. Danh sách chỉ đọc — không thể xóa hoặc chỉnh sửa bất kỳ bản ghi nào
3. Lọc theo: Thiết bị / Loại sự kiện / Khoảng thời gian / Actor
4. Bấm **"Xác minh chuỗi hash"** để kiểm tra tính toàn vẹn

**Mở CAPA (IMM CAPA Record):**
1. Vào **AssetCore → Quản trị → CAPA**
2. Bấm **"Tạo mới"** → điền Nguyên nhân gốc rễ, Hành động khắc phục, Deadline
3. Gán Owner thực hiện → theo dõi tiến độ từ Dashboard CAPA

---

## I.6. Bảng Điều Khiển Tổng Hợp (Foundation Dashboard)

Vào **AssetCore → Dashboard** để xem tổng quan toàn hệ thống:

| KPI | Ý nghĩa | Trend tốt |
|---|---|---|
| **Tổng thiết bị Active** | Thiết bị đang vận hành | Ổn định |
| **CAPA đang mở / quá hạn** | Số hồ sơ CAPA chưa đóng | ↓ Giảm |
| **Thiết bị chưa có SLA** | Cảnh báo thiếu cấu hình | = 0 |
| **Audit Trail — Ghi nhận hôm nay** | Hoạt động hệ thống | Bình thường |
| **Hợp đồng sắp hết hạn (30 ngày)** | Cảnh báo gia hạn nhà cung cấp | = 0 |
| **Tồn kho dưới mức tối thiểu** | Phụ tùng thiếu | = 0 |

---

## I.7. Câu Hỏi Thường Gặp

**Q: Tôi không thấy menu "AssetCore" sau khi đăng nhập?**
> A: Tài khoản của bạn chưa được gán vai trò IMM. Liên hệ System Admin để được cấp quyền (xem §I.5.c).

**Q: Tôi tạo AC Asset nhưng không chọn được Địa điểm?**
> A: Cần tạo AC Location trước (xem §I.5.a Bước 1). Địa điểm là dữ liệu bắt buộc trước thiết bị.

**Q: Hệ thống báo "Serial number đã tồn tại"?**
> A: Số serial phải unique toàn hệ thống. Kiểm tra lại — có thể thiết bị đã được nhập trước đó với tên khác.

**Q: Cấu hình SLA có hiệu lực ngay không?**
> A: Có — SLA mới áp dụng cho Work Order tạo sau thời điểm kích hoạt. Work Order đang mở giữ SLA cũ.

**Q: Làm sao xem audit trail của 1 thiết bị cụ thể?**
> A: Mở chi tiết AC Asset → tab **Lịch sử sự kiện** → toàn bộ vết kiểm toán của thiết bị đó.

**Q: CAPA tự động tạo khi nào?**
> A: Hệ thống gợi ý CAPA (không tự tạo) khi: (1) thiết bị hỏng ≥ 2 lần/30 ngày, (2) SLA bị vi phạm liên tiếp. QA Officer quyết định có mở CAPA không.

**Q: Scheduler jobs có chạy tự động không sau khi cài đặt?**
> A: Có, nếu đã cấu hình đúng theo `08_Deployment.md §II.5`. Kiểm tra bằng `bench --site [site] list-scheduled-jobs`.

**Q: Dữ liệu Audit Trail lưu bao lâu?**
> A: Tối thiểu 7 năm theo NĐ 98/2021 §15.2 và chính sách kiểm toán AssetCore. Không được xóa thủ công.

---

## I.8. Phím Tắt & Tham Chiếu Nhanh

| Phím | Chức năng |
|---|---|
| `Ctrl+K` | Tìm kiếm nhanh toàn hệ thống |
| `Esc` | Đóng popup / hủy thao tác |
| `Tab` | Chuyển trường tiếp theo trong form |
| `Ctrl+S` | Lưu bản ghi |

**Cheat sheet trạng thái AC Asset:**

| Trạng thái | Ý nghĩa |
|---|---|
| Active | Thiết bị đang vận hành bình thường |
| Under Maintenance | Đang bảo trì hoặc sửa chữa |
| Out of Service | Tạm ngưng sử dụng |
| In Storage | Đang lưu kho, chưa triển khai |
| Retired | Đã thanh lý / hủy bỏ |

**Cheat sheet trạng thái CAPA:**

| Trạng thái | Ý nghĩa |
|---|---|
| Open | Mới mở, chờ phân công |
| In Progress | Đang thực hiện hành động |
| Pending Verification | Chờ QA xác minh hiệu quả |
| Closed | Hoàn tất, đã xác minh |
| Overdue | Quá hạn deadline |

---

## I.9. Liên Hệ Hỗ Trợ

| Vấn đề | Liên hệ |
|---|---|
| Không đăng nhập được, quên mật khẩu | IT Helpdesk: ext. 1234 hoặc it@hospital.vn |
| Lỗi hệ thống, cài đặt không thành công | DevOps AssetCore: devops@assetcore.vn |
| Câu hỏi nghiệp vụ, quy trình | BA Lead AssetCore: ba@assetcore.vn |
| Khẩn cấp (hệ thống không khởi động) | Hotline: 0903.xxx.xxx (24/7) |

---

## I.10. Lịch Sử Cập Nhật Tài Liệu

| Phiên bản | Ngày | Thay đổi | Owner |
|---|---|---|---|
| 4.2.0 | 2026-05-14 | Wave 2 GA — 20 IMM roles, Asset Finance Hub, fixture sync hardening; doc deep-sync vs codebase | BA Lead |
| 4.0.0 | 2026-05-08 | Phát hành lần đầu tài liệu template-chuẩn IMM-00 v4 — thêm Inventory sub-domain | BA Lead |
| 3.2.0 | 2026-03-01 | Bổ sung GMDN Status Management (FR-00-38→42), Inventory DocTypes v3.2 | BA Lead |
| 3.0.0 | 2025-12-01 | Tái cấu trúc — tách AssetCore khỏi ERPNext, toàn bộ DocType prefix AC/IMM | Tech Lead |

---

# Phần II — Release Notes

## II.1. Tóm Tắt

Phiên bản 4.0.0 (2026-05-08) hoàn thiện module nền tảng **IMM-00 Foundation** với bổ sung sub-domain Kho vật tư (Inventory v4) và GMDN Status Management. Đây là lớp hạ tầng bắt buộc cho toàn bộ 17 module nghiệp vụ IMM. Downtime dự kiến 60-90 phút trong cửa sổ bảo trì đêm khi nâng cấp từ v3.

## II.2. Tính Năng Mới (v4.0.0)

### Inventory Sub-domain — Kho vật tư (IMM System Admin + Storekeeper)

Quản lý toàn bộ kho phụ tùng vật tư y tế với 5 DocType mới, tích hợp kiểm soát tồn kho tự động.

- **AC Warehouse**: Quản lý nhiều kho vật lý, hỗ trợ mô hình multi-warehouse
- **AC Spare Part**: Danh mục phụ tùng với mức tồn kho tối thiểu (min_stock)
- **AC Spare Part Stock**: Tồn kho thực tế theo từng kho, cập nhật real-time
- **AC Stock Movement**: Ghi nhận mọi xuất/nhập/chuyển kho với audit trail
- Cảnh báo tự động khi tồn kho dưới min_stock (BR-INV-05)
- Cấm xuất kho vượt tồn kho (BR-INV-04)

[→ Hướng dẫn: §I.5.d]

### GMDN Status Management (IMM System Admin + Technician)

Quản lý trạng thái GMDN (Global Medical Device Nomenclature) trên thiết bị thông qua QR scan.

- QR scan kích hoạt / vô hiệu hóa thiết bị tức thời (FR-00-38→42)
- Trạng thái tự động ghi vào Asset Lifecycle Event
- Cảnh báo khi thiết bị active chưa có GMDN code (BR-00-11)
- Bắt buộc ghi lý do khi vô hiệu hóa qua QR (BR-00-12)

[→ Hướng dẫn: Xem `IMM-00_Functional_Specs.md §FR-00-38→42`]

## II.3. Cải Tiến (v4.0.0)

| Mô tả | Tác động |
|---|---|
| `check_capa_overdue` scheduler thêm gửi email cảnh báo | CAPA không bị bỏ sót khi quá hạn |
| `rollup_asset_kpi` chạy daily thay vì weekly | Dashboard KPI cập nhật hàng ngày |
| Permission query IMM Technician được index `responsible_technician` | Query danh sách phiếu nhanh hơn ~5× |
| Audit Trail hash chain verify — endpoint mới | QA có thể tự xác minh tính toàn vẹn |

## II.4. Lịch Sử Release

| Version | Ngày | Nội dung tóm tắt |
|---|---|---|
| 4.2.0 | 2026-05-14 | **Wave 2 GA** — IMM-01/02/03 (Needs/Spec/Procurement), IMM-06 (Training), IMM-15 (Spare Parts), IMM-16 (Compliance); 20 IMM roles + has_role fixtures; Asset Finance Hub (Depreciation list/stats); FE restructure FE/BE folders |
| 4.1.0 | 2026-05-11 | Sprint 6 DoD — 3-tier BE compliance, FE store + views wired, scheduler insurance + service contract |
| 4.0.0 | 2026-05-08 | Inventory sub-domain, GMDN QR scan, tài liệu template-chuẩn đầy đủ |
| 3.2.0 | 2026-03-01 | GMDN status field, Inventory DocTypes stub |
| 3.0.0 | 2025-12-01 | Tách khỏi ERPNext — toàn bộ DocType prefix AC/IMM — breaking migration |
| 2.x | 2025-06-01 | ERPNext-based — deprecated |

## II.4.1. Wave 2 Release Notes — v4.2.0 (2026-05-14)

**Phạm vi ảnh hưởng IMM-00:** Foundation cần phục vụ thêm 6 module Wave 2 với thay đổi schema và services.

### Tính năng IMM-00 đóng góp cho Wave 2

| Hạng mục | Commit(s) | Mô tả |
|---|---|---|
| Role expansion 8 → 20 | `5b4158e` `820e3fe` | Bổ sung Wave 2 roles (Planning Officer, Finance Officer, HTM Engineer, Procurement Officer, Risk Officer, Board Approver, Training Officer, Deputy Dept Head, Biomed Technician, Clinical User, Auditor, Vendor Engineer). Fixture chuyển từ `imm_roles.json` → `role.json` + `has_role.json` |
| Fixture sync hardening | `227e786` | Sửa warning "Skipping fixture syncing" lúc `bench migrate` |
| FE/BE folder restructure | `33a9668` | Refactor `frontend/src/api/`, `stores/`, `views/`; tách module IMM-XX rõ ràng |
| Launcher + UI optimization | `820e3fe` | Sidebar role-aware; launcher cards theo module |
| Depreciation Asset Finance Hub | (Wave 2 BE) | Thêm `list_assets_depreciation`, `get_depreciation_stats`, `compute_all_depreciation`, `bulk_regenerate_schedule_by_category` — 9 endpoints depreciation tổng |
| Service Contract + Insurance scheduler | (v4.1) | `check_insurance_expiry`, `check_service_contract_expiry` daily; total 5 daily IMM-00 jobs |
| `rollup_asset_kpi` chuyển sang monthly | (v4.1) | Hooks `monthly` thay vì `daily` |
| FE fullname + list view polish | `fce3655` | Hiển thị user fullname; cải thiện list view một số module |
| npm build + role permission fixes | `65c5dbc` `bcddfac` | Resolve npm build errors, frontend env trong frappe bench |

### Breaking changes (Wave 2)

| Thay đổi | Migration | Tác động |
|---|---|---|
| Fixture role JSON đổi tên | `bench migrate` tự áp `role.json` + `has_role.json` | Site cũ vẫn giữ role cũ — không cần manual cleanup |
| `scheduler_events["daily"]` thêm 2 job (insurance, service contract) | Tự áp khi update app | Khối lượng cron tăng nhẹ |
| `scheduler_events["monthly"]` mới (rollup_asset_kpi, run_due_depreciation) | Tự áp | KPI dashboard cập nhật chu kỳ tháng thay vì ngày |

### Khả năng tương thích

| Wave 1 module (IMM-04/05/08/09/11/12) | Tương thích ngược | Không cần thay đổi code |
| AC Asset registry | Schema breaking ở v3.1/008: DROP field trạng thái GMDN cũ (lọc theo `gmdn_code`) | depreciation fields (v4.0); ref [analysis §6](../res/gmdn-asset-category-analysis.md) |
| API envelope `_ok/_err` | Không đổi | Wave 2 modules tuân thủ |

### Known issues v4.2.0

| Vấn đề | Workaround | Fix |
|---|---|---|
| Một số PM Template endpoints có 2 implementations (imm00 + imm08) — FE route sang imm08 | FE đã pin sang imm08; BE giữ imm00 cho backward compat | v4.3 hợp nhất |
| FE coverage IMM-00 vẫn partial (Asset/Audit/CAPA detail forms chưa build hết) | Dùng Frappe Desk fallback | Cuốn chiếu theo Wave 3 |

## II.5. Sửa Lỗi

| Mã issue | Mô tả | Severity |
|---|---|---|
| AC-BUG-042 | `transition_asset_status` không cập nhật `last_status_change` khi status = Active → Active | Medium |
| AC-BUG-039 | `check_capa_overdue` không gửi email nếu owner không có địa chỉ email | Low |
| AC-BUG-035 | Audit Trail hash chain có thể bị phá vỡ nếu DB collation khác utf8mb4 | High |

## II.6. Thay Đổi Breaking (v4.0.0)

| Thay đổi | Migration |
|---|---|
| `AC Spare Part` thay thế `Item` (ERPNext) cho phụ tùng y tế | Patch `v4_0/001_add_inventory_tables` chạy tự động |
| Response envelope của imm00 API: `{"message": {}}` → `{"success": true, "data": {}}` | Update client API nếu integration từ bên ngoài |

**Migration tự động:** Chạy `bench migrate` sẽ áp dụng patch v4_0 tự động.

## II.7. Deprecations

| Thứ gì | Phiên bản bỏ | Thay thế |
|---|---|---|
| ERPNext `Item` doctype cho phụ tùng y tế | v4.0.0 | `AC Spare Part` |
| `{"message": {...}}` envelope trong API IMM-00 | v4.0.0 | `{"success": true, "data": {...}}` |

## II.8. Yêu Cầu Nâng Cấp

**Stack version:** Frappe v15, Python 3.11+, Node 20+, MariaDB 10.6+ (không thay đổi).

**Migration từ v3:** Xem `08_Deployment.md §III` — patch `v4_0/001_add_inventory_tables`.

**Training bắt buộc:** System Admin cần nắm quy trình thiết lập Inventory v4 mới (§I.5.d). Thời lượng ~2 giờ.

## II.9. Downtime / Compatibility / Known Issues

**Downtime:** 60-90 phút khi nâng cấp từ v3 (do migration tạo bảng inventory mới). Nâng cấp trong maintenance window 23:00-02:00.

**Khả năng tương thích:**

| Môi trường | Hỗ trợ |
|---|---|
| Chrome ≥ 120 | ✅ |
| Edge ≥ 120 | ✅ |
| Firefox ≥ 121 | ✅ |
| Safari ≥ 17 | ✅ |
| Mobile (responsive) | ✅ (Admin — khuyến nghị desktop) |

**Known issues:**

| Vấn đề | Workaround | Fix dự kiến |
|---|---|---|
| QR scan GMDN không hoạt động trên Safari iOS < 17.2 | Dùng Chrome trên iPhone hoặc tablet | v4.0.1 |
| `verify_audit_chain` chạy chậm với > 10,000 records | Chạy ngoài giờ cao điểm | v4.1.0 (batch optimize) |
| Inventory report thiếu filter theo nhà cung cấp | Filter thủ công trong danh sách | v4.0.1 |

## II.10. Liên Kết

- User Guide: §I file này
- Module Overview: [IMM-00_Module_Overview.md](./IMM-00_Module_Overview.md)
- Deployment Plan: [08_Deployment.md](./08_Deployment.md)
- Báo lỗi: `support@assetcore.vn` hoặc GitHub Issues

---

# Phần III — Traceability Matrix

## III.1. Cách Dùng

- Mỗi Business Rule / Compliance requirement / User Story có 1 dòng.
- Cell phải trỏ đến artefact cụ thể (file/function/test ID).
- Cập nhật xuyên suốt lifecycle; chốt cột `Released-in` khi release.
- Status: ⬜ Not started · 🟡 In progress · 🟠 Blocked · ✅ Done · ❌ Cancelled

> **Lưu ý IMM-00:** Vì đây là module nền tảng (không phải module nghiệp vụ), Traceability Matrix tập trung vào **Business Rules → DocType/Service/Test** thay vì User Story flow.

---

## III.2. Matrix — Business Rules

| Req ID | Loại | Mô tả ngắn | Doc ref | Design / Code | Test ID | UAT ID | PR | Released in | Status |
|---|---|---|---|---|---|---|---|---|---|
| BR-00-01 | Rule | IMM Device Model — GMDN code unique | Module Overview §7 | `IMM Device Model.gmdn_code` unique constraint | `TC-S-001: test_device_model_gmdn_unique` | S-04 | #imm00-core | v3.0.0 | ✅ |
| BR-00-02 | Rule | AC Asset — serial_number unique | Module Overview §7 | `AC Asset.serial_number` unique index | `TC-S-002: test_asset_serial_unique` | S-04 | #imm00-core | v3.0.0 | ✅ |
| BR-00-03 | Rule | Asset status transition — chỉ được path hợp lệ | Module Overview §7 | `services/imm00.py: transition_asset_status()` state machine | `TC-S-003: test_transition_active_to_maintenance`, `TC-S-003: test_invalid_transition_raises` | S-05 | #imm00-core | v3.0.0 | ✅ |
| BR-00-04 | Rule | IMM Audit Trail — append-only, không xóa/sửa | Module Overview §7 | `IMM Audit Trail` controller `before_save` raise if `not is_new()` | `TC-S-004: test_audit_trail_immutable` | S-07 | #imm00-core | v3.0.0 | ✅ |
| BR-00-05 | Rule | SHA-256 hash chain — mỗi record gắn prev_hash | Module Overview §7 | `services/imm00.py: log_audit_event()` hash computation | `TC-S-005: test_audit_hash_chain_integrity` | S-07 | #imm00-core | v3.0.0 | ✅ |
| BR-00-06 | Rule | CAPA — deadline bắt buộc, trạng thái → Overdue nếu quá hạn | Module Overview §7 | `services/imm00.py: check_capa_overdue()` daily scheduler | `TC-S-006: test_capa_overdue_flag` | S-08 | #imm00-core | v3.0.0 | ✅ |
| BR-00-07 | Rule | SLA Policy — phải có ít nhất 1 active policy | Module Overview §7 | `services/imm00.py: get_applicable_sla()` fallback logic | `TC-S-007: test_sla_lookup_by_category` | S-09 | #imm00-core | v3.0.0 | ✅ |
| BR-00-08 | Rule | Vendor contract expiry — cảnh báo 30 ngày trước | Module Overview §7 | `services/imm00.py: check_vendor_contract_expiry()` daily scheduler | `TC-S-008: test_vendor_expiry_alert` | S-10 | #imm00-core | v3.0.0 | ✅ |
| BR-00-09 | Rule | Asset Lifecycle Event — append-only | Module Overview §7 | `Asset Lifecycle Event` controller `before_save` raise if not new | `TC-S-009: test_lifecycle_event_immutable` | S-05 | #imm00-core | v3.0.0 | ✅ |
| BR-00-10 | Rule | Incident report — phải linked asset | Module Overview §7 | `Incident Report.asset` mandatory field validation | `TC-S-010: test_incident_requires_asset` | S-11 | #imm00-core | v3.0.0 | ✅ |
| BR-00-11 | Rule | Asset Active phải có GMDN code | Module Overview §7 | `services/imm00.py: validate_gmdn_before_active()` | `TC-S-011: test_gmdn_required_for_active` | S-06 | #imm00-core | v3.2.0 | ✅ |
| ~~BR-00-12~~ | Rule | *(Đã loại bỏ 2026-05-19 — trạng thái sử dụng GMDN bỏ; lọc theo `gmdn_code`. Ref [analysis §6](../res/gmdn-asset-category-analysis.md))* | — | — | — | — | #imm00-core | v3.1.0 | ⛔ removed |

---

## III.3. Matrix — Inventory Business Rules (v4)

| Req ID | Loại | Mô tả ngắn | Doc ref | Design / Code | Test ID | UAT ID | PR | Released in | Status |
|---|---|---|---|---|---|---|---|---|---|
| BR-INV-01 | Rule | Stock Movement phải chỉ định warehouse_from (Issue/Transfer) | Inventory Design §BR | `services/inventory.py: validate_movement()` | `TC-INV-001: test_issue_requires_warehouse_from` | S-12 | #imm00-inv | v4.0.0 | ✅ |
| BR-INV-02 | Rule | Transfer phải có cả warehouse_from và warehouse_to | Inventory Design §BR | `services/inventory.py: validate_movement()` | `TC-INV-001: test_transfer_requires_both_warehouses` | S-12 | #imm00-inv | v4.0.0 | ✅ |
| BR-INV-03 | Rule | Adjustment phải có approved_by | Inventory Design §BR | `services/inventory.py: validate_movement()` | `TC-INV-002: test_adjustment_requires_approver` | S-12 | #imm00-inv | v4.0.0 | ✅ |
| BR-INV-04 | Rule | Cấm Issue vượt tồn kho hiện tại | Inventory Design §BR | `services/inventory.py: _check_stock_availability()` | `TC-INV-001: test_insufficient_stock_raises` | S-12 | #imm00-inv | v4.0.0 | ✅ |
| BR-INV-05 | Rule | Cảnh báo khi tồn kho < min_stock | Inventory Design §BR | `services/inventory.py: _check_low_stock_alert()` | `TC-INV-003: test_low_stock_alert_fires` | S-13 | #imm00-inv | v4.0.0 | ✅ |
| BR-INV-06 | Rule | Spare Part Stock — on_hand_qty không âm | Inventory Design §BR | `AC Spare Part Stock.on_hand_qty` validate ≥ 0 | `TC-INV-001: test_stock_cannot_go_negative` | S-12 | #imm00-inv | v4.0.0 | ✅ |
| BR-INV-07 | Rule | Stock Movement — submitted = immutable | Inventory Design §BR | `AC Stock Movement` controller `before_save` raise if submitted | `TC-INV-002: test_submitted_movement_immutable` | S-12 | #imm00-inv | v4.0.0 | ✅ |
| BR-INV-08 | Rule | Spare Part SKU unique | Inventory Design §BR | `AC Spare Part.sku` unique index | `TC-INV-003: test_sku_unique` | S-13 | #imm00-inv | v4.0.0 | ✅ |

---

## III.4. Matrix — Compliance

| Req ID | Loại | Mô tả ngắn | Doc ref | Design / Code | Test ID | UAT ID | PR | Released in | Status |
|---|---|---|---|---|---|---|---|---|---|
| NĐ98/Điều 15.2 | Compliance | Lưu trữ hồ sơ ≥ 5 năm (khuyến nghị 7 năm) | 08 §IV.1 | `IMM Audit Trail` immutable + retention policy 7yr | `TC-S-004`, `test_audit_chain_intact` | S-07 | #imm00-core | v3.0.0 | ✅ |
| NĐ98/Điều 22.3 | Compliance | Thiết bị phải có traceability vật tư | 08 §IV.1 | `Asset Lifecycle Event` ghi nhận mọi thay đổi + vật tư | `TC-S-009` | S-05 | #imm00-core | v3.0.0 | ✅ |
| NĐ98/Điều 8.1 | Compliance | Phân loại thiết bị theo Class I/II/III | 04 §II.5 | `AC Asset Category.risk_class` field + SLA lookup | `TC-S-007` | S-04 | #imm00-core | v3.0.0 | ✅ |
| WHO HTM 2025 §3.2 | Compliance | Lifecycle Event toàn vòng đời thiết bị | 02 §II | `Asset Lifecycle Event` DocType — ALE- prefix | `TC-S-009` | S-05 | #imm00-core | v3.0.0 | ✅ |
| WHO HTM 2025 §5.1 | Compliance | CAPA management | 04 §II.9 | `IMM CAPA Record` + `check_capa_overdue()` | `TC-S-006` | S-08 | #imm00-core | v3.0.0 | ✅ |
| ISO 13485 §8.5.2 | Compliance | Corrective action có deadline và verification | 04 §II.9 | `IMM CAPA Record.deadline` + `Pending Verification` state | `TC-S-006` | S-08 | #imm00-core | v3.0.0 | ✅ |
| ISO 13485 §4.2.4 | Compliance | Document control — version, approval | 04 §II | `IMM Audit Trail` + `QMS Document` via integration | `TC-S-004`, `TC-S-005` | S-07 | #imm00-core | v3.0.0 | ✅ |
| ISO/IEC 17025 §6.4 | Compliance | Thiết bị đo lường có hiệu chuẩn truy xuất | 04 §II.1 | `AC Asset.calibration_due_date` + `check_registration_expiry()` | `TC-S-013` | S-10 | #imm00-core | v3.0.0 | ✅ |

---

## III.5. Matrix — Security

| Req ID | Loại | Mô tả ngắn | Doc ref | Design / Code | Test ID | Released in | Status |
|---|---|---|---|---|---|---|---|
| SEC-00-01 | Security | KTV chỉ thấy Asset được giao (permission query scope) | 07 §III.2 | `permissions.py: asset_permission_query()` | `SEC-01: test_ktv_permission_scope` | v3.0.0 | ✅ |
| SEC-00-02 | Security | Audit Trail không thể xóa/sửa — kể cả Admin | 07 §III.2 | DocPerm no-delete + controller guard | `SEC-02: test_admin_cannot_delete_audit` | v3.0.0 | ✅ |
| SEC-00-03 | Security | Hash chain phá vỡ khi tamper | 07 §III.2 | `verify_audit_chain()` — SHA-256 recompute | `SEC-03: test_audit_chain_breaks_on_tamper` | v3.0.0 | ✅ |
| SEC-00-04 | Security | API rate limit 300 req/min | 07 §III.2 | Frappe rate limiting middleware | `SEC-04: test_rate_limit_exceeded` | v3.0.0 | ✅ |
| SEC-00-05 | Security | CSRF protection trên mọi POST/PUT/DELETE | 07 §III.2 | Frappe CSRF middleware + axios interceptor | `SEC-05: test_csrf_rejected` | v3.0.0 | ✅ |
| ~~SEC-00-06~~ | Security | *(Đã loại bỏ 2026-05-19 — endpoint trạng thái sử dụng GMDN đã gỡ. Ref [analysis §6](../res/gmdn-asset-category-analysis.md))* | — | — | — | v3.1.0 | ⛔ removed |
| SEC-00-07 | Security | Stock Movement Adjustment phải có approver | 07 §III.2 | `BR-INV-03` enforcement | `SEC-07: test_adjustment_role_check` | v4.0.0 | ✅ |
| SEC-00-08 | Security | Không có SQL injection qua filter params | 07 §III.2 | Frappe ORM parameterized queries | `SEC-08: test_sql_injection_prevention` | v3.0.0 | ✅ |

---

## III.6. Matrix — User Stories (Foundation Setup)

| Req ID | Loại | Mô tả ngắn | Doc ref | Design / Code | Test ID | Released in | Status |
|---|---|---|---|---|---|---|---|
| US-00-01 | Story | Admin nhập toàn bộ AC Asset từ CSV một lần | Functional Specs §3 | `api/imm00.py: bulk_import_assets()` | `TC-S-001` | v3.0.0 | ✅ |
| US-00-02 | Story | Tra trạng thái thiết bị theo serial | Functional Specs §3 | `api/imm00.py: get_asset_by_serial()` | `TC-S-002` | v3.0.0 | ✅ |
| US-00-03 | Story | Chuyển trạng thái thiết bị có audit trail tự động | Functional Specs §3 | `services/imm00.py: transition_asset_status()` + `log_audit_event()` | `TC-S-003` | v3.0.0 | ✅ |
| US-00-04 | Story | QA xác minh audit chain | Functional Specs §3 | `api/imm00.py: verify_audit_chain()` | `TC-S-005` | v3.0.0 | ✅ |
| US-00-05 | Story | QA mở CAPA từ sự kiện repeat failure | Functional Specs §3 | `api/imm00.py: create_capa()` | `TC-S-006` | v3.0.0 | ✅ |
| US-00-06 | Story | Ops Manager xem SLA compliance report | Functional Specs §3 | `api/imm00.py: get_sla_compliance_report()` | `TC-S-007` | v3.0.0 | ✅ |
| US-00-07 | Story | Scheduler cảnh báo hợp đồng sắp hết hạn | Functional Specs §3 | `services/imm00.py: check_vendor_contract_expiry()` | `TC-S-008` | v3.0.0 | ✅ |
| US-00-08 | Story | Technician quét QR → mở hồ sơ thiết bị (repurposed 2026-05-19, không còn toggle) | Functional Specs §3 | `views/system/QRScanView.vue` → `/assets/:id` | — | v3.1.0 | ✅ |
| US-00-09 | Story | Storekeeper nhập xuất tồn kho phụ tùng | Functional Specs §3 | `services/inventory.py: process_stock_movement()` | `TC-INV-001`, `TC-INV-002` | v4.0.0 | ✅ |
| US-00-10 | Story | Hệ thống cảnh báo khi tồn kho dưới min | Functional Specs §3 | `services/inventory.py: _check_low_stock_alert()` | `TC-INV-003` | v4.0.0 | ✅ |

---

## III.7. Reverse Lookup

| Test ID | Requirement(s) cover |
|---|---|
| `TC-S-001: test_device_model_gmdn_unique` | BR-00-01, US-00-01 |
| `TC-S-002: test_asset_serial_unique` | BR-00-02, US-00-02 |
| `TC-S-003: test_transition_active_to_maintenance` | BR-00-03, US-00-03 |
| `TC-S-003: test_invalid_transition_raises` | BR-00-03 |
| `TC-S-004: test_audit_trail_immutable` | BR-00-04, NĐ98/Điều 15.2 |
| `TC-S-005: test_audit_hash_chain_integrity` | BR-00-05, US-00-04 |
| `TC-S-005: test_audit_chain_breaks_on_tamper` | BR-00-05, SEC-00-03, ISO 13485 §4.2.4 |
| `TC-S-006: test_capa_overdue_flag` | BR-00-06, US-00-05, WHO HTM §5.1, ISO 13485 §8.5.2 |
| `TC-S-007: test_sla_lookup_by_category` | BR-00-07, US-00-06, NĐ98/Điều 8.1 |
| `TC-S-008: test_vendor_expiry_alert` | BR-00-08, US-00-07 |
| `TC-S-009: test_lifecycle_event_immutable` | BR-00-09, NĐ98/Điều 22.3, WHO HTM §3.2 |
| `TC-S-010: test_incident_requires_asset` | BR-00-10 |
| `TC-S-011: test_gmdn_required_for_active` | BR-00-11 |
| `TC-S-012: test_gmdn_disable_requires_reason` | BR-00-12, US-00-08, SEC-00-06 |
| `TC-S-013` | ISO/IEC 17025 §6.4 |
| `TC-INV-001: test_issue_requires_warehouse_from` | BR-INV-01, US-00-09 |
| `TC-INV-001: test_transfer_requires_both_warehouses` | BR-INV-02, US-00-09 |
| `TC-INV-001: test_insufficient_stock_raises` | BR-INV-04, US-00-09 |
| `TC-INV-001: test_stock_cannot_go_negative` | BR-INV-06 |
| `TC-INV-002: test_adjustment_requires_approver` | BR-INV-03, SEC-00-07 |
| `TC-INV-002: test_submitted_movement_immutable` | BR-INV-07 |
| `TC-INV-003: test_low_stock_alert_fires` | BR-INV-05, US-00-10 |
| `TC-INV-003: test_sku_unique` | BR-INV-08 |
| `SEC-01: test_ktv_permission_scope` | SEC-00-01 |
| `SEC-02: test_admin_cannot_delete_audit` | SEC-00-02, BR-00-04, ISO 13485 §4.2.4 |
| `SEC-04: test_rate_limit_exceeded` | SEC-00-04 |
| `SEC-05: test_csrf_rejected` | SEC-00-05 |
| `SEC-08: test_sql_injection_prevention` | SEC-00-08 |

---

## III.8. Coverage Gaps

Sau rà soát matrix, không có req Must/Should còn ⬜ trước v4.0.0. Gaps roadmap:

| Req ID | Thiếu gì? | Owner | Deadline |
|---|---|---|---|
| `verify_audit_chain` performance | Chậm với > 10,000 records — cần batch processing | DevOps | v4.1.0 |
| QR scan GMDN trên Safari iOS < 17.2 | Fix WebRTC camera API | Dev IMM-00 | v4.0.1 |
| Pentest report `docs/security/` | Report chưa upload | Security Lead | Trước go-live |
| 2FA cho IMM System Admin | Roadmap Phase 2 | Tech Lead | v5.0 |
| Inventory report filter by supplier | Filter API chưa expose | Dev IMM-00 | v4.0.1 |

---

## III.9. Bảng Thống Kê Thông Tin Ứng Dụng

| Hạng mục | Số lượng | Ghi chú |
|---|---|---|
| DocType (core — prefix AC) | 5 | `AC Asset`, `AC Supplier`, `AC Location`, `AC Department`, `AC Asset Category` |
| DocType (governance — prefix IMM) | 6 | `IMM Device Model`, `IMM SLA Policy`, `IMM Audit Trail`, `IMM CAPA Record`, `Asset Lifecycle Event`, `Incident Report` |
| DocType (inventory v4 — prefix AC) | 5 | `AC Warehouse`, `AC Spare Part`, `AC Spare Part Stock`, `AC Stock Movement`, `AC Stock Movement Item` |
| DocType (child) | 3 | `Asset Lifecycle Event Item`, `CAPA Action Item`, `AC Stock Movement Item` |
| Tổng DocType | 18 + 3 child | Foundation layer — dùng bởi tất cả 17 module IMM |
| API endpoint (imm00.py) | 42 | 11 nhóm: Asset, Supplier, Location/Dept/Cat, Device Model, SLA, Audit, CAPA, ALE, Incident, GMDN, Scheduler |
| API endpoint (inventory.py) | 14 | 4 nhóm: Warehouse, Spare Part, Stock, Movement |
| Service function (imm00.py) | 9 | `log_audit_event`, `transition_asset_status`, `get_applicable_sla`, `check_capa_overdue`, `check_vendor_contract_expiry`, `check_registration_expiry`, `rollup_asset_kpi`, `verify_audit_chain`, `validate_gmdn_before_active` *(2 hàm trạng thái GMDN cũ đã gỡ 2026-05-19)* |
| Service function (inventory.py) | 7 | `process_stock_movement`, `get_stock_by_spare_part`, `get_stock_by_warehouse`, `validate_movement`, `_update_stock_balance`, `_check_stock_availability`, `_check_low_stock_alert` |
| Scheduler job | 4 | `check_capa_overdue` (daily), `check_vendor_contract_expiry` (daily), `check_registration_expiry` (daily), `rollup_asset_kpi` (daily) |
| IMM Role | 8 | System Admin, Dept Head, Ops Manager, Workshop Lead, Technician, Document Officer, Storekeeper, QA Officer |
| Business Rule (core) | 12 | BR-00-01 → BR-00-12 |
| Business Rule (inventory) | 8 | BR-INV-01 → BR-INV-08 |
| User Story | 10 | US-00-01 → US-00-10 |
| Compliance standard map | 4 | NĐ 98/2021, WHO HTM 2025, ISO 13485:2016, ISO/IEC 17025 |
| Test case unit (core) | 13 | TC-S-001 → TC-S-013 |
| Test case unit (inventory) | 3 | TC-INV-001 → TC-INV-003 |
| Security test case | 8 | SEC-01 → SEC-08 |
| FE view / page | 13+ | Dashboard, Asset List/Detail/Form, SLA Matrix, Audit Trail, CAPA Board, Incident Wizard, Inventory views |
| FE Pinia store | 4 | `authStore`, `uiStore`, `notifStore`, module store pattern |
| FE composable | 3+ | `useAsset`, `useAuditTrail`, `useInventory` |
| Smoke test checklist | 13 | S-01 → S-13 (xem 08_Deployment.md §V.1) |
| Migration patch | 4 | v3_0/001, v3_2/001, v3_2/002, v4_0/001 |
| Audit retention | 7 năm | Theo NĐ 98/2021 §15.2 + WHO HTM 2025 |

---

## III.10. Audit-readiness — Quick Links

**Auditor hỏi:** "Chứng minh rằng không ai có thể sửa hồ sơ kiểm toán sau khi tạo?"

Trace: `BR-00-04 → IMM Audit Trail controller (before_save guard) → DocPerm no-delete → SEC-00-02 test`

---

**Auditor hỏi:** "Làm sao biết hồ sơ audit trail chưa bị giả mạo?"

Trace: `BR-00-05 → log_audit_event() SHA-256 hash chain → verify_audit_chain() endpoint → SEC-00-03 test_audit_chain_breaks_on_tamper`

---

**Auditor hỏi:** "Thiết bị Class III có được theo dõi vòng đời đầy đủ không?"

Trace: `Asset Lifecycle Event (ALE- prefix) → transition_asset_status() ghi mọi thay đổi → WHO HTM 2025 §3.2 compliance → TC-S-003, TC-S-009`

---

**Auditor hỏi:** "CAPA có được theo dõi và đóng trong thời hạn không?"

Trace: `IMM CAPA Record → check_capa_overdue() daily scheduler → Overdue state → email cảnh báo → ISO 13485 §8.5.2 → TC-S-006`

---

**Auditor hỏi:** "Xuất vật tư phụ tùng có được kiểm soát không?"

Trace: `BR-INV-01→04 → validate_movement() → AC Stock Movement (submitted = immutable) → TC-INV-001→002 → NĐ98/Điều 22.3`

---

## III.11. Cập Nhật Quy Ước

| Khi | Ai update | Cell nào |
|---|---|---|
| DocType mới thêm vào IMM-00 | Tech Lead | Bảng Thống Kê + Matrix dòng mới |
| BR mới (từ Business Change Request) | BA Lead | Thêm dòng BR, điền `Doc ref`, `Design/Code` |
| Test case viết xong | Dev/QA | Điền `Test ID` |
| Compliance requirement mới | QA Officer / BA Lead | Thêm dòng Compliance, map về BR/Code |
| Release mới | PM | Chốt `Released-in` + status ✅ |
| Gap phát hiện | QA/Dev | Thêm vào §III.8 Coverage Gaps |

---

## DoD — Hoàn chỉnh

### I. User Guide (System Admin)
- [x] Tiếng Việt 100%, không jargon kỹ thuật
- [x] Quy trình thiết lập 9 bước từ cài đặt đến bàn giao
- [x] Hướng dẫn từng role: System Admin, Ops Manager, Storekeeper, QA Officer
- [x] FAQ 8 câu thực tế (thiết lập + vận hành)
- [x] Cheat sheet trạng thái AC Asset + CAPA
- [x] Bảng điều khiển KPI tổng hợp
- [ ] Screenshot UI thực tế trên staging (cần chụp trước go-live)
- [ ] Reviewed bởi BA + đại diện System Admin bệnh viện

### II. Release Notes
- [x] Tóm tắt user-friendly về v4.0.0
- [x] Tính năng mới: Inventory v4 + GMDN QR scan
- [x] Breaking changes documented (envelope + Spare Part migration)
- [x] Known issues + workaround
- [x] Compatibility table
- [x] Lịch sử version từ v2 đến v4
- [ ] Reviewed bởi PM + Tech Lead + BA

### III. Traceability Matrix
- [x] 12 BR core (BR-00-01→12) đầy đủ
- [x] 8 BR inventory (BR-INV-01→08) đầy đủ
- [x] 8 Compliance rows (NĐ98, WHO HTM, ISO 13485, ISO/IEC 17025)
- [x] 8 Security rows (SEC-00-01→08)
- [x] 10 User Stories (US-00-01→10)
- [x] Reverse lookup table 29 entries
- [x] Coverage Gaps 5 items
- [x] Bảng Thống Kê 20+ hạng mục
- [x] Audit-readiness Quick Links (5 audit scenarios)
- [ ] Reviewed bởi PM + Tech Lead + QA Lead
