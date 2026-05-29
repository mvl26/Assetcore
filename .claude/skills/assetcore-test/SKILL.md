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

### R-9: Backend test fixture PHẢI tự dọn — không rely on `frappe.db.rollback`

**Bug đã gặp 2026-05-27:** sau nhiều lần `bench --site miyano run-tests --app assetcore`, DB tích luỹ 776+ records test (`Test Asset IMM-15`, `_Diag Asset`, `_TEST-PROG-*`, `Test Part IMM-15`, `Test WH IMM-15`, `Dräger Evita V500 — ICU-decom/-pm/-event/-trans`, etc.).

Lý do leak:
- `FrappeTestCase` rollback PER-test, không per-class. Test tạo doc trong `setUpClass` → commit → KHÔNG rollback.
- Test gọi service function `frappe.db.commit()` bên trong (lifecycle event, audit trail) → savepoint rollback không tới được.
- Test pass `delete=False` hoặc dùng `frappe.db.set_value` trực tiếp bypass ORM.

**Quy tắc:**

1. Mọi fixture tạo trong `setUpClass` PHẢI xoá trong `tearDownClass`:
   ```python
   @classmethod
   def tearDownClass(cls):
       for name in reversed(cls._created):  # reversed: children trước parents
           try:
               doc = frappe.get_doc(cls._dt_map[name], name)
               if doc.docstatus == 1:
                   doc.cancel()
               frappe.delete_doc(cls._dt_map[name], name, force=True,
                                 ignore_permissions=True, delete_permanently=True)
           except Exception:
               pass
       frappe.db.commit()
       super().tearDownClass()
   ```

2. Đặt prefix dễ grep, KHÔNG dùng pattern mơ hồ:
   - `_Test{Module}{Purpose}-{uniq}` — VD `_TestIMM15Asset-abc123`
   - **KHÔNG** dùng `_%` placeholder (`_` là SQL wildcard → match toàn bảng khi cleanup)
   - **KHÔNG** dùng tên giống real data (`Dräger Evita V500 — ICU-decom`) — sẽ confuse cleanup

3. **Pre-release verify** (mỗi sprint):
   ```bash
   bench --site miyano mariadb -e "
     SELECT 'AC Asset' AS dt, COUNT(*) FROM \`tabAC Asset\`
     WHERE LOWER(name) LIKE '%test%' OR LOWER(asset_name) LIKE '%test%'
     UNION ALL SELECT 'IMM Audit Trail', COUNT(*) FROM \`tabIMM Audit Trail\`
     WHERE LOWER(change_summary) LIKE '%_test%';"
   ```
   Tất cả phải = 0.

Reference: `CONVENTIONS.md §23 + §33`, `assetcore-deploy` Phần 3.

---

### R-10: KHÔNG chạy `bench run-tests` song song với destructive DB op

Bug 2026-05-27: trong lúc cleanup 13:55, test chạy parallel tạo data mới timestamps 14:31 → phải cleanup vòng 2.

**Trước khi cleanup hoặc destructive op:**
- [ ] `bench --site <site> set-maintenance-mode on`
- [ ] Confirm không có terminal khác chạy `bench run-tests`
- [ ] Scheduler tạm pause: `bench --site <site> disable-scheduler`
- [ ] Sau cleanup: `enable-scheduler` + `set-maintenance-mode off`

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

### 🛑 Playwright MCP Recovery Recipe (recurring blocker — 3 phiên: 2026-05-15, 16, 16)

Chrome MCP **chết sau 1-2 calls** trên môi trường này (software GL + ~1.8GB free RAM hoặc OOM khi RAM dùng ~12GB). Sau crash, lock file `Singleton*` còn lại → error `"Browser is already in use"` cho mọi call kế tiếp.

**Recovery (đã verify thành công ở 3 phiên):**

