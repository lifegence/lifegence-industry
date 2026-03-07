import frappe


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": "Declaration", "fieldtype": "Link", "options": "Customs Declaration", "width": 150},
		{"fieldname": "declaration_type", "label": "Type", "fieldtype": "Data", "width": 80},
		{"fieldname": "declaration_date", "label": "Date", "fieldtype": "Date", "width": 100},
		{"fieldname": "customs_office", "label": "Customs Office", "fieldtype": "Data", "width": 130},
		{"fieldname": "trade_shipment", "label": "Shipment", "fieldtype": "Link", "options": "Trade Shipment", "width": 150},
		{"fieldname": "customs_value_jpy", "label": "Customs Value (JPY)", "fieldtype": "Currency", "width": 150},
		{"fieldname": "total_duty", "label": "Total Duty", "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_consumption_tax", "label": "Consumption Tax", "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_local_tax", "label": "Local Tax", "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_taxes", "label": "Total Taxes", "fieldtype": "Currency", "width": 120},
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters:
		if filters.get("from_date"):
			conditions.append("cd.declaration_date >= %(from_date)s")
			values["from_date"] = filters["from_date"]
		if filters.get("to_date"):
			conditions.append("cd.declaration_date <= %(to_date)s")
			values["to_date"] = filters["to_date"]
		if filters.get("declaration_type"):
			conditions.append("cd.declaration_type = %(declaration_type)s")
			values["declaration_type"] = filters["declaration_type"]

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	return frappe.db.sql(
		f"""
		SELECT
			cd.name, cd.declaration_type, cd.declaration_date,
			cd.customs_office, cd.trade_shipment,
			cd.customs_value_jpy, cd.total_duty,
			cd.total_consumption_tax, cd.total_local_tax,
			cd.total_taxes, cd.status
		FROM `tabCustoms Declaration` cd
		WHERE cd.docstatus = 1 AND {where_clause}
		ORDER BY cd.declaration_date DESC
		""",
		values=values,
		as_dict=True,
	)
