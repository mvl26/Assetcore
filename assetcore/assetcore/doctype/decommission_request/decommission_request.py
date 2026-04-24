# Copyright (c) 2026, AssetCore Team
# Controller cho Decommission Request (IMM-13).
# Logic nghiệp vụ delegate hoàn toàn sang service layer.

from __future__ import annotations

import frappe
from frappe.model.document import Document


class DecommissionRequest(Document):
    """Phiếu Ngừng sử dụng & Điều chuyển Thiết bị — IMM-13.

    Submittable document. Sau khi Submit (tùy outcome):
    - Transfer: Asset.status = Transferred, location updated
    - Suspend: Asset.status = Suspended
    - Retire: Asset.status = Decommissioned + trigger IMM-14
    Mọi transition đều log Asset Lifecycle Event.
    """

    # ── Lifecycle Hooks ──────────────────────────────────────────────────

    def before_insert(self) -> None:
        """Auto-insert 7 default suspension checklist items."""
        from assetcore.services import imm13 as svc
        svc.insert_default_checklist(self)

    def validate(self) -> None:
        """Chạy toàn bộ validation rules BR-13-01 đến BR-13-10."""
        from assetcore.services import imm13 as svc
        svc.validate_suspension_request(self)

    def before_submit(self) -> None:
        """Validation cuối trước submit: data destruction, high-value approval."""
        from assetcore.services import imm13 as svc
        svc.before_submit_handler(self)

    def on_submit(self) -> None:
        """Atomic: set asset status + log ALE + optional IMM-14 trigger."""
        from assetcore.services import imm13 as svc
        svc.on_submit_handler(self)

    def on_cancel(self) -> None:
        """Log ALE cancelled; revert asset status if needed."""
        from assetcore.services import imm13 as svc
        svc.on_cancel_handler(self)
