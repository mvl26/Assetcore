---
name: assetcore-test
description: >
  Viết và chạy test cho AssetCore — bao gồm unit test service layer (Python/Frappe),
  workflow smoke test, integration test, UAT scripts, và UI test bằng Playwright MCP.
  Dùng khi user nói "viết test", "TDD", "kiểm thử", "test case cho IMM-XX",
  "bench run-tests", "test fails", "DoD", "playwright", "test UI", "kiểm tra giao diện",
  "chạy e2e", "UI xong chưa", "verify UI IMM-XX". Bắt buộc dùng trước khi khai báo
  bất kỳ feature BE hoặc FE nào là "xong" — CLAUDE.md §17 mandates TDD.
---

# AssetCore Test — Backend Unit + Playwright UI

Skill này bao 2 loại test: **Backend (Python/Frappe)** + **UI (Playwright MCP)**.
Mọi feature phải pass cả 2 trước khi được khai báo Done.

---

## NGUYÊN TẮC BẤT BIẾN — Đọc trước khi làm bất cứ điều gì

### R-0: Hai chế độ test có quy tắc data KHÁC NHAU

| Loại test | Nơi chạy | Quy tắc data |
|---|---|---|
| **Backend unit test** (Python) | `assetcore/tests/` | Dùng prefix `_Test` — Frappe auto-rollback/cleanup |
| **UI test** (Playwright) | Browser trên `localhost:3000` | **TUYỆT ĐỐI KHÔNG dùng tên test** — phải dùng data thực tế |

> Backend unit tests dùng `_Test` prefix vì Frappe wrap từng test trong savepoint và rollback.
> UI test KHÔNG được dùng `_Test` vì data tạo ra qua UI **không được rollback tự động** → gây rác.

---

### R-1: UI Test — Dữ liệu PHẢI thực tế — TUYỆT ĐỐI không dùng tên "test"

**Sai (cấm tuyệt đối trong UI test):**
- Tên rule: `TEST-R`, `Test Rule`, `IMM-Rule-01`, `testcomp`
- Tên khoa: `Dept`, `dept01`, `Unknown`, `Test Dept`, `Test WH IMM-15`
- Người dùng: `test@test.com`, `admin`, `testuser`
- Mô tả: `test`, `testing`, `some description`, `abc`, `123`
- Thiết bị: `Test Device`, `Asset 01`, `machine01`, `Test Asset IMM-15`, `Máy XQuangNew`
- Phụ tùng: `Test Part IMM-15`, `_TestSCSupplier`

**Đúng — dùng context bệnh viện Việt Nam thực tế:**
- Tên khoa: `Khoa Ngoại Tổng hợp`, `Khoa Hồi sức tích cực (ICU)`, `Phòng Mổ số 2`
- Tên thiết bị: `Máy thở Dräger Evita V500`, `Máy siêu âm Philips EPIQ 7`, `Monitor bệnh nhân Mindray BeneView T9`
- Nhà cung cấp: `Công ty TNHH Dräger Medical Vietnam`, `Meditronic Vietnam Co., Ltd`
- Phụ tùng: `Van PEEP máy thở Dräger Evita V500`, `Cảm biến SpO2 Masimo SET`
- Mô tả sự cố: `Thiết bị báo lỗi E-001 khi bệnh nhân thở thụ động`, `Màn hình hiển thị nhiễu sau 3 giờ vận hành`
- Ghi chú kỹ thuật: `Thay thế van PEEP do mòn — ref phụ tùng SP-DR-0234`

---

### R-2: Kiểm tra data tồn tại TRƯỚC KHI tạo bản ghi mới

**LUÔN làm trước bước 1 của bất kỳ UI test nào:**

```
1. Navigate → list page của master data cần thiết
2. Snapshot → verify dữ liệu có sẵn
3. Nếu thiếu → TẠO MASTER DATA THỰC TẾ TRƯỚC (xem R-3)
4. Chỉ sau khi có đủ master data → bắt đầu test operational record
```

**Dependency map — mỗi DocType cần những gì:**

