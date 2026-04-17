import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';

const STORAGE_KEY = 'lastCypherQuery';

const QUERY_TEMPLATES = {
  merge: {
    label: 'Merge Nodes',
    query: `MATCH (a {id: 'node_truong_dai_hoc_cong_nghe_dai_hoc_quoc_gia_ha_noi'}),
      (b {id: 'node_truong_dhcn'})
CALL apoc.refactor.mergeNodes([a, b], {
  properties: 'combine',
  mergeRels: true
})
YIELD node
SET node.id = 'node_truong_dai_hoc_cong_nghe_dai_hoc_quoc_gia_ha_noi',
    node.name = 'Trường Đại học Công nghệ, Đại học Quốc gia Hà Nội'
RETURN node`
  },
  search: {
    label: 'Search Nodes',
    query: `MATCH (n)
WHERE n.name CONTAINS 'keyword'
RETURN n
LIMIT 10`
  },
  delete: {
    label: 'Delete Node',
    query: `MATCH (n {id: 'node_id_here'})
DETACH DELETE n`
  },
  relationships: {
    label: 'View Relationships',
    query: `MATCH (n {id: 'node_id_here'})-[r]->(m)
RETURN n, r, m
LIMIT 20`
  }
};

export default function Merge() {
  const [searchParams] = useSearchParams();
  const [cypherQuery, setCypherQuery] = useState('');
  const [cypherState, setCypherState] = useState({ submitting: false, result: null, error: null });
  const [activeTab, setActiveTab] = useState('merge');

  // Load query on mount: priority = URL params > localStorage > default template
  useEffect(() => {
    const queryFromUrl = searchParams.get('query');
    if (queryFromUrl) {
      setCypherQuery(decodeURIComponent(queryFromUrl));
    } else {
      const savedQuery = localStorage.getItem(STORAGE_KEY);
      if (savedQuery) {
        setCypherQuery(savedQuery);
      } else {
        setCypherQuery(QUERY_TEMPLATES.merge.query);
      }
    }
  }, [searchParams]);

  // Save query to localStorage whenever it changes
  useEffect(() => {
    if (cypherQuery.trim()) {
      localStorage.setItem(STORAGE_KEY, cypherQuery);
    }
  }, [cypherQuery]);

  const handleTabClick = (tabKey) => {
    setActiveTab(tabKey);
    setCypherQuery(QUERY_TEMPLATES[tabKey].query);
  };

  const handleRunCypher = async () => {
    if (!cypherQuery.trim()) {
      setCypherState({ submitting: false, result: null, error: 'Please enter a Cypher query.' });
      return;
    }

    setCypherState({ submitting: true, result: null, error: null });

    try {
      const response = await api.runCypher(cypherQuery);

      if (!response.success) {
        setCypherState({ submitting: false, result: null, error: response.error || 'Query failed.' });
        return;
      }

      setCypherState({ submitting: false, result: response.data, error: null });
    } catch (error) {
      setCypherState({ submitting: false, result: null, error: error.message || 'Query failed.' });
    }
  };

  const renderCypherResult = () => {
    if (cypherState.error) {
      return <div className="merge-box merge-error">{cypherState.error}</div>;
    }

    if (!cypherState.result) {
      return null;
    }

    return (
      <div className="merge-box merge-success">
        <div><strong>Query executed successfully</strong></div>
        <div style={{ marginTop: '10px' }}>Results ({cypherState.result.length} records):</div>
        <pre style={{ marginTop: '10px', padding: '10px', background: '#f5f5f5', borderRadius: '4px', overflow: 'auto', maxHeight: '400px' }}>
          {JSON.stringify(cypherState.result, null, 2)}
        </pre>
      </div>
    );
  };

  return (
    <main>
      <h1 className="entity-title">Run Neo4j Cypher Query</h1>
      <div className="entity-uri">Select a template or write your own Cypher command.</div>

      <div className="merge-form">
        {/* Query Templates Tabs */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', borderBottom: '2px solid var(--border)' }}>
          {Object.entries(QUERY_TEMPLATES).map(([key, template]) => (
            <button
              key={key}
              onClick={() => handleTabClick(key)}
              style={{
                padding: '8px 16px',
                background: activeTab === key ? 'var(--primary)' : 'transparent',
                color: activeTab === key ? 'white' : 'var(--text)',
                border: 'none',
                borderBottom: activeTab === key ? '2px solid var(--primary)' : '2px solid transparent',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: activeTab === key ? 'bold' : 'normal',
                marginBottom: '-2px',
              }}
            >
              {template.label}
            </button>
          ))}
        </div>

        <textarea
          className="merge-textarea"
          value={cypherQuery}
          onChange={(e) => setCypherQuery(e.target.value)}
          placeholder="Enter your Cypher query here..."
          rows={12}
          style={{ fontFamily: 'monospace', fontSize: '13px' }}
        />

        <div className="merge-actions">
          <button className="merge-button" onClick={handleRunCypher} disabled={cypherState.submitting}>
            {cypherState.submitting ? 'Running...' : 'Run Query'}
          </button>
        </div>

        {renderCypherResult()}
      </div>
    </main>
  );
}