```bash
# B1 — kill toàn bộ chrome process từ MCP server
pkill -9 -f mcp-chrome-9a5b890 2>/dev/null
pkill -9 chrome 2>/dev/null

# B2 — xoá lock file (path có thể là ~/.cache/.../chrome-mcp/* tùy MCP setup)
find /tmp /home/miyano/.cache 2>/dev/null -name "Singleton*" -delete

# B3 — gọi browser_close trước khi browser_navigate lại
#       (nếu vẫn lỗi "in use" → cần USER restart MCP server, không tự fix được)
```

**Quy tắc khi MCP unstable:**

1. **Đừng burn turns trên kill-loop**. Sau 2 lần recovery fail → switch sang **static code audit** (3 parallel `assetcore-fe-cleaner` agents per module, có docs/imm-XX làm source-of-truth) như phiên 2026-05-15 IMM-04/05/06 đã làm.
2. **Tiết kiệm browser call**: `browser_navigate` tự snapshot pre-hydration (shell-only, vô dụng) → dùng `browser_snapshot`/`browser_evaluate` để lấy nội dung sau khi hydrate. 1 navigate = 1 snapshot/eval = 1 call ngân sách cho mỗi page.
3. **Không snapshot trang đã biết healthy** — chỉ snapshot trang đang test bug.
4. **Báo cho user sớm**: nếu phải fallback code-audit, nói rõ "Playwright MCP locked, switching to code audit" thay vì im lặng cố thêm.

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

> ⚠️ **TRUST `frontend/src/router/index.ts`, NOT this table** — routes change. Trước mọi session, chạy:
> ```bash
> grep -nE "path: '/" frontend/src/router/index.ts | head -80
> ```
> Table dưới đây là snapshot 2026-05-26.

| Module | List URL | Detail URL |
|---|---|---|
| IMM-01 Needs | `/needs-requests` | `/needs-requests/:id` |
| IMM-01 Plans | `/procurement-plans` | `/procurement-plans/:id` |
| IMM-02 TechSpec | `/tech-specs` | `/tech-specs/:id` |
| IMM-02 VendorEval | `/vendor-evaluations` | `/vendor-evaluations/:id` |
| IMM-03 Decisions | `/procurement-decisions` | `/procurement-decisions/:id` |
| IMM-03 Purchases | `/purchases` | `/purchases/:name` |
| IMM-06 Programs | `/imm06/programs` | `/imm06/programs/:name` |
| IMM-06 Sessions | `/imm06/sessions` | `/imm06/sessions/:name` |
| IMM-08 | `/pm/work-orders` | `/pm/work-orders/:id` |
| IMM-09 | `/cm/work-orders` | `/cm/work-orders/:id` |
| IMM-11 | `/calibration` | `/calibration/:id` |
| IMM-12 | `/incidents/list` | `/incidents/:id` |
| IMM-15 Dashboard | `/inventory` | (dashboard) |
| IMM-15 Movements | `/stock-movements` | `/stock-movements/:name` |
| IMM-15 Spare Parts | `/spare-parts` | `/spare-parts/:name` |
| IMM-16 Rules | `/compliance/rules` | `/compliance/rules/:id` |
| IMM-16 Findings | `/compliance/findings` | `/compliance/findings/:id` |
| IMM-16 CAPA | `/capas` | `/capas/:id` |
| Assets | `/assets` | `/assets/:id` |
| Suppliers | `/suppliers` | `/suppliers/:id` |

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

### LL-TEST-9: Fixture cho DocType autonamed PHẢI lookup theo business field, không phải `name`

Bug 2026-05-26: `test_imm08._ensure_cat("_TestCatIMM08")` dùng `frappe.db.exists("AC Asset Category", "_TestCatIMM08")` — nhưng DocType autoname là `CAT-####`, nên `name` không bao giờ bằng `_TestCatIMM08`. Lần chạy đầu insert thành công (autoname `CAT-0598`); lần thứ 2 lại insert tiếp → `UniqueValidationError` trên `category_name`.

