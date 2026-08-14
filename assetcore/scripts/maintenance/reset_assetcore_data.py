# Copyright (c) 2026, AssetCore Team
"""reset_assetcore_data.py — đưa dữ liệu AssetCore về trạng thái VỪA CÀI APP.

Khác ``purge_test_data`` (chỉ xoá bản ghi trong DocType của app): script này dọn
**cả phần cặn nằm ở DocType lõi Frappe** do AssetCore sinh ra (bình luận, phiên
bản, thông báo, workflow action, tệp đính kèm, việc cần làm), **đặt lại bộ đếm
mã** để số chạy lại từ 1, rồi **dựng lại cấu hình mà ``after_install`` tạo**
(workflow, UOM, ma trận RBAC, Role Profile, DocPerm, fixtures).

⚠️ Site này DÙNG CHUNG với erpnext + hrms. Script TUYỆT ĐỐI không truncate bảng
lõi; mọi thao tác trên bảng lõi đều lọc theo đúng danh sách DocType của AssetCore.

⚠️ ``bench execute --kwargs`` chạy qua ``eval()`` của PYTHON, KHÔNG phải JSON:
   phải viết ``True``/``False``/``None`` (viết hoa), ``true`` sẽ ném
   ``NameError: name 'true' is not defined``.

Chạy:
    # 1) Xem trước — KHÔNG ghi gì:
    bench --site miyano execute assetcore.scripts.maintenance.reset_assetcore_data.preview

    # 2) Xoá thật (phải truyền đúng token):
    bench --site miyano execute assetcore.scripts.maintenance.reset_assetcore_data.run \
          --kwargs "{'confirm': 'XOA-SACH-ASSETCORE'}"

    # 3) Sạch hoàn toàn nhưng giữ vài tài khoản thật:
    bench --site miyano execute assetcore.scripts.maintenance.reset_assetcore_data.run \
          --kwargs "{'confirm': 'XOA-SACH-ASSETCORE', 'wipe_users': True, 'wipe_logs': True,
                     'keep_users': ['Administrator', 'Guest', 'nguoi.that@vidu.vn']}"

    # Tuỳ chọn:
    #    wipe_users=True  → xoá luôn User do AssetCore tạo (giữ keep_users + ai có hồ sơ Employee)
    #    wipe_logs=True   → xoá Email Queue / Error Log / Scheduled Job Log / Activity Log (TOÀN SITE)
    #    reseed=False     → không dựng lại cấu hình after_install

Việc script KHÔNG làm (cố ý):
  - KHÔNG đụng schema: DocType / Custom Field / Workflow definition / Role vẫn nguyên.
  - KHÔNG chạy ``bench migrate`` (HARD-STOP của dự án).
  - KHÔNG build frontend (``after_install`` có ``_build_frontend`` — nặng và ghi
    đè assets live; chạy tay khi cần).
  - KHÔNG xoá tệp vật lý trong ``public/files`` (chỉ xoá bản ghi ``File``).
"""
from __future__ import annotations

import frappe

CONFIRM_TOKEN = "XOA-SACH-ASSETCORE"

#: User không bao giờ xoá, kể cả khi wipe_users=True.
DEFAULT_KEEP_USERS = ("Administrator", "Guest")

#: Bảng lõi Frappe + cột trỏ về DocType — dọn theo PHẠM VI DocType của AssetCore.
#: (doctype lõi, cột chứa tên DocType được tham chiếu)
_CORE_RESIDUE: tuple[tuple[str, str], ...] = (
    ("Comment", "reference_doctype"),
    ("Version", "ref_doctype"),
    ("Notification Log", "document_type"),
    ("ToDo", "reference_type"),
    ("Workflow Action", "reference_doctype"),
    ("Tag Link", "document_type"),
    ("File", "attached_to_doctype"),
    ("Activity Log", "reference_doctype"),
    ("Document Follow", "ref_doctype"),
    ("Assignment Rule", "document_type"),
)

#: Log vận hành TOÀN SITE — chỉ đụng khi wipe_logs=True (không phân biệt app nổi).
_SITE_LOGS: tuple[str, ...] = (
    "Email Queue Recipient", "Email Queue", "Error Log",
    "Scheduled Job Log", "Activity Log",
)


# ──────────────────────────────────────────────────────────────────────────
# Khám phá phạm vi
# ──────────────────────────────────────────────────────────────────────────
def _app_modules() -> list[str]:
    return frappe.get_all("Module Def", filters={"app_name": "assetcore"}, pluck="name")


