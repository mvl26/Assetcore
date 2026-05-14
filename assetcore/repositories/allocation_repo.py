# Copyright (c) 2026, AssetCore Team
"""IMM-15 Spare Parts Inventory — Repository layer."""
from __future__ import annotations

import frappe

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


class SparePartForecastRepo(BaseRepository):
    """Repository cho IMM Spare Part Forecast."""
    DOCTYPE = "IMM Spare Part Forecast"


class SparePartRepo(BaseRepository):
    """Repository cho AC Spare Part (read-mostly cho IMM-15)."""
    DOCTYPE = "AC Spare Part"


class StockMovementRepo(BaseRepository):
    """Repository cho AC Stock Movement (IMM-15 consumption queries)."""
    DOCTYPE = "AC Stock Movement"

    @classmethod
    def get_consumption(cls, spare_part: str, months: int = 12) -> float:
        """Tổng qty Issue cho 1 spare_part trong N tháng qua."""
        row = frappe.db.sql(
            """SELECT COALESCE(SUM(i.qty), 0)
               FROM `tabAC Stock Movement Item` i
               JOIN `tabAC Stock Movement` m ON m.name = i.parent
               WHERE i.spare_part = %s
                 AND m.movement_type = 'Issue'
                 AND m.docstatus = 1
                 AND m.movement_date >= DATE_SUB(CURDATE(), INTERVAL %s MONTH)""",
            (spare_part, int(months)),
        )
        return float((row or [[0]])[0][0])
