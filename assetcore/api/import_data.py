# Copyright (c) 2026, AssetCore Team
"""Import/Export API — Tier 1 thin wrapper.

Endpoints:
    preview_ref_data(doctype, file_url)          → parse + validate, no insert
    import_ref_data(doctype, file_url)           → validate + insert rows, return job summary
    export_ref_data(doctype)                     → download current data as xlsx
    download_template(doctype)                   → download blank Excel template
"""
from __future__ import annotations

import frappe

from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.import_helpers import (
    GROUPED_IMPORT_DOCTYPES,
    LINK_DISPLAY_BY_DOCTYPE,
    SOURCE_ROW_KEY,
    UPDATE_LOCKED_FIELDS_BY_DOCTYPE,
    enrich_issues,
    enum_to_stored,
    find_existing_by_key,
)
from assetcore.utils.response import _err, _ok


def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except (ValueError, FileNotFoundError) as e:
        return _err(str(e), ErrorCode.VALIDATION)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Import API Error")
        return _err("Lỗi hệ thống — xem Error Log để biết chi tiết.", ErrorCode.INTERNAL)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED CONSTANTS (used by both preview + import)
# ─────────────────────────────────────────────────────────────────────────────

# Bool fields shared across DocTypes. Add new flags here when introducing
# import templates that include them — _normalise_row() consults this set.
_BOOL_FIELDS: set[str] = {
    "is_active", "is_group", "is_transporter",
    "default_pm_required", "default_calibration_required",
    "has_radiation", "power_backup_available",
    "is_pm_required", "is_calibration_required",
    "is_radiation_device", "registration_required",
    "auto_renew",
}

# Link fields where the user fills the display name in the template but the
# Frappe field expects the doc name (system code). SSoT nằm ở
# `utils.import_helpers.LINK_DISPLAY_BY_DOCTYPE` — dùng chung với export (in TÊN
# thay vì mã) và với validator (`_link_lookup_set` chấp nhận cả tên lẫn mã).
# Alias giữ tên cũ cho call-site/test đang tham chiếu.
_RESOLVABLE_LINKS_BY_DOCTYPE = LINK_DISPLAY_BY_DOCTYPE

# Link fields that are tolerated as missing — if value doesn't resolve, drop
# the field rather than fail the row. Only fields the user can legitimately
# leave unmapped at import time should go here.
_OPTIONAL_LINKS_BY_DOCTYPE: dict[str, dict[str, str]] = {
    "AC Asset": {
        "device_model": "IMM Device Model",
        "location": "AC Location",
        "department": "AC Department",
        "supplier": "AC Supplier",
        "custodian": "User",
        "responsible_technician": "User",
    },
    # dept_head/manager là email User — sai chính tả không được làm hỏng cả dòng;
    # validator đã cảnh báo "sẽ để trống" nên insert phải bỏ field, không throw.
    "AC Department": {"dept_head": "User"},
    "AC Location": {"dept_head": "User"},
    "AC Warehouse": {"location": "AC Location", "department": "AC Department", "manager": "User"},
    "AC Spare Part": {"preferred_supplier": "AC Supplier"},
}


# ─────────────────────────────────────────────────────────────────────────────
# FOLDER INIT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def init_import_folders(doctype: str) -> dict:
    """
    Create Frappe folder hierarchy and commit. FE calls this before upload_file
    so the target folder exists when Frappe validates the Link field.
    Returns: {folder: "Home/AssetCore Imports/<doctype>"} or Home/Attachments fallback.
    """
    from assetcore.utils.import_helpers import ensure_import_folder
    try:
        safe = doctype.replace(" ", "_")
        folder = ensure_import_folder(safe)
        ensure_import_folder("Error Reports")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Init Import Folders")
        folder = "Home/Attachments"
    return _ok({"folder": folder})


# ─────────────────────────────────────────────────────────────────────────────
# PREVIEW
# ─────────────────────────────────────────────────────────────────────────────

def _as_bool(value) -> bool:
    """Cờ từ HTTP có thể tới dạng bool, số, hoặc chuỗi 'true'/'0'.

    `cint("true")` trả 0 nên KHÔNG dùng được ở đây — một cờ đọc sai là ghi đè
    dữ liệu ngoài ý muốn (update_existing) hoặc nhập thiếu (skip_invalid).
    """
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


@frappe.whitelist(methods=["POST"])
def preview_ref_data(doctype: str, file_url: str, update_existing=False) -> dict:
    """
    Parse file + chạy pre-validators. KHÔNG insert.
    Returns: {total_rows, valid_rows, preview (10 dòng), errors, warnings,
              groups (DocType cha + bảng con)}

    update_existing=True: bản ghi đã tồn tại được xem là 'sẽ cập nhật' thay vì
    lỗi trùng — FE gọi lại preview khi người dùng bật lựa chọn này.
    """
    return _handle(_do_preview, doctype, file_url, _as_bool(update_existing))


