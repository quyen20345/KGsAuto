import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';

export default function Search() {
  const { query } = useParams();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.search(query)
      .then(data => {
        setResults(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [query]);

  return (
    <main>
      <h3>Search results for: <i>{query}</i></h3>
      {loading ? (
        <div>Loading...</div>
      ) : results.length === 0 ? (
        <p>No results found.</p>
      ) : (
        <ul>
          {results.map(item => (
            <li key={item.id} style={{ marginBottom: '10px' }}>
              <Link className="internal-link" to={`/entity/${item.id}`}>{item.name || item.id}</Link>
              <span className="badge" style={{ marginLeft: '10px' }}>{item.labels[0]}</span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}