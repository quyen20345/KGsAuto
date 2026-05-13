import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { pipelineApi } from '../../services/api';

export default function RunHistory() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => { loadRuns(); }, []);

  async function loadRuns() {
    setLoading(true);
    try {
      setRuns(await pipelineApi.listRuns());
    } catch (e) {
      console.error('Failed to load runs:', e);
    }
    setLoading(false);
  }

  function statusColor(status) {
    if (status === 'completed') return '#4caf50';
    if (status === 'failed') return '#f44336';
    if (status === 'pending') return '#9e9e9e';
    return '#2196f3';
  }

  if (loading) return <div className="pipeline-loading">Loading...</div>;

  return (
    <div className="run-history">
      <h3>Pipeline Runs</h3>
      {runs.length === 0 ? (
        <p>No pipeline runs yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Run ID</th>
              <th>Mode</th>
              <th>Status</th>
              <th>Progress</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {runs.map(run => (
              <tr key={run.id} onClick={() => navigate(`/pipeline/runs/${run.id}`)} style={{ cursor: 'pointer' }}>
                <td>{run.id}</td>
                <td>{run.mode}</td>
                <td><span style={{ color: statusColor(run.status) }}>{run.status}</span></td>
                <td>{run.progress_pct}%</td>
                <td>{new Date(run.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
