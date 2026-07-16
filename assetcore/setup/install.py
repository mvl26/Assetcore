# Copyright (c) 2026, AssetCore Team
"""
IMM-00 Setup — tạo Custom Fields bổ sung cho Frappe User DocType.

Chạy sau khi install/migrate:
  bench --site <site> migrate
  (after_install và after_migrate hooks tự gọi hàm này)
"""
from __future__ import annotations

import frappe

# ── Custom fields cần thêm vào tabUser ────────────────────────────────────────
_USER_CUSTOM_FIELDS: list[dict] = [
    {
        "fieldname": "imm_section",
        "fieldtype": "Section Break",
        "label": "IMM AssetCore",
        "insert_after": "enabled",
    },
    {
        "fieldname": "imm_approval_status",
        "fieldtype": "Select",
        # Empty option đầu = "chưa thuộc luồng duyệt IMM" (vd: Administrator, user
        # ERPNext gốc). KHÔNG để default "Pending": default cũ khiến MỌI user tạo
        # ngoài luồng self-signup (test fixture, desk, bench, import) bị gán Pending
        # dù enabled=1 → badge "Chờ duyệt" giả, không có gate thật phía sau.
        # Invariant: Pending ⟺ enabled=0 (chờ admin). enabled=1 ⇒ Approved/empty.
        "options": "\nPending\nApproved\nRejected",
        "default": "",
        "insert_after": "imm_section",
        "in_list_view": 0,
    },
    {
        "fieldname": "imm_approved_by",
        "fieldtype": "Link",
        "label": "Duyệt bởi",
        "options": "User",
        "insert_after": "imm_approval_status",
        "read_only": 1,
    },
    {
        "fieldname": "imm_approved_at",
        "fieldtype": "Datetime",
        "label": "Thời điểm duyệt",
        "insert_after": "imm_approved_by",
        "read_only": 1,
    },
    {
        "fieldname": "imm_rejection_reason",
        "fieldtype": "Small Text",
        "label": "Lý do từ chối",
        "insert_after": "imm_approved_at",
    },
    {
        "fieldname": "ac_department",
        "fieldtype": "Link",
        "label": "Khoa / Phòng (AssetCore)",
        "options": "AC Department",
        "insert_after": "imm_rejection_reason",
    },
]


# Fieldtype trỏ tới DocType khác — cần target DocType tồn tại trước khi tạo field.
_LINK_LIKE_FIELDTYPES = {"Link", "Table", "Table MultiSelect"}


def _ensure_custom_field(dt: str, fieldname: str, definition: dict) -> None:
    """Tạo Custom Field nếu chưa tồn tại.

    Bỏ qua AN TOÀN nếu field là Link/Table trỏ tới DocType **chưa tồn tại** — tránh
    `WrongOptionsDoctypeLinkError` chặn cả `install-app` khi `after_install` chạy
    trước lúc DocType đích (vd ``AC Department``) sync xong trên fresh site / cloud.
    Field sẽ được tạo ở lần `after_migrate` kế tiếp khi DocType đích đã có (cả hai
    hook đều gọi `create_user_custom_fields`, nên idempotent + self-heal).
    """
    existing = frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname})
    if existing:
        return
    options = definition.get("options")
    if (
        definition.get("fieldtype") in _LINK_LIKE_FIELDTYPES
        and options
        and not frappe.db.exists("DocType", options)
    ):
        print(
            f"[AssetCore] Bỏ qua Custom Field {dt}.{fieldname}: DocType đích "
            f"{options!r} chưa tồn tại (sẽ tạo lại ở migrate kế tiếp)."
        )
        return
    cf = frappe.new_doc("Custom Field")
    cf.dt = dt
    cf.fieldname = fieldname
    for k, v in definition.items():
        if k != "fieldname":
            cf.set(k, v)
    # Gắn module AssetCore → Frappe track field này theo app, giúp uninstall dọn
    # sạch (KHÔNG để orphan trên doctype core như User). before_uninstall vẫn xoá
    # tường minh để phủ cả field cũ đã tạo với module=None.
    cf.module = "AssetCore"
    cf.flags.ignore_permissions = True
    cf.insert(ignore_if_duplicate=True)


