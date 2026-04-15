# Mã Nguồn Chuẩn Bị Triển Khai Thực Tế (Source Code Build) - IMM-04

Dựa trên thiết kế Dev Spec, dưới đây là phiên bản Code thực tiễn nhất (Production-ready) để đưa thẳng vào khung máy chủ của Frappe/ERPNext. Gói này cung cấp các đoạn Code lõi liên quan đến Data Schema, Workflow Json và Python Hook cấp độ server.

---

## 1. JSON DocType Definition: `Asset Commissioning Process`
Toàn bộ Cấu hình Field này có thể ném vào file `asset_commissioning.json` trong source core của module (được tự động sinh bởi `bench new-doctype`).

```json
{
 "actions": [],
 "autoname": "format:IMM04-.YY.-.MM.-.#####",
 "creation": "2026-04-15 10:00:00.000000",
 "doctype": "DocType",
 "document_type": "Document",
 "engine": "InnoDB",
 "field_order": [
  "po_reference",
  "master_item",
  "vendor",
  "installation_break",
  "clinical_dept",
  "expected_installation_date",
  "installation_date",
  "identification_break",
  "vendor_serial_no",
  "internal_tag_qr",
  "baseline_tests_tab",
  "baseline_tests",
  "qa_attributes_tab",
  "is_radiation_device",
  "qa_license_doc",
  "final_asset"
 ],
 "fields": [
  {
   "fieldname": "po_reference",
   "fieldtype": "Link",
   "label": "Lệnh mua gốc",
   "options": "Purchase Order",
   "reqd": 1
  },
  {
   "fieldname": "master_item",
   "fieldtype": "Link",
   "label": "Model Nhập kho",
   "options": "Item",
   "reqd": 1
  },
  {
   "fieldname": "baseline_tests",
   "fieldtype": "Table",
   "label": "Lưới Check an toàn",
   "options": "Commissioning Checklist",
   "reqd": 1
  },
  {
   "fieldname": "vendor_serial_no",
   "fieldtype": "Data",
   "label": "Serial Hàng",
   "reqd": 1,
   "search_index": 1,
   "unique": 1
  },
  {
   "fieldname": "final_asset",
   "fieldtype": "Link",
   "label": "Asset Sinh ra",
   "options": "Asset",
   "read_only": 1
  }
 ],
 "is_submittable": 1,
 "modified": "2026-04-15 10:05:00.000000",
 "module": "Assetcore",
 "name": "Asset Commissioning",
 "naming_rule": "Expression",
 "owner": "Administrator",
 "permissions": [
  {
   "create": 1,
   "write": 1,
   "read": 1,
   "role": "HTM Technician"
  },
  {
   "submit": 1,
   "read": 1,
   "role": "VP_Block2"
  }
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "track_changes": 1,
 "track_views": 1
}
```

---

## 2. Mã Code Python Native (Server Script Controllers)

Tệp Controller gắn dính với DocType: `apps/assetcore/assetcore/assetcore/doctype/asset_commissioning/asset_commissioning.py`

