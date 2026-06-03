# Copyright (c) 2026, AssetCore Team
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cint, getdate


_DOCTYPE = "Service Contract"
_CONTRACT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9._\-/]+$")
_DEFAULT_NAMING_SERIES = "SC-.YYYY.-.####"


class ServiceContract(Document):
    """Service Contract — tracks maintenance/calibration/repair agreements with suppliers.

    Naming rule (unified — same pattern as AC Department / AC Asset):
        - Nếu user nhập ``contract_code`` → dùng làm ``name`` (PK).
        - Nếu để trống → tự sinh từ ``naming_series`` (mặc định SC-.YYYY.-.####)
          và đồng bộ ``contract_code = name`` để field không bị rỗng.
    """

    def autoname(self) -> None:
        code = (self.contract_code or "").strip()
        if code:
            if not _CONTRACT_CODE_PATTERN.match(code):
                frappe.throw(_(
                    "Mã hợp đồng chỉ được chứa chữ cái, số và các ký tự . _ - /"
                ))
            self.contract_code = code
            self.name = code
            return

        series = (self.naming_series or "").strip() or _DEFAULT_NAMING_SERIES
        self.naming_series = series
        self.name = make_autoname(series, doc=self)
        self.contract_code = self.name

    def validate(self) -> None:
        self._validate_contract_code_immutable()
        self._validate_dates()
        self._validate_sla_response()
        self._populate_amount_in_words()

    def _validate_contract_code_immutable(self) -> None:
        if self.is_new() or not self.contract_code:
            return
        old = frappe.db.get_value(_DOCTYPE, self.name, "contract_code")
        if old and old != self.contract_code:
            frappe.throw(_(
                "Mã hợp đồng không thể thay đổi sau khi tạo "
                "(hiện tại: {0}, cố đổi sang: {1})."
            ).format(old, self.contract_code))

    def _populate_amount_in_words(self) -> None:
        """Tự sinh 'Số tiền bằng chữ' từ giá trị hợp đồng (slide 05b/c)."""
        from assetcore.services.shared.num_to_words_vi import num_to_words_vi

        if self.contract_value and float(self.contract_value) > 0:
            self.amount_in_words = num_to_words_vi(float(self.contract_value))
        else:
            self.amount_in_words = None

    def _validate_dates(self) -> None:
        if self.contract_start and self.contract_end:
            if getdate(self.contract_end) <= getdate(self.contract_start):
                frappe.throw(_("Ngày kết thúc phải sau ngày bắt đầu hợp đồng."))

    def _validate_sla_response(self) -> None:
        if self.sla_response_hours in (None, ""):
            return
        hours = cint(self.sla_response_hours)
        self.sla_response_hours = hours
        if hours < 0:
            frappe.throw(_("Thời gian phản hồi SLA phải >= 0."))
