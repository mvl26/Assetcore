import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

_IMM_ROLE_PREFIX = "IMM "
_DT_HAS_ROLE = "Has Role"


class ACUserProfile(Document):
    def validate(self):
        self._validate_imm_roles()
        self._handle_approval_transition()

    def on_update(self):
        self._sync_roles_to_user()
        self._apply_user_enabled()

    def _handle_approval_transition(self) -> None:
        """Ghi approved_by/at khi chuyển sang Approved."""
        if self.approval_status != "Approved":
            return
        prev = self.get_doc_before_save()
        prev_status = prev.approval_status if prev else "Pending"
        if prev_status != "Approved":
            self.approved_by = frappe.session.user
            self.approved_at = now_datetime()

    def _apply_user_enabled(self) -> None:
        """Approval_status → User.enabled."""
        if not self.user:
            return
        target_enabled = 1 if self.approval_status == "Approved" else 0
        current = frappe.db.get_value("User", self.user, "enabled")
        if current != target_enabled:
            frappe.db.set_value("User", self.user, "enabled", target_enabled)

    def _validate_imm_roles(self) -> None:
        seen: set[str] = set()
        for row in self.imm_roles or []:
            if not row.role.startswith(_IMM_ROLE_PREFIX):
                frappe.throw(_("Role '{0}' không phải IMM role. Chỉ cho phép role bắt đầu với 'IMM '.").format(row.role))
            if row.role in seen:
                frappe.throw(_("Role '{0}' bị trùng lặp.").format(row.role))
            seen.add(row.role)

    def _sync_roles_to_user(self) -> None:
        """Đồng bộ imm_roles trong profile sang tabHas Role (không dùng user_doc.save() để tránh hook loop)."""
        if not self.user:
            return
        desired = {r.role for r in (self.imm_roles or [])}

        existing_rows = frappe.get_all(
            _DT_HAS_ROLE,
            filters={"parent": self.user, "parenttype": "User", "role": ["like", f"{_IMM_ROLE_PREFIX}%"]},
            fields=["name", "role"],
        )
        existing_imm = {r.role for r in existing_rows}

        to_add = desired - existing_imm
        to_remove = existing_imm - desired

        if not to_add and not to_remove:
            return

        for row in existing_rows:
            if row.role in to_remove:
                frappe.db.delete(_DT_HAS_ROLE, row.name)

        for role in to_add:
            frappe.db.insert({
                "doctype": _DT_HAS_ROLE,
                "parent": self.user,
                "parenttype": "User",
                "parentfield": "roles",
                "role": role,
            })

        frappe.db.commit()
