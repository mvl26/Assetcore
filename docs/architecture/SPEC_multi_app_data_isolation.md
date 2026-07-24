# Spec: Cách ly dữ liệu đa-app trên site dùng chung (Multi-App Data Isolation)

- **Ngày:** 2026-07-22
- **Trạng thái:** Draft — chờ USER duyệt trước khi implement
- **Module:** IMM-00 (Foundation) — ảnh hưởng chéo toàn app
- **Actor:** Quản trị viên hệ thống (QTV), mọi persona AssetCore, và người dùng của các app cùng site
- **Triggering issue:** `WFC-ACT-202607-041074` — `WFC Activity Log` ghi `user_created` cho
  `crm.user5@example.com` (user của app `antmed_crm`).

---

## 1. Objective

Site `miyano` chạy **6 app cùng lúc**: `frappe`, `assetcore`, `workflowcore`, `antmed_crm`,
`erpnext`, `hrms`. Các app này dùng chung một tập **DocType lõi** (`User`, `Has Role`,
`Notification Log`, `Email Queue`, `Contact`, `File`, `ToDo`, `Comment`, `Communication`).

Nhiều điểm trong AssetCore (và WorkflowCore) **đọc/ghi/xoá các DocType lõi này ở phạm vi
toàn site** thay vì phạm vi app của mình. Hệ quả:

- Ghi nhầm bản ghi của app khác vào log/dữ liệu của mình (triệu chứng USER báo).
- Ghi đè / phá dữ liệu app khác (nghiêm trọng nhất: chặn hàng đợi email của CRM/HRMS).
- Lộ dữ liệu app khác ra UI/export của AssetCore (PII, thông báo).

**Mục tiêu:** mọi thao tác đọc/ghi/xoá của AssetCore lên DocType dùng chung phải
**giới hạn trong phạm vi sở hữu của AssetCore**, xác định qua marker đã có sẵn — không
thêm field, không `bench migrate`.

**Không thuộc mục tiêu:** tách site, tách DB, đổi kiến trúc RBAC, sửa `erpnext`/`hrms`/`antmed_crm`.

### Định nghĩa "thuộc AssetCore" (ownership marker — quyết định của USER)

| Đối tượng | Marker | Nguồn |
|---|---|---|
| **User** | giữ base role `AssetCore System User` | `assetcore.setup.role_profile_catalog.BASE_ROLE` (SSoT đã có) |
| **Bản ghi (record)** | `DocType.module` ∈ module của app `assetcore` | `Module Def.app_name == "assetcore"` → 110 DocType |
| **User của WorkflowCore** | giữ bất kỳ role `WFC *` (`WFC Admin` / `WFC Manager` / `WFC Staff`) | `Role` live |
| **Bản ghi WorkflowCore** | `Module Def.app_name == "workflowcore"` → 18 DocType | |

Marker này **runtime-derivable**, không cần custom field, không cần backfill, không cần migrate.

---

## 2. Bằng chứng (đã xác minh trên DB live, site `miyano`)

### 2.1 Triệu chứng USER báo — app `workflowcore`

```
WFC-ACT-202607-041074
  event_type   = user_created
  target_doctype = User
  target_name  = crm.user5@example.com     ← user của antmed_crm
  target_title = David Sales
```

Nguồn: `apps/workflowcore/workflowcore/hooks.py:22`

```python
doc_events: dict = {
    "User": {
        "after_insert": "workflowcore.auth_hooks.on_user_insert",
        "on_update":    "workflowcore.auth_hooks.on_user_update",
    },
}
```

`on_user_insert` (`auth_hooks.py:150`) chỉ loại `Guest`/`Administrator` — **không có bộ lọc
app-ownership** → mọi user do bất kỳ app nào tạo đều bị ghi vào `WFC Activity Log`.

Phân bố thực tế `tabWFC Activity Log`:

| target_doctype | event_type | count |
|---|---|---|
| User | user_created | 17.608 |
| User | user_enabled | 16.353 |
| User | user_disabled | 1.504 |
| User | login_success | 343 |
| User | profile_updated | 264 |
| User | notification_policy_updated | 6 |
| **WFC Task** | task_completed | **4** |
| **WFC Workflow Instance** | instance_created | **1** |
| **WFC Workflow Template** | template_created | **1** |

