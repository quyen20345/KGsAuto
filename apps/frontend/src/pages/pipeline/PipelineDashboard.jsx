import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { pipelineApi } from '../../services/api';
import RunTrigger from './RunTrigger';
import { useBreadcrumb } from '../../context/BreadcrumbContext';

export default function PipelineDashboard() {
  const { setBreadcrumbs } = useBreadcrumb();

  useEffect(() => {
    setBreadcrumbs([
      { label: 'Home', link: '/' },
      { label: 'Pipeline', link: '/pipeline' },
      { label: 'Dashboard', link: null }
    ]);
  }, [setBreadcrumbs]);

  const [stats, setStats] = useState({ raw: 0, extracted: 0, completedRuns: 0, runs: [] });
  const [showTrigger, setShowTrigger] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const loadStats = async () => {
    setLoading(true);
    setError('');
    try {
      const [raw, extracted, runs] = await Promise.all([
        pipelineApi.listRawFiles(),
        pipelineApi.listExtractedFiles(),
        pipelineApi.listRuns(),
      ]);
      setStats({
        raw: raw.length,
        extracted: extracted.length,
        completedRuns: runs.filter(r => r.status === 'completed').length,
        runs: runs.slice(0, 5),
      });
    } catch (e) {
      setError(e.message || 'Failed to load stats');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadStats();
  }, []);

  function statusColor(status) {
    if (status === 'completed') return '#4caf50';
    if (status === 'failed') return '#f44336';
    if (status === 'pending') return '#9e9e9e';
    return '#2196f3';
  }

  if (loading) return <div className="pipeline-loading">Loading...</div>;

  return (
    <div className="pipeline-dashboard">
      <div className="stats-cards">
        <div className="stat-card">
          <div className="stat-value">{stats.raw}</div>
          <div className="stat-label">Raw Markdowns</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.extracted}</div>
          <div className="stat-label">Extracted</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.completedRuns}</div>
          <div className="stat-label">Completed Runs</div>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="dashboard-actions">
        <button className="btn-primary" onClick={() => setShowTrigger(true)}>Run Pipeline</button>
        <button className="btn-secondary" onClick={() => navigate('/pipeline/files')}>Manage Files</button>
      </div>

      {stats.runs.length > 0 && (
        <div className="recent-runs">
          <h3>Recent Runs</h3>
          <table>
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Mode</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {stats.runs.map(run => (
                <tr key={run.id} onClick={() => navigate(`/pipeline/runs/${run.id}`)} style={{ cursor: 'pointer' }}>
                  <td>{run.id}</td>
                  <td>{run.mode}</td>
                  <td><span style={{ color: statusColor(run.status) }}>{run.status}</span></td>
                  <td>{new Date(run.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showTrigger && (
        <RunTrigger
          onClose={() => setShowTrigger(false)}
          onStarted={(runId) => {
            setShowTrigger(false);
            navigate(`/pipeline/runs/${runId}`);
          }}
        />
      )}
    </div>
  );
}
