# Copyright (c) 2026, AssetCore Team
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname

_CATEGORY_CODE_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class ACAssetCategory(Document):
    """AC Asset Category — danh mục thiết bị y tế.

    Naming rule:
        - Nếu user nhập `category_code` → dùng làm `name` (PK).
        - Nếu để trống → tự sinh theo series CAT-.####
          và đồng bộ `category_code = name` để field không bị rỗng.
    """

    def autoname(self) -> None:
        code = (self.category_code or "").strip()
        if code:
            if not _CATEGORY_CODE_PATTERN.match(code):
                frappe.throw(_(
                    "Mã danh mục chỉ được chứa chữ cái, số và các ký tự . _ -"
                ))
            self.category_code = code
            self.name = code
            return

        self.name = make_autoname("CAT-.####", doc=self)
        self.category_code = self.name

    def validate(self) -> None:
        if not self.is_new():
            old = frappe.db.get_value(self.doctype, self.name, "category_code")
            if old and old != self.category_code:
                frappe.throw(_(
                    "Mã danh mục không thể thay đổi sau khi tạo "
                    "(hiện tại: {0}, cố đổi sang: {1})."
                ).format(old, self.category_code))
        self._validate_pm_interval()
        self._validate_calibration_interval()
        self._validate_gmdn_unique()

    def on_update(self) -> None:
        """C4 (P3 Hybrid): cascade gmdn_code xuống Model kế thừa + Asset.

        Chỉ cascade khi gmdn_code THỰC SỰ đổi (has_value_changed). Service
        layer chỉ set_value trên Model/Asset — KHÔNG save lại Category nên
        không gây đệ quy on_update. Bỏ qua khi đang trong luồng install/insert
        (chưa có dữ liệu cũ để so).

        Ref: docs/res/plans/2026-05-19-gmdn-code-sync-strategy.md §6 C4.
        """
        if self.is_new() or not self.has_value_changed("gmdn_code"):
            return
        old_code = self.get_doc_before_save()
        old_code = old_code.gmdn_code if old_code else None
        from assetcore.services.imm00 import cascade_category_gmdn

        cascade_category_gmdn(self.name, old_code, self.gmdn_code)

    def _validate_gmdn_unique(self) -> None:
        if not self.gmdn_code:
            return
        dup = frappe.db.get_value(
            "AC Asset Category",
            {"gmdn_code": self.gmdn_code, "name": ["!=", self.name or ""]},
            "name",
        )
        if dup:
            frappe.throw(_(
                "Mã GMDN '{0}' đã được dùng bởi danh mục '{1}'. "
                "Mỗi mã GMDN chỉ thuộc một danh mục."
            ).format(self.gmdn_code, dup))

    def _validate_pm_interval(self) -> None:
        if not self.default_pm_required:
            return
        if not self.default_pm_interval_days or int(self.default_pm_interval_days) <= 0:
            frappe.throw(_("default_pm_interval_days phải > 0 khi default_pm_required=1 (VR-00-16)."))

    def _validate_calibration_interval(self) -> None:
        if not self.default_calibration_required:
            return
        if not self.default_calibration_interval_days or int(self.default_calibration_interval_days) <= 0:
            frappe.throw(_("default_calibration_interval_days phải > 0 khi default_calibration_required=1."))
