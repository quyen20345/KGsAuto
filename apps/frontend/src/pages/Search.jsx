import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import EntityLink from '../components/EntityLink';

export default function Search() {
  const { query } = useParams();
  const navigate = useNavigate();
  const [inputValue, setInputValue] = useState(query || '');
  const [labelFilter, setLabelFilter] = useState('');
  const [availableLabels, setAvailableLabels] = useState([]);
  const [searchState, setSearchState] = useState({
    query: null,
    results: [],
    error: null,
    loading: false,
  });

  // Fetch available labels on mount
  useEffect(() => {
    api.getGraphMetadata()
      .then((data) => {
        if (data.labels) {
          // Filter out KgNode and sort alphabetically
          const filtered = data.labels
            .filter(label => label !== 'KgNode')
            .sort();
          setAvailableLabels(filtered);
        }
      })
      .catch((error) => {
        console.error('Failed to fetch labels:', error);
      });
  }, []);

  useEffect(() => {
    setInputValue(query || '');
  }, [query]);

  useEffect(() => {
    if (!query) {
      setSearchState({ query: null, results: [], error: null, loading: false });
      return;
    }

    let cancelled = false;
    setSearchState({ query, results: [], error: null, loading: true });

    api.searchLexical(query, 10, labelFilter || null)
      .then((data) => {
        if (cancelled) {
          return;
        }
        setSearchState({ query, results: Array.isArray(data) ? data : [], error: null, loading: false });
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        setSearchState({ query, results: [], error: error?.message || 'Search failed.', loading: false });
      });

    return () => {
      cancelled = true;
    };
  }, [query, labelFilter]);

  const loading = searchState.loading && searchState.query === query;
  const results = searchState.query === query ? searchState.results : [];

  const handleSubmit = (event) => {
    event.preventDefault();
    const nextQuery = inputValue.trim();
    if (!nextQuery) {
      navigate('/search');
      return;
    }
    navigate(`/search/${encodeURIComponent(nextQuery)}`);
  };

  return (
    <main>
      <h3>Search duplicate candidates</h3>
      <form onSubmit={handleSubmit} style={{ marginBottom: '20px' }}>
        <input
          className="merge-input"
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Nhập tên entity, alias, hoặc từ khóa"
        />
        <div style={{ fontSize: '13px', color: '#666', marginTop: '8px' }}>
          💡 Tip: You can search without diacritics (e.g., "dai hoc cong nghe").
          Use the filter below to narrow results by type.
        </div>
        <div style={{ marginTop: '10px', marginBottom: '10px' }}>
          <label style={{ marginRight: '10px', fontWeight: 'bold' }}>
            Filter by type:
            <select
              value={labelFilter}
              onChange={(e) => setLabelFilter(e.target.value)}
              style={{ marginLeft: '8px', padding: '6px 12px', fontSize: '14px' }}
            >
              <option value="">All types</option>
              {availableLabels.map((label) => (
                <option key={label} value={label}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="merge-actions" style={{ marginTop: '10px' }}>
          <button className="merge-button" type="submit">Search</button>
        </div>
      </form>

      {!query ? (
        <p>Nhập query rồi bấm Search.</p>
      ) : (
        <>
          <h4>Duplicate-candidate results for: <i>{query}</i></h4>
          {loading ? (
            <div>Loading...</div>
          ) : searchState.error ? (
            <div className="merge-box merge-error">{searchState.error}</div>
          ) : results.length === 0 ? (
            <p>No results found.</p>
          ) : (
            <ul>
              {results.map((item) => (
                <li key={item.id} style={{ marginBottom: '12px' }}>
                  <EntityLink entityId={item.id}>
                    {item.name || item.id}
                  </EntityLink>
                  <span className="badge" style={{ marginLeft: '10px' }}>{item.labels?.[0] || 'Unknown'}</span>
                  {typeof item.score === 'number' && (
                    <span className="badge" style={{ marginLeft: '10px', backgroundColor: '#2f855a', color: '#fff' }}>
                      {Math.round(item.score * 100)}% match
                    </span>
                  )}
                  <div className="entity-uri" style={{ marginTop: '4px' }}>{item.id}</div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </main>
  );
}
