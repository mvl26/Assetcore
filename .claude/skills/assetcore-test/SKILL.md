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

### R-1: Dữ liệu test PHẢI thực tế — TUYỆT ĐỐI không dùng tên "test"

**Sai (cấm tuyệt đối):**
- Tên rule: `TEST-R`, `Test Rule`, `IMM-Rule-01`
- Tên khoa: `Dept`, `dept01`, `Unknown`, `Test Dept`
- Người dùng: `test@test.com`, `admin`, `testuser`
- Mô tả: `test`, `testing`, `some description`, `abc`, `123`
- Thiết bị: `Test Device`, `Asset 01`, `machine01`

**Đúng — dùng context bệnh viện Việt Nam thực tế:**
- Tên khoa: `Khoa Ngoại Tổng hợp`, `Khoa Hồi sức tích cực (ICU)`, `Phòng Mổ số 2`, `Khoa Chẩn đoán Hình ảnh`
- Tên thiết bị: `Máy thở Dräger Evita V500`, `Máy siêu âm Philips EPIQ 7`, `Monitor bệnh nhân Mindray BeneView T9`
- Nhà cung cấp: `Công ty TNHH Dräger Medical Vietnam`, `Meditronic Vietnam Co., Ltd`
- Mô tả sự cố: `Thiết bị báo lỗi E-001 khi bệnh nhân thở thụ động`, `Màn hình hiển thị nhiễu sau 3 giờ vận hành`
- Ghi chú kỹ thuật: `Thay thế van PEEP do mòn — ref phụ tùng SP-DR-0234`, `Hiệu chuẩn cảm biến SpO2 theo quy trình QP-03-2025`

### R-2: Điền ĐẦY ĐỦ tất cả fields có thể điền

Khi test tạo bản ghi mới, **bắt buộc điền tất cả fields hiển thị** — không bỏ trống bất kỳ field optional nào có ý nghĩa nghiệp vụ.

Checklist fields bắt buộc theo loại bản ghi:
- **Work Order (PM/CM/Cal)**: asset, loại, ngày dự kiến, kỹ thuật viên, mô tả triệu chứng, địa điểm
- **Incident**: thiết bị, mô tả sự cố, mức độ, khoa/phòng, người báo cáo, thời gian xảy ra
- **CAPA**: root cause method, mô tả nguyên nhân gốc rễ, hành động khắc phục, người phụ trách, hạn xử lý
- **Needs Request**: thiết bị cần mua, lý do, khoa đề xuất, ưu tiên, tổng CAPEX ước tính
- **Compliance Rule**: tên rule cụ thể, phạm vi (khoa hoặc toàn viện), threshold, tần suất kiểm tra
- **Compliance Finding**: asset vi phạm, rule vi phạm, giá trị thực tế vs ngưỡng, mức độ, khoa chịu trách nhiệm
- **Management Review**: quý, ngày, chủ tịch, biên bản URL, ít nhất 1 output action có mô tả + người phụ trách + hạn

### R-3: Mỗi page test phải đi qua FULL user journey

Không chỉ test "list page load" — phải test toàn bộ luồng:
1. **Tạo mới** → điền đầy đủ fields → submit → verify record tạo thành công với tên đúng format
2. **Xem chi tiết** → click vào record → verify tất cả fields hiển thị đúng, không có `undefined`, `[object Object]`, `null`, `—` ở chỗ nên có dữ liệu
3. **Workflow actions** → test từng nút hành động theo đúng state transition → verify trạng thái thay đổi đúng
4. **Filter** → áp dụng ít nhất 1 bộ lọc → verify kết quả đúng
5. **Edge case** → thử tạo bản ghi thiếu field bắt buộc → verify lỗi hiện rõ ràng

### R-4: Trang chi tiết PHẢI có đủ các chức năng

Mỗi trang chi tiết bản ghi phải có:
- [ ] Hiển thị tất cả fields (không thiếu field nào so với DocType)
- [ ] Tất cả workflow action buttons phù hợp với state hiện tại
- [ ] Lịch sử/audit trail (ít nhất hiển thị các action đã thực hiện)
- [ ] Liên kết đến bản ghi liên quan (CAPA, Work Order, Asset, v.v.)
- [ ] Nút quay lại (breadcrumb hoặc back button)

**Nếu trang chi tiết thiếu workflow actions → BUG, phải fix trước khi khai báo PASS.**

### R-5: Asset detail page — bắt buộc có đủ dữ liệu thống kê

