# Copyright (c) 2026, AssetCore Team
"""Notification Framework (Wave N1) — Tier 2 Service Layer.

Bắn thông báo 2 kênh khi có sự kiện vòng đời liên quan trực tiếp tới user:
  - In-app: Frappe Notification Log (chuông góc phải) qua
    `enqueue_create_notification(users, doc)` — Frappe core, đã là record/audit.
  - Email:  `frappe.sendmail` (qua `_safe_sendmail`) CHỈ khi user bật email
    (Frappe Notification Settings.enable_email_notifications).

Frappe-first: KHÔNG modify core, KHÔNG DocType mới. Tái dùng Notification Log +
Notification Settings. Logic recipient-resolution + email-toggle nằm ở service,
KHÔNG ở controller (CLAUDE.md §15).

Spec: docs/imm-00/04_Backend_Design.md §III.1b.
"""
from __future__ import annotations

import frappe
from frappe.desk.doctype.notification_log.notification_log import (
    enqueue_create_notification,
)
from frappe.desk.doctype.notification_settings.notification_settings import (
    is_email_notifications_enabled,
    is_notifications_enabled,
)
from frappe.utils.user import get_users_with_role

from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.services.shared.permissions import is_admin
from assetcore.utils.helpers import _safe_sendmail

# Nhãn tiếng Việt cho severity sự cố — tránh rò chuỗi English ("Medium", …) vào
# nội dung thông báo VI (FE đã có INCIDENT_SEVERITY_LABEL; BE giữ map riêng vì BE
# là nguồn sinh nội dung notification). Giá trị lạ → trả nguyên văn (an toàn).
_SEVERITY_VI: dict[str, str] = {
    "Critical": "Nghiêm trọng",
    "High": "Cao",
    "Medium": "Trung bình",
    "Low": "Thấp",
}


def _severity_vi(value: str | None) -> str:
    """Dịch severity sang nhãn VI; None/giá trị lạ → nguyên văn."""
    if not value:
        return ""
    return _SEVERITY_VI.get(value, value)

# ─── Approval-pending resolution (vòng 2 — sửa root-cause) ──────────────────────
#
# Trước đây E2 hard-code tập tên state ("Pending Approval", "Chờ duyệt", …) +
# resolve approver qua field `supervisor`. Cả 2 workflow Wave-1 KHÔNG có state nào
# trùng tập đó, và Asset Repair không có field `supervisor` → E2 chưa từng kích
# hoạt thật. Thiết kế mới (docs/imm-00/04_Backend_Design.md §III.1b-1):
#   - "State cần duyệt" xác định ĐỘNG từ Workflow metadata: state có ≥1 transition
#     rời nó mà `allowed` role ∈ role phê duyệt của doctype.
#   - Approver = union(user enabled giữ allowed-role phê duyệt) + `supervisor` nếu set.

# Role mặc định coi là "vai trò phê duyệt" khi doctype chưa khai báo riêng.
_DEFAULT_APPROVAL_ROLES: frozenset[str] = frozenset({"System Manager"})

# Cấu hình mở rộng per-doctype (vd thêm "QA Manager" nếu nghiệp vụ cần). Trống =
# dùng _DEFAULT_APPROVAL_ROLES. KHÔNG hard-code tên state ở đây — chỉ role.
_APPROVAL_ROLES: dict[str, frozenset[str]] = {}

# Transition do role phê duyệt nhưng dẫn tới các next_state mang nghĩa HỦY/loại bỏ
# KHÔNG phải hành vi "duyệt" → loại khỏi resolution để tránh false-positive
# (vd "In Progress → Cancelled" do System Manager không có nghĩa state đang chờ duyệt).
_NON_APPROVAL_NEXT_STATES: frozenset[str] = frozenset(
    {"Cancelled", "Cancelled", "Đã hủy", "Rejected", "Từ chối"}
)


def _approval_roles_for(doctype: str) -> frozenset[str]:
    """Tập role phê duyệt áp dụng cho `doctype` (fallback role mặc định)."""
    return _APPROVAL_ROLES.get(doctype) or _DEFAULT_APPROVAL_ROLES


def _is_approval_transition(
    t, approval_roles: frozenset[str], state: str, finalize_states: frozenset[str]
) -> bool:
    """True nếu transition `t` rời `state` là một bước PHÊ DUYỆT (không phải dispatch/hủy).

    Điều kiện (xem docs/imm-00/04_Backend_Design.md §III.1b-1):
      (a) rời đúng `state` và `allowed` role ∈ role phê duyệt;
      (b) `next_state` KHÔNG phải state hủy/từ chối;
      (c) `next_state` là state finalize (doc_status == '1') → chốt phiếu, không phải
          phân công (state đích còn nháp doc_status=0).
    """
    return (
        t.get("state") == state
        and t.get("allowed") in approval_roles
        and t.get("next_state") not in _NON_APPROVAL_NEXT_STATES
        and t.get("next_state") in finalize_states
    )


def _active_workflow(doctype: str):
    """Trả Workflow doc active gắn với `doctype` (None nếu không có).

    Frappe-first: đọc qua `Workflow` (core), KHÔNG đọc JSON file.
    """
    names = frappe.get_all(
        "Workflow",
        filters={"document_type": doctype, "is_active": 1},
        pluck="name",
    )
    if not names:
        return None
    try:
        return frappe.get_doc("Workflow", names[0])
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Notification _active_workflow")
        return None


def _active_workflow_transitions(doctype: str) -> list:
    """Trả transitions của Workflow active gắn với `doctype` (rỗng nếu không có)."""
    wf = _active_workflow(doctype)
    return (wf.transitions or []) if wf else []


def _finalize_states(doctype: str) -> frozenset[str]:
    """Tập state finalize (doc_status == '1', tức submit) của Workflow `doctype`.

    Dùng để phân biệt transition "phê duyệt/chốt phiếu" với "phân công/điều phối"
    (state đích vẫn ở doc_status=0). Đọc từ Workflow State con của Workflow active.
    """
    wf = _active_workflow(doctype)
    if not wf:
        return frozenset()
    return frozenset(
        s.state for s in (wf.states or []) if str(s.get("doc_status")) == "1"
    )


def _state_needs_approval(doctype: str, state: str) -> bool:
    """True nếu `state` là "cần duyệt" theo metadata Workflow của `doctype`.

    Quy ước: tồn tại ≥1 transition rời `state` (transition.state == state) mà
    `allowed` role thuộc tập role phê duyệt của doctype. Tức bước chuyển kế tiếp
    do vai trò quản trị thực hiện ⇒ state hiện tại đang chờ vai trò đó duyệt.

    Args:
        doctype: tên DocType có workflow.
        state: workflow_state hiện tại cần kiểm tra.

    Returns:
        True nếu state cần duyệt; False nếu không (hoặc không có workflow).
    """
    if not doctype or not state:
        return False
    approval_roles = _approval_roles_for(doctype)
    finalize = _finalize_states(doctype)
    for t in _active_workflow_transitions(doctype):
        if _is_approval_transition(t, approval_roles, state, finalize):
            return True
    return False


