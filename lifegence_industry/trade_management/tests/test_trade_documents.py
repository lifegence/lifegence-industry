import frappe
from frappe.tests.utils import FrappeTestCase


class TradeDocumentTestBase(FrappeTestCase):
	"""Base class with shared test data creation helpers."""

	def setUp(self):
		self.ensure_masters_exist()

	def ensure_masters_exist(self):
		# Ports
		for code, name, ptype, country in [
			("JPYOK", "Yokohama", "Seaport", "Japan"),
			("CNSHA", "Shanghai", "Seaport", "China"),
			("JPNRT", "Narita", "Airport", "Japan"),
			("HKHKG", "Hong Kong", "Airport", "Hong Kong"),
		]:
			if not frappe.db.exists("Port Master", code):
				frappe.get_doc({
					"doctype": "Port Master",
					"port_code": code,
					"port_name": name,
					"port_type": ptype,
					"country": country,
					"is_active": 1,
				}).insert(ignore_permissions=True)

		# Shipping Line
		if not frappe.db.exists("Shipping Line", "MAEU"):
			frappe.get_doc({
				"doctype": "Shipping Line",
				"line_code": "MAEU",
				"line_name": "Maersk",
			}).insert(ignore_permissions=True)

		# Airline Master
		if not frappe.db.exists("Airline Master", "NH"):
			frappe.get_doc({
				"doctype": "Airline Master",
				"iata_code": "NH",
				"airline_name": "All Nippon Airways",
				"airline_prefix": "205",
			}).insert(ignore_permissions=True)

	def get_test_item(self):
		if not frappe.db.exists("Item", "TEST-TRADE-001"):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": "TEST-TRADE-001",
				"item_name": "Test Trade Item",
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
			}).insert(ignore_permissions=True)
		return "TEST-TRADE-001"

	def create_trade_shipment(self, **kwargs):
		item_code = self.get_test_item()
		company = (
			frappe.db.get_single_value("Global Defaults", "default_company")
			or frappe.get_all("Company", limit=1)[0].name
		)
		incoterms = frappe.get_all("Incoterm", limit=1)

		defaults = {
			"doctype": "Trade Shipment",
			"shipment_type": "Export",
			"transport_mode": "Sea FCL",
			"company": company,
			"shipper_type": "Company",
			"shipper": company,
			"consignee_type": "Company",
			"consignee": company,
			"incoterm": incoterms[0].name if incoterms else None,
			"currency": "JPY",
			"exchange_rate": 1,
			"country_of_origin": "Japan",
			"country_of_destination": "China",
			"port_of_loading": "JPYOK",
			"port_of_discharge": "CNSHA",
			"items": [{
				"item_code": item_code,
				"item_name": "Test Trade Item",
				"qty": 100,
				"uom": "Nos",
				"rate": 1000,
				"gross_weight": 500,
				"net_weight": 450,
				"volume": 2.5,
				"packages": 10,
			}],
		}
		defaults.update(kwargs)
		doc = frappe.get_doc(defaults)
		doc.insert(ignore_permissions=True)
		return doc