→ **35.465 dòng** nhắm `User` (đa số ngoại lai) vs **6 dòng** nhắm DocType của chính WorkflowCore.

### 2.2 Cùng loại lỗi bên trong AssetCore (repo này, code production, đã loại test/patch scratch)

| # | Mức | Vị trí | Hành vi hiện tại | Hệ quả chéo app |
|---|---|---|---|---|
| **A1** | **P1 ghi** | `assetcore/setup/email.py:130` `_quarantine_stale_queue()` | `get_all("Email Queue", {"status": "Not Sent"})` rồi set `status="Error"` cho **mọi** dòng | Huỷ email đang chờ gửi của CRM/HRMS/ERPNext. Phá dữ liệu app khác. |
| **A2** | **P1 ghi** | `assetcore/api/layout.py:120` `mark_all_as_read()` | `UPDATE tabNotification Log SET read=1 WHERE for_user=%s` | "Đánh dấu tất cả đã đọc" của AssetCore xoá luôn trạng thái chưa đọc của CRM/WFC/HRMS. |
| **A3** | **P1 đọc** | `assetcore/api/layout.py:57,88` `get_unread_notifications` / `list_notifications` | lọc duy nhất `for_user` | Chuông AssetCore hiển thị thông báo của CRM/WorkflowCore/HRMS. |
| **A4** | **P1 ghi** | `assetcore/patches/v3_2/009_backfill_base_role.py:38` `grant_base_role()` | `user_names=None` → `get_all("User", {"user_type": "System User"})` toàn site, rồi append `AssetCore System User` | Cấp base role AssetCore cho user CRM/HRMS → họ **lọt vào** `list_users` / `list_assignable_users` (vốn lọc đúng theo base role). Ô nhiễm tự khuếch đại. |
| **A5** | P2 đọc | `assetcore/repositories/notification_repo.py:79` `count_email_opt_out()` | đếm mọi `User` `enabled=1, user_type="System User"` | KPI "độ phủ thông báo" của AssetCore lấy mẫu số là user của app khác → số liệu sai. |
| **A6** | P2 đọc | `assetcore/utils/import_helpers.py:413` `_export_users()` | `get_all("User", name not in [Administrator, Guest])` | File export user của AssetCore chứa toàn bộ user CRM/HRMS (rò rỉ PII). |
| **A7** | P2 ghi | `assetcore/api/user.py:689` `_cleanup_orphan_contacts()` | xoá `Contact` khớp `email_id` không phụ thuộc app sở hữu | Xoá nhầm Contact của CRM (lead/khách hàng trùng email). |
| **A8** | P3 quyền | `assetcore/setup/setup_core_permissions.py:67-73,109-121` | cấp R/W/C/D cho role AssetCore trên `File`/`ToDo`/`Comment`/`Communication`/`Contact`/`Address`/`Notification Log` phạm vi toàn site | Người dùng AssetCore đọc/sửa được dữ liệu lõi của CRM/HRMS qua desk/API. |

### 2.3 Đã đúng phạm vi — KHÔNG sửa (tránh regression)

| Vị trí | Vì sao đã đúng |
|---|---|
| `assetcore/api/user.py:327,1082` `list_users` / `list_assignable_users` | đã lọc `base_holders = _users_with_role(BASE_ROLE)` |
| `assetcore/services/shared/role_hooks.py:33` `sync_umbrella` | early-return nếu `doc.role != "AssetCore Super Admin"` |
| `assetcore/services/imm06.py:1966` `handle_user_dept_change` | chỉ đọc `IMM User Competency` lọc theo `user` |
| `IMM Audit Trail`, `Asset Lifecycle Event` | chỉ ghi từ code AssetCore, target là DocType AssetCore |
| `assetcore/hooks.py:208-228` doc_events `User`/`Has Role`/`Custom DocPerm` | có kích hoạt cho user ngoại lai nhưng early-return, **không ghi dữ liệu** — chỉ là nhiễu hiệu năng, chấp nhận được |

