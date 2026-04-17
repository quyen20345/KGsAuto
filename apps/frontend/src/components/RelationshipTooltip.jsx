import { useState, useRef, useCallback } from 'react';

export default function RelationshipTooltip({ relationshipType, description, children }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const triggerRef = useRef(null);
  const tooltipRef = useRef(null);

  const handleMouseEnter = useCallback((e) => {
    if (!description) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const tooltipWidth = 300;
    const padding = 10;

    let left = rect.left + rect.width / 2 - tooltipWidth / 2;
    let top = rect.bottom + padding;

    // Adjust if tooltip goes off right edge
    if (left + tooltipWidth > window.innerWidth) {
      left = window.innerWidth - tooltipWidth - padding;
    }

    // Adjust if tooltip goes off left edge
    if (left < padding) {
      left = padding;
    }

    // If tooltip would go off bottom, show above instead
    if (top + 100 > window.innerHeight) {
      top = rect.top - 100 - padding;
    }

    setPosition({ top, left });
    setShowTooltip(true);
  }, [description]);

  const handleMouseLeave = useCallback(() => {
    setShowTooltip(false);
  }, []);

  if (!description) {
    return children;
  }

  return (
    <>
      <span
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        style={{
          cursor: 'help',
          borderBottom: '1px dotted currentColor',
          display: 'inline-block',
        }}
      >
        {children}
      </span>

      {showTooltip && (
        <div
          ref={tooltipRef}
          className="relationship-tooltip"
          style={{
            position: 'fixed',
            top: `${position.top}px`,
            left: `${position.left}px`,
            zIndex: 20000,
          }}
        >
          <div className="relationship-tooltip-content">
            <div className="relationship-tooltip-type">{relationshipType}</div>
            <div className="relationship-tooltip-description">{description}</div>
          </div>
        </div>
      )}
    </>
  );
}
