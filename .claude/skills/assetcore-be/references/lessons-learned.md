# assetcore-be — Lessons Learned (LL-BE-1..49)

> Bug patterns production đã gặp — **always-apply rules**, KHÔNG phải tham khảo tùy chọn.
> `SKILL.md` trỏ tới file này; ĐỌC TRƯỚC khi viết/sửa service · API · DocType · workflow.

## Lessons Learned 2026-05 (bug patterns đã gặp — phải tránh)

### LL-BE-1: `@frappe.whitelist()` KHÔNG được dùng `int | None`, `float | None` cho GET params

Frappe v15 dùng `validate_argument_types` (typing_validations.py) tự động cast theo type hint. Khi GET request truyền query string trống (`year=`), Frappe nhận `""` rồi cố cast sang `int` → raise `FrappeTypeError` → HTTP **417 Expectation Failed**.

```python
# ❌ SAI — gây 417 khi FE truyền year=""
@frappe.whitelist()
def get_metrics(asset_name: str, year: int | None = None):
    y = int(year) if year else default_year()

# ✅ ĐÚNG — nhận str từ query, tự convert trong hàm
@frappe.whitelist()
def get_metrics(asset_name: str, year: str = ""):
    y = int(year) if year else default_year()
```

**Quy tắc**: optional numeric params đến từ GET PHẢI khai báo là `str = ""`. POST body params có thể dùng `int | None` vì Frappe parse JSON đúng kiểu.

**⚠️ NUANCE QUAN TRỌNG (xác minh 2026-05-29 — chống false-positive):** 417 CHỈ xảy ra khi annotation là **real type object**. Nếu module có `from __future__ import annotations` (PEP 563), MỌI annotation thành **string** → `validate_argument_types` KHÔNG resolve được → **SKIP coercion** → KHÔNG 417, kể cả khi hint là `int | None` / `int = None`.

- `api/dashboard.py` **KHÔNG** có future-import → `persona: str=""` + `persona=None` → 417 THẬT (đã fix `41a7048`).
- `api/imm16.py` / `imm08.py` / `imm11.py` **CÓ** future-import → `get_compliance_heatmap(period_year: int|None)`, `get_pm_dashboard_stats(year: int=None)`, `get_calibration_kpis(year: int=None)` **KHÔNG 417** dù hint sai kiểu. Backlog "imm16 sẽ 417" hoá ra là **FALSE POSITIVE**.

**Cách xác định 417 risk THẬT (chạy trước khi tin báo cáo "endpoint X sẽ 417"):**
```bash
# Nếu file CÓ dòng này → annotation=string → KHÔNG 417 (an toàn, đừng "fix")
grep -L 'from __future__ import annotations' assetcore/api/*.py
#   -L liệt kê file KHÔNG có → CHỈ những file này mới 417 với GET numeric hint sai
```
Hoặc verify bằng probe thật `validate_argument_types(fn, apply_condition=lambda: True)(year="")` — RAISE = bug, OK = an toàn. **TDD RED phải fail trước; pass-trước-fix = không có bug, đừng sửa source.**

> Khuyến nghị defensive (không bắt buộc): file CÓ future-import vẫn nên dùng `str=""` cho GET numeric để khỏi 417 nếu sau này ai gỡ future-import. Nhưng KHÔNG churn file đang chạy đúng chỉ vì hint — ưu tiên không đổi code không hỏng.

### LL-BE-2: Response phải enrich tên display cho mọi Link field

```python
# ❌ SAI — FE nhận department="AC-DEPT-0101" và hiển thị code
def _get_needs_request(name):
    return frappe.get_doc("IMM Needs Request", name).as_dict()

# ✅ ĐÚNG — bổ sung *_name fields cho mọi Link field quan trọng
def _get_needs_request(name):
    doc = frappe.get_doc("IMM Needs Request", name).as_dict()
    if doc.get("requesting_department"):
        doc["requesting_department_name"] = frappe.db.get_value(
            "AC Department", doc["requesting_department"], "department_name"
        )
    if doc.get("device_model"):
        doc["device_model_name"] = frappe.db.get_value(
            "IMM Device Model", doc["device_model"], "model_name"
        )
    return doc
```

**Quy tắc**: mọi field kiểu Link bắt buộc có `_name` companion trong response. Dùng pattern `_enrich()` batch (xem `imm00.py`) cho list endpoints để tránh N+1.

**List endpoint pattern chuẩn (CONVENTIONS §37)** — bug recurring 2026-05-27 `list_user_competencies`:
```python
def list_user_competencies(filters, *, page=1, page_size=20) -> dict:
    rows, pg = UserCompetencyRepo.list(filters=..., fields=[..., "device_model"], ...)
    model_ids = list({r["device_model"] for r in rows if r.get("device_model")})
    if model_ids:
        names = dict(frappe.get_all("IMM Device Model",
            filters={"name": ("in", model_ids)},
            fields=["name", "model_name"], as_list=True))
        for r in rows:
            mid = r.get("device_model")
            if mid:
                r["device_model_name"] = names.get(mid) or mid
    return {"data": rows, "pagination": pg}
```
**Self-check ngay sau khi viết list endpoint**: grep mọi Link field trong `fields=[]` → có block enrichment tương ứng không? Nếu thiếu → bug §0 GATE-2.

### LL-BE-3: Verify DocType JSON schema TRƯỚC khi viết service code

Bug 1: `_record_contract()` set `doc.contract_signed_date = signed_date` nhưng field này không tồn tại trong DocType → `Unknown column 'contract_signed_date' in 'SET'` (1054).

Bug 2 (2026-05-26): `_enrich_capa` thêm `frappe.db.get_value("Incident Report", x, "subject")` — đoán field name `subject` theo intuition Frappe convention. Field thực là `description` → 500 `(1054, "Unknown column 'subject' in 'SELECT'")`.

Áp dụng CẢ 2 trường hợp: **set field (write)** VÀ **db.get_value / frappe.get_list(fields=[...]) (read)**.

```bash
# Trước khi viết service code động đến field nào, verify:
python3 -c "import json; d=json.load(open('<doctype>.json')); \
  print([f['fieldname'] for f in d['fields']])"
# Hoặc grep nhanh:
grep -E "\"fieldname\":" assetcore/assetcore/doctype/<doctype_snake>/<doctype_snake>.json
```

Self-check pattern khi enrich Link field display: viết unit test gọi endpoint trên data sẵn có **TRƯỚC** khi đẩy lên FE — bắt 1054 sớm.

### LL-BE-4: Workflow action labels phải khớp EXACT với workflow JSON

Bug: FE gọi `transition("Trình Ban Giám đốc")` nhưng workflow JSON định nghĩa action là `"Trình BGĐ"` → `WorkflowTransitionError`.

**Quy tắc**: action label là string khớp byte-by-byte. Sau khi tạo workflow JSON:
```bash
python3 -c "import json; d=json.load(open('workflow.json')); \
  [print(t['action']) for t in d['transitions']]"
```
Export ra constants module và dùng trong cả BE và FE.

### LL-BE-5: Gate validators phải explicit, không "implicit nullable"

Bug: G05 yêu cầu `contract_doc` trước khi award nhưng service chỉ kiểm tra `not doc.contract_doc` mà không enforce trong validator → user submit form không có contract_doc → save thành công nhưng award fail muộn.

**Quy tắc**: mọi gate (G01, G04, G05...) phải có validator trong `_validate_gate_gNN()` hàm riêng, gọi từ workflow `on_update` hook hoặc service entrypoint. Test riêng từng gate.

### LL-BE-6: Child table fieldname chuẩn — không reference `name`

Bug: FE hiển thị `5mvh1o4qsa` (Frappe auto-name) thay vì `NR-26-05-00010`. Service trả về `plan_items` với mỗi row có `name` auto-generated + Link field `needs_request`.

**Quy tắc**: khi service trả về child rows, FE phải đọc Link field (`it.needs_request`), KHÔNG đọc `it.name`. Document rõ trong API spec.

### LL-BE-7: Import endpoint phải bypass workflow validator bằng "Draft + transition"

Bug: 2026-05-27 `import_data.py` cho phép set `lifecycle_status="Active"` từ CSV → Frappe Workflow validator chặn vì doc mới chỉ được khởi tạo ở state đầu (Draft). Pre-validator thì pass (status nằm trong VALID_LIFECYCLE) → row fail ở insert.

**Quy tắc cho mọi import bulk DocType có workflow:**

1. Pre-validator chấp nhận desired_status (mọi giá trị hợp lệ)
2. Insert path:

   ```python
   desired_status = (clean.get("status_field") or "").strip()
   clean["status_field"] = INITIAL_STATE  # vd "Draft"
   doc.update(clean)
   doc.insert(ignore_permissions=True)
   if desired_status and desired_status != INITIAL_STATE:
       transition_to_status(doc.name, desired_status)
   ```

3. `transition_to_status` walk qua state machine (vd Draft → Commissioned → Active) — dùng cùng service layer `transition_<x>_status` để giữ audit trail + lifecycle event
4. Nếu desired_status không reachable từ INITIAL_STATE (vd terminal Decommissioned), skip transition silently — không trap row mid-flight

Pattern reference: `api/imm00.py:create_asset` (line 200-209), `api/import_data.py:_transition_asset_lifecycle`

### LL-BE-8: Import resolvable links — accept display name HOẶC system code

Bug: 2026-05-27 user fill template với "Máy chụp CT" (category_name) nhưng AC Asset Category PK = code → Frappe Link validator reject.

**Quy tắc:**

1. Define `_RESOLVABLE_LINKS_BY_DOCTYPE` cho mỗi import-supported DocType:

   ```python
   _RESOLVABLE_LINKS_BY_DOCTYPE = {
       "AC Asset": {
           "asset_category":  ("AC Asset Category",  "category_name"),
           "device_model":    ("IMM Device Model",    "model_name"),
           "location":        ("AC Location",         "location_name"),
           "department":      ("AC Department",       "department_name"),
           "supplier":        ("AC Supplier",         "supplier_name"),
       },
   }
   ```

2. Trong loop insert, trước `doc.update(clean)`:

   ```python
   for fld, (link_dt, display_field) in resolvable_links.items():
       val = clean.get(fld)
       if not val or frappe.db.exists(link_dt, val):
           continue
       resolved = frappe.db.get_value(link_dt, {display_field: val}, "name")
       if resolved:
           clean[fld] = resolved
   ```

3. Pre-validator cũng phải accept cả 2 (name OR display field) — không cứng chỉ chấp nhận PK

### LL-BE-9: Completion gate validator — service phải reject khi prerequisite chưa hoàn

Bug: 2026-05-16
- IMM-08 PM: `complete_pm()` cho phép đóng phiếu với checklist 0/N rated + `work_time_minutes=0` + `maintenance_tag="Chưa gắn"` → PM bị mark Completed mà chưa làm việc thực tế
- IMM-11 Calibration: `submit_calibration()` cho phép submit với 0 measurement param + không Pass/Fail result

**Quy tắc:**

