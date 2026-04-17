import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import EntityLink from '../components/EntityLink';
import RelationshipTooltip from '../components/RelationshipTooltip';

export default function Entity() {
  const { id } = useParams();
  const [entityState, setEntityState] = useState({
    id: null,
    entity: null,
    error: false,
  });
  const [duplicates, setDuplicates] = useState([]);
  const [loadingDuplicates, setLoadingDuplicates] = useState(false);

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

  // Search for possible duplicates when entity loads
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

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
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
                    <EntityLink key={i} entityId={r.target_id}>
                      {r.target_name || r.target_id}
                    </EntityLink>
                  ))}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="statements-header" style={{ marginTop: '40px' }}>Possible Duplicates</div>
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
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