class TestBillOfLading(TradeDocumentTestBase):
	def create_bl(self, **kwargs):
		ts = self.create_trade_shipment()
		bl_number = f"MAEU{frappe.generate_hash(length=8).upper()}"

		defaults = {
			"doctype": "Bill of Lading",
			"bl_number": bl_number,
			"bl_type": "Master B/L",
			"trade_shipment": ts.name,
			"shipping_line": "MAEU",
			"date_of_issue": frappe.utils.today(),
			"shipper_name": "Test Shipper Co., Ltd.",
			"shipper_address": "1-1 Tokyo, Japan",
			"consignee_name": "To Order",
			"port_of_loading": "JPYOK",
			"port_of_discharge": "CNSHA",
			"description_of_goods": "Electronic Components",
			"total_packages": 10,
			"gross_weight": 500,
			"freight_prepaid_or_collect": "Prepaid",
		}
		defaults.update(kwargs)
		doc = frappe.get_doc(defaults)
		doc.insert(ignore_permissions=True)
		return doc

	def test_create_bl(self):
		doc = self.create_bl()
		self.assertTrue(doc.name)
		self.assertEqual(doc.bl_type, "Master B/L")
		self.assertEqual(doc.bl_status, "Draft")

	def test_bl_status_transition_valid(self):
		doc = self.create_bl()
		doc.bl_status = "Original Issued"
		doc.save()
		self.assertEqual(doc.bl_status, "Original Issued")

	def test_bl_status_transition_invalid(self):
		doc = self.create_bl()
		doc.bl_status = "Accomplished"
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_bl_sea_waybill_transition(self):
		doc = self.create_bl(bl_type="Sea Waybill")
		doc.bl_status = "Released"
		doc.save()
		self.assertEqual(doc.bl_status, "Released")

	def test_bl_surrendered_to_released(self):
		doc = self.create_bl()
		doc.bl_status = "Original Issued"
		doc.save()
		doc.bl_status = "Surrendered"
		doc.save()
		doc.bl_status = "Released"
		doc.save()
		self.assertEqual(doc.bl_status, "Released")


class TestAirWaybill(TradeDocumentTestBase):
	def create_awb(self, **kwargs):
		ts = self.create_trade_shipment(transport_mode="Air")
		awb_number = f"205-{frappe.generate_hash(length=8).upper()}"

		defaults = {
			"doctype": "Air Waybill",
			"awb_number": awb_number,
			"awb_type": "Master AWB",
			"trade_shipment": ts.name,
			"airline": "NH",
			"date_of_issue": frappe.utils.today(),
			"shipper_name": "Test Shipper Co., Ltd.",
			"shipper_address": "1-1 Tokyo, Japan",
			"consignee_name": "Test Buyer Corp.",
			"consignee_address": "Shanghai, China",
			"airport_of_departure": "JPNRT",
			"airport_of_destination": "HKHKG",
			"pieces": 5,
			"gross_weight": 120,
			"chargeable_weight": 150,
			"commodity_description": "Electronic Components",
			"freight_prepaid_or_collect": "Prepaid",
		}
		defaults.update(kwargs)
		doc = frappe.get_doc(defaults)
		doc.insert(ignore_permissions=True)
		return doc

	def test_create_awb(self):
		doc = self.create_awb()
		self.assertTrue(doc.name)
		self.assertEqual(doc.awb_type, "Master AWB")

	def test_awb_total_charge_calculation(self):
		doc = self.create_awb(weight_charge=15000, valuation_charge=5000)
		self.assertEqual(doc.total_charge, 20000)

	def test_awb_total_charge_zero_when_empty(self):
		doc = self.create_awb()
		self.assertEqual(doc.total_charge, 0)


class TestCommercialInvoice(TradeDocumentTestBase):
	def create_ci(self, **kwargs):
		ts = self.create_trade_shipment()
		item_code = self.get_test_item()
		incoterms = frappe.get_all("Incoterm", limit=1)

		defaults = {
			"doctype": "Commercial Invoice",
			"trade_shipment": ts.name,
			"invoice_date": frappe.utils.today(),
			"currency": "USD",
			"seller_name": "Test Seller Co., Ltd.",
			"seller_address": "Tokyo, Japan",
			"buyer_name": "Test Buyer Corp.",
			"buyer_address": "Shanghai, China",
			"incoterm": incoterms[0].name if incoterms else None,
			"country_of_origin": "Japan",
			"items": [
				{
					"item_code": item_code,
					"qty": 100,
					"uom": "Nos",
					"rate": 50,
				},
				{
					"item_code": item_code,
					"qty": 200,
					"uom": "Nos",
					"rate": 30,
				},
			],
		}
		defaults.update(kwargs)
		doc = frappe.get_doc(defaults)
		doc.insert(ignore_permissions=True)
		return doc

	def test_create_ci(self):
		doc = self.create_ci()
		self.assertTrue(doc.name)
		self.assertTrue(doc.name.startswith("CI-"))

	def test_ci_item_amount_calculation(self):
		doc = self.create_ci()
		self.assertEqual(doc.items[0].amount, 5000)
		self.assertEqual(doc.items[1].amount, 6000)

	def test_ci_subtotal_calculation(self):
		doc = self.create_ci()
		self.assertEqual(doc.subtotal, 11000)

	def test_ci_total_with_freight_insurance(self):
		doc = self.create_ci(freight=500, insurance=200)
		self.assertEqual(doc.total_amount, 11700)

	def test_ci_total_without_extras(self):
		doc = self.create_ci()
		self.assertEqual(doc.total_amount, 11000)


