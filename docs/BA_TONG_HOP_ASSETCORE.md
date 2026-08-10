# AssetCore — Tài liệu BA tổng hợp (Chức năng · Giao diện · Backend)

| Mục | Giá trị |
|---|---|
| Phạm vi | Toàn hệ thống AssetCore — 18 module IMM-00 → IMM-17 |
| Loại tài liệu | Tổng hợp BA (consolidated) — **dẫn xuất**, không thay thế `docs/imm-XX/` |
| Nguồn | `docs/imm-XX/02_Analysis_Design.md` (§I Module Overview) + `docs/architecture/Ho_so_kien_truc_IMMIS.md` + đối chiếu mã nguồn |
| Ngày lập | 2026-08-05 |
| Nhánh mã đối chiếu | `feature/hieuc/core-refinement` |
| Trạng thái | Snapshot — số liệu đếm từ mã nguồn tại ngày lập |

---

## Phần 0 — Cách đọc tài liệu này

### 0.1. Mục đích

Tài liệu này gom **toàn bộ chức năng nghiệp vụ, giao diện người dùng và thiết kế backend** của AssetCore vào một chỗ, để:

- BA / khách hàng nắm được **hệ thống làm được gì** mà không phải mở 18 thư mục tài liệu.
- Đội phát triển tra nhanh **module nào sở hữu DocType / endpoint / màn hình nào**.
- Kiểm toán truy vết **chức năng ↔ mã nguồn ↔ tuân thủ**.

### 0.2. Quan hệ với bộ tài liệu module (KHÔNG thay thế)

| Tài liệu | Vai trò | Thẩm quyền |
|---|---|---|
| `docs/imm-XX/02_Analysis_Design.md` … `09_Release.md` | **Core Doc / PRD gốc** của từng module — nguồn chuẩn để code | **Cao nhất** |
| `docs/architecture/Ho_so_kien_truc_IMMIS.md` | Kiến trúc tổng — tên module, khối, đợt, vai trò | Cao |
| **File này** | Bản tổng hợp dẫn xuất — điều hướng + tra cứu nhanh | Tham chiếu |

> ⚠️ Khi có mâu thuẫn: **Core Doc module thắng**. File này chỉ tóm tắt, không phải nơi chốt spec. Sửa yêu cầu nghiệp vụ ⇒ sửa `docs/imm-XX/`, rồi cập nhật lại file này.

### 0.3. Quy ước ký hiệu

| Ký hiệu | Nghĩa |
|---|---|
| **LIVE ✅** | Có mã BE + FE chạy thật trong repo |
| **PARTIAL 🟡** | Có mã một phần (BE có / FE thiếu, hoặc chỉ đọc) |
| **PLANNED ⬜** | Chỉ có tài liệu thiết kế — chưa scaffold mã |
| `[ROADMAP]` | Chức năng cam kết cho giai đoạn sau, hiện chưa có mã |
| `[UNVERIFIED]` | Nội dung lấy từ tài liệu, chưa đối chiếu được nguồn gốc |

### 0.4. Cách các con số trong tài liệu được đếm

Mọi con số định lượng ở Phần 1 và Phần 4 đều **đếm thật từ mã nguồn**, kèm lệnh tái lập:

```bash
# Số DocType
grep -l '"doctype": "DocType"' assetcore/assetcore/doctype/*/*.json | wc -l

# Số endpoint REST
grep -h "@frappe.whitelist" assetcore/api/*.py | wc -l

# Số route giao diện
grep -oE "path: '[^']*'" frontend/src/router/index.ts | sort -u | wc -l

# Số vai trò
python3 -c "import json;print(len(json.load(open('assetcore/fixtures/role.json'))))"

# Số workflow
python3 -c "import json;print(len(json.load(open('assetcore/fixtures/workflow.json'))))"
```

---

## Phần 1 — Tổng quan hệ thống

### 1.1. AssetCore là gì

AssetCore là **hệ thống quản trị vòng đời thiết bị y tế (Healthcare Technology Management — HTM)** xây trên nền Frappe Framework v15, phục vụ bệnh viện Việt Nam.

Điểm khác biệt cốt lõi so với một CMMS thông thường: AssetCore **không chỉ quản lý lệnh bảo trì**, mà quản trị toàn bộ chuỗi vòng đời theo khung WHO HTM:

```
Nhu cầu → Đặc tả → Mua sắm → Lắp đặt → Hồ sơ → Đào tạo
   → Vận hành → Bảo trì định kỳ → Sửa chữa → Hiệu chuẩn → Sự cố
   → Tồn kho phụ tùng → Tuân thủ → Ngừng sử dụng → Giải nhiệm
```

Ba nguyên tắc kiến trúc bất di bất dịch:

1. **Mọi nghiệp vụ đều sinh bản ghi** — không có thao tác nào không để lại dấu vết kiểm toán.
2. **Mọi hành động đi qua Work Order hoặc phiếu nghiệp vụ** — không có "sửa chữa miệng".
3. **Không sửa lõi ERPNext/Frappe** — chỉ mở rộng bằng DocType riêng (tiền tố `AC` / `IMM`).

### 1.2. Bản đồ 18 module

| Khối | Module | Tên nghiệp vụ | Đợt | Trạng thái mã |
|---|---|---|---|---|
| **Nền tảng** | **IMM-00** | Dữ liệu nền & Dịch vụ dùng chung | 1 | **LIVE ✅** |
| **A. Hoạch định** | IMM-01 | Nhu cầu & Dự toán ngân sách | 2 | **LIVE ✅** |
| | IMM-02 | Đặc tả kỹ thuật & Phân tích thị trường | 2 | **LIVE ✅** |
| | IMM-03 | Đánh giá nhà cung cấp & Quyết định mua sắm | 2 | **LIVE ✅** |
| **B. Triển khai** | IMM-04 | Lắp đặt & Nghiệm thu đưa vào sử dụng | 1 | **LIVE ✅** |
| | IMM-05 | Hồ sơ thiết bị | 1 | **LIVE ✅** |
| | IMM-06 | Đào tạo & Năng lực vận hành | 2 | **LIVE ✅** |
| **C. Vận hành** | IMM-07 | Theo dõi hiệu suất | 3 | **PLANNED ⬜** |
| | IMM-08 | Bảo trì định kỳ (PM) | 1 | **LIVE ✅** |
| | IMM-09 | Sửa chữa (CM) | 1 | **LIVE ✅** |
| | IMM-10 | Hậu kiểm & Thu hồi (PMS / Recall) | 3 | **PLANNED ⬜** |
| | IMM-11 | Hiệu chuẩn | 1 | **LIVE ✅** |
| | IMM-12 | Sự cố & Phân tích nguyên nhân gốc | 1 | **LIVE ✅** |
| | IMM-15 | Tồn kho phụ tùng | 2 | **LIVE ✅** |
| | IMM-16 | Giám sát tuân thủ & Hành động khắc phục | 2 | **LIVE ✅** |
| | IMM-17 | Phân tích dự đoán | 3 | **PLANNED ⬜** |
| **D. Kết thúc vòng đời** | IMM-13 | Ngừng sử dụng & Điều chuyển | 3 | **PLANNED ⬜** |
| | IMM-14 | Giải nhiệm thiết bị | 3 | **PARTIAL 🟡** |

**Tổng: 18 module** (IMM-00 nền tảng + 17 module nghiệp vụ). 12 module LIVE, 1 PARTIAL, 5 PLANNED.

> 📌 Lưu ý đánh số: dãy IMM-01…IMM-17 **không có khoảng trống** — nhưng IMM-13 và IMM-14 nằm ở khối D (kết thúc vòng đời) chứ không nối tiếp IMM-12 về mặt thời gian nghiệp vụ; IMM-15/16/17 quay lại khối C.

### 1.3. Số liệu hệ thống (đếm từ mã nguồn, 2026-08-05)

| Hạng mục | Số lượng | Ghi chú |
|---|---|---|
| Module | **18** | IMM-00 → IMM-17 |
| DocType (mô hình dữ liệu) | **110** | 65 bảng chính + 45 bảng con (`istable=1`); 26 bảng có ký duyệt (`is_submittable=1`) |
| Endpoint REST công bố | **527** | `@frappe.whitelist()` trên 27 file trong `assetcore/api/` |
| Workflow (máy trạng thái) | **22** | `assetcore/fixtures/workflow.json` |
| Vai trò hệ thống | **30** | 4 vai trò hệ thống + 26 vai trò nghiệp vụ (13 module × Quản lý/Người dùng) |
| Capability (quyền chi tiết) | **105** | 15 miền × 6 loại quyền + 15 quyền chuyên biệt |
| Route giao diện | **148** | `frontend/src/router/index.ts` |
| Màn hình Vue | **137** | `frontend/src/views/**/*.vue` |
| Kho trạng thái (Pinia store) | **18** | `frontend/src/stores/` |
| Composable dùng chung | **20** | `frontend/src/composables/` |
| Thành phần dùng chung | **41** | 33 `components/common/` + 8 `components/ui/` (tầng nguyên thủy) |
| Tác vụ định kỳ (scheduler) | **~40** | hằng ngày / hằng tuần / hằng tháng, `assetcore/hooks.py` |
| Tệp kiểm thử | **539** | 140 kiểm thử Python + 399 kiểm thử Vitest |
| Dòng mã | **~300.000** | ~215.000 Python + ~85.000 TypeScript/Vue |

### 1.4. Kiến trúc phân lớp

```
┌──────────────────────────────────────────────────────────────┐
│  NGƯỜI DÙNG (trình duyệt / thiết bị di động)                 │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼───────────────────────────────────┐
│  LỚP GIAO DIỆN — Vue 3 SPA (tách rời)                        │
│  Vue 3 · TypeScript · Vite · Pinia · Vue Router · TanStack    │
│  Query · TailwindCSS                                          │
│  148 route · 137 màn hình · 18 store · 41 thành phần chung    │
└──────────────────────────┬───────────────────────────────────┘
                           │ JSON, phong bì {success, data} / {success, error, code}
┌──────────────────────────▼───────────────────────────────────┐
│  LỚP API — assetcore/api/*.py  (527 endpoint)                │
│  Chỉ làm: xác thực tham số · gọi service · gói phong bì       │
│  KHÔNG chứa logic nghiệp vụ                                   │
└──────────────────────────┬───────────────────────────────────┘
┌──────────────────────────▼───────────────────────────────────┐
│  LỚP DỊCH VỤ — assetcore/services/*.py                       │
│  Toàn bộ quy tắc nghiệp vụ · gate · tính toán · điều phối     │
│  services/shared/: rbac · permissions · scope · state ·       │
│                    constants · filters · truncation           │
└──────────────────────────┬───────────────────────────────────┘
┌──────────────────────────▼───────────────────────────────────┐
│  LỚP DỮ LIỆU — 110 DocType (Frappe ORM) · MariaDB            │
│  Controller hook (validate / before_save / on_submit)         │
│  22 Workflow · DocPerm · permission_query_conditions          │
└──────────────────────────┬───────────────────────────────────┘
┌──────────────────────────▼───────────────────────────────────┐
│  LỚP NỀN — Frappe Framework v15                              │
│  Scheduler · Email Queue · File · Version · Socket.IO         │
└──────────────────────────────────────────────────────────────┘
```

**Ràng buộc bắt buộc:** logic nghiệp vụ **chỉ** nằm ở lớp dịch vụ. API không tính toán, DocType controller chỉ kiểm tra tính hợp lệ ở mức bản ghi.

### 1.5. Công nghệ nền

| Lớp | Công nghệ | Ghi chú |
|---|---|---|
| Ngôn ngữ backend | Python 3.11+ | bắt buộc type hint + docstring |
| Khung backend | **Frappe Framework v15** | WSGI / Werkzeug — **KHÔNG dùng FastAPI** |
| Phụ thuộc ERPNext | **Không** | DocType lõi tái tạo native với tiền tố `AC` / `IMM` |
| Cơ sở dữ liệu | MariaDB | |
| Khung frontend | **Vue 3** + TypeScript | SPA tách rời — **KHÔNG dùng Frappe UI** |
| Công cụ dựng | Vite | |
| Quản lý trạng thái | Pinia | 18 store theo module |
| Truy vấn dữ liệu | TanStack Query | cache + revalidate |
| Định tuyến | Vue Router | 148 route, có route guard theo capability |
| Kiểu dáng | TailwindCSS | token màu ngữ nghĩa 2 chiều (sáng/tối) |
| Kiểm thử | Frappe TestCase (Python) · Vitest (FE) · Playwright (giao diện) | |
| Tích hợp | OpenAPI 3 (`api/openapi.py`) · FHIR `[ROADMAP]` | |

---

## Phần 2 — Nền tảng dùng chung (áp dụng cho mọi module)

Đây là phần **quan trọng nhất** để hiểu hệ thống: mọi module đều tiêu thụ các cơ chế dưới đây thay vì tự dựng lại.

### 2.1. Sự kiện vòng đời (Lifecycle Event) — trục trung tâm

`Asset Lifecycle Event` là **sổ cái duy nhất** ghi nhận mọi biến cố của thiết bị.

| Trường | Ý nghĩa |
|---|---|
| `asset` | Thiết bị liên quan |
| `event_type` | Loại biến cố (`commissioned`, `pm_completed`, `failure_reported`, `repaired`, `calibrated`, `transferred`, `decommissioned`, …) |
| `timestamp` | Thời điểm |
| `actor` | Người thực hiện |
| `from_status` → `to_status` | Chuyển trạng thái vòng đời |
| `root_record` | Bản ghi nghiệp vụ gốc (phiếu PM / phiếu sửa chữa / phiếu hiệu chuẩn …) |

**Nguyên tắc:** mọi module thay đổi trạng thái thiết bị đều gọi `services/imm00.transition_asset_status()` — **không module nào tự viết lại máy trạng thái của thiết bị**.

Máy trạng thái thiết bị (`AC Asset.lifecycle_status`) — 8 trạng thái:

```
Nháp → Đã nghiệm thu → Đang sử dụng ⇄ Đang bảo trì
                                     ⇄ Đang sửa chữa
                                     ⇄ Đang hiệu chuẩn
                                     → Ngừng sử dụng → Đã giải nhiệm
```

### 2.2. Nhật ký kiểm toán bất biến (Audit Trail)

`IMM Audit Trail` ghi mọi thao tác thay đổi dữ liệu, có **chuỗi băm SHA-256** nối tiếp — sửa một bản ghi giữa chuỗi sẽ làm hỏng toàn bộ chuỗi phía sau và bị phát hiện.

- Cài đặt: `assetcore/utils/lifecycle.py`
- Kiểm tra tính toàn vẹn: endpoint `verify_chain`
- Xem trên giao diện: `/audit-trail`

### 2.3. Phân quyền — 30 vai trò + 105 capability

#### 2.3.1. Bốn vai trò hệ thống