```python
# ❌ SAI — name field là CAT-####, không phải category_name
if not frappe.db.exists("AC Asset Category", name):
    frappe.get_doc({"doctype": "AC Asset Category", "category_name": name}).insert(...)
    return name  # caller dùng làm FK → LinkValidationError

# ✅ ĐÚNG — lookup bằng field unique của business
def _ensure_cat(name: str) -> str:
    existing = frappe.db.get_value("AC Asset Category", {"category_name": name}, "name")
    if existing: return existing
    doc = frappe.get_doc({"doctype": "AC Asset Category", "category_name": name}).insert(...)
    return doc.name  # autoname (CAT-####)
```

**Quy tắc**: trước khi viết fixture, đọc `autoname` trong DocType JSON. Nếu autonamed → lookup qua `frappe.db.get_value({...filter...}, "name")` và trả về autoname thực tế.

### LL-TEST-10: Mass deletion test residue cần user approval — đừng tự chạy

Auto mode classifier chặn bulk DELETE/cancel trên DocTypes shared (Incident Report, AC Asset, Work Order, Audit Trail). Khi script cleanup cần xóa > vài chục records → STOP, báo user. Kể cả khi `_Test*` rõ ràng là rác.

**Quy tắc bulk-delete script**:
1. In TOÀN BỘ records sẽ xóa (name + tóm tắt) TRƯỚC khi xóa
2. Ask user confirm
3. Khi bị classifier block → KHÔNG tự lách — báo user

### LL-TEST-11: `frappe.get_all(..., limit_page_length=0)` vẫn bị permission-filter

Bug 2026-05-26: `frappe.get_all("Incident Report", limit_page_length=0)` chỉ trả 9 records dù DB có 188. Frappe áp permissions theo `frappe.session.user` ngay cả khi `limit_page_length=0`.

```python
# ❌ SAI — bị permission-filter
rows = frappe.get_all("Incident Report", limit_page_length=0)

# ✅ ĐÚNG — raw SQL cho cleanup/diagnostic
frappe.set_user("Administrator")
rows = [r[0] for r in frappe.db.sql("SELECT name FROM `tabIncident Report`")]
```

### LL-TEST-12: MySQL LIKE — `_` là wildcard, KHÔNG phải literal underscore

Bug 2026-05-26: filter `description LIKE '%_Test%'` không match `"_Test description"` đúng — `_` match 1 ký tự bất kỳ → false negative trong cleanup.

```python
# ❌ SAI
frappe.db.sql("SELECT name FROM tab WHERE x LIKE '%_Test%'")

# ✅ ĐÚNG (1) — ESCAPE
frappe.db.sql(r"SELECT name FROM tab WHERE x LIKE %s ESCAPE '\\'", (r"%\_Test%",))

# ✅ ĐÚNG (2) — Python substring filter (rõ nhất)
rows = frappe.db.sql("SELECT name, x FROM tab", as_dict=True)
test = [r for r in rows if "_Test" in (r.x or "")]
```

### LL-TEST-13: DOM probe regex KHÔNG đủ để khẳng định "code leak" — đọc parent context

Bug 2026-05-26 (false positive): `browser_evaluate` quét leaf-text `/AC-(SUP|LOC)-\d+/` thấy code → kết luận FE thiếu enrich. Sự thật: FE template hiển thị `name` (primary) + `code` (text-xs subtitle) trong 2 div riêng.

```javascript
// ❌ SAI — leaf text only, miss sibling chứa tên
[...document.querySelectorAll('*')]
  .filter(el => el.children.length === 0 && /AC-SUP-\d+/.test(el.textContent))

// ✅ ĐÚNG — đọc cả label + value group
[...document.querySelectorAll('dt, label')].map(lbl => ({
  label: lbl.textContent.trim(),
  valueGroup: lbl.nextElementSibling?.textContent?.trim() || '',
})).filter(f =>
  /AC-(SUP|LOC|DEPT)-\d+/.test(f.valueGroup) &&
  !/[A-ZĐ][a-zđ]/.test(f.valueGroup.replace(/AC-\w+-\d+/g, ''))  // value chỉ có code
)
```

