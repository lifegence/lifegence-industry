import frappe
from frappe.utils import today, add_days, date_diff


def check_eta_alerts():
	"""Send alerts for shipments arriving within 3 days."""
	alert_date = add_days(today(), 3)

	shipments = frappe.get_all(
		"Trade Shipment",
		filters={
			"status": ["in", ["Shipped", "In Transit"]],
			"eta": ["between", [today(), alert_date]],
		},
		fields=["name", "shipment_type", "eta", "consignee", "port_of_discharge"],
	)

	for shipment in shipments:
		frappe.publish_realtime(
			"eta_alert",
			{
				"shipment": shipment.name,
				"eta": str(shipment.eta),
				"port": shipment.port_of_discharge,
			},
		)


def check_lc_expiry():
	"""Alert on L/Cs expiring within 14 days."""
	alert_date = add_days(today(), 14)

	lcs = frappe.get_all(
		"Letter of Credit",
		filters={
			"status": ["not in", ["Fully Drawn", "Expired", "Cancelled"]],
			"expiry_date": ["between", [today(), alert_date]],
		},
		fields=["name", "lc_type", "expiry_date", "lc_amount", "balance", "issuing_bank"],
	)

	for lc in lcs:
		days_left = date_diff(lc.expiry_date, today())
		frappe.publish_realtime(
			"lc_expiry_alert",
			{
				"lc": lc.name,
				"expiry_date": str(lc.expiry_date),
				"days_left": days_left,
				"balance": lc.balance,
			},
		)

		# Auto-expire if past expiry
		if days_left <= 0:
			frappe.db.set_value("Letter of Credit", lc.name, "status", "Expired")

	# Expire any L/Cs past expiry date
	expired = frappe.get_all(
		"Letter of Credit",
		filters={
			"status": ["not in", ["Fully Drawn", "Expired", "Cancelled"]],
			"expiry_date": ["<", today()],
		},
		pluck="name",
	)
	for name in expired:
		frappe.db.set_value("Letter of Credit", name, "status", "Expired")