class TestPackingList(TradeDocumentTestBase):
	def create_pl(self, **kwargs):
		ts = self.create_trade_shipment()
		item_code = self.get_test_item()

		defaults = {
			"doctype": "Packing List",
			"trade_shipment": ts.name,
			"packing_date": frappe.utils.today(),
			"seller_name": "Test Seller Co., Ltd.",
			"seller_address": "Tokyo, Japan",
			"buyer_name": "Test Buyer Corp.",
			"buyer_address": "Shanghai, China",
			"items": [
				{
					"item_code": item_code,
					"qty": 100,
					"uom": "Nos",
					"packages": 5,
					"gross_weight": 250,
					"net_weight": 225,
					"volume": 1.2,
				},
				{
					"item_code": item_code,
					"qty": 200,
					"uom": "Nos",
					"packages": 8,
					"gross_weight": 400,
					"net_weight": 360,
					"volume": 2.0,
				},
			],
		}
		defaults.update(kwargs)
		doc = frappe.get_doc(defaults)
		doc.insert(ignore_permissions=True)
		return doc

	def test_create_pl(self):
		doc = self.create_pl()
		self.assertTrue(doc.name)
		self.assertTrue(doc.name.startswith("PL-"))

	def test_pl_total_packages(self):
		doc = self.create_pl()
		self.assertEqual(doc.total_packages, 13)

	def test_pl_total_weights(self):
		doc = self.create_pl()
		self.assertEqual(doc.total_gross_weight, 650)
		self.assertEqual(doc.total_net_weight, 585)

	def test_pl_total_volume(self):
		doc = self.create_pl()
		self.assertAlmostEqual(doc.total_volume, 3.2)


class TestCertificateOfOrigin(TradeDocumentTestBase):
	def create_coo(self, **kwargs):
		ts = self.create_trade_shipment()
		item_code = self.get_test_item()
		coo_number = f"COO-{frappe.generate_hash(length=8).upper()}"

		defaults = {
			"doctype": "Certificate of Origin",
			"coo_number": coo_number,
			"coo_type": "Non-Preferential",
			"trade_shipment": ts.name,
			"date_of_issue": frappe.utils.today(),
			"issuing_authority": "Tokyo Chamber of Commerce",
			"exporter_name": "Test Exporter Co., Ltd.",
			"exporter_address": "Tokyo, Japan",
			"consignee_name": "Test Importer Corp.",
			"country_of_origin": "Japan",
			"country_of_destination": "China",
			"items": [{
				"item_code": item_code,
				"qty": 100,
				"uom": "Nos",
				"origin_criterion": "WO",
			}],
		}
		defaults.update(kwargs)
		doc = frappe.get_doc(defaults)
		doc.insert(ignore_permissions=True)
		return doc

	def test_create_coo(self):
		doc = self.create_coo()
		self.assertTrue(doc.name)
		self.assertEqual(doc.coo_type, "Non-Preferential")

	def test_coo_preferential(self):
		doc = self.create_coo(coo_type="Preferential (EPA/FTA)", fta_agreement="RCEP")
		self.assertEqual(doc.coo_type, "Preferential (EPA/FTA)")
		self.assertEqual(doc.fta_agreement, "RCEP")