def _do_preview(doctype: str, file_url: str, update_existing: bool = False) -> dict:
    from assetcore.services.import_validators import get_validator
    from assetcore.utils.import_helpers import (
        SUPPORTED_REF_DOCTYPES,
        parse_upload_file,
    )

    if doctype not in SUPPORTED_REF_DOCTYPES:
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"DocType '{doctype}' chưa hỗ trợ import — hỗ trợ: {', '.join(SUPPORTED_REF_DOCTYPES)}",
        )

    fieldnames, rows = parse_upload_file(file_url, doctype)

    if not rows:
        raise ServiceError(ErrorCode.VALIDATION, "File không có dòng dữ liệu (từ hàng 6 trở xuống).")

    validator = get_validator(doctype, update_existing=update_existing)
    all_issues = enrich_issues(doctype, rows, validator.validate_all(rows))

    errors   = [e for e in all_issues if e["severity"] == "error"]
    warnings = [e for e in all_issues if e["severity"] == "warning"]
    invalid_rows = {e["row"] for e in errors}

    # Tree DocType: predict cascade so FE can show "5 lỗi + 2 phụ thuộc"
    # before user picks skip mode.
    _, cascade = _cascade_skip_for_tree(doctype, rows, set(invalid_rows))
    cascade_count = len(cascade)

    from assetcore.utils.import_helpers import field_label

    result = {
        "doctype": doctype,
        "total_rows": len(rows),
        "valid_rows": len(rows) - len(invalid_rows) - cascade_count,
        "preview": rows[:10],
        "fieldnames": fieldnames,
        # Nhãn VI cho từng cột — FE hiển thị "Danh mục tài sản", không phải
        # "asset_category" (người dùng chỉ biết nhãn ở hàng 3 của template).
        "field_labels": {fn: field_label(doctype, fn) for fn in fieldnames if fn},
        "errors": errors,
        "warnings": warnings,
        "cascade_count": cascade_count,
    }

    # DocType cha + bảng con: đếm DÒNG là vô nghĩa với người dùng — họ cần biết
    # file này tạo/cập nhật MẤY BẢN GHI và mỗi bản ghi mấy dòng con.
    if doctype in GROUPED_IMPORT_DOCTYPES:
        groups = _summarise_groups(doctype, rows, invalid_rows, update_existing)
        result["groups"] = groups
        result["groups_total"] = len(groups)
    else:
        existing_by_row = find_existing_by_key(doctype, rows)
        valid = [i for i in range(1, len(rows) + 1) if i not in invalid_rows]
        # Chỉ đếm là "sẽ cập nhật" khi người dùng ĐÃ bật công tắc — tắt thì các
        # dòng đó đang bị chặn, đếm vào là hứa hẹn thứ hệ thống sẽ không làm.
        result["will_update"] = (
            len([i for i in valid if i in existing_by_row]) if update_existing else 0
        )
        result["will_create"] = len([i for i in valid if i not in existing_by_row])
        # Có bản ghi trùng nhưng chưa bật công tắc ⇒ FE vẫn phải mời chào bật.
        result["existing_rows"] = len([
            i for i in range(1, len(rows) + 1) if i in existing_by_row
        ])
        result["warnings"].extend(
            enrich_issues(doctype, rows,
                          _locked_field_warnings(doctype, rows, existing_by_row))
            if update_existing else []
        )
    return result


def _locked_field_warnings(
    doctype: str, rows: list[dict], existing_by_row: dict[int, str],
) -> list[dict]:
    """Cảnh báo khi file đòi đổi cột bị khoá của bản ghi đã có.

    Bỏ qua im lặng là tệ nhất: người dùng sửa 'trạng thái vòng đời' trong file,
    nhập xong thấy báo thành công, tưởng đã đổi. Nói thẳng là đã giữ nguyên.
    """
    locked = UPDATE_LOCKED_FIELDS_BY_DOCTYPE.get(doctype, ())
    if not locked or not existing_by_row:
        return []

    from assetcore.utils.import_helpers import enum_to_stored, field_label

    issues: list[dict] = []
    for row_idx, name in existing_by_row.items():
        row = rows[row_idx - 1]
        for field in locked:
            value = str(row.get(field, "")).strip()
            if not value:
                continue
            current = str(frappe.db.get_value(doctype, name, field) or "")
            if enum_to_stored(doctype, field, value) == current:
                continue
            issues.append({
                "row": row_idx,
                "field": field,
                "message": (
                    f"'{field_label(doctype, field)}' không đổi được bằng nhập file "
                    f"— giữ nguyên '{current}'. Sửa trên màn hình chi tiết để có "
                    "đủ phê duyệt và lịch sử thay đổi."
                ),
                "severity": "warning",
            })
    return issues


