# Copyright (c) 2026, AssetCore Team and contributors
# Controller: IMM Recall Notice — IMM-10 Cảnh báo thu hồi thiết bị (Recall/FSCA).
#
# QA Officer tạo/đóng notice trên desk Web (NGOÀI scope mobile); mobile CHỈ đọc
# qua `assetcore.api.imm10.check_asset_recall`. Select options (source/severity/
# status) + mandatory do Frappe core validate — controller không thêm rule.
# `status {Active/Closed}` = collapse có chủ ý của TO-BE 5-state WF-IMM10
# (Spec mobile 47 §3a — Đợt-3 mở rộng workflow KHÔNG vỡ shape đọc).

from frappe.model.document import Document


class IMMRecallNotice(Document):
	pass