class TestShippingLine(FrappeTestCase):
	def test_create_shipping_line(self):
		code = f"TS{frappe.generate_hash(length=2).upper()}"
		if frappe.db.exists("Shipping Line", code):
			frappe.delete_doc("Shipping Line", code, force=True)

		doc = frappe.get_doc({
			"doctype": "Shipping Line",
			"line_code": code,
			"line_name": "Test Shipping Line",
		})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.name, code)


class TestAirlineMaster(FrappeTestCase):
	def test_create_airline(self):
		code = f"T{frappe.generate_hash(length=1).upper()}"
		if frappe.db.exists("Airline Master", code):
			frappe.delete_doc("Airline Master", code, force=True)

		doc = frappe.get_doc({
			"doctype": "Airline Master",
			"iata_code": code,
			"airline_name": "Test Airline",
			"airline_prefix": "999",
		})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.name, code)


class TestVesselMaster(FrappeTestCase):
	def test_create_vessel(self):
		imo = f"IMO{frappe.generate_hash(length=7).upper()}"
		if frappe.db.exists("Vessel Master", imo):
			frappe.delete_doc("Vessel Master", imo, force=True)

		doc = frappe.get_doc({
			"doctype": "Vessel Master",
			"imo_number": imo,
			"vessel_name": "Test Vessel",
			"vessel_type": "Container",
		})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.name, imo)


class TestFreightForwarder(FrappeTestCase):
	def test_create_forwarder(self):
		name = f"Test Forwarder {frappe.generate_hash(length=4).upper()}"
		if frappe.db.exists("Freight Forwarder", name):
			frappe.delete_doc("Freight Forwarder", name, force=True)

		doc = frappe.get_doc({
			"doctype": "Freight Forwarder",
			"forwarder_name": name,
		})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.name, name)


class TestCustomsBroker(FrappeTestCase):
	def test_create_broker(self):
		name = f"Test Broker {frappe.generate_hash(length=4).upper()}"
		if frappe.db.exists("Customs Broker", name):
			frappe.delete_doc("Customs Broker", name, force=True)

		doc = frappe.get_doc({
			"doctype": "Customs Broker",
			"broker_name": name,
			"license_number": "T-9999",
		})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.name, name)