---

## 3. Tech Stack

- Python 3.11 / Frappe v15 (không phụ thuộc ERPNext)
- MariaDB
- Test: `frappe.tests.utils.FrappeTestCase` (unittest), chạy qua `bench run-tests`
- App liên quan: `assetcore` (repo này), `workflowcore` (`/home/miyano/frappe-bench/apps/workflowcore`)

---

## 4. Commands

```bash
# Test module-isolated (DoD chính)
bench --site miyano run-tests --app assetcore --module assetcore.tests.test_app_isolation

# Test toàn app AssetCore
bench --site miyano run-tests --app assetcore

# Test WorkflowCore
bench --site miyano run-tests --app workflowcore

# Lint
cd /home/miyano/frappe-bench/apps/assetcore && ruff check assetcore/

# Backup TRƯỚC khi dọn dữ liệu (bắt buộc)
bench --site miyano backup --with-files

# Dọn dữ liệu ngoại lai (script mới, chạy tay sau khi backup)
cd /home/miyano/frappe-bench/sites && ../env/bin/python ../purge_foreign_app_records.py
```

> **HARD-STOP còn hiệu lực:** KHÔNG `bench migrate`. KHÔNG `git commit` khi USER chưa gọi
> `/assetcore-commit`. Sửa `api/*.py` cần USER reload gunicorn `--preload` mới có hiệu lực HTTP-live.

---

## 5. Project Structure

```
assetcore/
  utils/app_scope.py                  → MỚI: SSoT marker sở hữu app (doctype + user)
  api/layout.py                       → SỬA A2, A3
  setup/email.py                      → SỬA A1
  patches/v3_2/009_backfill_base_role.py → SỬA A4
  repositories/notification_repo.py   → SỬA A5
  utils/import_helpers.py             → SỬA A6
  api/user.py                         → SỬA A7
  setup/setup_core_permissions.py     → SỬA A8 (chỉ nếu USER duyệt riêng, xem §9)
  tests/test_app_isolation.py         → MỚI: guard tĩnh + test hành vi

../workflowcore/workflowcore/
  utils/app_scope.py                  → MỚI: marker tương ứng
  auth_hooks.py                       → SỬA W1
  tests/test_app_isolation.py         → MỚI

/home/miyano/frappe-bench/
  purge_foreign_app_records.py        → MỚI (ngoài repo — script dọn dữ liệu, chạy tay)
```

---

## 6. Code Style

Theo CLAUDE.md §15: type hints cho mọi function, docstring bắt buộc, không logic trong
controller, đặt tên theo domain.

Module SSoT mới `assetcore/utils/app_scope.py`:

```python
# Copyright (c) 2026, AssetCore Team
"""SSoT phạm vi sở hữu của app AssetCore trên site dùng chung nhiều app.

Site khách hàng có thể cài AssetCore CẠNH các app khác (CRM, ERPNext, HRMS,
WorkflowCore). Các app này dùng CHUNG DocType lõi (`User`, `Notification Log`,
`Email Queue`, `Contact`...). Mọi truy vấn của AssetCore lên DocType lõi PHẢI đi
qua module này để không đọc/ghi/xoá nhầm dữ liệu của app khác.

Marker sở hữu (KHÔNG cần custom field, KHÔNG cần migrate):
  - DocType thuộc AssetCore  ⟺ `DocType.module` ∈ module của app `assetcore`.
  - User thuộc AssetCore     ⟺ giữ base role `AssetCore System User`.
"""
from __future__ import annotations

import frappe

from assetcore.setup.role_profile_catalog import BASE_ROLE

APP_NAME = "assetcore"


def owned_doctypes() -> set[str]:
    """Tập tên DocType do app AssetCore sở hữu (cache theo request).

    Returns:
        set[str]: vd {"AC Asset", "PM Work Order", "IMM Audit Trail", ...} (110 DocType).
    """
    def _load() -> list[str]:
        modules = frappe.get_all("Module Def", {"app_name": APP_NAME}, pluck="name")
        if not modules:
            return []
        return frappe.get_all("DocType", {"module": ["in", modules]}, pluck="name")

    return set(frappe.cache().get_value(f"{APP_NAME}:owned_doctypes", _load) or [])


def owned_users() -> set[str]:
    """Tập user thuộc AssetCore = người giữ base role `AssetCore System User`.

    Loại `Administrator`/`Guest` (tài khoản hạ tầng, không thuộc scope nghiệp vụ).

    Returns:
        set[str]: email/username của user AssetCore.
    """
    holders = frappe.get_all(
        "Has Role",
        filters={"parenttype": "User", "role": BASE_ROLE},
        pluck="parent",
    )
    return set(holders) - {"Administrator", "Guest"}
```

