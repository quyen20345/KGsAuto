import { useState } from 'react';
import { pipelineApi } from '../../services/api';

export default function RunTrigger({ onClose, onStarted }) {
  const [mode, setMode] = useState('quick_import');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleStart() {
    setLoading(true);
    setError(null);
    try {
      const res = await pipelineApi.triggerRun({ mode });
      onStarted(res.run_id);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h3>Run Pipeline</h3>
        <div className="form-group">
          <label>Mode:</label>
          <select value={mode} onChange={e => setMode(e.target.value)}>
            <option value="quick_import">Quick Import (Extract + Import, skip ER)</option>
            <option value="full_pipeline">Full Pipeline (Extract + ER + Import)</option>
          </select>
        </div>
        <div className="mode-description">
          {mode === 'quick_import'
            ? 'Extracts new files and imports directly to Neo4j. Fast but may have duplicates.'
            : 'Extracts, runs entity resolution (dedup), then imports. Higher quality but slower.'}
        </div>
        {error && <p className="error-text">{error}</p>}
        <div className="modal-actions">
          <button className="btn-primary" onClick={handleStart} disabled={loading}>
            {loading ? 'Starting...' : 'Start Run'}
          </button>
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