def resolve_approvers_by_workflow(doc) -> list[str]:
    """Phân giải danh sách approver cho `doc` đang ở state cần duyệt.

    Approver = union của:
      - user enabled đang giữ allowed-role phê duyệt của các transition rời
        `doc.workflow_state` (resolve qua `frappe.utils.user.get_users_with_role`);
      - field `supervisor` trên doc nếu có & set (bổ sung, không thay thế).
    Loại actor hiện tại (`frappe.session.user`) để tránh self-notify (FR-00-NTF-04),
    loại Administrator, và dedupe.

    Args:
        doc: Document có `.doctype` và `.workflow_state`.

    Returns:
        Danh sách user email (không trùng, không gồm actor/Administrator).
    """
    doctype = getattr(doc, "doctype", None)
    state = doc.get("workflow_state") if hasattr(doc, "get") else getattr(doc, "workflow_state", None)
    if not doctype or not state:
        return []

    approval_roles = _approval_roles_for(doctype)
    finalize = _finalize_states(doctype)
    # Role thực sự được dùng trong các transition phê duyệt rời state hiện tại.
    roles_at_state = {
        t.get("allowed")
        for t in _active_workflow_transitions(doctype)
        if _is_approval_transition(t, approval_roles, state, finalize)
    }

    candidates: list[str] = []
    for role in roles_at_state:
        try:
            candidates.extend(get_users_with_role(role))
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Notification resolve_approvers_by_workflow")

    # Bổ sung supervisor nếu doc có field này & set.
    supervisor = doc.get("supervisor") if hasattr(doc, "get") else getattr(doc, "supervisor", None)
    if supervisor:
        candidates.append(supervisor)

    actor = frappe.session.user
    seen: set[str] = set()
    out: list[str] = []
    for u in candidates:
        if u and u != actor and u != "Administrator" and u not in seen:
            seen.add(u)
            out.append(u)
    return out


# ─── Recipient resolution ──────────────────────────────────────────────────────


def resolve_recipients(doc, role_or_field: str, include_self: bool = False) -> list[str]:
    """Phân giải danh sách user nhận thông báo từ một field user trên `doc`.

    Mặc định loại bỏ actor hiện tại (`frappe.session.user`) để tránh tự-thông-báo
    (FR-00-NTF-04), và loại các giá trị rỗng/None. Trả về list email duy nhất.

    Self-confirm (FR-00-NTF-07, §III.1b-2b): với event mà người báo chính là bên
    cần được xác nhận đã ghi nhận (cụ thể: nhánh fallback `reported_by` của
    `notify_incident_created` khi chưa phân công ai), caller truyền
    `include_self=True` để GIỮ actor lại. Đây là opt-in có kiểm soát — mặc định
    `False` ⇒ hành vi cũ KHÔNG đổi, mọi caller hiện hữu an toàn.

    Args:
        doc: Document (hoặc đối tượng có `.get(field)`).
        role_or_field: tên field chứa user (vd "assigned_to", "supervisor").
        include_self: True → giữ actor trong kết quả (self-confirm). Mặc định False.

    Returns:
        Danh sách user email (không trùng; loại actor trừ khi include_self=True).
    """
    actor = frappe.session.user
    candidate = doc.get(role_or_field) if hasattr(doc, "get") else getattr(doc, role_or_field, None)
    recipients = [candidate] if candidate else []
    seen: set[str] = set()
    out: list[str] = []
    for u in recipients:
        if not u or u in seen:
            continue
        if u == actor and not include_self:
            continue
        seen.add(u)
        out.append(u)
    return out


def _user_wants_email(user: str) -> bool:
    """True nếu user bật nhận email (Notification Settings.enable_email_notifications).

    Dùng helper Frappe core: default True khi user chưa có settings (Frappe tạo
    Notification Settings lazily). `enabled=0` (tắt toàn bộ notification) cũng
    coi như không gửi email.
    """
    if not user or user == "Administrator":
        # Administrator là system account — không spam email.
        return False
    try:
        if not is_notifications_enabled(user):
            return False
        return bool(is_email_notifications_enabled(user))
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Notification _user_wants_email")
        return False


# ─── Email HTML template (vòng 4 — §III.1b-3) ────────────────────────────────────