1. Mọi service function thay đổi state về terminal/Completed PHẢI có gate validator:

   ```python
   def complete_pm(name: str) -> None:
       require_role(Roles.CAN_COMPLETE_WO)
       doc = repo.get(name)
       # Gate 1: tất cả checklist items đã rated
       unrated = [c for c in doc.checklist_items if c.status in ("Open", "Pending")]
       if unrated:
           raise ServiceError(ErrorCode.VALIDATION,
               f"Còn {len(unrated)} checklist item chưa đánh giá")
       # Gate 2: work time > 0
       if not doc.work_time_minutes or int(doc.work_time_minutes) <= 0:
           raise ServiceError(ErrorCode.VALIDATION, "Phải nhập thời gian thực hiện (phút)")
       # Gate 3: deliverable thực có (tag/photo/measurement…)
       if not doc.maintenance_tag:
           raise ServiceError(ErrorCode.VALIDATION, "Phải gắn tem bảo trì")
       # ...transition state
   ```

2. **KHÔNG tin FE button hide** — user có thể bypass bằng cách gọi API trực tiếp. BE là chốt chặn cuối.

3. Pattern: viết test `test_complete_pm_rejects_unrated_checklist`, `test_submit_cal_rejects_no_measurement` cho mỗi completion path.

4. Cross-reference: `services/imm08.py:complete_pm`, `services/imm11.py:submit_calibration`.

### LL-BE-10: DocType name precision — PHẢI grep JSON tồn tại trước khi viết API

> 🗺️ **Phòng tại lúc-thiết-kế:** tra tên verbatim trong [`doctype-catalog.md`](doctype-catalog.md) (bản đồ 107 DocType) TRƯỚC khi sketch data model — grep dưới đây là lưới an toàn lúc-viết-code, catalog chặn đoán-sai từ lúc-thiết-kế (`Department`→`AC Department`, `Device Model`→`IMM Device Model`, spare/stock→`AC Spare Part`/`AC Stock Movement` chứ KHÔNG `Item`/`Stock Entry`).

Bug 2026-05-26 (BUG-019): `api/imm01.py` gọi `frappe.get_all("Department", …)` thay vì `"AC Department"` → toàn bộ `/procurement-plans/:id` crash với banner `Lỗi: ('DocType', 'Department')`. Một ký tự sai = mất chức năng cả module.

**Quy tắc:**

1. **Trước khi viết** `frappe.get_all`, `get_doc`, `db.get_value`, `db.exists` với DocType mới, verify tồn tại:
   ```bash
   find assetcore -name "<doctype_snake>.json" -path "*/doctype/*"
   # Nếu là "AC Department" thì path = assetcore/assetcore/doctype/ac_department/ac_department.json
   ```
2. **AssetCore convention**: master data DocTypes có prefix `AC ` (AC Department, AC Asset, AC Asset Category, AC Supplier). ERPNext core DocTypes (Item, Employee, User) KHÔNG có prefix.
3. **Self-check sau khi viết**: grep tất cả DocType strings trong file vs JSON files thực:
   ```bash
   grep -oE '"[A-Z][A-Z a-z]+"' api/immXX.py | sort -u | while read dt; do
     name=$(echo $dt | tr -d '"' | tr '[:upper:] ' '[:lower:]_')
     test -f "assetcore/assetcore/doctype/$name/$name.json" || echo "MISSING: $dt"
   done
   ```
4. Pattern review: nếu file đã có nơi khác dùng `"AC Department"`, đừng viết mới `"Department"` — copy đúng string từ chỗ cũ. (Trong BUG-019, dòng 111/146/148 đều dùng `"AC Department"` nhưng dòng 395 sai.)

### LL-BE-11: Derived field — re-compute ở `validate()`, validate user input bounds

Bug 2026-05-25 (BUG-002): 36/39 `IMM Management Review` rows có `quarter="Q1-2099"` vì:
- `before_insert()` chỉ compute quarter `if not self.quarter` → user-supplied value WIN
- Service `create_management_review` không validate format/range của `quarter`
- Test fixture leak `"Q1-2099"` vào miyano site

**Quy tắc:**

1. **Derived field = field tính được từ field khác** (quarter từ review_date, line_total từ qty×price, days_overdue từ due_date) → PHẢI re-compute trong `validate()`, KHÔNG chỉ `before_insert`:
   ```python
   def validate(self) -> None:
       if self.review_date:
           d = getdate(self.review_date)
           self.quarter = f"Q{(d.month - 1) // 3 + 1}-{d.year}"  # always recompute
   ```
2. Service không trust user-supplied derived field — validate format + range:
   ```python
   _QUARTER_RE = re.compile(r"^Q[1-4]-\d{4}$")
   if data.get("quarter") and not _QUARTER_RE.match(data["quarter"]):
       raise ServiceError(ErrorCode.VALIDATION, "quarter sai format")
   year = int(data["quarter"].split("-")[1])
   if not (current_year - 3 <= year <= current_year + 1):
       raise ServiceError(ErrorCode.VALIDATION, f"quarter ngoài range hợp lệ")
   ```
3. **Khi sửa derived field logic, viết patch backfill** cho legacy data: `patches/v3_x/fix_<field>_<reason>.py` + register `patches.txt`. Patch phải idempotent.
4. Cross-reference: `services/imm16.py:create_management_review`, `patches/v3_2/002_fix_mr_quarter_q1_2099.py`.

### LL-BE-12: Enrichment phải handle dangling FK — show `[Đã xoá]`, không leak raw ID

Bug 2026-05-26 (BUG-020): 13 PO references `AC-SUP-2026-0025` — supplier đã bị xóa. Enrichment dùng `sup_map.get(r.supplier, r.supplier)` → fallback về raw ID → UI hiển thị `"AC-SUP-2026-0025"`.

**Quy tắc:**

1. Enrichment helper phải đánh dấu rõ "missing":
   ```python
   for row in items:
       sup = sup_map.get(row.get("supplier"))
       if sup is None and row.get("supplier"):
           row["supplier_name"] = f"[Đã xoá] {row['supplier']}"
           row["supplier_missing"] = True
       else:
           row["supplier_name"] = sup or ""
   ```
2. FE có thể style row khác đi (badge đỏ, italic, warning icon) khi `_missing: true`.
3. **Root cause prevention**: master DocType (Supplier, Department, Asset Category) khi delete phải check link existence — hoặc soft-delete (status="Archived") thay vì hard delete. Reference: `ac_asset.py::on_trash` đã có guard này — apply pattern tương tự cho master data khác.
4. Self-check sau enrichment: `assert all("_name" in r for r in rows)` — không có row nào lỡ thiếu name.

### LL-BE-13: Slug KHÔNG được vào display_name field

Bug 2026-05-26 (BUG-014): `PM Checklist Template` rows có `template_name = "Checklist PM Quý — Thiet-bi-Chan-doan-Hinh-anh"` — vì creation logic concatenate `category_slug` thay vì `category_name`.

**Quy tắc:**

1. **Display name composition** PHẢI lookup display name từ linked doc:
   ```python
   # ❌ SAI
   template_name = f"Checklist PM {period} — {category_slug}"

   # ✅ ĐÚNG
   cat_name = frappe.db.get_value("AC Asset Category", category, "category_name") or category
   template_name = f"Checklist PM {period} — {cat_name}"
   ```
2. **Quy tắc chung**: bất kỳ field nào user nhìn (label, header, badge) không được chứa kebab/snake-case identifier — chỉ chứa display strings.
3. Self-check: regex tìm slug leak trong text fields:
   ```bash
   bench --site miyano console <<'EOF'
   import frappe, re
   slug_re = re.compile(r"[a-z]+-[a-z]+-[a-z]+")  # 3+ dash-separated lowercase
   for r in frappe.db.get_all("PM Checklist Template", fields=["name","template_name"]):
       if slug_re.search(r.template_name or ""): print(r)
   EOF
   ```
4. Cross-reference: `services/imm08.py:list_templates` (display_template_name fallback), `patches/v3_2/003_fix_pm_template_name_slug.py`.

### LL-BE-14: Audit trail message PHẢI localize enum trước khi interpolate

Bug: 2026-05-26 B-IMM16-3 — CAPA audit entry text `"CAPA opened: severity=Minor"` — câu Việt nhưng enum `Minor` tiếng Anh.

Root cause: `log_audit_event()` / `log_lifecycle_event()` nhận message dạng `f"..."` đã pre-rendered ở caller. Caller f-string interpolate `capa.severity` raw → giá trị Select tiếng Anh (per §8 conventions) leak vào câu Việt. Sau khi ghi, audit trail là **bất biến** — không thể "fix khi render", phải fix tại điểm write.

**Quy tắc:**

1. Tạo `assetcore/services/shared/labels.py` — mirror với FE `constants/labels.ts`:

   ```python
   # services/shared/labels.py
   SEVERITY_VI = {"Minor": "Nhỏ", "Major": "Lớn", "Critical": "Nghiêm trọng"}
   FREQ_VI = {"Weekly": "Hàng tuần", "Monthly": "Hàng tháng", "Quarterly": "Hàng quý",
              "Yearly": "Hàng năm", "On Demand": "Theo yêu cầu"}
   WORKFLOW_STATE_VI = {"Draft": "Bản nháp", "Active": "Đang hoạt động",
                        "Locked": "Đã khóa", "Contract Signed": "Đã ký HĐ", ...}
   STATUS_VI = {"Open": "Đang mở", "In Progress": "Đang xử lý", "Closed": "Đã đóng", ...}
   ```

2. Mọi `log_audit_event` / `log_lifecycle_event` message string phải localize trước khi compose:

   ```python
   # ❌ SAI
   log_audit_event(asset, msg=f"CAPA opened: severity={capa.severity}")
   log_lifecycle_event(asset, event_type="pm_completed",
                       msg=f"PM completed by {tech_email}, status={asset.status}")

   # ✅ ĐÚNG
   from assetcore.services.shared.labels import SEVERITY_VI, STATUS_VI
   from assetcore.repositories.user_repo import get_full_name

   sev_vi = SEVERITY_VI.get(capa.severity, capa.severity)
   log_audit_event(asset, msg=f"Mở CAPA — Mức độ: {sev_vi}")

   status_vi = STATUS_VI.get(asset.status, asset.status)
   tech_name = get_full_name(tech_email) or tech_email
   log_lifecycle_event(asset, event_type="pm_completed",
                       msg=f"Hoàn thành PM — KTV: {tech_name}, Trạng thái: {status_vi}")
   ```

3. Convention: msg phải là 1 câu Việt hoàn chỉnh, KHÔNG mix English token. Email/code không phải enum cũng phải resolve display name (LL-BE-2, LL-BE-12).

4. Self-check (grep audit caller sites cho English token leak):

   ```bash
   grep -rnE "log_(audit|lifecycle)_event.*=(Locked|Evaluated|Scheduled|Minor|Major|Critical|Weekly|Monthly|Open|Closed|Draft|Active)" assetcore/services/ assetcore/assetcore/doctype/
   # mỗi match là 1 bug tiềm năng — phải localize qua *_VI dict
   ```

5. Cross-reference: §27, FE LL-FE-30.

### LL-BE-15: Test fixture "shared reuse" pattern KHÔNG bypass Frappe rollback — sẽ leak

Bug session 2026-05-26 (B-IMM06-1): `test_imm06.py:_ensure_test_program` dùng pattern "if exists, reuse" để optimize test speed:

```python
existing = frappe.db.get_value("IMM Training Program",
                                {"program_name": "_Test Program IMM06 Shared"},
                                "name")
if existing:
    return existing  # ← bypass savepoint rollback
```

Sau khi 1 test commit qua scope của savepoint (vd: chạy patch, gọi `frappe.db.commit()`), record không bị rollback. Lần chạy tiếp theo reuse → orphan ngày càng nhiều, eventually leak vào UI list `/imm06/programs`.

**Quy tắc:**

1. **Cấm "ensure exists / reuse" cho test fixtures**. Mỗi test class: fresh `setUpClass` + explicit `tearDownClass`:

   ```python
   class TestImm06(unittest.TestCase):
       _created: list[tuple[str, str]] = []  # (doctype, name)

       @classmethod
       def setUpClass(cls):
           prog = frappe.get_doc({
               "doctype": "IMM Training Program",
               "program_code": f"_TEST-PROG-{int(time.time())}",
               # ...
           }).insert(ignore_permissions=True)
           cls._created.append(("IMM Training Program", prog.name))

       @classmethod
       def tearDownClass(cls):
           for dt, name in reversed(cls._created):
               try:
                   frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
               except Exception:
                   pass
           super().tearDownClass()
   ```

2. **Defense-in-depth ở BE list service**: filter `_Test*` khỏi list user-facing:

   ```python
   def list_training_programs(filters, ...):
       nf = normalize_filters(filters)
       nf.setdefault("program_code", ["not like", "\\_Test%"])
       ...
   ```

3. **Pre-release SQL audit**:

   ```bash
   bench --site miyano mariadb -e "
     SELECT name FROM \`tabIMM Training Program\` WHERE name LIKE '\\_Test%' OR name LIKE 'TEST-%';
     SELECT name FROM \`tabAC Asset\` WHERE name LIKE '\\_Test%' OR asset_name LIKE '\\_Test%';
   "  # phải rỗng
   ```

4. Cross-reference: `assetcore-fe` LL-FE-19; `assetcore-test` R-1, R-8.

### LL-BE-16: Werkzeug auto-reload không tin cậy — verify code mới active TRƯỚC khi test FE

Bug session 2026-05-26: edit `services/imm16.py:get_capa` thêm enrich. Werkzeug dev-server lúc reload lúc không (depend vào how editor saves file — atomic vs in-place). FE fetch nhận old code → debug nhầm là logic sai.

**Quy tắc post-fix Python:**

```bash
# 1. Verify code mới active TRƯỚC khi mở browser:
bench --site miyano execute assetcore.services.<module>.<func> --args '[<args>]'
#   → output JSON: nếu nhận expected field → code mới đã load
#   → exception khác expected → fix code error trước
#
# 2. Nếu bench execute OK nhưng HTTP vẫn lỗi → force restart:
pkill -f "honcho start"
bench start &
sleep 5
#
# 3. Với change ở fixtures.py / hooks.py / permissions.py / DocType JSON:
bench --site miyano migrate
#   không chỉ rely auto-reload — fixtures need migrate
```

**Anti-pattern**: edit BE → đi thẳng test FE → 500 → đoán logic. Pattern đúng: bench execute first, FE sau.

### LL-BE-17: Linter / formatter có thể tự sửa file SKILL.md/code — re-read trước khi Edit nếu thấy lock-warning

Khi tool `Edit` báo `File has been modified since read` → KHÔNG retry blindly. Re-read file (đọc lại tail/affected section) để xem linter đã đổi gì. Một số trường hợp linter đã apply fix tương đương → skip edit thừa.

### LL-BE-18: Service detail endpoint — `Repo.get(fk).field` PHẢI null-guard

Bug 2026-05-26 thực: `services/imm12.py:489` build dict `data["rca"] = {"name": rca.name, ...}` ngay sau `rca = RCARepo.get(doc.rca_record)` mà không check `if rca:`. Test residue tạo orphan refs (Incident.rca_record trỏ tới RCA đã xóa) → `AttributeError: 'NoneType' object has no attribute 'name'` → BE 500 (wrap HTTP 200) → FE "Lỗi server" trên 3 incident pages.

```python
# ❌ SAI — crash khi orphan FK
if doc.rca_record:
    rca = RCARepo.get(doc.rca_record)
    data["rca"] = {"name": rca.name, "status": rca.status, ...}

# ✅ ĐÚNG — guard cả "có set FK" và "FK resolve được"
if doc.rca_record:
    rca = RCARepo.get(doc.rca_record)
    if rca:  # FK có thể orphan sau xóa thủ công / test cleanup / data migration
        data["rca"] = {"name": rca.name, "status": rca.status, ...}
```

**Quy tắc**: BẤT KỲ `Repo.get(fk)` hay `frappe.get_doc(dt, fk)` nào trên FK từ DocType khác PHẢI `if obj:` guard. Đặc biệt nguy hiểm trong service detail endpoints (`get_xxx_detail`), enrich helpers (xem cũng LL-BE-12), cross-module computed fields.

**Grep self-check**:
```bash
grep -nE "Repo\.get\([^)]+\)\.\w+" assetcore/services/imm*.py
grep -nE "frappe\.get_doc\([^)]+\)\.\w+" assetcore/services/imm*.py | grep -v "self\.\|cls\."
# Mỗi match → verify có `if obj:` guard hoặc `getattr(obj, field, default)` ngay phía trên
```

Companion fix: backfill orphans với `frappe.db.set_value(parent_dt, p.name, fk_field, None)`. Frappe Link KHÔNG có DB-level FK constraint nên orphan refs là trạng thái có thể xảy ra trong thực tế.

### LL-BE-19: `on_trash` audit guard — phải có `frappe.flags.in_test` bypass

Bug pattern 2026-05-26: `AC Asset.on_trash` (`assetcore/doctype/ac_asset/ac_asset.py:223`) chặn `delete_doc` khi còn Audit Trail / Lifecycle Event / Downtime Log — đúng nghiệp vụ CLAUDE.md §10/§12. Nhưng tearDown của unit tests dùng `force=True` KHÔNG bypass on_trash → `test_imm00/08/09` báo cumulative `errors=N` ở tearDownClass.

```python
def on_trash(self) -> None:
    # ✅ Sản phẩm: chặn delete khi có audit trail
    if frappe.flags.get("in_test") or frappe.flags.get("in_install"):
        return  # bypass cho test environment + fixture import
    # ... existing blocker check
```

**Quy tắc** khi viết `on_trash` audit guard:
- Bắt buộc bypass `frappe.flags.in_test` HOẶC document procedure cancel-children trong test fixture (xem `assetcore-test` LL-TEST-17)
- Bypass `frappe.flags.in_install` cho fixture import / patch
- KHÔNG bypass cho user thực — `frappe.session.user != "Administrator"` vẫn phải enforce

### LL-BE-20: HTTP 200 wrap `success:false` — `log_error` PHẢI có full traceback

Bug pattern 2026-05-26: `imm12.get_incident` catch `Exception` → return `_err(_(_MSG_SERVER_ERROR), 500)` (HTTP 200 envelope). Nếu KHÔNG log full trace, FE chỉ thấy "Lỗi server" → không debug được.

```python
except Exception:
    frappe.log_error(frappe.get_traceback(), "IMM-12 get_incident")  # ✅ full trace
    return _err(_(_MSG_SERVER_ERROR), 500)
```

**Quy tắc**:
- Mọi `except Exception:` bao endpoint PHẢI `frappe.log_error(frappe.get_traceback(), "<MODULE> <function>")`
- Title pattern `"<MODULE-XX> <function_name>"` — dễ filter qua `Error Log`
- KHÔNG dùng `frappe.log_error(str(e), ...)` — mất stack trace, không debug được

### LL-BE-21: SQL safety — pymysql `%` escape + LIKE wildcard `_`/`%` (2026-05-27)

**Root cause:** data-cleanup session, xoá nhầm 4 asset thật vì `LIKE '_%'`.

**3 bug pattern và fix:**

#### Bug 1: f-string giá trị vào SQL → "not enough arguments for format string"

`pymysql` parse `%` trong query string TRƯỚC bind params. Mọi `%` literal trong query đều phải escape thành `%%` HOẶC dùng param.

```python
# SAI
val = "abc"
frappe.db.sql(f"SELECT * FROM `tabFoo` WHERE name LIKE '%{val}%'")
# SAI — raw string vẫn vỡ vì có `%`
frappe.db.sql("SELECT name FROM `tabFoo` WHERE name LIKE '\\_%'")

# ĐÚNG
frappe.db.sql("SELECT * FROM `tabFoo` WHERE name LIKE %s", (f"%{val}%",))
frappe.db.sql("SELECT name FROM `tabFoo` WHERE name LIKE %s", (r"\_%",))
```

#### Bug 2: LIKE `_` là wildcard "đúng 1 ký tự" — match nhầm toàn bảng

```python
# SAI — match MỌI string ≥1 char (đã gặp: xoá 4 AC Asset thật)
matches = frappe.db.sql_list("SELECT name FROM `tabFoo` WHERE LOWER(name) LIKE '_%'")

# ĐÚNG — escape `_` bằng `\_` HOẶC dùng ESCAPE clause
matches = frappe.db.sql_list(
    "SELECT name FROM `tabFoo` WHERE LOWER(name) LIKE %s",
    (r"\_%",),
)
matches = frappe.db.sql_list(
    r"SELECT name FROM `tabFoo` WHERE LOWER(name) LIKE %s ESCAPE '\\'",
    (r"\_%",),
)
```

#### Bug 3: Subquery cùng bảng đang DELETE → MariaDB "can't reopen table"

```sql
-- SAI
DELETE FROM `tabAsset Lifecycle Event`
WHERE asset NOT IN (SELECT name FROM `tabAC Asset`);  -- OK
DELETE FROM `tabIMM Audit Trail`
WHERE name IN (SELECT name FROM `tabIMM Audit Trail` WHERE ...);  -- FAIL

-- ĐÚNG — wrap với alias để MariaDB hiểu là bảng tạm
DELETE FROM `tabIMM Audit Trail`
WHERE name IN (SELECT name FROM (SELECT name FROM `tabIMM Audit Trail` WHERE ...) x);
```

**Checklist trước khi commit raw SQL:**
- [ ] Mọi giá trị từ user/string interpolation → dùng param `%s` với tuple
- [ ] Mọi LIKE pattern chứa `_` hoặc `%` literal → escape `\_` `\%` + ESCAPE clause
- [ ] Mọi subquery trên cùng table đang mutate → wrap alias `(SELECT ... ) x`
- [ ] Reference: `CONVENTIONS.md §32`

### LL-BE-22: Verify column tồn tại TRƯỚC khi viết raw SQL (2026-05-27)

**Bug đã gặp 2026-05-27:** viết `WHERE serial_no = ...`, `WHERE reported_issue LIKE ...`, `WHERE part = ...`, `SELECT code FROM ...` — đều `Unknown column 1054` runtime vì cột thực tế tên khác (`gmdn_code`, `failure_description`, `spare_part`).

**Quy tắc:**

1. Trước khi viết `WHERE`/`SELECT` trên cột ngoài `name`/`creation`/`modified`/`owner`/`docstatus`, verify schema:
   ```bash
   bench --site miyano mariadb -e "DESCRIBE \`tabXxx\`;" | grep -iE '<keyword>'
   ```