class TestCustomsDeclaration(TradeDocumentTestBase):
	def get_test_broker(self):
		name = "Test CD Broker"
		if not frappe.db.exists("Customs Broker", name):
			frappe.get_doc({
				"doctype": "Customs Broker",
				"broker_name": name,
				"license_number": "CD-0001",
			}).insert(ignore_permissions=True)
		return name

	def get_test_hs_code(self):
		hs = "8542.31"
		if not frappe.db.exists("Customs Tariff Number", hs):
			frappe.get_doc({
				"doctype": "Customs Tariff Number",
				"tariff_number": hs,
				"description": "Electronic integrated circuits - Processors",
			}).insert(ignore_permissions=True)
		return hs

	def create_cd(self, **kwargs):
		ts = self.create_trade_shipment(shipment_type="Import")
		broker = self.get_test_broker()
		hs_code = self.get_test_hs_code()
		company = (
			frappe.db.get_single_value("Global Defaults", "default_company")
			or frappe.get_all("Company", limit=1)[0].name
		)

		defaults = {
			"doctype": "Customs Declaration",
			"declaration_type": "Import",
			"trade_shipment": ts.name,
			"declaration_date": frappe.utils.today(),
			"customs_office": "Tokyo Customs",
			"declarant": broker,
			"importer_exporter_type": "Company",
			"importer_exporter": company,
			"invoice_amount": 100000,
			"invoice_currency": "USD",
			"exchange_rate_customs": 150.0,
			"customs_value": 105000,
			"customs_value_jpy": 15750000,
			"items": [{
				"description": "Electronic integrated circuits",
				"hs_code": hs_code,
				"country_of_origin": "China",
				"qty": 1000,
				"uom": "Nos",
				"statistical_value": 15000000,
				"customs_value": 15750000,
				"duty_rate": 3.3,
				"consumption_tax_rate": 10,
			}],
		}
		defaults.update(kwargs)
		doc = frappe.get_doc(defaults)
		doc.insert(ignore_permissions=True)
		return doc

	def test_create_cd(self):
		doc = self.create_cd()
		self.assertTrue(doc.name)
		self.assertTrue(doc.name.startswith("CD-IMP-"))
		self.assertEqual(doc.status, "Draft")

	def test_cd_export_naming(self):
		doc = self.create_cd(declaration_type="Export")
		self.assertTrue(doc.name.startswith("CD-EXP-"))

	def test_cd_duty_calculation(self):
		doc = self.create_cd()
		# duty = 15750000 * 3.3% = 519750
		self.assertAlmostEqual(doc.items[0].duty_amount, 519750, places=0)
		self.assertAlmostEqual(doc.total_duty, 519750, places=0)

	def test_cd_consumption_tax_calculation(self):
		doc = self.create_cd()
		# consumption_tax = (15750000 + 519750) * 10% = 1626975
		self.assertAlmostEqual(doc.items[0].consumption_tax_amount, 1626975, places=0)
		self.assertAlmostEqual(doc.total_consumption_tax, 1626975, places=0)

	def test_cd_local_tax_calculation(self):
		doc = self.create_cd()
		# local_tax = consumption_tax * 22/78
		expected_local = doc.total_consumption_tax * 22 / 78
		self.assertAlmostEqual(doc.total_local_tax, expected_local, places=0)

	def test_cd_total_taxes(self):
		doc = self.create_cd()
		expected = doc.total_duty + doc.total_consumption_tax + doc.total_local_tax
		self.assertAlmostEqual(doc.total_taxes, expected, places=0)

	def test_cd_preferential_rate(self):
		doc = self.create_cd()
		doc.items[0].preferential_rate = 0
		doc.items[0].preferential_agreement = "RCEP"
		doc.save()
		# When preferential_rate is 0, it should NOT override (>0 check)
		self.assertAlmostEqual(doc.items[0].duty_amount, 519750, places=0)

	def test_cd_submit(self):
		doc = self.create_cd()
		doc.submit()
		doc.reload()
		self.assertEqual(doc.docstatus, 1)
		self.assertEqual(doc.status, "Submitted")

	def test_cd_cancel(self):
		doc = self.create_cd()
		doc.submit()
		doc.cancel()
		doc.reload()
		self.assertEqual(doc.docstatus, 2)
		self.assertEqual(doc.status, "Cancelled")


class TestCustomsTariffRate(TradeDocumentTestBase):
	def get_test_hs_code(self):
		hs = "8542.31"
		if not frappe.db.exists("Customs Tariff Number", hs):
			frappe.get_doc({
				"doctype": "Customs Tariff Number",
				"tariff_number": hs,
				"description": "Electronic integrated circuits - Processors",
			}).insert(ignore_permissions=True)
		return hs

	def test_create_tariff_rate(self):
		hs_code = self.get_test_hs_code()
		doc = frappe.get_doc({
			"doctype": "Customs Tariff Rate",
			"customs_tariff_number": hs_code,
			"rate_type": "General",
			"duty_rate": 3.3,
			"effective_from": "2026-01-01",
		})
		doc.insert(ignore_permissions=True)
		self.assertTrue(doc.name)
		self.assertEqual(doc.duty_rate, 3.3)

	def test_tariff_rate_epa(self):
		hs_code = self.get_test_hs_code()
		doc = frappe.get_doc({
			"doctype": "Customs Tariff Rate",
			"customs_tariff_number": hs_code,
			"rate_type": "EPA",
			"country": "China",
			"fta_agreement": "RCEP",
			"duty_rate": 0,
			"effective_from": "2026-01-01",
			"effective_to": "2030-12-31",
		})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.rate_type, "EPA")
		self.assertEqual(doc.fta_agreement, "RCEP")

	def test_tariff_rate_invalid_dates(self):
		hs_code = self.get_test_hs_code()
		doc = frappe.get_doc({
			"doctype": "Customs Tariff Rate",
			"customs_tariff_number": hs_code,
			"rate_type": "General",
			"duty_rate": 5,
			"effective_from": "2026-12-31",
			"effective_to": "2026-01-01",
		})
		self.assertRaises(frappe.ValidationError, doc.insert)