| Vai trò | Mục đích |
|---|---|
| `AssetCore Super Admin` | Toàn quyền, bao trùm System Manager |
| `AssetCore System User` | Vai trò nền — đăng nhập, xem bảng điều khiển, đọc dữ liệu dùng chung. **Mọi người dùng AssetCore đều có vai trò này** |
| `AssetCore Auditor` | Chỉ đọc toàn bộ + nhật ký kiểm toán |
| `Vendor Engineer` | Kỹ sư nhà cung cấp — cô lập theo thiết bị / lệnh công việc được phân công |

#### 2.3.2. Hai mươi sáu vai trò nghiệp vụ (13 module × Quản lý / Người dùng)

| Module | Vai trò Quản lý | Vai trò Người dùng |
|---|---|---|
| IMM-00 Dữ liệu nền | `Data Manager` | `Data User` |
| IMM-01 Nhu cầu | `Needs Manager` | `Needs User` |
| IMM-02 Đặc tả | `Spec Manager` | `Spec User` |
| IMM-03 Mua sắm | `Procurement Manager` | `Procurement User` |
| IMM-04 Lắp đặt | `Commissioning Manager` | `Commissioning User` |
| IMM-05 Hồ sơ | `Document Manager` | `Document User` |
| IMM-06 Đào tạo | `Training Manager` | `Training User` |
| IMM-08 Bảo trì định kỳ | `PM Manager` | `PM User` |
| IMM-09 Sửa chữa | `Repair Manager` | `Repair User` |
| IMM-11 Hiệu chuẩn | `Calibration Manager` | `Calibration User` |
| IMM-12 Sự cố | `Corrective Manager` | `Corrective User` |
| IMM-15 Tồn kho | `Inventory Manager` | `Inventory User` |
| IMM-16 Tuân thủ | `Compliance Manager` | `Compliance User` |

#### 2.3.3. Capability — lớp quyền chi tiết

Giao diện **không bao giờ kiểm tra tên vai trò**. Thay vào đó backend suy ra 105 capability từ bảng DocPerm và trả về cho frontend:

```
<miền>.<loại quyền>     ví dụ:  pm.read · repair.submit · compliance.write
```

15 miền: `data · needs · spec · procurement · commissioning · document · training · pm · repair · calibration · corrective · inventory · compliance · asset · purchase` × 6 loại quyền (`read · write · create · delete · submit · cancel`) = 90, cộng 15 capability chuyên biệt:

`pm.reschedule · pm.read_history · incident.acknowledge · incident.close · cal.send_lab · doc.approve · capa.close · data.admin · audit.read · training.submit · decommission.read · decommission.create · decommission.approve · asset.print · asset.qr.rotate · firmware.approve`

> **Vì sao quan trọng:** đổi "ai được duyệt" = sửa DocPerm trong giao diện quản trị, **không cần triển khai lại mã**. Ngược lại, gate bằng tên vai trò cứng sẽ hỏng âm thầm nếu vai trò đó không tồn tại.

Bộ capability có **dấu phiên bản** (`__cap_version`) — khi thêm/bớt capability, frontend tự phát hiện bộ đệm cũ đã lỗi thời và nạp lại.

#### 2.3.4. Persona (nhóm vai trò nghiệp vụ)

Người dùng thật được gán **Role Profile** (hồ sơ vai trò) tiếng Việt — mỗi hồ sơ gom sẵn nhiều vai trò. Giao diện dùng persona để chọn bảng điều khiển và menu, nhưng **quyền thật luôn đến từ DocPerm**.

#### 2.3.5. Cô lập theo dòng dữ liệu

`permissions.py::ac_asset_query` giới hạn danh sách thiết bị:

- Kỹ thuật viên nội bộ: **thấy toàn bộ** thiết bị.
- `Vendor Engineer`: **chỉ thấy** thiết bị mình được phân công (`responsible_technician`).

Bất biến bắt buộc: **số đếm trên thẻ KPI phải bằng số dòng khi bấm vào xem chi tiết** (`count == drill`) — cả hai đều đi qua cùng một hàm lọc.

### 2.4. Hợp đồng API — phong bì chuẩn

Mọi endpoint trả về **HTTP 200** kèm phong bì:

```jsonc
// Thành công
{ "success": true, "data": { … }, "pagination": { "total": 128, "page": 1, "page_size": 20 } }

// Lỗi
{ "success": false, "error": "Thiết bị chưa có hồ sơ pháp lý đầy đủ",
  "code": "BUSINESS_RULE", "fields": { "byt_reg_no": "Bắt buộc" } }
```

**Bảng mã lỗi** (`assetcore/utils/response.py::ErrorCode`) — frontend phân nhánh trải nghiệm theo mã này:

| Mã | HTTP tương ứng | Ý nghĩa |
|---|---|---|
| `VALIDATION` | 422 | Dữ liệu nhập sai ở mức trường |
| `VALIDATION_ERROR` | 400 | Sai định dạng / không phân tích được |
| `BUSINESS_RULE` | 422 | Vi phạm quy tắc nghiệp vụ |
| `UNAUTHORIZED` | 401 | Chưa đăng nhập / hết phiên |
| `FORBIDDEN` | 403 | Đã đăng nhập nhưng thiếu quyền |
| `NOT_FOUND` | 404 | Không tìm thấy bản ghi |
| `CONFLICT` | 409 | Trùng lặp / xung đột trạng thái |
| `BAD_STATE` | 409 | Sai trạng thái quy trình |
| `DUPLICATE` | 409 | Trùng khoá |
| `INVALID_PARAMS` | 400 | Tham số không hợp lệ |
| `PAYLOAD_TOO_LARGE` | 413 | Vượt giới hạn kích thước |
| `RATE_LIMITED` | 429 | Vượt ngưỡng tần suất |
| `COMPLIANCE_BLOCKED` | 422 | Bị chặn bởi cổng tuân thủ IMM-16 |
| `INTERNAL` | 500 | Lỗi máy chủ ngoài dự kiến |

**Thông điệp lỗi bắt buộc tiếng Việt**, kèm gợi ý hành động. Lớp dịch vụ ném `ServiceError`, lớp API bắt và gói lại.

### 2.5. Máy trạng thái — 22 quy trình

| # | Quy trình | DocType | Số trạng thái | Các trạng thái |
|---|---|---|---|---|
| 1 | AC Asset Lifecycle | AC Asset | 8 | Nháp · Đã nghiệm thu · Đang sử dụng · Đang bảo trì · Đang sửa chữa · Đang hiệu chuẩn · Ngừng sử dụng · Đã giải nhiệm |
| 2 | IMM-01 Needs Workflow | IMM Needs Request | 8 | Nháp · Đã gửi · Đang rà soát · Đã xếp ưu tiên · Đã dự toán · Chờ phê duyệt · Đã duyệt · Từ chối |
| 3 | IMM-01 Plan Workflow | IMM Procurement Plan | 4 | Nháp · Đã duyệt · Đang hiệu lực · Đã đóng |
| 4 | IMM-02 Spec Workflow | IMM Tech Spec | 7 | Nháp · Đang rà soát · Đã đối chuẩn · Đã đánh giá rủi ro · Chờ phê duyệt · Đã chốt · Đã rút |
| 5 | IMM-03 Vendor Eval Workflow | IMM Vendor Evaluation | 5 | Nháp · Mở mời thầu · Đã nhận báo giá · Đã chấm điểm · Huỷ |
| 6 | IMM-03 AVL Workflow | IMM AVL Entry | 5 | Nháp · Đã duyệt · Có điều kiện · Tạm đình chỉ · Hết hạn |
| 7 | IMM-03 Decision Workflow | IMM Procurement Decision | 9 | Nháp · Đã chọn phương thức · Đàm phán · Đề xuất trúng · Chờ phê duyệt · Đã trao thầu · Đã ký hợp đồng · Đã phát hành đơn hàng · Huỷ |
| 8 | IMM-04 Workflow | Asset Commissioning | 11 | Nháp · Chờ kiểm hồ sơ · Chờ lắp đặt · Đang lắp đặt · Định danh · Kiểm tra ban đầu · Không phù hợp · Tạm giữ lâm sàng · Kiểm tra lại · Cho phép sử dụng · Trả nhà cung cấp |
| 9 | IMM-05 Document Workflow | Asset Document | 6 | Nháp · Chờ rà soát · Hiệu lực · Từ chối · Lưu trữ · Hết hạn |
| 10 | IMM-06 Session Workflow | IMM Training Session | 7 | Đã lên kế hoạch · Đã xác nhận · Đang diễn ra · Hoàn thành · Đã kiểm chứng · Đã đóng · Huỷ |
| 11 | IMM-06 Competency Workflow | IMM User Competency | 6 | Chờ đánh giá · Hiệu lực · Sắp hết hạn · Hết hạn · Tạm đình chỉ · Thu hồi |
| 12 | IMM-08 PM Workflow | PM Work Order | 7 | Mở · Đang thực hiện · Chờ – thiết bị bận · Quá hạn · Dừng – hỏng nặng · Hoàn thành · Huỷ |
| 13 | IMM-09 Repair Workflow | Asset Repair | 9 | Mở · Đã phân công · Đang chẩn đoán · Chờ phụ tùng · Đang sửa · Chờ nghiệm thu · Không sửa được · Hoàn thành · Huỷ |
| 14 | IMM-11 Calibration Workflow | IMM Asset Calibration | 8 | Đã lên lịch · Đang thực hiện · Đã gửi phòng kiểm định · Đã nhận chứng chỉ · Đạt · Không đạt · Đạt có điều kiện · Huỷ |
| 15 | IMM-12 Incident Workflow | Incident Report | 7 | Mở · Đã tiếp nhận · Đang xử lý · Đã khắc phục · Cần phân tích nguyên nhân · Đã đóng · Huỷ |
| 16 | IMM-12 RCA Workflow | IMM RCA Record | 4 | Cần phân tích · Đang phân tích · Hoàn thành · Huỷ |
| 17 | IMM-15 Spare Allocation Workflow | IMM Spare Allocation | 6 | Yêu cầu · Đã duyệt · Đã soạn hàng · Đã xuất · Đã trả · Huỷ |
| 18 | IMM-15 Cycle Count Workflow | IMM Stock Cycle Count | 4 | Đã lên kế hoạch · Đang kiểm · Đã rà soát · Đã ghi sổ |
| 19 | IMM-16 CAPA Workflow | IMM CAPA Record | 7 | Mở · Đang điều tra · Kế hoạch hành động · Đang thực thi · Kiểm chứng · Đã đóng · Mở lại |
| 20 | IMM-16 Compliance Finding Workflow | IMM Compliance Finding | 7 | Mở · Đang rà soát · Xác nhận không phù hợp · Cảnh báo giả · Miễn trừ · Đã khắc phục · Đã đóng |
| 21 | IMM-16 Internal Audit Workflow | IMM Internal Audit | 4 | Đã lên kế hoạch · Đang thực hiện · Đang lập báo cáo · Đã đóng |
| 22 | IMM-16 Management Review Workflow | IMM Management Review | 4 | Nháp · Đã họp · Đã duyệt biên bản · Đã đóng |

**Quy tắc bắt buộc về nút thao tác:** giao diện chỉ hiển thị nút chuyển trạng thái theo danh sách `allowed_transitions` do máy chủ trả về (đã lọc theo vai trò). **Cấm** frontend tự suy từ `workflow_state === 'X'` — làm vậy sẽ hiện nút mà người dùng bấm vào bị từ chối.

**Song hành hai trục trạng thái:** `docstatus` (sổ cái Frappe: nháp/đã ký/đã huỷ) và `workflow_state` (luồng nghiệp vụ hiển thị) là hai trục độc lập, cố ý không gộp.

### 2.6. Tác vụ định kỳ (Scheduler)

Khoảng 40 tác vụ tự động, khai báo tại `assetcore/hooks.py`:

**Hằng ngày:**

| Tác vụ | Module | Việc |
|---|---|---|
| `check_capa_overdue` | IMM-00 | Cảnh báo hành động khắc phục quá hạn |
| `check_vendor_contract_expiry` | IMM-00 | Hợp đồng nhà cung cấp sắp hết hạn |
| `check_registration_expiry` | IMM-00 | Số đăng ký lưu hành Bộ Y tế sắp hết hạn (90/60/30/7 ngày) |
| `check_insurance_expiry` | IMM-00 | Bảo hiểm thiết bị sắp hết hạn |
| `check_service_contract_expiry` | IMM-00 | Hợp đồng bảo trì sắp hết hạn |
| `check_document_expiry` | IMM-05 | Hồ sơ thiết bị sắp hết hạn |
| `check_pm_overdue` | IMM-08 | Đánh dấu lệnh bảo trì quá hạn |
| `backfill_pm_schedules_for_due_assets` | IMM-08 | Bù lịch bảo trì cho thiết bị thiếu |
| `generate_pm_work_orders_from_schedule` | IMM-08 | Sinh lệnh bảo trì đến hạn |
| `create_due_calibration_wos` | IMM-11 | Sinh phiếu hiệu chuẩn đến hạn |
| `check_calibration_expiry` | IMM-11 | Chứng chỉ hiệu chuẩn hết hạn |
| `detect_chronic_failures` | IMM-12 | Phát hiện sự cố mãn tính (≥3 lần/90 ngày cùng mã lỗi) |
| `check_low_stock` · `check_low_stock_and_alert` | IMM-00/15 | Tồn kho dưới ngưỡng |
| `check_critical_spare_breach` | IMM-15 | Phụ tùng trọng yếu thủng ngưỡng |
| `check_expiring_batches` | IMM-15 | Lô phụ tùng sắp hết hạn |
| `compute_inventory_kpis` | IMM-15 | Tính chỉ số tồn kho |
| `check_pending_request_overdue` | IMM-01 | Phiếu nhu cầu tồn > 30 ngày |
| `check_overdue_drafts` | IMM-02 | Bản đặc tả nháp quá hạn |
| `check_avl_expiry` · `check_audit_due` · `check_decision_overdue` | IMM-03 | Danh sách nhà cung cấp hết hạn / đến kỳ đánh giá / quyết định quá hạn |
| `check_expiring_competencies` · `auto_expire_competencies` · `check_recertification_due` | IMM-06 | Năng lực sắp/đã hết hạn, đến hạn tái chứng nhận |
| `check_commissioning_overdue` | IMM-04 | Phiếu nghiệm thu quá 30 ngày |
| `evaluate_all_compliance_rules` · `check_capa_due` · `check_audit_milestones` | IMM-16 | Chạy bộ quy tắc tuân thủ, hạn CAPA, mốc kiểm toán |

**Hằng tuần:** cảnh báo sử dụng ngân sách (IMM-01) · đối chuẩn thị trường lỗi thời (IMM-02) · báo cáo thiếu hụt năng lực (IMM-06) · đánh giá tuân thủ + nhắc họp xem xét lãnh đạo (IMM-16).

**Hằng tháng:** tổng hợp chỉ số thiết bị (IMM-00) · chạy khấu hao đến kỳ (IMM-00).

