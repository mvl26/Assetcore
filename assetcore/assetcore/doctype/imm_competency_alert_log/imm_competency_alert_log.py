# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document


class IMMCompetencyAlertLog(Document):
    """Idempotency log for competency expiry alert scheduler.

    Unique constraint on (competency, alert_date, milestone) ensures the scheduler
    does not generate duplicate alerts for the same competency expiry milestone.
    Milestones: 90 days (Info), 60 days (Warning), 30 days (Critical), 0 days (Danger).
    """
    pass