Trang `/assets/:id` phải hiển thị dữ liệu thực tế ở tất cả tabs:
- **Tab Thông tin**: tất cả fields điền đầy đủ (model, serial, vendor, department, purchase date, warranty, v.v.)
- **Tab Khấu hao**: depreciation schedule phải được tính (nếu asset đã nhập vào sử dụng)
- **Tab Lịch sử**: ít nhất phải có lifecycle event "installed" hoặc "commissioned"
- **Tab KPI**: uptime%, MTBF, MTTR phải có dữ liệu (hoặc hiển thị rõ "Chưa đủ dữ liệu để tính")
- **Widget Ngừng máy**: nếu chưa có downtime event → hiển thị "0 sự kiện ngừng máy" (không để trống)
- **Audit Trail**: phải có ít nhất 1 entry từ lúc tạo asset

**Nếu tab KPI/depreciation/audit trail trống hoàn toàn → phải kiểm tra BE service và tạo test data.**

### R-6: Không khai báo PASS khi còn lỗi console

Sau mỗi page test, luôn chạy `browser_console_messages` và `browser_network_requests`. Test chỉ PASS khi:
- 0 lỗi JS console (TypeError, ReferenceError, Uncaught, v.v.)
- 0 API calls trả về 4xx hoặc 5xx trên trang hiện tại
- 0 field hiển thị `undefined`, `[object Object]`, `null` chuỗi

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
bench --site <site> run-tests --app assetcore
bench --site <site> run-tests --module assetcore.tests.test_immXX
bench --site <site> run-tests --module assetcore.tests.test_immXX --test TestRepairCreation
bench --site <site> run-tests --skip-test-records  # faster iteration
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
        cls.asset = _make_asset()          # shared fixture

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
            "source": "test",
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
"""Run: bench --site <site> execute assetcore.scripts.uat.uat_immXX.run"""
import frappe

def run() -> None:
    print("UAT IMM-XX: full flow")
    # steps...
    print("✅ All steps passed")
    frappe.db.commit()  # bắt buộc trong CLI context
```

### Conventions
- `setUpClass` cho fixtures dùng chung; `setUp` cho per-test state.
- Luôn prefix test records với `_Test` — cleanup hooks find them.
- Tests phải chạy được trên fresh site — `setUpClass` self-seed mọi dependency.
- Không mock database — Frappe wrap mỗi test trong savepoint, rollback tự động.
- Pre-existing test failure PHẢI fix trong cùng sprint phát hiện.

### Fixture rules (học từ bug thực tế)
- **Serial number phải unique**: luôn dùng timestamp để tránh `DuplicateEntryError`:
  ```python
  import time
  sn = f"SN-{module}-{tag}-{int(time.time()) % 100000}"
  ```
- **Double-dash trong suffix**: `suffix="-create"` → `tag = suffix.lstrip("-")` trước khi ghép.
- **Field value phải khớp DocType options**: trước khi dùng field value trong fixture, kiểm tra DocType JSON cho `options`. Ví dụ `risk_classification` của AC Asset là `"Low/Medium/High/Critical"`.
- **Submitted docs (docstatus=1) không thể force-delete**: phải cancel trước:
  ```python
  doc = frappe.get_doc("DocType", name)
  if doc.docstatus == 1:
      doc.cancel()
  frappe.delete_doc("DocType", name, force=True, ignore_permissions=True)
  ```
- **PM Schedule naming là deterministic** (`PMS-{asset}-{pm_type}`): dùng shared schedule trong `setUpClass`.
- **Child table `reqd:1`**: khi service tạo child rows với value rỗng, field `reqd:1` sẽ raise `MandatoryError`. Kiểm tra DocType JSON trước khi viết service code.
- **Naming series**: DocType phải có `naming_rule: "Naming Series"` — không dùng `"Expression (old style)"` với `format:` prefix. Kiểm tra với: `"autoname": "PREFIX-.YYYY.-.#####"` (không có `format:`).
- **Frappe class name**: `class_name = doctype.replace(" ", "").replace("-", "")` — "IMM MR Attendee" → `IMMMRAttendee`. Kiểm tra .py file khi có `ImportError`.

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

File: `/home/miyano/frappe-bench/apps/assetcore/.env`

```bash
# Đọc credentials (chạy lệnh này để lấy giá trị thực)
cat /home/miyano/frappe-bench/apps/assetcore/.env
```

Nội dung hiện tại:
```
TEST_USER=chuvanhieu357@gmail.com
TEST_PASSWORD=chuvanhieu357gmail.com
```

**Quy tắc**:
- KHÔNG hardcode credentials trực tiếp vào test script hoặc Playwright steps
- LUÔN đọc `.env` đầu session để lấy giá trị mới nhất trước khi login
- Nếu `.env` không tồn tại → báo user tạo file trước khi tiếp tục

### Bộ dữ liệu mẫu thực tế (bắt buộc dùng trong mọi UI test)

```yaml
departments:
  - Khoa Hồi sức tích cực (ICU)
  - Khoa Ngoại Tổng hợp
  - Khoa Chẩn đoán Hình ảnh
  - Phòng Mổ số 2
  - Khoa Tim mạch can thiệp
  - Khoa Nội thần kinh