```python
# Copyright (c) 2026, AssetCore Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class AssetCommissioning(Document):

	# [Event: Xác thực Input Lõi - Không dùng Client giả]
	def validate(self):
		self.validate_checklist_completion()
		self.validate_unique_serial()
		self.block_release_if_nc_open()

	# [Requirement 3.1: Hàm Validate Checklist]
	def validate_checklist_completion(self):
		if self.workflow_state == "Initial_Inspection":
			if not self.baseline_tests:
				frappe.throw("Bắt buộc phải điền bằng lưới Baseline Test trước khi thẩm định!")
			for row in self.baseline_tests:
				if not row.test_result:
					frappe.throw(f"Tại dòng {row.idx}, Bắt buộc phải chọn [Đạt/Không Đạt].")
				if row.test_result == "Fail" and not row.fail_note:
					frappe.throw("Vì Test Thất Bại, dòng {0} Bắt buộc Điền lý do rớt vào ô Ghi Chú!".format(row.idx))

	# [Requirement 3.2: Hàm Validate Số ID]
	def validate_unique_serial(self):
		if self.vendor_serial_no:
			# Tìm đè chéo bên bảng Asset Core
			existing_asset = frappe.db.get_value("Asset", {"custom_vendor_serial": self.vendor_serial_no}, "name")
			if existing_asset:
				frappe.throw(f"Sốc: Mã Serial {self.vendor_serial_no} đã xuất hiện trên máy {existing_asset}. Nghi vấn hàng nhái!")

	# [Requirement 3.3: Chặn Thẻ Clinical Release Mếu Còn Cặn DOA (Rác)]
	def block_release_if_nc_open(self):
		if self.workflow_state == "Clinical_Release":
			# Chọc DB truy ID NC
			open_ncs = frappe.db.count("Asset QA Non Conformance", {
				"ref_commissioning": self.name,
				"resolution_status": "Open"
			})
			if open_ncs > 0:
				frappe.throw("Cấm Phê Chuẩn! Hiện có phiếu rủi ro hỏng hóc (NON-CONFORMANCE) chưa được Hãng xử lý xong đính kèm với lệnh này.")

	# [Event: MINTING ENGINE - Sinh Hệ Thống Tài Khóa Cố Định]
	def on_submit(self):
		# Chỉ sinh mã nếu được Chữ ký Giám đốc mở Gate
		if self.workflow_state != "Clinical_Release":
			frappe.throw("Trạng thái chưa chín muồi. Không thể khởi tạo Asset.")

		# Tạo Dòng Đời Thực Asset Mới (Băm Database)
		new_asset = frappe.get_doc({
			"doctype": "Asset",
			"item_code": self.master_item,
			"location": self.clinical_dept,
			"purchase_receipt": self.po_reference,
			"available_for_use_date": nowdate(),
			# Đẩy mã giáp Custom sang
			"custom_vendor_serial": self.vendor_serial_no,
			"custom_internal_qr": self.internal_tag_qr,
			"custom_comm_ref": self.name,
			"status": "In Use"
		})
		
		# Nhúng sâu qua tường lửa Kế toán
		new_asset.insert(ignore_permissions=True)
		
		# Lưu ID lại ngược vào Dọc Mẫu Gốc (Traceability Đóng Cửa)
		self.db_set('final_asset', new_asset.name)
		
		# [Requirement 4: Bắn Báo Cáo Event Hook]
		frappe.publish_realtime('imm04_asset_minted', message={'asset_id': new_asset.name, 'commissioning_form': self.name})
```

---

## 3. Workflow JSON (Config Core Giao thức chuyển Node)
Config tĩnh này export/import cực kỳ chuẩn hóa. Tương xứng State Machine.

```json
{
 "name": "imm_04_workflow",
 "doctype": "Workflow",
 "document_type": "Asset Commissioning",
 "is_active": 1,
 "override_status": 1,
 "send_email_alert": 0,
 "states": [
  {
   "allow_edit": "HTM Technician",
   "doc_status": 0,
   "state": "Draft",
   "update_field": ""
  },
  {
   "allow_edit": "Biomed Engineer",
   "doc_status": 0,
   "state": "Initial_Inspection",
   "update_field": ""
  },
  {
   "allow_edit": "VP_Block2",
   "doc_status": 1,
   "state": "Clinical_Release",
   "update_field": ""
  }
 ],
 "transitions": [
  {
   "action": "Submit_For_Verify",
   "allow": "HTM Technician",
   "next_state": "Pending_Doc_Verify",
   "state": "Draft"
  },
  {
   "action": "Approve_Release",
   "allow": "VP_Block2",
   "next_state": "Clinical_Release",
   "state": "Initial_Inspection"
  }
 ]
}
```

---

## 4. API Endpoint: `api.py` (Kênh Mở Rộng Ngoài Biên - External Hook)
Ví dụ tích hợp: Phục vụ Scanner súng đọc mã vạch lấy API dữ liệu từ Máy. (Hoặc Cục An Toàn bức xạ).

```python
import frappe

@frappe.whitelist() # Mở trạm bắt Endpoint Restful API
def get_commissioning_by_barcode(qr_code_internal):
	"""
	API GET: /api/method/assetcore.api.get_commissioning_by_barcode
	Trả về lịch sử khám bệnh lúc sơ sinh của 1 cái máy bằng cách quét mã vạch.
	"""
	if not qr_code_internal:
		return {"status": "error", "message": "No QR Scanned"}

	# Quét trên SQL tìm thằng đẻ ra con Mã vạch này
	record = frappe.db.get_value("Asset Commissioning", {"internal_tag_qr": qr_code_internal}, "name")
	
	if not record:
		return {"status": "error", "message": "Lỗ hổng: Không tồn tại trong kho IMM-04 (Có thể là Máy Ảo)"}

	doc = frappe.get_doc("Asset Commissioning", record)
	
	return {
		"status": "success",
		"asset_birth_data": {
			"commissioning_id": doc.name,
			"vendor_name": doc.vendor,
			"passed_qa": doc.workflow_state == "Clinical_Release",
			"installation_date": doc.installation_date,
			"baseline_tests": [row.as_dict() for row in doc.baseline_tests]
		}
	}
```
