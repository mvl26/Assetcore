import frappe
from frappe.model.document import Document


class IMMCalibrationSchedule(Document):
    def validate(self):
        if self.asset and not self.device_model:
            self.device_model = frappe.db.get_value("AC Asset", self.asset, "device_model")