def _drop_orphan_user_link_fields() -> None:
    """Gỡ Custom Field Link/Table trên User trỏ tới DocType KHÔNG còn tồn tại.

    Triệu chứng: mở form User trên desk báo
    `Field ac_department is referring to non-existing doctype AC Department`
    (frappe/desk/form/meta.py::add_search_fields → get_meta(options) →
    DoesNotExistError → frappe.throw). Xảy ra khi DocType đích (vd `AC Department`)
    chưa/không sync (bug app_modules cache cũ trên cloud) NHƯNG Custom Field đã tồn
    tại từ lần cài trước → orphan, làm crash desk.

    Gỡ orphan để desk không vỡ. Field idempotent sẽ được tạo lại ở
    `create_user_custom_fields` lần migrate kế tiếp khi DocType đích đã có. Chỉ gỡ
    khi target THỰC SỰ thiếu (broken state) → no-op trên site khỏe; an toàn vì field
    vô dụng nếu thiếu doctype đích.
    """
    for field_def in _USER_CUSTOM_FIELDS:
        if field_def.get("fieldtype") not in _LINK_LIKE_FIELDTYPES:
            continue
        options = field_def.get("options")
        if not options or frappe.db.exists("DocType", options):
            continue
        cf = frappe.db.exists(
            "Custom Field", {"dt": "User", "fieldname": field_def["fieldname"]}
        )
        if cf:
            frappe.delete_doc(
                "Custom Field", cf, ignore_permissions=True, force=True
            )
            print(
                f"[AssetCore] Gỡ orphan Custom Field User.{field_def['fieldname']} "
                f"(DocType đích {options!r} chưa tồn tại — desk khỏi crash; sẽ tạo lại "
                f"khi doctype đích đã sync)."
            )


def create_user_custom_fields() -> None:
    """Tạo toàn bộ custom fields cho User nếu chưa có."""
    # Dọn field orphan TRƯỚC: tránh `Missing DocType` crash khi target chưa sync.
    _drop_orphan_user_link_fields()
    for field_def in _USER_CUSTOM_FIELDS:
        fieldname = field_def["fieldname"]
        if fieldname.endswith("_section"):
            # Section Break không cần check column
            _ensure_custom_field("User", fieldname, field_def)
        else:
            if not frappe.db.has_column("User", fieldname):
                _ensure_custom_field("User", fieldname, field_def)

    _reconcile_approval_status_field()
    frappe.db.commit()


def _reconcile_approval_status_field() -> None:
    """Idempotent: gỡ default 'Pending' lệch trên Custom Field đã tồn tại.

    Site cũ đã insert Custom Field với default='Pending'. Đổi định nghĩa trong
    _USER_CUSTOM_FIELDS không tự cập nhật record đã có (ensure chỉ insert-if-missing).
    Hàm này ép default về '' và options về '\\nPending\\nApproved\\nRejected' để mọi
    user mới tạo ngoài luồng IMM không bị gán 'Pending' giả.
    """
    cf = frappe.db.exists("Custom Field", {"dt": "User", "fieldname": "imm_approval_status"})
    if not cf:
        return
    current_default = frappe.db.get_value("Custom Field", cf, "default")
    if current_default == "Pending":
        frappe.db.set_value(
            "Custom Field", cf,
            {"default": "", "options": "\nPending\nApproved\nRejected"},
        )