2. Trong Python:
   ```python
   if not frappe.db.has_column(doctype, fieldname):
       # column không tồn tại — log + return early
   ```
3. Khi viết script generic chạy trên nhiều DocType, dùng meta:
   ```python
   meta = frappe.get_meta(doctype)
   text_fields = [f.fieldname for f in meta.fields
                  if f.fieldtype in ("Data", "Small Text", "Long Text", "Text Editor", "Text")
                  and frappe.db.has_column(doctype, f.fieldname)]
   ```
4. **KHÔNG đoán** tên cột từ docs hoặc memory — luôn DESCRIBE/has_column.

**Common mismatches gặp phải:**

| Đoán | Thực tế |
|---|---|
| `serial_no` (AC Asset) | `gmdn_code`, `udi_di`, `udi_pi` |
| `code` (AC Asset Category) | `category_name` only |
| `asset` (Asset Document) | `asset_ref` |
| `asset` (Asset Repair) | `asset_ref` |
| `part` (AC Spare Part Stock) | `spare_part` |
| `source_doctype` (IMM Audit Trail) | `ref_doctype`, `ref_name` |
| `reported_issue` (Asset Repair) | `failure_description` |

Reference: `CONVENTIONS.md §32 (c)`, `assetcore-audit` data-hygiene pillar.

### LL-BE-23: Lifecycle Hook Chain — cross-module trigger PHẢI wire + idempotent + audit (2026-05-27)

**Pattern bug đã gặp 5 lần (G2 Test Plan NextRound_1):** action complete trên doc A không trigger việc tạo/cập nhật doc B nghiệp vụ yêu cầu.

Bug records:
- **RC-03**: RCA Completed → CAPA không tạo
- **RC-04**: RCA Completed → Incident không auto-advance state
- **RC-06**: Phiếu nghiệm thu Hoàn tất → Asset không tự sinh
- **RC-07**: Asset tick "Yêu cầu HC" → CalibrationSchedule không sinh
- **RC-11**: Asset có chu kỳ PM/Cal → nextPM/nextCal không compute

**Quy tắc khi viết bất kỳ service `_finalize_*` / `complete_*` / `submit_*` (BẮT BUỘC):**

1. **Định danh chain trong docs trước khi code**:
   ```
   docs/imm-XX/04_Backend_Design.md §Cross-Module Triggers
   Trigger:      services/immA::complete_X
   Side effect:  services/immB::create_from_A(a.name) — idempotent
   ```

2. **Wire chain trong service A** (KHÔNG controller), lazy import:
   ```python
   def complete_acceptance(name):
       doc = repo.get(name)
       _validate_completion_gates(doc)
       repo.transition(doc.name, _STATUS_COMPLETED)

       # CHAIN — Trigger downstream
       from assetcore.services.imm05 import create_asset_from_acceptance
       asset_name = create_asset_from_acceptance(doc.name)

       # Audit chain (separate row)
       log_audit_event(
           doctype="Asset Commissioning",
           doc_name=doc.name,
           action="completed_and_triggered_asset",
           triggered_record=asset_name,
       )
   ```

3. **Service B PHẢI idempotent**:
   ```python
   def create_asset_from_acceptance(acceptance_name):
       existing = frappe.db.exists("AC Asset", {"source_acceptance": acceptance_name})
       if existing:
           return existing
       # ...create new
   ```

4. **Anti-pattern CẤM**:
   - `try/except: pass` quanh chain call — lỗi chain phải raise
   - Chain call trong controller `on_submit` mà không qua service
   - Quên audit `triggered_record`

5. **Test bắt buộc** trong `test_imm<A>.py`:
   ```python
   def test_complete_creates_b(self):
       a = self._create_a()
       self._transition_to_completed(a)
       self.assertTrue(
           frappe.db.exists("DocType B", {"source_a": a.name}),
           "Hook chain A→B failed silently"
       )

   def test_complete_b_idempotent(self):
       """Calling chain twice không tạo 2 records"""
       a = self._create_a()
       self._transition_to_completed(a)
       count = frappe.db.count("DocType B", {"source_a": a.name})
       self.assertEqual(count, 1)
   ```

6. **Self-check trước commit**:
   ```bash
   grep -B2 -A30 "def _finalize_\|def complete_\|def submit_" assetcore/services/imm*.py \
     | grep -B5 "_STATUS_COMPLETED\|_STATUS_CLOSED\|status.*Completed"
   # Đối chiếu mỗi terminal transition với 04_Backend_Design.md §Cross-Module Triggers
   ```

Reference: `CONVENTIONS.md §40`, `assetcore-audit` Pillar 9, `docs/res/reports/AssetCore_Test_Plan_NextRound_1_Analysis.md` §3.

### LL-BE-24: Whitelist Permission Backup Gate — BE PHẢI gate, không tin FE hide (2026-05-27)

**Pattern rủi ro security cao (AUTH-02 chưa fix):** FE ẩn nút bằng `useCapabilities().can()` nhưng BE `@frappe.whitelist()` thiếu `rbac.require()` → attacker gọi API trực tiếp qua DevTools/curl vẫn execute.

**Quy tắc tuyệt đối (vi phạm = P1 security):**

1. Mọi `@frappe.whitelist()` mutating endpoint (POST/PUT/DELETE semantics) PHẢI có 1 trong 2 ở dòng đầu function body:
   ```python
   from assetcore.services.shared import rbac

   @frappe.whitelist()
   def approve_capa(name):
       rbac.require("capa.write")  # ← preferred
       # ...
   ```
   HOẶC:
   ```python
   from assetcore.services.shared import has_any_role, Roles

   @frappe.whitelist()
   def approve_capa(name):
       if not has_any_role((Roles.QA_MANAGER, Roles.SYS_ADMIN)):
           raise ServiceError(ErrorCode.FORBIDDEN, "Chỉ QA mới có quyền duyệt")
       # ...
   ```

2. Read-only endpoint có thể skip explicit gate NẾU đã filter qua `permission_query_conditions`. Vẫn khuyến nghị `rbac.require("xxx.read")` để document.

3. **Capability string BE và FE PHẢI khớp EXACT** — đặt tên thân thiện ở FE là bug.

4. **Test bắt buộc** mỗi mutating endpoint:
   ```python
   def test_approve_rejects_low_role(self):
       frappe.set_user("low.role@test")
       with self.assertRaises(ServiceError) as ctx:
           api.approve_capa(self.doc_name)
       self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)
   ```

5. **Audit self-check command**:
   ```bash
   for f in assetcore/api/imm*.py; do
       python3 -c "
   import ast
   tree = ast.parse(open('$f').read())
   for n in ast.walk(tree):
       if isinstance(n, ast.FunctionDef) and any('whitelist' in ast.unparse(d) for d in n.decorator_list):
           body = ast.unparse(n)
           if 'rbac.require' not in body and 'has_any_role' not in body:
               print('$f::' + n.name + ' missing gate')
   "
   done
   ```

Reference: `CONVENTIONS.md §41`, `assetcore-audit` Pillar 8 Security.

### LL-BE-25: Auto-Default Field on Create — `before_save` controller hook (2026-05-27)

**Pattern bug (RC-02):** Field nghiệp vụ bắt buộc nhưng không có default → user quên nhập → break downstream. Triệu chứng RC-01: Asset thiếu `depreciation_method` → "Sinh lịch khấu hao" treo silently.

**Quy tắc:**

1. Field default-by-condition PHẢI implement trong controller `before_save`:
   ```python
   # assetcore/overrides/asset.py hoặc doctype/<x>/<x>.py
   def before_save(self):
       if self.purchase_amount and self.purchase_amount > 0 and not self.depreciation_method:
           self.depreciation_method = "Straight Line"
       if self.has_calibration_requirement and not self.calibration_interval_months:
           self.calibration_interval_months = 12
   ```

2. **KHÔNG dùng `default` trong DocType JSON** cho conditional defaults — JSON `default` là static, không nhìn được field khác.

3. **Required-when-condition**: dùng `validate()` chặn save nếu default không compute được:
   ```python
   def validate(self):
       if self.has_calibration_requirement and not self.calibration_interval_months:
           frappe.throw("Phải nhập chu kỳ hiệu chuẩn khi tick yêu cầu HC")
   ```

4. **Test bắt buộc**:
   ```python
   def test_asset_auto_defaults_depreciation_method(self):
       asset = frappe.new_doc("AC Asset")
       asset.update({"asset_name": "Test", "purchase_amount": 100_000_000})
       asset.insert()
       self.assertEqual(asset.depreciation_method, "Straight Line")
   ```

5. **Trace check**: với mọi field downstream service đọc (vd `services/imm05.py:generate_depreciation_schedule` đọc `asset.depreciation_method`), trace ngược nơi field được set. Nếu không có default + không required → bug tái xuất.

Reference: `CONVENTIONS.md §44`, `docs/res/reports/AssetCore_Test_Plan_NextRound_1_Analysis.md` §3 RC-02.

### LL-BE-26: State machine — MỌI state khai báo phải REACHABLE (2026-05-29)

**Bug đã gặp 2026-05-29 (IMM-12):** `acknowledge_incident()` transition thẳng `Open → In Progress`, nhưng workflow JSON có khai báo state `Acknowledged` ở giữa. Hệ quả: state `Acknowledged` **không bao giờ tới được** → FE stepper có node chết, nút "Bắt đầu xử lý" không có chỗ render. Khác LL-FE-1/5/10 (FE map thiếu state) — đây là **bug ở chính đồ thị transition BE**: một transition nhảy qua state đã khai báo.

**Quy tắc:**

1. Khi định nghĩa `_VALID_TRANSITIONS` / workflow JSON, mỗi state (trừ initial) PHẢI có ít nhất 1 transition TỚI nó, và mỗi state (trừ terminal) PHẢI có ít nhất 1 transition RỜI nó. Không "đảo state" bằng cách nhảy qua.

2. Nếu nghiệp vụ thực sự cần 2 bước (vd Open → Acknowledged → In Progress), tách thành 2 service function riêng (`acknowledge` rồi `start_work`), KHÔNG gộp 1 hàm nhảy 2 cấp.

3. **Self-check reachability** (chạy sau khi sửa transition graph):
   ```python
   # bench execute hoặc test: BFS từ initial state qua _VALID_TRANSITIONS
   declared = set(STATES)                      # mọi state khai báo
   reachable = set()
   frontier = {INITIAL_STATE}
   while frontier:
       reachable |= frontier
       frontier = {t for s in frontier for t in _VALID_TRANSITIONS.get(s, [])} - reachable
   orphan = declared - reachable - {INITIAL_STATE}
   assert not orphan, f"State không reachable: {orphan}"
   ```

4. **Test bắt buộc**: traverse full lifecycle qua service layer — assert vào được mọi non-terminal state. Cross-ref: `assetcore-fe` LL-FE-1/5/10 (FE map phải khớp graph này).

Reference: `services/imm12.py:_VALID_TRANSITIONS` (acknowledge + start_work), `assetcore-fe` LL-FE-1.

### LL-BE-27: Maintenance/cleanup script — execution & immutable-audit (2026-05-29)

**2 bug đã gặp 2026-05-29 khi dọn dữ liệu eval:**