| Bản ghi cần tạo | Master data bắt buộc phải có trước |
|---|---|
| AC Asset | AC Supplier, AC Location, AC Department |
| Work Order (PM/CM/Cal) | AC Asset đang Active |
| AC Incident Report | AC Asset đang Active, AC Department |
| AC CAPA | AC Incident Report hoặc Work Order gốc |
| AC Spare Part | AC UOM (đơn vị tính) |
| AC Spare Part Stock | AC Spare Part, AC Warehouse |
| AC Stock Movement | AC Spare Part, AC Warehouse (nguồn + đích) |
| AC Compliance Rule | (không cần) |
| AC Compliance Finding | AC Compliance Rule, AC Asset |
| AC Purchase | AC Supplier |
| AC Needs Request | AC Department |

---

### R-3: Khi master data chưa có — TẠO THỰC TẾ, không tạo tạm

**Ví dụ sai — tạo khoa tạm để vượt qua bước validation:**
> ~~Tạo "Dept-Temp-01" để có khoa cho test user~~

**Đúng — tạo khoa thực tế:**
> Navigate → `/departments` → Tạo "Khoa Nội thần kinh" với đầy đủ thông tin → sau đó quay lại tạo user

**Checklist khi tạo master data mới:**
- [ ] Tên đúng chuẩn tên bệnh viện Việt Nam (không viết tắt, không mã hóa)
- [ ] Điền đầy đủ tất cả optional fields có ý nghĩa
- [ ] Xác nhận bản ghi đã được lưu và có thể tìm thấy trong list

**Master data thực tế có sẵn trong hệ thống (tính đến 2026-05-18):**

```yaml
departments:
  - HC: HÀNH CHÍNH NS
  - HCNS: Hành chính
  - Khoa-CDHA: Khoa Chẩn đoán Hình ảnh
  - Khoa-HSTC: Khoa Hồi sức tích cực (ICU)
  - Khoa-NGTH: Khoa Ngoại Tổng hợp
  - Khoa-TMCT: Khoa Tim mạch can thiệp
  - OR: Khoa mổ
  - Phong-Mo-2: Phòng Mổ số 2

warehouses:
  - AC-WH-0388: Kho trung tâm Vật tư Thiết bị Y tế
  - AC-WH-0389: Kho phân xưởng kỹ thuật
  - AC-WH-0390: Kho QC Hold — phụ tùng chờ kiểm

assets_active:
  - AC-ASSET-2026-00407: Máy thở Dräger Evita V500 — ICU giường số 3
  - AC-ASSET-2026-00408: Monitor bệnh nhân Mindray BeneView T9 — ICU giường số 7
  - AC-ASSET-2026-00409: Máy siêu âm Philips EPIQ 7 — Khoa Chẩn đoán Hình ảnh

suppliers:
  - AC-SUP-2026-0017: Công ty TNHH Dräger Medical Vietnam
  - AC-SUP-2026-0018: Công ty CP Thiết bị Y tế Bình Minh
  - AC-SUP-2026-0021: Meditronic Vietnam Co., Ltd

locations:
  - AC-LOC-2026-0127: Phòng ICU — Tầng 3, Nhà A
  - AC-LOC-2026-0128: Phòng Mổ số 2 — Tầng 5, Nhà B
  - AC-LOC-2026-0129: Phòng Chẩn đoán Hình ảnh — Tầng 1, Nhà C
  - AC-LOC-2026-0131: Kho Vật tư Thiết bị Y tế — Tầng B1

spare_parts_in_stock:
  - AC-SP-2026-0263: Pin Lithium-ion Mindray BeneView T9 11.1V 5800mAh
  - AC-SP-2026-0264: Van PEEP máy thở Dräger Evita V500
  - AC-SP-2026-0274: Cảm biến nồng độ O2 máy thở Dräger Evita V500
  - AC-SP-2026-0275: Cảm biến SpO2 Masimo SET cho Mindray BeneView T9
  - AC-SP-2026-0276: Đầu dò siêu âm Convex C5-1 cho Philips EPIQ 7
  - AC-SP-2026-0277: Gel siêu âm Aquasonic 100 — can 5L cho Philips EPIQ 7
  - AC-SP-2026-0278: Bộ dây truyền B. Braun Perfusor Original 50ml
  - AC-SP-2026-0279: Cáp ECG 5 đạo trình AHA cho Monitor đa thông số
```

---

### R-4: Điền ĐẦY ĐỦ tất cả fields có thể điền

