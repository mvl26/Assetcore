# Copyright (c) 2026, AssetCore Team
import re

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils.nestedset import NestedSet


_DEPARTMENT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class ACDepartment(NestedSet):
    """AC Department — Organizational tree distinct from physical Location.

    Naming rule:
        - Nếu user nhập `department_code` → dùng làm `name` (PK).
        - Nếu để trống → tự sinh từ `naming_series` (mặc định AC-DEPT-.####)
          và đồng bộ `department_code = name` để field không bị rỗng.
    """

    nsm_parent_field = "parent_department"

    def autoname(self) -> None:
        code = (self.department_code or "").strip()
        if code:
            if not _DEPARTMENT_CODE_PATTERN.match(code):
                frappe.throw(_(
                    "Mã khoa chỉ được chứa chữ cái, số và các ký tự . _ -"
                ))
            self.department_code = code
            self.name = code
            return

        series = self.naming_series or "AC-DEPT-.####"
        self.naming_series = series
        self.name = make_autoname(series, doc=self)
        self.department_code = self.name

    def validate(self) -> None:
        if not self.is_new():
            old = frappe.db.get_value(self.doctype, self.name, "department_code")
            if old and old != self.department_code:
                frappe.throw(_(
                    "Mã khoa không thể thay đổi sau khi tạo "
                    "(hiện tại: {0}, cố đổi sang: {1})."
                ).format(old, self.department_code))
