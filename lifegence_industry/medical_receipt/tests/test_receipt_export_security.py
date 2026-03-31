# Copyright (c) 2026, Lifegence Corporation and contributors
# For license information, please see license.txt

"""
Security tests for receipt export API: role-based access control.
"""

import frappe
from frappe.tests.utils import FrappeTestCase


TEST_UNPRIVILEGED_USER = "test-receipt-noaccess@example.com"


def _ensure_roles():
    for role_name in ("Medical Receipt Manager",):
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": 1,
            }).insert(ignore_permissions=True)
    frappe.db.commit()


def _ensure_test_user():
    if not frappe.db.exists("User", TEST_UNPRIVILEGED_USER):
        user = frappe.new_doc("User")
        user.email = TEST_UNPRIVILEGED_USER
        user.first_name = "NoReceipt"
        user.last_name = "User"
        user.send_welcome_email = 0
        user.insert(ignore_permissions=True)
        frappe.db.commit()


class TestReceiptExportSecurity(FrappeTestCase):
    """Test that receipt export API enforces role checks."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_roles()
        _ensure_test_user()

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_export_requires_medical_receipt_manager(self):
        """export_receipt_csv should reject users without Medical Receipt Manager role."""
        from lifegence_industry.medical_receipt.api.receipt_export import export_receipt_csv

        frappe.set_user(TEST_UNPRIVILEGED_USER)
        with self.assertRaises(frappe.PermissionError):
            export_receipt_csv("ANY-BATCH-ID")