def before_install() -> None:
    """Rebuild module map TRƯỚC khi Frappe sync doctype — fix fresh-install cloud.

    Triệu chứng đã gặp (cloud, bench đang chạy): `bench install-app assetcore` báo
    `Workflow sync error … DocType <X> not found` cho MỌI doctype + `_seed_uoms` lỗi
    `No module named 'frappe.core.doctype.ac_uom'`.

    Nguyên nhân: trên bench cloud có web worker + scheduler sống, Redis cache key
    `app_modules`/`all_apps` được nạp TRƯỚC khi assetcore thêm vào bench → cache cũ
    KHÔNG có "assetcore". Khi tiến trình `install-app` boot, `setup_module_map()` đọc
    cache cũ (truthy → KHÔNG rebuild) → `frappe.local.app_modules` thiếu key
    "assetcore". `install_app()` gọi `frappe.clear_cache()` (xoá Redis key) NHƯNG
    KHÔNG reset `local.app_modules` in-memory → vẫn cũ. `sync_for("assetcore")` lặp
    `frappe.local.app_modules.get("assetcore") or []` → rỗng → 0/108 doctype được
    sync → `after_install` (_sync_workflows/_seed_uoms) fail vì doctype chưa tồn tại
    (`get_controller("AC UOM")` fallback `["Core", …]` → import `frappe.core.…`).

    `install_app()` chạy `before_install` NGAY TRƯỚC `add_module_defs` + `sync_for`,
    nên bust cache app-list/module-map ở đây + rebuild khiến `sync_for` thấy
    assetcore và sync đủ doctype. Idempotent + no-op trên site đã đúng map (local dev).
    Best-effort: lỗi rebuild KHÔNG được chặn install.
    """
    try:
        _rebuild_module_map()
        mods = (frappe.local.app_modules or {}).get("assetcore") or []
        print(f"[AssetCore] before_install: module map rebuilt — assetcore modules={mods}")
    except Exception as e:  # noqa: BLE001
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore before_install: module map refresh failed",
        )
        print(f"[AssetCore] before_install warning: {e}")


def _rebuild_module_map() -> None:
    """Bust cache app-list/module-map rồi rebuild để Frappe thấy module 'assetcore'.

    Xem docstring `before_install` cho bối cảnh: trên bench cloud đang chạy, Redis
    cache `app_modules` cũ có thể thiếu "assetcore" → mọi cơ chế dựa vào
    `frappe.local.app_modules` (sync_for, get_module_app) bỏ sót doctype của app.
    """
    frappe.cache.delete_value([
        "app_modules",
        "installed_app_modules",
        "all_apps",
        "installed_apps",
        "module_app",
        "module_installed_app",
    ])
    frappe.setup_module_map(include_all_apps=True)


def _ensure_app_doctypes_synced() -> None:
    """Self-heal: bảo đảm doctype của AssetCore đã được sync TRƯỚC các bước phụ thuộc.

    `install_app()` của Frappe gọi `sync_for("assetcore")` trước `after_install`,
    nhưng trên bench cloud đang chạy, `sync_for` có thể lặp 0 module (app_modules
    cache cũ thiếu "assetcore") → 0/108 doctype được tạo → `_sync_workflows`,
    `_seed_uoms` và cả `sync_fixtures` (chạy SAU after_install) đều fail
    'DocType ... not found'. Hook `before_install` đã rebuild map để sync_for native
    chạy đúng; hàm này là lớp phòng vệ thứ 2: nếu doctype VẪN thiếu khi after_install
    chạy thì rebuild map + `sync_for(force=True)` thủ công ngay tại đây.

    Idempotent: nếu doctype mốc ("AC Asset") đã tồn tại → no-op nhanh, không sync lại.
    Vì hàm chạy ở ĐẦU after_install (trước workflow/UOM) và after_install chạy TRƯỚC
    sync_fixtures trong install_app, sửa được ở đây = sạch toàn bộ chuỗi cài.
    """
    if frappe.db.exists("DocType", "AC Asset"):
        return
    try:
        from frappe.model.sync import sync_for

        _rebuild_module_map()
        mods = (frappe.local.app_modules or {}).get("assetcore") or []
        if not mods:
            print(
                "[AssetCore] after_install self-heal: app_modules vẫn thiếu 'assetcore' "
                "sau rebuild — kiểm tra modules.txt/apps.txt + file doctype trên server."
            )
            return
        sync_for("assetcore", force=True, reset_permissions=True)
        frappe.db.commit()
        synced = frappe.db.exists("DocType", "AC Asset")
        print(
            f"[AssetCore] after_install self-heal: sync_for('assetcore') xong "
            f"(modules={mods}, AC Asset tồn tại={synced!r})."
        )
    except Exception as e:  # noqa: BLE001 — không chặn install; bước sau sẽ báo cụ thể
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore after_install: ensure doctypes synced failed",
        )
        print(f"[AssetCore] after_install doctype self-heal warning: {e}")


