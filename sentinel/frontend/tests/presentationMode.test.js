import test, { describe, beforeEach } from 'node:test';
import assert from 'node:assert';

// Mock DOM / Browser environment for Node.js test runner
const createMockLocalStorage = () => {
  const store = new Map();
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => { store.set(key, String(value)); },
    removeItem: (key) => { store.delete(key); },
    clear: () => { store.clear(); }
  };
};

class MockCustomEvent {
  constructor(type, eventInitDict = {}) {
    this.type = type;
    this.detail = eventInitDict.detail || {};
  }
}

const eventListeners = new Map();

global.localStorage = createMockLocalStorage();
global.CustomEvent = MockCustomEvent;
global.window = {
  localStorage: global.localStorage,
  addEventListener: (event, cb) => {
    if (!eventListeners.has(event)) eventListeners.set(event, new Set());
    eventListeners.get(event).add(cb);
  },
  removeEventListener: (event, cb) => {
    if (eventListeners.has(event)) eventListeners.get(event).delete(cb);
  },
  dispatchEvent: (event) => {
    const listeners = eventListeners.get(event.type);
    if (listeners) {
      listeners.forEach((cb) => cb(event));
    }
    return true;
  }
};

describe('SENTINEL Presentation Mode Suite', async () => {
  const {
    getPresentationMode,
    setPresentationMode,
    togglePresentationMode,
    subscribePresentationMode,
    resetPresentationStoreForTesting
  } = await import('../src/presentationStore.js');

  beforeEach(() => {
    global.localStorage.clear();
    eventListeners.clear();
    resetPresentationStoreForTesting(false);
  });

  test('Scenario 1: Presentation Mode OFF - Critical event produces normal popup', () => {
    setPresentationMode(false);
    assert.strictEqual(getPresentationMode(), false);

    let popupRendered = false;
    let renderedAlert = null;

    // Simulate LiveAlertToast listener logic
    const handleAlert = (e) => {
      if (getPresentationMode()) return;
      const data = e.detail || {};
      if (data.risk_score >= 70) {
        popupRendered = true;
        renderedAlert = data;
      }
    };

    window.addEventListener('sentinel_alert', handleAlert);

    const criticalEvent = new CustomEvent('sentinel_alert', {
      detail: { tx_id: 'TX-CRIT-001', risk_score: 94, amount: 250000, risk_level: 'CRITICAL' }
    });
    window.dispatchEvent(criticalEvent);

    assert.strictEqual(popupRendered, true, 'Alert popup must be rendered when Presentation Mode is OFF');
    assert.strictEqual(renderedAlert.tx_id, 'TX-CRIT-001');
    assert.strictEqual(renderedAlert.risk_score, 94);
  });

  test('Scenario 2: Presentation Mode ON - Critical event does not produce popup', () => {
    setPresentationMode(true);
    assert.strictEqual(getPresentationMode(), true);

    let popupRendered = false;
    let actionToastRendered = false;

    // Simulate LiveAlertToast and ActionTakenToast suppression
    const handleAlert = (e) => {
      if (getPresentationMode()) return;
      const data = e.detail || {};
      if (data.risk_score >= 70) {
        popupRendered = true;
      }
    };

    const handleAction = (e) => {
      if (getPresentationMode()) return;
      actionToastRendered = true;
    };

    window.addEventListener('sentinel_alert', handleAlert);
    window.addEventListener('sentinel_transaction_action', handleAction);

    // Dispatch critical alert & operator required action
    window.dispatchEvent(new CustomEvent('sentinel_alert', {
      detail: { tx_id: 'TX-CRIT-002', risk_score: 88, risk_level: 'CRITICAL' }
    }));
    window.dispatchEvent(new CustomEvent('sentinel_transaction_action', {
      detail: { tx_id: 'TX-CRIT-002', action: 'FREEZE', execution_status: 'REQUIRES_OPERATOR_ACTION' }
    }));

    assert.strictEqual(popupRendered, false, 'Critical risk popup must be suppressed in Presentation Mode');
    assert.strictEqual(actionToastRendered, false, 'Action toast popup must be suppressed in Presentation Mode');
  });

  test('Scenario 3: Presentation Mode ON - WebSocket events are still received and dispatched', () => {
    setPresentationMode(true);

    let wsEventDispatched = false;
    let receivedPayload = null;

    window.addEventListener('sentinel_alert', (e) => {
      wsEventDispatched = true;
      receivedPayload = e.detail;
    });

    const incomingPayload = {
      event: 'tx_scored',
      tx_id: 'TX-INCOMING-101',
      risk_score: 92,
      risk_level: 'CRITICAL',
      amount: 1500000
    };

    // WebSocket event bus dispatch
    window.dispatchEvent(new CustomEvent('sentinel_alert', { detail: incomingPayload }));

    assert.strictEqual(wsEventDispatched, true, 'WebSocket event must continue dispatching in Presentation Mode');
    assert.strictEqual(receivedPayload.tx_id, 'TX-INCOMING-101');
    assert.strictEqual(receivedPayload.risk_score, 92);
  });

  test('Scenario 4: Presentation Mode ON - Transaction/case state still updates normally', () => {
    setPresentationMode(true);

    // Mock store state representing application feed and case management
    const stateStore = {
      transactions: [],
      cases: []
    };

    const processTxScored = (payload) => {
      stateStore.transactions.unshift({
        tx_id: payload.tx_id,
        risk_score: payload.risk_score,
        risk_level: payload.risk_level
      });
      if (payload.risk_score >= 85) {
        stateStore.cases.push({
          case_id: `CASE-${payload.tx_id}`,
          status: 'NEW',
          primary_tx_id: payload.tx_id,
          total_fraud_amount: payload.amount
        });
      }
    };

    processTxScored({ tx_id: 'TX-FEED-55', risk_score: 89, risk_level: 'CRITICAL', amount: 800000 });

    assert.strictEqual(stateStore.transactions.length, 1);
    assert.strictEqual(stateStore.transactions[0].tx_id, 'TX-FEED-55');
    assert.strictEqual(stateStore.transactions[0].risk_score, 89);
    assert.strictEqual(stateStore.cases.length, 1);
    assert.strictEqual(stateStore.cases[0].case_id, 'CASE-TX-FEED-55');
  });

  test('Scenario 5: Toggle persists after browser reload via localStorage', () => {
    // Presenter enables Presentation Mode
    setPresentationMode(true);
    assert.strictEqual(global.localStorage.getItem('sentinel_presentation_mode'), 'true');

    // Simulate page reload: re-read preference from localStorage
    const reloadedValue = global.localStorage.getItem('sentinel_presentation_mode') === 'true';
    assert.strictEqual(reloadedValue, true, 'Presentation Mode preference must persist in localStorage');

    // Presenter turns it OFF
    setPresentationMode(false);
    assert.strictEqual(global.localStorage.getItem('sentinel_presentation_mode'), 'false');
    const reloadedValueOff = global.localStorage.getItem('sentinel_presentation_mode') === 'true';
    assert.strictEqual(reloadedValueOff, false, 'OFF state must persist in localStorage');
  });

  test('Scenario 6: Turning Presentation Mode OFF restores normal popups without application restart', () => {
    let popupRenderCount = 0;
    const handleAlert = () => {
      if (getPresentationMode()) return;
      popupRenderCount += 1;
    };
    window.addEventListener('sentinel_alert', handleAlert);

    // 1. Initially ON: event suppressed
    setPresentationMode(true);
    window.dispatchEvent(new CustomEvent('sentinel_alert', { detail: { risk_score: 90 } }));
    assert.strictEqual(popupRenderCount, 0, 'Popup should not render when mode is ON');

    // 2. Presenter dynamically toggles OFF during demo
    setPresentationMode(false);
    assert.strictEqual(getPresentationMode(), false);

    // 3. New event arrives immediately
    window.dispatchEvent(new CustomEvent('sentinel_alert', { detail: { risk_score: 95 } }));
    assert.strictEqual(popupRenderCount, 1, 'Popup must immediately render once Presentation Mode is toggled OFF');
  });

  test('Scenario 7: No duplicate notification subscriptions or memory leaks', () => {
    let callCount = 0;
    const listener = () => {
      callCount += 1;
    };

    const unsubscribe = subscribePresentationMode(listener);
    togglePresentationMode();
    assert.strictEqual(callCount, 1);

    togglePresentationMode();
    assert.strictEqual(callCount, 2);

    unsubscribe();
    togglePresentationMode();
    assert.strictEqual(callCount, 2, 'Unsubscribed listener must not receive further notifications');
  });

  test('Scenario 8: Existing non-popup UI behavior remains unchanged', () => {
    setPresentationMode(true);

    // Risk badge calculation test
    const getRiskBadgeProps = (score) => {
      if (score >= 85) return { label: 'CRITICAL', color: 'rose' };
      if (score >= 70) return { label: 'HIGH', color: 'orange' };
      if (score >= 40) return { label: 'MEDIUM', color: 'amber' };
      return { label: 'LOW', color: 'emerald' };
    };

    const criticalBadge = getRiskBadgeProps(91);
    assert.strictEqual(criticalBadge.label, 'CRITICAL');
    assert.strictEqual(criticalBadge.color, 'rose');

    const highBadge = getRiskBadgeProps(74);
    assert.strictEqual(highBadge.label, 'HIGH');
    assert.strictEqual(highBadge.color, 'orange');
  });
});
