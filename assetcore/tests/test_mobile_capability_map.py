"""TC-MOB-CAP-01..06 — Guard hợp đồng quyền mobile: 10 endpoint MVP ↔ CAPABILITY_MAP (A14).

Biến claim "capability mỗi flow MVP khớp CAPABILITY_MAP" (manually verified ở
`docs/mobile/11-phase-a-exit.md §1` matrix + checklist A-5 + §4 row 'Capability khớp
SSoT') thành GUARD CHẠY ĐƯỢC, máy-đọc.

KHÁC các suite OAS khác:
  - test_mobile_oas (TC-MOB-OAS-*): contract-identity của *yaml* (operationId / $ref /
    orphan / error-response) — KHÔNG đọc rbac binding.
  - test_oas_generator / test_oas_signatures: AUTO-GEN AssetCore spec — KHÔNG đọc rbac.
  ⇒ 3 suite đó KHÔNG hồi quy vì A14 (chúng không import rbac.CAPABILITY_MAP).

Mức guard (chủ ý — KHÔNG re-implement gate):
  - Khẳng định **ma trận endpoint→capability** (11 §1) ÁNH XẠ ĐÚNG cap như matrix.
  - Khẳng định **mỗi cap TỒN TẠI trong CAPABILITY_MAP** (import rbac.py SSoT) + binding
    `(DocType, ptype)` KHỚP ĐÚNG matrix. Cap thiếu / đổi-binding = hard-fail (= drift
    hợp đồng quyền).
  - Anti-cap-creep: 0 cap MỚI vì mobile — `len(CAPABILITY_MAP)==98` + cap-set version
    == 'v104.e46d05d9a66d' (bench-verified) ⇒ mọi cap mobile dùng ⊆ tập hiện hữu (chống
    'hệ quyền thứ 2' — ADR-MOBILE-001 (b)).
  - Drift-guard 2 chiều doc↔source: version đóng băng trong test = version doc 11
    §1/§3/§4/§Tham-chiếu. Nếu cap-set đổi (thêm/bớt/đổi cap) → test ĐỎ → buộc [BA]
    cập nhật matrix + version trước khi qua.

KHÔNG hardcode tuple `(DocType, ptype)` ngoài 1 bảng `_EXPECTED_MATRIX` có chú giải
`@source file:line` cho từng dòng. KHÔNG so DocPerm runtime (gate THỰC do
`frappe.has_permission` quyết định khi user gọi — không thuộc phạm vi hợp đồng A14).
List-endpoint gate (read) nằm trong service/handle + permission_query_conditions (CHỦ Ý
— `asset_list_count_drill_technician`); guard này CHỈ chốt cap-binding của matrix.

Run: bench --site miyano run-tests --module assetcore.tests.test_mobile_capability_map
"""
from __future__ import annotations

import unittest

from assetcore.services.shared.rbac import (
    CAP_SET_VERSION,
    CAPABILITY_MAP,
)

# ── Đóng băng cap-set (drift-guard 2 chiều doc↔source) ───────────────────────────
# Giá trị NÀY PHẢI khớp doc `docs/mobile/11-phase-a-exit.md` (§1 legend · A-5 · §4
# row 'Capability khớp SSoT' · §Tham chiếu chéo) VÀ `03-auth-oauth2.md §3 / §3.2`.
# @source bench-verified: `bench --site miyano execute
#   assetcore.services.shared.rbac._compute_cap_set_version` → "v104.e46d05d9a66d"
# (= rbac.py:144-153 _compute_cap_set_version → f"v{len(MAP)}.{sha256(sorted keys)[:12]}").
# Đổi cap-set (thêm/bớt/đổi cap) ⇒ version đổi ⇒ test ĐỎ ⇒ buộc [BA] cập nhật
# matrix 11 §1 + version trong các doc trên + dòng dưới TRƯỚC khi qua.
# Re-freeze IMM-03 vòng 19 (ADR-IMM-03-05): +6 cap purchase.{read,write,create,
# delete,submit,cancel} bind AC Purchase → 98→104 (bench-verified, KHÔNG bịa hash).
_EXPECTED_CAP_SET_VERSION = "v104.e46d05d9a66d"
_EXPECTED_CAP_COUNT = 104