def after_install() -> None:
    _ensure_app_doctypes_synced()
    _sync_workflows()
    _seed_uoms()
    create_user_custom_fields()
    _apply_erpnext_asset_custom_fields()
    _apply_rbac_matrix()
    _seed_role_profiles()
    _seed_module_profiles()
    _apply_core_permissions()
    _build_frontend(force=True)


def before_migrate() -> None:
    """Rebuild module map + xóa Has Role orphan rows trước khi migrate sync schema.

    `before_migrate` chạy TRƯỚC `sync_all()` (đồng bộ doctype) trong `bench migrate`.
    Rebuild map ở đây bảo đảm đường RECOVERY (`bench migrate` chữa site đã lỡ cài
    hỏng vì app_modules cache cũ) cũng sync đủ doctype — cùng lý do với `before_install`.
    `_clear_role_profile_has_role_rows`: ngăn lỗi 'already has the role' khi Frappe
    delete+reinsert Role Profile fixture."""
    try:
        _rebuild_module_map()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore before_migrate: module map refresh failed",
        )
    _clear_role_profile_has_role_rows()


def _asset_custom_fields_path() -> str:
    """Đường dẫn JSON Custom Field cho ERPNext Asset.

    LƯU Ý path: file ở `apps/assetcore/assetcore/config/...` (dưới Python PACKAGE),
    KHÔNG ở dưới module folder. `get_app_path('assetcore')` đã = `.../assetcore/assetcore`
    nên CHỈ thêm 'config' — KHÔNG thêm 'assetcore' nữa (bug cũ thêm dư → path không tồn
    tại → _apply_erpnext_asset_custom_fields silent no-op trên site ERPNext).
    """
    return frappe.get_app_path(
        "assetcore", "config", "erpnext_integration", "asset_custom_fields.json"
    )


def _load_asset_custom_field_names() -> list[str]:
    """Đọc fieldname của Custom Field AssetCore đặt lên ERPNext Asset (từ JSON nguồn)."""
    import json as _json
    import os

    json_path = _asset_custom_fields_path()
    if not os.path.exists(json_path):
        return []
    with open(json_path) as f:
        docs = _json.load(f)
    return [d["fieldname"] for d in docs if d.get("fieldname")]


def _foreign_custom_field_specs() -> list[tuple[str, str]]:
    """(dt, fieldname) cho mọi Custom Field AssetCore đặt lên doctype KHÔNG thuộc app.

    Gồm: User (Frappe core — 6 field IMM/ac_department) + Asset (ERPNext — custom_imm_*).
    Dùng để gỡ sạch khi uninstall (Frappe không tự dọn field trên doctype ngoài app).
    """
    specs: list[tuple[str, str]] = [
        ("User", fdef["fieldname"]) for fdef in _USER_CUSTOM_FIELDS
    ]
    try:
        specs += [("Asset", fn) for fn in _load_asset_custom_field_names()]
    except Exception:  # noqa: BLE001 — không có ERPNext / JSON lỗi → bỏ qua
        pass
    return specs


