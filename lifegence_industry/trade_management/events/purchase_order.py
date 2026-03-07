import frappe


def on_submit(doc, method):
	"""Create Trade Shipment from Purchase Order on submit if trade fields are set."""
	if not frappe.db.get_single_value("Trade Settings", "auto_create_shipment_from_po"):
		return

	if doc.get("trade_shipment"):
		return

	_create_trade_shipment_from_po(doc)


def _create_trade_shipment_from_po(doc):
	"""Create a Trade Shipment linked to a Purchase Order."""
	shipment = frappe.new_doc("Trade Shipment")
	shipment.shipment_type = "Import"
	shipment.status = "Draft"
	shipment.purchase_order = doc.name
	shipment.shipper = doc.supplier
	shipment.consignee = doc.company
	shipment.currency = doc.currency
	shipment.exchange_rate = doc.conversion_rate or 1

	if doc.get("incoterm"):
		shipment.incoterm = doc.incoterm
	if doc.get("named_place"):
		shipment.named_place = doc.named_place

	for item in doc.items:
		shipment.append("items", {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"description": item.description,
			"qty": item.qty,
			"uom": item.uom,
			"rate": item.rate,
			"amount": item.amount,
			"net_weight": (item.total_weight or 0),
		})

	shipment.flags.ignore_permissions = True
	shipment.insert()

	doc.db_set("trade_shipment", shipment.name, update_modified=False)
	frappe.msgprint(
		f"Trade Shipment {shipment.name} created.",
		alert=True,
		indicator="green",
	)
