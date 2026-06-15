# Copyright (c) 2026, AssetCore Team and contributors
# assetcore.api.mobile — endpoint vận hành nội bộ cho initiative AssetCore Mobile (backend-for-mobile).
#
# Lưu ý phạm vi (ADR-MOBILE-001):
#   - KHÔNG phải hợp đồng API cho app native — app native CHỈ gọi các endpoint
#     nghiệp vụ hiện hữu (imm00/imm08/imm09/imm11/imm12) + provider OAuth2 của Frappe.
#   - Module này chứa các tiện ích admin-only (pre-flight / chẩn đoán) phục vụ
#     Phase-A→B bridge. Tất cả READ-ONLY, gate System Manager, KHÔNG tạo/sửa record.
