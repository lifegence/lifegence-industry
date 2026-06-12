# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint
from frappe.website.website_generator import WebsiteGenerator


class DispatchClient(WebsiteGenerator):
	website = frappe._dict(
		template="templates/generators/dispatch_client.html",
		condition_field="publish_hub",
		page_title_field="client_name",
	)

	def validate(self):
		if not self.route and self.publish_hub:
			self.route = f"companies/{frappe.scrub(self.client_name).replace('_', '-')}"

	def get_context(self, context):
		"""Build the public HUB page: client info + its job postings."""
		context.no_cache = 1
		context.nav_active = "jobs"

		show_closed = cint(
			frappe.db.get_single_value("Staffing Settings", "show_closed_jobs")
		)
		filters = {"dispatch_client": self.name, "publish": 1}
		if not show_closed:
			filters["status"] = "Open"

		context.jobs = frappe.get_all(
			"Dispatch Order",
			filters=filters,
			fields=[
				"name",
				"job_title",
				"route",
				"status",
				"work_location",
				"job_category",
				"employment_type",
				"pay_rate",
				"pay_rate_unit",
			],
			order_by="status desc, modified desc",
		)
		context.job_count = len(context.jobs)
		context.open_count = frappe.db.count(
			"Dispatch Order", {"dispatch_client": self.name, "publish": 1, "status": "Open"}
		)
		context.total_count = frappe.db.count(
			"Dispatch Order", {"dispatch_client": self.name, "publish": 1}
		)
		context.category_count = len(
			{j.job_category for j in context.jobs if j.job_category}
		)
		return context
