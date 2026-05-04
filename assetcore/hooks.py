app_name = "assetcore"
after_install = "assetcore.setup.install.after_install"
after_migrate = "assetcore.setup.install.after_migrate"
app_title = "AssetCore"
app_publisher = "miyano"
app_description = "Medical Equipment Lifecycle Management (HTM)"
app_email = ""
app_license = "MIT"

# ──────────────────────────────────────────────
# Fixtures — IMM-00 v3 foundation
# ──────────────────────────────────────────────
_IMM_ROLES = [
    "IMM System Admin",
    "IMM Operations Manager",
    "IMM Department Head",
    "IMM Deputy Department Head",
    "IMM Workshop Lead",
    "IMM QA Officer",
    "IMM Biomed Technician",
    "IMM Technician",
    "IMM Document Officer",
    "IMM Storekeeper",
    "IMM Clinical User",
    "IMM Auditor",
    "Vendor Engineer",
]
_IMM_ROLE_PROFILES = [
    "IMM - System Administrator",
    "IMM - Operations Manager",
    "IMM - Department Head",
    "IMM - Deputy Department Head",
    "IMM - Workshop Lead",
    "IMM - Biomed Technician",
    "IMM - Field Technician",
    "IMM - QA Officer",
    "IMM - Internal Auditor",
    "IMM - Storekeeper",
    "IMM - Document Officer",
    "IMM - Clinical User",
    "IMM - Vendor Engineer",
]
fixtures = [
    {"dt": "Role", "filters": [["name", "in", _IMM_ROLES]]},
    {"dt": "Role Profile", "filters": [["name", "in", _IMM_ROLE_PROFILES]]},
    # Has Role rows trong Role Profile — đảm bảo bundle role được export đầy đủ
    {"dt": "Has Role", "filters": [
        ["parenttype", "=", "Role Profile"],
        ["parent", "in", _IMM_ROLE_PROFILES],
    ]},
    {"dt": "IMM SLA Policy"},
    {"dt": "Workspace", "filters": [["name", "in", ["IMM Operations"]]]},
    {"dt": "Workflow", "filters": [["name", "in", [
        "AC Asset Lifecycle",
        "IMM-04 Workflow",
        "IMM-05 Document Workflow",
        "IMM-08 PM Workflow",
        "IMM-09 Repair Workflow",
        "IMM-11 Calibration Workflow",
        "IMM-12 Incident Workflow",
        "IMM-12 RCA Workflow",
    ]]]},
    {"dt": "Workflow State", "filters": [["name", "in", [
        # AC Asset Lifecycle
        "Draft", "Commissioned", "Active",
        "Under Maintenance", "Under Repair", "Calibrating",
        "Out of Service", "Decommissioned",
        # IMM-04 Asset Commissioning
        "Pending Doc Verify", "To Be Installed", "Installing", "Identification",
        "Initial Inspection", "Non Conformance", "Clinical Hold",
        "Re Inspection", "Clinical Release", "Return To Vendor",
        # IMM-05 Asset Document
        "Pending Review", "Rejected", "Archived", "Expired",
        # IMM-08 PM Work Order / IMM-09 Asset Repair / IMM-11 Calibration
        "Open", "In Progress", "Pending–Device Busy", "Overdue",
        "Halted–Major Failure", "Completed", "Cancelled",
        "Assigned", "Diagnosing", "Pending Parts", "In Repair",
        "Pending Inspection", "Cannot Repair",
        "Scheduled", "Sent to Lab", "Certificate Received",
        "Passed", "Failed", "Conditionally Passed",
        # IMM-12 Incident / RCA
        "Acknowledged", "Resolved", "RCA Required", "Closed",
        "RCA In Progress",
    ]]]},
    {"dt": "Workflow Action Master", "filters": [["name", "in", [
        # AC Asset Lifecycle
        "Commission", "Activate",
        "Bắt đầu bảo trì", "Hoàn thành bảo trì",
        "Bắt đầu sửa chữa", "Bắt đầu hiệu chuẩn", "Đưa ra khỏi sử dụng",
        "Hoàn thành sửa chữa", "Không thể sửa chữa",
        "Hiệu chuẩn đạt", "Hiệu chuẩn không đạt",
        "Khôi phục hoạt động", "Sửa chữa lại", "Thanh lý",
        # IMM-04
        "Gửi kiểm tra tài liệu", "Xác nhận đủ tài liệu", "Yêu cầu bổ sung tài liệu",
        "Bắt đầu lắp đặt", "Báo cáo sự cố", "Lắp đặt hoàn thành", "Báo cáo DOA",
        "Bắt đầu kiểm tra", "Phê duyệt phát hành", "Giữ lâm sàng",
        "Báo cáo lỗi baseline", "Gỡ giữ lâm sàng", "Phê duyệt sau tái kiểm",
        "Khắc phục xong", "Trả lại nhà cung cấp",
        # IMM-05
        "Gửi duyệt", "Phê duyệt", "Từ chối", "Gửi lại", "Lưu trữ", "Hủy bỏ",
        # IMM-08
        "Bắt đầu thực hiện", "Đánh dấu trễ hạn", "Hủy phiếu",
        "Hoàn thành PM", "Báo lỗi nghiêm trọng", "Thiết bị bận - hoãn",
        "Tiếp tục thực hiện", "Bắt đầu muộn", "Tiếp tục sau xử lý",
        # IMM-09
        "Phân công KTV", "Bắt đầu chẩn đoán", "Yêu cầu linh kiện",
        "Linh kiện đã nhận - bắt đầu sửa", "Hoàn thành sửa chữa - chờ kiểm tra",
        "Xác nhận hoàn thành", "Kiểm tra thất bại - sửa lại",
        # IMM-11
        "Gửi phòng hiệu chuẩn", "Hủy lịch", "Đạt hiệu chuẩn",
        "Không đạt hiệu chuẩn", "Đạt có điều kiện", "Hủy hiệu chuẩn",
        "Nhận chứng chỉ", "Phê duyệt đạt", "Phê duyệt không đạt",
        "Phê duyệt có điều kiện", "CAPA hoàn tất - chuyển có điều kiện",
        # IMM-12 Incident
        "Tiếp nhận sự cố", "Hủy sự cố", "Bắt đầu xử lý",
        "Đánh dấu đã giải quyết", "Yêu cầu RCA", "Đóng sự cố",
        "RCA hoàn tất - đóng sự cố", "Mở lại điều tra", "Mở lại sự cố",
        # IMM-12 RCA
        "Bắt đầu phân tích RCA", "Hủy RCA", "Hoàn thành RCA",
    ]]]},
]

