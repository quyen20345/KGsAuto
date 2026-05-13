import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../services/api';

const CHECKLIST_LABELS = {
  name_match: 'Name Match',
  alias_overlap: 'Alias Overlap',
  label_match: 'Label Match',
  description_contradiction: 'Contradiction',
  relationship_overlap: 'Relationship Overlap',
};

export default function CompareModal({ isOpen, onClose, entityA, duplicateId, onMergeComplete }) {
  const [loading, setLoading] = useState(false);
  const [comparison, setComparison] = useState(null);
  const [error, setError] = useState(null);
  const [merging, setMerging] = useState(false);
  const [mergeError, setMergeError] = useState(null);

  const [selectedCanonicalId, setSelectedCanonicalId] = useState('');
  const [nameOption, setNameOption] = useState('suggested');
  const [customName, setCustomName] = useState('');
  const [idOption, setIdOption] = useState('canonical');
  const [customId, setCustomId] = useState('');

  useEffect(() => {
    if (!isOpen || !entityA || !duplicateId) return;

    setLoading(true);
    setComparison(null);
    setError(null);
    setMergeError(null);

    api.compareEntities({ entity_id_a: entityA.id, entity_id_b: duplicateId })
      .then((result) => {
        if (result.success) {
          setComparison(result.data);
          setSelectedCanonicalId(result.data.canonical_entity_id);
          setCustomName('');
          setNameOption('suggested');
          setIdOption('canonical');
          setCustomId('');
        } else {
          setError(result.error || 'Comparison failed.');
        }
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [isOpen, entityA, duplicateId]);

  const getSelectedName = () => {
    if (nameOption === 'suggested') return comparison?.suggested_name || '';
    if (nameOption === 'entity_a') return entityA?.name || '';
    if (nameOption === 'entity_b') return comparison?.entity_id_b ? duplicateId : '';
    if (nameOption === 'custom') return customName;
    return '';
  };

  const getSelectedNewId = () => {
    if (idOption === 'canonical') return null;
    if (idOption === 'custom') return customId || null;
    return null;
  };

  const handleConfirmMerge = async () => {
    if (!comparison) return;
    setMerging(true);
    setMergeError(null);

    const canonicalId = selectedCanonicalId;
    const mergeId = canonicalId === entityA.id ? duplicateId : entityA.id;
    const canonicalName = getSelectedName();
    const canonicalNewId = getSelectedNewId();

    try {
      const result = await api.mergeEntities({
        canonical_id: canonicalId,
        merge_ids: [mergeId],
        canonical_name: canonicalName || undefined,
        canonical_new_id: canonicalNewId || undefined,
      });
      if (result.success) {
        onMergeComplete(result.data?.canonical_id || canonicalId);
      } else {
        setMergeError(result.error || 'Merge failed.');
      }
    } catch (err) {
      setMergeError(err.message);
    }
    setMerging(false);
  };

  if (!isOpen) return null;

  const modalContent = (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Entity Comparison</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          {loading && (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#666' }}>
              <div style={{ marginBottom: '12px', fontSize: '1.1rem' }}>Analyzing entities...</div>
              <div style={{ fontSize: '0.9rem' }}>LLM is comparing properties, aliases, and relationships</div>
            </div>
          )}

          {error && (
            <div className="merge-box merge-error">
              <strong>Error:</strong> {error}
            </div>
          )}

          {comparison && (
            <>
              {/* Decision badge */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                <span
                  className="badge"
                  style={{
                    backgroundColor: comparison.decision === 'merge' ? '#2e7d32' : '#c0392b',
                    color: '#fff',
                    fontSize: '0.9rem',
                    padding: '5px 12px',
                  }}
                >
                  {comparison.decision === 'merge' ? 'Merge Recommended' : 'Do Not Merge'}
                </span>
                <span className="badge" style={{ fontSize: '0.85rem' }}>
                  {Math.round(comparison.confidence * 100)}% confidence
                </span>
              </div>

              {/* Checklist */}
              {comparison.checklist && (
                <ul className="checklist">
                  {Object.entries(CHECKLIST_LABELS).map(([key, label]) => {
                    const item = comparison.checklist[key];
                    if (!item) return null;
                    const isContradiction = key === 'description_contradiction';
                    const isPositive = isContradiction ? !item.result : item.result;
                    return (
                      <li key={key} className="checklist-item">
                        <span className={`checklist-icon ${isPositive ? 'checklist-pass' : 'checklist-fail'}`}>
                          {isPositive ? '✓' : '✗'}
                        </span>
                        <span className="checklist-label">{label}</span>
                        <span className="checklist-detail">{item.detail || '-'}</span>
                      </li>
                    );
                  })}
                </ul>
              )}

              {/* Reasoning */}
              <div style={{ margin: '12px 0', padding: '10px', background: '#f8f9fa', borderRadius: '4px', fontSize: '0.9rem', lineHeight: '1.5' }}>
                {comparison.reasoning}
              </div>

              {/* Merge options */}
              {comparison.decision === 'merge' && (
                <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border)' }}>
                  {/* Canonical ID selection */}
                  <div className="merge-option-group">
                    <label>Canonical Entity (giữ lại):</label>
                    <select
                      value={selectedCanonicalId}
                      onChange={(e) => setSelectedCanonicalId(e.target.value)}
                    >
                      <option value={entityA.id}>{entityA.name || entityA.id} ({entityA.id})</option>
                      <option value={duplicateId}>{duplicateId}</option>
                    </select>
                  </div>

                  {/* Name selection */}
                  <div className="merge-option-group">
                    <label>Name cho node sau merge:</label>
                    <select value={nameOption} onChange={(e) => setNameOption(e.target.value)}>
                      <option value="suggested">LLM suggest: {comparison.suggested_name}</option>
                      <option value="entity_a">Entity A: {entityA.name || entityA.id}</option>
                      <option value="entity_b">Entity B: {duplicateId}</option>
                      <option value="custom">Custom...</option>
                    </select>
                    {nameOption === 'custom' && (
                      <input
                        type="text"
                        value={customName}
                        onChange={(e) => setCustomName(e.target.value)}
                        placeholder="Nhập tên tùy chỉnh..."
                      />
                    )}
                  </div>

                  {/* ID selection */}
                  <div className="merge-option-group">
                    <label>ID cho node sau merge:</label>
                    <select value={idOption} onChange={(e) => setIdOption(e.target.value)}>
                      <option value="canonical">Giữ nguyên: {selectedCanonicalId}</option>
                      <option value="custom">Custom...</option>
                    </select>
                    {idOption === 'custom' && (
                      <input
                        type="text"
                        value={customId}
                        onChange={(e) => setCustomId(e.target.value)}
                        placeholder="Nhập ID tùy chỉnh (ví dụ: node_ten_moi)..."
                      />
                    )}
                  </div>

                  {mergeError && (
                    <div className="merge-box merge-error" style={{ marginTop: '10px' }}>
                      {mergeError}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {comparison && comparison.decision === 'merge' && (
          <div className="modal-footer">
            <button
              className="merge-button"
              style={{ backgroundColor: '#6b7280' }}
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              className="merge-button"
              style={{ backgroundColor: '#2e7d32' }}
              onClick={handleConfirmMerge}
              disabled={merging}
            >
              {merging ? 'Merging...' : 'Confirm Merge'}
            </button>
          </div>
        )}

        {comparison && comparison.decision !== 'merge' && (
          <div className="modal-footer">
            <button className="merge-button" onClick={onClose}>
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
