import React from 'react';

const ActionButton = ({ label, onClick, disabled, className = "" }) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-3 py-1.5 bg-primary text-white rounded-lg text-xs font-semibold 
      hover:bg-primary/90 transition-all duration-150 shadow-sm font-sans shrink-0
      ${disabled ? 'opacity-40 grayscale cursor-not-allowed pointer-events-none' : 'cursor-pointer active:scale-[0.98]'} ${className}`}
    >
      {label}
    </button>
  );
};

export default ActionButton;
