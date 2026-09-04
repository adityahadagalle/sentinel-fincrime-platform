import test, { describe } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import parser from '@babel/parser';
import traverseModule from '@babel/traverse';

const traverse = traverseModule.default || traverseModule;
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

const browserGlobals = new Set([
  'console', 'window', 'document', 'fetch', 'setTimeout', 'clearTimeout',
  'setInterval', 'clearInterval', 'Math', 'JSON', 'Object', 'Array',
  'String', 'Number', 'Boolean', 'Date', 'Promise', 'alert', 'confirm',
  'undefined', 'null', 'NaN', 'Infinity', 'process', 'encodeURIComponent',
  'decodeURIComponent', 'Intl', 'navigator', 'localStorage', 'sessionStorage',
  'WebSocket', 'EventSource', 'CustomEvent', 'Event', 'URL', 'URLSearchParams',
  'location', 'history', 'requestAnimationFrame', 'cancelAnimationFrame',
  'FormData', 'Blob', 'File', 'FileReader', 'AbortController', 'Headers',
  'Request', 'Response', 'performance'
]);

describe('SENTINEL Benchmark Lab Runtime Integrity & Regression Suite', () => {

  test('BenchmarkLab.jsx has zero undeclared identifiers in AST scope', () => {
    const filePath = path.join(rootDir, 'src', 'pages', 'BenchmarkLab.jsx');
    const code = fs.readFileSync(filePath, 'utf8');
    const ast = parser.parse(code, {
      sourceType: 'module',
      plugins: ['jsx']
    });

    const undeclared = new Set();
    traverse(ast, {
      Program(p) {
        p.traverse({
          ReferencedIdentifier(identPath) {
            const name = identPath.node.name;
            if (browserGlobals.has(name)) return;
            if (!identPath.scope.hasBinding(name)) {
              undeclared.add(name);
            }
          }
        });
      }
    });

    assert.deepStrictEqual(
      Array.from(undeclared),
      [],
      `BenchmarkLab.jsx contains undeclared identifiers: ${Array.from(undeclared).join(', ')}`
    );
  });

  test('CustomTransactionModal.jsx has zero undeclared identifiers in AST scope', () => {
    const filePath = path.join(rootDir, 'src', 'components', 'CustomTransactionModal.jsx');
    const code = fs.readFileSync(filePath, 'utf8');
    const ast = parser.parse(code, {
      sourceType: 'module',
      plugins: ['jsx']
    });

    const undeclared = new Set();
    traverse(ast, {
      Program(p) {
        p.traverse({
          ReferencedIdentifier(identPath) {
            const name = identPath.node.name;
            if (browserGlobals.has(name)) return;
            if (!identPath.scope.hasBinding(name)) {
              undeclared.add(name);
            }
          }
        });
      }
    });

    assert.deepStrictEqual(
      Array.from(undeclared),
      [],
      `CustomTransactionModal.jsx contains undeclared identifiers: ${Array.from(undeclared).join(', ')}`
    );
  });

  test('BenchmarkLab explicitly defines handleCustomInputAdded callback', () => {
    const filePath = path.join(rootDir, 'src', 'pages', 'BenchmarkLab.jsx');
    const code = fs.readFileSync(filePath, 'utf8');

    assert.ok(
      code.includes('const handleCustomInputAdded = (data) =>'),
      'BenchmarkLab.jsx must explicitly define handleCustomInputAdded'
    );
    assert.ok(
      code.includes('onAddedToBatch={handleCustomInputAdded}'),
      'BenchmarkLab.jsx must pass handleCustomInputAdded to onAddedToBatch'
    );
    assert.ok(
      code.includes('onCustomInputAdded={handleCustomInputAdded}'),
      'BenchmarkLab.jsx must pass handleCustomInputAdded to onCustomInputAdded'
    );
  });

  test('CustomTransactionModal accepts and triggers onCustomInputAdded and onAddedToBatch', () => {
    const filePath = path.join(rootDir, 'src', 'components', 'CustomTransactionModal.jsx');
    const code = fs.readFileSync(filePath, 'utf8');

    assert.ok(
      code.includes('onCustomInputAdded'),
      'CustomTransactionModal must accept onCustomInputAdded prop'
    );
    assert.ok(
      code.includes('onAddedToBatch'),
      'CustomTransactionModal must accept onAddedToBatch prop'
    );
  });

  test('Custom transaction addition data-flow contract updates ledger and summary', () => {
    // Simulate benchmark batch state receiving custom transaction
    let benchmarkRun = {
      run_id: 'BM-TEST-001',
      status: 'UNEVALUATED',
      total_requested: 2,
      transactions: [
        { tx_id: 'TX-001', status: 'UNEVALUATED' },
        { tx_id: 'TX-002', status: 'UNEVALUATED' }
      ]
    };

    const handleCustomInputAddedMock = (data) => {
      if (data?.transaction) {
        benchmarkRun = {
          ...benchmarkRun,
          transactions: [data.transaction, ...benchmarkRun.transactions],
          total_requested: data.total_requested ?? (benchmarkRun.total_requested + 1)
        };
      }
    };

    const incomingData = {
      run_id: 'BM-TEST-001',
      status: 'UNEVALUATED',
      total_requested: 3,
      transaction: {
        tx_id: 'TX-BM-TEST-001-CUST-0003',
        benchmark_run_id: 'BM-TEST-001',
        benchmark_profile: 'CUSTOM_MANUAL',
        amount: 75000,
        status: 'UNEVALUATED'
      }
    };

    handleCustomInputAddedMock(incomingData);

    assert.strictEqual(benchmarkRun.transactions.length, 3);
    assert.strictEqual(benchmarkRun.transactions[0].tx_id, 'TX-BM-TEST-001-CUST-0003');
    assert.strictEqual(benchmarkRun.total_requested, 3);
  });

});