def _summarise_groups(
    doctype: str, rows: list[dict], invalid_idx: set[int], update_existing: bool,
) -> list[dict]:
    """Xem trước theo NHÓM: mỗi bản ghi cha sẽ tạo/cập nhật + số dòng con.

    Hàng lỗi bị loại khỏi số hạng mục để con số hiện ra khớp với thứ sẽ nhập
    thật, không phải số hàng thô trong file.
    """
    cfg = GROUPED_IMPORT_DOCTYPES[doctype]
    cache: dict[tuple[str, str], str] = {}
    name_field = cfg.get("name_field", "")

    groups: dict[tuple, dict] = {}
    for i, row in enumerate(rows, start=1):
        key = _group_key_of(doctype, cfg, row, cache)
        key_text = " · ".join(str(k) for k in key if str(k).strip())
        g = groups.setdefault(key, {
            # Hàng thiếu cột khoá gộp vào một nhóm khoá rỗng — gọi tên nó ra,
            # đừng để bảng tóm tắt hiện một dòng trống không ai hiểu là gì.
            "key": key_text or "(thiếu thông tin nhận dạng)",
            "name_value": str(row.get(name_field, "") or "") if name_field else "",
            "rows": 0,
            "items": 0,
            "first_source_row": row.get(SOURCE_ROW_KEY) or i,
        })
        g["rows"] += 1
        if i not in invalid_idx:
            g["items"] += 1

    summary: list[dict] = []
    for key, g in groups.items():
        filters = dict(zip(cfg["group_key_fields"], key))
        existing = frappe.db.exists(doctype, filters)
        display = _group_key_display(doctype, cfg, key)
        summary.append({
            **g,
            **display,
            "exists": bool(existing),
            "existing_items": (
                frappe.db.count(cfg["child_doctype"],
                                {"parent": existing, "parenttype": doctype})
                if existing else 0
            ),
            "action": (
                ("update" if update_existing else "blocked") if existing else "create"
            ),
        })
    return summary


def _group_key_display(doctype: str, cfg: dict, key: tuple) -> dict:
    """Khoá nhóm (mã + enum gốc) → chữ người dùng đọc được.

    Khoá dựng bằng mã danh mục và enum tiếng Anh để gộp cho đúng; hiện ra màn
    hình mà vẫn là mã thì người dùng không đối chiếu được với file họ vừa điền.
    """
    from assetcore.utils.import_helpers import enum_display

    resolvable = _RESOLVABLE_LINKS_BY_DOCTYPE.get(doctype, {})
    out: dict[str, str] = {}
    for field, value in zip(cfg["group_key_fields"], key):
        text = str(value or "")
        link_cfg = resolvable.get(field)
        if link_cfg and text:
            link_dt, display_field = link_cfg
            text = frappe.db.get_value(link_dt, text, display_field) or text
        else:
            text = enum_display(doctype, field, text)
        out[_GROUP_KEY_ALIAS.get(field, field)] = text
    return out


# Tên khoá gửi cho FE — giữ ngắn và không phụ thuộc fieldname của một DocType
# cụ thể, để màn hình khác dùng lại được khi có loại dữ liệu nhóm thứ hai.
_GROUP_KEY_ALIAS = {"asset_category": "category"}


# ─────────────────────────────────────────────────────────────────────────────
# CASCADE HELPER (Tree DocType skip propagation)
# ─────────────────────────────────────────────────────────────────────────────

