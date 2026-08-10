# Backend Tests (Python/Frappe) — deep reference

> Heavy reference cho `assetcore-test` SKILL.md **Phần 1 — Backend Tests**. Đọc khi viết/sửa
> unit test service layer, workflow smoke test, UAT, fixture cleanup. Nguyên tắc bất biến
> (R-0..R-12) và Verification ở SKILL.md — file này là chi tiết template + lessons.

## Project layout
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

## Chạy tests
```bash
bench --site miyano run-tests --app assetcore
bench --site miyano run-tests --module assetcore.tests.test_immXX
bench --site miyano run-tests --module assetcore.tests.test_immXX --test TestRepairCreation
bench --site miyano run-tests --skip-test-records  # faster iteration
```

## Standard test file template
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

## Service-layer tests (preferred — nhanh, không cần DB)
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

## Permission tests
```python
def test_technician_cannot_close_wo(self):
    frappe.set_user("technician@test.com")
    try:
        with self.assertRaises(frappe.PermissionError):
            close_work_order(self.wo.name, ...)
    finally:
        frappe.set_user("Administrator")  # PHẢI restore trong finally
```

## Workflow smoke test
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

## UAT script
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

## Conventions — Backend

- `setUpClass` cho fixtures dùng chung; `setUp` cho per-test state.
- **Backend unit test**: LUÔN prefix fixtures với `_Test` — Frappe rollback tự động.
- Tests phải chạy được trên fresh site — `setUpClass` self-seed mọi dependency.
- Không mock database — Frappe wrap mỗi test trong savepoint, rollback tự động.
- Pre-existing test failure PHẢI fix trong cùng sprint phát hiện.

## Fixture rules (học từ bug thực tế)
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

## R-9 fixture cleanup — `tearDownClass` template

> Moved từ SKILL.md R-9 (progressive disclosure). Rule statement (fixture `setUpClass` PHẢI dọn ở
> `tearDownClass`) ở SKILL.md R-9; đây là code template. Asset đi qua `on_trash` guard → ưu tiên
> `_asset_cleanup.purge_asset` (LL-TEST-22, LL-TEST-17). Template generic dưới đây cho fixture
> KHÔNG có ISO/LinkExists guard:

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

> ⚠️ `try/except: pass` ở trên CHỈ chấp nhận cho fixture generic không-guard. Với chain delete đụng
> `on_trash` guard (Asset/Audit Trail) → KHÔNG nuốt exception (LL-TEST-17/22): để propagate, dùng
> raw-SQL purge audit + cancel-children procedure.

## Coverage targets
Priority: Validators → Service entrypoints → Permission gates → Status transitions.
Skip: trivial getters, Frappe internals, DocType property accessors.

## Event-driven / side-effect feature — assert SIDE-EFFECT, không chỉ return (chống false-green)
> Học từ bug Notification V2 (2026-05-29): `notify_approval_pending` hard-code state/role không khớp workflow thật → feature **chết** nhưng test vẫn **PASS** vì test data dựng theo đúng giả định sai (dựng state nằm trong tập hard-code, gán field `supervisor`). Test xanh ≠ feature chạy.