# ── Ma trận endpoint MVP → capability (11 §1, 6 flow) ───────────────────────────
# Mỗi dòng: dotted-path endpoint → (capability, (DocType, ptype) kỳ vọng).
# (DocType, ptype) chú giải @source theo từng cap — KHÔNG hardcode rải rác; tất cả
# tuple kỳ vọng nằm DUY NHẤT trong bảng này.
#   @source endpoint  : assetcore/api/imm{00,08,09,11,12}.py (grep '^def …')
#   @source cap-binding: assetcore/services/shared/rbac.py
#     - asset.read           → ('AC Asset','read')              rbac.py:88-91 (Asset prefix)
#     - corrective.create    → ('Incident Report','create')     rbac.py:88-91 (Corrective prefix)
#     - corrective.read      → ('Incident Report','read')       rbac.py:88-91
#     - pm.create            → ('PM Work Order','create')       rbac.py:88-91 (PM prefix)
#     - pm.read              → ('PM Work Order','read')          rbac.py:88-91
#     - repair.create        → ('Asset Repair','create')        rbac.py:88-91 (Repair prefix)
#     - repair.read          → ('Asset Repair','read')          rbac.py:88-91
#     - calibration.create   → ('IMM Asset Calibration','create') rbac.py:88-91 (Calibration prefix)
# (8 cap auto-gen từ _DOMAIN_PRIMARY × _PTYPES; KHÔNG cap mobile-riêng.)
_EXPECTED_MATRIX: dict[str, tuple[str, tuple[str, str]]] = {
    # Flow 2 — Quét QR → hồ sơ thiết bị (asset.read ×3)  @source 11 §1 Flow 2
    "assetcore.api.imm00.resolve_qr_token":      ("asset.read", ("AC Asset", "read")),
    "assetcore.api.imm00.get_asset_scan_info":   ("asset.read", ("AC Asset", "read")),
    "assetcore.api.imm00.get_asset":             ("asset.read", ("AC Asset", "read")),
    # Flow 3 — Báo hỏng  @source 11 §1 Flow 3 (imm12.py:55 _CAP_REPORT)
    "assetcore.api.imm12.report_incident":       ("corrective.create", ("Incident Report", "create")),
    # Flow 4 — Yêu cầu PM / CM / Hiệu chuẩn  @source 11 §1 Flow 4
    "assetcore.api.imm08.create_pm_work_order":  ("pm.create", ("PM Work Order", "create")),
    "assetcore.api.imm09.create_repair_work_order": ("repair.create", ("Asset Repair", "create")),
    "assetcore.api.imm11.create_calibration":    ("calibration.create", ("IMM Asset Calibration", "create")),
    # Flow 5 — "Phiếu của tôi" (3 list, *.read)  @source 11 §1 Flow 5
    "assetcore.api.imm08.list_pm_work_orders":   ("pm.read", ("PM Work Order", "read")),
    "assetcore.api.imm09.list_repair_work_orders": ("repair.read", ("Asset Repair", "read")),
    "assetcore.api.imm12.list_incidents":        ("corrective.read", ("Incident Report", "read")),
}

# Phân phối cap kỳ vọng theo matrix 11 §1 (acceptance #1):
#   asset.read×3 / corrective.create / pm.create / repair.create / calibration.create
#   / pm.read / repair.read / corrective.read  = 10 dòng, 8 cap distinct.
_EXPECTED_DISTINCT_CAPS = {
    "asset.read", "corrective.create", "pm.create", "repair.create",
    "calibration.create", "pm.read", "repair.read", "corrective.read",
}


