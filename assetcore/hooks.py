app_name = "assetcore"
app_title = "AssetCore"
app_publisher = "miyano"
app_description = "Medical Equipment Lifecycle Management (HTM)"
app_email = ""
app_license = "MIT"

# ──────────────────────────────────────────────
# Fixtures — export config/role data với bench
# ──────────────────────────────────────────────
fixtures = [
	{"dt": "Role", "filters": [["name", "in", [
		"HTM Technician",
		"Biomed Engineer",
		"Workshop Head",
		"VP Block2",
		"QA Risk Team",
		"CMMS Admin",
		"Tổ HC-QLCL",        # IMM-05
	]]]},
	{"dt": "Workflow", "filters": [["name", "in", [
		"IMM-04 Workflow",
		"IMM-05 Document Workflow",   # IMM-05
	]]]},
	{"dt": "Required Document Type"},   # IMM-05 seed data
	{"dt": "Custom Field", "filters": [["dt", "in", ["Asset"]]]},
]

# ──────────────────────────────────────────────
# Document Events — gắn hook vào các DocType
# ──────────────────────────────────────────────
doc_events = {}

# ──────────────────────────────────────────────
# Scheduled Jobs — Cron tasks
# ──────────────────────────────────────────────
scheduler_events = {
	"daily": [
		"assetcore.tasks.check_clinical_hold_aging",
		"assetcore.tasks.check_commissioning_sla",
		"assetcore.tasks.check_document_expiry",            # IMM-05: expiry alert + auto-Expire
		"assetcore.tasks.update_asset_completeness",        # IMM-05: cập nhật pct + document_status
		"assetcore.tasks.check_overdue_document_requests",  # IMM-05: leo thang Document Request
	],
	"hourly": [
		"assetcore.tasks.send_pending_approvals_reminder",
	]
}

# ──────────────────────────────────────────────
# Override list view — ẩn nút New trên Asset
# ──────────────────────────────────────────────
override_whitelisted_methods = {}

# Web hooks
website_route_rules = []
