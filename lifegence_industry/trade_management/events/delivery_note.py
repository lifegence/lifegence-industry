import frappe


def on_submit(doc, method):
	"""Update Trade Shipment status when Delivery Note is submitted."""
	trade_shipment = doc.get("trade_shipment")
	if not trade_shipment:
		return

	if not frappe.db.exists("Trade Shipment", trade_shipment):
		return

	shipment = frappe.get_doc("Trade Shipment", trade_shipment)
	if shipment.status == "Draft":
		shipment.status = "Booked"
		shipment.delivery_note = doc.name
		shipment.flags.ignore_permissions = True
		shipment.save()
		frappe.msgprint(
			f"Trade Shipment {shipment.name} updated to Booked.",
			alert=True,
			indicator="blue",
		)