class TestMobileCapabilityMap(unittest.TestCase):
    """A14 — endpoint↔CAPABILITY_MAP binding guard (matrix 11 §1 ↔ rbac.py SSoT)."""

    # AC#1 — 10 endpoint MVP ánh xạ đúng capability như matrix 11 §1.
    def test_mob_cap_01_matrix_shape(self):
        self.assertEqual(
            len(_EXPECTED_MATRIX), 10,
            "Matrix MVP phải đúng 10 endpoint (11 §1). Đổi số endpoint = đổi hợp đồng "
            "→ cập nhật matrix doc + bảng này cùng lúc.",
        )
        caps = [cap for cap, _b in _EXPECTED_MATRIX.values()]
        # asset.read xuất hiện đúng 3 lần (Flow 2 ×3); còn lại 1 lần mỗi cap.
        self.assertEqual(caps.count("asset.read"), 3, "asset.read phải dùng ×3 (Flow 2).")
        self.assertEqual(
            set(caps), _EXPECTED_DISTINCT_CAPS,
            "Tập cap distinct phải khớp matrix 11 §1 (8 cap): asset.read / "
            "corrective.create / pm.create / repair.create / calibration.create / "
            "pm.read / repair.read / corrective.read.",
        )

    # AC#2 — MỖI cap TỒN TẠI trong CAPABILITY_MAP (SSoT) + binding khớp ĐÚNG matrix.
    def test_mob_cap_02_each_cap_exists_and_binding_matches(self):
        for endpoint, (cap, expected_binding) in _EXPECTED_MATRIX.items():
            with self.subTest(endpoint=endpoint, cap=cap):
                self.assertIn(
                    cap, CAPABILITY_MAP,
                    f"Cap '{cap}' (cho {endpoint}) KHÔNG có trong CAPABILITY_MAP — "
                    f"drift hợp đồng quyền (cap thiếu). Sửa rbac.py HOẶC matrix 11 §1.",
                )
                self.assertEqual(
                    CAPABILITY_MAP[cap], expected_binding,
                    f"Binding cap '{cap}' lệch: CAPABILITY_MAP={CAPABILITY_MAP[cap]} "
                    f"≠ matrix {expected_binding} ({endpoint}). Đổi-binding = drift "
                    f"hợp đồng quyền → cập nhật matrix 11 §1 + bảng này cùng lúc.",
                )

    # AC#3 — anti-cap-creep: 0 cap MỚI vì mobile (len==97).
    def test_mob_cap_03_no_cap_creep_count(self):
        self.assertEqual(
            len(CAPABILITY_MAP), _EXPECTED_CAP_COUNT,
            f"len(CAPABILITY_MAP)={len(CAPABILITY_MAP)} ≠ {_EXPECTED_CAP_COUNT}. "
            "Mobile KHÔNG được thêm cap (chống 'hệ quyền thứ 2' — ADR-MOBILE-001 b). "
            "Nếu cap-set hợp lệ đổi → [BA] cập nhật version + count ở doc + bảng này.",
        )
        # Mọi cap mobile dùng ⊆ tập hiện hữu (không có cap mobile-riêng).
        self.assertTrue(
            _EXPECTED_DISTINCT_CAPS.issubset(set(CAPABILITY_MAP)),
            "Có cap mobile NGOÀI CAPABILITY_MAP — cấm 'hệ quyền thứ 2'.",
        )

    # AC#3/#4 — cap-set version đóng băng = bench-verified = giá trị doc (drift-guard).
    def test_mob_cap_04_cap_set_version_frozen(self):
        self.assertEqual(
            CAP_SET_VERSION, _EXPECTED_CAP_SET_VERSION,
            f"CAP_SET_VERSION='{CAP_SET_VERSION}' ≠ đóng băng "
            f"'{_EXPECTED_CAP_SET_VERSION}'. Cap-set đã đổi (thêm/bớt/đổi cap) ⇒ "
            "BUỘC [BA] cập nhật matrix 11 §1 + version ở 11 §1/§3/§4/§Tham-chiếu + "
            "03 §3/§3.2 + bảng EXPECTED này TRƯỚC khi qua (drift doc↔source).",
        )

    # AC#4 — count nhúng trong version stamp khớp count thật (phòng version-format drift).
    def test_mob_cap_05_version_embeds_real_count(self):
        # CAP_SET_VERSION = f"v{len(MAP)}.{digest}" (rbac.py:150) → prefix 'v98'.
        self.assertTrue(
            CAP_SET_VERSION.startswith(f"v{len(CAPABILITY_MAP)}."),
            f"version stamp '{CAP_SET_VERSION}' không nhúng count thật "
            f"{len(CAPABILITY_MAP)} — format rbac.py đã drift.",
        )
        self.assertEqual(
            CAP_SET_VERSION, _EXPECTED_CAP_SET_VERSION.split(".")[0] + "." +
            _EXPECTED_CAP_SET_VERSION.split(".", 1)[1],
            "version stamp không khớp dạng đóng băng.",
        )

    # AC#2 — không có dòng matrix nào trỏ cap không-tồn-tại (mutation-guard tổng).
    def test_mob_cap_06_all_matrix_caps_resolve(self):
        missing = sorted(
            cap for cap, _b in _EXPECTED_MATRIX.values() if cap not in CAPABILITY_MAP
        )
        self.assertEqual(
            missing, [],
            f"Cap matrix thiếu trong CAPABILITY_MAP: {missing}. Mọi cap MVP PHẢI "
            "resolve về SSoT (rbac.py).",
        )
