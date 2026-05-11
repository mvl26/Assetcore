# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document


class IMMGapDetailRow(Document):
    """Child table row for IMM Competency Gap Report.

    Represents one (department, device_class) combination in the gap analysis matrix.
    Contains counts for competent users vs required minimum and the resulting gap.
    """
    pass
