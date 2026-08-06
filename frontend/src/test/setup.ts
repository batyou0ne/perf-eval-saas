import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';

// Without `test.globals: true`, RTL can't auto-detect a global afterEach to
// hook its cleanup into, so each render() would otherwise pile up in the DOM
// across tests in the same file.
afterEach(cleanup);