def _cascade_skip_for_tree(
    doctype: str,
    rows: list[dict],
    invalid_idx: set[int],
) -> tuple[set[int], list[dict]]:
    """If DocType is Tree and a parent row is skipped, propagate skip to all
    descendants in the same batch. Avoids orphan tree nodes and "Could not
    find Parent" crashes downstream. Returns (final_invalid_idx, extra_skip).
    """
    if not invalid_idx:
        return invalid_idx, []

    try:
        meta = frappe.get_meta(doctype)
    except Exception:
        return invalid_idx, []
    if not getattr(meta, "is_tree", 0):
        return invalid_idx, []

    parent_field = getattr(meta, "nsm_parent_field", None)
    cfg = _RESOLVABLE_LINKS_BY_DOCTYPE.get(doctype, {}).get(parent_field or "")
    if not parent_field or not cfg:
        return invalid_idx, []
    _, display_field = cfg

    skipped_names: set[str] = {
        str(rows[i - 1].get(display_field, "")).strip()
        for i in invalid_idx
        if 1 <= i <= len(rows) and str(rows[i - 1].get(display_field, "")).strip()
    }

    extra_skip: list[dict] = []
    changed = True
    while changed:
        changed = False
        for i, row in enumerate(rows, start=1):
            if i in invalid_idx:
                continue
            parent_val = str(row.get(parent_field, "")).strip()
            if parent_val and parent_val in skipped_names:
                invalid_idx.add(i)
                extra_skip.append({
                    "row": i,
                    "reason": "cascade_parent_skipped",
                    "field": parent_field,
                    "message": f"Cha '{parent_val}' đã bị bỏ qua → bỏ qua dòng này",
                })
                own_name = str(row.get(display_field, "")).strip()
                if own_name:
                    skipped_names.add(own_name)
                changed = True

    return invalid_idx, extra_skip


# ─────────────────────────────────────────────────────────────────────────────
# IMPORT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def import_ref_data(
    doctype: str, file_url: str, skip_invalid=False, update_existing=False,
) -> dict:
    """
    Validate + insert rows trực tiếp (không qua Frappe Data Import engine).
    Reference data không có side-effects → direct insert an toàn.

    skip_invalid=False (mặc định): có lỗi pre-validate → ServiceError, abort.
    skip_invalid=True: bỏ qua dòng lỗi (+ cascade child cho Tree DocType),
        vẫn insert phần hợp lệ. KHÔNG hỗ trợ cho `User` doctype.
    update_existing=True: DocType cha+bảng con — bản ghi đã tồn tại được cập
        nhật, TOÀN BỘ bảng con thay theo file. Mặc định False (chỉ tạo mới).

    Returns: {total, success, failed, skipped, errors, skipped_rows,
              groups_created, groups_updated}
    """
    return _handle(
        _do_import, doctype, file_url, _as_bool(skip_invalid), _as_bool(update_existing),
    )


def _do_import(
    doctype: str, file_url: str, skip_invalid: bool = False,
    update_existing: bool = False,
) -> dict:
    from assetcore.services.import_validators import get_validator
    from assetcore.utils.import_helpers import (
        SUPPORTED_REF_DOCTYPES,
        parse_upload_file,
    )

    if doctype not in SUPPORTED_REF_DOCTYPES:
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"DocType '{doctype}' chưa hỗ trợ import",
        )

    _, rows = parse_upload_file(file_url, doctype)
    if not rows:
        raise ServiceError(ErrorCode.VALIDATION, "File không có dòng dữ liệu.")

    # ── Pre-validate ───────────────────────────────────────────────────────
    validator = get_validator(doctype, update_existing=update_existing)
    issues = validator.validate_all(rows)
    blocking = [e for e in issues if e["severity"] == "error"]

    invalid_idx: set[int] = set()
    skipped_rows: list[dict] = []

    if blocking:
        if not skip_invalid:
            raise ServiceError(
                ErrorCode.VALIDATION,
                f"File có {len(blocking)} dòng lỗi cần sửa trước khi nhập. "
                "Xem chi tiết ở bước kiểm tra, hoặc chọn "
                "'Bỏ qua dòng lỗi/trùng' để nhập phần hợp lệ.",
            )

        for e in blocking:
            invalid_idx.add(e["row"])
            skipped_rows.append({
                "row": e["row"],
                "reason": "pre_validate",
                "field": e["field"],
                "message": e["message"],
            })

        # Tree DocType: skip child cũng nếu parent bị skip (avoid orphans)
        invalid_idx, cascade = _cascade_skip_for_tree(doctype, rows, invalid_idx)
        skipped_rows.extend(cascade)

        if len(invalid_idx) >= len(rows):
            raise ServiceError(
                ErrorCode.VALIDATION,
                "Không có dòng hợp lệ nào để nhập — toàn bộ file đều lỗi.",
            )

    enrich_issues(doctype, rows, skipped_rows)

    # ── Insert ─────────────────────────────────────────────────────────────
    if doctype == "User":
        return _do_import_users(rows, invalid_idx, skipped_rows)
    if doctype in GROUPED_IMPORT_DOCTYPES:
        return _do_import_grouped(
            doctype, rows, invalid_idx, skipped_rows, update_existing)

    resolvable_links = _RESOLVABLE_LINKS_BY_DOCTYPE.get(doctype, {})
    optional_links = _OPTIONAL_LINKS_BY_DOCTYPE.get(doctype, {})
    existing_by_row = find_existing_by_key(doctype, rows) if update_existing else {}

    results: dict = {
        "total": len(rows),
        "success": 0,
        "failed": 0,
        "skipped": len(invalid_idx),
        "errors": [],
        "skipped_rows": skipped_rows,
        "updated": 0,
    }

    for i, row in enumerate(rows, start=1):
        if i in invalid_idx:
            continue
        try:
            clean = _normalise_row(row, _BOOL_FIELDS)
            _resolve_links(clean, resolvable_links)
            _restore_enum_values(doctype, clean)
            _drop_unresolved_optional_links(clean, optional_links)

            if i in existing_by_row:
                _update_flat_record(doctype, existing_by_row[i], clean)
                results["updated"] += 1
                results["success"] += 1
                continue

            # AC Asset: workflow only allows new docs at "Draft". Capture the
            # desired status so we can transition AFTER insert (mirrors the
            # logic in api.imm00.create_asset for non-procurement assets).
            desired_status = ""
            if doctype == "AC Asset":
                desired_status = (clean.get("lifecycle_status") or "").strip()
                clean["lifecycle_status"] = "Draft"

            doc = frappe.new_doc(doctype)
            doc.update(clean)
            doc.insert(ignore_permissions=True)

            if doctype == "AC Asset" and desired_status and desired_status != "Draft":
                _transition_asset_lifecycle(doc.name, desired_status)
            results["success"] += 1
        except Exception as e:
            frappe.log_error(f"Import row {i} failed: {e}", "Import Ref Data")
            results["failed"] += 1
            results["errors"].append({
                "row": i,
                "field": "",
                "message": _friendly_frappe_error(str(e)),
                "severity": "error",
            })

    enrich_issues(doctype, rows, results["errors"])
    frappe.db.commit()
    return results