### 2.7. Chính sách SLA

`IMM SLA Policy` tra cứu theo `mức ưu tiên × mức rủi ro thiết bị`, dùng chung bởi IMM-04/08/09/11/12.

- Thang ưu tiên: **P1 → P4**.
- Sự cố dùng thang mức độ nghiêm trọng (Thấp/Trung bình/Cao/Nghiêm trọng) và được ánh xạ: `Nghiêm trọng→P1, Cao→P2, Trung bình→P3, Thấp→P4`.
- Không tìm được chính sách khớp ⇒ **bỏ qua việc đặt hạn**, không chặn thao tác.

### 2.8. Thông báo

Khung thông báo hai kênh: **trong ứng dụng** (chuông) + **thư điện tử** (bật/tắt theo người dùng).

- Danh sách người nhận lấy từ nguồn duy nhất `services/shared/notify_roles.py` — không rải tên vai trò khắp mã.
- Thông điệp lấy từ sổ đăng ký `utils/messages.py` (`MSG.*`), có tiêu đề, mức độ, gợi ý hành động.
- Endpoint: `get_notification_preferences` · `set_email_enabled` · `get_delivery_kpi` · `list_notifications` · `mark_notification_as_read` · `mark_all_as_read`.
- Màn hình: `/settings/notifications`.

### 2.9. Hệ thống thiết kế giao diện

| Thành phần | Vai trò |
|---|---|
| **Token màu ngữ nghĩa** | 15 biến `--ac-color-*` + 5 họ màu × {50,500,700}, hoạt động hai chiều sáng/tối |
| **8 primitive** (`components/ui/`) | `Button` · `Badge` · `Card` · `DataTable` · `EmptyState` · `ErrorState` · `Skeleton` · `ListPageShell` |
| **`ListPageShell`** | Khuôn màn hình danh sách — cưỡng chế **4 trạng thái loại trừ lẫn nhau**: đang tải / lỗi + nút «Thử lại» / rỗng + hướng dẫn / có dữ liệu |
| **`DetailPageShell`** | Khuôn màn hình chi tiết — lỗi phân loại theo nguyên nhân (mạng / 403 / 404), tắt bảng thao tác khi chưa có dữ liệu |
| **`BaseModal`** | Nguồn duy nhất cho hộp thoại: `role="dialog"`, `aria-modal`, `aria-labelledby`, đóng bằng ESC, bẫy tiêu điểm, trả tiêu điểm về nút mở |
| **`useFocusTrap`** | Composable bẫy tiêu điểm dùng chung |
| **`DetailTabBar`** | Thanh tab màn chi tiết, đáp ứng màn hình nhỏ |
| **`CommandPalette`** | Bảng lệnh gõ nhanh (Ctrl/Cmd+K) |
| **`WorkflowStepper`** | Hiển thị tiến trình quy trình |
| **`ApproverSelect`** | Bộ chọn người duyệt — **bắt buộc** dùng thay cho chọn thẳng DocType `User` |
| **`FileUploadField`** | Ô tải tệp — **bắt buộc**, cấm ô gõ đường dẫn `/files/...` |

**Lỗi phân loại giả rỗng (*false-empty*):** khi API hỏng mà màn hình rơi vào nhánh «chưa có dữ liệu», người dùng tin là *kho rỗng* thay vì *hệ thống lỗi*. Đây là loại lỗi được xử lý ở tầng khuôn dùng chung, không xử lý rời rạc từng màn.

**Chính sách ngôn ngữ giao diện:** giao diện phải viết **đầy đủ tiếng Việt** — dịch mọi từ viết tắt tiếng Anh (CAPEX, SLA, KPI, CAPA, RCA, WO, PO, PM, CM, QA…); giữ nguyên QR, PIN và các từ viết tắt quen dùng ở Việt Nam (BHYT, NSNN, KTV…).

---

## Phần 3 — Danh mục chức năng theo module

> Mỗi mục dưới đây trình bày: **Mục tiêu · Người dùng · Chức năng · Mô hình dữ liệu · Quy trình · Giao diện · API · Chỉ số**.

---

### IMM-00 — Dữ liệu nền & Dịch vụ dùng chung · **LIVE ✅**

| Mục | Giá trị |
|---|---|
| Khối | Nền tảng (không thuộc A/B/C/D) |
| Đợt | 1 |
| Mã nguồn | `services/imm00.py` · `api/imm00.py` (117 endpoint) |
| Tài liệu gốc | `docs/imm-00/` (9 file + 12 ADR) |

**Mục tiêu.** IMM-00 không phải module nghiệp vụ mà là **lớp nền tự chứa** mà cả 17 module còn lại phụ thuộc. Nó cung cấp danh mục dữ liệu gốc, dịch vụ dùng chung, cơ chế kiểm toán và phân quyền.

**Chức năng chính.**

| Nhóm | Chức năng |
|---|---|
| Sổ đăng ký thiết bị | Tạo / sửa / xoá / tra cứu thiết bị · máy trạng thái vòng đời 8 trạng thái · dòng thời gian thiết bị · kiểm tra điều kiện đưa vào vận hành |
| Định danh QR | Sinh mã QR nội bộ · giải mã token QR (`/a/:token`) · in nhãn hàng loạt ra PDF · đánh dấu đã in · sinh lại token |
| Dữ liệu gốc | Nhà cung cấp · Vị trí · Phòng ban · Nhóm thiết bị · Mẫu thiết bị · Đơn vị tính + quy đổi |
| Quản trị | Chính sách SLA · Hợp đồng dịch vụ · Yêu cầu hồ sơ bắt buộc |
| Điều chuyển | Tạo / duyệt / từ chối / nhận bàn giao phiếu điều chuyển thiết bị (`AT-.YYYY.-.####`) |
| Kiểm toán | Nhật ký kiểm toán chuỗi băm · xác minh tính toàn vẹn chuỗi |
| Hành động khắc phục | Mở / đóng / liệt kê CAPA (dùng chung cho IMM-09/11/12/16) |
| Sự cố | Tiếp nhận / cập nhật / gửi báo cáo sự cố (dùng chung với IMM-12) |
| Khấu hao | Tính lịch khấu hao · xem trước · sinh lại · chạy đến kỳ · thống kê theo nhóm |
| Lịch & mẫu bảo trì | Lịch PM · mẫu danh mục kiểm tra PM (dùng chung với IMM-08) |
| Yêu cầu thay đổi phần sụn | Tạo / duyệt / chuyển trạng thái phiếu thay đổi firmware |
| Yêu cầu hồ sơ | Tạo / theo dõi yêu cầu bổ sung hồ sơ thiếu |
| Hộp thư duyệt | Tổng hợp mọi việc chờ duyệt của người dùng qua mọi module |
| Chỉ số | Chỉ số thiết bị · chỉ số ngừng hoạt động |

**Mô hình dữ liệu (18 DocType chính do IMM-00 sở hữu).**

`AC Asset` · `AC Asset Category` · `AC Department` · `AC Location` · `AC Supplier` · `AC UOM` · `AC UOM Conversion` · `IMM Device Model` · `IMM Device Spare Part` · `AC Authorized Technician` · `Service Contract` (+ `Service Contract Asset`) · `Required Document Type` · `IMM SLA Policy` · `Asset Lifecycle Event` · `AC Asset Depreciation Schedule` · `AC Asset Downtime Log` · `IMM Audit Trail` · `Asset Transfer` · `AC Mobile Device Token`

**Giao diện — 40 route.**

| Nhóm | Route |
|---|---|
| Thiết bị | `/assets` · `/assets/new` · `/assets/:id` · `/assets/:id/edit` · `/assets/:id/info` · `/assets/labels/print` |
| QR | `/qr-scan` · `/a/:token` |
| Điều chuyển | `/asset-transfers` · `/asset-transfers/new` · `/asset-transfers/:id` |
| Nhà cung cấp | `/suppliers` · `/suppliers/new` · `/suppliers/:id` · `/suppliers/:id/edit` |
| Mẫu thiết bị | `/device-models` · `/device-models/new` · `/device-models/:id` |
| Dữ liệu gốc | `/reference-data` · `/sla-policies` |
| Hợp đồng dịch vụ | `/service-contracts` · `/service-contracts/new` · `/service-contracts/:id` |
| Khấu hao | `/depreciation` |
| Kiểm toán | `/audit-trail` |
| Duyệt | `/approvals/pending` |
| Bảng điều khiển | `/` · `/dashboard` · `/launcher` · `/modules` |

**API.** 117 endpoint tại `api/imm00.py` — tệp API lớn nhất hệ thống. Nhóm tiêu biểu: `list_assets` · `get_asset` · `create_asset` · `update_asset` · `transition_status` · `get_asset_timeline` · `resolve_qr_token` · `print_asset_labels_pdf` · `list_audit_trail` · `verify_chain` · `list_capas` · `open_capa` · `close_capa_record` · `get_pending_approvals_inbox` · `compute_depreciation` · `get_depreciation_schedule`.

**Chỉ số.** Độ phủ nhật ký kiểm toán 100% · độ phủ chính sách SLA 100% · 4 tác vụ định kỳ chạy đủ, 0 lần bỏ lỡ/ngày · chuỗi băm toàn vẹn 100% · cảnh báo hết hạn đăng ký lưu hành phủ 100% thiết bị đang dùng.

---

### IMM-01 — Nhu cầu & Dự toán ngân sách · **LIVE ✅**

| Mục | Giá trị |
|---|---|
| Khối | A. Hoạch định · Đợt 2 |
| Chủ sở hữu | Phó Trưởng phòng Khối 1 · Nhóm Kế hoạch – Tài chính |
| Mã nguồn | `services/imm01.py` · `api/imm01.py` (22 endpoint) |

**Vấn đề giải quyết.** Bệnh viện tiếp nhận đề xuất mua thiết bị qua thư điện tử / văn bản, không có chấm điểm ưu tiên, không tính tổng chi phí sở hữu, không đối chiếu nguồn vốn.

**Mục tiêu.** Chuẩn hoá vòng đời tiếp nhận nhu cầu: đề xuất lâm sàng → chấm điểm đa tiêu chí → dự toán chi đầu tư + chi vận hành 5 năm → tổng hợp Kế hoạch mua sắm được Ban Giám đốc phê duyệt. Chỉ chuyển sang IMM-02 khi Kế hoạch ở trạng thái **Đã duyệt**.

**Người dùng.** Người dùng khoa (Kỹ thuật viên / Điều dưỡng trưởng) · Trưởng khoa · Người rà soát kỹ thuật · Cán bộ Kế hoạch – Tài chính · Cán bộ Tài chính Kế toán · Phó Trưởng phòng Khối 1 · Ban Giám đốc · Quản trị hệ thống.

**Chức năng trong phạm vi.**

- Lập phiếu nhu cầu, đính kèm luận giải lâm sàng bắt buộc.
- Chấm điểm ưu tiên **6 tiêu chí có trọng số** → xếp hạng P1 (≥4,0) / P2 (3,0–3,99) / P3 (2,0–2,99) / P4 (<2,0).
- Dự toán chi đầu tư + chi vận hành theo 5 năm.
- Tổng hợp thành Kế hoạch mua sắm; đặt hạn mức ngân sách; kích hoạt / đóng kế hoạch.
- Dự báo nhu cầu (cấp nhóm thiết bị) — đầu vào cho IMM-15 và IMM-17.
- Bảng điều khiển 6 chỉ số.

**Ngoài phạm vi.** Soạn thông số kỹ thuật chi tiết (→IMM-02) · đánh giá nhà cung cấp và đấu thầu (→IMM-03) · lắp đặt nghiệm thu (→IMM-04) · tích hợp bảo hiểm y tế thời gian thực · đánh giá công nghệ y tế chuyên sâu.

**Mô hình dữ liệu (7).** `IMM Needs Request` · `Needs Priority Scoring` (con) · `Budget Estimate Line` (con) · `IMM Procurement Plan` · `Procurement Plan Line` (con) · `IMM Demand Forecast` · `Forecast Driver` (con).

**Quy trình.**

- *Phiếu nhu cầu* (8 trạng thái): Nháp → Đã gửi → Đang rà soát → Đã xếp ưu tiên → Đã dự toán → Chờ phê duyệt → Đã duyệt / Từ chối.
- *Kế hoạch mua sắm* (4 trạng thái): Nháp → Đã duyệt → Đang hiệu lực → Đã đóng.

**Quy tắc nghiệp vụ chốt (11 quy tắc BR-01-01…11).** Bắt buộc có khoa đề xuất + luận giải lâm sàng · bắt buộc tỷ lệ sử dụng 12 tháng khi loại đề xuất là *Thay thế* hoặc *Nâng cấp* · một thiết bị chỉ có một phiếu thay thế đang hiệu lực · chấm đủ 6/6 tiêu chí · dự toán chi đầu tư > 0 và chi vận hành đủ 5 năm · năm mục tiêu ≥ năm hiện tại · sai số điểm tổng < 0,01 · phiếu tồn > 30 ngày sinh thông báo leo thang tới `Needs Manager` (một bản tóm tắt/người nhận/ngày).

**Giao diện — 5 route.** `/needs-requests` · `/needs-requests/new` · `/needs-requests/:id` · `/procurement-plans` · `/procurement-plans/:id`.

**API tiêu biểu.** `list_needs_requests` · `create_needs_request` · `score_needs_request` · `submit_budget_estimate` · `approve_needs_request` · `reject_needs_request` · `get_allowed_transitions` · `create_procurement_plan` · `set_budget_envelope` · `approve_plan` · `activate_plan` · `roll_into_plan` · `get_demand_forecast` · `dashboard_kpis`.

**Chỉ số mục tiêu.** Thời gian từ tiếp nhận → duyệt < 45 ngày · tỷ lệ phiếu đúng thủ tục ≥ 95% · sử dụng hạn mức ngân sách 70–95% · độ phủ tín hiệu thay thế ≥ 80% · độ chính xác dự báo ≥ 85%.

---

### IMM-02 — Đặc tả kỹ thuật & Phân tích thị trường · **LIVE ✅**

| Mục | Giá trị |
|---|---|
| Khối | A. Hoạch định · Đợt 2 |
| Mã nguồn | `services/imm02.py` · `api/imm02.py` (16 endpoint) |

**Mục tiêu.** Là **cổng đặc tả kỹ thuật** giữa IMM-01 và IMM-03. Không có bản đặc tả ở trạng thái **Đã chốt** thì không có đánh giá nhà cung cấp và không có đơn hàng.

**Chức năng trong phạm vi.**

