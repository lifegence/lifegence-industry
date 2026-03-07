import frappe


def on_submit(doc, method):
	"""Update Trade Shipment status when Purchase Receipt is submitted."""
	trade_shipment = doc.get("trade_shipment")
	if not trade_shipment:
		return

	if not frappe.db.exists("Trade Shipment", trade_shipment):
		return

	shipment = frappe.get_doc("Trade Shipment", trade_shipment)
	if shipment.status in ("Customs Cleared", "Arrived"):
		shipment.status = "Delivered"
		shipment.purchase_receipt = doc.name
		shipment.delivery_date = frappe.utils.today()
		shipment.flags.ignore_permissions = True
		shipment.save()
		frappe.msgprint(
			f"Trade Shipment {shipment.name} updated to Delivered.",
			alert=True,
			indicator="green",
		)
