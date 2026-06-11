import * as path from 'path';
import { createDeadWorkspaceLinkSpec } from '@lifegence/e2e-common';

createDeadWorkspaceLinkSpec({
  appRoot: path.resolve(__dirname, '../../../lifegence_industry'),
});