# ──────────────────────────────────────────────
# Document Events — IMM-00 v3
# ──────────────────────────────────────────────
doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_from_commissioning",
            "assetcore.services.imm11.create_calibration_schedule_from_commissioning",
        ],
    },
    "AC Stock Movement": {
        "on_submit": [
            "assetcore.services.purchase.auto_mark_purchase_received",
        ],
        "on_cancel": [
            "assetcore.services.purchase.auto_unmark_purchase_received",
        ],
    },
    # ─── IMM-01 (Wave 2) — controllers tự gọi service; không cần khai ở đây ───
    # ─── IMM-03 (Wave 2) — validate AC Purchase phải link IMM-03 Decision ───
    "AC Purchase": {
        "validate": "assetcore.services.imm03.validate_ac_purchase_imm_link",
    },
}

# ──────────────────────────────────────────────
# Scheduler — IMM-00 v3 foundation jobs
# ──────────────────────────────────────────────
scheduler_events = {
    "daily": [
        # IMM-00 foundation alerts
        "assetcore.services.imm00.check_capa_overdue",
        "assetcore.services.imm00.check_vendor_contract_expiry",
        "assetcore.services.imm00.check_registration_expiry",
        "assetcore.services.imm00.check_insurance_expiry",
        "assetcore.services.imm00.check_service_contract_expiry",
        # IMM-05 document expiry alerts
        "assetcore.services.imm05.check_document_expiry",
        # IMM-08 PM auto work order generation
        "assetcore.services.imm08.generate_pm_work_orders_from_schedule",
        # IMM-11 Calibration auto WO + expiry check
        "assetcore.services.imm11.create_due_calibration_wos",
        "assetcore.services.imm11.check_calibration_expiry",
        # IMM-12 Incident chronic failure detection
        "assetcore.services.imm12.detect_chronic_failures",
        # IMM-00 Inventory low-stock alert
        "assetcore.services.inventory.check_low_stock",
        # IMM-01 (Wave 2) — overdue Needs Request alert
        "assetcore.services.imm01.check_pending_request_overdue",
        # IMM-02 — overdue Tech Spec drafts
        "assetcore.services.imm02.check_overdue_drafts",
        # IMM-03 — daily checks
        "assetcore.services.imm03.check_avl_expiry",
        "assetcore.services.imm03.check_audit_due",
        "assetcore.services.imm03.check_decision_overdue",
    ],
    "weekly": [
        # IMM-01 — envelope utilization warning
        "assetcore.services.imm01.budget_envelope_alert",
        # IMM-02 — stale benchmark warning
        "assetcore.services.imm02.benchmark_freshness_alert",
    ],
    "monthly": [
        "assetcore.services.imm00.rollup_asset_kpi",
        # IMM-00 Asset depreciation execution
        "assetcore.services.depreciation.run_due_depreciation",
        # IMM-01 — Demand Forecast generation
        "assetcore.services.imm01.generate_demand_forecast",
    ],
    # Frappe v15 không có "quarterly" → dùng cron expression
    "cron": {
        # IMM-03 — Vendor Scorecard 1/4/7/10 hàng năm 02:00
        "0 2 1 1,4,7,10 *": [
            "assetcore.services.imm03.update_vendor_scorecard",
        ],
    },
}

# ──────────────────────────────────────────────
# Permission Query Conditions
# ──────────────────────────────────────────────
permission_query_conditions = {
    "AC Asset": "assetcore.permissions.ac_asset_query",
    "Incident Report": "assetcore.permissions.incident_report_query",
    "Asset Repair": "assetcore.permissions.asset_repair_query",
    "PM Work Order": "assetcore.permissions.pm_work_order_query",
}

# Not overriding any Frappe/ERPNext DocType — AssetCore is Frappe-only (no ERPNext dep)
override_doctype_class = {}
override_whitelisted_methods = {}
website_route_rules = []
