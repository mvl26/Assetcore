# Copyright (c) 2026, AssetCore Team
import re

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils.nestedset import NestedSet


# Cho phép chữ cái, số, gạch ngang, gạch dưới, dấu chấm — tránh ký tự đặc biệt
# (`/`, `?`, `&`, ...) gây lỗi URL/route khi dùng làm name (PK).
_LOCATION_CODE_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class ACLocation(NestedSet):
    """AC Location — Physical hospital location tree (Building → Floor → Ward → Room).

    Naming rule:
        - Nếu user nhập `location_code` → dùng làm `name` (PK).
        - Nếu để trống → tự sinh từ `naming_series` (mặc định AC-LOC-.YYYY.-.####)
          và đồng bộ `location_code = name` để field không bị rỗng.
    """

    nsm_parent_field = "parent_location"

    def autoname(self) -> None:
        code = (self.location_code or "").strip()
        if code:
            if not _LOCATION_CODE_PATTERN.match(code):
                frappe.throw(_(
                    "Mã vị trí chỉ được chứa chữ cái, số và các ký tự . _ -"
                ))
            self.location_code = code
            self.name = code
            return

        series = self.naming_series or "AC-LOC-.YYYY.-.####"
        self.naming_series = series
        self.name = make_autoname(series, doc=self)
        # Đồng bộ code = name để search/listing hiển thị nhất quán.
        self.location_code = self.name

    def validate(self) -> None:
        # Mã vị trí là PK — không thể thay đổi sau khi tạo (set_only_once đã chặn
        # ở mức field, đây là double-check kèm message tiếng Việt rõ ràng).
        if not self.is_new():
            old = frappe.db.get_value(self.doctype, self.name, "location_code")
            if old and old != self.location_code:
                frappe.throw(_(
                    "Mã vị trí không thể thay đổi sau khi tạo "
                    "(hiện tại: {0}, cố đổi sang: {1})."
                ).format(old, self.location_code))
