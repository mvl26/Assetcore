# Copyright (c) 2026, AssetCore Team
# Controller cho Decommission Request (IMM-13).
# Logic nghiệp vụ delegate hoàn toàn sang service layer.

from __future__ import annotations

import frappe
from frappe.model.document import Document


class DecommissionRequest(Document):
    """Phiếu yêu cầu thanh lý thiết bị y tế — IMM-13.

    Submittable document. Sau khi Submit:
    - Asset.status = Decommissioned
    - Asset Lifecycle Event "decommissioned" được tạo
    - Asset Archive Record (IMM-14) được tự động tạo
    """

    # ── Lifecycle Hooks ──────────────────────────────────────────────────

    def validate(self) -> None:
        """Chạy toàn bộ validation rules VR-01 đến VR-05."""
        from assetcore.services import imm13 as svc
        svc.validate_decommission_request(self)

    def on_submit(self) -> None:
        """Khi Submit: set Asset Decommissioned + log ALE + trigger IMM-14."""
        from assetcore.services import imm13 as svc
        svc.on_submit_handler(self)

    def on_cancel(self) -> None:
        """Block cancel nếu asset đã Decommissioned."""
        from assetcore.services import imm13 as svc
        svc.on_cancel_handler(self)