**Quy tắc**: trước khi report code leak — verify KHÔNG có tên human-readable ở sibling div của value group.

### LL-TEST-14: "Detail thiếu workflow buttons" có thể là role-gating, KHÔNG phải bug

Bug 2026-05-26 (false positive): Calibration detail ở Scheduled không hiện nút "Bắt đầu hiệu chuẩn" → kết luận stuck. Sự thật: user Chu Hiếu thiếu role CAL_EXECUTE; FE `v-if="canExecuteCal"` ẩn đúng theo permission.

**Quy tắc kiểm chứng TRƯỚC khi report**:
1. Check user role (đọc Pinia auth store hoặc User doc)
2. Đọc `v-if` của button trong view file — nếu gate role thì expected
3. Real bug = state có valid transition trong workflow JSON, role check pass, mà vẫn không có button. UX gap (P3) = role hợp lệ nhưng thiếu empty-state "Không có hành động khả dụng".

### LL-TEST-15: `bench --site execute` cần callable trong app path, không phải `/tmp/`

Bug 2026-05-26: `/tmp/diag.py` + `bench execute assetcore.diag.run` → `ModuleNotFoundError`. Bench resolve qua Python import — phải nằm trong `apps/<app>/<app>/`.

```bash
# ❌ SAI
cp script.py /tmp/diag.py && bench --site miyano execute assetcore.diag.run

# ✅ ĐÚNG
cp script.py /home/miyano/frappe-bench/apps/assetcore/assetcore/diag.py
bench --site miyano execute assetcore.diag.run
rm /home/miyano/frappe-bench/apps/assetcore/assetcore/diag.py
```

### LL-TEST-16: `bench console` ăn stdin không in output — dùng `bench execute`

Bug 2026-05-26: `bench console <<'PYEOF' ... PYEOF` cho output rỗng. Console là IPython interactive, không phải REPL non-interactive — heredoc bị nuốt. Cho diagnostic/cleanup chạy 1 lần — luôn `bench execute <module.function>` với script file (xem LL-TEST-15).

### LL-TEST-17: tearDown vs `on_trash` audit guard — cancel-children procedure

Bug pattern recurring (2026-05-26 → fix 2026-05-27): `test_imm00/08/09` báo `errors=N` ở tearDownClass vì `AC Asset.on_trash` chặn delete khi còn Audit Trail / Lifecycle Event / Downtime Log. `force=True` KHÔNG bypass custom `on_trash`. Đặc biệt:
- `IMM Audit Trail.on_trash` throw `"Audit Trail records cannot be deleted (ISO 13485:7.5.9)"` — `delete_doc` LUÔN fail dù force=True. Phải dùng **raw SQL** cho audit (chỉ vì là fixture rác).
- `AC Asset.on_trash` (`ac_asset.py:225-256`) check 5 tables → còn 1 row là `LinkExistsError WR-03`.

```python
@classmethod
def tearDownClass(cls):
    asset_name = cls.asset.name
    # 1) Purge IMM Audit Trail TRƯỚC bằng RAW SQL (bypass ISO guard cho fixture rác)
    # ORM `delete_doc` luôn throw "ISO 13485:7.5.9" — except: pass sẽ swallow → asset không xoá được.
    frappe.db.sql(
        "DELETE FROM `tabIMM Audit Trail` "
        "WHERE asset=%s OR (ref_doctype='AC Asset' AND ref_name=%s)",
        (asset_name, asset_name),
    )
    # 2) Purge operational dependents (ORM được, vì các DocType này không có on_trash guard)
    for dt, fld in [
        ("PM Work Order", "asset_ref"), ("PM Schedule", "asset_ref"),
        ("Asset Repair", "asset_ref"), ("IMM Calibration Order", "asset_ref"),
        ("Incident Report", "asset"), ("Asset Lifecycle Event", "asset"),
        ("AC Asset Downtime Log", "asset"), ("Asset Document", "asset_ref"),
        ("Asset Transfer", "asset"),
    ]:
        if not frappe.db.table_exists(dt): continue
        for c in frappe.get_all(dt, filters={fld: asset_name}, pluck="name"):
            cd = frappe.get_doc(dt, c)
            if cd.docstatus == 1: cd.cancel()
            frappe.delete_doc(dt, c, force=True, ignore_permissions=True, delete_permanently=True)
    frappe.db.commit()
    # 3) AC Asset bây giờ delete được
    frappe.delete_doc("AC Asset", asset_name, force=True, ignore_permissions=True)
```

