import frappe
from frappe import _
from frappe.model.document import Document
from assetcore.services.imm11 import handle_calibration_pass, handle_calibration_fail


class IMMAssetCalibration(Document):
    def validate(self):
        self._auto_populate()
        self._validate_external_requirements()
        self._validate_inhouse_requirements()
        self._validate_certificate_date()
        self._compute_measurement_results()

    def before_submit(self):
        if not self.actual_date:
            self.actual_date = frappe.utils.nowdate()
        for m in self.measurements or []:
            if m.measured_value is None:
                frappe.throw(_(f"Tham số '{m.parameter_name}' chưa có giá trị đo (CAL-004)"))

    def on_submit(self):
        if self.overall_result == "Failed":
            handle_calibration_fail(self)
        elif self.overall_result in ("Passed", "Conditionally Passed"):
            handle_calibration_pass(self)

    def on_cancel(self):
        frappe.throw(_("Không thể hủy Phiếu Hiệu chuẩn đã Submit. Vui lòng dùng Amend (BR-11-05)"))

    def on_trash(self):
        if self.docstatus == 1:
            frappe.throw(_("Không thể xóa Phiếu Hiệu chuẩn đã Submit (BR-11-05)"))

    def _auto_populate(self):
        if self.asset and not self.device_model:
            self.device_model = frappe.db.get_value("AC Asset", self.asset, "device_model")

    def _validate_external_requirements(self):
        if self.calibration_type != "External":
            return
        if not self.lab_supplier:
            frappe.throw(_("Vui lòng chọn lab hiệu chuẩn (VR-11-01)"))
        self._validate_lab_iso_17025(self.lab_supplier)
        if self.status == "Certificate Received":
            if not self.certificate_file:
                frappe.throw(_("Vui lòng upload Calibration Certificate (VR-11-03)"))
            if not self.lab_accreditation_number:
                frappe.throw(_("Vui lòng nhập Số công nhận ISO/IEC 17025 (VR-11-04)"))

    @staticmethod
    def _validate_lab_iso_17025(supplier: str) -> None:
        """BR-11-01: Lab phải có vendor_type=Calibration Lab + ISO/IEC 17025 còn hạn."""
        lab = frappe.db.get_value(
            "AC Supplier", supplier,
            ["vendor_type", "iso_17025_cert", "iso_17025_expiry"],
            as_dict=True,
        ) or {}
        if lab.get("vendor_type") != "Calibration Lab":
            frappe.throw(_("NCC phải có vendor_type = 'Calibration Lab' (VR-11-02)"))
        if not lab.get("iso_17025_cert"):
            frappe.throw(_("Lab chưa có số chứng chỉ ISO/IEC 17025 (VR-11-02)"))
        expiry = lab.get("iso_17025_expiry")
        if expiry and str(expiry) < frappe.utils.nowdate():
            frappe.throw(_("Chứng chỉ ISO/IEC 17025 của lab đã hết hạn (VR-11-02)"))

    def _validate_inhouse_requirements(self):
        if self.calibration_type == "In-House" and not self.reference_standard_serial:
            frappe.throw(_("Vui lòng nhập serial thiết bị chuẩn (VR-11-06)"))

    def _validate_certificate_date(self):
        if self.certificate_date and self.certificate_date > frappe.utils.nowdate():
            frappe.throw(_("Ngày cấp chứng chỉ không thể trong tương lai (VR-11-07)"))

    def _compute_measurement_results(self):
        if not self.measurements:
            return
        any_fail = False
        for m in self.measurements:
            if m.measured_value is None:
                continue
            base = abs(m.nominal_value or 0)
            tol_plus = (m.tolerance_positive or 0) / 100 * base
            tol_minus = (m.tolerance_negative or 0) / 100 * base
            dev = (m.measured_value or 0) - (m.nominal_value or 0)
            m.out_of_tolerance = 1 if (dev > tol_plus or dev < -tol_minus) else 0
            m.pass_fail = "Fail" if m.out_of_tolerance else "Pass"
            if m.out_of_tolerance:
                any_fail = True
        self.overall_result = "Failed" if any_fail else "Passed"