def _remove_foreign_customizations() -> int:
    """Xóa Custom Field AssetCore khỏi doctype core/ERPNext (User, Asset). Trả số đã xóa."""
    removed = 0
    for dt, fieldname in _foreign_custom_field_specs():
        cf = frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname})
        if cf:
            frappe.delete_doc(
                "Custom Field", cf, ignore_permissions=True, force=True
            )
            removed += 1
    # Property Setter AssetCore trên doctype foreign (hiện không có, nhưng quét cho chắc).
    for ps in frappe.get_all(
        "Property Setter", filters={"module": "AssetCore"}, pluck="name"
    ):
        frappe.delete_doc("Property Setter", ps, ignore_permissions=True, force=True)
        removed += 1
    if removed:
        frappe.db.commit()
    return removed


def before_uninstall() -> None:
    """Dọn modification AssetCore lên doctype CORE/ERPNext TRƯỚC khi gỡ app.

    AssetCore thêm Custom Field vào doctype KHÔNG thuộc app (User của Frappe, Asset
    của ERPNext). `uninstall-app` của Frappe chỉ drop doctype thuộc module app → các
    field này bị bỏ lại (orphan). Hậu quả: mở form User/Asset sau khi gỡ báo
    `Field <x> is referring to non-existing doctype <Y>` (frappe/desk/form/meta.py
    add_search_fields → get_meta → DoesNotExist). Hàm này xóa tường minh các field đó
    (phủ cả field cũ tạo với module=None). Idempotent + best-effort: lỗi KHÔNG chặn gỡ.
    """
    try:
        n = _remove_foreign_customizations()
        print(
            f"[AssetCore] before_uninstall: gỡ {n} customization khỏi doctype core/ERPNext "
            f"(User/Asset Custom Field + Property Setter)."
        )
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore before_uninstall: remove foreign customizations failed",
        )


def after_migrate() -> None:
    _reconcile_asset_repair_override()
    _sync_workflows()
    _seed_uoms()
    create_user_custom_fields()
    _apply_erpnext_asset_custom_fields()
    _apply_rbac_matrix()
    _seed_role_profiles()
    _seed_module_profiles()
    _apply_core_permissions()
    _install_notifications()
    _bust_capability_cache()
    _build_frontend(force=False)


def _reconcile_asset_repair_override() -> None:
    """ROOT-CAUSE FIX — core-doctype name collision (Asset Repair).

    AssetCore ships its own "Asset Repair" doctype (module=AssetCore, uses
    ``asset_ref`` + AssetCore controller) that overrides the core ERPNext
    "Asset Repair" (module=Assets, core ``asset`` field + ERPNext controller).

    ERPNext migrates AFTER assetcore in installed_apps
    (``[frappe, assetcore, …, erpnext, …]``), so ``sync_all()`` re-syncs
    ERPNext's version LAST every ``bench migrate`` and clobbers the override.
    Symptom: ``DoesNotExistError 'Asset None not found'`` — ERPNext's
    ``AssetRepair.validate()`` reads core ``asset`` (always None; AssetCore
    only sets ``asset_ref``). A plain ``bench migrate`` therefore does NOT
    fix this — it re-drifts.

    ``after_migrate`` runs AFTER ``sync_all()``, so re-asserting AssetCore's
    JSON here makes the override deterministically win regardless of app
    order. Idempotent (guarded by current module) + self-healing.

    NOTE for [BA] — durable fix is out of scope here: the override of a core
    ERPNext doctype name violates CLAUDE.md §5/§19 (don't modify core) and is
    inherently fragile. The lasting fix is to rename this doctype to a
    non-colliding AssetCore name (e.g. "AC Asset Repair"), which is an
    architecture change spanning data + code + FE + OpenAPI and needs a
    Core Doc spec.
    """
    try:
        current = frappe.db.get_value("DocType", "Asset Repair", "module")
        if current == "AssetCore":
            return
        frappe.reload_doc("assetcore", "doctype", "asset_repair", force=True)
        frappe.clear_cache(doctype="Asset Repair")
        print(
            f"[AssetCore] Asset Repair override re-asserted "
            f"(was module={current!r} → AssetCore)"
        )
    except Exception as e:  # noqa: BLE001 — không chặn migrate
        frappe.log_error(
            f"_reconcile_asset_repair_override failed: {e}",
            "AssetCore after_migrate",
        )