def _app_doctypes() -> tuple[list[str], list[str]]:
    """(child_tables, parents) của app — con trước cha để không bỏ lại dòng mồ côi."""
    modules = _app_modules()
    if not modules:
        return [], []
    rows = frappe.get_all(
        "DocType",
        filters={"module": ["in", modules], "issingle": 0},
        fields=["name", "istable"],
        order_by="name asc",
    )
    return ([r["name"] for r in rows if r["istable"]],
            [r["name"] for r in rows if not r["istable"]])


def _count(doctype: str, where: str = "", args: tuple = ()) -> int:
    try:
        sql = f"SELECT COUNT(*) FROM `tab{doctype}`" + (f" WHERE {where}" if where else "")
        return frappe.db.sql(sql, args)[0][0]
    except Exception:
        return 0


def _in_clause(values: list[str]) -> tuple[str, tuple]:
    placeholders = ", ".join(["%s"] * len(values))
    return placeholders, tuple(values)


def _series_prefixes(parents: list[str]) -> list[str]:
    """Tiền tố mã CHỈ thuộc AssetCore — suy từ tên bản ghi ĐANG CÓ.

    Phải gọi TRƯỚC khi xoá. Cách này an toàn hơn đoán từ ``autoname``: bảng
    ``tabSeries`` dùng chung với erpnext/hrms (ACC-*, AM-*, AntMed-*…), xoá nhầm
    là làm hỏng đánh số của app khác.
    """
    all_series = frappe.db.sql_list("SELECT name FROM `tabSeries`")
    hit: set[str] = set()
    for dt in parents:
        try:
            names = frappe.db.sql_list(f"SELECT name FROM `tab{dt}` LIMIT 50")
        except Exception:
            continue
        for nm in names:
            for s in all_series:
                if s and nm.startswith(s):
                    hit.add(s)

    # Loại tiền tố CÓ THỂ dùng chung với app khác. Trên site này AssetCore ở cạnh
    # erpnext + hrms; reset bộ đếm của app khác ⇒ họ cấp lại mã ĐÃ TỒN TẠI ⇒ lỗi
    # trùng khoá chính về sau. Đối chiếu với phần literal (trước dấu '.') trong
    # autoname của MỌI doctype không thuộc AssetCore — nghi ngờ thì GIỮ, đừng xoá.
    foreign_heads = set()
    for autoname in frappe.db.sql_list(
        "SELECT DISTINCT autoname FROM tabDocType WHERE autoname IS NOT NULL AND autoname<>'' "
        "AND module NOT IN (SELECT name FROM `tabModule Def` WHERE app_name='assetcore')"
    ):
        head = str(autoname).split(".")[0].replace("format:", "").strip()
        if head and not head.endswith(":"):
            foreign_heads.add(head)

    safe, skipped = set(), set()
    for s in hit:
        if any(s.startswith(h) or h.startswith(s) for h in foreign_heads):
            skipped.add(s)
        else:
            safe.add(s)
    if skipped:
        print(f"[series] BỎ QUA {len(skipped)} tiền tố dùng chung với app khác: "
              f"{sorted(skipped)}")
    return sorted(safe)


def _wipeable_users(keep_users: tuple[str, ...]) -> list[str]:
    """User sẽ bị xoá khi wipe_users=True — TRỪ keep-list và người có hồ sơ hrms.

    Bảo vệ Employee: site dùng chung, xoá user gắn chấm công/nhân sự là mất dữ
    liệu của app khác chứ không phải rác AssetCore.
    """
    keep = set(keep_users)
    if frappe.db.table_exists("Employee"):
        keep |= set(frappe.db.sql_list(
            "SELECT user_id FROM `tabEmployee` WHERE user_id IS NOT NULL AND user_id<>''"
        ))
    return [u for u in frappe.db.sql_list("SELECT name FROM `tabUser`") if u not in keep]