devices:
  - Máy thở Dräger Evita V500 | SN: EVT-2023-0891
  - Monitor bệnh nhân Mindray BeneView T9 | SN: MBT9-2024-1122
  - Máy siêu âm Philips EPIQ 7 | SN: EPQ7-2022-0445
  - Máy X-quang di động Canon CXDI-Elite | SN: CXD-2023-0678
  - Máy bơm tiêm B. Braun Perfusor Space | SN: BBR-2024-2201

vendors:
  - Công ty TNHH Dräger Medical Vietnam
  - Công ty CP Thiết bị Y tế Bình Minh
  - Meditronic Vietnam Co., Ltd
  - Công ty TNHH Philips Việt Nam

technicians:
  - KTV. Nguyễn Văn Hùng — Trưởng kỹ thuật
  - KTV. Trần Thị Lan — Kỹ thuật viên cơ điện
  - KTV. Lê Minh Đức — Chuyên viên điện tử y tế

incident_descriptions:
  - "Máy thở báo lỗi E-001 — áp lực đường thở tăng bất thường khi bệnh nhân thở thụ động. Đã tạm dừng sử dụng, chuyển sang máy dự phòng."
  - "Monitor bệnh nhân mất tín hiệu SpO2 sau 2 giờ vận hành liên tục tại ICU giường số 7. Nghi ngờ lỏng đầu cảm biến."
  - "Máy X-quang hiển thị artifact dạng sọc ngang — ảnh hưởng chất lượng chẩn đoán. Sự cố xảy ra sau khi di chuyển thiết bị."

capa_root_causes:
  - "Quy trình bảo trì định kỳ không được thực hiện đúng lịch (delay 3 tuần do thiếu nhân lực)"
  - "Van PEEP bị mòn do vượt quá chu kỳ thay thế khuyến nghị (>18 tháng)"
  - "Nhân viên chưa được đào tạo cập nhật quy trình vận hành thiết bị phiên bản mới"

compliance_rules:
  - "Tần suất bảo dưỡng định kỳ thiết bị Class II — tối đa 6 tháng/lần | category: PM"
  - "Kiểm định hiệu chuẩn máy đo SpO2 — 12 tháng/lần theo TCVN 8023 | category: Calibration"
  - "Hồ sơ thiết bị y tế phải đầy đủ UDI và giấy phép lưu hành | category: Document"

procurement:
  - plan: "Kế hoạch mua sắm Q2/2026 | ngân sách: 4,500,000,000 VNĐ"
  - needs: "Đề xuất mua máy siêu âm tim mạch 4D cho Khoa Tim mạch can thiệp | CAPEX: 1,200,000,000 VNĐ"