**KHÔNG dùng `try/except: pass`** quanh delete chain — exception bị nuốt = leak silently. Để exception propagate (test sẽ fail → bạn fix tearDown ngay, thay vì leak vào prod DB).

**Local-var fixtures** trong test method (`other = _make_asset("-other")`) PHẢI dùng `self.addCleanup(...)` ngay sau tạo — `tearDownClass` chỉ thấy `cls.*` → local var leak. Recurring incident: `test_imm08.py` test method tạo `other_asset = _make_asset("-other")` không cleanup → leak 6 `_Test Asset IMM08-other` qua nhiều run.

Reference: CONVENTIONS §23 + §39.

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
| English status leak | Cell hiển thị "Locked", "Evaluated", "Contract Signed" | FE: bổ sung key vào `STATUS_MAP` + `STATUS_COLOR` ở `utils/formatters.ts` |
| Frequency/enum English | "Weekly" thay vì "Hàng tuần" | FE: dùng local label map (vd `FREQUENCY_LABELS`) hoặc thêm key vào `STATUS_MAP` |
| Audit message English | "CAPA opened: severity=Minor" | BE: localize `change_summary` trong `log_audit_event(...)`; tránh f-string với enum English |
| Test data leak in prod | `_TEST-*`, `_Test *` xuất hiện trên UI | BE list service filter `name not like '\_Test%'`; cleanup orphan via bench console |
| HTTP 200 + envelope success=false | Page show "Lỗi server" nhưng network 200 | BE: check `frappe.log_error`; thường do null-deref trong service. Test phải đọc response body, không chỉ HTTP code |
| Orphan FK ref 500 | `AttributeError 'NoneType' has no attribute 'name'` | BE: every `Repo.get(fk)` PHẢI `if obj:` guard (xem LL-BE-X) |
| tearDown FAILED nhưng tests OK | `errors=N` không phải `failures=N` | Cancel-children procedure (xem LL-TEST-17), KHÔNG phải bug logic |
| Fixture unique-constraint sau re-run | `UniqueValidationError` ở insert thứ 2 | Autoname DocType → lookup by business field (xem LL-TEST-9) |
| Bulk delete bị classifier chặn | "denied by Claude Code auto mode classifier" | KHÔNG tự lách — báo user (xem LL-TEST-10) |
| `get_all(limit_page_length=0)` miss records | Cleanup script thấy ít rows hơn DB thực | Permission-filter ẩn; dùng raw SQL (xem LL-TEST-11) |
| LIKE `_X` match nhầm | Filter `%_Test%` không match `_Test...` | `_` là wildcard MySQL — dùng `ESCAPE '\\'` hoặc Python (xem LL-TEST-12) |
| False positive "code leak" | Leaf text bắt code nhưng sibling có name | Probe theo label+valueGroup, không leaf-text (xem LL-TEST-13) |
| False positive "stuck workflow" | Button thiếu vì role-gate | Check user role trước khi report (xem LL-TEST-14) |

### LL-TEST-9: Discover URLs from `router/index.ts` — KHÔNG trust skill mapping

Bug session 2026-05-26: skill mapping ghi `/imm01/needs-requests` nhưng route thực là `/needs-requests` → 404. Wasted 1 chu kỳ tool call.

**Quy tắc:**
```bash
# Đầu session, dump tất cả routes:
grep -nE "path: '/" frontend/src/router/index.ts > /tmp/routes.txt
# Khi 404, grep ngay route đúng:
grep -i "<module-keyword>" /tmp/routes.txt
```
Khi bị 404 → ĐỪNG đoán biến thể; mở `router/index.ts` và xác minh path chính xác.

