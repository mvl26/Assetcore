# Copyright (c) 2026, AssetCore Team
"""Controller cho DocType `AC Mobile Device Token` (EPIC-D / D1).

Registry token push FCM cho persona field-tech (kỹ thuật viên hiện trường).
Spec: `docs/mobile/06-push-fcm.md §2` · `docs/mobile/completion/EPIC-D-push-fcm.md §5.1`.

DELEGATE RỖNG — KHÔNG logic trong controller (CLAUDE.md §15). Nghiệp vụ
register/unregister/invalidate (UPSERT-dedup, ép user=session, audit NĐ98)
nằm ở service layer `assetcore/services/mobile_device_token.py` (D2). Row-level
self-scope (user==frappe.session.user) thực thi qua hook `permission_query_conditions`
+ `has_permission` (D7), KHÔNG đặt ở đây.
"""
from __future__ import annotations

from frappe.model.document import Document


class ACMobileDeviceToken(Document):
    """Token thiết bị mobile để gửi push FCM. autoname=hash, fcm_token UNIQUE."""

    pass
