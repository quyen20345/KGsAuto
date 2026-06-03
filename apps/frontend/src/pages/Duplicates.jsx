import { useState, useEffect } from 'react';
import { useBreadcrumb } from '../context/BreadcrumbContext';
import { api } from '../services/api';

export default function Duplicates() {
  const { setBreadcrumbs } = useBreadcrumb();
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mergeState, setMergeState] = useState({});

  useEffect(() => {
    setBreadcrumbs([
      { label: 'Home', link: '/' },
      { label: 'Duplicate Review', link: null },
    ]);
    fetchCandidates();
  }, [setBreadcrumbs]);

  async function fetchCandidates() {
    setLoading(true);
    setError('');
    try {
      const result = await api.getDuplicateCandidates(20, 0.85);
      if (result.success) {
        setCandidates(result.data);
      } else {
        setError(result.error || 'Failed to fetch candidates');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch candidates');
    } finally {
      setLoading(false);
    }
  }

  async function handleMerge(pairIndex, canonicalId, mergeId) {
    setMergeState(prev => ({ ...prev, [pairIndex]: 'merging' }));
    try {
      const res = await api.mergeEntities({
        canonical_id: canonicalId,
        merge_ids: [mergeId]
      });
      if (res.success) {
        setMergeState(prev => ({ ...prev, [pairIndex]: 'success' }));
        // Remove from list after brief delay
        setTimeout(() => {
          setCandidates(prev => prev.filter((_, i) => i !== pairIndex));
          setMergeState(prev => {
            const newState = { ...prev };
            delete newState[pairIndex];
            return newState;
          });
        }, 1500);
      } else {
        setMergeState(prev => ({ ...prev, [pairIndex]: 'error' }));
        alert(`Merge failed: ${res.error}`);
      }
    } catch (err) {
      setMergeState(prev => ({ ...prev, [pairIndex]: 'error' }));
      alert(`Merge failed: ${err.message}`);
    }
  }

  function handleKeepSeparate(pairIndex) {
    // For now, just hide it from the list
    setCandidates(prev => prev.filter((_, i) => i !== pairIndex));
  }

  return (
    <main>
      <h1 className="entity-title">Duplicate Review</h1>
      <div className="entity-uri">Review potential duplicate entities identified by vector similarity.</div>

      {error && <div className="error-box" style={{ marginTop: '20px' }}>{error}</div>}

      <div style={{ marginTop: '20px', marginBottom: '20px' }}>
        <button className="btn-primary" onClick={fetchCandidates} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh Candidates'}
        </button>
      </div>

      {candidates.length === 0 && !loading && !error && (
        <div style={{ padding: '20px', background: 'var(--surface)', borderRadius: '8px', textAlign: 'center' }}>
          No duplicate candidates found.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {candidates.map((pair, index) => {
          const status = mergeState[index];
          if (status === 'success') {
            return (
              <div key={index} style={{ padding: '20px', background: 'var(--surface)', borderRadius: '8px', border: '1px solid var(--primary)' }}>
                <strong style={{ color: 'var(--primary)' }}>Merged Successfully!</strong>
              </div>
            );
          }

          return (
            <div key={index} style={{ padding: '20px', background: 'var(--surface)', borderRadius: '8px', border: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <span style={{ fontWeight: 'bold', color: 'var(--primary)', fontSize: '1.2em' }}>Similarity Score: {(pair.score * 100).toFixed(1)}%</span>
              </div>
              
              <div style={{ display: 'flex', gap: '20px' }}>
                {/* Entity A */}
                <div style={{ flex: 1, padding: '16px', background: 'var(--bg)', borderRadius: '6px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-light)', marginBottom: '4px' }}>Entity A (ID: {pair.entity1.id})</div>
                  <h3 style={{ margin: '0 0 10px 0', fontSize: '16px' }}>{pair.entity1.name}</h3>
                  <div style={{ fontSize: '13px', marginBottom: '10px' }}>
                    <strong>Labels:</strong> {pair.entity1.labels.join(', ')}
                  </div>
                  <div style={{ fontSize: '13px', marginBottom: '10px' }}>
                    <strong>Aliases:</strong> {pair.entity1.properties.aliases?.join(', ') || 'None'}
                  </div>
                </div>

                {/* Entity B */}
                <div style={{ flex: 1, padding: '16px', background: 'var(--bg)', borderRadius: '6px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-light)', marginBottom: '4px' }}>Entity B (ID: {pair.entity2.id})</div>
                  <h3 style={{ margin: '0 0 10px 0', fontSize: '16px' }}>{pair.entity2.name}</h3>
                  <div style={{ fontSize: '13px', marginBottom: '10px' }}>
                    <strong>Labels:</strong> {pair.entity2.labels.join(', ')}
                  </div>
                  <div style={{ fontSize: '13px', marginBottom: '10px' }}>
                    <strong>Aliases:</strong> {pair.entity2.properties.aliases?.join(', ') || 'None'}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', marginTop: '20px', justifyContent: 'center' }}>
                <button 
                  className="btn-primary" 
                  onClick={() => handleMerge(index, pair.entity1.id, pair.entity2.id)}
                  disabled={status === 'merging'}
                >
                  {status === 'merging' ? 'Merging...' : 'Merge B into A'}
                </button>
                <button 
                  className="btn-primary" 
                  onClick={() => handleMerge(index, pair.entity2.id, pair.entity1.id)}
                  disabled={status === 'merging'}
                >
                  {status === 'merging' ? 'Merging...' : 'Merge A into B'}
                </button>
                <button 
                  className="btn-secondary" 
                  onClick={() => handleKeepSeparate(index)}
                  disabled={status === 'merging'}
                >
                  Keep Separate
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}
