import { useState, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import EntityPopover from './EntityPopover';

export default function EntityLink({ entityId, children, className = 'internal-link', disablePopover = false }) {
  const [isHovered, setIsHovered] = useState(false);
  const [showPopover, setShowPopover] = useState(false);
  const linkRef = useRef(null);
  const hoverTimeoutRef = useRef(null);
  const hideTimeoutRef = useRef(null);

  const handleMouseEnter = useCallback(() => {
    if (disablePopover) return;

    setIsHovered(true);

    // Clear any pending hide timeout
    if (hideTimeoutRef.current) {
      clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }

    // Delay showing popover by 300ms to prevent accidental triggers
    hoverTimeoutRef.current = setTimeout(() => {
      setShowPopover(true);
    }, 300);
  }, [disablePopover]);

  const handleMouseLeave = useCallback(() => {
    if (disablePopover) return;

    setIsHovered(false);

    // Clear the timeout if mouse leaves before popover shows
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }

    // Delay hiding popover by 500ms to allow moving to popover
    hideTimeoutRef.current = setTimeout(() => {
      setShowPopover(false);
    }, 500);
  }, [disablePopover]);

  const handlePopoverMouseEnter = useCallback(() => {
    // Keep popover open when hovering over it
    setIsHovered(true);
    setShowPopover(true);

    // Clear any pending hide timeout
    if (hideTimeoutRef.current) {
      clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }
  }, []);

  const handlePopoverMouseLeave = useCallback(() => {
    // Hide popover when mouse leaves popover
    setIsHovered(false);
    setShowPopover(false);
  }, []);

  return (
    <>
      <Link
        ref={linkRef}
        className={className}
        to={`/entity/${entityId}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {children}
      </Link>

      {!disablePopover && (
        <EntityPopover
          entityId={entityId}
          triggerRef={linkRef}
          isVisible={showPopover}
          onMouseEnter={handlePopoverMouseEnter}
          onMouseLeave={handlePopoverMouseLeave}
        />
      )}
    </>
  );
}
