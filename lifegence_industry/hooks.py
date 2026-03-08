app_name = "lifegence_industry"
app_title = "Lifegence Industry"
app_publisher = "Lifegence"
app_description = "Industry-Specific Modules - Medical Receipt, Trade Management"
app_email = "info@lifegence.co.jp"
app_license = "mit"

required_apps = ["frappe", "erpnext"]

export_python_type_annotations = True

after_install = "lifegence_industry.install.after_install"

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
}

# Scheduled Tasks
# ---------------
scheduler_events = {
	"daily": [
		# Trade Management
		"lifegence_industry.trade_management.services.schedule.check_eta_alerts",
		"lifegence_industry.trade_management.services.schedule.check_lc_expiry",
	],
	"cron": {
		# Medical Receipt - 5th of each month at 9:00 AM
		"0 9 5 * *": [
			"lifegence_industry.medical_receipt.api.receipt_generation.send_deadline_reminder",
		],
	},
}
