app_name = "assetcore"
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
        # IMM-00 governance roles
        "IMM System Admin",
        "IMM Department Head",
        "IMM Operations Manager",
        "IMM Workshop Lead",
        "IMM Technician",
        "IMM Document Officer",
        "IMM Storekeeper",
        "IMM QA Officer",
        "IMM Clinical User",
        # IMM-04/05/08/09/11 operational roles (hospital workflow)
        "HTM Technician",
        "CMMS Admin",
        "Workshop Head",
        "VP Block2",
        "Biomed Engineer",
        "Tổ HC-QLCL",
        "Clinical Head",
    ]]]},
    {"dt": "IMM SLA Policy"},
]

# ──────────────────────────────────────────────
# Document Events — IMM-00 v3
# ──────────────────────────────────────────────
doc_events = {
    "Asset Commissioning": {
        "on_submit": "assetcore.services.imm11.create_calibration_schedule_from_commissioning",
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
    ],
    "monthly": [
        "assetcore.services.imm00.rollup_asset_kpi",
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