Áp dụng tại điểm gọi — ví dụ A3 (`api/layout.py`):

```python
    rows = frappe.get_all(
        _DT_NOTIF,
        # Site dùng chung nhiều app: chuông AssetCore CHỈ hiển thị thông báo phát
        # sinh từ DocType của AssetCore, không lẫn CRM/WorkflowCore/HRMS.
        filters={
            "for_user": user,
            "read": 0,
            "document_type": ["in", sorted(app_scope.owned_doctypes())],
        },
        fields=_NOTIF_FIELDS,
        order_by="creation desc",
        limit_page_length=limit,
    )
```

---

## 7. Testing Strategy

- **Framework:** `FrappeTestCase`, file `assetcore/tests/test_app_isolation.py`.
- **Mức test:**
  1. **Guard tĩnh (chống tái phát — quan trọng nhất).** Quét AST toàn bộ `assetcore/**/*.py`
     (trừ `tests/`, `patches/`, `seed/`, `scripts/`): mọi lời gọi `frappe.get_all` /
     `frappe.db.get_all` / `frappe.db.count` / `frappe.db.sql` / `frappe.delete_doc` /
     `frappe.db.set_value` nhắm một DocType trong `_SHARED_CORE_DOCTYPES` phải nằm trong
     allowlist đã review. DocType lõi mới bị đụng ⇒ test đỏ, buộc reviewer quyết định.
     Cùng khuôn với `tests/test_workflow_submit_gate.py` đã có.
  2. **Test hành vi (fixture 2 app).** Tạo 1 user AssetCore (có base role) + 1 user "ngoại
     lai" (không base role, mô phỏng CRM) + `Notification Log` cho cả hai + `Email Queue`
     `Not Sent` của app khác. Xác nhận từng fix A1–A7 chỉ chạm phần của AssetCore.
- **Coverage kỳ vọng:** mỗi finding A1–A7 có ≥1 test khẳng định (chỉ chạm của mình) và
  ≥1 test phủ định (**không** chạm của app khác) — đây là phần dễ false-green nhất.
- **DoD:** `bench --site miyano run-tests --app assetcore` xanh, không thêm test đỏ mới.
  Số test đỏ có sẵn (`test_oas_baseline`, `test_oas_d9_tags` — owner IMM-10) giữ nguyên,
  không sửa (LL-BE-64).

---

## 8. Boundaries

**Always (luôn làm)**
- Đi qua `utils/app_scope.py` cho mọi truy vấn lên DocType lõi dùng chung.
- Viết test trước khi sửa (TDD — CLAUDE.md §17), gồm cả nhánh phủ định.
- Backup DB trước bất kỳ thao tác dọn dữ liệu nào.
- Ghi checkpoint session sau mỗi việc đáng kể.

**Ask first (hỏi trước khi làm)**
- A8 (thu hẹp DocPerm lõi) — có thể làm hỏng luồng đính kèm file / giao việc hiện có.
- Bất kỳ thay đổi nào lên `erpnext` / `hrms` / `antmed_crm`.
- Bất kỳ thao tác `DELETE` nào ngoài script purge đã duyệt.

**Never (tuyệt đối không)**
- `bench migrate` (HARD-STOP của USER).
- `git commit` / `push` khi USER chưa gọi `/assetcore-commit`.
- Thêm custom field lên DocType lõi (USER đã chọn phương án không-migrate).
- Sửa core Frappe/ERPNext (CLAUDE.md §19).
- Xoá dữ liệu mà không backup trước.