### LL-TEST-10: Playwright MCP browser lock — cleanup procedure

Bug session 2026-05-26: nhiều lần `Error: Browser is already in use for /home/miyano/.cache/ms-playwright/mcp-chrome-XXXXX` → tool calls failed liên tiếp.

**Quy tắc khi gặp lock:**
```bash
rm -rf /home/miyano/.cache/ms-playwright/mcp-chrome-*/SingletonLock \
       /home/miyano/.cache/ms-playwright/mcp-chrome-*/SingletonCookie \
       /home/miyano/.cache/ms-playwright/mcp-chrome-*/SingletonSocket 2>/dev/null
pkill -9 -f "ms-playwright/chromium\|mcp-chrome" 2>/dev/null
sleep 2
```
Sau đó retry `browser_navigate`. Đừng spawn nhiều shell `browser_*` parallel trên cùng session — chỉ 1 browser context.

### LL-TEST-11: Role-gated buttons KHÔNG phải bug — verify quyền user test trước

Bug session 2026-05-26: tester `chuvanhieu357@gmail.com` không có `ROLES_TRAINING_MANAGE` → IMM-06 detail không hiển thị "Chỉnh sửa", "Lưu trữ" → tưởng B-IMM06-2/4. Thực ra RBAC đúng — nút role-gated.

**Quy tắc:**
1. Đầu session, dump roles của tester:
   ```bash
   bench --site miyano console <<< "import frappe; print(frappe.get_roles('chuvanhieu357@gmail.com'))"
   ```
2. Khi thấy "list/detail thiếu nút" → grep FE component xem có `v-if="canManage"` / `useCapabilities()` / `hasAnyRole(...)` không. Nếu có → KHÔNG report là bug; ghi rõ "role-gated, needs <role> to test".
3. Để test full coverage, cần 4 user accounts (Admin / User / Auditor / Vendor-tech) — single-account session chỉ cover được subset.

### LL-TEST-12: Sau fix BE Python — verify dev server đã reload trước khi test FE

Bug session 2026-05-26: sửa `services/imm16.py:get_capa` nhưng werkzeug auto-reload đôi khi không pick up → FE vẫn 500. Mất thời gian debug.

**Quy tắc post-fix BE:**
```bash
# 1. Trigger reload bằng cách hit endpoint qua bench (ngoài HTTP layer):
bench --site miyano execute assetcore.services.<module>.<func> --args '[...]'
# Nếu raise lỗi → fix code (không phải reload issue)
# Nếu OK → kiểm tra HTTP qua Playwright fetch
```
Nếu BE OK qua bench nhưng HTTP vẫn lỗi → restart bench: `pkill -f "honcho start" && bench start &`.

### LL-TEST-13: Khi fix có dùng `frappe.db.get_value(doctype, name, "fieldX")` — verify fieldX tồn tại TRƯỚC

Bug session 2026-05-26: thêm enrich `subject = frappe.db.get_value("Incident Report", x, "subject")` → 500 `(1054, "Unknown column 'subject'")` vì IR field là `description`, không phải `subject`.

**Quy tắc:**
```bash
# Trước khi viết get_value với field mới, grep DocType JSON:
grep -E "\"fieldname\":" assetcore/assetcore/doctype/<doctype_snake>/<doctype_snake>.json
```
Hoặc Python:
```python
fields = [f.fieldname for f in frappe.get_meta("Incident Report").fields]
assert "subject" in fields, f"Field 'subject' không tồn tại; có sẵn: {fields}"
```

### LL-TEST-18: Test hook chain cross-module — bắt buộc cho mọi service `complete_*` / `submit_*` (2026-05-27)

**Bug pattern G2:** 5/11 bug là hook chain không wire (RC-03/04/06/07/11). Tests đã PASS vì test chỉ check transition state, không check downstream record có được tạo.

**Quy tắc test cho mọi terminal transition cross-module:**

