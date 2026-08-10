"""Backfill ``workflow_state`` từ ``status`` cho doctype vận hành (ADR-CORE-01).

Bối cảnh (2026-07-22): ADR trước coi ``workflow_state`` là *vestigial* trên các doctype
vận hành — service chỉ ghi ``status``, workflow engine không được gọi. Hệ quả:
``workflow_state`` đọng ở giá trị khởi tạo (thường 'Open'/rỗng) trong khi ``status`` đi
hết vòng đời. ADR-CORE-01 lấy workflow engine làm nguồn sự thật, nên trước khi engine
tiếp quản, hai field phải KHỚP — nếu không, bản ghi cũ sẽ bị engine coi là đang ở trạng
thái sai và người dùng thấy sai bộ nút.

Chiều backfill: ``workflow_state ← status``. ``status`` là field mà service THẬT SỰ đã
ghi suốt thời gian qua nên nó là dữ liệu đúng; ``workflow_state`` là field đọng.

Phạm vi: 10 doctype có giá trị ``status`` TRÙNG KHỚP hoàn toàn tên state của workflow
(kiểm 2026-07-22) ⇒ ánh xạ 1-1, không cần chuyển đổi giá trị. Hai doctype ngoại lệ
(``IMM CAPA Record`` từ vựng khác, ``AC Asset`` đã dùng ``lifecycle_status`` làm trục
đúng) KHÔNG thuộc patch này — xem ROLLUP_MAP trong ``services/shared/state.py``.

An toàn:
  - **Idempotent**: chỉ ghi khi rỗng/lệch ⇒ chạy lần 2 sửa 0 bản ghi.
  - ``db.set_value(..., update_modified=False)``: không đụng ``modified`` nên không làm
    nhiễu các job đồng bộ theo mốc thời gian, và KHÔNG chạy hook — đây là sửa dữ liệu
    lịch sử, không phải một chuyển trạng thái nghiệp vụ.
  - Bỏ qua doctype/cột chưa tồn tại (site cài một phần) thay vì làm hỏng cả migrate.
  - Chỉ ghi giá trị NẰM TRONG danh sách state của workflow — dữ liệu rác không được
    chép sang, mà được đếm và báo cáo để người vận hành xử lý riêng.
"""
from __future__ import annotations

import frappe

#: (doctype, tên field nguồn) — 10 doctype ánh xạ 1-1 status ↔ tên state workflow.
_IDENTITY_MAPPED: list[tuple[str, str]] = [
    ("PM Work Order", "status"),
    ("Asset Repair", "status"),
    ("IMM Asset Calibration", "status"),
    ("Incident Report", "status"),
    ("IMM RCA Record", "status"),
    ("IMM Stock Cycle Count", "status"),
    ("IMM Spare Allocation", "allocation_status"),
    ("IMM Compliance Finding", "status"),
    ("IMM Internal Audit", "status"),
    ("IMM Management Review", "status"),
]


def _workflow_states(doctype: str) -> set[str]:
    """Tên state hợp lệ của workflow đang gắn vào doctype (rỗng nếu không có)."""
    workflow = frappe.db.get_value(
        "Workflow", {"document_type": doctype, "is_active": 1}, "name"
    )
    if not workflow:
        return set()
    return set(
        frappe.get_all("Workflow Document State", filters={"parent": workflow}, pluck="state")
    )


def backfill(doctypes: list[tuple[str, str]] | None = None) -> dict[str, int]:
    """Đồng bộ ``workflow_state`` theo field nguồn. Trả {doctype: số bản ghi đã sửa}.

    Tách khỏi ``execute`` để test được trên tập doctype hẹp, không phải chạy cả site.
    """
    result: dict[str, int] = {}
    for doctype, source_field in doctypes if doctypes is not None else _IDENTITY_MAPPED:
        if not frappe.db.table_exists(doctype):
            continue
        if not frappe.db.has_column(doctype, "workflow_state"):
            continue
        if not frappe.db.has_column(doctype, source_field):
            continue

        valid_states = _workflow_states(doctype)
        if not valid_states:
            continue

        rows = frappe.get_all(
            doctype,
            filters={source_field: ["is", "set"]},
            fields=["name", source_field, "workflow_state"],
            limit_page_length=0,
            ignore_permissions=True,
        )

        fixed = 0
        skipped_unknown = 0
        for row in rows:
            source_value = row.get(source_field)
            if source_value == row.get("workflow_state"):
                continue  # đã khớp — idempotent
            if source_value not in valid_states:
                skipped_unknown += 1
                continue  # giá trị rác: KHÔNG chép sang trục mới
            frappe.db.set_value(
                doctype, row["name"], "workflow_state", source_value, update_modified=False
            )
            fixed += 1

        if fixed or skipped_unknown:
            result[doctype] = fixed
            print(
                f"  {doctype}: đồng bộ {fixed} bản ghi"
                + (
                    f"; BỎ QUA {skipped_unknown} bản ghi có {source_field} ngoài danh "
                    f"sách state của workflow (cần rà thủ công)"
                    if skipped_unknown
                    else ""
                )
            )
        else:
            result[doctype] = 0
    return result


def execute() -> None:
    print("ADR-CORE-01 — đồng bộ workflow_state từ status:")
    total = sum(backfill().values())
    print(f"  Tổng cộng: {total} bản ghi được đồng bộ.")
