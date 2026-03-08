app_name = "lifegence_industry"
app_title = "Lifegence Industry"
app_publisher = "Lifegence"
app_description = "Industry-Specific Modules - Medical, Trade, Mind Analysis"
app_email = "info@lifegence.co.jp"
app_license = "mit"

required_apps = ["frappe", "erpnext"]

export_python_type_annotations = True

after_install = "lifegence_industry.install.after_install"

# Includes in <head>
# ------------------
app_include_css = "/assets/lifegence_industry/css/mind_analyzer.css"

# Apps Screen
# -----------
add_to_apps_screen = [
	{
		"name": "lifegence_industry_medical",
		"logo": "/assets/lifegence_industry/images/medical-receipt-logo.svg",
		"title": "レセプト",
		"route": "/app/medical-receipt",
	},
	{
		"name": "lifegence_industry_trade",
		"logo": "/assets/lifegence_industry/images/trade-logo.svg",
		"title": "貿易管理",
		"route": "/app/trade-management",
	},
	{
		"name": "lifegence_industry_mind",
		"logo": "/assets/lifegence_industry/images/mind-analyzer-icon.svg",
		"title": "マインド分析",
		"route": "/app/mind-analyzer",
		"has_permission": "lifegence_industry.mind_analyzer.api.session.has_analyzer_access",
	},
]

# Fixtures
# --------
fixtures = [
	"Medical Receipt Settings",
	"Trade Settings",
	{
		"dt": "Custom Field",
		"filters": [["module", "=", "Trade Management"]],
	},
]

# Document Events
# ---------------
doc_events = {
	# Medical Receipt
	"Patient Encounter": {
		"on_submit": "lifegence_industry.medical_receipt.api.fee_calculation.on_encounter_submit",
	},
	# Trade Management
	"Sales Order": {
		"on_submit": "lifegence_industry.trade_management.events.sales_order.on_submit",
	},
	"Purchase Order": {
		"on_submit": "lifegence_industry.trade_management.events.purchase_order.on_submit",
	},
	"Delivery Note": {
		"on_submit": "lifegence_industry.trade_management.events.delivery_note.on_submit",
	},
	"Purchase Receipt": {
		"on_submit": "lifegence_industry.trade_management.events.purchase_receipt.on_submit",
	},
	# Mind Analyzer
	"Voice Analysis Session": {
		"after_insert": "lifegence_industry.mind_analyzer.services.realtime_service.on_session_created",
		"on_update": "lifegence_industry.mind_analyzer.services.realtime_service.on_session_updated",
	},
}

# Scheduled Tasks
# ---------------
scheduler_events = {
	"daily": [
		# Trade Management
		"lifegence_industry.trade_management.services.schedule.check_eta_alerts",
		"lifegence_industry.trade_management.services.schedule.check_lc_expiry",
		# Mind Analyzer
		"lifegence_industry.mind_analyzer.services.cleanup_service.cleanup_old_data",
	],
	"cron": {
		# Medical Receipt - 5th of each month at 9:00 AM
		"0 9 5 * *": [
			"lifegence_industry.medical_receipt.api.receipt_generation.send_deadline_reminder",
		],
		# Mind Analyzer - every 6 hours
		"0 */6 * * *": [
			"lifegence_industry.mind_analyzer.services.cleanup_service.cleanup_stale_sessions",
		],
	},
}

# User Data Protection
# --------------------
user_data_fields = [
	{
		"doctype": "Voice Analysis Session",
		"filter_by": "user",
		"redact_fields": [],
		"partial": 1,
	},
	{
		"doctype": "Individual Analysis Result",
		"filter_by": "owner",
		"partial": 1,
	},
	{
		"doctype": "Meeting Analysis Result",
		"filter_by": "owner",
		"partial": 1,
	},
]

# Analysis Configuration
# ----------------------
TRIGGER_TYPES = [
	{"value": "silence_spike", "label": "Silence Spike"},
	{"value": "apology_phrase", "label": "Apology/Shrinking Phrase"},
	{"value": "hedge_increase", "label": "Hedge Word Increase"},
	{"value": "speech_rate_change", "label": "Speech Rate Change"},
	{"value": "restart_increase", "label": "Restart Increase"},
	{"value": "interruption", "label": "Interruption"},
	{"value": "overlap", "label": "Overlap Speech"},
	{"value": "power_imbalance", "label": "Power Imbalance"},
]

ANALYSIS_MODES = [
	{"value": "individual", "label": "Individual"},
	{"value": "meeting", "label": "Meeting"},
]