Khi test tạo bản ghi mới, **bắt buộc điền tất cả fields hiển thị** — không bỏ trống bất kỳ field optional nào có ý nghĩa.

Checklist fields bắt buộc theo loại bản ghi:
- **Work Order (PM/CM/Cal)**: asset, loại, ngày dự kiến, kỹ thuật viên, mô tả triệu chứng, địa điểm
- **Incident**: thiết bị, mô tả sự cố, mức độ, khoa/phòng, người báo cáo, thời gian xảy ra
- **CAPA**: root cause method, mô tả nguyên nhân gốc rễ, hành động khắc phục, người phụ trách, hạn xử lý
- **Needs Request**: thiết bị cần mua, lý do, khoa đề xuất, ưu tiên, tổng CAPEX ước tính
- **Compliance Rule**: tên rule cụ thể, phạm vi (khoa hoặc toàn viện), threshold, tần suất kiểm tra
- **Compliance Finding**: asset vi phạm, rule vi phạm, giá trị thực tế vs ngưỡng, mức độ, khoa chịu trách nhiệm

---

### R-5: Mỗi page test phải đi qua FULL user journey

Không chỉ test "list page load" — phải test toàn bộ luồng:
1. **Pre-check**: verify master data đủ (xem R-2 dependency map)
2. **Tạo mới** → điền đầy đủ fields → submit → verify record tạo thành công với tên đúng format
3. **Xem chi tiết** → click vào record → verify tất cả fields hiển thị đúng, không có `undefined`, `[object Object]`, `null`
4. **Workflow actions** → test từng nút hành động theo đúng state transition → verify trạng thái thay đổi đúng
5. **Filter** → áp dụng ít nhất 1 bộ lọc → verify kết quả đúng
6. **Edge case** → thử tạo bản ghi thiếu field bắt buộc → verify lỗi hiện rõ ràng

---

### R-6: Trang chi tiết PHẢI có đủ các chức năng

Mỗi trang chi tiết bản ghi phải có:
- [ ] Hiển thị tất cả fields (không thiếu field nào so với DocType)
- [ ] Tất cả workflow action buttons phù hợp với state hiện tại
- [ ] Lịch sử/audit trail (ít nhất hiển thị các action đã thực hiện)
- [ ] Liên kết đến bản ghi liên quan (CAPA, Work Order, Asset, v.v.)
- [ ] Nút quay lại (breadcrumb hoặc back button)

**Nếu trang chi tiết thiếu workflow actions → BUG, phải fix trước khi khai báo PASS.**

---

### R-7: Không khai báo PASS khi còn lỗi console

Sau mỗi page test, luôn chạy `browser_console_messages` và `browser_network_requests`. Test chỉ PASS khi:
- 0 lỗi JS console (TypeError, ReferenceError, Uncaught, v.v.)
- 0 API calls trả về 4xx hoặc 5xx trên trang hiện tại
- 0 field hiển thị `undefined`, `[object Object]`, `null` chuỗi

---

### R-8: Dữ liệu tạo trong UI test PHẢI được theo dõi và dọn dẹp

**Ghi lại mọi bản ghi tạo ra:**
Mỗi UI test session phải ghi rõ:
```
Data tạo trong session này:
  - [DocType]: [name] — [mô tả ngắn, lý do tạo]
  - ...
```

**Sau test session:**
- Các bản ghi operational (Work Order, Incident, CAPA, Finding) tạo để test có thể giữ lại nếu dữ liệu thực tế
- Nếu cần xóa: dùng `assetcore.scripts.cleanup_junk_data` script, hoặc qua UI (Cancel → Delete nếu DocType cho phép)
- **Tuyệt đối không để lại** bản ghi có tên chứa: `test`, `Test`, `TEST`, `_T-`, `IMM-XX`, `placeholder`, các mã giả

---

## Phần 1 — Backend Tests (Python/Frappe)

### Project layout
```
assetcore/tests/
├── __init__.py
├── test_imm00.py          # foundation DocTypes
├── test_workflows.py      # workflow smoke test (deploy gate)
└── test_immXX.py          # 1 file per module (TDD — CLAUDE.md §17)

assetcore/scripts/uat/
└── uat_immXX.py           # end-to-end UAT scenario (human-led)
```

