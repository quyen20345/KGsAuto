import { useState } from 'react';
import { api } from '../services/api';

export default function Query() {
  const [cypher, setCypher] = useState('MATCH (n) RETURN n LIMIT 5');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const executeCypher = async () => {
    setLoading(true);
    setResult("Running...");
    try {
      const data = await api.queryCypher(cypher);
      setResult(JSON.stringify(data.data, null, 2));
    } catch (e) {
      setResult("Error execution");
    }
    setLoading(false);
  };

  return (
    <main>
      <h2>Run Cypher Query</h2>
      <div id="query-box">
        <textarea 
          value={cypher} 
          onChange={(e) => setCypher(e.target.value)}
        />
        <br />
        <button 
          onClick={executeCypher} 
          disabled={loading}
          style={{ padding: '10px 20px', background: 'var(--primary)', color: 'white', border: 'none', cursor: 'pointer', opacity: loading ? 0.7 : 1 }}
        >
          {loading ? 'Executing...' : 'Execute Query'}
        </button>
      </div>
      <div className="statements-header" style={{ marginTop: '20px' }}>Result</div>
      <div id="query-result">
        {result || 'Awaiting query...'}
      </div>
    </main>
  );
}