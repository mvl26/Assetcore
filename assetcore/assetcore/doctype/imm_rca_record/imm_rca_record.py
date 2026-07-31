# Copyright (c) 2026, AssetCore Team
from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import today


class IMMRCARecord(Document):
    """IMM-12 RCA Record — Root Cause Analysis cho sự cố chronic / High-Critical."""

    def validate(self) -> None:
        self._validate_assignment()
        self._validate_five_why_when_method_5why()
        self._validate_completion_requirements()

    def before_save(self) -> None:
        if self.status == "Completed" and not self.completed_date:
            self.completed_date = today()
        if self.status == "Completed" and not self.completed_by:
            self.completed_by = frappe.session.user
        if not self.root_cause and self.get("five_why_steps"):
            last = sorted(self.five_why_steps, key=lambda r: r.why_number or 0)
            if last:
                self.root_cause = last[-1].why_answer or ""

    def on_submit(self) -> None:
        if self.status != "Completed":
            from assetcore.utils.messages import MSG
            from assetcore.utils.notify import nthrow_in_hook
            nthrow_in_hook(MSG.IMM12_RCA_SUBMIT_NOT_COMPLETED, status=self.status)
        self._mark_incident_rca_done()
        self._log_lifecycle_event()
        self._trigger_capa_and_incident_chain()

    def _trigger_capa_and_incident_chain(self) -> None:
        """RC-03 + RC-04: tạo CAPA + đẩy Incident workflow → Closed."""
        if not self.incident_report:
            return
        try:
            from assetcore.services.imm12 import on_rca_completed
            on_rca_completed(self.incident_report, self.name)
        except Exception as e:
            frappe.log_error(
                f"on_rca_completed chain failed for RCA {self.name}: {e}",
                "IMM-12 RCA chain"
            )

    # ───────── validations ─────────

    # AC-CR-83 (docs/imm-12/04_Backend_Design.md §4.3): 3 validator dưới đây là
    # BACKSTOP cho đường Desk/`doc.save()` trực tiếp. Luật nghiệp vụ nằm ở
    # predicate SSoT trong `services/imm12.py` — controller KHÔNG giữ bản kiểm tra
    # thứ hai (INV-RCA-2). Import LAZY trong thân hàm: top-level import service từ
    # controller gây circular ImportError lúc `bench start` (tiền lệ: lazy-import
    # `on_rca_completed` bên dưới).

    def _validate_assignment(self) -> None:
        from assetcore.services.imm12 import (
            _nthrow_violation_in_hook, validate_rca_assignment,
        )
        v = validate_rca_assignment(self.status, self.assigned_to)
        if v:
            _nthrow_violation_in_hook(v)

    def _validate_five_why_when_method_5why(self) -> None:
        if self.status not in ("RCA In Progress", "Completed"):
            return                                   # cổng trạng thái Ở CALL-SITE
        from assetcore.services.imm12 import (
            _nthrow_violation_in_hook, validate_five_why_payload,
        )
        v = validate_five_why_payload(self.rca_method, self.get("five_why_steps"))
        if v:
            _nthrow_violation_in_hook(v)

    def _validate_completion_requirements(self) -> None:
        from assetcore.services.imm12 import (
            _nthrow_violation_in_hook, validate_rca_completion,
        )
        # allow_capa_substitute mặc định True (D-RCA-2): hồ sơ Desk đã gắn CAPA
        # được miễn tóm tắt khắc phục — KHÁC service submit_rca (False).
        v = validate_rca_completion(self.status, self.root_cause,
                                    self.corrective_action_summary, self.linked_capa)
        if v:
            _nthrow_violation_in_hook(v)

    # ───────── side-effects ─────────

    def _mark_incident_rca_done(self) -> None:
        """Khi RCA hoàn tất, mở khóa cho Incident Report đóng (BR-12-02)."""
        if not self.incident_report:
            return
        if not frappe.db.exists("Incident Report", self.incident_report):
            return
        frappe.db.set_value(
            "Incident Report", self.incident_report,
            {"requires_rca": 0},
            update_modified=False,
        )

    def _log_lifecycle_event(self) -> None:
        """Ghi Lifecycle Event để traceability (CLAUDE.md #10)."""
        if not self.asset:
            return
        try:
            frappe.get_doc({
                "doctype": "Asset Lifecycle Event",
                "asset": self.asset,
                "event_type": "rca_completed",
                "actor": frappe.session.user,
                "from_state": "RCA In Progress",
                "to_state": "Completed",
                "root_record_doctype": "IMM RCA Record",
                "root_record": self.name,
                "remarks": f"RCA hoàn tất - Root cause: {(self.root_cause or '')[:140]}",
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"RCA lifecycle log failed: {e}", "IMM-12 RCA")
