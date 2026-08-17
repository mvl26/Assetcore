# Copyright (c) 2026, AssetCore Team
"""TC-STATE-SVC — ``services.shared.state``: đường ghi trạng thái DUY NHẤT (ADR-CORE-01).

Kiểm 3 nhóm:
  1. **Đọc đúng trục.** ``state_field`` phải trả field mà workflow THẬT SỰ bind — riêng
     ``AC Asset`` là ``lifecycle_status``, đoán bừa 'workflow_state' sẽ cho ra danh sách
     hành động rỗng mà không lỗi.
  2. **Bảng rollup phủ hết state.** Thiếu một state ⇒ tới ngày state đó xảy ra, `status`
     nhận giá trị ngoài enum và bị chặn khi lưu. Phải đỏ ở test, không phải ở production.
  3. **Chuyển trạng thái đi qua engine** và báo lỗi PHÂN BIỆT được nguyên nhân: sai
     đường đi (cấu hình) khác với thiếu quyền (vai trò) — đúng cái mà bug "QTV đủ quyền
     vẫn không duyệt được" từng không phân biệt nổi.

Run:
  bench --site miyano run-tests --app assetcore --module assetcore.tests.integration.test_shared_state
"""
from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.services.shared.errors import ServiceError
from assetcore.services.shared.state import (
    ROLLUP_MAP,
    action_for,
    allowed_next_states,
    current_state,
    rollup_coverage_gaps,
    rollup_status,
    state_field,
    transition_to,
)
from assetcore.tests._helpers._asset_cleanup import purge_asset, purge_category_by_name

_CAT_NAME = "SharedState Test Category"


class TestStateFieldResolution(FrappeTestCase):
    """Trục trạng thái được đọc từ khai báo workflow, không phải đoán theo tên."""

    def test_ac_asset_uses_lifecycle_status_not_workflow_state(self) -> None:
        self.assertEqual(state_field("AC Asset"), "lifecycle_status")

    def test_operational_doctypes_use_workflow_state(self) -> None:
        for doctype in ("PM Work Order", "Asset Repair", "Incident Report"):
            self.assertEqual(state_field(doctype), "workflow_state", doctype)

    def test_doctype_without_workflow_returns_blank(self) -> None:
        self.assertEqual(state_field("AC Asset Category"), "")


class TestRollupMap(FrappeTestCase):
    """`status` dẫn xuất phải phủ hết state và không bịa giá trị."""

    def test_every_workflow_state_has_a_rollup(self) -> None:
        gaps = rollup_coverage_gaps()
        self.assertEqual(gaps, [], "State thiếu ánh xạ rollup:\n  - " + "\n  - ".join(gaps))

    def test_rollup_values_stay_inside_the_field_enum(self) -> None:
        """Giá trị rollup phải nằm trong enum của chính field `status` trên doctype đó."""
        for doctype, mapping in ROLLUP_MAP.items():
            options = set(
                (frappe.get_meta(doctype).get_field("status").options or "").split("\n")
            )
            outside = sorted(set(mapping.values()) - options)
            self.assertEqual(
                outside, [],
                f"{doctype}: rollup sinh giá trị ngoài enum `status` ⇒ lưu sẽ bị chặn: {outside}",
            )

    def test_unmapped_doctype_is_identity(self) -> None:
        # 10/12 doctype có `status` trùng khớp tên state ⇒ không cần khai trong bảng.
        self.assertEqual(rollup_status("PM Work Order", "In Progress"), "In Progress")

    def test_capa_collapses_detailed_states(self) -> None:
        self.assertEqual(rollup_status("IMM CAPA Record", "Investigating"), "In Progress")
        self.assertEqual(rollup_status("IMM CAPA Record", "Verification"), "Pending Verification")

    def test_overdue_is_never_produced_by_rollup(self) -> None:
        # 'Overdue' suy từ THỜI HẠN chứ không từ trạng thái — rollup không được ghi đè.
        self.assertNotIn("Overdue", set(ROLLUP_MAP["IMM CAPA Record"].values()))

    def test_unknown_state_passes_through_instead_of_blanking(self) -> None:
        self.assertEqual(rollup_status("AC Asset", "Trạng Thái Lạ"), "Trạng Thái Lạ")


