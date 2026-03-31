# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def calculate_medical_totals(doc, detail_field="details"):
	"""Calculate total points, amounts, copay, and insurance claim for medical documents.

	Shared by Receipt and PatientEncounter DocTypes.

	Args:
		doc: The document (must have total_points, total_amount, copay_amount,
			insurance_claim_amount fields and a patient_insurance link).
		detail_field: Name of the child table field containing line items
			with fee_points and quantity.
	"""
	total_points = 0
	for line in getattr(doc, detail_field, []):
		line.line_total_points = (line.fee_points or 0) * (line.quantity or 1)
		total_points += line.line_total_points

	doc.total_points = total_points

	settings = frappe.get_single("Medical Receipt Settings")
	unit_price = flt(settings.point_unit_price) or 10
	doc.total_amount = doc.total_points * unit_price

	insurance = frappe.get_doc("Patient Insurance Info", doc.patient_insurance)
	copay_rate_str = insurance.copay_rate or "30%"
	copay_rate = flt(copay_rate_str.replace("%", "")) / 100

	doc.copay_amount = flt(doc.total_amount * copay_rate, 0)
	doc.insurance_claim_amount = flt(doc.total_amount - doc.copay_amount, 0)