**Tình trạng (May 2026):** chỉ có `test_imm00.py` và `test_workflows.py`. Module mới PHẢI thêm `test_immXX.py`.

### Chạy tests
```bash
bench --site miyano run-tests --app assetcore
bench --site miyano run-tests --module assetcore.tests.test_immXX
bench --site miyano run-tests --module assetcore.tests.test_immXX --test TestRepairCreation
bench --site miyano run-tests --skip-test-records  # faster iteration
```

### Standard test file template
```python
# assetcore/tests/test_immXX.py
from __future__ import annotations
import unittest, frappe

class TestXCreation(unittest.TestCase):
    """BR-XX-01: business rule statement."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset()          # shared fixture — prefix _Test

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")   # reset per test

    def tearDown(self):
        for r in frappe.get_all("DocType", filters={"parent_ref": self.asset.name}):
            frappe.delete_doc("DocType", r.name, force=True, ignore_permissions=True)

    def test_create_without_source_fails(self):
        from frappe.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            frappe.get_doc({
                "doctype": "DocType",
                "asset_ref": self.asset.name,
            }).insert(ignore_permissions=True)

    def test_create_with_source_succeeds(self):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "asset_ref": self.asset.name,
            "source": "Mô tả nguồn gốc thực tế",
        }).insert(ignore_permissions=True)
        self.assertEqual(doc.status, "Open")
```

### Service-layer tests (preferred — nhanh, không cần DB)
```python
from assetcore.services.imm09 import get_sla_target
from assetcore.services.shared import ErrorCode

class TestSlaMatrix(unittest.TestCase):
    def test_class3_emergency_is_4h(self):
        self.assertEqual(get_sla_target("Class III", "Emergency"), 4.0)

class TestServiceErrorContract(unittest.TestCase):
    def test_close_already_closed_raises_bad_state(self):
        with self.assertRaises(ServiceError) as cm:
            close_work_order(wo.name, ...)
        self.assertEqual(cm.exception.code, ErrorCode.BAD_STATE)
```
Assert trên `e.code` (machine-readable), không phải `e.message` (tiếng Việt, có thể thay).

### Permission tests
```python
def test_technician_cannot_close_wo(self):
    frappe.set_user("technician@test.com")
    try:
        with self.assertRaises(frappe.PermissionError):
            close_work_order(self.wo.name, ...)
    finally:
        frappe.set_user("Administrator")  # PHẢI restore trong finally
```

### Workflow smoke test
`tests/test_workflows.py` validate state/transition counts và docstatus rules — đây là **deploy gate**.
Khi thêm workflow mới:
```python
# tests/test_workflows.py
EXPECTED_WORKFLOWS = {
    "IMM-XX Workflow": {"doctype": "<DocType>", "min_states": N, "min_transitions": M},
}
```
**Đếm từ JSON, không đoán**:
```bash
python3 -c "import json; d=json.load(open('workflow.json')); print(len(d['states']), len(d['transitions']))"
```

### UAT script
```python
# assetcore/scripts/uat/uat_immXX.py
"""Run: bench --site miyano execute assetcore.scripts.uat.uat_immXX.run"""
import frappe

def run() -> None:
    print("UAT IMM-XX: full flow")
    # steps...
    print("✅ All steps passed")
    frappe.db.commit()  # bắt buộc trong CLI context
```

### Conventions — Backend

- `setUpClass` cho fixtures dùng chung; `setUp` cho per-test state.
- **Backend unit test**: LUÔN prefix fixtures với `_Test` — Frappe rollback tự động.
- Tests phải chạy được trên fresh site — `setUpClass` self-seed mọi dependency.
- Không mock database — Frappe wrap mỗi test trong savepoint, rollback tự động.
- Pre-existing test failure PHẢI fix trong cùng sprint phát hiện.

### Fixture rules (học từ bug thực tế)
- **Serial number phải unique**: luôn dùng timestamp:
  ```python
  import time
  sn = f"SN-{module}-{tag}-{int(time.time()) % 100000}"
  ```
