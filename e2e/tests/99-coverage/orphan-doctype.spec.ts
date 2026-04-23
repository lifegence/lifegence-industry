import * as path from 'path';
import { createOrphanDocTypeSpec } from '@lifegence/e2e-common';
import { KNOWN_UI_HIDDEN_DOCTYPES } from '../../fixtures/coverage-allowlist';

createOrphanDocTypeSpec({
  modules: ['Medical Receipt', 'Trade Management'],
  appRoot: path.resolve(__dirname, '../../../lifegence_industry'),
  entryPoints: [
    '/desk',
    '/desk/medical-receipt',
    '/desk/trade-management',
  ],
  allowlist: KNOWN_UI_HIDDEN_DOCTYPES,
});