#### Bug 1: `bench --site console < file.py` KHÔNG chạy reliably

Pipe file Python vào `bench console` chỉ echo source theo dòng ipython, KHÔNG đảm bảo gọi hàm/`run()` ở cuối, output không capture sạch để parse.

```bash
# ❌ KHÔNG tin được cho script mutation / cần đọc kết quả
bench --site miyano console < cleanup.py

# ✅ ĐÚNG — đặt function trong module thật rồi execute
#   tạo tạm assetcore/scripts/_tmp_cleanup.py với def run(): ...
bench --site miyano execute assetcore.scripts._tmp_cleanup.run
#   rm file tạm sau khi xong — KHÔNG commit script _tmp_*
```
Cross-ref LL-BE-16 (verify code active bằng `bench execute`).

#### Bug 2: Audit/lifecycle docs KHÔNG xoá được kể cả `force=True`

`Asset Lifecycle Event` (và các audit doc) có `on_trash` guard raise "cannot be deleted" — đúng thiết kế chống tamper audit trail (CLAUDE.md §10/§12, LL-BE-14/19). `frappe.delete_doc(..., force=True)` VẪN chạy `on_trash` → ValidationError, và nếu nằm giữa loop sẽ rollback cả batch.

**Quy tắc cho cleanup script:**

1. KHÔNG cố xoá audit/lifecycle event để "khôi phục trạng thái". Audit là bất biến — giữ nguyên làm lịch sử.
2. "Restore" trạng thái asset bằng `frappe.db.set_value(...)` (vd `lifecycle_status` về giá trị trước), GIỮ event audit.
3. Xoá record giao dịch (Incident/RCA/WO eval) trước; nếu loop có cả audit doc → tách riêng, đừng để 1 ValidationError rollback toàn bộ.
4. Mọi cleanup chạm dữ liệu thật = HARD-STOP xin phép user trước (xem `assetcore-test` R-8, `assetcore-deploy`).

Reference: LL-BE-14, LL-BE-19, `assetcore-test` R-8/R-9.

### LL-BE-28: Data-scoping PHẢI fail-closed khi context phạm vi thiếu (2026-05-29)

**Bug đã gặp 2026-05-29 (IMM-00 clinical dashboard):** `_build_clinical` lấy `dept = _current_dept()`; khi user clinical CHƯA gắn `Employee.department`/`User.ac_department` → `dept = None`. Code cũ: `if dept: filters["department"] = dept` → khi None thì **bỏ luôn filter** → query trả **toàn bộ sự cố/đề xuất/asset CẢ VIỆN** gắn nhãn "khoa mình" → rò rỉ data vượt ranh giới role (vi phạm RBAC data-isolation, CLAUDE.md §5/§19).

Đây là **fail-OPEN**: thiếu điều kiện thu hẹp → trả nhiều hơn. Mọi scope theo dept/vendor/owner đều dễ dính.

**Quy tắc (BẮT BUỘC mọi service đọc dữ liệu có scope theo dept/vendor/khoa/owner):**

1. **Thiếu scope context → trả RỖNG (fail-closed), KHÔNG bỏ filter:**
   ```python
   # ❌ SAI — fail-open: dept None → bỏ filter → lộ toàn bộ
   dept = _current_dept()
   if dept:
       filters["department"] = dept
   rows = repo.list(filters)

   # ✅ ĐÚNG — fail-closed: không có scope → rỗng + cờ báo cấu hình
   dept = _current_dept()
   if not dept:
       return {"rows": [], "scope_configured": False}  # FE hiện banner "chưa gắn khoa"
   filters["department"] = dept
   rows = repo.list(filters)
   ```
2. **KHÔNG bao giờ** để một filter scope-bắt-buộc trở thành optional vì giá trị None. Scope thiếu = bug cấu hình, KHÔNG phải "xem tất cả".
3. Ngoại lệ DUY NHẤT: role admin/superuser được phép "all" — phải kiểm tra role TƯỜNG MINH (`is_superuser`/`has_role`), không suy ra từ "dept rỗng".
4. **Test bắt buộc**: case `scope context = None` → assert rỗng (không leak). RED phải chứng minh leak trước khi fix (session 2026-05-29: D-BE-9 RED trả `IR-2026-0130` của viện → GREEN rỗng).
5. FE companion: cờ `scope_configured: False` → empty-state actionable "Liên hệ quản trị gắn khoa" (LL-FE-13), KHÔNG render data toàn cục.

Reference: `services/imm00`/`api/dashboard.py:_build_clinical`, `assetcore-audit` Pillar 8 (vendor/dept isolation), CLAUDE.md §19.

### LL-BE-29: Verify-before-fix — reproduce TRƯỚC khi sửa; pass-trước-fix = KHÔNG có bug (2026-05-29)

**Pattern đã gặp 3 lần trong 1 session (2026-05-29):** nhận một "bug" từ backlog/báo cáo vòng trước rồi định sửa ngay → hoá ra **FALSE POSITIVE**, suýt churn code đang chạy đúng:
- "imm16/08/11 sẽ HTTP 417" → SAI (các file có `from __future__ import annotations` → validator skip → không 417). Xem LL-BE-1 nuance.
- "OpsmgrDashboard leak 'Critical'" → SAI (`translateStatus` đã map `Critical→Khẩn cấp`).
- "Clinical empty-state thiếu" → SAI (đã handle) — NHƯNG khi verify lại lộ bug THẬT khác (LL-BE-28).

**Quy tắc (BẮT BUỘC trước khi sửa BẤT KỲ bug nào được "báo" mà bạn chưa tự thấy):**

1. **REPRODUCE trước, sửa sau.** Viết test/probe làm bug FAIL (TDD RED) HOẶC `bench execute`/đọc code chứng minh hành vi sai THẬT. Chưa reproduce được = chưa biết có bug.
2. **Pass-trước-fix = KHÔNG có bug → KHÔNG sửa.** Nếu test viết ra PASS ngay khi chưa đụng source → đó là báo động giả, đóng backlog item là "false positive", KHÔNG churn code đang chạy đúng chỉ để "cho chắc".
3. **KHÔNG tin báo cáo/backlog/intuition** (kể cả của chính mình vòng trước) làm bằng chứng. Mỗi claim "X bị lỗi" phải verify lại từ đầu (môi trường/Frappe có nuance — vd PEP 563, union types).
4. Khi verify một FP lại lộ bug khác (như clinical) → fix bug THẬT đó (có RED), ghi rõ FP ban đầu đã bị bác.
5. Ghi kết quả: "FALSE POSITIVE — lý do" vào báo cáo, để vòng sau không đuổi lại.

Cross-ref: `assetcore-audit` "anti-false-positive checklist", LL-FE-27 (bench execute trước khi sửa FE), `assetcore-test` Phần 1.5 (RED phải fail trước).

---

## Lessons Learned 2026-05-29 — Event-driven / Notification feature (Notification Framework V1→V8)

> Nguồn: 8 vòng factory xây Notification Framework (in-app + email). Mỗi rule dưới đây là **bug THẬT đã commit rồi self-correct trong session** (không phải giả định). Áp dụng cho MỌI feature cross-cutting event-driven: notification, escalation, SLA scan, audit hook, digest.

### LL-BE-30: Event-driven feature — resolve recipient & trigger-state ĐỘNG từ Workflow metadata, KHÔNG hard-code (2026-05-29)

**Bug (Notification V1→V2):** `notify_approval_pending` hard-code `_PENDING_APPROVAL_STATES = {...}` + đọc field `supervisor`. Cả 2 workflow Wave-1 **không có state nào trùng** tập hard-code; Asset Repair **không có field `supervisor`** → notification **chưa từng fire** — silent no-op, KHÔNG raise, và test ban đầu cũng PASS vì test data dựng theo đúng giả định sai. Chỉ lộ khi verify code ↔ workflow runtime thật.

**Quy tắc:**

1. Feature đụng nhiều DocType/workflow (notification, escalation, SLA, audit) **KHÔNG hard-code danh sách tên state** và **KHÔNG giả định một role-field tồn tại** trên doc. Resolve động từ `frappe.get_doc("Workflow", wf)` transitions + `transition.allowed` roles.
2. "Cần duyệt / đặc biệt" phải **derive từ transition metadata** (vd: có transition rời state với role phê duyệt → `next_state` finalize `doc_status==1`), KHÔNG từ tên state literal.
3. Recipient = `union(users có role trong transition.allowed)` + optional field **chỉ khi** `frappe.db.has_column(dt, "supervisor")`; rồi loại actor + Administrator + dedupe.
4. **Test phải verify CẢ HAI trên workflow THẬT**: (a) trigger-state thực sự fire, (b) recipient resolve **non-empty**. Đừng chỉ test với data dựng theo giả định — sẽ pass dù feature chết.
5. **Silent no-op nguy hiểm hơn crash**: ở path lẽ ra phải có người nhận mà recipient rỗng → `frappe.log_error` / assert, đừng nuốt lặng.

Cross-ref: LL-BE-26 (state reachability), LL-BE-4 (action label khớp JSON).

### LL-BE-31: Workflow State `style`/`type` (Danger/Success…) KHÔNG persist runtime DB — đừng branch logic trên nó (2026-05-29)

**Bug (Notification V7 escalation):** Core Doc định nghĩa escalation = state có `Workflow State.type == "Danger"`. Field `style`/`type` **chỉ có trong fixture JSON**; runtime DB child `Workflow Document State` KHÔNG có field này, master `Workflow State.style` lưu `""`. Điều kiện luôn False → escalation câm. Self-correct: đổi sang đọc transitions metadata.

**Quy tắc:**

1. **KHÔNG branch business logic trên `Workflow State.style`/`type`/màu** — chúng là cosmetic fixture, không reliable runtime.
2. Tín hiệu "state đặc biệt" phải derive từ STRUCTURE có thật runtime: role nào VÀO state, role nào RỜI, `next_state` có finalize (`doc_status==1`) không.
3. Verify field workflow-meta bất kỳ TRƯỚC khi dùng — `bench execute` đọc giá trị THẬT từ DB, đừng tin JSON fixture:
   ```python
   frappe.get_all("Workflow Document State",
       filters={"parent": wf}, fields=["state", "doc_status", "allowed", "allow_edit"])
   # chỉ những field này tin được ở runtime
   ```

Cross-ref: LL-BE-30, LL-BE-3 (verify schema trước khi code).

### LL-BE-32: Scheduler function KHÔNG chạy nếu thiếu `hooks.scheduler_events` — wire + verify đăng ký (2026-05-29)

**Bug (Notification V8):** phát hiện `imm09.check_repair_sla_breach` viết sẵn nhưng **chưa từng đăng ký** trong `scheduler_events` → chưa bao giờ chạy (dead code; SLA breach không ai được báo). E6 phải wire `run_sla_breach_scan` vào `scheduler_events["hourly"]`.

**Quy tắc:**

