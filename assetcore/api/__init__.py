# Copyright (c) 2026, AssetCore Team and contributors
# assetcore.api — REST API package cho AssetCore modules

# Re-export legacy endpoints để không break URL cũ
from assetcore.api.imm04 import get_barcode_lookup as get_commissioning_by_barcode  # noqa: F401
from assetcore.api.imm04 import get_dashboard_stats  # noqa: F401
