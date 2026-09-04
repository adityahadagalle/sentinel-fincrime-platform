import { useState, useEffect } from 'react';
import {
  getPresentationMode,
  setPresentationMode,
  togglePresentationMode,
  subscribePresentationMode
} from '../presentationStore';

/**
 * Custom React hook to consume and control Presentation Mode state.
 * Syncs seamlessly across components and persists in localStorage.
 */
export const usePresentationMode = () => {
  const [isPresentationMode, setIsPresentationMode] = useState(getPresentationMode());

  useEffect(() => {
    // Initial sync
    setIsPresentationMode(getPresentationMode());

    // Subscribe to store updates
    const unsubscribe = subscribePresentationMode((newMode) => {
      setIsPresentationMode(newMode);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  return {
    isPresentationMode,
    setPresentationMode,
    togglePresentationMode
  };
};

export default usePresentationMode;
