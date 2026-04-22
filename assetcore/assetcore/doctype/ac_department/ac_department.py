# Copyright (c) 2026, AssetCore Team
from frappe.utils.nestedset import NestedSet


class ACDepartment(NestedSet):
    """AC Department - Organizational tree distinct from physical Location."""

    nsm_parent_field = "parent_department"