def _update_flat_record(doctype: str, name: str, clean: dict) -> None:
    """Ghi đè bản ghi đã có bằng các ô CÓ DỮ LIỆU trong file.

    Hai luật đã chốt với người dùng (2026-08-11):
      - **Ô để trống = giữ nguyên giá trị cũ.** Người nhập liệu thường chỉ quan
        tâm vài cột; coi ô trống là "xoá" thì xuất 8 cột sửa 1 cột là mất 7.
      - **Cột nhạy cảm bị khoá** (`UPDATE_LOCKED_FIELDS_BY_DOCTYPE`): trạng thái
        vòng đời / mã tài sản / serial đi kèm workflow + vết kiểm toán, đổi bằng
        file là đi vòng cả hai. Cảnh báo đã báo ở bước xem trước.
    """
    locked = set(UPDATE_LOCKED_FIELDS_BY_DOCTYPE.get(doctype, ()))
    payload = {
        field: value for field, value in clean.items()
        if field not in locked and value not in ("", None)
    }
    doc = frappe.get_doc(doctype, name)
    doc.update(payload)
    doc.save(ignore_permissions=True)


def _group_key_of(
    doctype: str, cfg: dict, row: dict, cache: dict | None = None,
) -> tuple:
    """Khoá định danh của nhóm — đã chuẩn hoá tên→mã và nhãn VI→giá trị lưu.

    Người dùng có thể viết "Máy thở" ở dòng này, mã "CAT-0007" ở dòng kia; cùng
    một mẫu thì phải rơi vào cùng nhóm, nếu không sẽ tạo 2 lần và đụng khoá.
    `cache` gom kết quả tra Link cho cả file — không có nó thì file 300 hàng bắn
    600 truy vấn cho đúng vài giá trị lặp lại.
    """
    resolvable = _RESOLVABLE_LINKS_BY_DOCTYPE.get(doctype, {})
    if cache is None:
        cache = {}
    key: list[str] = []
    for field in cfg["group_key_fields"]:
        value = str(row.get(field, "")).strip()
        cfgl = resolvable.get(field)
        if cfgl and value:
            cache_key = (field, value)
            if cache_key not in cache:
                link_dt, display_field = cfgl
                cache[cache_key] = (
                    value if frappe.db.exists(link_dt, value)
                    else (frappe.db.get_value(link_dt, {display_field: value}, "name")
                          or value)
                )
            value = cache[cache_key]
        key.append(enum_to_stored(doctype, field, value))
    return tuple(key)


