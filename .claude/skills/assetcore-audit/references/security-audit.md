# assetcore-audit — Security Review (heavy reference)

> Phần 2 — Security Review: threat model + layered security checklist. `SKILL.md` giữ INLINE: security report format + audit verdict. Đây là chi tiết để chạy security review.
>
> Bổ sung: whitelist permission gate (S-9..S-11) ở [`module-audit-pillars.md`](module-audit-pillars.md) Phần 5; regression class A–L + LL-AUDIT-* ở [`rules.md`](rules.md).

## Threat model

1. **Privilege escalation** — Technician trigger admin-only action
2. **Vendor data leakage** — Hospital A thấy data Hospital B
3. **Audit trail tampering** — backdating hoặc xóa lifecycle record
4. **Session hijacking** — CSRF, stale token
5. **Injection** — SQL via raw `frappe.db.sql`, XSS in descriptions
6. **Mass exfiltration** — unbounded list endpoint dump toàn bộ table

## Security checklist

### Layer 1 — Service permission gate

```python
from assetcore.services.shared.permissions import require_role
from assetcore.services.shared.constants import Roles

def assign_technician(name: str, *, technician: str):
    require_role(Roles.CAN_CREATE_WO, "Không đủ quyền giao việc")
    # ...
```

- [ ] Mọi mutating service function có `require_role(...)` ở đầu
- [ ] Roles từ `Roles` constant, không hardcode string
- [ ] Permission check TRƯỚC khi đọc record (không để data leak qua error message)

### Layer 2 — DocPerm (defense in depth)

```bash
# Verify permissions trong JSON
grep -A10 '"permissions"' assetcore/assetcore/doctype/<name>/<name>.json
```

- [ ] `delete: 0` cho mọi role trên audit trail DocTypes
- [ ] Không có `System Manager` trong non-admin DocType permissions
- [ ] `read: 1` tối thiểu cho operational roles

### Whitelist hygiene

```bash
# Tìm endpoints thiếu permission gate
grep -B2 "@frappe.whitelist" api/immXX.py | grep -v "require_role\|#"
```

- [ ] Mọi POST endpoint có `methods=["POST"]`
- [ ] Mọi endpoint đọc data nhạy cảm có `require_role` hoặc filter theo `frappe.session.user`
- [ ] Pagination params bounded: `min(int(page_size), 200)` — không cho dump unlimited

### Audit trail integrity

```bash
# Tìm bypass (insert trực tiếp thay vì log_audit_event)
grep -rn "doctype.*IMM Audit Trail" assetcore/ | grep -v "log_audit_event\|test_"
```

- [ ] Không có code insert `IMM Audit Trail` trực tiếp
- [ ] Không có `frappe.delete_doc("IMM Audit Trail", ...)` ngoài test teardown
- [ ] `delete: 0` trong DocPerm cho `IMM Audit Trail`

### Input validation & Injection

```bash
# Tìm raw SQL với string interpolation
grep -n "frappe\.db\.sql" assetcore/ -r | grep -v "?.*%s\|:%(.*)" | grep "%\|format\|f\""
```

- [ ] Raw SQL dùng parameterized queries (`%s`, không f-string)
- [ ] User-entered text không render as HTML (escape hoặc dùng Jinja `{{ value | e }}`)
- [ ] File upload qua `@frappe.whitelist(methods=["POST"])` với MIME type check

### Vendor isolation (multi-tenant)

```python
# Mọi list query phải filter theo tenant
filters["hospital_site"] = frappe.local.site
# Hoặc check ownership:
if doc.created_by_hospital != frappe.local.site:
    frappe.throw("Không có quyền truy cập")
```

- [ ] Mọi `list_*` endpoint filter theo `hospital_site` hoặc user scope
- [ ] Vendor Engineer không thấy data của hospital khác
