# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.naming import set_name_from_naming_options
from frappe.website.website_generator import WebsiteGenerator

# Characters that are unsafe in a URL path segment (reserved/delimiters).
_UNSAFE_ROUTE_CHARS = re.compile(r"[#?%&+/\\<>\"'`\s]+")


def slugify_segment(text: str) -> str:
	"""Build a URL-safe path segment, preserving non-ASCII (e.g. Japanese)."""
	text = (text or "").strip().lower()
	text = text.replace("_", "-")
	text = _UNSAFE_ROUTE_CHARS.sub("-", text)
	text = re.sub(r"-{2,}", "-", text).strip("-")
	return text or "item"


class DispatchOrder(WebsiteGenerator):
	website = frappe._dict(
		template="templates/generators/dispatch_order.html",
		condition_field="publish",
		page_title_field="job_title",
	)

	def autoname(self):
		# WebsiteGenerator names by title by default; use the naming series instead.
		set_name_from_naming_options(frappe.get_meta(self.doctype).autoname, self)

	def validate(self):
		self.set_route()

	def set_route(self):
		if self.publish and not self.route:
			client_slug = slugify_segment(self.dispatch_client or "general")
			title_slug = slugify_segment(self.job_title)
			# Fall back to the document name to guarantee uniqueness.
			self.route = f"jobs/{client_slug}/{title_slug}-{frappe.scrub(self.name)}"

	def get_context(self, context):
		context.no_cache = 1
		context.nav_active = "jobs"
		context.is_closed = self.status == "Closed"
		if self.dispatch_client:
			context.client = frappe.db.get_value(
				"Dispatch Client",
				self.dispatch_client,
				["client_name", "route", "publish_hub", "logo", "about", "headquarters_location"],
				as_dict=True,
			)
		return context
