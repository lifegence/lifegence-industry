import { createLegacyRedirectSpec } from '@lifegence/e2e-common';

createLegacyRedirectSpec({
  paths: [
    { legacy: '/app/medical-receipt', canonical: '/desk/medical-receipt' },
    { legacy: '/app/patient-encounter', canonical: '/desk/patient-encounter' },
    { legacy: '/app/trade-shipment', canonical: '/desk/trade-shipment' },
  ],
});
