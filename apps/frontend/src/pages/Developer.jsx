import { useEffect, useState } from 'react';
import { api, pipelineApi } from '../services/api';
import { useBreadcrumb } from '../context/BreadcrumbContext';

export default function Developer() {
  const { setBreadcrumbs } = useBreadcrumb();
  
  useEffect(() => {
    setBreadcrumbs([
      { label: 'Home', link: '/' },
      { label: 'Developer Tools', link: null }
    ]);
  }, [setBreadcrumbs]);

  // States for Quick Links Dashboard
  const [selectedService, setSelectedService] = useState(null);
  const [actionResult, setActionResult] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [customCypher, setCustomCypher] = useState('MATCH (n) RETURN count(n) AS node_count');
  const [nodeLimit, setNodeLimit] = useState(15);
  const [neighborTarget, setNeighborTarget] = useState('');
  const [neighborDepth, setNeighborDepth] = useState(2);

  const handleServiceClick = (service, e) => {
    e.preventDefault();
    if (selectedService === service) {
      setSelectedService(null);
      setActionResult(null);
      setActionError(null);
    } else {
      setSelectedService(service);
      setActionResult(null);
      setActionError(null);
    }
  };

  const runNeo4jAllGraph = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await api.runCypher(`MATCH (n) RETURN coalesce(n.name, n.id, elementId(n)) AS name, labels(n)[0] AS label, elementId(n) AS id LIMIT ${nodeLimit}`);
      if (res.success) {
        setActionResult({
          type: 'neo4j_300_nodes',
          title: `Graph Nodes (Limit ${nodeLimit})`,
          data: res.data
        });
      } else {
        throw new Error(res.error || 'Failed to fetch graph nodes');
      }
    } catch (err) {
      setActionError(err.message || 'Failed to execute query');
    } finally {
      setActionLoading(false);
    }
  };

  const getNeo4jStats = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await api.getGraphMetadata();
      setActionResult({
        type: 'neo4j_stats',
        title: 'Database Schema Metadata',
        data: res
      });
    } catch (err) {
      setActionError(err.message || 'Failed to fetch metadata');
    } finally {
      setActionLoading(false);
    }
  };

  const testQdrantConnection = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await fetch('http://localhost:6333/', { method: 'GET' });
      if (res.ok) {
        const data = await res.json();
        setActionResult({
          type: 'qdrant_conn',
          title: 'Qdrant Vector Database Status',
          status: 'UP',
          data: data
        });
      } else {
        throw new Error(`Connection returned status ${res.status}`);
      }
    } catch (err) {
      setActionError('Qdrant unreachable: ' + err.message + '\n\nTry running "docker compose up -d" to start Qdrant.');
    } finally {
      setActionLoading(false);
    }
  };

  const getQdrantCollections = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await fetch('http://localhost:6333/collections', { method: 'GET' });
      if (res.ok) {
        const data = await res.json();
        setActionResult({
          type: 'qdrant_collections',
          title: 'Active Qdrant Collections',
          data: data
        });
      } else {
        throw new Error(`HTTP Error ${res.status}`);
      }
    } catch (err) {
      setActionError('Failed to fetch Qdrant collections. Error: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const checkGraphApiStatus = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      await api.getRandomTriplets(1);
      setActionResult({
        type: 'graph_api_status',
        title: 'Graph API Health Status',
        status: 'UP',
        message: 'Graph API is running healthy and connected to Neo4j database.'
      });
    } catch (err) {
      setActionError('Graph API unreachable: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const runCustomCypher = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await api.runCypher(customCypher);
      if (res.success) {
        setActionResult({
          type: 'custom_cypher',
          title: 'Cypher Query Execution Result',
          data: res.data
        });
      } else {
        throw new Error(res.error || 'Failed to execute custom Cypher query');
      }
    } catch (err) {
      setActionError(err.message || 'Failed to execute custom Cypher query');
    } finally {
      setActionLoading(false);
    }
  };

  const checkPipelineApiHealth = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await fetch('http://localhost:8001/api/health');
      if (res.ok) {
        const data = await res.json();
        setActionResult({
          type: 'pipeline_health',
          title: 'Pipeline API Health Status',
          status: 'UP',
          data: data
        });
      } else {
        throw new Error(`Status ${res.status}`);
      }
    } catch (err) {
      setActionError('Pipeline API unreachable: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const getRecentRuns = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await pipelineApi.listRuns();
      setActionResult({
        type: 'pipeline_runs',
        title: 'Recent Pipeline Processing Runs',
        data: res
      });
    } catch (err) {
      setActionError('Failed to fetch recent pipeline runs: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const checkChatApiHealth = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await fetch('http://localhost:8002/health');
      if (res.ok) {
        const data = await res.json();
        setActionResult({
          type: 'chat_health',
          title: 'Chat API Health Status',
          status: 'UP',
          data: data
        });
      } else {
        throw new Error(`Status ${res.status}`);
      }
    } catch (err) {
      setActionError('Chat API unreachable: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const getChatModes = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await api.getChatModes();
      setActionResult({
        type: 'chat_modes',
        title: 'Supported Chat RAG Modes',
        data: res
      });
    } catch (err) {
      setActionError('Failed to retrieve chat modes: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <main>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ margin: '0 0 8px 0', fontSize: '1.8rem', fontWeight: '700', color: 'var(--text)' }}>🛠️ Developer Services & Settings</h2>
        <p style={{ margin: 0, color: 'var(--text-light)', fontSize: '0.95rem' }}>
          Explore microservices, Vector databases, run custom Cypher graph queries, or check API connection metrics.
        </p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px', background: 'var(--bg-surface)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border)', marginBottom: '20px' }}>
        <span style={{ fontWeight: '600', color: 'var(--text-light)', fontSize: '0.9rem', marginRight: '5px' }}>🛠️ Developer Services:</span>
        <button onClick={(e) => handleServiceClick('neo4j', e)} style={{ padding: '6px 12px', fontSize: '0.85rem', borderRadius: '4px', border: '1px solid var(--border)', background: selectedService === 'neo4j' ? 'var(--primary)' : 'var(--bg)', color: selectedService === 'neo4j' ? '#fff' : 'var(--text)', cursor: 'pointer', transition: 'var(--transition)' }}>Neo4j</button>
        <button onClick={(e) => handleServiceClick('qdrant', e)} style={{ padding: '6px 12px', fontSize: '0.85rem', borderRadius: '4px', border: '1px solid var(--border)', background: selectedService === 'qdrant' ? 'var(--primary)' : 'var(--bg)', color: selectedService === 'qdrant' ? '#fff' : 'var(--text)', cursor: 'pointer', transition: 'var(--transition)' }}>Qdrant</button>
        <button onClick={(e) => handleServiceClick('graph_api', e)} style={{ padding: '6px 12px', fontSize: '0.85rem', borderRadius: '4px', border: '1px solid var(--border)', background: selectedService === 'graph_api' ? 'var(--primary)' : 'var(--bg)', color: selectedService === 'graph_api' ? '#fff' : 'var(--text)', cursor: 'pointer', transition: 'var(--transition)' }}>Graph API</button>
        <button onClick={(e) => handleServiceClick('pipeline_api', e)} style={{ padding: '6px 12px', fontSize: '0.85rem', borderRadius: '4px', border: '1px solid var(--border)', background: selectedService === 'pipeline_api' ? 'var(--primary)' : 'var(--bg)', color: selectedService === 'pipeline_api' ? '#fff' : 'var(--text)', cursor: 'pointer', transition: 'var(--transition)' }}>Pipeline API</button>
        <button onClick={(e) => handleServiceClick('chat_api', e)} style={{ padding: '6px 12px', fontSize: '0.85rem', borderRadius: '4px', border: '1px solid var(--border)', background: selectedService === 'chat_api' ? 'var(--primary)' : 'var(--bg)', color: selectedService === 'chat_api' ? '#fff' : 'var(--text)', cursor: 'pointer', transition: 'var(--transition)' }}>Chat API</button>
      </div>

      {/* Dynamic Service Options Panel */}
      {selectedService && (
        <div className="service-options-panel">
          <div className="options-header">
            <span className="options-title">
              {selectedService === 'neo4j' && '📊 Neo4j Graph Database Actions'}
              {selectedService === 'qdrant' && '🚀 Qdrant Vector Database Actions'}
              {selectedService === 'graph_api' && '🔌 Graph API Actions'}
              {selectedService === 'pipeline_api' && '⚙️ Pipeline API Actions'}
              {selectedService === 'chat_api' && '💬 Chat API Actions'}
            </span>
            <button className="options-close" onClick={() => { setSelectedService(null); setActionResult(null); setActionError(null); }}>&times;</button>
          </div>

          {selectedService === 'neo4j' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              {/* Dedicated Card for Neighborhood Graph around Node (Ego-Network Explorer) */}
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '8px', padding: '20px', maxWidth: '500px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
                <div style={{ fontWeight: '600', fontSize: '1rem', color: 'var(--primary)', marginBottom: '8px' }}>🎯 Đồ Thị Quanh Tâm (Node Ego-Network Explorer)</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-light)', marginBottom: '16px', lineHeight: '1.4' }}>
                  Nhập tên hoặc ID thực thể tâm để vẽ mạng lưới quan hệ vệ tinh xung quanh thực thể đó trực quan bằng đồ thị trong Neo4j Browser.
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {/* Input: Target Entity */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '0.8rem', fontWeight: '600', color: '#555' }}>Thực thể tâm:</label>
                    <input 
                      type="text" 
                      value={neighborTarget} 
                      onChange={(e) => setNeighborTarget(e.target.value)}
                      placeholder="Nhập tên thực thể tâm (ví dụ: Đại học Công nghệ)..."
                      style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: '4px', fontSize: '0.85rem', boxSizing: 'border-box' }}
                    />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    {/* Select: Jump Steps */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label style={{ fontSize: '0.8rem', fontWeight: '600', color: '#555' }}>Số bước nhảy (1..3):</label>
                      <select 
                        value={neighborDepth} 
                        onChange={(e) => setNeighborDepth(parseInt(e.target.value))}
                        style={{ padding: '8px 10px', border: '1px solid var(--border)', borderRadius: '4px', fontSize: '0.85rem', width: '100%' }}
                      >
                        <option value="1">1 bước nhảy</option>
                        <option value="2">2 bước nhảy</option>
                        <option value="3">3 bước nhảy</option>
                      </select>
                    </div>

                    {/* Input: Node Limit */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label style={{ fontSize: '0.8rem', fontWeight: '600', color: '#555' }}>Giới hạn node:</label>
                      <input 
                        type="number" 
                        value={nodeLimit} 
                        onChange={(e) => setNodeLimit(Math.max(1, parseInt(e.target.value) || 15))}
                        placeholder="15"
                        style={{ padding: '8px 10px', border: '1px solid var(--border)', borderRadius: '4px', fontSize: '0.85rem', width: '100%', boxSizing: 'border-box' }}
                      />
                    </div>
                  </div>

                  {/* Trigger Anchor Link to Neo4j Desktop Browser */}
                  <a 
                    href={`http://localhost:7474/browser/?cmd=edit&arg=${encodeURIComponent(`MATCH (target) WHERE target.name CONTAINS '${neighborTarget}' OR target.id = '${neighborTarget}' MATCH (target)-[*1..${neighborDepth}]-(neighbor) RETURN DISTINCT neighbor, target LIMIT ${nodeLimit}`)}`} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ 
                      textDecoration: 'none', 
                      textAlign: 'center', 
                      fontSize: '0.85rem', 
                      padding: '10px 14px', 
                      borderRadius: '6px', 
                      background: 'var(--primary)', 
                      color: 'white', 
                      fontWeight: '600', 
                      cursor: neighborTarget.trim() ? 'pointer' : 'not-allowed',
                      opacity: neighborTarget.trim() ? 1 : 0.6,
                      pointerEvents: neighborTarget.trim() ? 'auto' : 'none',
                      transition: 'var(--transition)'
                    }}
                  >
                    Vẽ đồ thị trong Neo4j 🌐
                  </a>
                </div>
              </div>

              <div style={{ borderTop: '1px solid #eee', paddingSelf: '12px 0', marginTop: '10px' }} />

              <div className="action-row">
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <label style={{ fontSize: '0.9rem', color: '#555' }}>Limit nodes:</label>
                  <input 
                    type="number" 
                    value={nodeLimit} 
                    onChange={(e) => setNodeLimit(parseInt(e.target.value) || 10)} 
                    style={{ width: '60px', padding: '4px 8px', border: '1px solid #ccc', borderRadius: '4px' }}
                  />
                  <button className="merge-button" onClick={runNeo4jAllGraph}>List Graph Nodes</button>
                  <button className="merge-button-secondary" onClick={getNeo4jStats}>Show Schema Metadata</button>
                </div>
              </div>
            </div>
          ) : null}

          {selectedService === 'qdrant' ? (
            <div className="action-row">
              <button className="merge-button" onClick={testQdrantConnection}>Check Qdrant Server Status</button>
              <button className="merge-button-secondary" onClick={getQdrantCollections}>List Vector Collections</button>
            </div>
          ) : null}

          {selectedService === 'graph_api' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="action-row">
                <button className="merge-button" onClick={checkGraphApiStatus}>Verify Service Connection</button>
              </div>
              <div style={{ borderTop: '1px solid #eee', paddingSelf: '12px 0' }} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontWeight: '600', fontSize: '0.9rem', color: '#555' }}>Run Cypher Query:</label>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <input 
                    type="text" 
                    className="merge-input" 
                    value={customCypher} 
                    onChange={(e) => setCustomCypher(e.target.value)} 
                    style={{ flex: 1 }}
                  />
                  <button className="merge-button" onClick={runCustomCypher}>Execute</button>
                </div>
              </div>
            </div>
          ) : null}

          {selectedService === 'pipeline_api' ? (
            <div className="action-row">
              <button className="merge-button" onClick={checkPipelineApiHealth}>Check Pipeline Health Status</button>
              <button className="merge-button-secondary" onClick={getRecentRuns}>List Execution History</button>
            </div>
          ) : null}

          {selectedService === 'chat_api' ? (
            <div className="action-row">
              <button className="merge-button" onClick={checkChatApiHealth}>Verify Chat API Status</button>
              <button className="merge-button-secondary" onClick={getChatModes}>Get Chat Modes</button>
            </div>
          ) : null}

          {/* Action Loading & Error Notifications */}
          {actionLoading && <div style={{ marginTop: '15px', color: '#666', fontStyle: 'italic' }}>Running service request...</div>}
          {actionError && <div className="merge-box merge-error" style={{ marginTop: '15px' }}>{actionError}</div>}

          {/* Action Success Container */}
          {!actionLoading && actionResult && (
            <div className="action-result-box" style={{ marginTop: '15px', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '6px', padding: '15px' }}>
              <div style={{ fontWeight: '600', borderBottom: '1px solid var(--border)', paddingBottom: '6px', marginBottom: '10px' }}>
                {actionResult.title}
              </div>

              {actionResult.status && (
                <div style={{ marginBottom: '10px' }}>
                  Status Indicator: <span className="status-badge status-completed" style={{ background: '#d1fae5', color: '#065f46' }}>{actionResult.status}</span>
                </div>
              )}

              {actionResult.message && <p style={{ margin: '0 0 10px 0', fontSize: '0.9rem' }}>{actionResult.message}</p>}

              {/* Neo4j Node List Special Renderer */}
              {actionResult.data && actionResult.type === 'neo4j_300_nodes' && (
                <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  <table style={{ fontSize: '0.85rem' }}>
                    <thead>
                      <tr>
                        <th>Node Name</th>
                        <th>Type Label</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {actionResult.data.length === 0 ? (
                        <tr><td colSpan="3">No nodes returned from limit.</td></tr>
                      ) : (
                        actionResult.data.map((node) => (
                          <tr key={node.id}>
                            <td><strong>{node.name}</strong></td>
                            <td><span className="badge">{node.label}</span></td>
                            <td>
                              <a href={`/entity/${encodeURIComponent(node.id)}`} style={{ textDecoration: 'none', color: 'var(--primary)', fontWeight: '600' }}>
                                View Details
                              </a>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Neo4j Stats Metadata Special Renderer */}
              {actionResult.data && actionResult.type === 'neo4j_stats' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', fontSize: '0.85rem' }}>
                  <div>
                    <div style={{ fontWeight: '600', marginBottom: '5px' }}>Node Labels</div>
                    <ul>
                      {actionResult.data.labels?.map((label, idx) => <li key={idx}><code>{label}</code></li>)}
                    </ul>
                  </div>
                  <div>
                    <div style={{ fontWeight: '600', marginBottom: '5px' }}>Relationship Types</div>
                    <ul>
                      {actionResult.data.relationshipTypes?.map((rel, idx) => <li key={idx}><code>{rel}</code></li>)}
                    </ul>
                  </div>
                </div>
              )}

              {/* Qdrant Collections Special Renderer */}
              {actionResult.data && actionResult.type === 'qdrant_collections' && (
                <div>
                  <div style={{ fontWeight: '600', marginBottom: '5px', fontSize: '0.85rem' }}>Collections inside Vector Database:</div>
                  <ul style={{ fontSize: '0.85rem' }}>
                    {actionResult.data.result?.collections?.length === 0 ? (
                      <li>No vector collections defined yet.</li>
                    ) : (
                      actionResult.data.result?.collections?.map((col, idx) => (
                        <li key={idx}><code>{col.name}</code></li>
                      ))
                    )}
                  </ul>
                </div>
              )}

              {/* Pipeline Runs Special Renderer */}
              {actionResult.data && actionResult.type === 'pipeline_runs' && (
                <table style={{ fontSize: '0.85rem' }}>
                  <thead>
                    <tr>
                      <th>Run ID</th>
                      <th>Status</th>
                      <th>Mode</th>
                    </tr>
                  </thead>
                  <tbody>
                    {actionResult.data.length === 0 ? (
                      <tr>
                        <td colSpan="3">No pipeline runs loaded yet.</td>
                      </tr>
                    ) : (
                      actionResult.data.map((run, idx) => (
                        <tr key={idx}>
                          <td><code>{run.id}</code></td>
                          <td><span className={`status-badge status-${run.status}`}>{run.status}</span></td>
                          <td>{run.config?.mode || 'N/A'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              )}

              {actionResult.data && actionResult.type === 'chat_modes' && (
                <ul>
                  {actionResult.data.modes?.map((mode, idx) => (
                    <li key={idx} style={{ marginBottom: '8px', fontSize: '0.85rem' }}>
                      <strong><code>{mode.id}</code></strong>: {mode.description}
                    </li>
                  ))}
                </ul>
              )}

              {/* General Data Fallback */}
              {actionResult.data && 
               actionResult.type !== 'neo4j_300_nodes' && 
               actionResult.type !== 'neo4j_stats' && 
               actionResult.type !== 'qdrant_collections' &&
               actionResult.type !== 'pipeline_runs' &&
               actionResult.type !== 'chat_modes' && (
                <pre style={{ fontSize: '0.8rem', background: 'var(--bg-surface)', color: 'var(--text)', padding: '10px', borderRadius: '4px', overflowX: 'auto', border: '1px solid var(--border)' }}>{JSON.stringify(actionResult.data, null, 2)}</pre>
              )}
            </div>
          )}
        </div>
      )}
    </main>
  );
}
