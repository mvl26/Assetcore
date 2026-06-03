import frappe
from frappe.model.document import Document
from assetcore.services.imm11 import handle_calibration_pass, handle_calibration_fail
from assetcore.utils.notify import nthrow_in_hook, MSG


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
        # BR-11-08: phải có ≥1 tham số đo trước khi Submit phiếu hiệu chuẩn.
        if not self.measurements:
            nthrow_in_hook(MSG.IMM11_NO_MEASUREMENTS)
        for m in self.measurements or []:
            if m.measured_value is None:
                nthrow_in_hook(MSG.IMM11_MEASUREMENT_VALUE_REQUIRED,
                               parameter=m.parameter_name)
        # Đảm bảo overall_result đã được tính từ measurements.
        self._compute_measurement_results()
        # BR-11-09: phải có kết quả tổng (Passed/Failed/Conditionally Passed).
        if self.overall_result not in ("Passed", "Failed", "Conditionally Passed"):
            nthrow_in_hook(MSG.IMM11_RESULT_REQUIRED)

    def on_submit(self):
        if self.overall_result == "Failed":
            handle_calibration_fail(self)
        elif self.overall_result in ("Passed", "Conditionally Passed"):
            handle_calibration_pass(self)

    def on_cancel(self):
        nthrow_in_hook(MSG.IMM11_CANCEL_SUBMITTED)

    def on_trash(self):
        if self.docstatus == 1:
            nthrow_in_hook(MSG.IMM11_CANCEL_SUBMITTED)

    def _auto_populate(self):
        if self.asset and not self.device_model:
            self.device_model = frappe.db.get_value("AC Asset", self.asset, "device_model")

    def _validate_external_requirements(self):
        if self.calibration_type != "External":
            return
        if not self.lab_supplier:
            nthrow_in_hook(MSG.IMM11_LAB_REQUIRED)
        self._validate_lab_iso_17025(self.lab_supplier)
        if self.status == "Certificate Received":
            if not self.certificate_file:
                nthrow_in_hook(MSG.IMM11_CERT_FILE_REQUIRED)
            if not self.lab_accreditation_number:
                nthrow_in_hook(MSG.IMM11_LAB_ACCRED_NUMBER_REQUIRED)

    @staticmethod
    def _validate_lab_iso_17025(supplier: str) -> None:
        """BR-11-01: Lab phải có vendor_type=Calibration Lab + ISO/IEC 17025 còn hạn."""
        lab = frappe.db.get_value(
            "AC Supplier", supplier,
            ["vendor_type", "iso_17025_cert", "iso_17025_expiry"],
            as_dict=True,
        ) or {}
        if lab.get("vendor_type") != "Calibration Lab":
            nthrow_in_hook(MSG.IMM11_LAB_NOT_ACCREDITED)
        if not lab.get("iso_17025_cert"):
            nthrow_in_hook(MSG.IMM11_LAB_NOT_ACCREDITED)
        expiry = lab.get("iso_17025_expiry")
        if expiry and str(expiry) < frappe.utils.nowdate():
            nthrow_in_hook(MSG.IMM11_LAB_NOT_ACCREDITED)

    def _validate_inhouse_requirements(self):
        if self.calibration_type == "In-House" and not self.reference_standard_serial:
            nthrow_in_hook(MSG.IMM11_REF_STANDARD_REQUIRED)

    def _validate_certificate_date(self):
        if self.certificate_date and self.certificate_date > frappe.utils.nowdate():
            nthrow_in_hook(MSG.IMM11_CERT_DATE_FUTURE)

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