- Tạo bản đặc tả từ dòng Kế hoạch mua sắm (`draft_from_plan`).
- Quản lý danh mục yêu cầu kỹ thuật (nhập tay + nhập hàng loạt từ Excel).
- **Đối chuẩn thị trường** ≥ 3 ứng viên, tính tỷ lệ khớp đặc tả và điểm khuyến nghị.
- **Đánh giá tương thích hạ tầng** 6 lĩnh vực: điện, khí y tế, mạng, không gian, giao diện HIS/PACS/LIS, môi trường.
- **Đánh giá rủi ro phụ thuộc nhà cung cấp** 5 chiều có trọng số: Giao thức 30% · Vật tư tiêu hao 20% · Phần mềm 20% · Phụ tùng 15% · Dịch vụ 15%.
- Phiên bản hoá: Rút hồ sơ + Phát hành lại (nhân bản, tăng phiên bản 1.0 → 2.0).
- Chốt đặc tả → kích hoạt IMM-03.

**Ngoài phạm vi.** Soạn hồ sơ mời thầu hoàn chỉnh (→IMM-03) · đánh giá nhà cung cấp cụ thể (→IMM-03) · lập kế hoạch mua sắm (→IMM-01).

**Mô hình dữ liệu (8).** `IMM Tech Spec` · `Tech Spec Requirement` (con) · `Tech Spec Document` (con) · `IMM Market Benchmark` · `Benchmark Candidate` (con) · `Infra Compatibility Item` (con) · `IMM Lock In Risk Assessment` · `Lock In Risk Item` (con).

**Quy trình (7 trạng thái).** Nháp → Đang rà soát → Đã đối chuẩn → Đã đánh giá rủi ro → Chờ phê duyệt → Đã chốt / Đã rút.

**Quy tắc nghiệp vụ chốt (10 quy tắc).** Một dòng kế hoạch ứng một bản đặc tả hiệu lực · ≥ 8 yêu cầu bắt buộc trước khi rà soát · yêu cầu bắt buộc phải có phương pháp kiểm chứng · ≥ 3 ứng viên đối chuẩn · đánh giá đủ 6/6 lĩnh vực hạ tầng · điểm phụ thuộc ≤ ngưỡng hoặc phải có kế hoạch giảm thiểu · bản đã chốt không sửa được, phải rút rồi phát hành lại · nút thao tác hiển thị theo cờ máy chủ `can_lock` / `can_withdraw` / `can_reissue`.

**Bảo mật dữ liệu.** Trường `lock_in_score` và `mitigation_plan` đặt ở `permlevel=1` — chỉ nhóm quản lý rủi ro, Ban Giám đốc Khối 1 và quản trị viên xem được.

**Giao diện — 3 route.** `/tech-specs` · `/tech-specs/new` · `/tech-specs/:id`.

**API tiêu biểu.** `list_tech_specs` · `draft_from_plan` · `add_requirement` · `bulk_import_requirements` · `submit_benchmark` · `submit_lock_in_assessment` · `lock_spec` · `withdraw_spec` · `reissue_spec` · `transition_workflow` · `dashboard_kpis`.

**Chỉ số.** *(Cần workshop BA để chốt baseline — không tự sinh số liệu.)*

---

### IMM-03 — Đánh giá nhà cung cấp & Quyết định mua sắm · **LIVE ✅**

| Mục | Giá trị |
|---|---|
| Khối | A. Hoạch định · Đợt 2 |
| Mã nguồn | `services/imm03.py` · `api/imm03.py` (25 endpoint) + `api/purchase.py` (13 endpoint) |

**Mục tiêu.** Chuẩn hoá chuỗi từ bản đặc tả đã chốt đến khi phát hành đơn hàng: chấm điểm nhà cung cấp đa tiêu chí, quản lý **Danh sách nhà cung cấp được phê duyệt (AVL)** theo nhóm thiết bị, chọn phương thức mua sắm hợp pháp, tạo `AC Purchase` có liên kết ngược tới quyết định mua sắm.

**Chức năng trong phạm vi.**

- Hồ sơ nhà cung cấp + chứng chỉ (`add_vendor_cert`).
- Đợt đánh giá: thêm ứng viên → nhận báo giá → chấm điểm đa tiêu chí (kỹ thuật / thương mại / tài chính / tuân thủ).
- Danh sách nhà cung cấp được phê duyệt: tạo · duyệt · đặt có điều kiện · tạm đình chỉ · tự hết hạn theo lịch.
- Quyết định mua sắm: chọn phương thức → đàm phán → đề xuất trúng → phê duyệt → trao thầu → ghi hợp đồng → phát hành đơn hàng.
- **Đơn mua hàng** (`AC Purchase`): tạo · sửa · gửi duyệt · huỷ · đánh dấu đã nhận · sinh phiếu nhập kho.
- Phiếu đánh giá nhà cung cấp định kỳ (`IMM Vendor Scorecard`) + kiểm toán nhà cung cấp.

**Ngoài phạm vi.** Hệ thống đấu thầu điện tử (chỉ tải kết quả lên) · quản lý toàn văn hợp đồng · thanh toán.

**Mô hình dữ liệu (12).** `IMM Vendor Evaluation` · `Vendor Eval Candidate` (con) · `Vendor Eval Criterion` (con) · `Vendor Quotation Line` (con) · `IMM AVL Entry` · `IMM Procurement Decision` · `IMM Vendor Scorecard` · `Scorecard Kpi Row` (con) · `IMM Supplier Audit` · `Vendor Cert` (con) · `AC Purchase` · `AC Purchase Item` / `AC Purchase Device Item` (con).

**Quy trình.** 3 máy trạng thái: Đánh giá (5) · Danh sách phê duyệt (5) · Quyết định (9).

**Quy tắc nghiệp vụ đáng chú ý.**

- **Không tự động trao thầu khi điểm đỉnh hoà** — phải có quyết định của người duyệt.
- Chỉ mục AVL "còn hiệu lực" xác định qua **một nguồn duy nhất** `_avl_is_live`.
- Chuyển trạng thái phải đi qua `apply_workflow` — cấm gán thẳng `workflow_state`.
- Toàn bộ 6 endpoint đổi trạng thái đơn mua hàng gate bằng capability `purchase.*` (bịt lỗ mọi người đăng nhập đều tự gửi duyệt / nhận hàng / huỷ).

**Giao diện — 14 route.** `/vendor-profiles` · `/vendor-profiles/:id` · `/vendor-evaluations` · `/vendor-evaluations/:id` · `/approved-vendors` · `/procurement-decisions` · `/procurement-decisions/:id` · `/purchases` · `/purchases/new` · `/purchases/:name` · `/purchases/:name/edit` (+ 4 bí danh `/purchase-orders/*`).

**API tiêu biểu.** `list_vendor_profiles` · `create_evaluation` · `add_candidate` · `submit_quotations` · `score_evaluation` · `create_avl_entry` · `approve_avl` · `set_avl_conditional` · `suspend_avl` · `create_decision` · `award_decision` · `record_contract` · `get_vendor_scorecard` · `create_purchase` · `submit_purchase` · `mark_received` · `create_receipt_movement`.

**Chỉ số mục tiêu.** Thời gian từ nháp đánh giá → trao thầu < 60 ngày · ≥ 90% đơn hàng đi qua nhà cung cấp trong danh sách phê duyệt · điểm trung bình nhà cung cấp trúng ≥ 4,0/5 · độ phủ danh sách phê duyệt theo nhóm ≥ 80% · tỷ lệ hoàn thành kiểm toán ≥ 95%.

---

### IMM-04 — Lắp đặt & Nghiệm thu đưa vào sử dụng · **LIVE ✅**

| Mục | Giá trị |
|---|---|
| Khối | B. Triển khai · Đợt 1 |
| Mã nguồn | `services/imm04.py` · `api/imm04.py` (34 endpoint) |

**Mục tiêu.** Là **cổng triển khai bắt buộc**. Mọi thiết bị từ khi nhận hàng đều phải đi qua đường ống 11 bước. **Không có phiếu ở trạng thái «Cho phép sử dụng» thì thiết bị không được dùng và không tồn tại bản ghi thiết bị trên hệ thống** — bảo đảm truy vết 100% từ ngày đầu.

**Người dùng.** Kỹ thuật viên HTM · Kỹ sư Y sinh · Kỹ sư nhà cung cấp · Cán bộ Quản lý chất lượng · Trưởng phân xưởng · Phó Trưởng Khối 2 · Quản trị hệ thống · Kế toán tài sản · Kiểm toán viên.

**Chức năng trong phạm vi.**

- Đường ống 11 trạng thái, 22 chuyển tiếp, 6 cổng kiểm soát (G01–G06), 7 quy tắc kiểm tra.
- Tạo phiếu từ đơn mua hàng (`create_from_purchase`) hoặc thủ công.
- Kiểm tra hồ sơ đầu vào (cổng G-2 truy vấn sang IMM-05).
- Định danh: gán số sê-ri nhà cung cấp (kiểm tra trùng), sinh mã QR nội bộ `BV-{KHOA}-{NĂM}-{SỐ}`.
- Đo kiểm an toàn điện, danh mục kiểm tra ban đầu (`submit_baseline_checklist`).
- Báo cáo và đóng điểm không phù hợp (`report_nonconformance` / `close_nonconformance`).
- Tạm giữ lâm sàng và giải toả (`clear_clinical_hold`), phê duyệt cho phép sử dụng.
- Báo hỏng khi nhận hàng (`report_doa`) → trả nhà cung cấp.
- **Tự động tạo bản ghi thiết bị** khi ký duyệt (`mint_core_asset`) + tự tạo bộ hồ sơ ban đầu sang IMM-05.
- Sinh biên bản bàn giao PDF, nhãn QR.
- Bảng điều khiển + tác vụ cảnh báo phiếu quá hạn 30 ngày.

**Ngoài phạm vi.** Tự tạo lịch bảo trì (sự kiện đã bắn, bộ lắng nghe IMM-08 chưa cài) · mẫu in nhãn QR phía máy chủ · tự phát hiện tạm giữ lâm sàng sau kiểm tra ban đầu.

**Mô hình dữ liệu (5).** `Asset Commissioning` · `Commissioning Checklist` (con) · `Commissioning Document Record` (con) · `Asset QA Non Conformance` · (dùng chung `Asset Transfer`, `Asset Decommission`).

**Quy trình (11 trạng thái).** Nháp → Chờ kiểm hồ sơ → Chờ lắp đặt → Đang lắp đặt → Định danh → Kiểm tra ban đầu → (Không phù hợp ⇄ Kiểm tra lại) → Tạm giữ lâm sàng → **Cho phép sử dụng** / Trả nhà cung cấp.

**Giao diện — 5 route.** `/commissioning` · `/commissioning/new` · `/commissioning/:id` · `/commissioning/:id/nc` · `/commissioning/:id/timeline`.

**API tiêu biểu.** `list_commissioning` · `create_commissioning` · `create_from_purchase` · `transition_state` · `check_sn_unique` · `assign_identification` · `generate_internal_qr` · `submit_baseline_checklist` · `report_nonconformance` · `close_nonconformance` · `clear_clinical_hold` · `approve_clinical_release` · `report_doa` · `submit_commissioning` · `retry_mint_asset` · `generate_handover_pdf` · `get_gate_status` · `get_dashboard_stats`.

**Chỉ số mục tiêu.** Phiếu hoàn thành đúng hạn (≤30 ngày từ ngày tiếp nhận) ≥ 85% · số sê-ri không trùng 100% · đạt kiểm tra ban đầu lần đầu ≥ 90% · thời gian xử lý trung bình ≤ 10 ngày · độ phủ nhật ký kiểm toán 100%.

---

### IMM-05 — Hồ sơ thiết bị · **LIVE ✅**

| Mục | Giá trị |
|---|---|
| Khối | B. Triển khai · Đợt 1 |
| Mã nguồn | `services/imm05.py` · `api/imm05.py` (16 endpoint) |

**Mục tiêu.** Kho hồ sơ tập trung cho toàn bộ tài liệu kỹ thuật, pháp lý, kiểm định và đào tạo gắn với từng thiết bị. Tổ chức theo **từng thiết bị** (per-instance) hoặc **theo mẫu thiết bị** (per-model), có kiểm soát phiên bản, quy trình duyệt, cảnh báo hết hạn tự động và cổng tuân thủ bắt buộc trước khi đưa thiết bị vào vận hành.

**Kết quả đo được kỳ vọng.** 0 hồ sơ thất lạc · 100% cảnh báo hết hạn trước 90 ngày · thời gian tìm tài liệu từ 30 phút xuống dưới 1 phút.

**Chức năng trong phạm vi.**

- Kho hồ sơ hai cấp (theo thiết bị / theo mẫu thiết bị).
- Kiểm soát phiên bản: tự lưu trữ phiên bản cũ khi phiên bản mới có hiệu lực.
- Quy trình duyệt 6 trạng thái, 10 chuyển tiếp.
- Tự nhập hồ sơ từ IMM-04 khi phiếu nghiệm thu được ký.
- **Cảnh báo hết hạn** theo mốc 90 / 60 / 30 / 0 ngày, chống trùng lặp thông báo.
- **Cổng tuân thủ G-2** cho IMM-04 — chặn ký duyệt nếu hồ sơ chưa đủ.
- Kiểm soát mức hiển thị (Công khai / Nội bộ).
- Luồng miễn trừ theo Nghị định 98 (`mark_exempt`).
- Yêu cầu bổ sung hồ sơ thiếu + theo dõi hạn + leo thang.
- Mỗi dòng hồ sơ **phơi tệp thật** (tên tệp, kích thước, đường dẫn, cờ riêng tư) — liên kết mồ côi trả cờ «chưa đính kèm», không phát link chết.

**Ngoài phạm vi.** Hợp đồng nhà cung cấp (→IMM-02) · lịch đào tạo (→IMM-06) · lịch hiệu chuẩn (→IMM-11, chỉ nhận chứng chỉ kết quả) · chữ ký số · tích hợp FHIR/HIS.

**Mô hình dữ liệu (3 + 1).** `Asset Document` · `Document Request` · `Expiry Alert Log` · `Required Document Type` (thuộc IMM-00).

**Quy trình (6 trạng thái).** Nháp → Chờ rà soát → Hiệu lực → (Từ chối) → Lưu trữ / Hết hạn.

**Giao diện — 5 route.** `/documents` · `/documents/new` · `/documents/view/:name` · `/documents/asset/:assetId` · `/documents/requests`.

**API tiêu biểu.** `list_documents` · `create_document` · `submit_for_review` · `approve_document` · `reject_document` · `archive_document` · `get_asset_documents` · `get_expiring_documents` · `get_compliance_by_dept` · `get_document_history` · `create_document_request` · `mark_exempt` · `get_dashboard_stats`.

**Chỉ số mục tiêu.** Thiết bị đủ hồ sơ bắt buộc ≥ 90% · hồ sơ sắp hết hạn được gia hạn ≥ 95% · thời gian từ tải lên → hiệu lực ≤ 3 ngày làm việc · tháo gỡ chặn cổng G-2 trong 5 ngày ≥ 85% · cảnh báo không trùng 100% · **số thiết bị có đăng ký lưu hành Bộ Y tế hết hạn đang khai thác lâm sàng → 0**.

