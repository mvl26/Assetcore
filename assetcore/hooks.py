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
		"CMMS Admin"
	]]]},
	{"dt": "Workflow", "filters": [["name", "in", ["IMM-04 Workflow"]]]},
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