- **Double-dash trong suffix**: `suffix="-create"` → `tag = suffix.lstrip("-")` trước khi ghép.
- **Field value phải khớp DocType options**: kiểm tra DocType JSON `options` trước khi dùng.
- **Submitted docs (docstatus=1) không thể force-delete**: phải cancel trước.
- **PM Schedule naming là deterministic** (`PMS-{asset}-{pm_type}`): dùng shared schedule trong `setUpClass`.
- **Naming series**: `"autoname": "PREFIX-.YYYY.-.#####"` (không có `format:` prefix).
- **Frappe class name**: `doctype.replace(" ", "").replace("-", "")` — "IMM MR Attendee" → `IMMMRAttendee`.

### Coverage targets
Priority: Validators → Service entrypoints → Permission gates → Status transitions.
Skip: trivial getters, Frappe internals, DocType property accessors.

---

## Phần 2 — UI Tests (Playwright MCP)

### Nguyên tắc
- **Playwright MCP là phương tiện duy nhất** — không đoán kết quả từ code.
- **Base URL**: `http://localhost:3000` (Vite dev server — phải có `bench start` chạy song song).
- **Test cases nguồn từ** `docs/imm-XX/07_Testing_QA.md` — bảng `UAT-IMMXX-NN`.

### Credentials — đọc từ .env TRƯỚC KHI bắt đầu bất kỳ UI test nào

```bash
cat /home/miyano/frappe-bench/apps/assetcore/.env
# TEST_USER=chuvanhieu357@gmail.com
# TEST_PASSWORD=chuvanhieu357gmail.com
```

**Quy tắc**: KHÔNG hardcode credentials. LUÔN đọc `.env` đầu session.

### Bộ dữ liệu mẫu thực tế (dùng trong mọi UI test)

```yaml
departments:
  - Khoa Hồi sức tích cực (ICU)
  - Khoa Ngoại Tổng hợp
  - Khoa Chẩn đoán Hình ảnh
  - Phòng Mổ số 2
  - Khoa Tim mạch can thiệp

devices:
  - Máy thở Dräger Evita V500 | SN: EVT-2023-0891 | ID: AC-ASSET-2026-00407
  - Monitor bệnh nhân Mindray BeneView T9 | SN: MBT9-2024-1122 | ID: AC-ASSET-2026-00408
  - Máy siêu âm Philips EPIQ 7 | SN: EPQ7-2022-0445 | ID: AC-ASSET-2026-00409

vendors:
  - Công ty TNHH Dräger Medical Vietnam | AC-SUP-2026-0017
  - Công ty CP Thiết bị Y tế Bình Minh | AC-SUP-2026-0018
  - Meditronic Vietnam Co., Ltd | AC-SUP-2026-0021

technicians:
  - KTV. Nguyễn Văn Hùng — Trưởng kỹ thuật
  - KTV. Trần Thị Lan — Kỹ thuật viên cơ điện
  - KTV. Lê Minh Đức — Chuyên viên điện tử y tế

incident_descriptions:
  - "Máy thở báo lỗi E-001 — áp lực đường thở tăng bất thường khi bệnh nhân thở thụ động. Đã tạm dừng sử dụng, chuyển sang máy dự phòng."
  - "Monitor bệnh nhân mất tín hiệu SpO2 sau 2 giờ vận hành liên tục tại ICU giường số 7. Nghi ngờ lỏng đầu cảm biến."
  - "Máy siêu âm hiển thị artifact dạng sọc ngang — ảnh hưởng chất lượng chẩn đoán sau khi di chuyển thiết bị."

capa_root_causes:
  - "Quy trình bảo trì định kỳ không được thực hiện đúng lịch (delay 3 tuần do thiếu nhân lực)"
  - "Van PEEP bị mòn do vượt quá chu kỳ thay thế khuyến nghị (>18 tháng)"
  - "Nhân viên chưa được đào tạo cập nhật quy trình vận hành thiết bị phiên bản mới"

compliance_rules:
  - "Tần suất bảo dưỡng định kỳ thiết bị Class II — tối đa 6 tháng/lần | category: PM"
  - "Kiểm định hiệu chuẩn máy đo SpO2 — 12 tháng/lần theo TCVN 8023 | category: Calibration"
  - "Hồ sơ thiết bị y tế phải đầy đủ UDI và giấy phép lưu hành | category: Document"
```

### Pre-test checklist (chạy TRƯỚC mọi test session)

