# Copyright (c) 2026, AssetCore Team
# REST API cho Module IMM-14 — Record Archive & Lifecycle Closure.
# Tier 1 — parse HTTP input → gọi services.imm14 → _ok / _err envelope.

from __future__ import annotations

import frappe

from assetcore.services import imm14 as svc
from assetcore.services.shared.errors import ServiceError
from assetcore.utils.helpers import _err, _ok


def _handle(fn, *args, **kwargs) -> dict:
    """Wrapper bắt ServiceError và Exception, trả _ok / _err."""
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except frappe.ValidationError as e:
        return _err(str(e), "VALIDATION_ERROR")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-14 {fn.__name__}")
        return _err(str(e), "SYSTEM_ERROR")


# ─── Read Endpoints ───────────────────────────────────────────────────────────

@frappe.whitelist()
def get_archive_record(name: str) -> dict:
    """Lấy chi tiết Asset Archive Record."""
    def _get(n):
        doc = frappe.get_doc("Asset Archive Record", n)
        return doc.as_dict()

    return _handle(_get, name)


@frappe.whitelist()
def list_archive_records(status: str = "", asset: str = "",
                          page: int = 1, page_size: int = 20) -> dict:
    """Danh sách Asset Archive Records với filter."""
    def _list(s, a, pg, ps):
        filters: dict = {}
        if s:
            filters["status"] = s
        if a:
            filters["asset"] = a

        total = frappe.db.count("Asset Archive Record", filters)
        rows = frappe.db.get_all(
            "Asset Archive Record",
            filters=filters,
            fields=["name", "asset", "asset_name", "decommission_request",
                    "archive_date", "release_date", "status",
                    "total_documents_archived", "modified"],
            order_by="modified desc",
            limit_page_length=int(ps),
            limit_start=(int(pg) - 1) * int(ps),
        )
        return {"rows": rows, "total": total, "page": int(pg), "page_size": int(ps)}

    return _handle(_list, status, asset, page, page_size)


@frappe.whitelist()
def get_asset_full_history(asset_name: str) -> dict:
    """Toàn bộ timeline vòng đời thiết bị."""
    return _handle(svc.get_asset_full_history, asset_name)


@frappe.whitelist()
def get_dashboard_stats() -> dict:
    """Dashboard KPIs cho IMM-14."""
    return _handle(svc.get_dashboard_stats)


# ─── Write Endpoints ──────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def create_archive_record(asset: str, decommission_request: str = "",
                           archive_date: str = "", storage_location: str = "",
                           retention_years: int = 10) -> dict:
    """Tạo Asset Archive Record mới."""
    def _create(ast, dr, ad, sl, ry):
        from frappe.utils import nowdate
        doc = frappe.get_doc({
            "doctype": "Asset Archive Record",
            "asset": ast,
            "decommission_request": dr or None,
            "archive_date": ad or nowdate(),
            "archived_by": frappe.session.user,
            "storage_location": sl,
            "retention_years": int(ry),
            "status": "Draft",
        })
        doc.insert(ignore_permissions=True)
        return {
            "name": doc.name,
            "asset": doc.asset,
            "status": doc.status,
            "release_date": str(doc.release_date) if doc.release_date else None,
        }

    return _handle(_create, asset, decommission_request, archive_date, storage_location, retention_years)


@frappe.whitelist(methods=["POST"])
def add_document(archive_name: str, document_type: str, document_name: str = "",
                  document_date: str = "", archive_status: str = "Included") -> dict:
    """Thêm tài liệu đơn lẻ vào documents table."""
    def _add(an, dt, dn, dd, ars):
        doc = frappe.get_doc("Asset Archive Record", an)
        doc.append("documents", {
            "document_type": dt,
            "document_name": dn,
            "document_date": dd or None,
            "archive_status": ars,
        })
        doc.save(ignore_permissions=True)
        return {"archive_name": an, "added": {"document_type": dt, "document_name": dn}}

    return _handle(_add, archive_name, document_type, document_name, document_date, archive_status)


@frappe.whitelist(methods=["POST"])
def compile_asset_history(archive_name: str) -> dict:
    """Tự động tổng hợp tài liệu từ tất cả module."""
    return _handle(svc.compile_asset_history, archive_name)


@frappe.whitelist(methods=["POST"])
def verify_archive(name: str, verified_by: str = "", notes: str = "") -> dict:
    """QA Officer xác minh hồ sơ đầy đủ."""
    def _verify(n, vb, nt):
        doc = frappe.get_doc("Asset Archive Record", n)
        from frappe.utils import nowdate
        doc.status = "Verified"
        doc.workflow_state = "Verified"
        if nt:
            doc.archive_notes = (doc.archive_notes or "") + f"\n[Verified by {vb or frappe.session.user}]: {nt}"
        doc.save(ignore_permissions=True)
        svc.log_lifecycle_event(doc, "archive_verified", "Compiling", "Verified",
                                 f"Xác minh bởi {vb or frappe.session.user}. {nt}")
        return {"name": n, "status": "Verified"}

    return _handle(_verify, name, verified_by, notes)


@frappe.whitelist(methods=["POST"])
def finalize_archive(name: str) -> dict:
    """Submit Asset Archive Record → Archived. Sets Asset.status = Archived."""
    def _finalize(n):
        doc = frappe.get_doc("Asset Archive Record", n)
        doc.submit()
        return {"name": n, "status": "Archived", "asset": doc.asset}

    return _handle(_finalize, name)