# ──────────────────────────────────────────────────────────────────────────
# Báo cáo
# ──────────────────────────────────────────────────────────────────────────
def _report(wipe_users: bool, wipe_logs: bool, keep_users: tuple[str, ...]) -> dict:
    children, parents = _app_doctypes()
    dt_all = children + parents

    biz = {dt: _count(dt) for dt in parents}
    biz = {k: v for k, v in sorted(biz.items(), key=lambda x: -x[1]) if v}
    child_rows = sum(_count(dt) for dt in children)

    ph, args = _in_clause(dt_all)
    residue = {}
    for core_dt, col in _CORE_RESIDUE:
        if not frappe.db.table_exists(core_dt) or not frappe.db.has_column(core_dt, col):
            continue
        n = _count(core_dt, f"`{col}` IN ({ph})", args)
        if n:
            residue[f"{core_dt}.{col}"] = n

    out = {
        "doctype_cua_app": {"cha": len(parents), "bang_con": len(children)},
        "ban_ghi_nghiep_vu": biz,
        "tong_ban_ghi_cha": sum(biz.values()),
        "tong_dong_bang_con": child_rows,
        "can_o_bang_loi": residue,
        "tong_can": sum(residue.values()),
        "bo_dem_ma_se_reset": _series_prefixes(parents),
    }
    if wipe_users:
        victims = _wipeable_users(keep_users)
        out["user_se_xoa"] = {"so_luong": len(victims), "vi_du": victims[:15]}
        out["user_giu_lai"] = list(keep_users)
    if wipe_logs:
        out["log_toan_site_se_xoa"] = {dt: _count(dt) for dt in _SITE_LOGS
                                       if frappe.db.table_exists(dt)}
    return out


def preview(wipe_users: bool = False, wipe_logs: bool = False) -> None:
    """Xem trước — KHÔNG ghi gì."""
    frappe.set_user("Administrator")
    rep = _report(bool(wipe_users), bool(wipe_logs), DEFAULT_KEEP_USERS)
    print(frappe.as_json(rep))
    print("\n>> Chưa thay đổi gì. Chạy thật:")
    print(f'   bench --site {frappe.local.site} execute '
          f'assetcore.scripts.maintenance.reset_assetcore_data.run '
          f'--kwargs \'{{"confirm": "{CONFIRM_TOKEN}"}}\'')


# ──────────────────────────────────────────────────────────────────────────
# Thi hành
# ──────────────────────────────────────────────────────────────────────────
def _truncate_app_tables(children: list[str], parents: list[str]) -> dict:
    """Xoá bằng SQL thô — CỐ Ý bỏ qua ``on_trash``.

    Reset toàn bộ thì mọi chốt chặn xoá (WR-03 của AC Asset, on_trash append-only
    của IMM Audit Trail / Asset Lifecycle Event) đều phải đi vòng; đi qua ORM sẽ
    chặn đúng những bảng cần dọn nhất.
    """
    wiped: dict[str, int] = {}
    for dt in children + parents:          # con trước, cha sau
        n = _count(dt)
        if not n:
            continue
        frappe.db.sql(f"DELETE FROM `tab{dt}`")
        wiped[dt] = n
    frappe.db.commit()
    return wiped


def _clean_core_residue(dt_all: list[str]) -> dict:
    ph, args = _in_clause(dt_all)
    cleaned: dict[str, int] = {}
    for core_dt, col in _CORE_RESIDUE:
        if not frappe.db.table_exists(core_dt) or not frappe.db.has_column(core_dt, col):
            continue
        n = _count(core_dt, f"`{col}` IN ({ph})", args)
        if not n:
            continue
        frappe.db.sql(f"DELETE FROM `tab{core_dt}` WHERE `{col}` IN ({ph})", args)
        cleaned[f"{core_dt}.{col}"] = n
    frappe.db.commit()
    return cleaned


def _reset_series(prefixes: list[str]) -> int:
    if not prefixes:
        return 0
    ph, args = _in_clause(prefixes)
    frappe.db.sql(f"DELETE FROM `tabSeries` WHERE name IN ({ph})", args)
    frappe.db.commit()
    return len(prefixes)


