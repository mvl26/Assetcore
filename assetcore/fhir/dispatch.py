# Copyright (c) 2026, AssetCore Team
"""Bảng định tuyến ``(Type, interaction) → handler`` — SSoT của bề mặt FHIR.

Vì sao bảng này tồn tại (SPEC §10, §13)
----------------------------------------
``CapabilityStatement`` là thứ **duy nhất** một client lạ đọc để biết server làm
được gì. Nếu nó được viết tay thì nó sẽ lệch khỏi mã thật — và lệch theo hướng tệ
nhất: client tin lời khai, gọi vào, nhận 404. Nên ở đây bảng dispatch là nguồn, và
:mod:`assetcore.fhir.conformance.capability` **sinh** ``CapabilityStatement`` từ nó.
Guard ``tests/guards/test_fhir_capability_parity.py`` khoá hai bên khớp tuyệt đối.

Cùng lý do với ``uiAuditDocParity`` ở phía FE: con số trong câu văn không tự đỏ được,
nên phải có một bên sinh ra bên kia.

Trạng thái Đợt 0
----------------
Đợt 0 chỉ dựng **nền**: chưa có mapper nào nên bảng cố ý RỖNG phần resource, chỉ
khai ``metadata``. Đợt 1 đăng ký ``Device``/``Location``/``Organization``/
``Practitioner``… bằng :func:`register`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

#: Các tương tác cấp resource-type mà R4 định nghĩa (subset ta dùng).
#: https://hl7.org/fhir/R4/valueset-type-restful-interaction.html
READ = "read"
VREAD = "vread"
SEARCH_TYPE = "search-type"
CREATE = "create"
UPDATE = "update"
PATCH = "patch"
DELETE = "delete"

#: Thứ tự công bố trong ``CapabilityStatement`` — cố định để bản khai tất định.
INTERACTION_ORDER = (READ, VREAD, SEARCH_TYPE, CREATE, UPDATE, PATCH, DELETE)


@dataclass(frozen=True)
class SearchParam:
    """Một tham số tìm kiếm được công bố cho client.

    Args:
        name: tên tham số theo chuẩn, vd ``identifier``.
        type_: kiểu R4 (``token``/``string``/``date``/``reference``/``number``).
        documentation: mô tả ngắn — client lạ đọc cái này để biết truyền gì.
    """

    name: str
    type_: str
    documentation: str = ""


@dataclass(frozen=True)
class ResourceEntry:
    """Một resource type được phơi ra cùng tập tương tác và tham số của nó."""

    type_: str
    interactions: tuple[str, ...]
    profile: str | None = None
    search_params: tuple[SearchParam, ...] = ()
    handlers: dict[str, Callable[..., Any]] = field(default_factory=dict)


#: Bảng SSoT. Khoá = resource type (vd ``"Device"``).
_REGISTRY: dict[str, ResourceEntry] = {}


def register(entry: ResourceEntry) -> None:
    """Đăng ký một resource type vào bề mặt FHIR.

    Raises:
        ValueError: nếu type đã đăng ký (đăng ký hai lần = hai định nghĩa cùng tồn
            tại, và bản nào thắng phụ thuộc thứ tự import — không tất định).
    """
    if entry.type_ in _REGISTRY:
        raise ValueError(
            f"Resource type '{entry.type_}' đã đăng ký. Mỗi type chỉ được khai MỘT lần — "
            "đăng ký trùng làm CapabilityStatement phụ thuộc thứ tự import."
        )
    unknown = set(entry.interactions) - set(INTERACTION_ORDER)
    if unknown:
        raise ValueError(
            f"Tương tác không thuộc R4: {sorted(unknown)}. "
            f"Chỉ dùng: {', '.join(INTERACTION_ORDER)}."
        )
    _REGISTRY[entry.type_] = entry


def registry() -> dict[str, ResourceEntry]:
    """Bản sao chỉ-đọc của bảng đăng ký (tránh sửa ngoài ý muốn)."""
    return dict(_REGISTRY)


def resource_types() -> list[str]:
    """Danh sách resource type đã đăng ký, sắp xếp — dùng cho bản khai tất định."""
    return sorted(_REGISTRY)


def lookup(resource_type: str, interaction: str) -> Callable[..., Any] | None:
    """Tìm handler cho một cặp ``(type, interaction)``.

    Returns:
        Handler, hoặc ``None`` nếu chưa hỗ trợ — caller trả 404/405 tương ứng.
    """
    entry = _REGISTRY.get(resource_type)
    if entry is None or interaction not in entry.interactions:
        return None
    return entry.handlers.get(interaction)