1. **Test xác minh chain wire** (assert B exists sau A complete):
   ```python
   def test_complete_acceptance_creates_asset(self):
       """RC-06: phiếu nghiệm thu Hoàn tất → AC Asset tự sinh"""
       acc = self._create_acceptance_to_completion_stage()
       imm04_api.complete_acceptance(acc.name)
       asset_name = frappe.db.exists("AC Asset", {"source_acceptance": acc.name})
       self.assertTrue(asset_name, "Hook chain ACC→Asset failed silently")
       # Cross-check: asset link back đúng
       asset = frappe.get_doc("AC Asset", asset_name)
       self.assertEqual(asset.source_acceptance, acc.name)
   ```

2. **Test idempotency** (gọi 2 lần không duplicate):
   ```python
   def test_complete_acceptance_idempotent(self):
       acc = self._create_acceptance_to_completion_stage()
       imm04_api.complete_acceptance(acc.name)
       count_1 = frappe.db.count("AC Asset", {"source_acceptance": acc.name})
       # Re-trigger (simulate retry / scheduler re-run)
       imm04_api.complete_acceptance(acc.name)  # phải no-op hoặc raise BAD_STATE
       count_2 = frappe.db.count("AC Asset", {"source_acceptance": acc.name})
       self.assertEqual(count_1, count_2, "Idempotency broken — created duplicate B")
   ```

3. **Test audit trail có triggered_record**:
   ```python
   def test_complete_audit_links_triggered_record(self):
       acc = self._create_acceptance_to_completion_stage()
       imm04_api.complete_acceptance(acc.name)
       asset_name = frappe.db.exists("AC Asset", {"source_acceptance": acc.name})
       audit = frappe.db.exists("IMM Audit Trail", {
           "doc_name": acc.name,
           "action": ["like", "%completed%"],
           "triggered_record": asset_name,
       })
       self.assertTrue(audit, "Audit log thiếu triggered_record cho chain")
   ```

4. **Test chain failure bubbles up** (không silent):
   ```python
   def test_complete_chain_failure_raises(self):
       """Nếu service B raise, complete_A phải raise (không try/except: pass)"""
       acc = self._create_acceptance_to_completion_stage()
       with patch("assetcore.services.imm05.create_asset_from_acceptance",
                  side_effect=ServiceError(ErrorCode.VALIDATION, "test")):
           with self.assertRaises(ServiceError):
               imm04_api.complete_acceptance(acc.name)
       # Acceptance state phải rollback (transaction)
       acc.reload()
       self.assertNotEqual(acc.workflow_state, "Completed")
   ```

Reference: `CONVENTIONS.md §40`, `assetcore-be` LL-BE-23, `assetcore-audit` Pillar 9, `docs/res/reports/AssetCore_Test_Plan_NextRound_1_Analysis.md` §3.

### LL-TEST-19: Test permission gate cho mọi mutating endpoint (2026-05-27)

**Bug pattern P1 chưa cover (AUTH-02):** test suite hiện chỉ chạy bằng Admin user → không bắt được BE whitelist thiếu `rbac.require()`.

**Quy tắc:**

1. **Mỗi mutating `@frappe.whitelist()` endpoint PHẢI có test reject low-role**:
   ```python
   class TestImm12Permissions(unittest.TestCase):
       @classmethod
       def setUpClass(cls):
           # Tạo user role thấp (vd: chỉ Người dùng hệ thống, không phải QA Manager)
           cls.low_user = make_test_user(roles=["Người dùng hệ thống"])
           cls.doc_name = create_test_incident()

       def test_close_rejects_low_role(self):
           frappe.set_user(self.low_user)
           with self.assertRaises(ServiceError) as ctx:
               imm12_api.close_incident(self.doc_name)
           self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)
   ```

