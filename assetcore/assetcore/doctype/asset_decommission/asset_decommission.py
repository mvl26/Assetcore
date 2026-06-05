# Copyright (c) 2026, AssetCore Team and contributors
# For license information, please see license.txt
"""Asset Decommission — controller (IMM-14 Decommission Closure Gate).

Mọi business logic ở service layer `assetcore.services.imm14` (CLAUDE.md §15).
Controller chỉ delegate hook → service.
"""
import frappe
from frappe.model.document import Document


class AssetDecommission(Document):

    def before_insert(self) -> None:
        """Snapshot asset_name + risk_classification + validate trùng/terminal."""
        from assetcore.services import imm14
        imm14.before_insert_decommission(self)

    def before_submit(self) -> None:
        """Gate trước Approve: field-level + sanitization (BR-14-W2-02..05).

        Chạy ở before_submit (KHÔNG validate) để cho phép lưu draft với
        patient_data_sanitized chưa tích — gate chỉ chặn khi Duyệt.
        """
        from assetcore.services import imm14
        imm14.validate_before_approve(self)

    def on_submit(self, method=None) -> None:
        """Approve → transition asset sang Decommissioned (idempotent)."""
        from assetcore.services import imm14
        imm14.on_decommission_submit(self, method)

    def on_cancel(self, method=None) -> None:
        """Cancel record — KHÔNG đảo asset status (rollback là Đợt 3)."""
        from assetcore.services import imm14
        imm14.on_decommission_cancel(self, method)
