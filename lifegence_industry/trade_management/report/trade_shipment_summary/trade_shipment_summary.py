import frappe


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": "Shipment", "fieldtype": "Link", "options": "Trade Shipment", "width": 150},
		{"fieldname": "shipment_type", "label": "Type", "fieldtype": "Data", "width": 80},
		{"fieldname": "transport_mode", "label": "Mode", "fieldtype": "Data", "width": 100},
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 120},
		{"fieldname": "company", "label": "Company", "fieldtype": "Link", "options": "Company", "width": 150},
		{"fieldname": "port_of_loading", "label": "POL", "fieldtype": "Link", "options": "Port Master", "width": 100},
		{"fieldname": "port_of_discharge", "label": "POD", "fieldtype": "Link", "options": "Port Master", "width": 100},
		{"fieldname": "etd", "label": "ETD", "fieldtype": "Date", "width": 100},
		{"fieldname": "eta", "label": "ETA", "fieldtype": "Date", "width": 100},
		{"fieldname": "total_value", "label": "Total Value", "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_packages", "label": "Packages", "fieldtype": "Int", "width": 80},
		{"fieldname": "total_gross_weight", "label": "Weight (kg)", "fieldtype": "Float", "width": 100},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters:
		if filters.get("from_date"):
			conditions.append("ts.posting_date >= %(from_date)s")
			values["from_date"] = filters["from_date"]
		if filters.get("to_date"):
			conditions.append("ts.posting_date <= %(to_date)s")
			values["to_date"] = filters["to_date"]
		if filters.get("shipment_type"):
			conditions.append("ts.shipment_type = %(shipment_type)s")
			values["shipment_type"] = filters["shipment_type"]
		if filters.get("status"):
			conditions.append("ts.status = %(status)s")
			values["status"] = filters["status"]
		if filters.get("company"):
			conditions.append("ts.company = %(company)s")
			values["company"] = filters["company"]

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	return frappe.db.sql(
		f"""
		SELECT
			ts.name, ts.shipment_type, ts.transport_mode, ts.status,
			ts.company, ts.port_of_loading, ts.port_of_discharge,
			ts.etd, ts.eta, ts.total_value,
			ts.total_packages, ts.total_gross_weight
		FROM `tabTrade Shipment` ts
		WHERE ts.docstatus < 2 AND {where_clause}
		ORDER BY ts.posting_date DESC
		""",
		values=values,
		as_dict=True,
	)
