# Copyright (c) 2026, AssetCore Team
"""Hợp đồng phản hồi FHIR — resource TRẦN + ``OperationOutcome`` (SPEC §6.2, §6.3).

Điểm gãy lớn nhất so với bề mặt hiện tại
----------------------------------------
=================  ==========================================  ==============================
                   ``api/`` (Frappe RPC)                       ``fhir/`` (R4)
=================  ==========================================  ==============================
Thành công         ``{"success": true, "data": {...}}``        resource **trần**
Danh sách          ``{"data": {"rows": [...], "total": N}}``   ``Bundle`` (``searchset``)
Lỗi                ``{"success": false, ...}`` trên **HTTP 200**  ``OperationOutcome`` + status **thật**
=================  ==========================================  ==============================

FHIR **cấm bọc resource**. Vì thế module này KHÔNG dùng — và không được phép
import — ``assetcore.utils.response``. Guard ``tests/guards/test_fhir_no_envelope.py``
khoá luật đó bằng máy.

Chuyện mã lỗi nằm trong thân HTTP 200 là một lỗi đã trả giá thật ở bề mặt cũ: bộ
sinh mã client đọc status-line để định tuyến lỗi, thấy 200 thì coi là thành công
rồi vỡ ở bước parse (ghi trong memory dự án: *in-handler 404/409/422 đến trên
HTTP-200 KHÔNG status-line ⇒ codegen route sai*). Ở nhánh FHIR, status-line là
hợp đồng — :func:`fhir_error` luôn đặt ``frappe.local.response.http_status_code``.
"""

from __future__ import annotations

from typing import Any

import frappe

#: Content-Type bắt buộc của mọi phản hồi FHIR JSON (R4 §3.1.0).
FHIR_JSON = "application/fhir+json"

#: ``ErrorCode`` nội bộ → (HTTP status, ``OperationOutcome.issue.code``).
#:
#: Valueset R4: https://hl7.org/fhir/R4/valueset-issue-type.html
#: Nguồn mã nội bộ: ``assetcore/utils/response.py::ErrorCode`` (15 mã, ánh xạ 1-1,
#: không mất thông tin — SPEC §6.3).
_ISSUE_FOR_CODE: dict[str, tuple[int, str]] = {
    "VALIDATION": (422, "invalid"),
    "VALIDATION_ERROR": (400, "structure"),
    "INVALID_PARAMS": (400, "structure"),
    "BUSINESS_RULE": (422, "business-rule"),
    "COMPLIANCE_BLOCKED": (422, "business-rule"),
    "UNAUTHORIZED": (401, "login"),
    "FORBIDDEN": (403, "forbidden"),
    "NOT_FOUND": (404, "not-found"),
    "CONFLICT": (409, "conflict"),
    "BAD_STATE": (409, "conflict"),
    "DUPLICATE": (409, "duplicate"),
    "PAYLOAD_TOO_LARGE": (413, "too-costly"),
    "RATE_LIMITED": (429, "throttled"),
    "INTERNAL": (500, "exception"),
    "INTERNAL_ERROR": (500, "exception"),
}

#: Mức nghiêm trọng mặc định theo lớp status.
_SEVERITY_FATAL_FROM = 500


def issue_for(code: str) -> tuple[int, str]:
    """Tra (HTTP status, ``issue.code``) cho một ``ErrorCode`` nội bộ.

    Mã lạ được quy về ``500/exception`` — an toàn hơn là đoán, vì đoán sai mã sẽ
    khiến client tự động thử lại một lỗi vĩnh viễn.

    Args:
        code: giá trị ``ErrorCode`` nội bộ, vd ``"NOT_FOUND"``.

    Returns:
        Cặp ``(http_status, issue_code)`` theo valueset ``issue-type`` của R4.
    """
    return _ISSUE_FOR_CODE.get(code, (500, "exception"))


