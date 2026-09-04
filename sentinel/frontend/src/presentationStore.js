/**
 * Global persistent store for SENTINEL Presentation Mode.
 * 
 * When Presentation Mode is active:
 * - Disruptive visual toasts and alert pop-ups are suppressed.
 * - Underlying risk scoring, WebSocket pipelines, case creation,
 *   audit logging, and operator actions continue running 100% normally.
 */

const STORAGE_KEY = 'sentinel_presentation_mode';

// Initialize from localStorage (default: false)
let presentationMode = (() => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(STORAGE_KEY) === 'true';
    }
  } catch (err) {
    console.warn('[PresentationStore] Failed to read localStorage:', err);
  }
  return false;
})();

const listeners = new Set();

/**
 * Returns current presentation mode synchronously.
 * @returns {boolean}
 */
export const getPresentationMode = () => presentationMode;

/**
 * Set presentation mode, persist to localStorage, notify listeners,
 * and dispatch window event.
 * @param {boolean} enabled 
 */
export const setPresentationMode = (enabled) => {
  presentationMode = Boolean(enabled);

  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEY, String(presentationMode));
    }
  } catch (err) {
    console.warn('[PresentationStore] Failed to write localStorage:', err);
  }

  // Notify store subscribers
  listeners.forEach((listener) => {
    try {
      listener(presentationMode);
    } catch (err) {
      console.error('[PresentationStore] Listener error:', err);
    }
  });

  // Dispatch custom event for external listeners
  if (typeof window !== 'undefined' && window.dispatchEvent) {
    window.dispatchEvent(
      new CustomEvent('sentinel_presentation_mode_changed', {
        detail: { presentationMode }
      })
    );
  }

  return presentationMode;
};

/**
 * Toggles current presentation mode.
 * @returns {boolean} New presentation mode state
 */
export const togglePresentationMode = () => {
  return setPresentationMode(!presentationMode);
};

/**
 * Subscribe a listener callback to presentation mode changes.
 * @param {(mode: boolean) => void} listener 
 * @returns {() => void} Unsubscribe function
 */
export const subscribePresentationMode = (listener) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

/**
 * Resets store state (used primarily for test isolation).
 */
export const resetPresentationStoreForTesting = (initial = false) => {
  presentationMode = Boolean(initial);
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEY, String(presentationMode));
    }
  } catch {
    // ignore
  }
  listeners.clear();
};
