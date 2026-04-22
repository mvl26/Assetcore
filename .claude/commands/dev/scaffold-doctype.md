---
description: Scaffold a new Frappe DocType with all required files for AssetCore
---

Scaffold a new DocType for: `$ARGUMENTS`

**Generate ALL of the following:**

**1. DocType JSON** — complete field list, permissions, naming, `track_changes: 1`

**2. Controller** (`<name>.py`)

```python
class <ClassName>(Document):
    def validate(self): ...
    def before_insert(self): ...
    def on_submit(self): ...
    def on_cancel(self): ...
```

Describe each method's responsibility — business logic goes in `assetcore/services/`.

**3. Service Layer** (`assetcore/services/<snake_name>.py`)

```python
def process_<action>(doc: Document) -> None:
    """Description."""
    ...
```

**4. API Endpoint** — new `@frappe.whitelist()` function in `assetcore/api/<module>.py` using `_ok`/`_err` pattern.

**5. Test File** (`assetcore/tests/test_<snake_name>.py`) — one happy-path test, one validation-failure test.

**6. Bench Commands**

```bash
bench --site miyano migrate
bench --site miyano clear-cache
bench --site miyano run-tests --doctype "<DocType Name>"
```

**File placement:** `assetcore/assetcore/doctype/<snake_name>/`