---

### IMM-06 — Đào tạo & Năng lực vận hành · **LIVE ✅**

| Mục | Giá trị |
|---|---|
| Khối | B. Triển khai · Đợt 2 |
| Mã nguồn | `services/imm06.py` · `api/imm06.py` (28 endpoint) |

**Vấn đề giải quyết.** Thiết bị nhóm II/III chỉ được vận hành bởi người có chứng nhận theo Nghị định 98 §35 và khung WHO HTM, nhưng toàn bộ hồ sơ đào tạo đang nằm ngoài hệ thống (Excel, sổ giấy, thư điện tử) — không truy vết, không cảnh báo hết hạn, không chặn được lệnh công việc.

**Mục tiêu.** *"Người dùng đủ năng lực trước khi vận hành, có tái đào tạo định kỳ và kiểm soát quyền sử dụng theo trạng thái năng lực."*

**Chức năng trong phạm vi.**

- Thiết kế chương trình đào tạo (curriculum) theo mẫu thiết bị.
- Tổ chức buổi đào tạo: lên kế hoạch → xác nhận → bắt đầu → ghi danh học viên → hoàn thành → kiểm chứng → đóng.
- Chấm điểm và **cấp năng lực** cho người vận hành.
- Vòng đời năng lực: chờ đánh giá → hiệu lực → sắp hết hạn → hết hạn / tạm đình chỉ / thu hồi; tái chứng nhận.
- **Cổng kiểm tra năng lực** phục vụ IMM-04 (cho phép sử dụng lâm sàng) và IMM-08/09/11/12 (phân công lệnh công việc): `check_user_authorization`, `get_asset_operator_coverage`.
- Báo cáo thiếu hụt năng lực hằng tuần — ma trận khoa phòng × nhóm rủi ro thiết bị.
- 4 tác vụ định kỳ: kiểm tra sắp hết hạn · tự hết hạn · nhắc tái chứng nhận · sinh báo cáo thiếu hụt.

**Ngoài phạm vi.** Hệ thống học trực tuyến (chỉ ghi nhận hoàn thành) · ngân sách đào tạo · đánh giá hiệu suất công việc tổng thể · chữ ký số trên chứng nhận.

**Mô hình dữ liệu (8).** `IMM Training Program` · `IMM Training Session` · `IMM Training Participant` (con) · `IMM Trainer` · `IMM User Competency` · `IMM Competency Gap Report` · `IMM Gap Detail Row` (con) · `IMM Competency Alert Log`.

**Quy trình.** Buổi đào tạo (7 trạng thái) · Năng lực (6 trạng thái).

**Rủi ro đã nhận diện.** Cổng kiểm tra năng lực bị gọi tần suất cao khi phân công lệnh công việc → cần bộ đệm 5 phút · khoa nhỏ thiếu người vận hành dự phòng cho thiết bị nhóm III → cần cơ chế miễn trừ có ghi nhận rủi ro.

**Giao diện — 9 route.** `/imm06/dashboard` · `/imm06/programs` · `/imm06/programs/new` · `/imm06/programs/:name` · `/imm06/sessions` · `/imm06/sessions/new` · `/imm06/sessions/:name` · `/imm06/competencies` · `/imm06/competencies/:name`.

**API tiêu biểu.** `list_programs` · `create_program` · `create_session` · `confirm_session` · `start_session` · `enroll_participants` · `complete_session` · `verify_session` · `close_session` · `signoff_competency` · `recertify_competency` · `suspend_competency` · `revoke_competency` · `restore_competency` · `check_user_authorization` · `get_asset_operator_coverage` · `get_competency_gaps_by_dept` · `get_expiring_competencies`.

---

### IMM-07 — Theo dõi hiệu suất · **PLANNED ⬜**

| Mục | Giá trị |
|---|---|
| Khối | C. Vận hành · Đợt 3 |
| Trạng thái | Chỉ có tài liệu thiết kế — chưa scaffold mã |

**Mục tiêu.** Lớp **đo hiệu suất** của AssetCore. Thu thập tự động sự kiện vòng đời (bảo trì, sửa chữa, hiệu chuẩn, sự cố) từ các module khối C, chuẩn hoá thành chỉ số vận hành, xác minh dữ liệu và phát **tín hiệu thay thế thiết bị** khi hiệu suất suy giảm bền vững.

**Chức năng dự kiến (7 tình huống sử dụng).**

| Mã | Chức năng |
|---|---|
| UC-07-01 | Tổng hợp ảnh chụp chỉ số theo chu kỳ (ngày / tuần / tháng / quý) |
| UC-07-02 | Xác minh 4 mắt và đóng kỳ chỉ số |
| UC-07-03 | Xem buồng lái hiệu suất |
| UC-07-04 | Phát hiện tín hiệu thay thế (ví dụ: thời gian giữa hai lần hỏng giảm > 30% qua 3 chu kỳ liên tiếp) |
| UC-07-05 | Xử lý / đóng tín hiệu |
| UC-07-06 | Xuất báo cáo định kỳ có ký số |
| UC-07-07 | Truy ngược từ chỉ số về sự kiện nguồn |

**Danh mục chỉ số dự kiến.** Khả dụng (availability) · hiệu suất khai thác (utilization) · thời gian ngừng (downtime) · thời gian giữa hai lần hỏng (MTBF) · thời gian sửa chữa trung bình (MTTR) · tỷ lệ tuân thủ bảo trì định kỳ.

**Phụ thuộc đầu vào.** IMM-04 (mốc chuẩn) · IMM-08 · IMM-09 · IMM-11 · IMM-12 · IMM-15.
**Cung cấp cho.** IMM-10 · IMM-13 · IMM-16 · IMM-17.

**Ngoài phạm vi.** Mô hình học máy dự đoán (→IMM-17) · thu hồi/FSCA (→IMM-10) · quyết định giải nhiệm cuối (→IMM-13/14; IMM-07 chỉ phát tín hiệu).

---

### IMM-08 — Bảo trì định kỳ (PM) · **LIVE ✅**

| Mục | Giá trị |
|---|---|
| Khối | C. Vận hành · Đợt 1 |
| Mã nguồn | `services/imm08.py` · `api/imm08.py` (26 endpoint) |

**Vấn đề giải quyết.** Lịch bảo trì quản lý bằng Excel và sổ giấy → thiết bị bị bỏ sót bảo trì, không có nhật ký kiểm toán đầy đủ.

**Mục tiêu.** Tự động hoá toàn bộ vòng đời bảo trì định kỳ: tạo lịch khi nghiệm thu → tác vụ hằng ngày sinh lệnh bảo trì đúng hạn → kỹ thuật viên điền danh mục kiểm tra chuẩn hoá → cập nhật ngày bảo trì kế tiếp → phát sinh lệnh sửa chữa khi phát hiện lỗi. Đích: tỷ lệ tuân thủ ≥ 90%, **0 thiết bị bỏ sót lịch**.

**Chức năng trong phạm vi.**

- Tự tạo lịch bảo trì khi phiếu nghiệm thu IMM-04 được ký.
- Mẫu danh mục kiểm tra theo nhóm thiết bị × loại bảo trì, có phiên bản và phê duyệt (`approve_pm_template`, `version_pm_template`, `apply_pm_template_to_category`).
- Tác vụ hằng ngày: sinh lệnh bảo trì, đánh dấu quá hạn, gửi thư leo thang.
- Kỹ thuật viên điền danh mục kiểm tra (**Đạt / Lỗi nhẹ / Lỗi nặng / Không áp dụng**), đính kèm ảnh, ký nộp.
- **Lỗi nặng → thiết bị chuyển Ngừng sử dụng + tự sinh lệnh sửa chữa IMM-09.**
- Nhật ký công việc bất biến (`PM Task Log`).
- Bảng điều khiển chỉ số + lịch dạng lịch tháng.

**Ngoài phạm vi.** Lệnh hiệu chuẩn (→IMM-11) · quy trình yêu cầu phụ tùng (→IMM-15) · hàng đợi ngoại tuyến trên di động · tính ngày đến hạn theo lịch nghỉ lễ · chứng chỉ hoàn thành có chữ ký số.

**Mô hình dữ liệu (6).** `PM Schedule` · `PM Checklist Template` · `PM Checklist Item` (con) · `PM Work Order` · `PM Checklist Result` (con) · `PM Task Log`.

**Quy trình (7 trạng thái).** Mở → Đang thực hiện → Hoàn thành; nhánh Chờ – thiết bị bận · Quá hạn · Dừng – hỏng nặng · Huỷ.

**Giao diện — 8 route.** `/pm/dashboard` · `/pm/calendar` · `/pm/work-orders` · `/pm/work-orders/new` · `/pm/work-orders/:id` · `/pm/schedules` · `/pm/templates` (+ `/pm` chuyển hướng).

**API tiêu biểu.** `list_pm_work_orders` · `create_pm_work_order` · `assign_technician` · `attach_pm_checklist_photo` · `submit_pm_result` · `report_major_failure` · `reschedule_pm` · `get_pm_calendar` · `get_pm_dashboard_stats` · `get_asset_pm_history` · `get_due_pm_schedules` · `create_pm_template` · `approve_pm_template` · `version_pm_template` · `apply_pm_template_to_category`.

**Chỉ số mục tiêu.** Tỷ lệ tuân thủ bảo trì ≥ 90% (nền: ~60% khi làm Excel) · lệnh quá hạn ≤ 5% · trễ trung bình ≤ 2 ngày · độ phủ nhật ký công việc 100% · 0 lệnh trùng do tác vụ tự động.

---

### IMM-09 — Sửa chữa (CM) · **LIVE ✅** *(module tham chiếu)*

| Mục | Giá trị |
|---|---|
| Khối | C. Vận hành · Đợt 1 |
| Mã nguồn | `services/imm09.py` · `api/imm09.py` (14 endpoint) |
| Ghi chú | Được đánh dấu **module tham chiếu** — tài liệu và mã của module này là chuẩn mẫu cho các module khác |

**Vấn đề giải quyết.** Sửa chữa xử lý qua điện thoại / thư điện tử, không có hồ sơ chuẩn — không biết ai đang xử lý, vật tư xuất không có chứng từ, không đo được thời gian sửa chữa trung bình.

**Mục tiêu.** MTTR thiết bị nhóm III khẩn cấp ≤ 4 giờ, tuân thủ SLA ≥ 90%.

**Chức năng trong phạm vi.**

- Tiếp nhận từ **báo cáo sự cố (IMM-12)** hoặc **lệnh bảo trì dừng do hỏng nặng (IMM-08)** — bắt buộc có nguồn.
- Phân công kỹ thuật viên · ghi chẩn đoán · bắt đầu sửa.
- **Yêu cầu và xuất vật tư có chứng từ kế toán** (gắn `stock_entry_ref`).
- Danh mục kiểm tra nghiệm thu — **bắt buộc 100% Đạt** trước khi hoàn thành.
- Kết luận «Không sửa được» → thiết bị Ngừng sử dụng → chuyển IMM-13/14.
- Đo MTTR theo ma trận `nhóm rủi ro × mức ưu tiên`; theo dõi vi phạm SLA.
- Phát hiện hỏng lặp (`is_repeat_failure`) → kích hoạt hành động khắc phục IMM-12.
- **Yêu cầu thay đổi phần sụn (Firmware Change Request)** — máy trạng thái riêng, duyệt theo capability `firmware.approve`.
- Tác vụ: kiểm tra vi phạm SLA hằng giờ · quá hạn hằng ngày · tổng hợp MTTR hằng tháng.

**Ngoài phạm vi.** Mua vật tư khẩn cấp · gửi thiết bị ra ngoài sửa · ứng dụng di động gốc · bảo trì dự đoán.

**Mô hình dữ liệu (4).** `Asset Repair` (có ký duyệt) · `Spare Parts Used` (con) · `Repair Checklist` (con) · `Firmware Change Request` (có ký duyệt).

**Quy trình (9 trạng thái).** Mở → Đã phân công → Đang chẩn đoán → (Chờ phụ tùng) → Đang sửa → Chờ nghiệm thu → Hoàn thành / Không sửa được / Huỷ.

**Giao diện — 10 route.** `/cm/dashboard` · `/cm/create` · `/cm/work-orders` · `/cm/work-orders/:id` · `/cm/work-orders/:id/diagnose` · `/cm/work-orders/:id/parts` · `/cm/work-orders/:id/checklist` · `/cm/firmware` · `/cm/firmware/:id` · `/cm/mttr`.

**API tiêu biểu.** `list_repair_work_orders` · `create_repair_work_order` · `assign_technician` · `submit_diagnosis` · `start_repair` · `request_spare_parts` · `attach_repair_checklist_photo` · `confirm_inspection` · `close_work_order` · `search_spare_parts` · `get_repair_kpis` · `get_mttr_report` · `get_asset_repair_history`.

**Chỉ số mục tiêu.** MTTR nhóm III khẩn cấp ≤ 4 giờ (nền ~12 giờ) · tuân thủ SLA ≥ 90% · sửa được ngay lần đầu ≥ 85% · tồn đọng ≤ 15 lệnh/cơ sở · tỷ lệ hỏng lặp ≤ 10%.

---

### IMM-10 — Hậu kiểm & Thu hồi (PMS / Recall) · **PLANNED ⬜**

| Mục | Giá trị |
|---|---|
| Khối | C. Vận hành · Đợt 3 |
| Bị chặn bởi | IMM-16 phải sẵn sàng trước |
| Mã nguồn hiện có | `api/imm10.py` — **1 endpoint** `check_asset_recall` (điểm móc nối) |

**Mục tiêu.** Biến hậu kiểm thành **vòng lặp khép kín**: mọi cảnh báo an toàn (từ nhà cung cấp / cơ quan quản lý / nội bộ) được mở thành **Hồ sơ tuân thủ**, hệ thống tự xác định phạm vi (thiết bị / mẫu / lô / số sê-ri), tạo hàng loạt lệnh công việc thu hồi, đếm ngược **hạn công bố 48 giờ** theo Nghị định 98, và đóng hồ sơ khi 100% thiết bị đã xử lý.

**Chức năng dự kiến (12 tình huống sử dụng).**

| Mã | Chức năng |
|---|---|
| UC-10-01 | Mở hồ sơ tuân thủ từ thông báo thu hồi của nhà cung cấp |
| UC-10-02 | Mở hồ sơ từ thông báo an toàn hiện trường của cơ quan quản lý |
| UC-10-03 | Mở hồ sơ từ tín hiệu hậu kiểm nội bộ (hỏng mãn tính) |
| UC-10-04 | Tự xác định phạm vi ảnh hưởng |
| UC-10-05 | Công bố tới Bộ Y tế trong 48 giờ |
| UC-10-06 | Tạo hàng loạt lệnh công việc thu hồi |
| UC-10-07 | Đưa thiết bị khỏi sử dụng tại khoa |
| UC-10-08 | Đóng hồ sơ tuân thủ |
| UC-10-09 | Theo dõi hành động khắc phục xuyên module |
| UC-10-10 | Kiểm tra hiệu quả 30/60/90 ngày |
| UC-10-11 | Sinh mục cho họp xem xét lãnh đạo |
| UC-10-12 | Xem bảng điều khiển tuân thủ hậu kiểm |