class TestTransitionThroughEngine(FrappeTestCase):
    """Chuyển trạng thái qua workflow engine + thông điệp lỗi phân biệt nguyên nhân."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": _CAT_NAME,
            "category_code": "TEST-CAT-SHSTATE",
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)

        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            cls.asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": "SharedState Asset",
                "asset_category": cls.cat.name,
                "lifecycle_status": "Commissioned",
                "manufacturer_sn": "SHSTATE-SN-1",
            }).insert(ignore_permissions=True).name
        finally:
            frappe.flags.in_install = prev
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(getattr(cls, "asset", None))
        purge_category_by_name(_CAT_NAME)
        frappe.db.commit()
        super().tearDownClass()

    def test_current_state_reads_the_bound_field(self) -> None:
        doc = frappe.get_doc("AC Asset", self.asset)
        self.assertEqual(current_state(doc), "Commissioned")

    def test_allowed_next_states_come_from_the_engine(self) -> None:
        doc = frappe.get_doc("AC Asset", self.asset)
        nxt = allowed_next_states(doc)
        # Administrator có mọi vai trò ⇒ phải thấy ít nhất một đường đi từ 'Commissioned'.
        self.assertTrue(nxt, "Engine không trả transition nào từ 'Commissioned'")
        self.assertNotIn("Commissioned", nxt, "Không được tự chuyển về chính trạng thái hiện tại")

    def test_action_for_resolves_a_real_action_name(self) -> None:
        doc = frappe.get_doc("AC Asset", self.asset)
        target = allowed_next_states(doc)[0]
        self.assertTrue(action_for(doc, target), f"Không tra được tên hành động tới '{target}'")

    def test_impossible_target_raises_bad_state_not_permission(self) -> None:
        doc = frappe.get_doc("AC Asset", self.asset)
        with self.assertRaises(ServiceError) as ctx:
            transition_to(doc, "Trạng Thái Không Có Trong Quy Trình")
        self.assertEqual(ctx.exception.code, "BAD_STATE")

    def test_doctype_without_workflow_raises_business_rule(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            transition_to(frappe.get_doc("AC Asset Category", self.cat.name), "Bất Kỳ")
        self.assertEqual(ctx.exception.code, "BUSINESS_RULE")

    def test_transition_actually_moves_the_state(self) -> None:
        doc = frappe.get_doc("AC Asset", self.asset)
        target = allowed_next_states(doc)[0]
        transition_to(doc, target)
        self.assertEqual(
            frappe.db.get_value("AC Asset", self.asset, "lifecycle_status"), target
        )

    def test_server_side_transition_passes_the_br_00_02_guard(self) -> None:
        """Regression: guard BR-00-02 nhận diện workflow qua ``form_dict['cmd']``.

        Gọi từ mã phía máy chủ (service/patch/scheduler) không có ``cmd`` nên guard chặn
        oan — đúng đường đi mà ADR-CORE-01 bắt buộc lại bị chính app khoá. Helper phải
        bật cờ ``in_workflow_apply`` thì mới qua được, và phải TRẢ LẠI cờ sau đó.
        """
        self.assertFalse(
            frappe.flags.get("in_workflow_apply"),
            "Cờ đã bật sẵn trước khi gọi ⇒ test không chứng minh được điều gì.",
        )
        doc = frappe.get_doc("AC Asset", self.asset)
        target = allowed_next_states(doc)[0]
        transition_to(doc, target)  # KHÔNG được ném ValidationError của BR-00-02
        self.assertFalse(
            frappe.flags.get("in_workflow_apply"),
            "Helper làm rò cờ in_workflow_apply sang phần còn lại của request ⇒ mọi thay "
            "đổi lifecycle_status sau đó sẽ lọt qua guard BR-00-02.",
        )
