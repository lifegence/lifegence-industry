import frappe
from frappe.tests.utils import FrappeTestCase


class TestTradeShipment(FrappeTestCase):
	def setUp(self):
		self.ensure_port_exists()

	def ensure_port_exists(self):
		if not frappe.db.exists("Port Master", "JPYOK"):
			frappe.get_doc({
				"doctype": "Port Master",
				"port_code": "JPYOK",
				"port_name": "Yokohama",
				"port_name_ja": "横浜",
				"port_type": "Seaport",
				"country": "Japan",
				"is_active": 1,
			}).insert(ignore_permissions=True)

		if not frappe.db.exists("Port Master", "CNSHA"):
			frappe.get_doc({
				"doctype": "Port Master",
				"port_code": "CNSHA",
				"port_name": "Shanghai",
				"port_type": "Seaport",
				"country": "China",
				"is_active": 1,
			}).insert(ignore_permissions=True)

	def get_test_item(self):
		if not frappe.db.exists("Item", "TEST-TRADE-001"):
			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": "TEST-TRADE-001",
				"item_name": "Test Trade Item",
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
			})
			item.insert(ignore_permissions=True)
		return "TEST-TRADE-001"

	def create_trade_shipment(self, **kwargs):
		item_code = self.get_test_item()
		company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.get_all("Company", limit=1)[0].name

		defaults = {
			"doctype": "Trade Shipment",
			"shipment_type": "Export",
			"transport_mode": "Sea FCL",
			"company": company,
			"shipper_type": "Company",
			"shipper": company,
			"consignee_type": "Company",
			"consignee": company,
			"incoterm": frappe.get_all("Incoterm", limit=1)[0].name if frappe.get_all("Incoterm", limit=1) else None,
			"currency": "JPY",
			"exchange_rate": 1,
			"country_of_origin": "Japan",
			"country_of_destination": "China",
			"port_of_loading": "JPYOK",
			"port_of_discharge": "CNSHA",
			"items": [
				{
					"item_code": item_code,
					"item_name": "Test Trade Item",
					"qty": 100,
					"uom": "Nos",
					"rate": 1000,
					"gross_weight": 500,
					"net_weight": 450,
					"volume": 2.5,
					"packages": 10,
				}
			],
		}
		defaults.update(kwargs)

		doc = frappe.get_doc(defaults)
		doc.insert(ignore_permissions=True)
		return doc

	def test_create_trade_shipment(self):
		doc = self.create_trade_shipment()
		self.assertTrue(doc.name)
		self.assertEqual(doc.shipment_type, "Export")
		self.assertEqual(doc.status, "Draft")

	def test_calculate_totals(self):
		doc = self.create_trade_shipment()
		self.assertEqual(doc.total_packages, 10)
		self.assertEqual(doc.total_gross_weight, 500)
		self.assertEqual(doc.total_net_weight, 450)
		self.assertAlmostEqual(doc.total_volume, 2.5)
		self.assertEqual(doc.total_value, 100000)

	def test_calculate_item_amount(self):
		doc = self.create_trade_shipment()
		self.assertEqual(doc.items[0].amount, 100000)

	def test_naming_series_export(self):
		doc = self.create_trade_shipment(shipment_type="Export")
		self.assertTrue(doc.name.startswith("TS-EXP-"))

	def test_naming_series_import(self):
		doc = self.create_trade_shipment(shipment_type="Import")
		self.assertTrue(doc.name.startswith("TS-IMP-"))

	def test_submit_changes_status(self):
		doc = self.create_trade_shipment()
		doc.submit()
		doc.reload()
		self.assertEqual(doc.status, "Booked")

	def test_cancel_changes_status(self):
		doc = self.create_trade_shipment()
		doc.submit()
		doc.cancel()
		doc.reload()
		self.assertEqual(doc.status, "Cancelled")

	def test_charges_calculation(self):
		doc = self.create_trade_shipment()
		doc.append("charges", {
			"charge_type": "Ocean Freight",
			"description": "Sea Freight",
			"currency": "USD",
			"amount": 2000,
			"exchange_rate": 150,
		})
		doc.append("charges", {
			"charge_type": "THC",
			"description": "Terminal Handling",
			"currency": "JPY",
			"amount": 50000,
			"exchange_rate": 1,
		})
		doc.save()
		self.assertEqual(doc.total_charges, 350000)

	def test_multiple_items(self):
		item_code = self.get_test_item()
		doc = self.create_trade_shipment(items=[
			{
				"item_code": item_code,
				"item_name": "Test Trade Item",
				"qty": 50,
				"uom": "Nos",
				"rate": 1000,
				"packages": 5,
				"gross_weight": 250,
				"net_weight": 225,
				"volume": 1.2,
			},
			{
				"item_code": item_code,
				"item_name": "Test Trade Item",
				"qty": 30,
				"uom": "Nos",
				"rate": 2000,
				"packages": 3,
				"gross_weight": 150,
				"net_weight": 135,
				"volume": 0.8,
			},
		])
		self.assertEqual(doc.total_packages, 8)
		self.assertEqual(doc.total_gross_weight, 400)
		self.assertEqual(doc.total_value, 110000)


class TestPortMaster(FrappeTestCase):
	def test_create_port(self):
		if frappe.db.exists("Port Master", "TESTP"):
			frappe.delete_doc("Port Master", "TESTP", force=True)

		doc = frappe.get_doc({
			"doctype": "Port Master",
			"port_code": "TESTP",
			"port_name": "Test Port",
			"port_type": "Seaport",
			"country": "Japan",
			"is_active": 1,
		})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.port_code, "TESTP")

	def test_port_code_uppercase(self):
		if frappe.db.exists("Port Master", "TESTQ"):
			frappe.delete_doc("Port Master", "TESTQ", force=True)

		doc = frappe.get_doc({
			"doctype": "Port Master",
			"port_code": "testq",
			"port_name": "Test Port Q",
			"port_type": "Airport",
			"country": "Japan",
			"is_active": 1,
		})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.port_code, "TESTQ")

	def test_port_code_length_validation(self):
		doc = frappe.get_doc({
			"doctype": "Port Master",
			"port_code": "AB",
			"port_name": "Invalid Port",
			"port_type": "Seaport",
			"country": "Japan",
		})
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)


class TestTradeSettings(FrappeTestCase):
	def test_settings_exists(self):
		settings = frappe.get_single("Trade Settings")
		self.assertIsNotNone(settings)
