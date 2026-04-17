import { useEffect, useState } from 'react';
import { api } from '../services/api';
import EntityLink from '../components/EntityLink';
import RelationshipTooltip from '../components/RelationshipTooltip';

export default function Home() {
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
    <main>
      <h2>Welcome to UETKB Knowledge Base</h2>
      <p>Search for entities in the top right, run custom Cypher queries, or start your exploration by clicking on any random triplet below.</p>

      <div className="statements-header">Random Triplets to Explore 🎲</div>

      {loading && <div style={{ padding: '20px', fontStyle: 'italic', color: '#666' }}>Fetching random knowledge...</div>}
      {error && <div style={{ color: 'red' }}>Error loading triplets: {error}</div>}

      {!loading && !error && (
        <table>
          <thead>
            <tr>
              <th style={{ width: '40%' }}>Subject</th>
              <th style={{ width: '20%' }}>Predicate (Relation)</th>
              <th style={{ width: '40%' }}>Object</th>
            </tr>
          </thead>
          <tbody>
            {triplets.map((t, i) => {
              const relationshipDescription = t.rel_properties?.description;
              const descriptionText = Array.isArray(relationshipDescription)
                ? relationshipDescription[0]
                : relationshipDescription;

              return (
                <tr key={i}>
                  <td>
                    <span className="badge">{t.source_label}</span><br />
                    <EntityLink entityId={t.source_id}>
                      <strong>{t.source_name}</strong>
                    </EntityLink>
                  </td>
                  <td className="predicate" style={{ verticalAlign: 'middle', textAlign: 'center', background: '#f8f9fa' }}>
                    <RelationshipTooltip
                      relationshipType={t.rel_type}
                      description={descriptionText}
                    >
                      {t.rel_type}
                    </RelationshipTooltip>
                  </td>
                  <td>
                    <span className="badge">{t.target_label}</span><br />
                    <EntityLink entityId={t.target_id}>
                      <strong>{t.target_name}</strong>
                    </EntityLink>
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