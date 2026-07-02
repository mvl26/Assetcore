# Copyright (c) 2026, AssetCore Team
"""L-18b (audit BaoCao_RaSoat_AssetCore_17062026) — seed master data khởi tạo.

VẤN ĐỀ: trên cài đặt mới, các dropdown bắt buộc (Danh mục / Khoa-Phòng / Vị trí /
Đơn vị tính) RỖNG → người dùng không tạo được tài sản (audit L-18). Patch nạp một
BỘ STARTER tối thiểu, generic.

⚠️ NỘI DUNG LÀ MỒI (starter) — tổ chức nên CHỈNH SỬA/BỔ SUNG sau khi cài cho khớp
   thực tế. Bổ trợ L-18a (quick-create trên form) chứ không thay thế cấu hình BA.

AN TOÀN:
  - IDEMPOTENT: bỏ qua bản ghi đã tồn tại (skip-if-exists theo field định danh).
  - KHÔNG CLOBBER: tuyệt đối không sửa/đụng bản ghi sẵn có của khách hàng.
  - ignore_permissions: chạy ở ngữ cảnh migrate (Administrator).

Chạy tự động khi `bench --site <site> migrate` (đã đăng ký ở patches.txt).
"""
from __future__ import annotations

import frappe

# Giữ TỐI THIỂU + generic. Mỗi nhóm = (doctype, id_field, rows).
_UOMS = [
    {"uom_name": "Cái", "symbol": "cái", "must_be_whole_number": 1, "is_active": 1},
    {"uom_name": "Bộ", "symbol": "bộ", "must_be_whole_number": 1, "is_active": 1},
    {"uom_name": "Chiếc", "symbol": "chiếc", "must_be_whole_number": 1, "is_active": 1},
    {"uom_name": "Hộp", "symbol": "hộp", "must_be_whole_number": 1, "is_active": 1},
    {"uom_name": "Ống", "symbol": "ống", "must_be_whole_number": 1, "is_active": 1},
    {"uom_name": "Lọ", "symbol": "lọ", "must_be_whole_number": 1, "is_active": 1},
    {"uom_name": "Gói", "symbol": "gói", "must_be_whole_number": 1, "is_active": 1},
]
_DEPARTMENTS = [
    {"department_name": "Phòng Vật tư - Thiết bị y tế"},
    {"department_name": "Khoa Hồi sức tích cực (ICU)"},
    {"department_name": "Khoa Chẩn đoán hình ảnh"},
    {"department_name": "Khoa Xét nghiệm"},
]
_LOCATIONS = [
    {"location_name": "Kho Vật tư trung tâm"},
]
_CATEGORIES = [
    {"category_name": "Thiết bị chẩn đoán hình ảnh"},
    {"category_name": "Thiết bị xét nghiệm"},
    {"category_name": "Thiết bị hồi sức - cấp cứu"},
    {"category_name": "Thiết bị theo dõi bệnh nhân"},
]


def _seed(doctype: str, id_field: str, rows: list[dict]) -> int:
    """Nạp idempotent: bỏ qua bản ghi đã tồn tại theo `id_field`. Trả số bản ghi MỚI."""
    created = 0
    for row in rows:
        if frappe.db.exists(doctype, {id_field: row[id_field]}):
            continue
        doc = frappe.new_doc(doctype)
        doc.update(row)
        doc.insert(ignore_permissions=True)
        created += 1
    return created


def execute() -> None:
    total = 0
    total += _seed("AC UOM", "uom_name", _UOMS)
    total += _seed("AC Department", "department_name", _DEPARTMENTS)
    total += _seed("AC Location", "location_name", _LOCATIONS)
    total += _seed("AC Asset Category", "category_name", _CATEGORIES)
    if total:
        frappe.db.commit()
    frappe.logger().info(f"[010_seed_master_data] seeded {total} master-data record(s)")