**Mô hình dữ liệu dự kiến.** `IMM Recall Notice` (đã có thư mục DocType) + Hồ sơ tuân thủ `[ROADMAP]`.

**Nguyên tắc triển khai.** IMM-10 **không tự định nghĩa quy tắc tuân thủ riêng** — nó đăng ký quy tắc chuyên biệt cho hậu kiểm vào bộ máy quy tắc của IMM-16.

**Chỉ số mục tiêu.** Công bố đúng hạn 48 giờ ≥ 95% · thời gian hoàn tất thu hồi (trung vị) ≤ 30 ngày.

---

### IMM-11 — Hiệu chuẩn · **LIVE ✅**

| Mục | Giá trị |
|---|---|
| Khối | C. Vận hành · Đợt 1 |
| Mã nguồn | `services/imm11.py` · `api/imm11.py` (19 endpoint) |

**Vấn đề giải quyết.** Bệnh viện không theo dõi được trạng thái hiệu chuẩn thiết bị đo lường y tế → sử dụng thiết bị ngoài dung sai mà không biết.

**Mục tiêu.** **Không thiết bị nào không đạt hiệu chuẩn mà vẫn tiếp tục dùng trên bệnh nhân.**

**Chức năng trong phạm vi.**

- Tự lập lịch hiệu chuẩn từ phiếu nghiệm thu IMM-04.
- **Tuyến bên ngoài** (phòng kiểm định ISO/IEC 17025): bàn giao (`send_to_lab`) → nhận chứng chỉ (`receive_certificate`) → nhập số liệu đo.
- **Tuyến nội bộ**: kỹ thuật viên tự hiệu chuẩn với chuẩn tham chiếu.
- Nhập số đo (`add_measurement`) → **tự tính Đạt / Không đạt theo dung sai**.
- **Không đạt → bắt buộc mở hành động khắc phục + rà soát hồi tố (lookback)** các kết quả đo đã dùng trên bệnh nhân.
- Tác vụ: tạo phiếu 30 ngày trước hạn · cảnh báo quá hạn · dừng lịch khi thiết bị đã giải nhiệm.
- Bảng điều khiển tuân thủ + chỉ số.

**Ngoài phạm vi.** Tích hợp API tự động với phòng kiểm định ngoài · nhận dạng ký tự chứng chỉ PDF · danh mục chuẩn tham chiếu · công nhận lẫn nhau xuyên biên giới.

**Mô hình dữ liệu (3).** `IMM Calibration Schedule` · `IMM Asset Calibration` · `IMM Calibration Measurement` (con).

**Quy trình (8 trạng thái).** Đã lên lịch → Đang thực hiện → Đã gửi phòng kiểm định → Đã nhận chứng chỉ → **Đạt / Không đạt / Đạt có điều kiện** / Huỷ.

**Giao diện — 5 route.** `/calibration/dashboard` · `/calibration` · `/calibration/new` · `/calibration/schedules` · `/calibration/:id`.

**API tiêu biểu.** `list_calibrations` · `create_calibration` · `reschedule_calibration` · `send_to_lab` · `receive_certificate` · `add_measurement` · `submit_calibration` · `cancel_calibration` · `get_due_calibrations` · `get_calibration_kpis` · `get_calibration_dashboard` · `get_asset_calibration_history` · `list_calibration_schedules`.

**Chỉ số mục tiêu.** Tuân thủ hiệu chuẩn ≥ 95% · tỷ lệ ngoài dung sai < 5% · đóng hành động khắc phục trong 30 ngày ≥ 90% · độ phủ chứng chỉ 100% · thời gian trung bình gửi → nhận chứng chỉ ≤ 14 ngày.

---

### IMM-12 — Sự cố & Phân tích nguyên nhân gốc · **LIVE ✅**

| Mục | Giá trị |
|---|---|
| Khối | C. Vận hành · Đợt 1 |
| Mã nguồn | `services/imm12.py` · `api/imm12.py` (21 endpoint) |

**Vấn đề giải quyết.** Sự cố thiết bị không được theo dõi có hệ thống → lặp lại mà không phát hiện, thiếu bằng chứng kiểm toán cho cơ quan quản lý.

**Chức năng trong phạm vi.**

- Tiếp nhận báo cáo sự cố từ người dùng khoa phòng hoặc tự động từ IMM-08/09/11.
- Phân loại **mức độ nghiêm trọng**: Thấp / Trung bình / Cao / Nghiêm trọng.
- Quy trình 7 trạng thái, tách rõ **«Tiếp nhận» (phân loại, phân công) ≠ «Bắt đầu xử lý»** — đúng chuẩn tiếp nhận yêu cầu công việc của WHO CMMS.
- Đính kèm ảnh hiện trường.
- **Phân tích nguyên nhân gốc bắt buộc** với mức Cao / Nghiêm trọng / hỏng mãn tính — phương pháp 5-Why hoặc biểu đồ xương cá.
- **Tự tạo hành động khắc phục** khi phân tích hoàn tất (gọi dịch vụ dùng chung IMM-00).
- **Phát hiện hỏng mãn tính**: ≥ 3 sự cố cùng mã lỗi trong cửa sổ trượt 90 ngày — tác vụ chạy hằng ngày.
- Theo dõi vi phạm SLA, ánh xạ mức nghiêm trọng → thang ưu tiên P1–P4.
- Nhật ký kiểm toán mọi chuyển trạng thái.

**Ngoài phạm vi.** Thực hiện sửa chữa (→IMM-09) · báo cáo cảnh giác tự động lên Bộ Y tế (→IMM-10) · sổ đăng ký rủi ro (→IMM-13) · thông báo SMS.

**Mô hình dữ liệu (5).** `Incident Report` · `IMM RCA Record` · `IMM RCA Five Why Step` (con) · `IMM RCA Related Incident` (con) · `Asset QA Non Conformance`.

**Quy trình.** Sự cố (7 trạng thái) · Phân tích nguyên nhân gốc (4 trạng thái).

**Giao diện — 7 route.** `/incidents/dashboard` · `/incidents/list` · `/incidents/new` · `/incidents/:id` · `/rca` · `/rca/:id` (+ `/incidents` chuyển hướng). Ngoài ra `/capas` · `/capas/:id` dùng chung với IMM-16.

**API tiêu biểu.** `report_incident` · `acknowledge_incident` · `start_work` · `resolve_incident` · `close_incident` · `reopen_incident` · `cancel_incident` · `attach_incident_photo` · `request_rca` · `create_rca` · `start_rca` · `submit_rca` · `get_chronic_failures` · `get_asset_incident_history` · `get_incident_stats` · `get_dashboard`.

**Chỉ số mục tiêu.** Thời gian xử lý sự cố giảm theo quý · phân tích nguyên nhân gốc đúng hạn ≥ 95% · đóng hành động khắc phục đúng hạn ≥ 90% · số nhóm hỏng mãn tính giảm theo quý · sự cố nghiêm trọng/tháng giảm theo quý.

---

### IMM-13 — Ngừng sử dụng & Điều chuyển · **PLANNED ⬜**

| Mục | Giá trị |
|---|---|
| Khối | D. Kết thúc vòng đời · Đợt 3 |
| Trạng thái | Tài liệu thiết kế; **cơ chế điều chuyển đang chạy nằm ở IMM-00** (`Asset Transfer`), khác luồng IMM-13 chưa scaffold |

**Mục tiêu.** Đóng phễu giữa "thiết bị hỏng / dư thừa" và "giải nhiệm": kỹ thuật viên và trưởng khoa nhập đề xuất, hệ thống tính rủi ro tồn dư theo WHO HTM §3.2, ban điều hành duyệt; nếu không còn dùng được trong nội viện thì chuyển sang IMM-14 đóng sổ. **Không thiết bị nào biến mất khỏi sổ đăng ký mà không có chữ ký số và biên bản.**

**Chức năng dự kiến (9 tình huống sử dụng).**

- Đề xuất **đưa khỏi sử dụng** (Đang dùng → Ngừng sử dụng) — bắt buộc có lý do + chữ ký điện tử.
- **Điều chuyển nội viện** (đổi khoa / phòng / vị trí) — cập nhật vị trí thiết bị nguyên tử.
- **Rà soát thay thế** — bảng đối chiếu chi phí sửa chữa với chi phí thay mới và điểm rủi ro.
- **Đánh giá rủi ro tồn dư** theo WHO §3.2 — ma trận rủi ro × khả năng × tác động × biện pháp giảm thiểu.
- **Đề xuất giải nhiệm** — đầu vào cho IMM-14.
- Tác vụ leo thang thiết bị ngừng sử dụng > 30 ngày; kiểm chứng vị trí sau điều chuyển; kiểm toán chuỗi chữ ký.

**Ngoài phạm vi.** Phát hành biên bản đóng sổ và đối soát kế toán (→IMM-14) · thanh lý / hiến tặng / bán (→IMM-14) · mua sắm thay thế (→IMM-01/02/03).

**Nguồn dữ liệu đầu vào.** IMM-08 (phát hiện hết vòng đời khi bảo trì) · IMM-09 (kết luận không sửa được) · IMM-11 (ngoài dung sai không khắc phục được) · IMM-12 (sự cố gây ngừng vĩnh viễn) · IMM-07 (tín hiệu thay thế).

**Ghi chú quan trọng.** IMM-13 là **lớp nghiệp vụ phía trên** máy trạng thái thiết bị của IMM-00 — **không tạo máy trạng thái mới** cho thiết bị.

---

### IMM-14 — Giải nhiệm thiết bị · **PARTIAL 🟡**

| Mục | Giá trị |
|---|---|
| Khối | D. Kết thúc vòng đời · Đợt 3 |
| Mã nguồn | `services/imm14.py` · `api/imm14.py` (**4 endpoint** — MVP đã chốt và code) |

**Mục tiêu.** **Đóng vĩnh viễn vòng đời** thiết bị: phát hành biên bản đóng sổ, đối soát thiết bị – kho – kế toán – hồ sơ, xoá/lưu trữ định danh, xử lý dữ liệu bệnh nhân, cập nhật sổ đăng ký.

**Phân biệt với IMM-13.** IMM-13 = quyết định *ngừng sử dụng / điều chuyển* (vẫn mở khả năng tái sử dụng nội viện). IMM-14 = đóng vĩnh viễn (thanh lý / hiến tặng / bán / đổi cũ lấy mới / lưu trữ cuối).

**Đã hiện thực (MVP).**

- DocType `Asset Decommission` — biên bản giải nhiệm.
- **Cổng chặn**: thiết bị không thể chuyển sang «Đã giải nhiệm» nếu chưa có biên bản được duyệt.
- Danh sách biên bản (`list_decommissions`) — đọc qua DocPerm, bảo toàn bất biến số đếm bằng số dòng, hiển thị họ tên người phụ trách (không lộ địa chỉ thư điện tử).
- Màn hình chi tiết + duyệt: `get_decommission` trả cờ `can_approve` và `approve_blocked_reason` (tiếng Việt) từ **cùng một nguồn đánh giá** mà `approve_decommission` thực thi — nút bấm do máy chủ quyết định.
- Dùng lại `transition_asset_status` của IMM-00 — không viết lại sự kiện vòng đời / kiểm toán / huỷ khấu hao.

**`[ROADMAP]` Đợt 3.** Đối soát kho – kế toán · đóng các lệnh công việc còn mở · làm sạch dữ liệu bệnh nhân · lưu trữ hồ sơ pháp lý · quay lui biên bản · bảng điều khiển kết thúc vòng đời · di trú biên bản cũ.

**Mô hình dữ liệu.** `Asset Decommission`.

**Giao diện — 2 route.** `/decommissions` · `/decommissions/:id`.

**API.** `create_decommission` · `get_decommission` · `approve_decommission` · `list_decommissions`.

---

### IMM-15 — Tồn kho phụ tùng · **LIVE ✅**

| Mục | Giá trị |
|---|---|
| Khối | C. Vận hành · Đợt 2 |
| Mã nguồn | `services/imm15.py` · `api/imm15.py` (24 endpoint) + `services/inventory.py` · `api/inventory.py` (36 endpoint) |

**Vấn đề giải quyết.** Mỗi kỹ sư giữ kho riêng, không truy nguyên được từ phụ tùng → lệnh công việc → thiết bị. Phụ tùng trọng yếu hết khi cần (2–3 lần/tháng). Thời gian máy nằm chờ phụ tùng chiếm **28%** tổng thời gian ngừng. Kiểm kê thủ công sai lệch **> 15%**.

**Chức năng trong phạm vi.**

*Lớp nền kho (LIVE từ đợt 1):*
- Kho hàng · danh mục phụ tùng · tồn kho theo kho · phiếu nhập/xuất/điều chỉnh · đơn vị tính và quy đổi.

*Lớp nghiệp vụ IMM-15:*
- **Cấp phát theo lệnh công việc** — không cấp ngoài lệnh trừ trường hợp khẩn cấp; luồng 6 trạng thái: Yêu cầu → Đã duyệt → Đã soạn hàng → Đã xuất → Đã trả / Huỷ. Xuất/trả **sinh phiếu kho tự động**.
- **Vượt cấp khẩn cấp** — cần hai chữ ký duyệt.
- **Danh sách theo dõi phụ tùng trọng yếu** — ánh xạ thiết bị trọng yếu → phụ tùng + tồn tối thiểu; cảnh báo tức thì khi thủng ngưỡng.
- **Kiểm kê chu kỳ** 4 trạng thái: Đã lên kế hoạch → Đang kiểm → Đã rà soát → Đã ghi sổ. Sai lệch > 5% hoặc > 5 triệu đồng ⇒ **bắt buộc mở hành động khắc phục**.
- **Dự báo nhu cầu cấp phần tử** (phân biệt rõ với dự báo cấp nhóm thiết bị của IMM-01).
- Phân loại ABC/XYZ hằng quý.
- Cảnh báo tồn thấp và lô sắp hết hạn.
- Phụ tùng thay thế tương đương (`IMM Spare Alternative`).

**Ngoài phạm vi.** Quy trình mua sắm (→IMM-03) · lịch bảo trì (→IMM-08) · mô hình dự đoán hỏng hóc (→IMM-17) · kế toán tài chính.

**Mô hình dữ liệu (15).** `AC Warehouse` · `AC Spare Part` · `AC Spare Part Stock` · `AC Stock Movement` (+ `AC Stock Movement Item`) · `IMM Spare Allocation` (+ `IMM Spare Allocation Item`) · `IMM Spare Alternative` · `IMM Spare Batch` · `IMM Critical Spare Watchlist` · `IMM Spare Part Forecast` (+ `IMM Spare Forecast Item`) · `IMM Stock Cycle Count` (+ `IMM Stock Cycle Count Item`, `IMM Cycle Count Item`).