```
1. Đọc .env → lấy TEST_USER, TEST_PASSWORD
2. Check master data đủ chưa (dùng danh sách R-3 ở trên)
3. Nếu thiếu master data:
   a. Navigate đến module master data tương ứng
   b. Tạo bản ghi với tên thực tế (không tạm, không test)
   c. Xác nhận lưu thành công
   d. Ghi lại tên bản ghi vừa tạo
4. Login → verify redirect khỏi /login
```

### Login
```
browser_navigate    → http://localhost:3000
browser_fill_form   → {"Email": <TEST_USER>, "Mật khẩu": <TEST_PASSWORD>}
browser_click       → "Đăng nhập"
browser_snapshot    → verify URL đã rời khỏi /login
```

### Playwright MCP tools
| Mục đích | Tool |
|---|---|
| Điều hướng | `browser_navigate` |
| Đọc DOM | `browser_snapshot` |
| Click | `browser_click` |
| Fill form | `browser_fill_form` / `browser_type` |
| Select dropdown | `browser_select_option` |
| Screenshot khi FAIL | `browser_take_screenshot` |
| Network calls | `browser_network_requests` + `browser_network_request` |
| JS assertion | `browser_evaluate` |
| Chờ element | `browser_wait_for` |
| Console errors | `browser_console_messages` |
| Resize responsive | `browser_resize` |

### Full User Journey — mỗi module PHẢI test đủ các bước này

#### Bước 0: Pre-check master data
- Verify tất cả dependency trong R-2 đã có trong hệ thống
- Nếu thiếu → tạo thực tế TRƯỚC (R-3), ghi lại tên

#### Bước 1: Tạo dữ liệu mới với dữ liệu THỰC TẾ
- Điền ĐẦY ĐỦ tất cả fields (không bỏ trống optional field có ý nghĩa)
- Dùng dữ liệu từ bộ mẫu thực tế ở trên
- Verify sau tạo: tên record có đúng format (vd: `CAPA-2026-XXXXX`), status đúng
- Kiểm tra network request trả về 200

#### Bước 2: Xem chi tiết bản ghi vừa tạo
- Navigate đến trang chi tiết
- Verify tất cả fields hiển thị đúng (không `undefined`, không `null`, không `[object Object]`)
- Verify tên người/thiết bị/đơn vị hiển thị dạng human-readable
- Verify có đủ workflow action buttons tương ứng state hiện tại

#### Bước 3: Thực hiện workflow action
- Click action button phù hợp với state hiện tại
- Confirm dialog nếu có
- Verify status thay đổi đúng
- Verify toast success/error xuất hiện

#### Bước 4: Kiểm tra filter và tìm kiếm
- Áp dụng ít nhất 1 filter → verify kết quả đúng

#### Bước 5: Kiểm tra error handling
- Thử submit form thiếu field bắt buộc → verify lỗi hiện rõ ràng

### DoD Checklist UI (áp dụng mọi module)

#### Bắt buộc PASS:
- [ ] List page load, không console error, không network 4xx/5xx
- [ ] Mỗi bản ghi trong list có thể click để xem chi tiết
- [ ] **Chi tiết page có workflow action buttons đúng với state** — nếu không có → BUG
- [ ] Filter hoạt động → table cập nhật đúng
- [ ] Tạo bản ghi mới với dữ liệu THỰC TẾ đầy đủ fields → thành công
- [ ] Tất cả fields hiển thị human-readable name
- [ ] Không có field nào hiển thị `undefined`, `[object Object]`, `null` chuỗi
- [ ] Toast/thông báo xuất hiện khi thành công và thất bại
- [ ] Audit trail có ít nhất 1 entry sau khi tạo bản ghi

#### Kiểm tra thêm:
- [ ] Pagination hoạt động nếu có > 1 trang
- [ ] Loading skeleton hiển thị trong lúc fetch
- [ ] Error banner + nút retry khi API lỗi
- [ ] Responsive 375px — không vỡ layout
- [ ] Sidebar không che content: test viewport ≥ 1280px

