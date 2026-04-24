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
fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        # IMM governance roles — primary
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
        # Legacy operational roles (kept for backward compatibility, to be migrated)
        "HTM Technician",
        "CMMS Admin",
        "Workshop Head",
        "VP Block2",
        "Biomed Engineer",
        "Tổ HC-QLCL",
        "Clinical Head",
    ]]]},
    {"dt": "IMM SLA Policy"},
    {"dt": "Workflow", "filters": [["name", "in", [
        "AC Asset Lifecycle",
        "IMM-04 Workflow",
    ]]]},
    {"dt": "Workflow State", "filters": [["name", "in", [
        "Draft", "Commissioned", "Active",
        "Under Maintenance", "Under Repair", "Calibrating",
        "Out of Service", "Decommissioned",
    ]]]},
    {"dt": "Workflow Action Master", "filters": [["name", "in", [
        "Commission", "Activate",
        "Bắt đầu bảo trì", "Hoàn thành bảo trì",
        "Bắt đầu sửa chữa", "Bắt đầu hiệu chuẩn", "Đưa ra khỏi sử dụng",
        "Hoàn thành sửa chữa", "Không thể sửa chữa",
        "Hiệu chuẩn đạt", "Hiệu chuẩn không đạt",
        "Khôi phục hoạt động", "Sửa chữa lại", "Thanh lý",
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
    ],
    "monthly": [
        "assetcore.services.imm00.rollup_asset_kpi",
        # IMM-00 Asset depreciation execution
        "assetcore.services.depreciation.run_due_depreciation",
    ],
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