```

### Login (dùng credentials từ .env)
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
| Network calls | `browser_network_requests` + `browser_network_request` (response body) |
| JS assertion | `browser_evaluate` |
| Chờ element | `browser_wait_for` |
| Console errors | `browser_console_messages` |
| Resize responsive | `browser_resize` |

### Full User Journey — mỗi module PHẢI test đủ các bước này

#### Bước 1: Tạo dữ liệu mới với dữ liệu THỰC TẾ
- Điền ĐẦY ĐỦ tất cả fields (không bỏ trống optional field có ý nghĩa)
- Dùng dữ liệu từ bộ mẫu thực tế ở trên
- Verify sau tạo: tên record có đúng format (vd: `CAPA-2026-XXXXX`), status đúng ("Draft" hoặc "Open")
- Kiểm tra network request trả về 200 (không 4xx/5xx)

#### Bước 2: Xem chi tiết bản ghi vừa tạo
- Navigate đến trang chi tiết (click row hoặc "Chi tiết →" button)
- Verify tất cả fields hiển thị đúng (không `undefined`, không `null`, không `[object Object]`)
- Verify tên người/thiết bị/đơn vị hiển thị dạng human-readable (không email thô, không mã DocType)
- Verify có đủ workflow action buttons tương ứng state hiện tại

#### Bước 3: Thực hiện workflow action
- Click action button phù hợp với state hiện tại (vd: Submit, Approve, Start, Complete, Close)
- Confirm dialog nếu có
- Verify status thay đổi đúng
- Verify toast success/error xuất hiện
- Verify buttons cập nhật theo state mới (button cũ biến mất, button mới xuất hiện)

#### Bước 4: Kiểm tra filter và tìm kiếm
- Áp dụng ít nhất 1 filter → verify kết quả đúng
- Tìm kiếm theo từ khóa thực tế → verify có kết quả

#### Bước 5: Kiểm tra error handling
- Thử submit form thiếu field bắt buộc → verify lỗi hiện rõ ràng cho user
- Không để trang crash hoàn toàn khi có lỗi

### DoD Checklist UI (áp dụng mọi module)

#### Bắt buộc PASS (không có ngoại lệ):
- [ ] List page load, không console error, không network 4xx/5xx
- [ ] Mỗi bản ghi trong list có thể click để xem chi tiết
- [ ] **Chi tiết page có workflow action buttons đúng với state** — nếu không có → BUG phải fix
- [ ] Filter hoạt động → table cập nhật đúng
- [ ] Tạo bản ghi mới với dữ liệu THỰC TẾ đầy đủ fields → thành công
- [ ] Tất cả fields hiển thị human-readable name (không mã DocType, không email thô)
- [ ] Không có field nào hiển thị `undefined`, `[object Object]`, `null` chuỗi
- [ ] Toast/thông báo xuất hiện rõ ràng khi thành công và thất bại
- [ ] Audit trail / lịch sử có ít nhất 1 entry sau khi tạo bản ghi

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
      Dữ liệu đã tạo: <tên record thực tế>

   ❌ FAIL — UAT-IMMXX-NN: <tên>
      Kỳ vọng: <expected>
      Thực tế : <actual>
      Root cause: <phân tích>
   ```

### UI bugs cần kiểm tra ngay (học từ bug thực tế)

| Pattern lỗi | Cách kiểm tra |
|---|---|
| Status FE ≠ BE constant | Grep `_STATUS_*` trong service, so với `STATUS_COLOR`/`STATUS_LABEL`/`allowed_transitions.includes` trong view |
| Hiển thị mã thay vì tên (NCC, asset, user) | Playwright snapshot → tìm chuỗi dạng `ACC-*`, `SUP-*`, `email@...` ở nơi phải là tên đọc được |
| Priority/select options FE ≠ BE | Grep DocType JSON `options` field, so với `<select>` options trong form |
| Risk class mapping FE→BE | Khi FE lấy risk từ AC Asset (Low/Medium/High/Critical) mà truyền sang DocType khác (Class I/II/III), phải có mapping layer |
| Form draft cache giữ giá trị cũ | Sau khi fix options, dùng `useFormDraft` clear hoặc test với fresh browser session |
| Trang detail thiếu workflow buttons | Snapshot trang detail → verify button tồn tại tương ứng state |
| Naming series sai | Verify DocType JSON: `naming_rule: "Naming Series"`, không có prefix `format:` |
| Frappe class name sai | Frappe: `doctype.replace(" ", "").replace("-", "")` = class name; kiểm tra .py file |

### DoD Report
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DoD Report — IMM-XX UI
  Tổng: N scenarios | ✅ P pass | ❌ F fail
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dữ liệu test tạo:
  - [tên bản ghi thực tế 1]: [mô tả ngắn]
  - [tên bản ghi thực tế 2]: [mô tả ngắn]
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
- [ ] `bench --site <site> run-tests --module assetcore.tests.test_immXX` — all pass
- [ ] Workflow smoke test còn pass: `--module assetcore.tests.test_workflows`
- [ ] `EXPECTED_WORKFLOWS` đã update nếu thêm workflow mới
- [ ] Không có `except: pass` mới

### UI (tất cả phải pass)
- [ ] Dữ liệu test là THỰC TẾ (không có "test", "IMM-XX", tên giả)
- [ ] Tất cả fields điền đầy đủ với dữ liệu có ý nghĩa
- [ ] Tất cả trang chi tiết có đủ workflow action buttons
- [ ] 0 console error trên mọi trang
- [ ] 0 API trả về 4xx/5xx trên trang hiện tại
- [ ] Playwright test chạy thực sự trên `localhost:3000` — không đoán từ code

### Reference files
- `assetcore/tests/test_imm00.py` — DocType-level pattern
- `assetcore/tests/test_workflows.py` — smoke test
- `/home/miyano/frappe-bench/apps/assetcore/.env` — `TEST_USER` / `TEST_PASSWORD` cho Playwright login (đọc đầu mỗi session)
- `docs/imm-XX/07_Testing_QA.md` — UAT scenarios nguồn
- `.claude/skills/assetcore-test/references/playwright-patterns.md` — Playwright patterns chi tiết