### Chạy từng UAT scenario
1. Đọc bảng UAT từ `docs/imm-XX/07_Testing_QA.md`
2. Với mỗi `UAT-IMMXX-NN`: thực hiện đúng thứ tự, snapshot sau mỗi action
3. Ghi kết quả:
   ```
   ✅ PASS — UAT-IMMXX-NN: <tên>
      Thực tế: <mô tả ngắn>
      Dữ liệu đã dùng/tạo: <tên record thực tế>

   ❌ FAIL — UAT-IMMXX-NN: <tên>
      Kỳ vọng: <expected>
      Thực tế : <actual>
      Root cause: <phân tích>
   ```

### UI bugs cần kiểm tra ngay (học từ bug thực tế)

| Pattern lỗi | Cách kiểm tra |
|---|---|
| Status FE ≠ BE constant | Grep `_STATUS_*` trong service, so với `STATUS_COLOR`/`STATUS_LABEL` trong view |
| Hiển thị mã thay vì tên | Playwright snapshot → tìm chuỗi `ACC-*`, `SUP-*`, `email@...` ở nơi phải là tên |
| Priority/select options FE ≠ BE | Grep DocType JSON `options` field, so với `<select>` options trong form |
| Risk class mapping FE→BE | FE lấy risk từ AC Asset (Low/Medium/High/Critical) mà truyền sang DocType khác |
| Trang detail thiếu workflow buttons | Snapshot trang detail → verify button tồn tại tương ứng state |
| Naming series sai | Verify DocType JSON: `naming_rule: "Naming Series"` |
| Link field free text | Phải là `<select>` hoặc autocomplete, không phải `<input type="text">` |

### DoD Report
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DoD Report — IMM-XX UI
  Tổng: N scenarios | ✅ P pass | ❌ F fail
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Master data đã dùng:
  - [tên bản ghi thực tế 1]: [loại]
Master data đã tạo mới trong session:
  - [tên bản ghi mới 1]: [lý do tạo mới]
Bản ghi operational đã tạo:
  - [tên bản ghi thực tế]: [mô tả ngắn]
VERDICT: ✅ DONE / ❌ NOT DONE
Việc cần làm: [action items cụ thể]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
**Chỉ DONE khi 0 FAIL và dữ liệu test là thực tế.**

### Module → URL mapping
| Module | List URL | Detail URL |
|---|---|---|
| IMM-01 Needs | `/imm01/needs-requests` | `/imm01/needs-requests/:id` |
| IMM-01 Plans | `/procurement-plans` | `/procurement-plans/:id` |
| IMM-06 | `/imm06/programs` | `/imm06/programs/:id` |
| IMM-08 | `/pm/work-orders` | `/pm/work-orders/:id` |
| IMM-09 | `/cm/work-orders` | `/cm/work-orders/:id` |
| IMM-11 | `/calibration` | `/calibration/:id` |
| IMM-12 | `/incidents` | `/incidents/:id` |
| IMM-15 | `/inventory` | (dashboard) |
| IMM-16 Rules | `/compliance/rules` | (list actions) |
| IMM-16 Findings | `/compliance/findings` | `/compliance/findings/:id` |
| IMM-16 CAPA | `/capas` | `/capas/:id` |
| Assets | `/assets` | `/assets/:id` |

---

## Before claiming DONE

### Backend
- [ ] `bench --site miyano run-tests --module assetcore.tests.test_immXX` — all pass
- [ ] Workflow smoke test còn pass: `--module assetcore.tests.test_workflows`
- [ ] `EXPECTED_WORKFLOWS` đã update nếu thêm workflow mới
- [ ] Không có `except: pass` mới

### UI (tất cả phải pass)
- [ ] Pre-check master data đủ (R-2) — nếu tạo mới thì dùng tên thực tế (R-3)
- [ ] Dữ liệu test là THỰC TẾ (không có "test", "IMM-XX", tên giả)
- [ ] Tất cả fields điền đầy đủ với dữ liệu có ý nghĩa
- [ ] Tất cả trang chi tiết có đủ workflow action buttons
- [ ] 0 console error trên mọi trang
- [ ] 0 API trả về 4xx/5xx trên trang hiện tại
- [ ] Playwright test chạy thực sự trên `localhost:3000` — không đoán từ code

### Reference files
- `assetcore/tests/test_imm00.py` — DocType-level pattern
- `assetcore/tests/test_workflows.py` — smoke test
- `/home/miyano/frappe-bench/apps/assetcore/.env` — `TEST_USER` / `TEST_PASSWORD`
- `docs/imm-XX/07_Testing_QA.md` — UAT scenarios nguồn
- `.claude/skills/assetcore-test/references/playwright-patterns.md` — Playwright patterns