class TestLetterOfCredit(TradeDocumentTestBase):
	def create_lc(self, **kwargs):
		ts = self.create_trade_shipment()
		company = (
			frappe.db.get_single_value("Global Defaults", "default_company")
			or frappe.get_all("Company", limit=1)[0].name
		)
		lc_number = f"LC-{frappe.generate_hash(length=8).upper()}"

		defaults = {
			"doctype": "Letter of Credit",
			"lc_number": lc_number,
			"lc_type": "Irrevocable",
			"trade_shipment": ts.name,
			"date_of_issue": frappe.utils.today(),
			"applicant_type": "Company",
			"applicant": company,
			"beneficiary_type": "Company",
			"beneficiary": company,
			"issuing_bank": "Test Bank Ltd.",
			"lc_amount": 100000,
			"currency": "USD",
			"expiry_date": frappe.utils.add_days(frappe.utils.today(), 90),
		}
		defaults.update(kwargs)
		doc = frappe.get_doc(defaults)
		doc.insert(ignore_permissions=True)
		return doc

	def test_create_lc(self):
		doc = self.create_lc()
		self.assertTrue(doc.name)
		self.assertEqual(doc.lc_type, "Irrevocable")
		self.assertEqual(doc.status, "Draft")

	def test_lc_balance_calculation(self):
		doc = self.create_lc()
		self.assertEqual(doc.balance, 100000)

	def test_lc_expiry_validation(self):
		doc = frappe.get_doc({
			"doctype": "Letter of Credit",
			"lc_number": f"LC-BAD-{frappe.generate_hash(length=4).upper()}",
			"lc_type": "Irrevocable",
			"date_of_issue": "2026-12-31",
			"applicant_type": "Company",
			"applicant": frappe.get_all("Company", limit=1)[0].name,
			"beneficiary_type": "Company",
			"beneficiary": frappe.get_all("Company", limit=1)[0].name,
			"issuing_bank": "Test Bank",
			"lc_amount": 50000,
			"currency": "USD",
			"expiry_date": "2026-01-01",
		})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_lc_draw(self):
		doc = self.create_lc()
		doc.draw(30000)
		doc.reload()
		self.assertEqual(doc.drawn_amount, 30000)
		self.assertEqual(doc.balance, 70000)
		self.assertEqual(doc.status, "Partially Drawn")

	def test_lc_fully_drawn(self):
		doc = self.create_lc()
		doc.draw(100000)
		doc.reload()
		self.assertEqual(doc.status, "Fully Drawn")
		self.assertEqual(doc.balance, 0)

	def test_lc_overdraw_blocked(self):
		doc = self.create_lc()
		self.assertRaises(frappe.ValidationError, doc.draw, 200000)

	def test_lc_with_amendment(self):
		doc = self.create_lc()
		doc.append("amendments", {
			"amendment_date": frappe.utils.today(),
			"amendment_number": "AMD-001",
			"amendment_type": "Amount Change",
			"description": "Increase L/C amount",
			"old_value": "100000",
			"new_value": "150000",
		})
		doc.save()
		self.assertEqual(len(doc.amendments), 1)


