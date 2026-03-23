import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';

export default function Entity() {
  const { id } = useParams();
  const [entity, setEntity] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getEntity(id).then(data => {
      setEntity(data);
      setLoading(false);
    });
  }, [id]);

  if (loading) return <main><div>Loading entity...</div></main>;
  if (!entity || entity.error) return <main><h2>Entity not found</h2></main>;

  // Gom nhóm properties
  const properties = Object.entries(entity.properties).filter(([key]) => key !== 'id' && key !== 'name');
  
  // Gom nhóm quan hệ Outgoing
  const outGroups = entity.outgoing.reduce((acc, rel) => {
    acc[rel.type] = acc[rel.type] || [];
    acc[rel.type].push(rel);
    return acc;
  }, {});

  // Gom nhóm quan hệ Incoming
  const inGroups = entity.incoming.reduce((acc, rel) => {
    acc[rel.type] = acc[rel.type] || [];
    acc[rel.type].push(rel);
    return acc;
  }, {});

  return (
    <main>
      <h1 className="entity-title">{entity.name || entity.id}</h1>
      <div className="entity-uri">URI: kg://entity/{entity.id}</div>
      <div>
        {entity.labels.map(l => <span key={l} className="badge">{l}</span>)}
      </div>
      
      <div className="statements-header">Statements</div>
      <table>
        <thead>
          <tr><th>Predicate</th><th>Object</th></tr>
        </thead>
        <tbody>
          {/* Properties */}
          {properties.map(([key, val]) => (
            <tr key={`prop-${key}`}>
              <td className="predicate">prop:{key}</td>
              <td className="object">
                {Array.isArray(val) ? val.map((v, i) => <div key={i}>{v}</div>) : val}
              </td>
            </tr>
          ))}

          {/* Outgoing */}
          {Object.entries(outGroups).map(([type, rels]) => (
            <tr key={`out-${type}`}>
              <td className="predicate">rel:{type}</td>
              <td className="object">
                {rels.map((r, i) => (
                  <Link key={i} className="internal-link" to={`/entity/${r.target_id}`}>
                    {r.target_name || r.target_id}
                  </Link>
                ))}
              </td>
            </tr>
          ))}

          {/* Incoming */}
          {Object.entries(inGroups).map(([type, rels]) => (
            <tr key={`in-${type}`}>
              <td className="predicate">rel:is_{type}_of</td>
              <td className="object">
                {rels.map((r, i) => (
                  <Link key={i} className="internal-link" to={`/entity/${r.target_id}`}>
                    {r.target_name || r.target_id}
                  </Link>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}