---

## Quick audit script (chạy đầu mọi session test)

```bash
# 1. Kiểm tra Frappe whitelist functions có type hint gây 417
grep -rn "int | None\|float | None\|Optional\[int\]" assetcore/api/ \
  | grep -B1 "@frappe.whitelist" -A2

# 2. Verify workflow action labels match BE JSON và FE TRANSITIONS_BY_STATE
for wf in assetcore/assetcore/workflow/*.json; do
  python3 -c "import json; d=json.load(open('$wf')); \
    print('$wf:', [t['action'] for t in d['transitions']])"
done

# 3. Search FE for hardcoded supplier/department codes
grep -rn "AC-SUP\|AC-DEPT\|IMM-MDL" frontend/src/views/*.vue \
  | grep -v "\.test\.\|\.spec\.\|// "
```

## Lessons Learned — Patterns phải kiểm tra mọi session

### LL-TEST-1: Test phải bắt được "list page thiếu nút tạo"
```
browser_snapshot → grep tìm button "Tạo" hoặc "+ "
Nếu không có → FAIL ngay
```

### LL-TEST-2: Test phải bắt được "detail thiếu workflow buttons"
Traverse từng state, mỗi state PHẢI có button transition.
Bug đã gặp: PD-26-00003 dừng ở "Contract Signed" vì FE thiếu nút "Phát hành PO".

### LL-TEST-3: Test phải bắt được "hiển thị code thay vì tên"
```javascript
const codes = document.body.innerText.match(/AC-(SUP|DEPT|ASSET)-\d+/g)
return codes  // nếu có code ở nơi user-facing → bug
```

### LL-TEST-4: Test phải bắt được "Frappe child row hiển thị auto-name"
```javascript
const autoNames = [...document.body.innerText.matchAll(/\b[a-z0-9]{10}\b/g)]
return autoNames.map(m => m[0])  // không nên có trên UI
```

### LL-TEST-5: Test phải traverse FULL lifecycle
- Tạo record → đi qua MỌI state (không skip)
- Ở mỗi state: verify stepper + nút action đúng
- Ở terminal state: verify không còn forward action

### LL-TEST-6: Catch HTTP 417 và 1054
```
browser_console_messages(level="error")
// "417 (EXPECTATION FAILED)" → BE whitelist type hint sai
// "Unknown column" hoặc "(1054, ...)" → field không tồn tại trong DocType
```

### LL-TEST-7: Select field options FE = BE DocType options
```bash
python3 -c "import json; d=json.load(open('<doctype>.json')); \
  [print(f['fieldname'], f.get('options','')) for f in d['fields'] if f['fieldtype']=='Select']"
```

### LL-TEST-8: Form Link field phải dropdown
Field DocType Link → phải là `<select>` hoặc autocomplete, không phải `<input type="text">`.

### Bug patterns table

| Pattern | Symptom | Fix |
|---|---|---|
| HTTP 417 from GET endpoint | "EXPECTATION FAILED" trong console | BE: đổi `int \| None` → `str = ""` |
| HTTP 1054 Unknown column | Error toast "Unknown column 'X'" | BE: verify DocType JSON có field 'X' |
| Workflow action 422 | "Not a valid Workflow Action" | FE: action label phải khớp BE JSON exact |
| Child row auto-name leak | UI hiển thị `5mvh1o4qsa` | FE: đọc Link field, không đọc `.name` |
| Display code leak | UI hiển thị `AC-DEPT-0101` | BE: enrich `_name` companion; FE: ưu tiên `_name` |
| Workflow state stuck | Detail không có action button | FE: thêm state vào `TRANSITIONS_BY_STATE` |
| List page no create | Chỉ có filter, không có "+ Tạo" | FE: thêm button vào `PageHeader #actions` |
| Status badge sai | Submitted hiển thị "Đã duyệt" | FE: sync `STATUS_LABEL`/`STATUS_COLOR` với BE state |
| Link field free text | Save fail "Could not find Row" | FE: đổi `<input>` → `<select>` load từ API |
| Select option mismatch | Save fail "Invalid Value" | FE: options khớp DocType JSON `options` |