def _bust_capability_cache() -> None:
    """BE-2 (USER REWORK IMM-14): sau khi DocPerm/Role/Role Profile da sync
    (rbac matrix + role profiles + core perms), bust toan bo cache Redis
    `ac_caps::*` → cap moi (vd decommission.*) toi FE NGAY lan goi
    get_capabilities dau tien sau deploy, KHONG doi TTL 1h.

    Idempotent + best-effort: loi cache KHONG duoc chan migrate."""
    try:
        from assetcore.services.shared import rbac

        rbac.invalidate_capabilities()
        print(f"[AssetCore] ac_caps::* busted (cap-set {rbac.CAP_SET_VERSION})")
    except Exception as e:  # noqa: BLE001
        frappe.log_error(
            f"_bust_capability_cache failed: {e}", "AssetCore after_migrate"
        )


def _seed_uoms() -> None:
    """Seed AC UOM master data (idempotent).

    AC Asset.uom mặc định là "Cái"; nếu master UOM chưa tồn tại thì mọi insert
    AC Asset sẽ throw LinkValidationError. Seed ở đây để fresh site / site drift
    luôn có bộ UOM chuẩn — không phụ thuộc one-time patch v3_0.
    """
    try:
        from assetcore.services.uom import seed_ac_uoms

        created = seed_ac_uoms()
        if created:
            print(f"[AssetCore] AC UOM seeded: {created}")
    except Exception as e:  # noqa: BLE001 — không chặn migrate vì UOM seed lỗi
        print(f"[AssetCore] AC UOM seed error: {e}")


def _import_workflow_file(fpath: str) -> set[str]:
    """Import một workflow JSON, trả về tập states tìm thấy."""
    import json as _json
    from frappe.modules.import_file import import_doc as _import_doc

    with open(fpath) as f:
        docdict = _json.load(f)
    _import_doc(docdict, path=fpath)
    states = {row["state"] for row in (docdict.get("states") or []) if row.get("state")}
    print(f"[AssetCore] Workflow synced: {docdict.get('workflow_name') or fpath}")
    return states


def _ensure_workflow_state(state_name: str) -> None:
    if frappe.db.exists("Workflow State", state_name):
        return
    try:
        ws = frappe.new_doc("Workflow State")
        ws.workflow_state_name = state_name
        ws.flags.ignore_permissions = True
        ws.insert(ignore_if_duplicate=True)
    except Exception as e:
        print(f"[AssetCore] Workflow State create error ({state_name!r}): {e}")


def _sync_workflows() -> None:
    """Import all AssetCore workflow JSON files and ensure Workflow State master records exist."""
    import os

    workflow_dir = frappe.get_app_path("assetcore", "assetcore", "workflow")
    if not os.path.exists(workflow_dir):
        return

    all_states: set[str] = set()
    for fname in sorted(os.listdir(workflow_dir)):
        if not fname.endswith(".json"):
            continue
        try:
            all_states |= _import_workflow_file(os.path.join(workflow_dir, fname))
        except Exception as e:
            print(f"[AssetCore] Workflow sync error ({fname}): {e}")

    for state_name in sorted(all_states):
        _ensure_workflow_state(state_name)

    frappe.db.commit()


