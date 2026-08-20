# Copyright (c) 2026, AssetCore Team
"""Re-export ``ServiceError`` — định nghĩa THẬT ở :mod:`assetcore.utils.errors`.

SPEC BE §5.4 (lô B6) chốt ranh giới **một chiều**:

* ``assetcore/utils/`` — hạ tầng kỹ thuật, không biết nghiệp vụ.
  Được import: thư viện ngoài + ``frappe``. **CẤM** import ``services/**``.
* ``assetcore/services/shared/`` — nhân nghiệp vụ dùng chung.
  Được import ``utils/``.

``ServiceError`` bị **cả hai tầng** dùng (``utils/api_handler.py`` bọc envelope,
service layer raise), nên nó thuộc tầng THẤP hơn. File này giữ lại để ~73 chỗ
``from assetcore.services.shared import ServiceError`` không phải sửa.
"""

from assetcore.utils.errors import (  # noqa: F401  (re-export một chiều)
    ServiceError,
    bad_state,
    conflict,
    forbidden,
    not_found,
    unauthorized,
    validation,
)
