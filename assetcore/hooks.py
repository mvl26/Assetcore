app_name = "assetcore"
app_title = "AssetCore"
app_publisher = "miyano"
app_description = "Medical Equipment Lifecycle Management (HTM)"
app_email = ""
app_license = "MIT"

# Apps
# ------------------
# required_apps = ["frappe", "erpnext"]

# Includes in <head>
# ------------------
# include_js = {"page,py" : "public/js/file.js"}
# include_css = {"page,py" : "public/css/file.css"}

# Home Pages
# ----------
# home_page = "login"

# Generators
# ----------
# website_generators = ["Web Page"]

# Jinja
# ----------
# jinja = {
#     "methods": "assetcore.utils.jinja_methods",
#     "filters": "assetcore.utils.jinja_filters"
# }

# Installation
# ------------
# before_install = "assetcore.install.before_install"
# after_install = "assetcore.install.after_install"

# Uninstallation
# ------------
# before_uninstall = "assetcore.uninstall.before_uninstall"
# after_uninstall = "assetcore.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# notification_config = "assetcore.notifications.get_notification_config"

# Permissions
# -----------
# permission_query_conditions = {
#     "Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
# has_permission = {
#     "Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# override_doctype_class = {
#     "ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# doc_events = {
#     "Asset": {
#         "on_submit": "assetcore.events.asset.on_submit",
#     }
# }

# Scheduled Tasks
# ---------------
# scheduler_events = {
#     "all": ["assetcore.tasks.all"],
#     "daily": ["assetcore.tasks.daily"],
#     "hourly": ["assetcore.tasks.hourly"],
#     "weekly": ["assetcore.tasks.weekly"],
#     "monthly": ["assetcore.tasks.monthly"],
# }

# Testing
# -------
# before_tests = "assetcore.install.before_tests"

# Overriding Methods
# ------------------------------
# override_whitelisted_methods = {
#     "frappe.desk.doctype.event.event.get_permission_query_conditions": "assetcore.event.get_permission_query_conditions"
# }

# Each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#     "Task": "assetcore.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["assetcore.utils.before_request"]
# after_request = ["assetcore.utils.after_request"]

# Job Events
# ----------
# before_job = ["assetcore.utils.before_job"]
# after_job = ["assetcore.utils.after_job"]

# User Data Protection
# --------------------
# user_data_fields = [
#     {
#         "doctype": "{doctype_1}",
#         "filter_by": "{filter_by}",
#         "redact_fields": ["{field_1}", "{field_2}"],
#         "partial": 1,
#     },
# ]

# Authentication and authorization
# ---------------------------------
# auth_hooks = [
#     "assetcore.auth.validate"
# ]
