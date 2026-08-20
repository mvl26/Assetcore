# Copyright (c) 2026, AssetCore Team
"""Điều phối đường dẫn FHIR → tương tác → handler (SPEC §6.1, §10).

Bảng không gian URL R4 mà module này hiện thực::

    GET  /fhir/R4/metadata                  CapabilityStatement
    GET  /fhir/R4/{Type}/{id}               đọc 1 resource
    GET  /fhir/R4/{Type}/{id}/_history/{v}  đọc bản phiên bản
    GET  /fhir/R4/{Type}?param=…            tìm kiếm → Bundle searchset
    POST /fhir/R4/{Type}                    tạo
    PUT  /fhir/R4/{Type}/{id}               cập nhật (kèm If-Match)
    PATCH/DELETE /fhir/R4/{Type}/{id}       vá / xoá logic

Module này CHỈ phân giải đường dẫn và tra bảng dispatch. Nó không biết gì về
nghiệp vụ và không chạm DB — đúng vai trò của một tầng vận chuyển.
"""

from __future__ import annotations

from typing import Any

from assetcore.fhir import dispatch
from assetcore.fhir.conformance.capability import build_capability_statement
from assetcore.fhir.response import fhir_error

#: Tiền tố phiên bản trong URL. R4 là bản normative đang dùng (SPEC §1 giả định #4).
VERSION_SEGMENT = "R4"

#: HTTP method → tương tác R4 khi đường dẫn có ``{id}``.
_INSTANCE_INTERACTION = {
    "GET": dispatch.READ,
    "PUT": dispatch.UPDATE,
    "PATCH": dispatch.PATCH,
    "DELETE": dispatch.DELETE,
}

#: HTTP method → tương tác R4 khi đường dẫn chỉ có ``{Type}``.
_TYPE_INTERACTION = {
    "GET": dispatch.SEARCH_TYPE,
    "POST": dispatch.CREATE,
}


def resolve(path: str, method: str) -> tuple[str, dict[str, Any]] | None:
    """Phân giải một đường dẫn FHIR thành ``(interaction, params)``.

    Args:
        path: phần sau ``/fhir/``, vd ``R4/Device/AC-ASSET-2026-1``.
        method: HTTP method viết hoa.

    Returns:
        ``(interaction, params)`` với ``params`` gồm ``resource_type``/``id``/
        ``version_id`` tuỳ dạng; ``None`` nếu đường dẫn không thuộc không gian FHIR.
    """
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts or parts[0] != VERSION_SEGMENT:
        return None
    rest = parts[1:]

    if not rest:
        return None
    if rest == ["metadata"]:
        return ("capabilities", {})

    resource_type = rest[0]
    if len(rest) == 1:
        interaction = _TYPE_INTERACTION.get(method)
        return (interaction, {"resource_type": resource_type}) if interaction else None

    if len(rest) == 2:
        interaction = _INSTANCE_INTERACTION.get(method)
        if not interaction:
            return None
        return (interaction, {"resource_type": resource_type, "id": rest[1]})

    if len(rest) == 4 and rest[2] == "_history" and method == "GET":
        return (dispatch.VREAD, {
            "resource_type": resource_type, "id": rest[1], "version_id": rest[3],
        })

    if len(rest) == 3 and rest[2].startswith("$") and method == "POST":
        return ("operation", {
            "resource_type": resource_type, "id": rest[1], "operation": rest[2][1:],
        })

    return None


def handle(path: str, method: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
    """Điểm vào duy nhất của bề mặt FHIR.

    Args:
        path: phần sau ``/fhir/``.
        method: HTTP method.
        query: tham số truy vấn.

    Returns:
        Resource FHIR dạng dict — TRẦN. Lỗi trả ``OperationOutcome`` và HTTP status
        đã được đặt ở status line bởi :func:`~assetcore.fhir.response.fhir_error`.
    """
    resolved = resolve(path, method)
    if resolved is None:
        return fhir_error(
            "NOT_FOUND",
            "Đường dẫn không thuộc bề mặt FHIR của AssetCore.",
            diagnostics=f"{method} /fhir/{path.strip('/')}",
        )

    interaction, params = resolved
    if interaction == "capabilities":
        return build_capability_statement()

    resource_type = params["resource_type"]
    if resource_type not in dispatch.registry():
        return fhir_error(
            "NOT_FOUND",
            f"Server không hỗ trợ resource type '{resource_type}'.",
            diagnostics="Xem GET /fhir/R4/metadata để biết các type được hỗ trợ.",
        )

    handler = dispatch.lookup(resource_type, interaction)
    if handler is None:
        return fhir_error(
            "BUSINESS_RULE",
            f"Resource '{resource_type}' không hỗ trợ tương tác '{interaction}'.",
            diagnostics="Xem GET /fhir/R4/metadata để biết các tương tác được hỗ trợ.",
        )

    return handler(query=query or {}, **{k: v for k, v in params.items() if k != "resource_type"})