**Giao diện — 16 route.** `/inventory` · `/warehouses` · `/warehouses/:name` · `/spare-parts` · `/spare-parts/:name` · `/stock` · `/stock-movements` · `/stock-movements/new` · `/stock-movements/:name` · `/stock-movements/:name/edit` · `/inventory/uom` · `/inventory/forecasts` · `/inventory/watchlist` · `/inventory/cycle-counts` · `/inventory/cycle-counts/new` · `/inventory/cycle-counts/:name`.

**API tiêu biểu.** `create_allocation` · `approve_allocation` · `issue_allocation` · `return_allocation` · `check_part_availability` · `create_cycle_count` · `submit_cycle_count` · `post_cycle_count` · `recount_cycle_count` · `generate_spare_forecast` · `approve_forecast` · `add_to_watchlist` · `get_critical_watchlist` · `get_low_stock_alerts` · `get_stock_snapshot` · `create_stock_movement` · `submit_stock_movement` · `convert_qty` · `upsert_uom_conversion`.

**Chỉ số mục tiêu.** Vòng quay tồn kho ≥ 4 · số ngày tồn 30–60 ngày (phụ tùng trọng yếu 60–90) · độ chính xác kiểm kê · số lần thủng ngưỡng phụ tùng trọng yếu.

---

### IMM-16 — Giám sát tuân thủ & Hành động khắc phục · **LIVE ✅**

| Mục | Giá trị |
|---|---|
| Khối | C. Vận hành · Đợt 2 |
| Mã nguồn | `services/imm16.py` · `api/imm16.py` (**53 endpoint** — tệp API lớn thứ hai) |

**Mục tiêu.** Là **xương sống tuân thủ và hành động khắc phục** của AssetCore: tổng hợp tín hiệu tuân thủ từ mọi module (IMM-04 → IMM-15), tự phát hiện điểm không phù hợp qua bộ máy quy tắc, quản lý vòng đời hành động khắc phục, sinh phiếu điểm tuân thủ hằng tháng và phục vụ họp xem xét lãnh đạo hằng quý theo ISO 13485 §5.6.

**15 nhóm chức năng trong phạm vi.**

| Mã | Chức năng |
|---|---|
| F-01 | Bộ máy quy tắc tuân thủ (khai báo, có phiên bản, kiểm soát thay đổi) |
| F-02 | Tự đánh giá tuân thủ theo lịch (ghi đè bất biến — chạy lại không sinh trùng) |
| F-03 | Nhập điểm không phù hợp thủ công |
| F-04 | Chu trình kiểm toán nội bộ (Lập kế hoạch → Danh mục kiểm → Phát hiện → Báo cáo → Đóng) |
| F-05 | Vòng đời hành động khắc phục / phòng ngừa |
| F-06 | Phân tích nguyên nhân gốc (dùng lại hạ tầng IMM-12) |
| F-07 | Kiểm tra hiệu quả + mở lại nếu không hiệu quả |
| F-08 | Phiếu điểm tuân thủ hằng tháng (bất biến sau khi công bố) |
| F-09 | Họp xem xét lãnh đạo hằng quý (ISO 13485 §5.6) |
| F-10 | Bản đồ nhiệt tuân thủ (ma trận Module × Khoa phòng) |
| F-11 | **Cổng chặn xuyên module IMM-08/09** — chặn ký lệnh công việc khi thiết bị có hành động khắc phục nghiêm trọng đang mở |
| F-12 | Quy trình miễn trừ (phê duyệt cấp Ban Giám đốc + hạn hiệu lực) |
| F-13 | Nhật ký kiểm toán bắt buộc (chuỗi băm) |
| F-14 | Ma trận leo thang (hành động khắc phục quá hạn → thư theo cấp) |
| F-15 | Thu nhận tín hiệu từ IMM-04/05/06/08/09/10/11/12/15 |

**Ngoài phạm vi.** Hồ sơ tài liệu thiết bị (→IMM-05) · lịch bảo trì/hiệu chuẩn (→IMM-08/11) · thu hồi & cảnh giác (→IMM-10) · kiểm toán phía nhà cung cấp (→IMM-03) · hạ tầng phân tích nguyên nhân gốc (→IMM-12) · phân tích dự đoán (→IMM-17) · chữ ký số pháp lý · nộp hồ sơ cho cơ quan quản lý.

**Mô hình dữ liệu (14).** `IMM Compliance Rule` · `IMM Compliance Finding` · `IMM CAPA Record` (+ `IMM CAPA Action Step`) · `IMM Internal Audit` (+ `IMM Audit Checklist Item`, `Audit Finding`) · `IMM Compliance Scorecard` (+ `IMM Scorecard Department Row`, `IMM Scorecard Module Row`, `Scorecard Kpi Row`) · `IMM Management Review` (+ `IMM MR Attendee`, `IMM MR Output Action`).

**Quy trình.** 4 máy trạng thái: Hành động khắc phục (7) · Điểm không phù hợp (7) · Kiểm toán nội bộ (4) · Họp xem xét lãnh đạo (4).

**Giao diện — 11 route.** `/compliance/rules` · `/compliance/rules/:id` · `/compliance/findings` · `/compliance/findings/:id` · `/compliance/audits` · `/compliance/audits/:id` · `/compliance/scorecard` · `/compliance/mr` · `/compliance/mr/:id` · `/compliance/heatmap` (+ `/capas`, `/capas/:id` dùng chung).

**API tiêu biểu.** `create_rule` · `run_compliance_evaluation` · `list_findings` · `confirm_finding` · `mark_false_positive` · `waive_finding` · `link_to_capa` · `create_capa_from_finding` · `advance_capa_state` · `perform_effectiveness_check` · `reopen_capa` · `create_audit` · `start_audit` · `complete_audit_checklist` · `close_audit` · `generate_scorecard` · `publish_scorecard` · `create_management_review` · `advance_mr_state` · `finalize_management_review` · `get_compliance_heatmap` · `get_capa_aging` · `get_overdue_actions` · `check_asset_compliance_status`.

**Chỉ số mục tiêu.** Điểm tuân thủ tổng thể ≥ 90% · tỷ lệ hành động khắc phục quá hạn ≤ 5% · họp xem xét lãnh đạo đúng chu kỳ hằng quý.

---

### IMM-17 — Phân tích dự đoán · **PLANNED ⬜**

| Mục | Giá trị |
|---|---|
| Khối | C. Vận hành · Đợt 3 |
| Điều kiện kích hoạt | Cần lớp dữ liệu IMM-07/08/09/11/12 ổn định + **≥ 12 tháng lịch sử vận hành** |

**Mục tiêu.** Tạo lớp phân tích dự đoán trên kho dữ liệu vận hành để dự báo hỏng hóc, đề xuất chu kỳ bảo trì tối ưu, tối ưu hoá phụ tùng và phát hiện tín hiệu thay thế sớm — biến thông tin thành hành động qua cảnh báo, tạo lệnh công việc tự động và mô phỏng "nếu – thì".

**Yêu cầu chức năng dự kiến.**

| Mã | Yêu cầu | Mức |
|---|---|---|
| FR-17-01 | Tổng hợp đặc trưng từ sự kiện vòng đời + lịch sử lệnh công việc | Bắt buộc |
| FR-17-02 | Sinh bản ghi dự đoán theo thiết bị / kỳ chạy | Bắt buộc |
| FR-17-03 | Phát tín hiệu thay thế qua sự kiện vòng đời | Bắt buộc |
| FR-17-04 | Buồng lái hiển thị N thiết bị rủi ro cao nhất, lọc theo khoa / loại | Bắt buộc |
| FR-17-05 | Hành động: tạo lệnh bảo trì theo dự đoán | Nên có |
| FR-17-06 | Hành động: tạo báo cáo sự cố nếu mức nghiêm trọng cao | Nên có |
| FR-17-07 | Mô phỏng: đổi chu kỳ bảo trì → ước lượng xác suất hỏng | Nên có |
| FR-17-08 | Quản trị phiên bản mô hình + ảnh chụp tập huấn luyện | Bắt buộc |
| FR-17-09 | Nhật ký kiểm toán mọi lần suy luận | Bắt buộc |
| FR-17-10 | Tích hợp dịch vụ học máy bên ngoài | Có thể (cuối đợt 3) |

**Ngoài phạm vi.** Dữ liệu cảm biến thời gian thực (cần cổng IoT) · học sâu (đợt đầu chỉ dùng thống kê / học máy cổ điển) · học liên kết đa cơ sở · mô phỏng ngân sách.

**Nguyên tắc.** IMM-17 **không tạo trạng thái mới** trên thiết bị — chỉ *đề xuất* hành động cho các module xuôi dòng.

---

## Phần 4 — Ma trận tổng hợp

### 4.1. Module × Mô hình dữ liệu × API × Giao diện

| Module | DocType | Endpoint | Route | Workflow | Trạng thái |
|---|---:|---:|---:|---:|---|
| IMM-00 Dữ liệu nền | 18 | 117 | 40 | 1 | LIVE ✅ |
| IMM-01 Nhu cầu | 7 | 22 | 5 | 2 | LIVE ✅ |
| IMM-02 Đặc tả | 8 | 16 | 3 | 1 | LIVE ✅ |
| IMM-03 Mua sắm | 12 | 38¹ | 14 | 3 | LIVE ✅ |
| IMM-04 Lắp đặt | 5 | 34 | 5 | 1 | LIVE ✅ |
| IMM-05 Hồ sơ | 3 | 16 | 5 | 1 | LIVE ✅ |
| IMM-06 Đào tạo | 8 | 28 | 9 | 2 | LIVE ✅ |
| IMM-07 Hiệu suất | 0 | 0 | 0 | 0 | PLANNED ⬜ |
| IMM-08 Bảo trì định kỳ | 6 | 26 | 8 | 1 | LIVE ✅ |
| IMM-09 Sửa chữa | 4 | 14 | 10 | 1 | LIVE ✅ |
| IMM-10 Hậu kiểm | 1 | 1 | 0 | 0 | PLANNED ⬜ |
| IMM-11 Hiệu chuẩn | 3 | 19 | 5 | 1 | LIVE ✅ |
| IMM-12 Sự cố | 5 | 21 | 7 | 2 | LIVE ✅ |
| IMM-13 Ngừng sử dụng | 0² | 0² | 0² | 0 | PLANNED ⬜ |
| IMM-14 Giải nhiệm | 1 | 4 | 2 | 0 | PARTIAL 🟡 |
| IMM-15 Tồn kho | 15 | 60³ | 16 | 2 | LIVE ✅ |
| IMM-16 Tuân thủ | 14 | 53 | 11 | 4 | LIVE ✅ |
| IMM-17 Dự đoán | 0 | 0 | 0 | 0 | PLANNED ⬜ |
| Xác thực & hệ thống⁴ | 0 | 58 | 12 | 0 | LIVE ✅ |
| **Tổng** | **110** | **527** | **148** | **22** | |

¹ 25 (`imm03.py`) + 13 (`purchase.py`) · ² điều chuyển thực tế nằm ở IMM-00 (`Asset Transfer`) · ³ 24 (`imm15.py`) + 36 (`inventory.py`) · ⁴ `user.py` 15 · `auth.py` 9 · `layout.py` 7 · `openapi.py` 11 · `import_data.py` 6 · `dashboard.py` 4 · `notifications.py` 3 · `files.py` 1 · `connections.py` 1 · `session_guard.py` 1

### 4.2. Vai trò × Module

| Vai trò | Module chính | Phạm vi tiêu biểu |
|---|---|---|
| `AssetCore Super Admin` | Tất cả | Toàn quyền, vượt cấp mọi cổng |
| `AssetCore System User` | Tất cả | Đăng nhập, bảng điều khiển, đọc dữ liệu dùng chung |
| `AssetCore Auditor` | Tất cả | Chỉ đọc + nhật ký kiểm toán |
| `Vendor Engineer` | IMM-04, IMM-09 | Chỉ thiết bị/lệnh được phân công |
| `Data Manager` / `Data User` | IMM-00 | Dữ liệu gốc, mẫu thiết bị, SLA |
| `Needs Manager` / `Needs User` | IMM-01 | Phiếu nhu cầu, kế hoạch mua sắm |
| `Spec Manager` / `Spec User` | IMM-02 | Đặc tả, đối chuẩn, rủi ro phụ thuộc |
| `Procurement Manager` / `Procurement User` | IMM-03 | Nhà cung cấp, đánh giá, quyết định, đơn hàng |
| `Commissioning Manager` / `Commissioning User` | IMM-04, IMM-14 | Nghiệm thu, điều chuyển, giải nhiệm |
| `Document Manager` / `Document User` | IMM-05 | Hồ sơ thiết bị |
| `Training Manager` / `Training User` | IMM-06 | Đào tạo, năng lực |
| `PM Manager` / `PM User` | IMM-08 | Bảo trì định kỳ |
| `Repair Manager` / `Repair User` | IMM-09 | Sửa chữa, thay đổi phần sụn |
| `Calibration Manager` / `Calibration User` | IMM-11 | Hiệu chuẩn |
| `Corrective Manager` / `Corrective User` | IMM-12 | Sự cố, phân tích nguyên nhân gốc |
| `Inventory Manager` / `Inventory User` | IMM-15 | Kho, phụ tùng, kiểm kê |
| `Compliance Manager` / `Compliance User` | IMM-16 | Quy tắc, phát hiện, hành động khắc phục, kiểm toán |

### 4.3. Đồ thị phụ thuộc giữa các module

```
IMM-01 Nhu cầu ──► IMM-02 Đặc tả ──► IMM-03 Mua sắm ──► IMM-04 Lắp đặt
   ▲                                                          │
   │                                                          ├──► IMM-05 Hồ sơ
   │                                                          ├──► IMM-08 Lịch bảo trì
   │                                                          ├──► IMM-11 Lịch hiệu chuẩn
   │                                                          └──► AC Asset (IMM-00)
   │                                                                    │
   │              ┌─────────────────────────────────────────────────────┤
   │              ▼                    ▼                 ▼              ▼
   │        IMM-08 Bảo trì      IMM-09 Sửa chữa   IMM-11 Hiệu chuẩn  IMM-12 Sự cố
   │              │  ▲   hỏng nặng   │   ▲               │              │
   │              └──┼───────────────┘   │  cần hiệu     │ không đạt    │
   │                 │                   │  chuẩn lại    │              │
   │                 │  ┌────────────────┘               ▼              ▼
   │                 │  │                        ┌──────────────────────────┐
   │                 │  │  yêu cầu phụ tùng      │  IMM-16 Tuân thủ & CAPA  │
   │                 └──┼──► IMM-15 Tồn kho ─────►  (cổng chặn ngược 08/09) │
   │                    │                        └──────────┬───────────────┘
   │                    │                                   │
   │              IMM-06 Đào tạo (cổng năng lực cho 04/08/09/11/12)
   │                    │
   │        IMM-07 Hiệu suất ⬜ ──► IMM-17 Dự đoán ⬜
   │                    │
   └────────────────────┴──► IMM-13 Ngừng sử dụng ⬜ ──► IMM-14 Giải nhiệm 🟡
                                          ▲
                              IMM-10 Hậu kiểm ⬜ (thu hồi / FSCA)
```

