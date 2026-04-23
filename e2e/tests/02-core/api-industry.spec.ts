import { test, expect, FrappeClient } from '@lifegence/e2e-common';

test.describe('Industry — DocType lists across modules (P1)', () => {
  let client: FrappeClient;

  test.beforeAll(async ({ baseURL }) => {
    client = await FrappeClient.login(
      baseURL!,
      process.env.ADMIN_USR || 'Administrator',
      process.env.ADMIN_PWD || 'admin',
    );
  });
  test.afterAll(async () => await client.dispose());

  for (const entity of [
    // Medical Receipt
    'Patient Encounter',
    'Patient Insurance Info',
    'Receipt',
    'Receipt Batch',
    'Medical Service Master',
    'Disease Master',
    // Trade Management
    'Trade Shipment',
    'Bill of Lading',
    'Air Waybill',
    'Commercial Invoice',
    'Packing List',
    'Certificate of Origin',
    'Letter of Credit',
    'Customs Declaration',
  ]) {
    test(`${entity} list is accessible`, async () => {
      const list = await client.getList<{ name: string }>(entity, {
        fields: ['name'], limit_page_length: 5,
      });
      expect(Array.isArray(list)).toBe(true);
    });
  }
});