Với notification / escalation / hook chain / scheduler / SLA — test PHẢI:
1. **Verify side-effect THẬT xảy ra**, không chỉ hàm return không lỗi: notification → assert có row `Notification Log` cho đúng recipient; hook chain A→B → assert doc B tồn tại (LL-BE-23); email → assert có Email Queue row.
2. **Dùng workflow/data THẬT của module**, đừng dựng data khớp giả định của chính code đang test. Recipient resolve phải **non-empty** trên workflow production (LL-BE-30 rule #4).
3. **Scheduler/background function**: gọi trực tiếp hàm scan với data dựng sẵn (đừng chờ cron), assert đúng số notification + anti-spam (chạy 2 lần không nhân đôi). Verify hàm thực sự đăng ký `scheduler_events` (LL-BE-32).
4. **RED phải fail vì lý do đúng**: trước khi viết fix, confirm test fail vì side-effect KHÔNG xảy ra — không phải vì assertion gõ sai. Pass ngay từ đầu trên feature mới = nghi ngờ false-green, kiểm lại side-effect có thật được assert.

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

---

## Lessons Learned — Backend test-execution patterns

> Các LL-TEST/LL-QA dưới đây là bug đã gặp khi viết/chạy backend test. Playwright/UI-specific
> lessons ở [`playwright-ui-tests.md`](playwright-ui-tests.md). LL-QA-9/10/11 ở [`playwright-patterns.md`](playwright-patterns.md).

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

Reference: LL-TEST-22, R-9.

### LL-TEST-13 (BE): Khi fix có dùng `frappe.db.get_value(doctype, name, "fieldX")` — verify fieldX tồn tại TRƯỚC

Bug session 2026-05-26: thêm enrich `subject = frappe.db.get_value("Incident Report", x, "subject")` → 500 `(1054, "Unknown column 'subject'")` vì IR field là `description`, không phải `subject`.

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

Reference: `assetcore-be` LL-BE-23, `assetcore-audit` Pillar 9, `docs/res/reports/AssetCore_Test_Plan_NextRound_1_Analysis.md` §3.

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

Reference: `assetcore-be` LL-BE-24, `assetcore-audit` Phần 5 Check S-9/S-10/S-11.

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

Reference: `assetcore-fe` LL-FE-29.

### LL-TEST-21: `tests_ran`/`PASS` chỉ true khi chạy THẬT `bench run-tests` + ĐỌC output (chống false-green) (LL-QA-4)

Triệu chứng→nguyên nhân: set `tests_ran=true`/`verdict=PASS` từ code-grep hoặc giả định → false-green. Pass-ngay-lần-đầu trên feature side-effect (notification/hook/SLA) thường che bug (xem §Event-driven). Phải đọc output mới biết: `errors=1` ở `setUpClass` abort cả class → đếm test sụt (631 vs 624) mà grep không thấy.

**Rule kiểm-được:**
1. Chạy THẬT `bench --site miyano run-tests --app assetcore` (hoặc `--module assetcore.tests.test_<x>`).
2. ĐỌC dòng tổng nguyên văn: `Ran N tests ... OK` / `FAILED (failures=.., errors=..)` — báo số pass/fail từ output, KHÔNG suy đoán.
3. Phân biệt `errors=N` ở tearDown (cancel-children, xem LL-TEST-17) ≠ `failures=N` logic.
4. Pass ngay lần đầu trên feature side-effect mới = NGHI false-green → kiểm side-effect có THẬT được assert (§Event-driven assert side-effect).

Reference: `memory/factory_rounds_6_10_20260602.md`, §Event-driven, LL-TEST-17.

### LL-TEST-22: Fixture `setUpClass` PHẢI dọn ở `tearDownClass` qua `tests/_asset_cleanup.py::purge_asset` (LL-QA-5)

Triệu chứng→nguyên nhân: doc tạo trong `setUpClass` → commit → KHÔNG rollback per-test (R-9). Asset đi qua `on_trash` guard (`force=True` KHÔNG bypass ISO/LinkExists) → leak thật đã gặp: 53 asset + 21 part + 21 warehouse.

**Rule kiểm-được:**
1. Asset cleanup dùng `from assetcore.tests._asset_cleanup import purge_asset` — raw-SQL purge IMM Audit Trail + Asset Lifecycle Event + Asset Document (cả 3 có `on_trash` guard không bypass được), cancel children docstatus=1 trước (xem LL-TEST-17).
2. **KHÔNG** `try/except: pass` quanh delete chain → nuốt exception = leak thầm. Để exception propagate.
3. Local-var fixture trong test method → `self.addCleanup(...)` NGAY (`tearDownClass` chỉ thấy `cls.*`).
4. Pre-release verify count `%test%` = 0 (R-9).

Reference: `assetcore/tests/_asset_cleanup.py`, R-9, LL-TEST-17, `memory/test_session_20260529_wave1.md`.

### LL-TEST-23: AC Asset Category — tra cứu + cleanup theo field `category_name`, KHÔNG theo `name` (LL-QA-6)

Triệu chứng→nguyên nhân: `autoname: autoname` → `name = CAT-####` series ≠ `category_name`. `frappe.db.exists("AC Asset Category", X)` LUÔN miss (PK là `CAT-####`) → insert lần 2 → `UniqueValidationError` trên index `category_name`, row leak hiện raw `CAT-####` trên UI (đã gặp 3×).

**Rule kiểm-được:** mọi test đụng AC Asset Category PHẢI:
- Tra tồn tại: `frappe.db.get_value("AC Asset Category", {"category_name": X}, "name")`.
- Cleanup/delete: resolve real name qua `frappe.get_all(filters={"category_name": X}, pluck="name")` rồi delete.

Reference: LL-TEST-9 (cùng pattern autoname), `memory/factory_rounds_6_10_20260602.md`, `_purge_category`.

### LL-TEST-24: Flaky QueryDeadlock — retry đúng module 1 LẦN rồi mới kết luận (LL-QA-7)

Triệu chứng→nguyên nhân: `bench run-tests` báo `QueryDeadlockError`/`LockWaitTimeout`/`OperationalError 1213` — infra-transient, thường do chạy `run-tests` song song destructive DB op (R-10), KHÔNG phải regression logic.

**Rule kiểm-được:**
1. Re-run đúng module 1 LẦN: `--module assetcore.tests.test_<x>`. Pass lần 2 = flaky → ghi nhận, KHÔNG block vòng.
2. Vẫn fail lần 2 = bug thật.
3. KHÔNG retry-vô-hạn để "làm xanh" (che bug). KHÔNG chạy `run-tests` song song destructive DB op (R-10) — chính là nguồn deadlock.

Reference: R-10, `memory/factory_rounds_6_10_20260602.md`.

### LL-TEST-25: Reload gunicorn TRƯỚC Playwright live khi đã sửa `api/`/`services/` .py — `--preload` đông cứng import (LL-QA-8)

Triệu chứng→nguyên nhân: gunicorn boot `--preload` → sửa `api/*.py`/`services/*.py` SAU boot CHỈ live ở `bench run-tests`/`bench execute` (fresh import), CHƯA live HTTP tới khi USER reload (HARD-STOP — BE/QA KHÔNG tự reload/restart/migrate). 417 phantom + guest-403 KHÔNG phải dấu hiệu stale.

**Rule kiểm-được — trước Playwright xác minh fix BE:**
1. `bench execute assetcore.api.<mod>.<fn>` chạy được = code OK (LL-TEST-12).
2. Nếu (1) OK mà HTTP vẫn lỗi cũ → nghi STALE-WORKER → báo USER reload, KHÔNG kết luận FE bug.
3. Sau USER reload mới chạy Playwright live.

Reference: `memory/gunicorn_preload_staleness.md`, `references/playwright-patterns.md:136` (LL-BE-16), LL-TEST-12.

### LL-TEST-26: Test PHẢI assert HIỆN-VẬT/RÀNG-BUỘC THẬT, KHÔNG proxy cấu trúc (false-green SÂU) (LL-QA-12)

Triệu chứng→nguyên nhân: test PASS nhưng KHÔNG bắt bug vì assert PROXY thay cho hành vi thật (đã gặp 2026-06-11, 3 lần):
- guard `_assert_200_oneof_discriminator` chỉ assert `propertyName=="success"` (CÓ key) — KHÔNG assert `type=="string"` → khoá-cứng `discriminator` trên property **boolean** = OAS-illegal (openapi-generator drop/sinh code hỏng). 57 test xanh, contract vẫn vỡ.
- test đếm SỐ BLOCK HTML thay vì SỐ TRANG PDF THẬT → nhãn tràn trang-2 vẫn "xanh" (BUG-LABEL-1).
- test gọi `openapi.spec()` Python-direct assert `dict['openapi']` → KHÔNG test HTTP wire → bỏ sót Frappe bọc `{message:}` làm Swagger render trắng (F-C1 blind-spot).

**Rule kiểm-được — khi viết/duyệt 1 guard test:**
1. Assert HIỆN-VẬT THẬT cuối cùng mà user/integrator chạm: trang PDF thật (`pypdf` page+MediaBox), **HTTP wire body** (không Python-return), kiểu+ràng-buộc OAS thật (`type=="string"` không chỉ "có key"), pixel render (Playwright) — KHÔNG proxy (đếm HTML block, "có key", "không-touch-nên-xanh").
2. Thêm guard → ghi RÕ failure-mode nó chặn + confirm RED fail ĐÚNG vì failure đó (LL-TEST-21 §4). "Có-mặt" (`assertIn` key) ≠ "đúng-ràng-buộc" (`assertEqual` type/value).
3. Pass NGAY trên fix vừa thêm guard = NGHI proxy → hỏi "revert fix thì test này có ĐỎ không?". Không đỏ = proxy, viết lại.

Reference: LL-TEST-21 §4, memory `mobile_be_openapi_contract_gotchas` (#3 boolean-discriminator, #4 {message:} envelope), session 2026-06-11.

### LL-TEST-27: Sửa SSoT introspect-được → chạy LẠI MỌI suite assert nó; KHÔNG báo aggregate từ giả định (LL-QA-13)

Triệu chứng→nguyên nhân: báo "full suite xanh, 285" = SỐ HỌC BỊA (cộng con số per-module nhớ/giả định, CHỈ chạy thật module vừa sửa). Module KHÁC (không đụng source) assert vào spec introspect ĐỘNG → endpoint mới (`imm00.print_asset_labels_pdf`) đẩy count 486→487 ⇒ 4 module `test_oas_d10/d12/d15/d17` (hardcode `assertEqual(total,486)`) ĐỎ, nhưng QA báo xanh vì "không touch nên giả định xanh" (gặp 2026-06-11; biến thể LL-TEST-21).

**Rule kiểm-được:**
1. Thay đổi đụng SSoT DÙNG-CHUNG introspect-được (tổng endpoint, cap-set version, status/label map, schema components) → CHẠY LẠI MỌI suite assert vào nó (vd toàn bộ `test_oas_*`+`test_mobile_*`), KHÔNG chỉ module vừa sửa.
2. KHÔNG báo aggregate ("N xanh") bằng cộng số per-module nhớ/giả định — chỉ tính từ output `Ran N OK` THẬT của lượt chạy này. Module KHÔNG chạy lượt này = KHÔNG được tính "xanh".
3. Baseline hardcode (vd `total==486`) = nợ kỹ thuật: ưu tiên derive ĐỘNG; khi mismatch → re-baseline + XÁC NHẬN delta là endpoint hợp lệ mới (không phải mất/thừa do bug) + sweep `grep` sửa MỌI nơi hardcode (đã có 4 file lệch cùng lúc).

Reference: LL-TEST-21, session 2026-06-11 (4 oas false-green do drift 486→487).

### LL-TEST-28: Eval/persona tạo USER login + data scoped throwaway → PHẢI dọn (tidy mở rộng sang DB) (LL-QA-14)

Triệu chứng→nguyên nhân: agent [USER]/eval tạo user login throwaway (`eval_tech@example.com`/`eval_vendor@example.com`) + asset/data scoped để verify RBAC persona → để LẠI trong DB (tidy-eval-artifacts CHỈ dọn FILE, không dọn DB) → user/data rác hiện trên UI thật (gặp 2026-06-11 cùng `ZZTEST-BYT-*`).

**Rule kiểm-được:**
1. Eval/persona tạo User login hoặc data scoped → tear-down CUỐI eval (delete user+data); nếu cần USER duyệt xoá (mass/production-like) → ghi DANH SÁCH CHÍNH XÁC vào `open_issues`/STATE 🔴 "chờ purge" (KHÔNG để lọt im lặng).
2. Ưu tiên `_Test`-prefix + Frappe auto-rollback (LL-TEST-22) thay vì user/data commit thật khi có thể.
3. "Xong" của eval = file artifact dọn (tidy-eval-artifacts, LL-AUDIT-13) **VÀ** DB test-user/data đã dọn-hoặc-flag. Verdict KHÔNG Pass khi còn user/data rác chưa khai báo.

Reference: LL-AUDIT-13 (tidy file), LL-TEST-22 (asset cleanup), `references/playwright-patterns.md` (persona cần user+pw), session 2026-06-11.

### LL-TEST-29: Test OUTPUT SINH RA → assert ARTIFACT THẬT đã render, KHÔNG assert template trung gian (false-green) (LL-QA-15 sibling)

Triệu chứng→nguyên nhân: `test_one_page_per_asset` (BUG-LABEL-1, 2026-06-11) đếm `html.count('<div class="label"')` == N rồi SUY RA "N trang" → PASS, NHƯNG PDF render THẬT có trang trắng (1 asset → 2 trang). Đếm thẻ HTML / đoạn template ≠ đếm output thật — template đúng vẫn render sai (overflow, page-break, MediaBox). Biến thể cụ thể của LL-TEST-26 cho output file/ảnh/PDF.

**Rule kiểm-được — test mọi PDF/ảnh/file SINH RA:**
1. Assert trên ARTIFACT ĐÃ RENDER, không trên template/HTML trung gian:
   - PDF: `len(pypdf.PdfReader(BytesIO(pdf_bytes)).pages)` + MediaBox dims (kích thước trang thật).
   - Ảnh: decode/pixel (PIL `Image.open(BytesIO(...)).size` / kiểm pixel), KHÔNG đếm `<img>`/data-URI.
2. Red-flag: "đếm phần tử template (block/div/thẻ) rồi SUY RA output đúng" → STOP, render artifact thật mà đếm.
3. Pass ngay khi vừa thêm guard đếm-template = NGHI proxy (LL-TEST-26 §3): "revert fix → test có ĐỎ không?". Không đỏ = proxy, viết lại assert trên artifact render.

Reference: LL-TEST-26 (proxy cấu trúc), BUG-LABEL-1 session 2026-06-11.

### LL-QA-15: `bench run-tests` xanh ≠ LIVE HTTP xanh — verdict `blocked-reload` khi BE `.py` sửa sau gunicorn `--preload` boot

Triệu chứng→nguyên nhân: 2026-06-11 — lỗi user "Không thể tạo PDF nhãn" = gunicorn `--preload` worker STALE (boot TRƯỚC khi tạo endpoint; `curl` → 417 "module … has no attribute"), KHÔNG phải bug code. Factory verify bằng `run-tests` (fresh-import) = false-green: code MỚI live ở `bench run-tests`/`bench execute` nhưng CHƯA live trên HTTP (worker đông cứng import — xem LL-TEST-25).

**Rule kiểm-được:**
1. BE `.py` (`api/*.py`/`services/*.py`) sửa SAU gunicorn `--preload` boot → CHỈ live ở `bench run-tests`/`bench execute`, CHƯA live HTTP. `bench run-tests` xanh KHÔNG chứng minh feature live trên HTTP/Playwright/in-thật/quét-thật.
2. QA/USER cho việc cần HTTP / Playwright / in-thật (PDF nhãn, máy in tem) / quét-QR → verdict **`blocked-reload`**. TUYỆT ĐỐI KHÔNG tuyên bố "đã verify live / trên HTTP / máy in tem" khi chưa reload.
3. Chỉ USER `bench restart` + `clear-cache` mới mở khoá (HARD-STOP — BE/QA KHÔNG tự reload/restart/migrate). Sau USER reload mới chạy Playwright/HTTP live rồi đổi verdict.

Reference: LL-TEST-25 (`--preload` đông cứng import), `memory/gunicorn_preload_staleness.md`, session 2026-06-11.

### LL-TEST-30: Đa-phiên chạy test trên CÙNG site DB → full BE suite ĐỎ là NHIỄM BẨN, KHÔNG phải regression (2026-06-29)

**Triệu chứng→nguyên nhân:** audit session — full `bench run-tests --app assetcore` báo 11 fail + 21 error, dễ kết luận "tôi làm hỏng". Thực tế nhiều phiên `/build auto` chạy test ĐỒNG THỜI trên cùng site `miyano` → fixtures `_Test*` rò rỉ (commit qua savepoint) → va chạm. Bằng chứng: `test_gmdn_cascade` setUp đỏ NGAY CẢ KHI chạy ĐỘC LẬP tại `ac_asset_category.py _validate_gmdn_unique` (GMDN-unique collision với category `_Test` leak) — không phải code mới. Triệu-chứng nhiễm: `tearDownClass` errors hàng loạt (capa/imm00_smoke/imm16), count-invariant fail (reserved_prefix, byt_expiry), gmdn-unique collision.

**Rule (kiểm được):** khi nghi đa-phiên (xem `[[multi_session_concurrency]]`):
1. **FE vitest = tín hiệu TIN CẬY** (isolated, không đụng DB) → dùng làm gate chính; full BE suite trên shared DB KHÔNG tin được pass/fail tổng.
2. **Cô lập trước khi quy lỗi**: chạy LẠI module nghi ngờ một mình (`run-tests --module X`); vẫn đỏ ở `setUp`/unique-collision/teardown ⇒ NHIỄM BẨN (leaked fixture), KHÔNG phải bug của bạn. TUYỆT ĐỐI không "sửa cho xanh" cái không phải lỗi mình.
3. **Việc của bạn vẫn phải xanh KHI chạy isolated** — verify từng module mình đụng chạy riêng (xanh) thay vì tin con số tổng nhiễm bẩn.
4. Clean BE verification THẬT chỉ khả thi khi **1 phiên duy nhất** + DB đã purge leak → đề xuất user consolidate rồi chạy 1 lần sạch. Cross-ref: LL-TEST-15 (fixture leak), LL-BE-15 (no shared-reuse fixture), `[[multi_session_concurrency]]`; session audit 2026-06-29.

### LL-TEST-31: Guard counter (`_EXPECTED_TEST_COUNT`/guard-sum/số path OAS) ĐỌC TỪ ĐĨA và chấm DELTA — lệch số ≠ đỏ (2026-07-28)

**Triệu chứng→nguyên nhân:** prompt/STATE đầu run ghi `983 / 1126 / 1152`; đĩa thực tế `1024 / 1167 / 1193` (các phiên song song đã land AC-CR-80..86). Agent mất thời gian điều tra "mình làm hỏng gì?", suýt dừng vòng và suýt "sửa cho khớp" con số cũ. Cùng run còn ca ngược: prompt ghi 278 file test FE, đĩa 284. Nguyên nhân cấu trúc: mọi con số baseline đi kèm prompt là **ảnh chụp tại thời điểm soạn**, trong khi working tree bị nhiều phiên ghi đồng thời.

**Rule (kiểm được):**
1. **Đo lại từ đĩa** trước khi dùng bất kỳ counter nào (`grep -n "_EXPECTED_TEST_COUNT" assetcore/tests/*.py`, đếm file thật) — KHÔNG lấy số trong prompt/STATE/handoff làm chuẩn.
2. **Chấm DELTA, không chấm tuyệt đối:** câu hỏi đúng là "vòng này làm số đó tăng/giảm bao nhiêu", không phải "số đó có bằng STATE không". Lệch so với STATE = STATE stale ⇒ **cập nhật STATE**, không dừng run, không sửa code cho khớp.
3. **Chỉ cập nhật counter khi CHÍNH vòng này thêm/bớt test**, và ghi rõ delta trong báo cáo (vd `983 → 1024 (+41, do phiên khác)` ≠ `+3 do vòng này`).
4. Cùng khuôn với triage đỏ đa-phiên: xác định **chủ sở hữu** trước khi hành động (`git log -S '<symbol>'` + mtime) — LL-TEST-30.

Cross-ref: LL-TEST-30 (đa-phiên nhiễm DB), [[LL-AUDIT-22]] (claim ≠ đĩa), `[[multi_session_concurrency]]`; session run-3 2026-07-28.
