# Copyright (c) 2026, AssetCore Team
"""Email helpers shared across schedulers and services."""
from typing import Iterable
import frappe


def get_role_emails(roles: Iterable[str]) -> list:
    roles = [r for r in roles if r]
    if not roles:
        return []
    placeholders = ", ".join(["%s"] * len(roles))
    rows = frappe.db.sql(
        f"""
        SELECT DISTINCT u.email
        FROM `tabHas Role` hr
        JOIN `tabUser` u ON u.name = hr.parent
        WHERE hr.role IN ({placeholders})
          AND hr.parenttype = 'User'
          AND u.enabled = 1
          AND u.email IS NOT NULL AND u.email != ''
        """,
        list(roles),
        as_dict=True,
    )
    return [r.email for r in rows]


def safe_sendmail(recipients, subject: str, message: str) -> None:
    if not recipients:
        return
    try:
        frappe.sendmail(recipients=recipients, subject=subject, message=message)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"safe_sendmail failed: {subject}")


# ─── Approval request email ───────────────────────────────────────────────────

_DOC_LABELS = {
    "Needs Assessment": ("Phiếu nhu cầu mua sắm", "planning/needs-assessments"),
    "Procurement Plan": ("Kế hoạch mua sắm", "planning/procurement-plans"),
    "Technical Specification": ("Đặc tả kỹ thuật", "planning/technical-specs"),
    "Purchase Order Request": ("Phiếu đặt hàng", "planning/purchase-order-requests"),
    "Vendor Evaluation": ("Phiếu đánh giá NCC", "planning/vendor-evaluations"),
}


def send_approval_request(
    doctype: str,
    doc_name: str,
    approver_user: str,
    submitted_by: str = "",
    extra_info: str = "",
) -> None:
    """Gửi email yêu cầu phê duyệt cho `approver_user`."""
    approver_email = frappe.db.get_value("User", approver_user, "email")
    if not approver_email:
        return

    label, route = _DOC_LABELS.get(doctype, (doctype, ""))
    site_url = frappe.utils.get_url()
    doc_url = f"{site_url}/assetcore#/{route}/{doc_name}"

    submitter_name = (
        frappe.db.get_value("User", submitted_by, "full_name") or submitted_by
        if submitted_by else "Hệ thống"
    )

    subject = f"[AssetCore] Yêu cầu phê duyệt: {doc_name}"
    message = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#1e40af;padding:20px 24px;border-radius:8px 8px 0 0;">
        <h2 style="color:#fff;margin:0;font-size:18px;">AssetCore — Yêu cầu phê duyệt</h2>
      </div>
      <div style="border:1px solid #e2e8f0;border-top:none;padding:24px;border-radius:0 0 8px 8px;">
        <p style="color:#374151;margin:0 0 16px;">Bạn có một tài liệu mới cần phê duyệt:</p>
        <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
          <tr>
            <td style="padding:8px 12px;background:#f8fafc;color:#64748b;font-size:13px;width:40%;border-radius:4px 0 0 4px;">Loại tài liệu</td>
            <td style="padding:8px 12px;background:#f8fafc;font-weight:600;font-size:13px;border-radius:0 4px 4px 0;">{label}</td>
          </tr>
          <tr>
            <td style="padding:8px 12px;color:#64748b;font-size:13px;">Mã tài liệu</td>
            <td style="padding:8px 12px;font-family:monospace;font-size:13px;">{doc_name}</td>
          </tr>
          <tr>
            <td style="padding:8px 12px;background:#f8fafc;color:#64748b;font-size:13px;">Người gửi</td>
            <td style="padding:8px 12px;background:#f8fafc;font-size:13px;">{submitter_name}</td>
          </tr>
          {f'<tr><td style="padding:8px 12px;color:#64748b;font-size:13px;">Ghi chú</td><td style="padding:8px 12px;font-size:13px;">{extra_info}</td></tr>' if extra_info else ''}
        </table>
        <div style="text-align:center;margin:24px 0;">
          <a href="{doc_url}"
             style="background:#1e40af;color:#fff;padding:12px 28px;border-radius:6px;
                    text-decoration:none;font-weight:600;font-size:14px;display:inline-block;">
            Mở tài liệu để phê duyệt
          </a>
        </div>
        <p style="color:#94a3b8;font-size:12px;margin:16px 0 0;text-align:center;">
          Email này được gửi tự động từ hệ thống AssetCore. Vui lòng không trả lời email này.
        </p>
      </div>
    </div>
    """
    safe_sendmail([approver_email], subject, message)
