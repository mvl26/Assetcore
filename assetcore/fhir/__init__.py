# Copyright (c) 2026, AssetCore Team
"""Bề mặt HL7 FHIR R4 (4.0.1) của AssetCore — SPEC ``docs/fhir/00_SPEC_FHIR_MIGRATION.md``.

Ranh giới của gói này (SPEC §12)
--------------------------------
* Mapper **chỉ dịch hình dạng dữ liệu**. Nghiệp vụ sống ở ``assetcore/services/``;
  truy vấn sống ở ``services/``/``repositories/``. Không SQL trần ở đây.
* **CẤM ``import assetcore.utils.response``** trong bất kỳ file nào dưới gói này.
  FHIR trả **resource TRẦN** — bọc envelope ``{"success": …}`` là vi phạm chuẩn
  (SPEC §6.2). Guard ``tests/guards/test_fhir_no_envelope.py`` khoá luật này.
* Mọi giá trị mã hoá cứng đi qua :mod:`assetcore.fhir.terminology`.

Vì sao tách hẳn khỏi ``api/``
-----------------------------
``api/`` là RPC Frappe với envelope ``{success, data}`` và mã lỗi nằm trong **thân
HTTP 200**. FHIR đòi ngược lại: thân là resource trần, mã lỗi nằm ở **status
line**. Hai hợp đồng loại trừ nhau, nên chúng phải là hai cây mã tách bạch —
dùng chung tầng service ở dưới.
"""
