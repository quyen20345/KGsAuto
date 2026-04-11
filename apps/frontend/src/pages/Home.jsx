import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';

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
      <h2>Welcome to KGsAuto Knowledge Base</h2>
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
            {triplets.map((t, i) => (
              <tr key={i}>
                <td>
                  <span className="badge">{t.source_label}</span><br />
                  <Link className="internal-link" to={`/entity/${t.source_id}`}><strong>{t.source_name}</strong></Link>
                </td>
                <td className="predicate" style={{ verticalAlign: 'middle', textAlign: 'center', background: '#f8f9fa' }}>
                  {t.rel_type}
                </td>
                <td>
                  <span className="badge">{t.target_label}</span><br />
                  <Link className="internal-link" to={`/entity/${t.target_id}`}><strong>{t.target_name}</strong></Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}