---

## 9. Success Criteria

| # | Tiêu chí | Cách kiểm chứng |
|---|---|---|
| SC-1 | Tạo user qua app khác (CRM) **không** sinh dòng `WFC Activity Log` | test hành vi + tạo thử user không có role WFC → đếm log không tăng |
| SC-2 | `mark_all_as_read` của AssetCore **không** đổi `read` của Notification Log app khác | test phủ định A2 |
| SC-3 | Chuông AssetCore **không** trả về thông báo có `document_type` ngoài 110 DocType AssetCore | test A3 |
| SC-4 | `_quarantine_stale_queue` **không** chạm Email Queue có `reference_doctype` ngoài AssetCore | test phủ định A1 |
| SC-5 | `grant_base_role()` mặc định chỉ cấp cho user đã thuộc AssetCore, không quét toàn site | test A4 |
| SC-6 | `list_users` / `list_assignable_users` **không** trả user CRM (giữ nguyên hành vi đúng) | test regression |
| SC-7 | `_export_users` chỉ xuất user AssetCore | test A6 |
| SC-8 | Guard tĩnh đỏ khi thêm truy vấn không-scope mới lên DocType lõi | test tự-cắn (self-biting) |
| SC-9 | Dữ liệu ngoại lai đã dọn: `WFC Activity Log` chỉ còn dòng thuộc WorkflowCore; base role AssetCore chỉ còn trên user AssetCore | truy vấn đối chiếu sau khi chạy purge |
| SC-10 | `bench run-tests --app assetcore` không có test đỏ MỚI | chạy thật, dán output |

---

## 10. Quyết định đã chốt (USER, 2026-07-22)

| # | Câu hỏi | Quyết định |
|---|---|---|
| D-1 | Phạm vi app | **Cả hai** — `assetcore` (A1–A7) **+** `workflowcore` (W1) |
| D-2 | Marker sở hữu | **Base role + doctype prefix** — không thêm field, không `bench migrate` |
| D-3 | Dữ liệu đã nhiễm | **Sửa code + dọn dữ liệu luôn** (backup trước) |
| D-4 | A8 (DocPerm lõi) | **Tách vòng sau.** Vòng này CHỈ ghi nhận rủi ro, KHÔNG sửa `setup_core_permissions.py` — thu hẹp quyền `File`/`Contact`/`Communication` dễ phá luồng đính kèm ảnh PM/sửa chữa, cần UAT riêng. → carry vào backlog. |
| D-5 | Purge `WFC Activity Log` | **Xoá hết 35.465 dòng `target_doctype = "User"`.** Sau purge chỉ còn 6 dòng nhắm DocType của WorkflowCore. Chấp nhận mất audit đăng nhập lịch sử của user WorkflowCore thật. |
| D-6 | `login_success` / `logout` (WorkflowCore) | **Chỉ log user WorkflowCore** (giữ role `WFC *`). Audit đăng nhập cấp-site đã có `Activity Log` của Frappe lõi. |

### Backlog carry sang vòng sau (KHÔNG làm vòng này)

- **A8 — DocPerm lõi phạm vi toàn site.** `setup/setup_core_permissions.py:67-73,109-121` cấp
  R/W/C/D cho role AssetCore trên `File`/`ToDo`/`Comment`/`Communication`/`Contact`/`Address`/
  `Notification Log`. Người dùng AssetCore vẫn đọc/sửa được dữ liệu lõi của CRM/HRMS qua desk/API.
  Cần thiết kế `permission_query_conditions` cho các DocType lõi này + UAT luồng đính kèm
  ảnh PM (IMM-08) / sửa chữa (IMM-09) trước khi siết.
- **Nhiễu hiệu năng doc_events.** `hooks.py:208-228` (`User` / `Has Role` / `Custom DocPerm`)
  vẫn kích hoạt cho mọi mutation user ngoại lai rồi early-return. Không ghi dữ liệu sai
  ⇒ chấp nhận được, nhưng có thể thêm guard sớm nếu site khách hàng nhiều app hơn nữa.
