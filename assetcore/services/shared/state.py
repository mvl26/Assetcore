# Copyright (c) 2026, AssetCore Team
"""Trạng thái tài liệu — ĐƯỜNG GHI DUY NHẤT (ADR-CORE-01).

Mọi chuyển trạng thái phải đi qua module này, để workflow engine của Frappe là nguồn sự
thật duy nhất. Cấm gán thẳng ``doc.status = ...`` hoặc
``frappe.db.set_value(dt, name, "status", ...)`` trong ``services/`` — hai cách đó bỏ qua
kiểm tra vai trò của transition, bỏ qua ``Workflow Action`` (hộp thư duyệt), bỏ qua
Version/audit, và khiến lỗi cấu hình workflow **câm lặng**. Ngân sách nợ cũ được siết dần
bởi ``tests/test_state_axis_invariant.py``.

Cung cấp 3 thứ:

  1. ``transition(doc, action)`` — áp một hành động workflow theo TÊN hành động.
  2. ``transition_to(doc, target_state)`` — áp theo TRẠNG THÁI ĐÍCH; tự tra tên hành
     động từ workflow. Dùng khi di trú code cũ vốn viết ``doc.status = <đích>``.
  3. ``allowed_next_states(doc)`` — danh sách trạng thái kế tiếp mà NGƯỜI DÙNG HIỆN TẠI
     được phép chuyển tới, sinh từ engine. Thay cho các bảng ``_*_VALID_TRANSITIONS``
     chép tay ở từng module (75 chỗ tính tới 2026-07-22).

⚠️ **Bẫy quan trọng khi di trú:** ``frappe.model.workflow.apply_workflow`` gọi
``doc.load_from_db()`` ⇒ MỌI thay đổi in-memory chưa lưu sẽ bị VỨT BỎ. Vì vậy thứ tự
đúng luôn là: gán các field nghiệp vụ → ``doc.save()`` → rồi mới ``transition_to(...)``.
Nếu làm ngược, dữ liệu người dùng nhập biến mất mà không có lỗi nào được ném ra.
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.workflow import (
    apply_workflow,
    get_transitions,
    get_workflow_name,
    get_workflow_state_field,
)

from assetcore.services.shared.errors import ServiceError
from assetcore.services.shared.constants import ErrorCode

# ─────────────────────────────────────────────────────────────────────────────
# Rollup — 2 doctype có từ vựng `status` KHÁC tên state của workflow
# ─────────────────────────────────────────────────────────────────────────────
# 10/12 doctype vận hành có `status` TRÙNG KHỚP hoàn toàn tên state ⇒ rollup = chính
# state, không cần khai. Chỉ 2 ngoại lệ dưới đây cần ánh xạ, và ánh xạ nằm ĐÚNG MỘT CHỖ
# này (ADR-CORE-01 §Quyết định điểm 4).
ROLLUP_MAP: dict[str, dict[str, str]] = {
    # `status` là tóm tắt cấp cao cho người dùng nghiệp vụ; workflow chi tiết hơn.
    # 'Overdue' KHÔNG xuất hiện ở đây vì nó suy từ THỜI HẠN, không suy từ trạng thái —
    # phần tính quá hạn giữ nguyên chỗ cũ, rollup không được ghi đè nó.
    "IMM CAPA Record": {
        "Open": "Open",
        "Investigating": "In Progress",
        "Action Plan": "In Progress",
        "Implementation": "In Progress",
        "Verification": "Pending Verification",
        "Closed": "Closed",
        "Re-opened": "Open",
    },
    # `AC Asset.status` là enum registry CŨ, thiếu 3 giá trị mà vòng đời có
    # (Draft/Commissioned/Under Maintenance). Ánh xạ dưới đây thu gọn CÓ CHỦ ĐÍCH:
    # chưa đưa vào sử dụng → 'Submitted'; đang bảo trì vẫn coi là 'Active' vì enum cũ
    # không có giá trị tương ứng và thiết bị vẫn thuộc biên chế đang dùng.
    "AC Asset": {
        "Draft": "Submitted",
        "Commissioned": "Submitted",
        "Active": "Active",
        "Under Maintenance": "Active",
        "Under Repair": "Under Repair",
        "Calibrating": "Calibrating",
        "Out of Service": "Out of Service",
        "Decommissioned": "Decommissioned",
    },
}


def rollup_status(doctype: str, state: str) -> str:
    """Giá trị `status` dẫn xuất từ trạng thái workflow.

    Doctype không khai trong ``ROLLUP_MAP`` ⇒ `status` chính là state (ánh xạ 1-1).
    State lạ ⇒ trả nguyên state thay vì rỗng, để lỗi lộ ra chứ không âm thầm xoá trạng
    thái đang hiển thị cho người dùng.
    """
    return ROLLUP_MAP.get(doctype, {}).get(state, state)


def rollup_coverage_gaps() -> list[str]:
    """State workflow chưa có ánh xạ rollup — dùng cho test bất biến.

    Bảng ánh xạ thiếu một state nghĩa là tới ngày state đó xảy ra, `status` sẽ nhận giá
    trị ngoài enum và bị Frappe chặn khi lưu. Phải phát hiện bằng test, không phải bằng
    sự cố production.
    """
    gaps: list[str] = []
    for doctype, mapping in ROLLUP_MAP.items():
        workflow_name = get_workflow_name(doctype)
        if not workflow_name:
            gaps.append(f"{doctype}: không có workflow active để đối chiếu rollup")
            continue
        states = frappe.get_all(
            "Workflow Document State",
            filters={"parent": workflow_name},
            pluck="state",
        )
        for state in states:
            if state not in mapping:
                gaps.append(f"{doctype}: state '{state}' chưa có trong ROLLUP_MAP")
    return gaps


# ─────────────────────────────────────────────────────────────────────────────
# Đọc trạng thái
# ─────────────────────────────────────────────────────────────────────────────
def state_field(doctype: str) -> str:
    """Tên field giữ trạng thái workflow của doctype (vd 'workflow_state').

    KHÔNG mặc định 'workflow_state': ``AC Asset`` bind vào ``lifecycle_status``, đoán sai
    sẽ đọc nhầm field và cho ra danh sách hành động rỗng mà không báo lỗi.
    """
    workflow_name = get_workflow_name(doctype)
    if not workflow_name:
        return ""
    return get_workflow_state_field(workflow_name) or "workflow_state"


def current_state(doc) -> str:
    field = state_field(doc.doctype)
    return (doc.get(field) or "") if field else ""


def allowed_next_states(doc) -> list[str]:
    """Trạng thái kế tiếp NGƯỜI DÙNG HIỆN TẠI được phép chuyển tới.

    Sinh từ ``get_transitions`` nên đã lọc theo vai trò và điều kiện của transition ⇒
    nút hiển thị ở giao diện khớp đúng thứ bấm được. Doctype không có workflow, hoặc
    bản ghi chưa có trạng thái, trả rỗng thay vì ném lỗi (khối phụ trợ không được làm
    vỡ màn hình).
    """
    if not get_workflow_name(doc.doctype):
        return []
    try:
        transitions = get_transitions(doc, raise_exception=True)
    except Exception:
        return []
    seen: list[str] = []
    for t in transitions:
        if t.get("next_state") and t["next_state"] not in seen:
            seen.append(t["next_state"])
    return seen


def allowed_actions(doc) -> list[dict]:
    """[{action, next_state}] — dùng khi giao diện cần hiện ĐÚNG nhãn nút của workflow."""
    if not get_workflow_name(doc.doctype):
        return []
    try:
        transitions = get_transitions(doc, raise_exception=True)
    except Exception:
        return []
    return [
        {"action": t.get("action"), "next_state": t.get("next_state")}
        for t in transitions
    ]


def action_for(doc, target_state: str) -> str:
    """Tên hành động workflow đưa ``doc`` từ trạng thái hiện tại tới ``target_state``.

    Chuỗi rỗng = không có đường đi hợp lệ CHO NGƯỜI DÙNG NÀY (có thể do thiếu vai trò,
    hoặc do transition không tồn tại — hai nguyên nhân khác nhau, xem ``transition_to``).
    """
    for t in allowed_actions(doc):
        if t["next_state"] == target_state:
            return t["action"] or ""
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Ghi trạng thái
# ─────────────────────────────────────────────────────────────────────────────
def _apply(doc, action: str):
    """``apply_workflow`` có bật cờ ``in_workflow_apply``.

    Vì sao cần cờ: controller ``AC Asset._validate_lifecycle_status_guard`` (BR-00-02)
    chặn mọi thay đổi trục trạng thái KHÔNG đến từ workflow. Nó nhận diện workflow bằng
    ``form_dict['cmd'].endswith('apply_workflow')`` — tức chỉ đúng khi lời gọi đi qua
    HTTP. Gọi từ mã phía máy chủ (service, patch, scheduler) thì không có ``cmd`` nên bị
    chặn oan, dù đây CHÍNH LÀ đường đi hợp lệ mà ADR-CORE-01 yêu cầu.

    Cờ ``in_workflow_apply`` là cửa thoát đã có sẵn trong chính guard đó. Đặt lại giá trị
    cũ trong ``finally`` để không rò trạng thái sang phần còn lại của request.
    """
    previous = frappe.flags.get("in_workflow_apply")
    frappe.flags.in_workflow_apply = True
    try:
        return apply_workflow(doc, action)
    finally:
        frappe.flags.in_workflow_apply = previous


def transition(doc, action: str):
    """Áp một hành động workflow theo TÊN hành động.

    ⚠️ ``apply_workflow`` nạp lại bản ghi từ CSDL — hãy ``doc.save()`` trước nếu còn
    thay đổi chưa lưu (xem ghi chú đầu module).
    """
    return _apply(doc, action)


def transition_to(doc, target_state: str):
    """Chuyển ``doc`` sang ``target_state`` qua workflow engine.

    Đây là hàm thay thế trực tiếp cho lối viết cũ ``doc.status = <đích>``: giữ nguyên ý
    định "đi tới trạng thái này", nhưng đi qua engine nên được kiểm tra vai trò, sinh
    ``Workflow Action``, cập nhật ``docstatus`` và ghi vết đầy đủ.

    Raises:
        ServiceError: không có đường đi hợp lệ. Thông điệp phân biệt rõ hai nguyên nhân
            — *không có transition nào* (lỗi cấu hình) và *có nhưng người dùng không đủ
            quyền* — để người dùng không phải đoán vì sao nút không ăn.
    """
    if not get_workflow_name(doc.doctype):
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            _("{0} chưa gắn quy trình duyệt nên không thể chuyển trạng thái.").format(
                _(doc.doctype)
            ),
            http_status=409,
        )

    action = action_for(doc, target_state)
    if action:
        return _apply(doc, action)

    # Không đi được: tách nguyên nhân để thông báo có ích.
    all_next = [
        t.next_state
        for t in frappe.get_doc("Workflow", get_workflow_name(doc.doctype)).transitions
        if t.state == current_state(doc)
    ]
    if target_state in all_next:
        raise ServiceError(
            ErrorCode.FORBIDDEN,
            _("Bạn không có quyền chuyển {0} sang trạng thái '{1}'.").format(
                _(doc.doctype), _(target_state)
            ),
            http_status=403,
        )
    raise ServiceError(
        ErrorCode.BAD_STATE,
        _("Không thể chuyển {0} từ '{1}' sang '{2}'.").format(
            _(doc.doctype), _(current_state(doc) or "—"), _(target_state)
        ),
        http_status=409,
    )
