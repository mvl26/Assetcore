# Copyright (c) 2026, AssetCore Team
# Controller cho Asset Archive Record (IMM-14).
# Logic nghiệp vụ delegate sang service layer.

from __future__ import annotations

import frappe
from frappe.model.document import Document


class AssetArchiveRecord(Document):
    """Hồ sơ lưu trữ cuối vòng đời thiết bị y tế — IMM-14.

    Submittable document. Sau khi Submit:
    - Asset.status = Archived
    - Asset Lifecycle Event "archived" được tạo
    """

    # ── Lifecycle Hooks ──────────────────────────────────────────────────

    def validate(self) -> None:
        """Validation rules VR-14-01 đến VR-14-04."""
        from assetcore.services import imm14 as svc
        svc.validate_archive_record(self)

    def before_save(self) -> None:
        """Tính release_date và đếm tài liệu."""
        from assetcore.services import imm14 as svc
        svc.before_save_handler(self)

    def on_submit(self) -> None:
        """Khi Submit: set Asset Archived + log ALE."""
        from assetcore.services import imm14 as svc
        svc.finalize_archive_handler(self)