1. Mọi function chạy nền (SLA scan, expiry/calibration-due check, digest) PHẢI có entry trong `hooks.py::scheduler_events` (`"hourly"`/`"daily"`/`"cron"`) trong **CÙNG commit** với code — y như doc_events (anti-pattern #7 trong SKILL.md).
2. Verify đăng ký runtime, đừng tin "đã viết hàm là xong":
   ```bash
   bench --site miyano execute frappe.get_hooks --args '["scheduler_events"]' | grep <func>
   ```
3. Verify scheduler **enabled** trên site (`bench --site x doctor` / Scheduler không pause) — hàm đúng nhưng scheduler tắt = vẫn không chạy.
4. **Test gọi trực tiếp function scan** với data dựng sẵn (đừng chờ cron), verify cả logic lẫn anti-spam state-change guard (chỉ bắn 1 lần khi cờ `0→1` / khi VÀO state, không spam mỗi lần quét).
5. Khi thay scheduler cũ bằng mới: xác nhận hàm cũ thực sự dead (chưa đăng ký) rồi mới supersede; để lại dead code = nợ kỹ thuật, ghi backlog dọn.

Cross-ref: SKILL.md anti-pattern #7 (doc_events wiring), LL-BE-23 (lifecycle hook chain).

### LL-BE-33: Verify field TYPE (Date vs Datetime) + enum VALUE thật + email reference trước khi code (2026-05-29)

**3 bug (Notification V5 + V8):**
- **V8:** giả định PM Work Order có timestamp đủ tính SLA deadline; field thực `due_date`/`completion_date` là **`Date`** (không có giờ) → không tính live deadline theo giờ → phải defer. Asset Repair có `open_datetime` (`Datetime`) mới dùng được.
- **V5:** giả định Email Queue email lỗi có `status == "Error"`; giá trị THẬT là `status == "Not Sent"` + `error` not null. Query lọc `"Error"` luôn rỗng → KPI sai 0.
- **V5:** `frappe.sendmail` mặc định KHÔNG set `reference_doctype`/`reference_name` → Email Queue không truy nguyên về record → KPI delivery không link được (cả 33 email cũ `reference_doctype=NULL`).

**Quy tắc:**

1. Trước khi viết **arithmetic thời gian**, verify fieldtype `Date` (không giờ) vs `Datetime`. `Date + duration-giờ` = sai:
   ```python
   frappe.get_meta(dt).get_field(f).fieldtype  # "Date" | "Datetime"
   ```
2. Trước khi **filter theo Select/status**, verify giá trị enum THẬT — đừng đoán:
   ```python
   frappe.get_all(dt, pluck="status", distinct=True)   # hoặc đọc options trong DocType JSON
   ```
   Đã gặp: Email Queue OK = `status="Sent"`; lỗi = `status="Not Sent"` + `error` not null (KHÔNG có "Error").
3. `frappe.sendmail` cho notification nghiệp vụ PHẢI truyền `reference_doctype=` / `reference_name=` để Email Queue truy nguyên + đo KPI delivery. Khi truyền `message` là HTML, Frappe core tự sinh phần `text/plain` (`set_html_as_text`) — KHÔNG cần `text_content` thủ công.
4. **Doc ↔ workflow JSON drift**: bảng `allow_edit`/role trong `docs/imm-XX/04_Backend_Design.md` phải khớp source-of-truth `*_workflow.json`. Đã gặp imm-08 ghi "PM Manager" nhưng JSON/DB thật là "System Manager" — reconcile doc theo JSON, không ngược lại.

Cross-ref: LL-BE-22 (verify column trước SQL), LL-BE-3 (verify schema), `assetcore-doc` (doc khớp source).

---

## Lessons Learned 2026-06-01 — Audit & refactor subsystem AUTH (đăng ký / đăng nhập / duyệt / mail)

> Nguồn: session audit + fix subsystem AUTH (self-signup, login gate, approve/reject, mail kích hoạt, dead-code cleanup). Mỗi rule là **bug/gap THẬT đã quan sát trong session** (RED đã xảy ra ở production thật — không phải giả định).

### LL-BE-34: Status field phản chiếu state machine — KHÔNG đặt DB `default` gây lệch; khoá invariant status ⟺ gate thật (2026-06-01)

**Bug đã gặp 2026-06-01 (IMM-00 user approval):** Custom Field `User.imm_approval_status` đặt `default='Pending'` ở DB. Hậu quả: MỌI User tạo NGOÀI luồng self-signup (test fixture, ERPNext desk, bench, import) inherit `Pending` **dù `enabled=1`** → badge "Chờ duyệt" giả, không có gate duyệt thật phía sau. Status **decoupled khỏi thực tế truy cập**. Live data: 14–24 user `enabled=1` nhưng vẫn `Pending`.

**Quy tắc:**

1. Field status phản chiếu một state machine / gate nghiệp vụ (approval, active, locked…) **KHÔNG được mang DB-level `default`** trỏ vào một state "có ý nghĩa" (Pending/Active). Default = `''`/null; state chỉ được set **chủ đích** bởi đúng luồng tạo (self-signup → Pending+enabled=0; admin-create → Approved+enabled=1).
2. Xác định **invariant** giữa status và gate thật rồi khoá bằng test — vd `Pending ⟺ enabled=0`. Test phải bắt record vi phạm (`enabled=1 AND status=Pending` PHẢI = 0).
3. Khi sửa default trên field ĐÃ deploy: (a) reconcile Custom Field default lệch trên site cũ (idempotent, trong `after_migrate`); (b) patch backfill data mâu thuẫn (`enabled=1 AND Pending → Approved`, stamp approver giữ audit trail). Verify contradictions = 0 sau patch; patch idempotent (re-run = 0).
4. Khác [[LL-BE-25]] (auto-default ON CREATE qua `before_save` controller — chủ đích, theo ngữ cảnh từng doc): LL-BE-34 cấm **DB static default** vì nó áp mù cho cả record tạo ngoài luồng → phá invariant.

Cross-ref: LL-BE-25 (auto-default controller hook), LL-BE-27 (patch + immutable-audit), `assetcore-test` (test khoá invariant).

### LL-BE-35: Trước khi GIẢI THÍCH hoặc SỬA "logic", xác minh code path LIVE thật sự được wire — dead parallel module đánh lừa (2026-06-01)

**Bug đã gặp 2026-06-01 (audit AUTH):** tồn tại 2 bản song song cùng tên hàm — `services/auth_service.py` (raise `ServiceError`) và `api/auth.py`+`api/user.py` (raise `_err`). FE/runtime CHỈ gọi bản `api/*`; `auth_service.py` là **DEAD CODE** (chỉ 1 test cũ tham chiếu). Agent vòng trước **trích dẫn nhầm `auth_service.py` như "logic đang chạy"** khi giải thích cho user → mô tả sai file thật thi hành. Login lại đi qua Frappe core `/api/method/login` (KHÔNG có hook custom) → gate dựa 100% vào `enabled=0`.

**Quy tắc:**

1. Trước khi mô tả/sửa "logic của X", **xác minh path nào THẬT SỰ chạy** — ai gọi + có whitelist không, KHÔNG chọn file có tên hợp lý nhất:
   ```bash
   grep -rnE "assetcore\.(api|services)\.\w+\.\w+" frontend/src/api/   # FE thật gọi method nào
   grep -rn "@frappe.whitelist" assetcore/api/<file>.py                # method có whitelist mới gọi được qua HTTP
   ```
2. **Hai implementation song song cùng tên hàm = trap.** Bản không có caller / không whitelist = dead code: nói rõ "DEAD CODE", đừng giải thích như đang chạy; backlog dọn (đừng để 2 đường lệch behavior).
3. Login/auth: AssetCore KHÔNG hook `/api/method/login` → mọi gate đăng nhập dựa Frappe core đọc `enabled`. Đừng giả định có custom login logic.
4. User hỏi "logic chỗ này là gì" → trả lời theo path ĐÃ verify chạy, KHÔNG theo file đọc đầu tiên. Sai file = sai câu trả lời (đã xảy ra session này — phải đính chính cho user).

**Red flag (DỪNG, verify lại):** "file này tên đúng nên chắc là nó"; giải thích logic mà chưa grep caller; thấy 2 file cùng chức năng mà không kiểm bản nào wired.

Cross-ref: LL-BE-16 (verify code active bằng bench execute), LL-BE-29 (reproduce trước khi sửa), [[LL-FE-35]] (FE api-client ↔ whitelisted method), [[LL-AUDIT-10]] (auth security).

### LL-BE-36: "Chuông trống / không nhận thông báo" — chẩn đoán DATA trước, đừng vá CODE (2026-06-01)

**Báo cáo user:** "nút chuông không thấy thông báo nào" → nghi engine hỏng. Điều tra: `tabNotification Log` = 0 record. **Engine + contract BE↔FE đúng 100%.** Nguyên nhân thật là **DATA**: mọi record nghiệp vụ đều do `Administrator` tạo + tự gán cho chính mình → `resolve_recipients` strip actor (FR-00-NTF-04, self-notify bị chặn **đúng thiết kế**) → recipients rỗng → không ghi gì. Đây KHÔNG phải bug. Tạo "fix" cho non-bug = vi phạm anti-symptom-patch.

**Decision tree khi gặp "chuông trống / email không tới" — chạy THEO THỨ TỰ, đừng nhảy vào sửa engine:**

1. **Có record không?** `frappe.db.count("Notification Log")`. Nếu 0 → KHÔNG phải lỗi render/FE, là lỗi sinh-record (xuống bước 2).
2. **Actor có ≠ recipient không?** Self-notify bị chặn cố ý. Kiểm tra `owner`/`assigned_to`/`reported_by` của record nghiệp vụ — nếu trùng nhau hết (điển hình: toàn `Administrator` thao tác solo) → recipients rỗng là ĐÚNG. Cần data đa-user (actor ≠ assignee) để có thông báo. Không sửa code.
3. **Engine có chạy không?** Test trực tiếp `_dispatch(["staff01"], ...)` → check `Notification Log` count tăng. Nếu tăng → engine OK, vấn đề ở recipient resolution/data, KHÔNG ở engine.
4. **FE query đúng nguồn không (naming contract)?** Chuông gọi `assetcore.api.layout.get_unread_notifications` → query Frappe core `Notification Log {for_user: session.user, read:0}`. FE client = `frontend/src/api/layout.ts`, KHÔNG phải `api/notifications.ts` (file sau chỉ toggle email/KPI setting). Đừng nhầm 2 file.
5. **Email không tới?** Xem LL-DEPLOY (SMTP site_config fallback + `_user_wants_email` gating) — phần lớn là gating/SMTP infra, không phải engine.

**Quy tắc:**
- `_user_wants_email(user)` chỉ True khi: user ≠ `Administrator` **VÀ** `Notification Settings.{enabled, enable_email_notifications} = 1`. Email câm cho 1 user → check 2 cờ này TRƯỚC khi nghi SMTP.
- **`status="Sent"` ≠ đã vào inbox.** Sender thật = SMTP account của site (vd `miyanovietnam@gmail.com`), KHÁC địa chỉ assignee → Gmail có thể tống spam. Sau khi gửi phải nói rõ "kiểm tra inbox/spam", đừng tuyên bố "đã nhận".
- **self-confirm là ngoại lệ CÓ KIỂM SOÁT** của FR-00-NTF-04 (FR-00-NTF-07): chỉ event tự-báo (Incident `assigned_to` rỗng) mới gọi `resolve_recipients(doc, "reported_by", include_self=True)`. Self-assign (`assigned_to == actor`) **vẫn bị chặn**. Mở rộng whitelist self-confirm = sửa Core Doc (`docs/imm-00/04 §III.1b-2b`) TRƯỚC, không tự nới trong code.

Cross-ref: LL-BE-30 (silent no-op recipient rỗng), `assetcore-deploy` (SMTP site_config + flush queue), `references/notification-contract.md`, anti-symptom-patch (SKILL.md).

### LL-BE-37: Đổi role / role_profile / enabled = CẤP QUYỀN → bắt buộc admin, TUYỆT ĐỐI không self-bypass (2026-06-01)

**2 bug P1 leo quyền (SEC-RBAC-1/2, `api/user.py`):**
- `update_user_roles`: nhánh `target == actor` (self-edit) **bỏ qua** `_assert_admin()` → user thường POST `user=<self>, roles=["AssetCore Super Admin"]` tự lên Super Admin. `_save_user` dùng `ignore_permissions=True` nên DocPerm KHÔNG chặn.
- `assign_role_profile`: điều kiện `session.user != user` cho phép self-assign → user tự gán Role Profile "Quản trị viên IT" → Frappe core clear+replace roles thành bộ admin.

**Root cause (sửa thiết kế, không vá triệu chứng):** coi "đổi role của chính mình" là self-service như đổi mật khẩu. SAI: đổi mật khẩu = self-service hợp lệ; **đổi role/role_profile/enabled = cấp quyền**.

**Quy tắc:**

1. MỌI endpoint sửa `roles`/`role_profile`/`enabled`/quyền của BẤT KỲ user nào (kể cả chính mình) PHẢI gate admin tuyệt đối — KHÔNG có nhánh `if target == session.user: skip_check`. Pattern: `err = _assert_admin(); if err: return err` (hoặc `rbac.require("data.admin")`) đặt **đầu hàm**, trước mọi nhánh.
2. Đừng tin DocPerm bảo vệ khi code set `ignore_permissions=True` (mọi `_save_user`-style helper) → check quyền PHẢI ở tầng service/API, không dựa DocPerm.
3. Phân biệt self-service hợp lệ (`change_password` cần mật khẩu cũ; sửa `full_name`/`phone` trong `_SELF_EDITABLE`) vs cấp quyền (role/profile/enabled) — không gộp chung "self-edit".
4. Test bắt buộc: `TestRolePrivilegeEscalation` — user thường gọi self-`update_user_roles`/`assign_role_profile` với role admin → PHẢI bị từ chối.

Cross-ref: [[LL-BE-24]] (whitelist gate, không tin FE hide), LL-AUDIT-10, `role_profile_catalog.py`, Core Doc `FE_Persona_Navigation.md §7.sexies`.

### LL-BE-38: Base role `AssetCore System User` chỉ read shared-core — over-grant DocPerm = leak BE dù FE ẩn (2026-06-01)

**Bug P1 (audit DocPerm):** role nền `AssetCore System User` (mọi user IMM bắt buộc có) được cấp **read trên ~38 DocType nghiệp vụ nhạy cảm** (Compliance Rule/CAPA/Internal Audit, Needs/Procurement/Vendor Eval, AC Supplier, Tech Spec, Training, Asset Document...) → mọi user (kể cả KTV) đọc được qua `/api/resource/<DocType>` **dù FE đã ẩn menu**. Một số còn bật `export:1`. `rbac.py` SẠCH (resolve qua `frappe.has_permission`); nguồn leak nằm 100% ở DocPerm trong doctype JSON.

**Quy tắc:**

1. **FE ẩn ≠ BE bảo vệ.** Ẩn menu/route ở FE chỉ là UX; data vẫn trả qua REST nếu DocPerm cho read. DocType nhạy cảm PHẢI chặn ở DocPerm/service, không chỉ ở nav.
2. Role nền `AssetCore System User` chỉ read **shared-core** (AC Asset, Asset Lifecycle Event, Depreciation, Downtime — đủ để SPA login + hiển thị tên/enrich). DocType nghiệp vụ chỉ cấp cho **owning role** (Domain Manager/User) + Auditor (read-all hợp lệ).
3. Audit nhanh role nền:
   ```bash
   grep -rl '"role": "AssetCore System User"' assetcore/assetcore/doctype/*/*.json
   ```
   Verify live: `frappe.set_user("<tech user>"); frappe.has_permission("Compliance Rule","read")` PHẢI = False.
4. Khi gỡ read khỏi base role: kiểm chéo owning role nghiệp vụ vẫn còn read (đừng under-grant), child table khoá theo parent cho nhất quán.
5. Migrate KHÔNG tự xoá DocPerm row đã gỡ khỏi JSON trên site cũ → cần DocType reload/patch khi deploy (xem `assetcore-deploy`).

Cross-ref: LL-BE-38 dùng cặp với LL-BE-39 (picker vs list trước khi gỡ), LL-AUDIT-10, LL-FE-35/36 (cap nav khớp DocPerm).

### LL-BE-39: Guest endpoint KHÔNG được tiết lộ tồn tại/trạng thái tài khoản — user enumeration (2026-06-01)

**Bug MEDIUM (`api/auth.py::check_account_status`, allow_guest):** trả nhãn phân biệt `not_found` vs `active` vs `pending/rejected/disabled` cho email BẤT KỲ **không cần mật khẩu** → kẻ tấn công liệt kê email đã đăng ký + trạng thái. Docstring "biện minh UX" KHÔNG cứu được — phân biệt tồn tại/trạng thái = enumeration.

**Quy tắc:**

1. Endpoint `allow_guest` KHÔNG được phân biệt "email tồn tại hay không": not_found và active phải trả **y hệt** (1 nhãn trung lập, vd `unknown`). Tốt nhất không chạm DB theo tồn tại → timing đồng nhất.
2. Trạng thái nhạy cảm (pending/rejected/disabled) chỉ surface **sau khi chứng minh biết mật khẩu** — endpoint password-gated (`account_state(usr, pwd)` xác thực `check_password` trước; sai mật khẩu / không tồn tại → đồng nhất `invalid_credentials`).
3. Rate-limit kép per-IP **và** per-email cho mọi guest endpoint nhận identifier.
4. Áp cho mọi guest endpoint nhận email/username: register, forgot-password, status-check. Chuẩn ngành (GitHub/Google): thông báo trung lập "sai thông tin đăng nhập".
5. Test bắt buộc: `assertEqual(guest_call("active_email"), guest_call("nonexistent_email"))`.

Cross-ref: Core Doc `04_Backend_Design.md` BR-00-USR-02, LL-AUDIT-10.

### LL-BE-40: Trước khi GỠ DocPerm read — phân biệt picker (`ignore_permissions`) vs list (theo quyền) (2026-06-01)

**Bối cảnh (audit DEFER):** định gỡ `AssetCore System User` read khỏi Data master (Department/Location/Category/Device Model...), nhưng phát hiện **2 đường tải tách biệt**:
- **Picker/dropdown trên form** (`SmartSelect`/`LinkSearch`) → `search_link` → `frappe.db.get_all(..., ignore_permissions=True)` → **KHÔNG phụ thuộc DocPerm** → gỡ read an toàn, dropdown vẫn chạy.
- **Filter của list view** (`AssetListView.refData.fetchAll` → `list_*`) → `frappe.get_list()` → **theo quyền user** → gỡ read = filter rỗng cho mọi user thường = regression nhìn thấy ngay.

**Quy tắc:**

1. Trước khi gỡ/siết DocPerm read một DocType "danh mục dùng chung", grep MỌI nơi FE tải nó và phân loại từng đường: `ignore_permissions` (an toàn gỡ) vs theo-quyền (gỡ sẽ vỡ).
   ```bash
   grep -rn 'doctype="<DT>"\|<DT>' frontend/src   # SmartSelect/LinkSearch vs refData/list_*
   grep -n 'ignore_permissions' assetcore/services/imm04.py   # search_link path
   ```
2. Còn đường theo-quyền cần data này → KHÔNG gỡ liều; chuyển đường đó sang endpoint `ignore_permissions` chuyên dụng (kèm đủ field, vd GMDN cho filter category) RỒI mới gỡ.
3. Test invariant chống regression: `search_link("<DT>")` trả options **bất kể** DocPerm read = False (`TestPickerPermissionDecoupling`).
4. Anti-FP: "siết quyền" mà làm rỗng dropdown/filter của user hợp lệ = regression, không phải fix. Verify dropdown thật trước khi tuyên bố xong.

Cross-ref: LL-BE-38 (over-grant base role), `services/imm04.py::search_link`, `_ALLOWED_SEARCH_DOCTYPES`.

### LL-BE-41: `frappe.db.count` ≠ `frappe.get_all` cho `["<", date]` với hàng NULL — count-vs-drill divergence (2026-06-04)

**Triệu chứng:** KPI count (qua `frappe.db.count`) và drill list (qua `frappe.get_all`) dùng "cùng" filter dict `{"expiry_date": ["<", today]}` nhưng RA SỐ KHÁC NHAU khi tồn tại hàng `expiry_date = NULL`.

**Root cause:** hai API build SQL khác nhau cho cùng operator-tuple:
- `frappe.db.count` (query_builder) → `expiry_date < '...'` → NULL **bị loại** (NULL `<` date = NULL, không true).
- `frappe.get_all` (DatabaseQuery) → bọc `ifnull(expiry_date, ...)` → hàng NULL **lại khớp** `< today`.

→ Một predicate "chung" cho count + drill VẪN diverge nếu chỉ dựa `["<", date]` ngầm-loại-NULL. Đây CHÍNH LÀ class bug count-vs-drill (mirror BR-05-16 / INV-EXP-1).

**Fix (BR-05-16, `services/imm05.py::expired_filter`):**
1. NULL-guard **tường minh** `["expiry_date", "is", "set"]` — KHÔNG dựa hành vi ngầm.
2. Dùng **list-of-conditions** `[[field, op, val], ...]` (KHÔNG dict): chứng minh bằng probe cho kết quả ĐỒNG NHẤT trên cả `db.count` và `get_all`.
3. Gộp với filter khác: `_dict_to_conditions(dict_filters) + expired_filter()` (AND).

**Anti-FP / quy tắc khoá:** mọi predicate "count card == drill rows" (SoT chung 2 read-path) PHẢI: (a) thêm NULL-guard tường minh nếu field nullable; (b) verify INV bằng **probe thật seed hàng NULL** (count==len(drill)), không tin "operator tự loại NULL". `db.count` đúng KHÔNG bảo chứng `get_all` đúng và ngược lại.

Cross-ref: BR-05-15 (is_fully_depreciated count==drill), `expired_filter()`, `_dict_to_conditions()`, test `TestExpiredSoT::test_expiry_null_not_expired_no_crash` + `test_count_equals_drill_mixed_set`.

## Lessons Learned 2026-06-10 — List/permission scoping, page-size DoS, error-surface, identity-leak, RBAC gate (QA + mobile-BE audit)

### LL-BE-42: List `pagination.total` PHẢI dùng cùng `permission_query_conditions` như drill — KHÔNG `db.count`/`get_all` (2026-06-10)

**Triệu chứng→nguyên nhân:** persona row-scoped (vendor/technician có `ac_asset_query`) → header "Tổng N" ≠ số dòng (KTV `/assets` total 1430, rows 0). `frappe.db.count` VÀ `frappe.get_all` đều BỎ QUA `permission_query_conditions` row-scope hook → count đếm CẢ bảng, rows chỉ subset.

**Rule (kiểm được):** mọi list endpoint phân trang → `pagination.total = len(frappe.get_list(DT, filters=..., or_filters=..., limit_page_length=0))` DƯỚI session user (KHÔNG `ignore_permissions`), cùng `filters`+`or_filters` với items query. Helper chuẩn = `count_with_or` (`services/shared/filters.py:105-160`, đã chuyển sang `get_list(limit_page_length=0)`). Self-check: probe `GET ...list_X?page=1&page_size=5` dưới persona row-scoped → assert `pagination.total == len(items_toàn_bộ_trang)`; KHÔNG bao giờ để count + items chạy 2 predicate khác nhau.

Cross-ref: LL-BE-41 (NULL-ifnull divergence — KHÁC; rule này lo permission_query_conditions scoping); `memory/asset_list_count_drill_technician_p1.md` (P1 KTV); `services/shared/filters.py:105-160`.

### LL-BE-43: `page_size` PHẢI cap upper-bound `min(int(page_size),100)` ở MỌI list endpoint — chống unbounded-fetch DoS (2026-06-10)

**Triệu chứng→nguyên nhân:** client gửi `page_size=999999` → `page_size=int(page_size)` trần materialize toàn bảng → OOM/latency.

**Rule (kiểm được):** mọi `@frappe.whitelist()` list/paginated endpoint → `page_size = max(1, min(int(page_size), 100))` NGAY dòng đầu function (trước khi truyền xuống service/get_list). Pattern đúng = `imm01.py:93/365`, `imm02.py:70`, `imm03.py:65/270/556`, `layout.py:56`, `user.py:889`. CÒN THIẾU cap (P1 backlog): `imm00.list_assets` (page_size:int=20 không clamp), `imm15.py:62/144/193`, `imm16.py:41/61/87`, `inventory.py:36/84`, `purchase.py:84`. Self-check: `grep -n 'page_size' api/*.py | grep -v 'min('` → mỗi list endpoint không có `min(...,100)` là 1 gap.

Cross-ref: LL-BE-42 (count==rows cùng predicate); `api/imm01.py:93` (pattern đúng) vs `api/imm15.py:62`/`inventory.py:36`/`purchase.py:84` (trần).

### LL-BE-44: `_err(str(e))`/`nthrow(str(e))` catch-all LEAK raw exception text ra FE — dùng message hằng + log_error trace riêng (2026-06-10)

**Triệu chứng→nguyên nhân:** `except Exception as e: return _err(str(e), ErrorCode.INTERNAL)` → `str(e)` rò chi tiết nội bộ (tên cột SQL, path, stack hint, DocType) ra envelope FE thấy.

**Rule (kiểm được):** trong `except Exception as e:` của API layer TUYỆT ĐỐI KHÔNG forward `str(e)`. Pattern đúng: `frappe.log_error(frappe.get_traceback(), '<MODULE-XX> <func>')` (giữ trace — LL-BE-20) RỒI `return _err(_(<hằng message Việt trung lập>), ErrorCode.INTERNAL)` HOẶC `nthrow(MSG.GENERIC_SERVER_ERROR)`. CHỈ forward `str(e)` khi e là `ServiceError` đã dùng `MSG.*` registry — bắt riêng `except ServiceError` TRƯỚC `except Exception`. Self-check: `grep -rn '_err(str(e)\|nthrow(str(e)\|_err(f"{e}' api/*.py` → mỗi match trên nhánh `ErrorCode.INTERNAL`/catch-all = leak. CÒN: `dashboard.py:337/532/1001`, `imm01.py:60`, `imm02.py:45`, `imm03.py:46`.

Cross-ref: LL-BE-20 (log_error full traceback), notification-contract `MSG.*`.

### LL-BE-45: In-handler error (404/409/422) đến TRÊN HTTP-200 + 2 loại 403 khác nhau — client/test KHÔNG branch theo status-line (2026-06-10)

**Triệu chứng→nguyên nhân:** `_err`/`nthrow`→`handle()` KHÔNG set `frappe.local.response.http_status_code` (verify `bench execute`: status-line = NULL); 404/409/422 CHỈ nằm trong body JSON (`http_status`/`code`). `messages.py['http_status']` là SSoT (vd `IMM11_ASSET_BLOCKED`=409 CAL-008, KHÔNG 422).

**Rule (kiểm được):**
1. Mô hình hoá OpenAPI cho client codegen → đáp lỗi nghiệp vụ khai dưới response `'200'` = `oneOf[<Created>, Error]` + discriminator `success` — KHÔNG khai key `'404'`/`'409'` (codegen route theo status-line không bắt được).
2. PHÂN BIỆT 2 loại 403: **dispatcher-403** (guest/no-token, gate `rbac.require(...)`/`frappe.throw(PermissionError)` TRƯỚC `handle()` vd imm09.py:40/imm11.py:95) = status-line 403 THẬT → client RE-AUTH; **in-handler cap-403** (bearer hợp lệ thiếu cap, `_err(msg,403)` vd imm12.py:96) = HTTP-200 + envelope `{code:FORBIDDEN, http_status:403}` → client SHOW-MESSAGE, KHÔNG re-auth.
3. Test/FE branch theo `envelope.http_status`/`envelope.code`, KHÔNG theo HTTP status-line.

Cross-ref: `memory/mobile_be_openapi_contract_gotchas.md` §2-3; `messages.py` http_status SSoT.

### LL-BE-46: Message trùng-định-danh (dup serial/asset_code) KHÔNG được leak record HIỆN HỮU sở hữu định danh đó (2026-06-10)

**Triệu chứng→nguyên nhân:** template `MSG.IMM04_DUP_SERIAL` = `"VR-01: Serial '{serial}' đã được gán cho {ref}."` (messages.py:424) → `{ref}` lộ asset hiện hữu → rò định danh chéo (user A biết asset của khoa/vendor B qua thông báo trùng).

**Rule (kiểm được):** lỗi duplicate trên field định danh (serial, asset_code, UDI) → template message KHÔNG interpolate tên/ref của record KHÁC giữ giá trị. Sửa: bỏ `{ref}` khỏi template user-facing (chỉ "Serial đã tồn tại trong hệ thống" + action_hint tra cứu); nếu cần điều hướng tới bản ghi cũ → gate theo quyền đọc record đó (chỉ surface `{ref}` khi caller có read-permission) HOẶC trả `ref` trong field `context` riêng để FE quyết định theo cap. Áp cho mọi `*_DUP_*`/`*_DUPLICATE_*` template có placeholder trỏ record khác.

Cross-ref: `utils/messages.py:422-426`; commit c827de3 (validate asset code+serial identity on bulk import).

### LL-BE-47: Predicate date so-sánh nullable (ifnull-coercion) — NULL-guard tường minh cho imm06/imm11 due/expiry (2026-06-10)

**Triệu chứng→nguyên nhân:** filter `{"<field>": ["<", nowdate()]}` trên field NULLABLE diverge giữa read-path (db.count loại NULL; get_list bọc `ifnull(...)` khớp NULL) → count card ≠ drill rows.

**Rule (kiểm được):** mọi predicate "count card == drill rows" trên field date nullable PHẢI thêm NULL-guard TƯỜNG MINH `["<field>", "is", "set"]` + dùng list-of-conditions `[[field,op,val],...]` (KHÔNG dict), verify bằng probe seed-NULL (count==len(drill)). Đã chuẩn ở imm05 (`expired_filter`). Áp đồng dạng cho `imm06.py:104` (`expiry_date: ["<", nowdate()]`) + `imm06.py:607` (`expiry_date: ("<", today)`) + mọi `due_date`/`recertification_due_date`/`next_calibration_date` count-vs-drill ở imm06/imm11 — đừng tin operator tự loại NULL.

Cross-ref: LL-BE-41 (imm05 expired_filter divergence), LL-BE-42; `services/imm06.py:104,607`.

### LL-BE-48: Overdue (PM/calibration/date-derived) = SERVER-side boolean flag SSoT — không có client-clock so-sánh, không deriver song song (2026-06-10)

**Triệu chứng→nguyên nhân:** QR-screen vs admin-detail bất đồng vì admin dùng `isPmOverdue()` client-clock (tz-drift → highlight đỏ sai).

**Rule (kiểm được):** mọi chỉ báo "quá hạn" suy từ ngày PHẢI là 1 boolean flag tính SERVER-side qua deriver dùng-chung, trả trong MỌI payload màn hình đó dùng; FE CHỈ render flag, KHÔNG bao giờ `new Date(d) < new Date()`. Deriver chuẩn (tz-safe): `True ⟺ ngày≠rỗng ∧ getdate(d) < getdate(nowdate())` (STRICT `<`) `∧ lifecycle_status ∉ BLOCKED_FOR_WO (Out of Service, Decommissioned)`. Reference duy nhất: `services/imm00.py:_is_pm_overdue` (:339) / `_is_calibration_overdue` (:355) — feed CẢ scan-info (`build_asset_scan_info`) LẪN admin-detail (`get_asset` emit `pm_overdue`+`calibration_overdue`). Chỉ báo date-derived MỚI → thêm flag mới qua deriver dùng-chung, KHÔNG so-sánh date client-side song song. Caveat: `byt_reg_expiry` (BYT) khác ngữ nghĩa → flag riêng `byt_reg_expired`, KHÔNG tái dùng deriver PM.

Cross-ref: `memory/overdue_server_flag_ssot.md`; `services/imm00.py:339-360`; LL-BE-47 (NULL-guard predicate).

### LL-BE-49: Mutating `@whitelist` endpoint THIẾU `rbac.require`/`has_any_role` = lỗ leo quyền (FE hide ≠ BE gate) — gate capability SSoT, không gate role-name (2026-06-10)

**Triệu chứng→nguyên nhân:** attacker gọi API trực tiếp qua DevTools/curl bypass FE button-hide (LL-BE-24). Gate bằng role-name literal không có trong hệ role thật → 'RBAC dead-gate': `has_any_role` luôn False (fail âm thầm, test giả định vẫn pass — LL-BE-30).

**Rule (kiểm được):** MỌI `@frappe.whitelist(methods=["POST"])` (hoặc mutating semantics) → `rbac.require("<cap>.write")` HOẶC `has_any_role((Roles.X, Roles.SYS_ADMIN))` ở DÒNG ĐẦU body. Capability string BE==FE EXACT; gate bằng CAPABILITY resolve qua `rbac.can()`/`frappe.has_permission`, KHÔNG gate bằng role-name không có trong `role.json`/`constants.py:Roles`. Endpoint sửa role/role_profile/enabled = admin tuyệt đối, KHÔNG self-bypass (LL-BE-37). CÒN backlog (P2, 0 gate): `imm15.py` (12 POST), `inventory.py` (19 POST), `purchase.py` (7 POST), `imm01/02/03/imm16` mutating. Self-check = AST audit LL-BE-24 §5 trên từng file.

Cross-ref: LL-BE-24 (whitelist permission backup gate), LL-BE-30 (RBAC dead-gate), LL-BE-37 (self-bypass admin); `memory/role_security_audit_20260601.md`.
