# Copyright (c) 2026, AssetCore Team
"""Guard: ``CapabilityStatement`` khớp TUYỆT ĐỐI bảng dispatch — SPEC §13, §15.

Class-of-bug đóng ở đây
------------------------
``/metadata`` là cửa duy nhất để một client **chưa từng nghe tên AssetCore** biết
server làm được gì. Nếu bản khai lệch khỏi mã thật, client tin lời khai, gọi vào,
nhận 404 — hỏng đúng thứ mà cả đợt FHIR nhắm tới.

Cùng khuôn với ``uiAuditDocParity`` ở phía FE: con số trong một câu văn không tự đỏ
được, nên phải có một bên **sinh ra** bên kia rồi khoá hai bên bằng test.
"""

from __future__ import annotations

import unittest

from assetcore.fhir import dispatch
from assetcore.fhir.conformance.capability import FHIR_VERSION, build_capability_statement


class TestFhirCapabilityParity(unittest.TestCase):
    """Bản khai năng lực == bảng dispatch, không thừa không thiếu."""

    def setUp(self):
        self.cs = build_capability_statement()
        self.rest = self.cs["rest"][0]

    def test_shape_is_a_valid_capability_statement(self):
        """Các trường R4 bắt buộc phải có mặt và đúng giá trị."""
        self.assertEqual(self.cs["resourceType"], "CapabilityStatement")
        self.assertEqual(self.cs["status"], "active")
        self.assertEqual(self.cs["kind"], "instance")
        self.assertEqual(self.cs["fhirVersion"], FHIR_VERSION)
        self.assertEqual(self.rest["mode"], "server")

    def test_declared_types_equal_registered_types(self):
        """Không thừa, không thiếu — so khớp tập hợp, không so số lượng."""
        declared = sorted(r["type"] for r in self.rest["resource"])
        self.assertEqual(
            declared, dispatch.resource_types(),
            "CapabilityStatement khai lệch bảng dispatch. Bản khai được SINH từ bảng — "
            "lệch nghĩa là có ai đó viết tay vào bản khai.",
        )

    def test_declared_interactions_equal_registered_interactions(self):
        """Mỗi type khai đúng tập tương tác đã đăng ký."""
        registry = dispatch.registry()
        for block in self.rest["resource"]:
            declared = {i["code"] for i in block["interaction"]}
            expected = set(registry[block["type"]].interactions)
            self.assertEqual(
                declared, expected,
                f"Type '{block['type']}' khai tương tác lệch bảng dispatch.",
            )

    def test_no_interaction_outside_r4_valueset(self):
        """Chỉ được khai tương tác thuộc valueset R4 — bịa mã làm client bỏ qua cả khối."""
        for block in self.rest["resource"]:
            for i in block["interaction"]:
                self.assertIn(i["code"], dispatch.INTERACTION_ORDER)

    def test_capability_is_deterministic(self):
        """Hai lần sinh cho cùng cấu trúc — bản khai không được phụ thuộc thứ tự import."""
        again = build_capability_statement()
        self.assertEqual(
            [r["type"] for r in self.rest["resource"]],
            [r["type"] for r in again["rest"][0]["resource"]],
        )
