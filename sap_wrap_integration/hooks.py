app_name = "sap_wrap_integration"
app_title = "Sap-Wrap"
app_publisher = "nicholas.briggs@honestfarms.com"
app_description = "SAP intergration"
app_email = "nicholas.briggs@honestfarms.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "sap_wrap_integration",
# 		"logo": "/assets/sap_wrap_integration/logo.png",
# 		"title": "Sap-Wrap",
# 		"route": "/sap_wrap_integration",
# 		"has_permission": "sap_wrap_integration.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/sap_wrap_integration/css/sap_wrap_integration.css"
# app_include_js = "/assets/sap_wrap_integration/js/sap_wrap_integration.js"

# include js, css files in header of web template
# web_include_css = "/assets/sap_wrap_integration/css/sap_wrap_integration.css"
# web_include_js = "/assets/sap_wrap_integration/js/sap_wrap_integration.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "sap_wrap_integration/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "sap_wrap_integration/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "sap_wrap_integration.utils.jinja_methods",
# 	"filters": "sap_wrap_integration.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "sap_wrap_integration.install.before_install"
# after_install = "sap_wrap_integration.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "sap_wrap_integration.uninstall.before_uninstall"
# after_uninstall = "sap_wrap_integration.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "sap_wrap_integration.utils.before_app_install"
# after_app_install = "sap_wrap_integration.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "sap_wrap_integration.utils.before_app_uninstall"
# after_app_uninstall = "sap_wrap_integration.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "sap_wrap_integration.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"sap_wrap_integration.tasks.all"
# 	],
# 	"daily": [
# 		"sap_wrap_integration.tasks.daily"
# 	],
# 	"hourly": [
# 		"sap_wrap_integration.tasks.hourly"
# 	],
# 	"weekly": [
# 		"sap_wrap_integration.tasks.weekly"
# 	],
# 	"monthly": [
# 		"sap_wrap_integration.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "sap_wrap_integration.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "sap_wrap_integration.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "sap_wrap_integration.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["sap_wrap_integration.utils.before_request"]
# after_request = ["sap_wrap_integration.utils.after_request"]

# Job Events
# ----------
# before_job = ["sap_wrap_integration.utils.before_job"]
# after_job = ["sap_wrap_integration.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"sap_wrap_integration.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# SAP Wrap document events
doc_events = {
    "*": {
        "after_insert": "sap_wrap_integration.sap_wrap.runner.run_sap_wraps",
        "on_update": "sap_wrap_integration.sap_wrap.runner.run_sap_wraps",
        "on_submit": "sap_wrap_integration.sap_wrap.runner.run_sap_wraps",
        "on_cancel": "sap_wrap_integration.sap_wrap.runner.run_sap_wraps",
        "on_trash": "sap_wrap_integration.sap_wrap.runner.run_sap_wraps",
        "on_update_after_submit": "sap_wrap_integration.sap_wrap.runner.run_sap_wraps",
        "on_change": "sap_wrap_integration.sap_wrap.runner.run_sap_wraps",
    }
}

# SAP Wrap scheduled cleanup
scheduler_events = {
    "daily": [
        "sap_wrap_integration.sap_wrap.runner.cleanup_old_sap_wrap_request_logs"
    ]
}

# SAP Wrap workspace and dashboard fixtures
fixtures = [
    {
        "dt": "Workspace",
        "filters": [["name", "=", "SAP Wrap Operations"]]
    },
    {
        "dt": "Dashboard Chart",
        "filters": [["name", "in", [
            "SAP Wrap Request Status Breakdown",
            "SAP Wrap Response Time Trend"
        ]]]
    },
    {
        "dt": "Number Card",
        "filters": [["name", "in", [
            "SAP Wrap Requests (7d)",
            "SAP Wrap Success Rate (7d)",
            "SAP Wrap Avg Response (7d)"
        ]]]
    }
]
