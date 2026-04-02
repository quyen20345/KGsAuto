import { useEffect, useState } from 'react';
import { api } from '../services/api';
import '../styles/LinkingV3.css';

function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export default function LinkingV3() {
  const [config, setConfig] = useState({
    input_dir: 'data/extracted_v2',
    score_threshold: 0.85,
    limit: 10,
    collection_name: '',
    output_dir: 'data/newgraph',
  });

  const [state, setState] = useState({ active: false });
  const [pairs, setPairs] = useState([]);
  const [pairTotal, setPairTotal] = useState(0);
  const [selectedPairId, setSelectedPairId] = useState(null);
  const [pairDetail, setPairDetail] = useState(null);
  const [draftCanonicalId, setDraftCanonicalId] = useState('');
  const [draftPropertiesText, setDraftPropertiesText] = useState('{}');

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  const refreshState = async () => {
    const data = await api.getLinkingV3State();
    setState(data || { active: false });
  };

  const refreshPairs = async () => {
    const data = await api.listLinkingV3Pairs(200, 0);
    if (data?.detail) {
      setMessage(data.detail);
      setPairs([]);
      setPairTotal(0);
      return;
    }
    setPairs(data.items || []);
    setPairTotal(data.total || 0);
    if ((data.items || []).length > 0) {
      setSelectedPairId((prev) => prev || data.items[0].pair_id);
    }
  };

  useEffect(() => {
    let alive = true;
    api.getLinkingV3State().then((data) => {
      if (!alive) return;
      setState(data || { active: false });
    });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!state.active) return;
    let alive = true;
    api.listLinkingV3Pairs(200, 0).then((data) => {
      if (!alive) return;
      if (data?.detail) {
        setMessage(data.detail);
        setPairs([]);
        setPairTotal(0);
        return;
      }
      setPairs(data.items || []);
      setPairTotal(data.total || 0);
      if ((data.items || []).length > 0) {
        setSelectedPairId((prev) => prev || data.items[0].pair_id);
      }
    });
    return () => {
      alive = false;
    };
  }, [state.active]);

  useEffect(() => {
    if (!selectedPairId) return;
    let alive = true;
    api.getLinkingV3Pair(selectedPairId).then((data) => {
      if (!alive) return;
      if (data?.detail) {
        setMessage(data.detail);
        setPairDetail(null);
        return;
      }
      setPairDetail(data);
      const suggested = data.suggested || {};
      setDraftCanonicalId(suggested.canonical_id || '');
      setDraftPropertiesText(JSON.stringify(suggested.merged_properties || {}, null, 2));
    });
    return () => {
      alive = false;
    };
  }, [selectedPairId]);

  const initRun = async () => {
    setBusy(true);
    setMessage('');

    const payload = {
      input_dir: config.input_dir,
      score_threshold: Number(config.score_threshold),
      limit: Number(config.limit),
      collection_name: config.collection_name || null,
    };

    const data = await api.initLinkingV3Run(payload);
    setBusy(false);
    if (data?.detail) {
      setMessage(data.detail);
      return;
    }

    setMessage(`Run initialized: ${data.pairs_total} pairs`);
    await refreshState();
    await refreshPairs();
  };

  const decide = async (decision) => {
    if (!selectedPairId) return;

    if (decision === 'MERGE') {
      const parsed = safeJsonParse(draftPropertiesText);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        setMessage('merged_properties phải là JSON object hợp lệ');
        return;
      }
    }

    setBusy(true);
    setMessage('');

    const payload = decision === 'MERGE'
      ? {
          decision: 'MERGE',
          canonical_id: draftCanonicalId || null,
          merged_properties: safeJsonParse(draftPropertiesText) || {},
        }
      : { decision: 'SKIP' };

    const data = await api.decideLinkingV3Pair(selectedPairId, payload);
    setBusy(false);
    if (data?.detail) {
      setMessage(data.detail);
      return;
    }

    setMessage(`Pair ${selectedPairId}: ${decision}`);
    await refreshState();
    await refreshPairs();

    const pending = pairs.find((p) => p.pair_id !== selectedPairId && p.status === 'pending');
    if (pending) {
      setSelectedPairId(pending.pair_id);
    }
  };

  const applyRewrite = async () => {
    setBusy(true);
    setMessage('');
    const data = await api.applyLinkingV3({ output_dir: config.output_dir });
    setBusy(false);

    if (data?.detail) {
      setMessage(data.detail);
      return;
    }

    setMessage(`Rewrite xong: ${data.output_dir} (canonical_map=${data.canonical_map_size})`);
    await refreshState();
  };

  const resetRun = async () => {
    setBusy(true);
    setMessage('');
    const data = await api.resetLinkingV3({ drop_collection: true });
    setBusy(false);

    if (data?.detail) {
      setMessage(data.detail);
      return;
    }

    setPairs([]);
    setPairTotal(0);
    setSelectedPairId(null);
    setPairDetail(null);
    setDraftCanonicalId('');
    setDraftPropertiesText('{}');

    setMessage('Run reset thành công');
    await refreshState();
  };

  const compareSeed = pairDetail?.pair?.seed || pairDetail?.seed || null;
  const compareCandidate = pairDetail?.pair?.candidate || pairDetail?.candidate || null;

  return (
    <main className="linking-v3-page">
      <h1>Entity Linking v3 - Simple Human Run</h1>
      <p>Chạy 1 vòng: init -&gt; review merge/skip -&gt; apply rewrite ra newgraph.</p>

      <section className="panel" style={{ minHeight: 'auto' }}>
        <div className="panel-header"><h3>Run Config</h3></div>
        <div className="linking-v3-toolbar" style={{ padding: '10px' }}>
          <input
            placeholder="input_dir"
            value={config.input_dir}
            onChange={(e) => setConfig((p) => ({ ...p, input_dir: e.target.value }))}
          />
          <input
            placeholder="score_threshold"
            type="number"
            step="0.01"
            value={config.score_threshold}
            onChange={(e) => setConfig((p) => ({ ...p, score_threshold: e.target.value }))}
          />
          <input
            placeholder="limit"
            type="number"
            value={config.limit}
            onChange={(e) => setConfig((p) => ({ ...p, limit: e.target.value }))}
          />
          <input
            placeholder="collection_name (optional)"
            value={config.collection_name}
            onChange={(e) => setConfig((p) => ({ ...p, collection_name: e.target.value }))}
          />
          <button disabled={busy} onClick={initRun}>Init</button>
        </div>

        <div className="linking-v3-toolbar" style={{ padding: '0 10px 10px 10px' }}>
          <input
            placeholder="output_dir"
            value={config.output_dir}
            onChange={(e) => setConfig((p) => ({ ...p, output_dir: e.target.value }))}
          />
          <button disabled={busy || !state.active} onClick={applyRewrite}>Apply & Rewrite</button>
          <button disabled={busy} onClick={resetRun}>Reset</button>
        </div>

        <div className="session-summary" style={{ margin: '0 10px 10px 10px' }}>
          <strong>Active:</strong> {String(state.active)}
          {' | '}
          <strong>Run:</strong> {state.run_id || '-'}
          {' | '}
          <strong>Total pairs:</strong> {state.pairs_total || 0}
          {' | '}
          <strong>Pending:</strong> {state.pending || 0}
          {' | '}
          <strong>Merged:</strong> {state.merged || 0}
          {' | '}
          <strong>Skipped:</strong> {state.skipped || 0}
        </div>
      </section>

      {message && <div className="linking-message">{message}</div>}

      <div className="linking-v3-grid">
        <section className="panel">
          <div className="panel-header"><h3>Pair Queue ({pairTotal})</h3></div>
          <div className="pair-list">
            {pairs.map((pair) => (
              <button
                key={pair.pair_id}
                className={`pair-item ${pair.pair_id === selectedPairId ? 'active' : ''}`}
                onClick={() => setSelectedPairId(pair.pair_id)}
              >
                <div>#{pair.pair_id} ({pair.score.toFixed(3)})</div>
                <div>{pair.seed_id}</div>
                <div>{pair.candidate_id}</div>
                <small>{pair.status}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header"><h3>Compare</h3></div>
          {!pairDetail ? (
            <div style={{ padding: '10px' }}>Chọn một pair để review.</div>
          ) : (
            <div className="compare-columns">
              <div>
                <h4>Seed</h4>
                {compareSeed ? (
                  <pre>{JSON.stringify(compareSeed, null, 2)}</pre>
                ) : (
                  <div style={{ padding: '10px' }}>Không có dữ liệu seed.</div>
                )}
              </div>
              <div>
                <h4>Candidate</h4>
                {compareCandidate ? (
                  <pre>{JSON.stringify(compareCandidate, null, 2)}</pre>
                ) : (
                  <div style={{ padding: '10px' }}>Không có dữ liệu candidate.</div>
                )}
              </div>
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-header"><h3>Draft + Decision</h3></div>
          {!pairDetail ? (
            <div style={{ padding: '10px' }}>Chọn pair để edit draft.</div>
          ) : (
            <>
              <div className="draft-fields">
                <label>
                  canonical_id
                  <input
                    value={draftCanonicalId}
                    onChange={(e) => setDraftCanonicalId(e.target.value)}
                  />
                </label>
                <label>
                  merged_properties (JSON)
                  <textarea
                    className="draft-json"
                    value={draftPropertiesText}
                    onChange={(e) => setDraftPropertiesText(e.target.value)}
                  />
                </label>
              </div>

              <div className="decision-actions">
                <button disabled={busy} onClick={() => decide('MERGE')}>MERGE</button>
                <button disabled={busy} onClick={() => decide('SKIP')}>SKIP</button>
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