def operation_outcome(
    code: str,
    message: str,
    *,
    diagnostics: str | None = None,
    message_code: str | None = None,
    expression: list[str] | None = None,
) -> dict[str, Any]:
    """Dựng resource ``OperationOutcome`` (R4).

    Tham chiếu: https://hl7.org/fhir/R4/operationoutcome.html

    Câu tiếng Việt sẵn có được giữ nguyên ở ``issue.details.text`` — client hiển
    thị được ngay cho người dùng; ``message_code`` đi vào ``issue.details.coding``
    để máy tra lại registry.

    Args:
        code: ``ErrorCode`` nội bộ.
        message: câu tiếng Việt đã render, dành cho người đọc.
        diagnostics: thông tin kỹ thuật thêm (không hiển thị cho người dùng cuối).
        message_code: khoá vào registry ``utils/messages.py``.
        expression: FHIRPath trỏ tới phần tử gây lỗi, vd ``["Device.status"]``.

    Returns:
        Resource ``OperationOutcome`` dạng dict — TRẦN, không bọc envelope.
    """
    http_status, issue_code = issue_for(code)
    details: dict[str, Any] = {"text": message}
    if message_code:
        details["coding"] = [{
            "system": "http://assetcore.vn/fhir/CodeSystem/message-code",
            "code": message_code,
        }]

    issue: dict[str, Any] = {
        "severity": "fatal" if http_status >= _SEVERITY_FATAL_FROM else "error",
        "code": issue_code,
        "details": details,
    }
    if diagnostics:
        issue["diagnostics"] = diagnostics
    if expression:
        issue["expression"] = expression

    return {"resourceType": "OperationOutcome", "issue": [issue]}


def fhir_error(
    code: str,
    message: str,
    *,
    diagnostics: str | None = None,
    message_code: str | None = None,
    expression: list[str] | None = None,
) -> dict[str, Any]:
    """Trả ``OperationOutcome`` **và đặt HTTP status thật ở status line**.

    Đây là khác biệt cốt lõi với ``utils/response.py::_err`` — hàm đó trả lỗi
    trong thân HTTP 200 để FE cũ tự phân nhánh. Client FHIR lạ không biết quy ước
    đó; nó đọc status line.

    Returns:
        Resource ``OperationOutcome`` — gọi xong thì trả thẳng, không bọc thêm.
    """
    http_status, _ = issue_for(code)
    frappe.local.response["http_status_code"] = http_status
    return operation_outcome(
        code, message,
        diagnostics=diagnostics, message_code=message_code, expression=expression,
    )


def bundle_searchset(
    resources: list[dict[str, Any]],
    *,
    total: int,
    self_link: str,
    next_link: str | None = None,
    previous_link: str | None = None,
) -> dict[str, Any]:
    """Dựng ``Bundle`` kiểu ``searchset`` cho kết quả tìm kiếm.

    Tham chiếu: https://hl7.org/fhir/R4/bundle.html

    ``total`` là **tổng số bản ghi khớp**, không phải số phần tử trên trang này —
    client dùng nó để biết còn bao nhiêu, nên đếm sai sẽ làm client dừng sớm hoặc
    lặp vô hạn.

    Args:
        resources: các resource của trang hiện tại (đã ở dạng dict trần).
        total: tổng số bản ghi khớp truy vấn.
        self_link: URL đầy đủ của chính truy vấn này.
        next_link: URL trang kế — ``None`` nếu đây là trang cuối.
        previous_link: URL trang trước — ``None`` nếu đây là trang đầu.

    Returns:
        Resource ``Bundle`` dạng dict.
    """
    link: list[dict[str, str]] = [{"relation": "self", "url": self_link}]
    if next_link:
        link.append({"relation": "next", "url": next_link})
    if previous_link:
        link.append({"relation": "previous", "url": previous_link})

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": total,
        "link": link,
        "entry": [{"fullUrl": _full_url(r), "resource": r} for r in resources],
    }


def _full_url(resource: dict[str, Any]) -> str:
    """URL tuyệt đối của một resource trong ``Bundle.entry.fullUrl``."""
    return f"{base_url()}/{resource.get('resourceType')}/{resource.get('id')}"


def base_url() -> str:
    """Base URL của bề mặt FHIR — ``<site>/fhir/R4``.

    Client dùng giá trị này để tự dựng link, nên nó phải khớp với ``implementation.url``
    trong ``CapabilityStatement``.
    """
    host = frappe.utils.get_url().rstrip("/")
    return f"{host}/fhir/R4"
