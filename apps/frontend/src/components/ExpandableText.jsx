import { useState, useRef, useCallback } from 'react';

export default function ExpandableText({ text, maxLength = 100 }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const triggerRef = useRef(null);

  const handleMouseEnter = useCallback((e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const tooltipWidth = 350;
    const padding = 10;

    let left = rect.left + rect.width / 2 - tooltipWidth / 2;
    let top = rect.bottom + padding;

    if (left + tooltipWidth > window.innerWidth) left = window.innerWidth - tooltipWidth - padding;
    if (left < padding) left = padding;
    if (top + 100 > window.innerHeight) top = rect.top - 100 - padding;

    setPosition({ top, left });
    setShowTooltip(true);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setShowTooltip(false);
  }, []);

  if (text === null || text === undefined) return null;
  
  const content = String(text);
  if (content.length <= maxLength) {
    return <span>{content}</span>;
  }
  
  const truncated = `${content.substring(0, maxLength).trim()}...`;
  
  return (
    <>
      <span 
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        style={{ cursor: 'pointer', borderBottom: '1px dotted currentColor' }}
      >
        {truncated}
      </span>
      
      {showTooltip && (
        <div
          className="relationship-tooltip"
          style={{
            position: 'fixed',
            top: `${position.top}px`,
            left: `${position.left}px`,
            zIndex: 999999,
            maxWidth: '400px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            pointerEvents: 'none'
          }}
        >
          <div className="relationship-tooltip-content">
            <div className="relationship-tooltip-description">{content}</div>
          </div>
        </div>
      )}
    </>
  );
}
