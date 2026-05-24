import { useEffect, useState } from 'react';
import { api } from '../services/api';
import EntityLink from '../components/EntityLink';
import RelationshipTooltip from '../components/RelationshipTooltip';
import { useBreadcrumb } from '../context/BreadcrumbContext';

export default function Home() {
  const { setBreadcrumbs } = useBreadcrumb();
  
  useEffect(() => {
    setBreadcrumbs([
      { label: 'Home', link: '/' },
      { label: 'Random Triplets', link: null }
    ]);
  }, [setBreadcrumbs]);

  const [triplets, setTriplets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getRandomTriplets()
      .then(data => {
        if (data.error) throw new Error(data.error);
        setTriplets(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <main style={{ maxWidth: '900px', margin: '0 auto', padding: '30px 20px' }}>

      {loading && (
        <div style={{ padding: '40px 20px', fontStyle: 'italic', color: '#666', textAlign: 'center' }}>
          Fetching random knowledge...
        </div>
      )}
      
      {error && (
        <div style={{ color: 'red', textAlign: 'center', padding: '20px' }}>
          Error loading triplets: {error}
        </div>
      )}

      {!loading && !error && (
        <table>
          <tbody>
            {triplets.map((t, i) => {
              const relationshipDescription = t.rel_properties?.description;
              const descriptionText = Array.isArray(relationshipDescription)
                ? relationshipDescription[0]
                : relationshipDescription;

              return (
                <tr key={i}>
                  <td style={{ width: '40%' }}>
                    <span className="badge" style={{ fontSize: '0.7rem', padding: '2px 6px', borderRadius: '4px' }}>
                      {t.source_label}
                    </span>
                    <div style={{ marginTop: '4px' }}>
                      <EntityLink entityId={t.source_id}>
                        <strong>{t.source_name}</strong>
                      </EntityLink>
                    </div>
                  </td>
                  <td className="predicate" style={{ width: '20%', verticalAlign: 'middle', textAlign: 'center', background: 'var(--bg)', padding: '12px 8px' }}>
                    <RelationshipTooltip
                      relationshipType={t.rel_type}
                      description={descriptionText}
                    >
                      <span style={{ fontWeight: '600', fontSize: '0.85rem' }}>{t.rel_type}</span>
                    </RelationshipTooltip>
                  </td>
                  <td style={{ width: '40%' }}>
                    <span className="badge" style={{ fontSize: '0.7rem', padding: '2px 6px', borderRadius: '4px' }}>
                      {t.target_label}
                    </span>
                    <div style={{ marginTop: '4px' }}>
                      <EntityLink entityId={t.target_id}>
                        <strong>{t.target_name}</strong>
                      </EntityLink>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </main>
  );
}