def _wipe_users(keep_users: tuple[str, ...]) -> dict:
    victims = _wipeable_users(keep_users)
    if not victims:
        return {"user": 0}
    ph, args = _in_clause(victims)
    # Contact do Frappe tự sinh theo User (create_contact) + các bảng bám theo user.
    contacts = frappe.db.sql_list(
        f"SELECT DISTINCT parent FROM `tabContact Email` WHERE email_id IN ({ph})", args)
    if contacts:
        cph, cargs = _in_clause(contacts)
        for tbl in ("Contact Email", "Contact Phone"):
            if frappe.db.table_exists(tbl):
                frappe.db.sql(f"DELETE FROM `tab{tbl}` WHERE parent IN ({cph})", cargs)
        frappe.db.sql(f"DELETE FROM `tabContact` WHERE name IN ({cph})", cargs)
    for tbl, col in (("Has Role", "parent"), ("User Social Login", "parent"),
                     ("DefaultValue", "parent"), ("Notification Settings", "name"),
                     ("ToDo", "allocated_to"), ("User Permission", "user")):
        if frappe.db.table_exists(tbl) and frappe.db.has_column(tbl, col):
            frappe.db.sql(f"DELETE FROM `tab{tbl}` WHERE `{col}` IN ({ph})", args)
    frappe.db.sql(f"DELETE FROM `tabUser` WHERE name IN ({ph})", args)
    frappe.db.commit()
    return {"user": len(victims), "contact": len(contacts)}


def _wipe_logs() -> dict:
    out: dict[str, int] = {}
    for dt in _SITE_LOGS:
        if not frappe.db.table_exists(dt):
            continue
        n = _count(dt)
        if n:
            frappe.db.sql(f"DELETE FROM `tab{dt}`")
            out[dt] = n
    frappe.db.commit()
    return out


def _reseed() -> list[str]:
    """Dựng lại đúng phần cấu hình mà ``after_install`` tạo (BỎ build frontend)."""
    from assetcore.setup import install as _install

    done: list[str] = []
    steps = (
        ("workflow", _install._sync_workflows),
        ("uom", _install._seed_uoms),
        ("custom_field_user", _install.create_user_custom_fields),
        ("custom_field_erpnext_asset", _install._apply_erpnext_asset_custom_fields),
        ("rbac_matrix", _install._apply_rbac_matrix),
        ("role_profile", _install._seed_role_profiles),
        ("module_profile", _install._seed_module_profiles),
        ("core_permission", _install._apply_core_permissions),
    )
    for label, fn in steps:
        try:
            fn()
            done.append(label)
        except Exception as e:  # noqa: BLE001 — báo ra, đừng nuốt
            done.append(f"{label}: LỖI {type(e).__name__}: {e}")
    try:
        from frappe.utils.fixtures import sync_fixtures
        sync_fixtures("assetcore")
        done.append("fixtures")
    except Exception as e:  # noqa: BLE001
        done.append(f"fixtures: LỖI {type(e).__name__}: {e}")
    frappe.db.commit()
    return done


def run(confirm: str = "", wipe_users: bool = False, wipe_logs: bool = False,
        reseed: bool = True, keep_users: tuple = DEFAULT_KEEP_USERS) -> None:
    """Xoá sạch dữ liệu AssetCore rồi dựng lại cấu hình như vừa cài app."""
    if confirm != CONFIRM_TOKEN:
        print(f"❌ Thiếu xác nhận. Truyền --kwargs '{{\"confirm\": \"{CONFIRM_TOKEN}\"}}'.")
        print("   Xem trước bằng .preview trước khi chạy.")
        return

    frappe.set_user("Administrator")
    frappe.flags.in_install = True          # tắt hook nghiệp vụ khi dọn
    children, parents = _app_doctypes()
    dt_all = children + parents

    prefixes = _series_prefixes(parents)    # PHẢI lấy trước khi xoá
    before = {"cha": sum(_count(d) for d in parents),
              "con": sum(_count(d) for d in children)}

    wiped = _truncate_app_tables(children, parents)
    residue = _clean_core_residue(dt_all)
    n_series = _reset_series(prefixes)
    users = _wipe_users(tuple(keep_users)) if wipe_users else {}
    logs = _wipe_logs() if wipe_logs else {}
    seeded = _reseed() if reseed else []

    frappe.flags.in_install = False
    frappe.clear_cache()

    print(frappe.as_json({
        "truoc": before,
        "da_xoa_ban_ghi_app": {"so_doctype": len(wiped), "tong_dong": sum(wiped.values())},
        "top_10": dict(sorted(wiped.items(), key=lambda x: -x[1])[:10]),
        "da_don_can_bang_loi": residue,
        "bo_dem_ma_da_reset": n_series,
        "user": users,
        "log": logs,
        "da_dung_lai": seeded,
        "con_lai_ban_ghi_app": sum(_count(d) for d in parents),
    }))
    print("\n✅ Xong. Kiểm lại bằng .preview — 'tong_ban_ghi_cha' phải = 0.")
