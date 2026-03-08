import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	"""Post-install setup for all industry modules."""
	_install_trade()
	frappe.db.commit()


def _install_trade():
	"""Set up Trade Management module defaults and custom fields."""
	try:
		_create_trade_settings()
		_create_trade_custom_fields()
		frappe.msgprint("Trade Management: Setup completed successfully.")
	except Exception:
		frappe.log_error("Trade Management: Error during post-install setup")
		raise


def _create_trade_settings():
	if not frappe.db.exists("Trade Settings", "Trade Settings"):
		doc = frappe.new_doc("Trade Settings")
		doc.auto_create_landed_cost = 1
		doc.auto_compliance_check = 0
		doc.enable_ai_hs_suggestion = 0
		doc.enable_ai_document_check = 0
		doc.insert(ignore_permissions=True)


def _create_trade_custom_fields():
	custom_fields = {
		"Item": [
			{
				"fieldname": "trade_section",
				"fieldtype": "Section Break",
				"label": "Trade / Export Control",
				"insert_after": "customs_tariff_number",
				"module": "Trade Management",
			},
			{
				"fieldname": "export_control_class",
				"fieldtype": "Data",
				"label": "Export Control Classification",
				"insert_after": "trade_section",
				"description": "e.g., EAR99, 3A001, etc.",
				"module": "Trade Management",
			},
			{
				"fieldname": "dual_use_flag",
				"fieldtype": "Check",
				"label": "Dual Use Item",
				"insert_after": "export_control_class",
				"module": "Trade Management",
			},
			{
				"fieldname": "column_break_trade",
				"fieldtype": "Column Break",
				"insert_after": "dual_use_flag",
				"module": "Trade Management",
			},
			{
				"fieldname": "catch_all_number",
				"fieldtype": "Data",
				"label": "Catch-All Number",
				"insert_after": "column_break_trade",
				"description": "Japan METI catch-all control classification",
				"module": "Trade Management",
			},
			{
				"fieldname": "export_license_required",
				"fieldtype": "Check",
				"label": "Export License Required",
				"insert_after": "catch_all_number",
				"module": "Trade Management",
			},
		],
	}
	create_custom_fields(custom_fields, update=True)