**Quy tắc gọi chéo module bắt buộc:**

- Nhập thư viện **trong thân hàm** (lazy import), không nhập ở đầu tệp → tránh phụ thuộc vòng làm chết `bench start`.
- Truyền **khoá chính** (chuỗi tên bản ghi), **không truyền đối tượng tài liệu đang mở**.
- Không tự viết lại máy trạng thái thiết bị — luôn gọi `services/imm00.transition_asset_status()`.

### 4.4. Bản đồ giao diện — 148 route

| Nhóm | Số route | Route |
|---|---:|---|
| Xác thực & tài khoản | 8 | `/login` `/register` `/set-password` `/profile` `/unauthorized` `/account/profile` `/account/change-password` `/settings/notifications` |
| Bảng điều khiển | 4 | `/` `/dashboard` `/launcher` `/modules` |
| Thiết bị (IMM-00) | 6 | `/assets` `/assets/new` `/assets/:id` `/assets/:id/edit` `/assets/:id/info` `/assets/labels/print` |
| Quét QR | 2 | `/qr-scan` `/a/:token` |
| Điều chuyển | 3 | `/asset-transfers` `/asset-transfers/new` `/asset-transfers/:id` |
| Dữ liệu gốc | 12 | `/suppliers*` (4) `/device-models*` (3) `/reference-data` `/sla-policies` `/service-contracts*` (3) |
| Khấu hao & kiểm toán | 2 | `/depreciation` `/audit-trail` |
| Hộp thư duyệt | 1 | `/approvals/pending` |
| Nhu cầu (IMM-01) | 5 | `/needs-requests*` (3) `/procurement-plans*` (2) |
| Đặc tả (IMM-02) | 3 | `/tech-specs*` |
| Mua sắm (IMM-03) | 14 | `/vendor-profiles*` (2) `/vendor-evaluations*` (2) `/approved-vendors` `/procurement-decisions*` (2) `/purchases*` (4) `/purchase-orders*` (4, bí danh) |
| Lắp đặt (IMM-04) | 5 | `/commissioning*` |
| Hồ sơ (IMM-05) | 5 | `/documents*` |
| Đào tạo (IMM-06) | 10 | `/imm06/*` |
| Bảo trì định kỳ (IMM-08) | 8 | `/pm/*` |
| Sửa chữa (IMM-09) | 10 | `/cm/*` |
| Hiệu chuẩn (IMM-11) | 5 | `/calibration*` |
| Sự cố & RCA (IMM-12) | 8 | `/incidents*` (5) `/rca*` (2) |
| Hành động khắc phục | 2 | `/capas` `/capas/:id` |
| Giải nhiệm (IMM-14) | 2 | `/decommissions*` |
| Tồn kho (IMM-15) | 16 | `/inventory*` `/warehouses*` `/spare-parts*` `/stock*` `/stock-movements*` |
| Tuân thủ (IMM-16) | 11 | `/compliance/*` |
| Quản trị người dùng | 4 | `/admin/roles` `/user-profiles*` (3) |
| Hệ thống | 2 | `/:pathMatch(.*)*` `/debug/asset-dashboard` |

---

## Phần 5 — Tuân thủ & Truy vết

### 5.1. Khung tham chiếu

| Khung | Áp dụng vào |
|---|---|
| **WHO HTM Series** | Cấu trúc vòng đời 6 giai đoạn · chương trình bảo trì · quản lý tồn kho · giải nhiệm thiết bị (§3.1–§3.8) |
| **Nghị định 98/2021/NĐ-CP** | Đăng ký lưu hành · phân loại A/B/C/D · hồ sơ pháp lý · công bố hậu kiểm 48 giờ · thanh lý |
| **Danh mục GMDN (Quyết định BYT)** | Mã danh pháp thiết bị · phân loại rủi ro |
| **ISO 13485** | §5.6 Xem xét của lãnh đạo · kiểm soát tài liệu · hành động khắc phục và phòng ngừa |
| **ISO/IEC 17025** | Yêu cầu với phòng kiểm định hiệu chuẩn bên ngoài |

### 5.2. Cơ chế truy vết trong hệ thống

| Cơ chế | Bảo đảm |
|---|---|
| `Asset Lifecycle Event` | Mọi biến cố thiết bị đều có bản ghi, gắn với bản ghi nghiệp vụ gốc |
| `IMM Audit Trail` chuỗi băm SHA-256 | Không sửa được lịch sử mà không bị phát hiện |
| `docstatus` + `workflow_state` | Bản ghi đã ký duyệt trở thành bất biến |
| Cổng tuân thủ IMM-16 (F-11) | Chặn ký lệnh công việc khi thiết bị có hành động khắc phục nghiêm trọng đang mở |
| Cổng hồ sơ IMM-05 (G-2) | Chặn nghiệm thu khi hồ sơ chưa đủ |
| Cổng năng lực IMM-06 | Chặn phân công lệnh công việc cho người chưa đủ năng lực |
| Cổng giải nhiệm IMM-14 | Chặn chuyển «Đã giải nhiệm» khi chưa có biên bản duyệt |
| `permission_query_conditions` | Cô lập dữ liệu theo dòng cho kỹ sư nhà cung cấp |

---

## Phần 6 — Khoảng trống & Lưu ý cho BA

Phần này ghi trung thực những chỗ tài liệu và mã **chưa khớp** hoặc **chưa hoàn tất** — để BA không cam kết sai với khách hàng.

### 6.1. Module chưa có mã

| Module | Trạng thái thật | Hệ quả cho BA |
|---|---|---|
| IMM-07 Theo dõi hiệu suất | Chỉ tài liệu | Không cam kết buồng lái hiệu suất và tín hiệu thay thế tự động |
| IMM-10 Hậu kiểm / Thu hồi | Chỉ 1 endpoint móc nối | Không cam kết đếm ngược công bố 48 giờ, tạo hàng loạt lệnh thu hồi |
| IMM-13 Ngừng sử dụng | Chỉ tài liệu | Điều chuyển **đang chạy** ở IMM-00 (`Asset Transfer`); luồng rà soát thay thế / rủi ro tồn dư chưa có |
| IMM-14 Giải nhiệm | MVP (4 endpoint) | Có biên bản + cổng chặn + duyệt; **chưa có** đối soát kho–kế toán, làm sạch dữ liệu bệnh nhân, quay lui |
| IMM-17 Phân tích dự đoán | Chỉ tài liệu | Cần ≥ 12 tháng dữ liệu vận hành trước khi bàn tới |

### 6.2. Sai lệch tên vai trò giữa tài liệu và mã

Tài liệu module IMM-01 → IMM-06 (viết ở Đợt 2) vẫn dùng bộ tên vai trò cũ theo persona:

`IMM Clinical User` · `IMM HTM Engineer` · `IMM Planning Officer` · `IMM Finance Officer` · `IMM Risk Officer` · `IMM Department Head` · `IMM Board Approver` · `IMM System Admin` · `IMM Workshop Lead` · `IMM Training Officer` · `IMM Biomed Technician`

**Các vai trò này KHÔNG tồn tại trong mã.** Bộ vai trò thật là 30 vai trò module-based ở §2.3 (đã thay thế qua bản vá `v3_2.001_module_role_redesign`). Tài liệu IMM-15 và IMM-16 đã cập nhật đúng; IMM-01…IMM-06 chưa.

> ⚠️ **Khi viết tài liệu cho khách hàng: dùng bộ 30 vai trò, không dùng tên persona cũ.**

### 6.3. Chức năng có tài liệu nhưng chưa nối dây

| Nội dung | Trạng thái |
|---|---|
| IMM-04 → IMM-08 tự tạo lịch bảo trì | Sự kiện `fire_release_event` đã bắn, **bộ lắng nghe chưa cài** |
| IMM-03 phiếu điểm nhà cung cấp | Sinh khung rỗng; dữ liệu thật từ IMM-04/09/15/10 chờ Đợt 3 |
| IMM-03 cảnh báo hết hạn danh sách phê duyệt 60/30 ngày | Tự đặt trạng thái Hết hạn đã có; **thư cảnh báo chưa có** |
| IMM-02 chỉ số mục tiêu | Chưa chốt — cần workshop BA |
| IMM-06 chỉ số + ánh xạ tuân thủ | Chuyển sang `_REPORT.md`, chờ workshop BA |
| Chữ ký số / chữ ký điện tử pháp lý | Toàn hệ thống — `[ROADMAP]` |
| Tích hợp FHIR / HIS / PACS / LIS | `[ROADMAP]` — hiện chỉ có OpenAPI |

### 6.3-bis. Liên kết hỏng trong tài liệu module (phát hiện khi lập tài liệu này)

Thư mục `docs/gmdn/` và `docs/WHO/` **đã chuyển vào `docs/architecture/`**, nhưng 5 file README module vẫn trỏ đường dẫn cũ `../gmdn/` và `../WHO/` — bấm vào sẽ 404:

`imm-07/README.md` · `imm-10/README.md` · `imm-13/README.md` · `imm-14/README.md` · `imm-17/README.md`

Đường dẫn đúng hiện tại: `../architecture/WHO/` và `../architecture/gmdn/`.

> Ghi nhận để chủ sở hữu tài liệu module sửa — tài liệu tổng hợp này **không tự sửa file module** (nguyên tắc light-touch: phân vân giữa sửa và báo cáo ⇒ chọn báo cáo).

### 6.4. Câu hỏi mở cần BA chốt

| Mã | Câu hỏi | Module |
|---|---|---|
| OQ-06-01 | Điểm đạt chuẩn cho từng mẫu thiết bị khác nhau theo nhóm rủi ro? | IMM-06 |
| OQ-06-02 | Thời hạn hiệu lực năng lực mặc định theo nhóm thiết bị? | IMM-06 |
| OQ-06-03 | Cấp năng lực theo từng thiết bị hay theo mẫu thiết bị? | IMM-06 |
| OQ-06-04 | Quy tắc ký duyệt khi người dùng thuộc hai khoa? | IMM-06 |
| — | Xoá thiết bị còn ràng buộc: chặn hay hạ liên kết? | IMM-00 |
| — | Chuyển trạng thái có bỏ qua kiểm tra liên kết không liên quan không? | IMM-00 |

### 6.5. Nguyên tắc bảo trì tài liệu này

1. **Không sửa yêu cầu nghiệp vụ ở đây** — sửa ở `docs/imm-XX/`, rồi đồng bộ ngược lại.
2. **Số liệu phải đếm lại** mỗi lần cập nhật (xem lệnh ở §0.4) — không sao chép số cũ.
3. Chức năng chưa có mã phải gắn nhãn `[ROADMAP]`; nội dung chưa kiểm chứng gắn `[UNVERIFIED]`.
4. Không dùng số ước lượng kiểu "100+", "8+" — đếm thật.
5. Tên hệ thống là **AssetCore**; các tên cũ IMMIS / IMESOM / SCM.CH1 là lỗi thời.

---

## Phụ lục A — Chỉ mục tài liệu gốc

| Module | Thư mục | Số file |
|---|---|---|
| IMM-00 | [`docs/imm-00/`](imm-00/README.md) | 22 (9 chuẩn + 12 ADR + báo cáo) |
| IMM-01 | [`docs/imm-01/`](imm-01/README.md) | 10 |
| IMM-02 | [`docs/imm-02/`](imm-02/README.md) | 10 |
| IMM-03 | [`docs/imm-03/`](imm-03/README.md) | 10 |
| IMM-04 | [`docs/imm-04/`](imm-04/README.md) | 11 |
| IMM-05 | [`docs/imm-05/`](imm-05/README.md) | 10 |
| IMM-06 | [`docs/imm-06/`](imm-06/README.md) | 10 |
| IMM-07 | [`docs/imm-07/`](imm-07/README.md) | 9 |
| IMM-08 | [`docs/imm-08/`](imm-08/README.md) | 10 |
| IMM-09 | [`docs/imm-09/`](imm-09/README.md) | 10 |
| IMM-10 | [`docs/imm-10/`](imm-10/README.md) | 9 |
| IMM-11 | [`docs/imm-11/`](imm-11/README.md) | 10 |
| IMM-12 | [`docs/imm-12/`](imm-12/README.md) | 11 |
| IMM-13 | [`docs/imm-13/`](imm-13/README.md) | 9 |
| IMM-14 | [`docs/imm-14/`](imm-14/README.md) | 9 |
| IMM-15 | [`docs/imm-15/`](imm-15/README.md) | 10 |
| IMM-16 | [`docs/imm-16/`](imm-16/README.md) | 10 |
| IMM-17 | [`docs/imm-17/`](imm-17/README.md) | 9 |

**Cấu trúc chuẩn mỗi module (9 file):** `README.md` · `02_Analysis_Design.md` · `03_Diagrams.md` · `04_Backend_Design.md` · `05_API_Specification.md` · `06_Frontend_Design.md` · `07_Testing_QA.md` · `08_Deployment.md` · `09_Release.md`

**Tài liệu liên quan khác:**

| Đường dẫn | Nội dung |
|---|---|
| [`docs/architecture/Ho_so_kien_truc_IMMIS.md`](architecture/Ho_so_kien_truc_IMMIS.md) | Kiến trúc tổng — nguồn chuẩn cho tên module, khối, đợt, vai trò |
| [`docs/ui-ux/`](ui-ux/) | Rà soát hiện trạng giao diện (148 route × 7 tiêu chí) + hệ thống thiết kế + khuôn màn hình |
| [`docs/huong-dan-su-dung/`](huong-dan-su-dung/) | Hướng dẫn sử dụng cho người dùng cuối (24 chương) |
| [`docs/nghiem-thu/`](nghiem-thu/) | Kịch bản nghiệm thu theo 8 nhóm người dùng |
| [`docs/mobile/`](mobile/) | Hợp đồng API cho ứng dụng di động |
| [`docs/architecture/WHO/`](architecture/WHO/) | Bộ tài liệu WHO HTM tham chiếu |
| [`docs/architecture/gmdn/`](architecture/gmdn/) | Quyết định Bộ Y tế về danh pháp GMDN |
| [`docs/template/`](template/) | Bộ mẫu 12 file để chuẩn hoá tài liệu module |

---

*Tài liệu tổng hợp — lập 2026-08-05 từ `docs/imm-XX/` và đối chiếu mã nguồn nhánh `feature/hieuc/core-refinement`. Mọi con số định lượng đếm thật tại thời điểm lập; xem §0.4 để tái lập.*
