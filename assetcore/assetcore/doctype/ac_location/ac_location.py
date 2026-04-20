# Copyright (c) 2026, AssetCore Team
from frappe.utils.nestedset import NestedSet


class ACLocation(NestedSet):
    """AC Location - Physical hospital location tree (Building -> Floor -> Ward -> Room)."""

    nsm_parent_field = "parent_location"
