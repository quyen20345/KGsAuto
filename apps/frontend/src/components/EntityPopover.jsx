import { useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../services/api';
import EntityLink from './EntityLink';
import RelationshipTooltip from './RelationshipTooltip';

export default function EntityPopover({ entityId, triggerRef, isVisible, onMouseEnter, onMouseLeave }) {
  const [entity, setEntity] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const popoverRef = useRef(null);

  useEffect(() => {
    if (!isVisible || !entityId) {
      return;
    }

    setLoading(true);
    setError(false);

    api.getEntity(entityId)
      .then((data) => {
        setEntity(data);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, [entityId, isVisible]);

  useEffect(() => {
    if (!isVisible || !triggerRef.current) {
      return;
    }

    const updatePosition = () => {
      const triggerRect = triggerRef.current.getBoundingClientRect();
      const popoverWidth = 500;
      const popoverHeight = 600;
      const padding = 20; // Increased from 10 to 20

      let top = triggerRect.bottom + padding;
      let left = triggerRect.left;

      // Adjust if popover goes off right edge
      if (left + popoverWidth > window.innerWidth) {
        left = window.innerWidth - popoverWidth - padding;
      }

      // Adjust if popover goes off left edge
      if (left < padding) {
        left = padding;
      }

      // Adjust if popover goes off bottom edge - show above instead
      if (top + popoverHeight > window.innerHeight) {
        top = triggerRect.top - popoverHeight - padding;
      }

      // If still off top edge, position at top of viewport with more spacing
      if (top < padding) {
        top = padding;
      }

      setPosition({ top, left });
    };

    updatePosition();
    window.addEventListener('scroll', updatePosition);
    window.addEventListener('resize', updatePosition);

    return () => {
      window.removeEventListener('scroll', updatePosition);
      window.removeEventListener('resize', updatePosition);
    };
  }, [isVisible, triggerRef]);

  if (!isVisible) {
    return null;
  }

  const popoverContent = (
    <div
      ref={popoverRef}
      className="entity-popover"
      style={{
        position: 'fixed',
        top: `${position.top}px`,
        left: `${position.left}px`,
        zIndex: 99999,
        isolation: 'isolate',
      }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {loading && (
        <div className="entity-popover-loading">
          Loading entity details...
        </div>
      )}

      {error && (
        <div className="entity-popover-error">
          Failed to load entity details
        </div>
      )}

      {entity && !loading && !error && (
        <div className="entity-popover-content">
          <div className="entity-popover-header">
            <h3 className="entity-title" style={{ fontSize: '1.3rem', margin: '0 0 8px 0' }}>
              <EntityLink entityId={entity.id} disablePopover={true}>
                {entity.name || entity.id}
              </EntityLink>
            </h3>
            <div className="entity-uri" style={{ fontSize: '0.85rem' }}>ID: {entity.id}</div>
            <div style={{ marginTop: '8px' }}>
              {entity.labels.map((l) => (
                <span key={l} className="badge" style={{ fontSize: '0.75rem' }}>
                  {l}
                </span>
              ))}
            </div>
          </div>

          {Object.entries(entity.properties).filter(([key]) => key !== 'id' && key !== 'name').length > 0 && (
            <>
              <div className="statements-header" style={{ fontSize: '1rem', marginTop: '16px' }}>
                Properties
              </div>
              <table style={{ fontSize: '0.9rem' }}>
                <thead>
                  <tr>
                    <th>Predicate</th>
                    <th>Object</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(entity.properties)
                    .filter(([key]) => key !== 'id' && key !== 'name')
                    .map(([key, val]) => (
                      <tr key={`prop-${key}`}>
                        <td className="predicate">prop:{key}</td>
                        <td className="object">
                          {Array.isArray(val) ? val.map((v, i) => <div key={i}>{v}</div>) : val}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </>
          )}

          {entity.outgoing && entity.outgoing.length > 0 && (
            <>
              <div className="statements-header" style={{ fontSize: '1rem', marginTop: '16px' }}>
                Relationships
              </div>
              <table style={{ fontSize: '0.9rem' }}>
                <thead>
                  <tr>
                    <th>Predicate</th>
                    <th>Object</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(
                    entity.outgoing.reduce((acc, rel) => {
                      acc[rel.type] = acc[rel.type] || [];
                      acc[rel.type].push(rel);
                      return acc;
                    }, {})
                  ).map(([type, rels]) => {
                    // Get description from first relationship of this type
                    const relationshipDescription = rels[0]?.properties?.description;
                    const descriptionText = Array.isArray(relationshipDescription)
                      ? relationshipDescription[0]
                      : relationshipDescription;

                    return (
                      <tr key={`out-${type}`}>
                        <td className="predicate">
                          <RelationshipTooltip
                            relationshipType={type}
                            description={descriptionText}
                          >
                            rel:{type}
                          </RelationshipTooltip>
                        </td>
                        <td className="object">
                          {rels.map((r, i) => (
                            <div key={i} style={{ marginBottom: '8px' }}>
                              <EntityLink entityId={r.target_id} disablePopover={true}>
                                {r.target_name || r.target_id}
                              </EntityLink>
                            </div>
                          ))}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}
    </div>
  );

  return createPortal(popoverContent, document.body);
}