def _deep_link(doc) -> str | None:
    """URL desk Frappe-native tới record (`/app/<doctype>/<name>`) hoặc None.

    Dùng `frappe.utils.get_url_to_form` (core). Trả None nếu doc thiếu doctype/name
    hoặc sinh URL lỗi — KHÔNG được làm vỡ `_dispatch` (email vẫn gửi, chỉ thiếu nút).

    Lý do dùng desk URL thay vì route FE Vue: SPA decoupled không có route ổn định
    cho mọi doctype; desk form luôn hợp lệ cho user Frappe đã đăng nhập.
    """
    document_type = getattr(doc, "doctype", None)
    document_name = getattr(doc, "name", None)
    if not document_type or not document_name:
        return None
    try:
        from frappe.utils import get_url_to_form

        return get_url_to_form(document_type, document_name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Notification _deep_link")
        return None


def _render_email(subject: str, body_html: str, doc) -> str:
    """Dựng HTML email tái sử dụng cho CẢ 4 event (E1..E4).

    Cấu trúc (inline CSS — email client không đọc `<style>` ngoài):
      - Header: dải tiêu đề chứa `subject`.
      - Body: `body_html` nguyên văn (giữ `<b>` mà listener đã dựng).
      - Deep-link: nút "Mở phiếu" tới `get_url_to_form(doctype, name)` nếu doc có
        cả doctype+name; bỏ qua nếu không (doc rời rạc) — không vỡ.
      - Footer: branding nhẹ "AssetCore" + lưu ý có thể tắt email trong Cài đặt.

    KHÔNG hard-code nội dung nghiệp vụ: subject/body do từng listener truyền vào.
    KHÔNG escape `body_html` (do listener kiểm soát, không phải user input tự do).
    Plain-text fallback do Frappe core tự sinh từ HTML này (`set_html_as_text` →
    `to_markdown`) khi gửi qua `frappe.sendmail` — KHÔNG cần text_content thủ công.

    Args:
        subject: tiêu đề thông báo (hiển thị ở header).
        body_html: nội dung thân (HTML inline, đã do listener dựng).
        doc: Document/đối tượng có thể có `.doctype` + `.name` (cho deep-link).

    Returns:
        Chuỗi HTML hoàn chỉnh (tài liệu `<html>...`).

    Spec: docs/imm-00/04_Backend_Design.md §III.1b-3.
    """
    link = _deep_link(doc)
    button_html = ""
    if link:
        button_html = (
            f'<tr><td style="padding:16px 0 4px 0;">'
            f'<a href="{link}" '
            f'style="display:inline-block;background:#1a56db;color:#ffffff;'
            f'text-decoration:none;padding:10px 20px;border-radius:6px;'
            f'font-weight:600;font-size:14px;">Mở phiếu</a>'
            f"</td></tr>"
        )

    return (
        '<html><body style="margin:0;padding:0;background:#f3f4f6;'
        'font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="background:#f3f4f6;padding:24px 0;"><tr><td align="center">'
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'style="background:#ffffff;border-radius:8px;overflow:hidden;'
        'border:1px solid #e5e7eb;">'
        # Header
        '<tr><td style="background:#eff6ff;border-bottom:1px solid #dbeafe;'
        'padding:20px 28px;">'
        f'<div style="font-size:16px;font-weight:700;color:#1e3a8a;">{subject}</div>'
        "</td></tr>"
        # Body + optional button
        '<tr><td style="padding:24px 28px;color:#374151;font-size:14px;'
        'line-height:1.6;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        f"<tr><td>{body_html}</td></tr>"
        f"{button_html}"
        "</table>"
        "</td></tr>"
        # Footer
        '<tr><td style="background:#f9fafb;border-top:1px solid #e5e7eb;'
        'padding:16px 28px;color:#9ca3af;font-size:12px;line-height:1.5;">'
        "<b>AssetCore</b> — Hệ thống quản lý vòng đời thiết bị y tế.<br>"
        "Đây là email tự động; bạn có thể tắt nhận email trong Cài đặt thông báo."
        "</td></tr>"
        "</table></td></tr></table></body></html>"
    )


# ─── Dispatch (2 kênh) ──────────────────────────────────────────────────────────


def _dispatch(users: list[str], subject: str, message: str, doc) -> None:
    """Bắn thông báo cho danh sách user qua 2 kênh.

    - In-app (luôn): tạo Notification Log type=Alert (Frappe enqueue/realtime),
      `email_content` giữ `message` ngắn (hiển thị trên chuông).
    - Email (per-user): chỉ user có `_user_wants_email(user)` True. Body email là
      HTML có cấu trúc + deep-link dựng qua `_render_email(subject, message, doc)`
      (vòng 4 — §III.1b-3); Frappe core tự sinh plain-text fallback từ HTML.

    Notification Log là record bất biến → audit trail tự nhiên (FR-00-NTF-03).
    """
    users = [u for u in dict.fromkeys(users) if u]  # dedupe, drop empty
    if not users:
        return

    document_type = getattr(doc, "doctype", None)
    document_name = getattr(doc, "name", None)

    # Kênh 1 — In-app (chuông). enqueue_create_notification tự lọc user disabled.
    enqueue_create_notification(
        users,
        {
            "subject": subject,
            "email_content": message,
            "type": "Alert",
            "document_type": document_type,
            "document_name": document_name,
            "from_user": frappe.session.user,
        },
    )

    # Kênh 2 — Email (chỉ user bật). HTML có cấu trúc + deep-link tới record.
    # Vòng 5: truyền reference_doctype/name của doc → email AssetCore truy nguyên
    # được trong Email Queue (audit linkage cho KPI delivery, §III.1b-4). Doc rời
    # rạc không có name → bỏ reference (không vỡ).
    email_html = _render_email(subject, message, doc)
    ref_kwargs: dict[str, str] = {}
    if document_type and document_name:
        ref_kwargs["reference_doctype"] = document_type
        ref_kwargs["reference_name"] = document_name
    for user in users:
        if _user_wants_email(user):
            _safe_sendmail(
                recipients=[user], subject=subject, message=email_html, **ref_kwargs
            )

    # Kênh 3 — Push FCM (EPIC-D / D6). 1 điểm fan-out phủ cả 7 event — KHÔNG sửa
    # call-site. Fail-safe BẮT BUỘC: try/except bọc TOÀN BỘ push (pattern
    # _safe_sendmail) — FCM lỗi/raise/creds-thiếu KHÔNG vỡ kênh 1 in-app + kênh 2
    # email (bất biến §1.3). Tái dùng `users` (đã dedupe :377) + document_type/name.
    _dispatch_push(users, subject, message, document_type, document_name, doc)


# ─── Kênh 3 — Push FCM (EPIC-D / D6) ─────────────────────────────────────────────


def _push_event_route(doc) -> tuple[str, str, str]:
    """Suy ra (event, deeplink, priority) từ `doc.doctype` — §5.5 (BA chốt D6).

    Chữ-ký `_dispatch` CHỈ thấy `doc` (KHÔNG thấy mã E#); bất biến "1 điểm fan-out,
    KHÔNG sửa 7 call-site" cấm thêm tham số `event`. Vậy suy `(event, deeplink)` từ
    `doc.doctype` qua bảng map thuần — đủ E3 MVP, fallback an toàn cho doctype khác.

    Map (EPIC-D §5.4/§5.5):
      - Incident Report  → incident_created → assetcore://incident/<name> → high
      - Asset Repair     → repair_assigned  → assetcore://wo/cm/<name>    → high
      - PM Work Order    → pm_assignment    → assetcore://wo/pm/<name>    → normal
      - AC Asset         → calibration_due  → assetcore://asset/<name>    → normal
      - (khác / name rỗng) → notification   → "" (bỏ deeplink)            → normal

    Returns:
        (event, deeplink, priority). `deeplink` rỗng "" ⇒ caller BỎ key khỏi `data`
        (APK mở inbox mặc định). KHÔNG raise (total-function fail-safe §1.3).
    """
    doctype = getattr(doc, "doctype", None)
    name = getattr(doc, "name", None)

    _ROUTES: dict[str, tuple[str, str, str]] = {
        "Incident Report": ("incident_created", "assetcore://incident/{name}", "high"),
        "Asset Repair": ("repair_assigned", "assetcore://wo/cm/{name}", "high"),
        "PM Work Order": ("pm_assignment", "assetcore://wo/pm/{name}", "normal"),
        "AC Asset": ("calibration_due", "assetcore://asset/{name}", "normal"),
    }
    route = _ROUTES.get(doctype or "")
    if not route or not name:
        # Fallback an toàn: doctype không khớp HOẶC name rỗng → bỏ deeplink.
        return "notification", "", "normal"
    event, deeplink_tpl, priority = route
    return event, deeplink_tpl.format(name=name), priority


def _dispatch_push(
    users: list[str],
    subject: str,
    message: str,
    document_type: str | None,
    document_name: str | None,
    doc,
) -> None:
    """Kênh 3 — gửi push FCM tới MỌI device-token enabled=1 của từng recipient.

    Fail-safe BẮT BUỘC (§1.3): toàn bộ thân bọc try/except + log_error — push lỗi/
    raise/creds-thiếu KHÔNG được vỡ kênh 1 in-app + kênh 2 email (đã chạy xong trước
    khi gọi hàm này). Per user → tra `AC Mobile Device Token` enabled=1 → mỗi token
    gọi `send_fcm_message`. User KHÔNG có token enabled=1 → skip im lặng. Creds chưa
    set (D3) → `send_fcm_message` trả None no-op → push skip, in-app/email VẪN gửi.

    Payload (§5.3): title=subject strip-HTML, body=message strip-HTML cắt ≤1000,
    data={doctype, name, event, deeplink} dựng từ `_push_event_route(doc)` (§5.5).

    Args:
        users: recipient list ĐÃ dedupe (tái dùng :377).
        subject/message: nội dung gốc (sẽ strip-HTML).
        document_type/document_name: routing keys (:381-382).
        doc: nguồn suy `event`/`deeplink` theo doctype.
    """
    try:
        from frappe.utils import strip_html

        from assetcore.utils.fcm import send_fcm_message

        title = strip_html(subject or "")
        body = strip_html(message or "")[:1000]
        event, deeplink, priority = _push_event_route(doc)

        data: dict[str, str] = {"event": event}
        if document_type:
            data["doctype"] = document_type
        if document_name:
            data["name"] = document_name
        if deeplink:
            data["deeplink"] = deeplink
        if priority and priority != "high":
            # `_build_message` mặc định priority='high'; chỉ truyền hint khi hạ.
            data["_priority"] = priority

        for user in users:
            tokens = frappe.get_all(
                "AC Mobile Device Token",
                filters={"user": user, "enabled": 1},
                pluck="fcm_token",
            )
            for token in tokens:
                if token:
                    send_fcm_message(token, title=title, body=body, data=data)
    except Exception:
        # Fail-safe: push KHÔNG được làm vỡ kênh 1/2. Log full traceback (LL-BE-20).
        frappe.log_error(frappe.get_traceback(), "Notification _dispatch_push (FCM)")


# ─── E1: notify_assignment ───────────────────────────────────────────────────────


def notify_assignment(doc, method: str | None = None) -> None:
    """Hook listener: WO được gán cho kỹ thuật viên → thông báo assignee.

    Wired: PM Work Order + Asset Repair on_update + on_submit (hooks.py).

    Idempotent: nếu `assigned_to` không đổi so với bản trước khi lưu → skip.
    Skip self-assign (assignee == actor). Bỏ qua doc đã cancel (docstatus=2).

    Signature `(doc, method=None)` bắt buộc cho doc_events (LL-BE-6).
    """
    try:
        if getattr(doc, "docstatus", 0) == 2:
            return

        assignee = doc.get("assigned_to") if hasattr(doc, "get") else getattr(doc, "assigned_to", None)
        if not assignee:
            return

        # Idempotent: chỉ bắn khi assigned_to thực sự đổi.
        before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
        if before is not None:
            prev = before.get("assigned_to") if hasattr(before, "get") else getattr(before, "assigned_to", None)
            if prev == assignee:
                return

        recipients = resolve_recipients(doc, "assigned_to")
        if not recipients:
            return

        doctype = getattr(doc, "doctype", "Work Order")
        name = getattr(doc, "name", "")
        subject = f"Bạn được phân công: {doctype} {name}"
        message = (
            f"Bạn vừa được phân công cho phiếu <b>{doctype} {name}</b>. "
            f"Vui lòng kiểm tra và xử lý."
        )
        _dispatch(recipients, subject, message, doc)
    except Exception:
        # Listener KHÔNG được làm vỡ luồng save chính; log full traceback (LL-BE-20).
        frappe.log_error(frappe.get_traceback(), "Notification notify_assignment")


# ─── E2: notify_approval_pending ─────────────────────────────────────────────────


def notify_approval_pending(doc, method: str | None = None) -> None:
    """Hook listener: doc chuyển VÀO state cần duyệt → thông báo người duyệt.

    "State cần duyệt" + approver xác định ĐỘNG từ Workflow metadata
    (`_state_needs_approval` + `resolve_approvers_by_workflow`), KHÔNG hard-code
    tên state/field. Bỏ qua doc đã cancel (docstatus=2). Idempotent: chỉ bắn khi
    `workflow_state` thực sự đổi (so `get_doc_before_save()`).

    Signature `(doc, method=None)` bắt buộc cho doc_events (LL-BE-6).
    """
    try:
        if getattr(doc, "docstatus", 0) == 2:
            return

        doctype = getattr(doc, "doctype", None)
        state = doc.get("workflow_state") if hasattr(doc, "get") else getattr(doc, "workflow_state", None)
        if not state or not _state_needs_approval(doctype, state):
            return

        # Chỉ bắn khi vừa chuyển VÀO state này (tránh lặp ở mỗi lần save).
        before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
        if before is not None:
            prev = before.get("workflow_state") if hasattr(before, "get") else getattr(before, "workflow_state", None)
            if prev == state:
                return

        recipients = resolve_approvers_by_workflow(doc)
        if not recipients:
            return

        doctype = getattr(doc, "doctype", "Work Order")
        name = getattr(doc, "name", "")
        subject = f"Cần duyệt: {doctype} {name}"
        message = (
            f"Phiếu <b>{doctype} {name}</b> đang chờ bạn phê duyệt "
            f"(trạng thái: {state})."
        )
        _dispatch(recipients, subject, message, doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Notification notify_approval_pending")


# ─── E3: notify_incident_created (vòng 3 — IMM-12) ───────────────────────────────


def notify_incident_created(doc, method: str | None = None) -> None:
    """Hook listener: Incident Report vừa được tạo → thông báo người phụ trách.

    Wired: `Incident Report` after_insert (hooks.py). Vì after_insert chỉ chạy
    đúng 1 lần/record nên KHÔNG cần idempotent-by-before-save; vẫn skip doc đã
    cancel (docstatus=2) cho an toàn.

    Recipient (động, FR-00-NTF-04): `assigned_to` nếu đã phân công; fallback
    `reported_by` để sự cố không "rơi". `resolve_recipients` đã loại self-notify
    + dedupe. Audit = Notification Log (Frappe core).

    Signature `(doc, method=None)` bắt buộc cho doc_events (LL-BE-6). Spec:
    docs/imm-00/04_Backend_Design.md §III.1b-2.
    """
    try:
        if getattr(doc, "docstatus", 0) == 2:
            return

        # Nhánh cross-assign: có người phụ trách → họ nhận "cần xử lý"
        # (loại actor như cũ — self-assign noise vẫn bị chặn, FR-00-NTF-04).
        recipients = resolve_recipients(doc, "assigned_to")
        self_confirm = False
        assigned_to = doc.get("assigned_to") if hasattr(doc, "get") else getattr(doc, "assigned_to", None)
        # Self-confirm CHỈ khi THỰC SỰ chưa phân công ai (assigned_to rỗng) — KHÔNG
        # áp khi assigned_to đã set (kể cả tự gán mình: đó là cross-assign, vẫn
        # bị chặn để tránh noise — TC-NTF-16). §III.1b-2b điểm 2.
        if not recipients and not assigned_to:
            # Fallback reported_by: chưa phân công ai → người TỰ báo nhận xác nhận
            # (self-confirm, FR-00-NTF-07 / §III.1b-2b).
            recipients = resolve_recipients(doc, "reported_by", include_self=True)
            self_confirm = frappe.session.user in recipients
        if not recipients:
            return

        name = getattr(doc, "name", "")
        severity = doc.get("severity") if hasattr(doc, "get") else getattr(doc, "severity", None)
        asset = doc.get("asset") if hasattr(doc, "get") else getattr(doc, "asset", None)

        if self_confirm:
            # Ngữ nghĩa XÁC NHẬN cho chính người báo — không phải "cần xử lý".
            subject = f"Đã ghi nhận sự cố: {name}"
            message = (
                f"Sự cố <b>{name}</b> bạn vừa báo đã được ghi nhận"
                + (f" trên thiết bị <b>{asset}</b>" if asset else "")
                + (f" (mức độ: {_severity_vi(severity)})" if severity else "")
                + ". Bộ phận kỹ thuật sẽ tiếp nhận xử lý."
            )
        else:
            severity_label = _severity_vi(severity) or "Chưa phân loại"
            subject = f"Sự cố mới [{severity_label}]: {name}"
            message = (
                f"Sự cố <b>{name}</b> vừa được ghi nhận"
                + (f" trên thiết bị <b>{asset}</b>" if asset else "")
                + (f" (mức độ: {_severity_vi(severity)})" if severity else "")
                + ". Vui lòng kiểm tra và xử lý."
            )
        _dispatch(recipients, subject, message, doc)
    except Exception:
        # Listener KHÔNG được làm vỡ luồng insert; log full traceback (LL-BE-20).
        frappe.log_error(frappe.get_traceback(), "Notification notify_incident_created")


# ─── E4: notify_calibration_due (vòng 3 — IMM-11, scheduler-driven) ──────────────

# Status calibration mà khi CHUYỂN VÀO sẽ phát thông báo escalation.
from assetcore.services.shared.constants import CalibrationStatus

_CALIBRATION_ALERT_STATES: frozenset[str] = frozenset(
    {CalibrationStatus.DUE_SOON, CalibrationStatus.OVERDUE}
)


def notify_calibration_due(asset_name: str, old_status: str, new_status: str) -> None:
    """Báo người phụ trách khi `calibration_status` của asset chuyển VÀO mức cảnh báo.

    Gọi từ scheduler `imm11.check_calibration_expiry` ngay sau khi set status mới.

    Anti-spam state-change guard (BẮT BUỘC): chỉ phát khi
    `old_status != new_status AND new_status ∈ {Due Soon, Overdue}`. Nhờ scheduler
    set status mỗi ngày, điều kiện "chuyển VÀO" đảm bảo mỗi mức escalation chỉ báo
    đúng 1 lần (On Schedule→Due Soon báo 1 lần; Due Soon→Overdue báo lại 1 lần là
    escalation tăng mức; Due Soon→Due Soon KHÔNG báo). Biến thể idempotent-by-state.

    Recipient (động): `responsible_technician` (primary), fallback `custodian` của
    AC Asset. Loại self-notify (actor) + dedupe. Audit = Notification Log.

    Args:
        asset_name: tên AC Asset.
        old_status: calibration_status trước khi scheduler cập nhật.
        new_status: calibration_status sau khi cập nhật.

    Spec: docs/imm-00/04_Backend_Design.md §III.1b-2.
    """
    try:
        if old_status == new_status or new_status not in _CALIBRATION_ALERT_STATES:
            return

        technician = frappe.db.get_value("AC Asset", asset_name, "responsible_technician")
        recipient = technician or frappe.db.get_value("AC Asset", asset_name, "custodian")
        if not recipient:
            return

        actor = frappe.session.user
        recipients = [r for r in dict.fromkeys([recipient]) if r and r != actor]
        if not recipients:
            return

        if new_status == CalibrationStatus.OVERDUE:
            subject = f"QUÁ HẠN hiệu chuẩn: {asset_name}"
            urgency = "đã <b>QUÁ HẠN</b> hiệu chuẩn"
        else:
            subject = f"Sắp đến hạn hiệu chuẩn: {asset_name}"
            urgency = "<b>sắp đến hạn</b> hiệu chuẩn"

        next_date = frappe.db.get_value("AC Asset", asset_name, "next_calibration_date")
        message = (
            f"Thiết bị <b>{asset_name}</b> {urgency}"
            + (f" (hạn: {next_date})" if next_date else "")
            + ". Vui lòng lên lịch hiệu chuẩn."
        )
        doc_like = frappe._dict(doctype="AC Asset", name=asset_name)
        _dispatch(recipients, subject, message, doc_like)
    except Exception:
        # Per-asset an toàn: 1 asset lỗi KHÔNG được dừng cả batch scheduler.
        frappe.log_error(frappe.get_traceback(), "Notification notify_calibration_due")


# ─── E5: notify_escalation (vòng 7 — IMM-08 Halted–Major Failure) ────────────────
#
# Bù khoảng trống E2: E2 chỉ bắt state finalize (doc_status=1) do role quản trị
# (phê duyệt/chốt phiếu). Nhưng PM Workflow có state nguy cấp NHÁP (doc_status=0)
# do role vận hành (PM User) báo lỗi nghiêm trọng — cần cấp quản trị can thiệp để
# gỡ. E5 bắt đúng nhóm state này. Mỗi state thuộc đúng 1 event (E2 nếu finalize,
# E5 nếu nháp + vào-bởi-vận-hành + gỡ-bởi-quản-trị) → KHÔNG double-notify.
#
# LƯU Ý ROOT-CAUSE (vòng 7): KHÔNG dùng Workflow State.type "Danger" để nhận diện
# — field style/type CHỈ có trong JSON fixture, KHÔNG persist DB runtime (Workflow
# Document State child không có field này; Workflow State master lưu style=""). Đọc
# runtime luôn None. Thay bằng tín hiệu CÓ THẬT trong metadata transitions:
# "VÀO bởi role vận hành" + "GỠ bởi role quản trị". Xem §III.1b-5.


def _state_entered_by_operational(doctype: str, state: str) -> bool:
    """True nếu ≥1 transition VÀO `state` do role VẬN HÀNH (không thuộc role quản trị).

    Phân biệt escalation (chính người thực thi đẩy phiếu vào, vd PM User báo lỗi)
    với state khởi tạo (`Open` — không có transition VÀO) hoặc state do quản trị đặt
    (`Overdue` — VÀO bởi System Manager). Đọc Frappe-first qua transitions metadata.
    """
    approval_roles = _approval_roles_for(doctype)
    for t in _active_workflow_transitions(doctype):
        if t.get("next_state") == state and t.get("allowed") not in approval_roles:
            return True
    return False


def _escalation_exit_roles(doctype: str, state: str) -> set[str]:
    """Tập role quản trị có transition GỠ (không hủy) rời `state`.

    "Gỡ" = transition rời `state` do role quản trị (`_approval_roles_for`) mà
    `next_state` KHÔNG thuộc `_NON_APPROVAL_NEXT_STATES` (hủy/từ chối). Đây là vai
    trò cần được báo để can thiệp tích cực (escalation cần gỡ, không phải chỉ hủy).
    """
    approval_roles = _approval_roles_for(doctype)
    out: set[str] = set()
    for t in _active_workflow_transitions(doctype):
        if (
            t.get("state") == state
            and t.get("allowed") in approval_roles
            and t.get("next_state") not in _NON_APPROVAL_NEXT_STATES
        ):
            out.add(t.get("allowed"))
    return out


def _state_is_escalation(doctype: str, state: str) -> bool:
    """True nếu `state` là ESCALATION theo §III.1b-5 (xác định ĐỘNG, không hard-code).

    Điều kiện (CẢ 3, đều đọc từ Workflow metadata CÓ THẬT lúc runtime):
      (a) `state` chưa finalize (`doc_status == "0"`) — phân biệt với E2 (finalize);
      (b) `state` được VÀO bởi ≥1 transition do role VẬN HÀNH (không thuộc role
          quản trị) — chính người thực thi đẩy phiếu vào (báo lỗi), không phải
          state khởi tạo (`Open`) hay state do quản trị đặt (`Overdue`);
      (c) tồn tại ≥1 transition GỠ rời `state` do role quản trị (xem
          `_escalation_exit_roles`) — tức cần cấp quản trị can thiệp tích cực.

    Args:
        doctype: tên DocType có workflow.
        state: workflow_state cần kiểm tra.

    Returns:
        True nếu `state` là escalation; False nếu không (hoặc không có workflow).
    """
    if not doctype or not state:
        return False
    # (a) chưa finalize.
    if state in _finalize_states(doctype):
        return False
    # (b) vào bởi role vận hành (không phải khởi tạo / không phải do quản trị đặt).
    if not _state_entered_by_operational(doctype, state):
        return False
    # (c) có lối gỡ do role quản trị.
    return bool(_escalation_exit_roles(doctype, state))


def resolve_escalation_recipients(doc) -> list[str]:
    """Phân giải người cần báo khi `doc` vào state escalation.

    Recipient = union của:
      - user enabled giữ role quản trị có transition GỠ rời `doc.workflow_state`
        (`_escalation_exit_roles` → `get_users_with_role`);
      - field `supervisor` của doc nếu có & set.
    Loại actor hiện tại (KTV vừa báo lỗi — FR-00-NTF-04), loại Administrator, dedupe.

    Args:
        doc: Document có `.doctype` + `.workflow_state` (+ tùy chọn `.supervisor`).

    Returns:
        Danh sách user email (không trùng, không gồm actor/Administrator).
    """
    doctype = getattr(doc, "doctype", None)
    state = doc.get("workflow_state") if hasattr(doc, "get") else getattr(doc, "workflow_state", None)
    if not doctype or not state:
        return []

    candidates: list[str] = []
    for role in _escalation_exit_roles(doctype, state):
        try:
            candidates.extend(get_users_with_role(role))
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Notification resolve_escalation_recipients")

    supervisor = doc.get("supervisor") if hasattr(doc, "get") else getattr(doc, "supervisor", None)
    if supervisor:
        candidates.append(supervisor)

    actor = frappe.session.user
    seen: set[str] = set()
    out: list[str] = []
    for u in candidates:
        if u and u != actor and u != "Administrator" and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def notify_escalation(doc, method: str | None = None) -> None:
    """Hook listener: WO chuyển VÀO state escalation → báo supervisor + role quản trị.

    Wired: `PM Work Order` on_update (hooks.py). "State escalation" xác định ĐỘNG
    qua Workflow metadata (`_state_is_escalation`), KHÔNG hard-code tên state. Bù
    khoảng trống E2 (state nháp-Danger do role vận hành báo, cần quản trị gỡ).

    Idempotent: chỉ bắn khi `workflow_state` thực sự đổi VÀO state escalation (so
    `get_doc_before_save()`). Bỏ qua doc đã cancel (docstatus=2).

    Signature `(doc, method=None)` bắt buộc cho doc_events (LL-BE-6). Spec:
    docs/imm-00/04_Backend_Design.md §III.1b-5.
    """
    try:
        if getattr(doc, "docstatus", 0) == 2:
            return

        doctype = getattr(doc, "doctype", None)
        state = doc.get("workflow_state") if hasattr(doc, "get") else getattr(doc, "workflow_state", None)
        if not state or not _state_is_escalation(doctype, state):
            return

        # Idempotent: chỉ bắn khi vừa chuyển VÀO state này.
        before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
        if before is not None:
            prev = before.get("workflow_state") if hasattr(before, "get") else getattr(before, "workflow_state", None)
            if prev == state:
                return

        recipients = resolve_escalation_recipients(doc)
        if not recipients:
            return

        name = getattr(doc, "name", "")
        subject = f"Cảnh báo nâng cấp: {doctype} {name}"
        message = (
            f"Phiếu <b>{doctype} {name}</b> vừa chuyển sang trạng thái nguy cấp "
            f"<b>{state}</b> và cần cấp quản lý can thiệp. Vui lòng kiểm tra và xử lý."
        )
        _dispatch(recipients, subject, message, doc)
    except Exception:
        # Listener KHÔNG được làm vỡ luồng save; log full traceback (LL-BE-20).
        frappe.log_error(frappe.get_traceback(), "Notification notify_escalation")


# ─── E6: notify_sla_breach_warning (vòng 8 — IMM-09 Asset Repair, scheduler) ─────
#
# Khoảng trống (xem docs/imm-00/04_Backend_Design.md §III.1b-6): scheduler cũ
# `imm09.check_repair_sla_breach` (a) chưa từng được đăng ký trong scheduler_events;
# (b) chỉ set sla_breached + publish_realtime — KHÔNG đi qua engine (không bell, không
# email theo toggle, không deep-link, không vào KPI); (c) không có tầng "sắp hết hạn";
# (d) không anti-spam. E6 thay thế: 2 tier (WARNING ≥80% & <100%; BREACH ≥100% hoặc
# sla_breached=1), anti-spam state-change (BREACH dùng cờ sla_breached 0→1; WARNING
# dedupe qua Notification Log), tái dùng engine `_dispatch`. Verify data model THẬT:
# Asset Repair có open_datetime (Datetime) + sla_target_hours (Float) → deadline động.

from frappe.utils import get_datetime, now_datetime, time_diff_in_seconds  # noqa: E402

_REPAIR_DOCTYPE: str = "Asset Repair"

# Terminal status (đồng hồ SLA dừng). BR-09-08: ALIAS về SoT DUY NHẤT
# `imm09.REPAIR_TERMINAL_STATES` — KHÔNG định nghĩa frozenset song song. SLA
# engine, KPI thẻ cm_open, persona KTV, drill-down SQL phải chia sẻ CÙNG tập
# (Completed | Cannot Repair | Cancelled), tránh hai nguồn lệch nhau.
from assetcore.services.imm09 import REPAIR_TERMINAL_STATES as _REPAIR_TERMINAL_STATUS  # noqa: E402

# Ngưỡng tier (%). WARNING ≥ WARN_PCT & < 100; BREACH ≥ 100 hoặc sla_breached=1.
_SLA_WARN_PCT: float = 80.0

# Role quản trị Repair được báo khi WO chưa phân công KTV.
_REPAIR_ADMIN_ROLE: str = "Repair Manager"

# Marker subject WARNING — dùng cho dedupe qua Notification Log (Frappe-first).
_SLA_WARN_MARKER: str = "sắp vi phạm SLA"


def _sla_tier(elapsed_h: float, sla_hours: float, sla_breached: int) -> str | None:
    """Phân loại tier SLA cho một WO: 'breach' / 'warning' / None.

    Args:
        elapsed_h: số giờ đã trôi kể từ open_datetime.
        sla_hours: SLA mục tiêu (giờ). <= 0 → None (guard chia-0, không xác định).
        sla_breached: cờ sla_breached hiện tại của WO (0/1).

    Returns:
        'breach' nếu đã quá deadline (pct ≥ 100) hoặc sla_breached đã =1;
        'warning' nếu pct ∈ [WARN_PCT, 100);
        None nếu chưa tới ngưỡng hoặc sla_hours không hợp lệ.

    Spec: docs/imm-00/04_Backend_Design.md §III.1b-6.
    """
    if sla_hours is None or sla_hours <= 0:
        return None
    pct = elapsed_h / sla_hours * 100.0
    if pct >= 100.0 or int(sla_breached or 0) == 1:
        return "breach"
    if pct >= _SLA_WARN_PCT:
        return "warning"
    return None


def _sla_recipients(wo: dict) -> list[str]:
    """Phân giải người cần báo SLA cho một Asset Repair WO.

    Recipient (FR-00-NTF-04): `assigned_to` (KTV đang xử lý) là primary; nếu chưa
    phân công → fallback union(`supervisor` của doc nếu set, user giữ role quản trị
    Repair `_REPAIR_ADMIN_ROLE`). Loại actor hiện tại + Administrator + dedupe.

    Args:
        wo: dict có ít nhất `assigned_to` (+ tùy chọn `supervisor`).

    Returns:
        Danh sách user email (không trùng, không gồm actor/Administrator).
    """
    candidates: list[str] = []
    assignee = wo.get("assigned_to")
    if assignee:
        candidates.append(assignee)
    else:
        supervisor = wo.get("supervisor")
        if supervisor:
            candidates.append(supervisor)
        try:
            candidates.extend(get_users_with_role(_REPAIR_ADMIN_ROLE))
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Notification _sla_recipients")

    actor = frappe.session.user
    seen: set[str] = set()
    out: list[str] = []
    for u in candidates:
        if u and u != actor and u != "Administrator" and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _warning_already_sent(wo_name: str) -> bool:
    """True nếu WARNING SLA đã từng bắn cho WO này (dedupe Frappe-first, không field mới).

    Kiểm tra tồn tại Notification Log type=Alert cho đúng record với subject chứa
    marker WARNING. BREACH KHÔNG dùng hàm này (dùng cờ `sla_breached` rẻ hơn).
    """
    return bool(
        frappe.db.exists(
            "Notification Log",
            {
                "document_type": _REPAIR_DOCTYPE,
                "document_name": wo_name,
                "subject": ("like", f"%{_SLA_WARN_MARKER}%"),
            },
        )
    )


def _emit_sla_notification(wo: dict, tier: str, elapsed_h: float, sla_hours: float) -> None:
    """Dựng subject/message theo tier rồi `_dispatch` (2 kênh) cho recipient của WO."""
    recipients = _sla_recipients(wo)
    if not recipients:
        return

    name = wo.get("name", "")
    pct = round(elapsed_h / sla_hours * 100.0, 1) if sla_hours else 0.0
    doc_like = frappe._dict(doctype=_REPAIR_DOCTYPE, name=name)

    if tier == "breach":
        over_h = round(elapsed_h - sla_hours, 1)
        subject = f"VI PHẠM SLA: Asset Repair {name}"
        message = (
            f"Phiếu sửa chữa <b>{name}</b> đã <b>VI PHẠM SLA</b> "
            f"(đã trôi {pct}% — quá hạn {over_h} giờ). Vui lòng xử lý khẩn."
        )
    else:  # warning
        remain_h = round(sla_hours - elapsed_h, 1)
        subject = f"Sắp vi phạm SLA: Asset Repair {name}"
        message = (
            f"Phiếu sửa chữa <b>{name}</b> <b>{_SLA_WARN_MARKER}</b> "
            f"(đã trôi {pct}%, còn {remain_h} giờ tới hạn). Vui lòng đẩy nhanh xử lý."
        )
    _dispatch(recipients, subject, message, doc_like)


def run_sla_breach_scan() -> None:
    """Scheduler (hourly): quét Asset Repair non-terminal, bắn cảnh báo SLA 2 tier.

    Supersede `imm09.check_repair_sla_breach`: vừa set `sla_breached=1` (giữ tương
    thích dashboard `cm_sla_breached`) vừa bắn notification qua engine.

    Anti-spam (§III.1b-6):
      - BREACH: chỉ bắn khi WO vừa chuyển `sla_breached 0→1` trong lần quét này
        (set cờ đồng thời bắn 1 lần; lần sau cờ đã =1 → skip). Nếu cờ đã =1 từ trước
        → KHÔNG bắn lại (idempotent qua state DB bền vững).
      - WARNING: dedupe qua Notification Log (`_warning_already_sent`).

    Per-WO bọc try/except — 1 WO lỗi KHÔNG dừng cả batch. Spec §III.1b-6.
    """
    try:
        from assetcore.repositories.repair_repo import RepairRepo
        from assetcore.services.imm09 import get_sla_target

        wos, _ = RepairRepo.list(
            filters={
                "status": ("not in", list(_REPAIR_TERMINAL_STATUS)),
                "docstatus": 0,
            },
            fields=[
                "name", "asset_ref", "status", "priority", "risk_class",
                "open_datetime", "sla_target_hours", "sla_breached",
                "assigned_to", "supervisor",
            ],
            page_size=2000,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Notification run_sla_breach_scan list")
        return

    now = now_datetime()
    for wo in wos:
        try:
            open_dt = wo.get("open_datetime")
            if not open_dt:
                continue
            elapsed_h = time_diff_in_seconds(now, get_datetime(open_dt)) / 3600.0
            sla_hours = wo.get("sla_target_hours") or get_sla_target(
                wo.get("risk_class") or "Class I", wo.get("priority") or "Normal"
            )
            tier = _sla_tier(elapsed_h, sla_hours, wo.get("sla_breached"))
            if not tier:
                continue

            if tier == "breach":
                already_breached = int(wo.get("sla_breached") or 0) == 1
                if not already_breached:
                    # State-change 0→1: set cờ (dashboard) + bắn đúng 1 lần.
                    from assetcore.repositories.repair_repo import RepairRepo as _RR

                    _RR.set_values(wo["name"], {"sla_breached": 1})
                    _emit_sla_notification(wo, "breach", elapsed_h, sla_hours)
                # cờ đã =1 từ trước → đã báo, skip (anti-spam).
            else:  # warning
                if not _warning_already_sent(wo["name"]):
                    _emit_sla_notification(wo, "warning", elapsed_h, sla_hours)
        except Exception:
            # Per-WO an toàn: 1 WO lỗi KHÔNG được dừng cả batch scheduler.
            frappe.log_error(
                frappe.get_traceback(), "Notification run_sla_breach_scan wo"
            )


# ─── E7: Incident SLA breach escalation (check_incident_sla_breach, IMM-12) ──────
# ROOT CAUSE (BR-12-09): `imm12.check_incident_sla_breach` (hourly) set cờ
# response_breached/resolution_breached=1 + ghi audit nhưng KHÔNG bắn notification —
# incident quá hạn chìm vào log câm. E7 mirror E6 (Asset Repair) cho Incident Report:
# resolve recipient (assigned_to + escalation_l1/l2_user policy + NĐ98 role gate) rồi
# `_dispatch` 2 kênh. Idempotent qua chính cờ DB (caller chỉ gọi khi 0→1).

_DT_INCIDENT_NOTIF: str = "Incident Report"

# Mức độ Incident yêu cầu gate NĐ98 (Đ67) — thêm QA Officer + Ops Manager vào
# recipient escalation KỂ CẢ khi SLA Policy không set escalation_l*_user.
_INCIDENT_ND98_SEVERITIES: frozenset[str] = frozenset({"Critical", "High"})

# Map severity → nhãn tiếng Việt (subject/message escalation).
_INCIDENT_SEVERITY_VI: dict[str, str] = {
    "Critical": "Nghiêm trọng",
    "High": "Cao",
    "Medium": "Trung bình",
    "Low": "Thấp",
}


def _incident_sla_recipients(incident: dict, severity: str) -> list[str]:
    """Phân giải người nhận escalation SLA cho một Incident (IMM-12).

    Recipient = union (dedupe, loại Administrator + rỗng) của:
      - `incident["assigned_to"]` (primary); trống → fallback `incident["reported_by"]`
        (Incident Report KHÔNG có field `supervisor` — khác Asset Repair WO);
      - `incident["escalation_l1_user"]` / `escalation_l2_user` (đọc từ IMM SLA Policy,
        caller bơm vào dict — TRƯỚC fix imm12 chưa dùng);
      - NĐ98 gate (BR-12-10): severity ∈ {Critical, High} → thêm role-block
        notify_roles.INCIDENT_ESCALATION_QA + INCIDENT_ESCALATION_OPS (resolve qua
        get_users_with_role) — KỂ CẢ khi policy không set escalation user.

    Role-name lấy từ SSoT `notify_roles` (anti RBAC-dead-gate) — KHÔNG literal.
    Trả [] ⇒ caller KHÔNG bắn (set cờ + audit phát hiện như cũ).
    """
    from assetcore.services.shared import notify_roles

    candidates: list[str] = []
    assignee = incident.get("assigned_to")
    if assignee:
        candidates.append(assignee)
    elif incident.get("reported_by"):
        candidates.append(incident["reported_by"])

    for key in ("escalation_l1_user", "escalation_l2_user"):
        val = incident.get(key)
        if val:
            candidates.append(val)

    if severity in _INCIDENT_ND98_SEVERITIES:
        for role in list(notify_roles.INCIDENT_ESCALATION_QA) + list(
            notify_roles.INCIDENT_ESCALATION_OPS
        ):
            try:
                candidates.extend(get_users_with_role(role))
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(), "Notification _incident_sla_recipients"
                )

    seen: set[str] = set()
    out: list[str] = []
    for u in candidates:
        if u and u != "Administrator" and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _emit_incident_sla_notification(
    incident: dict, kind: str, over_hours: float, severity: str
) -> bool:
    """Dựng subject/message tiếng Việt theo loại breach rồi `_dispatch` 2 kênh.

    Args:
        incident: dict có name, asset, assigned_to/reported_by, escalation_l1/l2_user,
            response_due_at/resolution_due_at.
        kind: 'response' (chưa tiếp nhận quá hạn) | 'resolution' (chưa đóng quá hạn).
        over_hours: số giờ đã quá hạn (đã làm tròn 1 chữ số).
        severity: mức độ incident (cho nhãn VI + NĐ98 gate).

    Returns:
        True nếu đã bắn cho ≥1 recipient; False nếu recipient rỗng (KHÔNG bắn rỗng).
    """
    recipients = _incident_sla_recipients(incident, severity)
    if not recipients:
        return False

    name = incident.get("name", "")
    asset = incident.get("asset") or ""
    asset_name = (
        frappe.db.get_value("AC Asset", asset, "asset_name") if asset else None
    ) or asset or "—"
    sev_vi = _INCIDENT_SEVERITY_VI.get(severity, severity)
    doc_like = frappe._dict(doctype=_DT_INCIDENT_NOTIF, name=name)

    if kind == "response":
        due = incident.get("response_due_at")
        subject = f"VI PHẠM SLA (tiếp nhận): Sự cố {name}"
        message = (
            f"Sự cố <b>{name}</b> trên thiết bị <b>{asset_name}</b> CHƯA được "
            f"tiếp nhận và đã quá hạn <b>{over_hours} giờ</b> "
            f"(hạn tiếp nhận: {due}). Mức độ: {sev_vi}. Vui lòng tiếp nhận khẩn."
        )
    else:  # resolution
        due = incident.get("resolution_due_at")
        subject = f"VI PHẠM SLA (xử lý): Sự cố {name}"
        message = (
            f"Sự cố <b>{name}</b> trên thiết bị <b>{asset_name}</b> CHƯA được "
            f"đóng và đã quá hạn xử lý <b>{over_hours} giờ</b> "
            f"(hạn xử lý: {due}). Mức độ: {sev_vi}. Vui lòng xử lý khẩn."
        )

    _dispatch(recipients, subject, message, doc_like)
    return True


# ─── Per-user preferences (API entrypoints) ─────────────────────────────────────


def get_notification_preferences(user: str | None = None) -> dict:
    """Đọc tùy chọn nhận email của user (mặc định = user hiện tại).

    Returns:
        {"email_enabled": bool}
    """
    target = user or frappe.session.user
    return {"email_enabled": bool(is_email_notifications_enabled(target))}


def set_email_enabled(enabled: bool, user: str | None = None) -> dict:
    """Bật/tắt nhận email cho user (mặc định = user hiện tại).

    Chỉ cho phép tự sửa của mình, trừ System Manager mới sửa được user khác.

    Returns:
        {"email_enabled": bool}
    """
    target = user or frappe.session.user
    if target != frappe.session.user and not is_admin():
        raise ServiceError(
            ErrorCode.FORBIDDEN,
            "Chỉ quản trị viên mới sửa được tùy chọn của người dùng khác.",
        )

    if not frappe.db.exists("Notification Settings", target):
        # Frappe tạo lazily; tự tạo để set được giá trị.
        from frappe.desk.doctype.notification_settings.notification_settings import (
            create_notification_settings,
        )

        create_notification_settings(target)

    frappe.db.set_value(
        "Notification Settings", target, "enable_email_notifications", 1 if enabled else 0
    )
    frappe.clear_cache(doctype="Notification Settings")
    return {"email_enabled": bool(enabled)}


# ─── KPI Notification Delivery (vòng 5 — §III.1b-4) ──────────────────────────────
#
# Tập reference_doctype của email do engine AssetCore phát (E1..E4). Dùng để tách
# email AssetCore khỏi email hệ thống khác khi đo delivery rate. Mở rộng khi thêm
# event mới gắn doctype khác.
_NOTIFY_REF_DOCTYPES: frozenset[str] = frozenset(
    {"AC Asset", "Incident Report", "PM Work Order", "Asset Repair"}
)

# Cửa sổ KPI mặc định (ngày).
_KPI_DEFAULT_DAYS: int = 30

# Ngưỡng màu (xem bảng §III.1b-4). delivery: cao = tốt; opt_out: thấp = tốt.
_DELIVERY_GOOD: float = 95.0
_DELIVERY_WARN: float = 80.0
_OPT_OUT_GOOD: float = 10.0
_OPT_OUT_WARN: float = 30.0

# Alias module-level trỏ repository → cho phép test patch (`patch.object(svc, ...)`)
# mà không phụ thuộc Email Queue thật khi test công thức.
from assetcore.repositories.notification_repo import (  # noqa: E402
    count_email_delivery as _count_email_delivery,
    count_email_opt_out as _count_email_opt_out,
)


def _delivery_status(rate: float | None) -> str:
    """Phân loại màu cho delivery_rate: good (≥95%) / warn (80–95%) / bad (<80%) / na."""
    if rate is None:
        return "na"
    if rate >= _DELIVERY_GOOD:
        return "good"
    if rate >= _DELIVERY_WARN:
        return "warn"
    return "bad"


def _opt_out_status(rate: float | None) -> str:
    """Phân loại màu cho opt_out_rate: good (≤10%) / warn (10–30%) / bad (>30%) / na."""
    if rate is None:
        return "na"
    if rate <= _OPT_OUT_GOOD:
        return "good"
    if rate <= _OPT_OUT_WARN:
        return "warn"
    return "bad"


def get_delivery_kpi(days: int = _KPI_DEFAULT_DAYS) -> dict:
    """KPI độ phủ thông báo: delivery rate (email gửi OK) + opt-out rate (user tắt email).

    Chỉ System Manager (KPI quản trị toàn hệ thống) — không phải vendor-scoped.

    Công thức (§III.1b-4):
      - delivery_rate = sent / (sent + failed) × 100; None nếu mẫu rỗng (chia-0 guard).
      - opt_out_rate  = opted_out / total_users × 100; None nếu total_users = 0.
    Nguồn: Email Queue (lọc reference_doctype ∈ `_NOTIFY_REF_DOCTYPES` trong `days`
    ngày) + User/Notification Settings (toàn hệ thống). Đọc qua repository (Tier 3).

    Args:
        days: cửa sổ tính delivery (ngày). Clamp về tối thiểu 1 nếu < 1.

    Returns:
        dict: {delivery_rate, sent, failed, opt_out_rate, total_users, opted_out,
               window_days, delivery_status, opt_out_status}. Các *_status ∈
               {good, warn, bad, na} drive màu KPI card FE.

    Raises:
        ServiceError(FORBIDDEN): nếu user không phải System Manager.
    """
    if not is_admin():
        raise ServiceError(
            ErrorCode.FORBIDDEN,
            "Chỉ quản trị viên hệ thống mới xem được KPI thông báo.",
        )

    days = max(1, int(days))

    delivery = _count_email_delivery(_NOTIFY_REF_DOCTYPES, days)
    opt_out = _count_email_opt_out()

    sent = int(delivery.get("sent", 0) or 0)
    failed = int(delivery.get("failed", 0) or 0)
    total = int(opt_out.get("total_users", 0) or 0)
    opted = int(opt_out.get("opted_out", 0) or 0)

    delivery_total = sent + failed
    delivery_rate = round(sent / delivery_total * 100, 1) if delivery_total else None
    opt_out_rate = round(opted / total * 100, 1) if total else None

    return {
        "delivery_rate": delivery_rate,
        "sent": sent,
        "failed": failed,
        "opt_out_rate": opt_out_rate,
        "total_users": total,
        "opted_out": opted,
        "window_days": days,
        "delivery_status": _delivery_status(delivery_rate),
        "opt_out_status": _opt_out_status(opt_out_rate),
    }