def _apply_erpnext_asset_custom_fields() -> None:
    """Áp dụng custom fields HTM lên ERPNext Asset — chỉ khi ERPNext đã cài."""
    import json as _json
    import os
    from frappe.modules.import_file import import_doc as _import_doc

    if not frappe.db.exists("DocType", "Asset"):
        return

    json_path = _asset_custom_fields_path()
    if not os.path.exists(json_path):
        return

    try:
        with open(json_path) as f:
            docs = _json.load(f)
        for doc in docs:
            # Gắn module AssetCore (JSON gốc để None) → field được track theo app để
            # uninstall dọn sạch khỏi doctype ERPNext Asset, không để orphan.
            doc.setdefault("module", "AssetCore")
            if not doc.get("module"):
                doc["module"] = "AssetCore"
            _import_doc(doc, path=json_path)
        frappe.db.commit()
        print(f"[AssetCore] ERPNext Asset custom fields applied ({len(docs)} fields).")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "AssetCore: apply ERPNext Asset custom fields failed")
        print(f"[AssetCore] ERPNext Asset custom fields warning: {e}")


def _install_notifications() -> None:
    """Sync 7 IMM Notification rules — idempotent."""
    try:
        from assetcore.notifications.setup import install_notifications
        result = install_notifications()
        print(f"[AssetCore] Notifications: {result['count']} rule(s) đã sync.")
    except Exception as e:
        print(f"[AssetCore] Notification install failed: {e}")


def _apply_rbac_matrix() -> None:
    """Cleanup legacy DocPerm/Has Role. Import locally để tránh circular."""
    try:
        from assetcore.setup.setup_permissions import run as apply_permissions
        apply_permissions()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore RBAC: setup_permissions.run failed",
        )


def _seed_role_profiles() -> None:
    """Tạo 8 Role Profile AssetCore (bộ role chọn sẵn) + cleanup legacy."""
    try:
        from assetcore.setup.setup_role_profiles import run as seed
        seed()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore Role Profiles: setup_role_profiles.run failed",
        )


def _seed_module_profiles() -> None:
    """Tạo Module Profile kiểm soát sidebar visibility cho từng nhóm user."""
    try:
        from assetcore.setup.setup_module_profiles import run as seed
        seed()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore Module Profiles: setup_module_profiles.run failed",
        )


def _apply_core_permissions() -> None:
    """Custom DocPerm cho Frappe core DocType — IMM role tự đủ quyền dùng desk."""
    try:
        from assetcore.setup.setup_core_permissions import run as apply_core
        apply_core()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore Core Permissions: setup_core_permissions.run failed",
        )


def _build_frontend(force: bool = False) -> None:
    """Wrapper — build Vue SPA, không raise exception để không block install."""
    try:
        from assetcore.setup.setup_frontend import build_frontend
        build_frontend(force=force)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AssetCore FE build failed")


def _clear_role_profile_has_role_rows() -> None:
    """Xóa Has Role rows thuộc AssetCore Role Profiles khỏi DB.

    Frappe fixture import (delete_old_doc → frappe.delete_doc with for_reload=True)
    không xóa được child Has Role rows khi chạy migrate. Nếu after_migrate đã chạy
    lần trước (thêm rows qua setup_role_profiles.run), lần migrate kế tiếp sẽ fail
    với ValidationError 'already has the role'. Hook before_migrate gọi hàm này để
    làm sạch trước khi fixture sync bắt đầu.
    """
    try:
        from assetcore.setup.role_profile_catalog import PROFILE_NAMES
        # Dọn Has Role rows của 8 Role Profile hiện hành (tên VI) + legacy
        # "AssetCore — %" còn sót, trước khi fixture sync re-insert.
        deleted = frappe.db.delete(
            "Has Role",
            {
                "parenttype": "Role Profile",
                "parent": ["in", PROFILE_NAMES],
            },
        )
        deleted += frappe.db.delete(
            "Has Role",
            {"parenttype": "Role Profile", "parent": ["like", "AssetCore — %"]},
        )
        if deleted:
            frappe.db.commit()
            print(f"[AssetCore] before_migrate: cleared {deleted} Has Role rows (Role Profile).")
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore before_migrate: _clear_role_profile_has_role_rows failed",
        )
