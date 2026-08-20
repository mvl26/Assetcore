# Copyright (c) 2026, AssetCore Team
"""Hệ thống mã (``system`` URI) — SSoT cho mọi ``Coding``/``Identifier`` của AssetCore.

Vì sao tập trung một chỗ (SPEC §12)
------------------------------------
Trong FHIR, ``system`` là thứ làm một mã có nghĩa: ``{"code": "47821"}`` không nói
lên điều gì, ``{"system": "...gmdn", "code": "47821"}`` mới tra cứu được. Rải chuỗi
URI khắp các mapper là cách chắc chắn nhất để hai resource cùng nói về một thứ mà
khai hai ``system`` khác nhau — client bên ngoài sẽ coi đó là hai khái niệm.

Quy ước URI
-----------
Chuẩn quốc tế thì dùng URI **chính thức của tổ chức ban hành**. Khái niệm riêng của
AssetCore mới dùng namespace ``http://assetcore.vn/fhir/...``.

⚠️ ``SYS_UDI_ISSUER`` chưa chốt: ``Device.udiCarrier.issuer`` bắt buộc phải là cơ
quan cấp UDI (GS1 hay HIBCC), mà ``udi_code`` hiện là văn bản tự do — không có
trường nguồn để suy ra. Xem SPEC §17 Q3. Cho tới khi user chốt, mapper **không
được bịa** giá trị này.
"""

from __future__ import annotations

# ── Chuẩn quốc tế — URI do chính tổ chức ban hành công bố ─────────────────────
#: GMDN — Global Medical Device Nomenclature.
SYS_GMDN = "urn:oid:2.16.840.1.113883.6.257"
#: GS1 — cơ quan cấp UDI phổ biến nhất.
SYS_UDI_GS1 = "http://hl7.org/fhir/NamingSystem/gs1-di"
#: HIBCC — cơ quan cấp UDI thay thế.
SYS_UDI_HIBCC = "http://hl7.org/fhir/NamingSystem/hibcc-dI"
#: Loại định danh (HL7 v2-0203) — dùng cho ``Identifier.type``.
SYS_IDENTIFIER_TYPE = "http://terminology.hl7.org/CodeSystem/v2-0203"

#: ⚠️ CHƯA CHỐT — SPEC §17 Q3. Mapper phải bỏ qua ``udiCarrier`` khi giá trị này là
#: ``None``, KHÔNG được đoán cơ quan cấp.
SYS_UDI_ISSUER: str | None = None

# ── Namespace riêng của AssetCore ─────────────────────────────────────────────
_BASE = "http://assetcore.vn/fhir"

#: Mã tài sản nội bộ (``AC Asset.asset_code``).
SYS_ASSET_CODE = f"{_BASE}/identifier/asset-code"
#: Mã bản ghi Frappe (``name``) — định danh kỹ thuật, không phải mã nghiệp vụ.
SYS_DOCNAME = f"{_BASE}/identifier/docname"
#: Trạng thái vòng đời nội bộ, khi không ánh xạ trọn vẹn sang valueset R4.
SYS_LIFECYCLE_STATUS = f"{_BASE}/CodeSystem/lifecycle-status"
#: Phân loại thiết bị theo NĐ98 (A/B/C/D).
SYS_NGHI_DINH_98 = f"{_BASE}/CodeSystem/nd98-device-class"
#: Mã thông báo nghiệp vụ (registry ``assetcore/utils/messages.py``).
SYS_MESSAGE_CODE = f"{_BASE}/CodeSystem/message-code"
#: Tiền tố profile ``StructureDefinition`` của AssetCore.
PROFILE_BASE = f"{_BASE}/StructureDefinition"


def profile(name: str) -> str:
    """URL canonical của một profile AssetCore.

    Args:
        name: tên profile, vd ``ac-device``.

    Returns:
        URL canonical đầy đủ để đặt vào ``Resource.meta.profile``.
    """
    return f"{PROFILE_BASE}/{name}"