2. **Test cover toàn bộ matrix** (mỗi mutating endpoint × mỗi role không hợp lệ):
   ```python
   def test_permission_matrix(self):
       """Reject nếu user thiếu role; allow nếu có"""
       cases = [
           ("low_user",  imm12_api.close_incident, "FORBIDDEN"),
           ("qa_user",   imm12_api.close_incident, "ok"),
           ("admin",     imm12_api.close_incident, "ok"),
           ("vendor_tech", imm12_api.close_incident, "FORBIDDEN"),  # vendor isolation
       ]
       for user, fn, expected in cases:
           frappe.set_user(getattr(self, user))
           if expected == "FORBIDDEN":
               with self.assertRaises(ServiceError) as ctx:
                   fn(self.doc_name)
               self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)
           else:
               fn(self.doc_name)
   ```

3. **Test direct API call bypass FE** (simulate AUTH-02):
   ```python
   def test_admin_endpoint_via_session_low_role(self):
       """User quyền thấp gọi trực tiếp endpoint admin — phải bị chặn"""
       frappe.set_user(self.low_user)
       with self.assertRaises(ServiceError):
           # Gọi endpoint mà FE đã ẩn nút — verify BE không tin FE
           imm00_api.delete_asset(self.asset_name)
   ```

4. **Test row-level filter** (vendor isolation):
   ```python
   def test_vendor_cannot_see_other_assets(self):
       frappe.set_user(self.vendor_user)
       assets = imm00_api.list_assets({})
       # Phải chỉ thấy asset assigned to vendor — không thấy asset khác
       self.assertTrue(all(a["assigned_vendor"] == self.vendor_id for a in assets["data"]))
   ```

5. **Helper `make_test_user`** chuẩn:
   ```python
   def make_test_user(roles, email=None):
       email = email or f"_test_{frappe.generate_hash()[:8]}@test.local"
       user = frappe.get_doc({
           "doctype": "User",
           "email": email,
           "first_name": "Test",
           "enabled": 1,
           "roles": [{"role": r} for r in roles],
       }).insert(ignore_permissions=True)
       return email
   ```

Reference: `CONVENTIONS.md §41`, `assetcore-be` LL-BE-24, `assetcore-audit` Phần 5 Check S-9/S-10/S-11.

### LL-TEST-20: Test KPI scope consistency — count khớp giữa tile và list filter (2026-05-27)

**Bug pattern RC-09, RC-10:** Dashboard tile và /pending list cho count khác nhau.

**Quy tắc:**

1. **Mỗi KPI tile clickable PHẢI có test xác minh count = list filter count**:
   ```python
   def test_kpi_pending_approvals_matches_list(self):
       """RC-09: /dashboard count = /approvals/pending count với cùng scope"""
       frappe.set_user(self.qa_user)
       seed_pending_approvals(count=3, assigned_to=self.qa_user)
       seed_pending_approvals(count=2, assigned_to="other@test")  # không thuộc qa_user

       # KPI "Của tôi"
       kpi_mine = approvals_api.count_pending(scope="mine")
       list_mine = approvals_api.list_pending(scope="mine")
       self.assertEqual(kpi_mine, len(list_mine["data"]))
       self.assertEqual(kpi_mine, 3)

       # KPI "Toàn hệ thống"
       frappe.set_user(self.admin_user)
       kpi_all = approvals_api.count_pending(scope="all")
       list_all = approvals_api.list_pending(scope="all")
       self.assertEqual(kpi_all, len(list_all["data"]))
       self.assertEqual(kpi_all, 5)
   ```

2. **Test phân biệt scope rõ ràng**:
   ```python
   def test_kpi_scopes_are_distinct(self):
       seed_pending_approvals(count=3, assigned_to=self.qa_user)
       seed_pending_approvals(count=2, assigned_to="other@test")
       frappe.set_user(self.qa_user)
       self.assertNotEqual(
           approvals_api.count_pending(scope="all"),  # = 5
           approvals_api.count_pending(scope="mine"), # = 3
           "KPI scope phải cho 2 số khác nhau khi data thực khác"
       )
   ```

Reference: `CONVENTIONS.md §43`, `assetcore-fe` LL-FE-29.