def _do_import_grouped(
    doctype: str, rows: list[dict],
    invalid_idx: set[int], skipped_rows: list[dict],
    update_existing: bool = False,
) -> dict:
    """Nhập DocType có BẢNG CON từ file phẳng: gộp các hàng cùng khoá thành 1 bản ghi.

    Mỗi hàng file = 1 dòng bảng con; cột của bản ghi cha lặp lại ở mọi hàng và
    lấy theo hàng ĐẦU TIÊN của nhóm. Hàng lỗi bị bỏ qua vẫn cho phần còn lại của
    nhóm được tạo — đúng tinh thần 'bỏ qua dòng lỗi/trùng'.

    `update_existing=True` (người dùng bật ở bước xem trước): bản ghi đã có được
    CẬP NHẬT — toàn bộ bảng con thay bằng nội dung file, đúng vòng
    "Xuất Excel → sửa → Nhập lại". Tắt (mặc định) thì bản ghi trùng đã bị
    validator chặn từ trước, không tới được đây.

    Đi qua service layer (`services.imm08.create_template` / `update_template`)
    chứ KHÔNG `new_doc().insert()` trần: quy tắc nghiệp vụ + đánh số hạng mục
    nằm ở đó.
    """
    cfg = GROUPED_IMPORT_DOCTYPES[doctype]
    resolvable = _RESOLVABLE_LINKS_BY_DOCTYPE.get(doctype, {})
    cache: dict[tuple[str, str], str] = {}

    results: dict = {
        "total": len(rows),
        "success": 0,
        "failed": 0,
        "skipped": len(invalid_idx),
        "errors": [],
        "skipped_rows": skipped_rows,
        "groups_created": 0,
        "groups_updated": 0,
    }

    # Gộp nhóm theo thứ tự xuất hiện để thông báo lỗi bám đúng hàng đầu nhóm.
    groups: dict[tuple, dict] = {}
    for i, row in enumerate(rows, start=1):
        if i in invalid_idx:
            continue
        key = _group_key_of(doctype, cfg, row, cache)
        group = groups.setdefault(key, {"first_row": i, "rows": [], "parent": {}})
        if not group["parent"]:
            parent = {f: row.get(f) for f in cfg["parent_fields"] if row.get(f) not in ("", None)}
            _resolve_links(parent, resolvable)
            for f in cfg["parent_fields"]:
                if parent.get(f):
                    parent[f] = enum_to_stored(doctype, f, str(parent[f]))
            group["parent"] = parent
        group["rows"].append((i, row))

    for key, group in groups.items():
        row_indexes = [i for i, _ in group["rows"]]
        try:
            children = [
                _build_child_row(doctype, cfg, row) for _, row in group["rows"]
            ]
            existing = (
                frappe.db.exists(doctype, dict(zip(cfg["group_key_fields"], key)))
                if update_existing else None
            )
            if existing:
                _update_grouped_record(
                    doctype, str(existing), group["parent"], cfg["child_table"], children)
                results["groups_updated"] += 1
            else:
                _create_grouped_record(
                    doctype, group["parent"], cfg["child_table"], children)
                results["groups_created"] += 1
            results["success"] += len(row_indexes)
        except Exception as e:            # noqa: BLE001 — lỗi 1 nhóm không được giết cả file
            frappe.log_error(f"Import group {key} failed: {e}", "Import Grouped Data")
            results["failed"] += len(row_indexes)
            for i in row_indexes:
                results["errors"].append({
                    "row": i,
                    "field": "",
                    "message": _friendly_frappe_error(str(e)),
                    "severity": "error",
                })

    enrich_issues(doctype, rows, results["errors"])
    frappe.db.commit()
    return results


def _build_child_row(doctype: str, cfg: dict, row: dict) -> dict:
    """1 hàng file → 1 dòng bảng con, đã ép kiểu số/cờ và đổi nhãn VI về giá trị lưu."""
    child: dict = {}
    for field in cfg["child_fields"]:
        value = row.get(field)
        if value in ("", None):
            continue
        if field in _BOOL_FIELDS or field == "is_critical":
            child[field] = 1 if str(value) in ("1", "True", "true", "yes") else 0
        elif field in ("expected_min", "expected_max"):
            child[field] = float(str(value))
        else:
            child[field] = enum_to_stored(doctype, field, str(value).strip())
    return child


def _create_grouped_record(
    doctype: str, parent: dict, child_table: str, children: list[dict],
) -> None:
    """Tạo bản ghi cha + bảng con qua service layer của module tương ứng."""
    if doctype == "PM Checklist Template":
        from assetcore.services import imm08

        imm08.create_template({**parent, child_table: children})
        return
    raise ServiceError(
        ErrorCode.VALIDATION,
        f"DocType '{doctype}' chưa có đường tạo bản ghi theo nhóm",
    )


