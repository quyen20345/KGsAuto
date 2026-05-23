import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import EntityLink from '../components/EntityLink';
import RelationshipTooltip from '../components/RelationshipTooltip';
import CompareModal from '../components/CompareModal';

export default function Entity() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [entityState, setEntityState] = useState({
    id: null,
    entity: null,
    error: false,
  });
  const [duplicates, setDuplicates] = useState([]);
  const [loadingDuplicates, setLoadingDuplicates] = useState(false);
  const [duplicateSearchQuery, setDuplicateSearchQuery] = useState('');
  const [duplicateSearchResults, setDuplicateSearchResults] = useState([]);
  const [duplicateSearchLoading, setDuplicateSearchLoading] = useState(false);
  const [duplicateSearchError, setDuplicateSearchError] = useState(null);
  const [compareTarget, setCompareTarget] = useState(null);

  const loading = entityState.id !== id && !entityState.error;
  const entity = entityState.id === id ? entityState.entity : null;

  useEffect(() => {
    api.getEntity(id)
      .then((data) => {
        setEntityState({ id, entity: data, error: false });
      })
      .catch(() => {
        setEntityState({ id, entity: null, error: true });
      });
  }, [id]);

  useEffect(() => {
    if (!entity?.name) return;

    setLoadingDuplicates(true);
    api.searchLexical(entity.name, 10, null)
      .then((results) => {
        const filtered = results.filter(r => r.id !== entity.id).slice(0, 5);
        setDuplicates(filtered);
        setLoadingDuplicates(false);
      })
      .catch(() => {
        setDuplicates([]);
        setLoadingDuplicates(false);
      });
  }, [entity]);

  const handleDuplicateSearch = (event) => {
    event.preventDefault();
    const query = duplicateSearchQuery.trim();
    if (!query) {
      setDuplicateSearchResults([]);
      setDuplicateSearchError(null);
      return;
    }

    setDuplicateSearchLoading(true);
    setDuplicateSearchError(null);
    api.searchLexical(query, 10, null)
      .then((results) => {
        const filtered = Array.isArray(results)
          ? results.filter(r => r.id !== entity.id)
          : [];
        setDuplicateSearchResults(filtered);
        setDuplicateSearchLoading(false);
      })
      .catch((error) => {
        setDuplicateSearchResults([]);
        setDuplicateSearchError(error?.message || 'Search failed.');
        setDuplicateSearchLoading(false);
      });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const handleMergeComplete = (canonicalId) => {
    setCompareTarget(null);
    navigate(`/entity/${encodeURIComponent(canonicalId)}`);
    if (canonicalId === entity.id) {
      window.location.reload();
    }
  };

  if (loading) return <main><div>Loading entity...</div></main>;
  if (!entity || entity.error) return <main><h2>Entity not found</h2></main>;

  const outGroups = entity.outgoing.reduce((acc, rel) => {
    acc[rel.type] = acc[rel.type] || [];
    acc[rel.type].push(rel);
    return acc;
  }, {});

  return (
    <main>
      <h1 className="entity-title">{entity.name || entity.id}</h1>

      <table>
        <thead>
          <tr><th>Predicate</th><th>Name</th></tr>
        </thead>
        <tbody>
          {Object.entries(outGroups).map(([type, rels]) => {
            return (
              <tr key={`out-${type}`}>
                <td className="predicate">
                  rel:{type}
                </td>
                <td className="object">
                  {rels.map((r, i) => {
                    const relDescription = r.properties?.description;
                    const relDescriptionText = Array.isArray(relDescription)
                      ? relDescription[0]
                      : relDescription;

                    return (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: i < rels.length - 1 ? '4px' : '0' }}>
                        <RelationshipTooltip
                          relationshipType={type}
                          description={relDescriptionText}
                        >
                          <span className="relationship-dot">•</span>
                        </RelationshipTooltip>
                        <EntityLink entityId={r.target_id}>
                          {r.target_name || r.target_id}
                        </EntityLink>
                      </div>
                    );
                  })}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="statements-header" style={{ marginTop: '40px' }}>Possible Duplicates</div>
      <form onSubmit={handleDuplicateSearch} style={{ marginTop: '12px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <input
            className="merge-input"
            type="text"
            value={duplicateSearchQuery}
            onChange={(event) => setDuplicateSearchQuery(event.target.value)}
            placeholder="Search entities to compare, e.g. UET"
            style={{ flex: 1 }}
          />
          <button className="merge-button" type="submit" disabled={duplicateSearchLoading}>
            Search
          </button>
        </div>
      </form>
      {duplicateSearchLoading && <div style={{ padding: '10px', color: '#666' }}>Searching entities...</div>}
      {duplicateSearchError && <div className="merge-box merge-error">{duplicateSearchError}</div>}
      {!duplicateSearchLoading && duplicateSearchResults.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {duplicateSearchResults.map((dup) => (
            <li key={dup.id} style={{ marginBottom: '16px', padding: '12px', border: '1px solid var(--border)', borderRadius: '4px', background: '#f8f9fa' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                <EntityLink entityId={dup.id}>
                  <strong>{dup.name || dup.id}</strong>
                </EntityLink>
                <span className="badge">{dup.labels?.[0] || 'Unknown'}</span>
                {typeof dup.score === 'number' && (
                  <span className="badge" style={{ backgroundColor: '#2f855a', color: '#fff' }}>
                    {Math.round(dup.score * 100)}% match
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <code className="entity-uri" style={{ fontSize: '0.85rem', flex: 1 }}>{dup.id}</code>
                <button
                  className="merge-button"
                  style={{ padding: '4px 10px', fontSize: '0.85rem' }}
                  onClick={() => copyToClipboard(dup.id)}
                >
                  Copy ID
                </button>
                <button
                  className="merge-button"
                  style={{ padding: '4px 10px', fontSize: '0.85rem', backgroundColor: '#2563eb' }}
                  onClick={() => setCompareTarget(dup.id)}
                >
                  Compare
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {loadingDuplicates && <div style={{ padding: '10px', color: '#666' }}>Searching for duplicates...</div>}
      {!loadingDuplicates && duplicates.length === 0 && (
        <div style={{ padding: '10px', color: '#666' }}>No potential duplicates found</div>
      )}
      {!loadingDuplicates && duplicates.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {duplicates.map((dup) => (
            <li key={dup.id} style={{ marginBottom: '16px', padding: '12px', border: '1px solid var(--border)', borderRadius: '4px', background: '#f8f9fa' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                <EntityLink entityId={dup.id}>
                  <strong>{dup.name || dup.id}</strong>
                </EntityLink>
                <span className="badge">{dup.labels?.[0] || 'Unknown'}</span>
                {typeof dup.score === 'number' && (
                  <span className="badge" style={{ backgroundColor: '#2f855a', color: '#fff' }}>
                    {Math.round(dup.score * 100)}% match
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <code className="entity-uri" style={{ fontSize: '0.85rem', flex: 1 }}>{dup.id}</code>
                <button
                  className="merge-button"
                  style={{ padding: '4px 10px', fontSize: '0.85rem' }}
                  onClick={() => copyToClipboard(dup.id)}
                >
                  Copy ID
                </button>
                <button
                  className="merge-button"
                  style={{ padding: '4px 10px', fontSize: '0.85rem', backgroundColor: '#2563eb' }}
                  onClick={() => setCompareTarget(dup.id)}
                >
                  Compare
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <CompareModal
        isOpen={!!compareTarget}
        onClose={() => setCompareTarget(null)}
        entityA={entity}
        duplicateId={compareTarget}
        onMergeComplete={handleMergeComplete}
      />
    </main>
  );
}
