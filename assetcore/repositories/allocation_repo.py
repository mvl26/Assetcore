# Copyright (c) 2026, AssetCore Team
"""IMM-15 Spare Parts Inventory — Repository layer."""
from __future__ import annotations

from assetcore.repositories.base import BaseRepository


class AllocationRepo(BaseRepository):
    """Repository cho IMM Spare Allocation."""
    DOCTYPE = "IMM Spare Allocation"


class CycleCountRepo(BaseRepository):
    """Repository cho IMM Stock Cycle Count."""
    DOCTYPE = "IMM Stock Cycle Count"


class CriticalWatchlistRepo(BaseRepository):
    """Repository cho IMM Critical Spare Watchlist."""
    DOCTYPE = "IMM Critical Spare Watchlist"

    @classmethod
    def get_active_entries(cls) -> list[dict]:
        """Trả list watchlist entries đang active."""
        rows, _ = cls.list(
            filters={"active": 1},
            fields=["name", "spare_part", "warehouse", "min_required_on_hand",
                    "critical_asset"],
            page_size=1000,
        )
        return rows