def _update_grouped_record(
    doctype: str, name: str, parent: dict, child_table: str, children: list[dict],
) -> None:
    """Cập nhật bản ghi cha + THAY toàn bộ bảng con theo file.

    Vẫn đi qua service layer để giữ nguyên validate nghiệp vụ và đánh số lại
    hạng mục; không `db_set` thẳng vào bảng con.
    """
    if doctype == "PM Checklist Template":
        from assetcore.services import imm08

        imm08.update_template(name, {**parent, child_table: children})
        return
    raise ServiceError(
        ErrorCode.VALIDATION,
        f"DocType '{doctype}' chưa có đường cập nhật bản ghi theo nhóm",
    )


def _resolve_links(clean: dict, resolvable: dict[str, tuple[str, str]]) -> None:
    """Resolve display name → doc name for Link fields. Mutates `clean` in-place.

    Tree DocType cross-row resolve in same batch works because frappe.db
    queries see the write-through transaction state after each doc.insert().
    """
    for fld, (link_dt, display_field) in resolvable.items():
        val = clean.get(fld)
        if not val or frappe.db.exists(link_dt, val):
            continue   # empty, or already a valid doc name (system code)
        resolved = frappe.db.get_value(link_dt, {display_field: val}, "name")
        if resolved:
            clean[fld] = resolved
        # else: leave value; Frappe core will surface "Could not find <Link>"


def _restore_enum_values(doctype: str, clean: dict) -> None:
    """Nhãn VI người dùng chọn trong file → giá trị gốc của DocType Select.

    Template + export in nhãn tiếng Việt ("Đang hoạt động"), nhưng field Select
    chỉ nhận giá trị gốc ("Active"). Bỏ bước này thì Frappe ném lỗi giá trị không
    hợp lệ — hoặc tệ hơn, lưu thẳng nhãn VI và vỡ mọi filter/workflow sau đó.
    Enum của DocType KHÔNG đổi — chỉ lớp nhập/xuất dịch qua lại (LL-FE-53).
    """
    from assetcore.utils.import_helpers import ENUM_DISPLAY_BY_DOCTYPE

    for field in ENUM_DISPLAY_BY_DOCTYPE.get(doctype, {}):
        value = clean.get(field)
        if value:
            clean[field] = enum_to_stored(doctype, field, str(value).strip())


def _drop_unresolved_optional_links(clean: dict, optional: dict[str, str]) -> None:
    """Drop Link values that don't resolve, so insert won't fail on optional FKs."""
    for fld, link_dt in optional.items():
        val = clean.get(fld)
        if val and not frappe.db.exists(link_dt, val):
            clean.pop(fld, None)


def _transition_asset_lifecycle(asset_name: str, desired_status: str) -> None:
    """Walk the AC Asset workflow from Draft to desired_status.

    Workflow path: Draft → Commissioned → Active. Other terminal/branch states
    (Out of Service, Decommissioned, ...) are not reachable in bulk import and
    silently ignored so a bad CSV row doesn't trap the asset mid-flight.
    """
    from assetcore.services.imm00 import transition_asset_status

    chain: list[str] = []
    if desired_status == "Commissioned":
        chain = ["Commissioned"]
    elif desired_status == "Active":
        chain = ["Commissioned", "Active"]
    else:
        return
    for step in chain:
        transition_asset_status(asset_name, to_status=step, reason="Bulk import")


def _normalise_row(row: dict, bool_fields: set[str]) -> dict:
    """Convert string values to proper Python types for frappe.new_doc."""
    out: dict = {}
    for k, v in row.items():
        # Khoá kỹ thuật của parser (SOURCE_ROW_KEY) KHÔNG phải field DocType.
        if k == SOURCE_ROW_KEY or k.startswith("__") or v == "" or v is None:
            continue
        if k in bool_fields:
            out[k] = 1 if str(v) in ("1", "True", "true", "yes") else 0
        else:
            out[k] = v
    return out


def _friendly_frappe_error(msg: str) -> str:
    """Extract meaningful part from Frappe exception strings."""
    if "Duplicate entry" in msg:
        return "Bản ghi đã tồn tại (trùng tên hoặc mã)."
    if "cannot be null" in msg.lower() or "mandatory" in msg.lower():
        return "Thiếu trường bắt buộc."
    return msg[:200]


