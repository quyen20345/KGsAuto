import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { pipelineApi } from '../../services/api';

const STEPS = ['extraction', 'entity_resolution', 'neo4j_import'];
const STEP_LABELS = { extraction: 'Extract', entity_resolution: 'Entity Resolution', neo4j_import: 'Import' };

export default function RunDetail() {
  const { runId } = useParams();
  const [run, setRun] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const logEndRef = useRef(null);
  const esRef = useRef(null);

  useEffect(() => {
    loadRun();
    return () => { if (esRef.current) esRef.current.close(); };
  }, [runId]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  async function loadRun() {
    setLoading(true);
    try {
      const data = await pipelineApi.getRun(runId);
      setRun(data.run);
      setLogs(data.logs || []);

      if (data.run.status !== 'completed' && data.run.status !== 'failed') {
        startSSE();
      }
    } catch (e) {
      console.error('Failed to load run:', e);
    }
    setLoading(false);
  }

  function startSSE() {
    if (esRef.current) esRef.current.close();
    esRef.current = pipelineApi.streamRunEvents(runId, (event) => {
      if (event.type === 'log') {
        setLogs(prev => [...prev, { timestamp: new Date().toISOString(), level: 'info', step: event.step, message: event.message }]);
      } else if (event.type === 'status') {
        setRun(prev => prev ? { ...prev, status: event.status, progress_pct: event.progress ?? prev.progress_pct } : prev);
        if (event.status === 'completed' || event.status === 'failed') {
          if (esRef.current) esRef.current.close();
        }
      }
    });
  }

  async function handleCancel() {
    try {
      await pipelineApi.cancelRun(runId);
    } catch (e) {
      alert('Cancel failed: ' + e.message);
    }
  }

  function stepStatus(step) {
    if (!run) return 'pending';
    const stepIdx = STEPS.indexOf(step);
    const currentIdx = STEPS.indexOf(run.current_step);
    if (run.status === 'completed') return 'done';
    if (run.status === 'failed' && run.current_step === step) return 'failed';
    if (step === run.current_step) return 'active';
    if (stepIdx < currentIdx) return 'done';
    return 'pending';
  }

  if (loading) return <div className="pipeline-loading">Loading...</div>;
  if (!run) return <div className="pipeline-loading">Run not found</div>;

  const isActive = !['completed', 'failed'].includes(run.status);

  return (
    <div className="run-detail">
      <div className="run-header">
        <h3>{run.id}</h3>
        <span className={`status-badge status-${run.status}`}>{run.status}</span>
        {isActive && <button className="btn-danger-sm" onClick={handleCancel}>Cancel</button>}
      </div>

      <div className="run-meta">
        <span>Mode: {run.mode}</span>
        <span>Progress: {run.progress_pct}%</span>
        <span>Started: {new Date(run.created_at).toLocaleString()}</span>
      </div>

      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${run.progress_pct}%` }} />
      </div>

      <div className="step-indicators">
        {STEPS.map(step => (
          <div key={step} className={`step-indicator step-${stepStatus(step)}`}>
            <div className="step-dot" />
            <span>{STEP_LABELS[step]}</span>
          </div>
        ))}
      </div>

      {run.error_message && <div className="error-box">{run.error_message}</div>}

      <div className="log-viewer">
        <h4>Logs</h4>
        <div className="log-output">
          {logs.map((log, i) => (
            <div key={i} className={`log-line log-${log.level}`}>
              <span className="log-step">{log.step || ''}</span>
              <span className="log-msg">{log.message}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}