class TestTradeComplianceCheck(TradeDocumentTestBase):
	def create_tcc(self, **kwargs):
		ts = self.create_trade_shipment()

		defaults = {
			"doctype": "Trade Compliance Check",
			"check_type": "Sanctions Screening",
			"trade_shipment": ts.name,
			"check_date": frappe.utils.now(),
			"checked_entity": "Test Company XYZ Corp.",
			"result": "Clear",
		}
		defaults.update(kwargs)
		doc = frappe.get_doc(defaults)
		doc.insert(ignore_permissions=True)
		return doc

	def test_create_tcc(self):
		doc = self.create_tcc()
		self.assertTrue(doc.name)
		self.assertTrue(doc.name.startswith("TCC-"))
		self.assertEqual(doc.result, "Clear")

	def test_tcc_with_hit(self):
		doc = self.create_tcc(result="Hit")
		doc.append("matched_entries", {
			"list_name": "OFAC SDN",
			"matched_name": "Test Entity",
			"match_score": 95,
			"match_type": "Fuzzy",
		})
		doc.save()
		self.assertEqual(doc.result, "Hit")
		self.assertEqual(len(doc.matched_entries), 1)

	def test_tcc_review(self):
		doc = self.create_tcc(result="Possible Match")
		doc.reviewed_by = "Administrator"
		doc.review_date = frappe.utils.now()
		doc.review_decision = "Approved"
		doc.save()
		self.assertEqual(doc.review_decision, "Approved")

	def test_tcc_export_control(self):
		doc = self.create_tcc(check_type="Export Control")
		self.assertEqual(doc.check_type, "Export Control")


class TestSanctionsListEntry(FrappeTestCase):
	def test_create_sanctions_entry(self):
		doc = frappe.get_doc({
			"doctype": "Sanctions List Entry",
			"entity_name": "Test Sanctioned Entity",
			"entity_type": "Organization",
			"list_source": "OFAC SDN",
			"program": "SDGT",
			"is_active": 1,
		})
		doc.insert(ignore_permissions=True)
		self.assertTrue(doc.name)
		self.assertEqual(doc.entity_type, "Organization")

	def test_sanctions_entry_individual(self):
		doc = frappe.get_doc({
			"doctype": "Sanctions List Entry",
			"entity_name": "Test Sanctioned Person",
			"entity_type": "Individual",
			"list_source": "UN Security Council",
			"country": "Japan",
			"aliases": "Test Person Alias 1\nTest Person Alias 2",
			"is_active": 1,
		})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.entity_type, "Individual")
		self.assertIn("Alias 1", doc.aliases)


class TestDocumentCheckService(TradeDocumentTestBase):
	def test_check_empty_shipment(self):
		from lifegence_industry.trade_management.services.document_check import check_document_consistency
		ts = self.create_trade_shipment()
		results = check_document_consistency(ts.name)
		# Should have document completeness checks
		self.assertTrue(len(results) > 0)
		# All docs should be missing
		missing = [r for r in results if r["status"] == "Missing"]
		self.assertTrue(len(missing) > 0)

	def test_check_with_documents(self):
		from lifegence_industry.trade_management.services.document_check import check_document_consistency
		ts = self.create_trade_shipment()
		item_code = self.get_test_item()
		incoterms = frappe.get_all("Incoterm", limit=1)

		# Create CI
		frappe.get_doc({
			"doctype": "Commercial Invoice",
			"trade_shipment": ts.name,
			"invoice_date": frappe.utils.today(),
			"currency": "USD",
			"seller_name": "Seller",
			"seller_address": "Tokyo",
			"buyer_name": "Buyer",
			"buyer_address": "Shanghai",
			"incoterm": incoterms[0].name if incoterms else None,
			"country_of_origin": "Japan",
			"items": [{"item_code": item_code, "qty": 10, "uom": "Nos", "rate": 100}],
		}).insert(ignore_permissions=True)

		results = check_document_consistency(ts.name)
		ci_check = [r for r in results if "Commercial Invoice" in r["check_item"]]
		self.assertEqual(ci_check[0]["status"], "OK")