def _do_import_users(
    rows: list[dict],
    invalid_idx: set[int] | None = None,
    skipped_rows: list[dict] | None = None,
) -> dict:
    """Upsert Frappe Users — insert new, update existing; assign roles additively.

    Resolves `ac_department` display name → AC-DEPT-#### code (LL-BE-26).
    `invalid_idx` = các dòng đã bị pre-validate loại khi bật 'bỏ qua dòng lỗi'.
    """
    invalid_idx = invalid_idx or set()
    results: dict = {
        "total": len(rows), "success": 0, "failed": 0,
        "skipped": len(invalid_idx), "errors": [],
        "skipped_rows": skipped_rows or [],
    }
    _USER_FIELDS = ("first_name", "last_name", "mobile_no", "ac_department", "imm_approval_status")
    user_resolvable = _RESOLVABLE_LINKS_BY_DOCTYPE.get("User", {})

    for i, row in enumerate(rows, start=1):
        if i in invalid_idx:
            continue
        try:
            email = str(row.get("email", "")).strip()
            if not email:
                raise ValueError("Email là bắt buộc")

            is_new = not frappe.db.exists("User", email)
            user = frappe.new_doc("User") if is_new else frappe.get_doc("User", email)

            if is_new:
                user.email = email
                user.send_welcome_email = 0

            # Resolve display-name → system code for Link fields (ac_department etc.)
            staged = {f: str(row.get(f, "")).strip() for f in _USER_FIELDS if row.get(f)}
            _resolve_links(staged, user_resolvable)
            for field, val in staged.items():
                setattr(user, field, val)

            if is_new:
                user.insert(ignore_permissions=True)
            else:
                user.save(ignore_permissions=True)

            # Add roles listed in file (additive — never removes existing roles)
            roles_raw = str(row.get("roles", "")).strip()
            if roles_raw:
                user_doc = frappe.get_doc("User", email)
                existing = {hr.role for hr in user_doc.get("roles", [])}
                new_roles = [
                    r.strip() for r in roles_raw.split(",")
                    if r.strip() and r.strip() not in existing and frappe.db.exists("Role", r.strip())
                ]
                if new_roles:
                    user_doc.add_roles(*new_roles)

            results["success"] += 1
        except Exception as e:
            frappe.log_error(f"Import User row {i} failed: {e}", "Import User Data")
            results["failed"] += 1
            results["errors"].append({
                "row": i, "field": "",
                "message": _friendly_frappe_error(str(e)),
                "severity": "error",
            })

    enrich_issues("User", rows, results["errors"])
    frappe.db.commit()
    return results


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def export_ref_data(doctype: str):
    """Download current data as Excel. Returns file as response attachment."""
    from assetcore.utils.import_helpers import (
        SUPPORTED_REF_DOCTYPES,
        export_ref_data as _export,
    )

    if doctype not in SUPPORTED_REF_DOCTYPES:
        frappe.throw(f"DocType '{doctype}' không hỗ trợ export")

    try:
        xlsx_bytes = _export(doctype)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Export Ref Data Error")
        frappe.throw(f"Lỗi khi tạo file export: {e}")

    safe_name = doctype.replace(" ", "_").lower()
    filename = f"export_{safe_name}.xlsx"

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = xlsx_bytes
    frappe.local.response.type = "download"


# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def download_template(doctype: str):
    """Serve blank Excel import template for the given DocType."""
    from assetcore.utils.import_helpers import get_template_path

    try:
        path = get_template_path(doctype)
    except (ValueError, FileNotFoundError) as e:
        frappe.throw(str(e))

    with open(path, "rb") as f:
        content = f.read()

    import os
    filename = os.path.basename(path)
    frappe.local.response.filename = filename
    frappe.local.response.filecontent = content
    frappe.local.response.type = "download"


# ─────────────────────────────────────────────────────────────────────────────
# BUILD ERROR REPORT (for FE download)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def build_error_report(doctype: str, file_url: str) -> dict:
    """
    Parse file, run validators, return error report as uploaded File URL.
    FE calls this to get a downloadable xlsx with highlighted error rows.
    """
    return _handle(_do_build_error_report, doctype, file_url)


def _do_build_error_report(doctype: str, file_url: str) -> dict:
    from frappe.utils.file_manager import save_file

    from assetcore.services.import_validators import get_validator
    from assetcore.utils.import_helpers import (
        build_error_report,
        ensure_import_folder,
        parse_upload_file,
    )

    fieldnames, rows = parse_upload_file(file_url, doctype)
    validator = get_validator(doctype)
    errors = enrich_issues(doctype, rows, validator.validate_all(rows))

    xlsx_bytes = build_error_report(fieldnames, rows, errors, doctype)

    folder = ensure_import_folder("Error Reports")
    fname = f"error_report_{doctype.replace(' ', '_').lower()}.xlsx"
    file_doc = save_file(fname, xlsx_bytes, dt="", dn="", folder=folder, is_private=1)

    return {"file_url": file_doc.file_url, "error_count": len(errors)}
