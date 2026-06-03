import { useEffect, useMemo, useRef, useState } from 'react';
import { useBreadcrumb } from '../../context/BreadcrumbContext';
import { pipelineApi } from '../../services/api';

const STAGE_LABELS = {
  input: 'Upload / Crawl',
  extract: 'Extract',
  er: 'Entity Resolution',
  import: 'Update Neo4j',
};

const INITIAL_PROGRESS = { extract: 0, er: 0, import: 0 };

const DEFAULT_DIRECTORIES = {
  input: {
    input: 'Browser upload / URL list',
    output: 'mocktest/raw',
  },
  extract: {
    input: 'mocktest/raw',
    output: 'mocktest/extracted',
  },
  er: {
    input: 'mocktest/extracted',
    output: 'mocktest/er_artifacts/local-preview',
  },
  import: {
    input: 'mocktest/er_artifacts/local-preview/stage3/output_graph',
    output: 'neo4j://localhost:7687',
  },
};

function uniqueByName(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = item.name.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function StatusPill({ status }) {
  return <span className={`workflow-status workflow-status-${status.toLowerCase().replace(/\s+/g, '-')}`}>{status}</span>;
}

function Metric({ label, value }) {
  return (
    <div className="workflow-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DirectoryFields({ stage, dirs, disabled, inputLabel = 'Input dir', outputLabel = 'Output dir', onChange }) {
  return (
    <div className="workflow-dir-box">
      <label>
        <span>{inputLabel}</span>
        <input
          value={dirs.input}
          onChange={(event) => onChange(stage, 'input', event.target.value)}
          disabled={disabled}
        />
      </label>
      <label>
        <span>{outputLabel}</span>
        <input
          value={dirs.output}
          onChange={(event) => onChange(stage, 'output', event.target.value)}
          disabled={disabled}
        />
      </label>
    </div>
  );
}

export default function Pipeline() {
  const { setBreadcrumbs } = useBreadcrumb();
  const fileInputRef = useRef(null);
  const eventSourceRef = useRef(null);
  const extractTotalsRef = useRef({ nodes: 0, relationships: 0 });

  const [sourceFiles, setSourceFiles] = useState([]);
  const [urlInput, setUrlInput] = useState('');
  const [progress, setProgress] = useState(INITIAL_PROGRESS);
  const [activeStage, setActiveStage] = useState(null);
  const [extractOutput, setExtractOutput] = useState(null);
  const [erOutput, setErOutput] = useState(null);
  const [importOutput, setImportOutput] = useState(null);
  const [skipExisting, setSkipExisting] = useState(true);
  const [directories, setDirectories] = useState(DEFAULT_DIRECTORIES);
  const [logs, setLogs] = useState([
    { stage: 'system', message: 'Ready. Upload/crawl, Extract, and Entity Resolution are connected to backend.' },
  ]);
  const [error, setError] = useState('');
  const [activeRunId, setActiveRunId] = useState(null);

  // Incremental ER Settings
  const [candidateTopK, setCandidateTopK] = useState(5);
  const [candidateMinScore, setCandidateMinScore] = useState(0.85);
  const [enableLlmBlocking, setEnableLlmBlocking] = useState(true);

  useEffect(() => {
    setBreadcrumbs([
      { label: 'Home', link: '/' },
      { label: 'Pipeline', link: null },
    ]);
  }, [setBreadcrumbs]);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, []);

  const sourceCount = sourceFiles.length;
  const erInputConfigured = Boolean(directories.er.input.trim());
  const importSource = erOutput || extractOutput;

  const stageStatuses = useMemo(() => {
    return {
      input: activeStage === 'input' ? 'Running' : sourceCount > 0 ? 'Ready' : 'Idle',
      extract: activeStage === 'extract' ? 'Running' : extractOutput ? 'Done' : sourceCount > 0 ? 'Ready' : 'Idle',
      er: activeStage === 'er' ? 'Running' : erOutput ? 'Done' : extractOutput || erInputConfigured ? 'Ready' : 'Idle',
      import: importOutput ? 'Done' : importSource ? 'Ready' : 'Idle',
    };
  }, [activeStage, erInputConfigured, erOutput, extractOutput, importOutput, importSource, sourceCount]);

  function appendLog(stage, message) {
    setLogs((prev) => [...prev.slice(-100), { stage, message }]);
  }

  function updateDirectory(stage, key, value) {
    setDirectories((prev) => ({
      ...prev,
      [stage]: {
        ...prev[stage],
        [key]: value,
      },
    }));
  }

  function updateStageDirsAfterInput(outputDir) {
    setDirectories((prev) => ({
      ...prev,
      input: { ...prev.input, output: outputDir },
      extract: { ...prev.extract, input: outputDir },
    }));
  }

  function updateStageDirsAfterExtract(outputDir) {
    setDirectories((prev) => ({
      ...prev,
      extract: { ...prev.extract, output: outputDir },
      er: { ...prev.er, input: outputDir },
    }));
  }

  function updateStageDirsAfterEr(outputDir, outputGraphDir) {
    setDirectories((prev) => ({
      ...prev,
      er: { ...prev.er, output: outputDir },
      import: { ...prev.import, input: outputGraphDir },
    }));
  }

  function resetDirectories() {
    setDirectories(DEFAULT_DIRECTORIES);
    appendLog('system', 'Directory controls reset to sandbox defaults.');
  }

  function resetDownstream(fromStage) {
    if (fromStage === 'input') {
      setExtractOutput(null);
      setErOutput(null);
      setImportOutput(null);
      setProgress(INITIAL_PROGRESS);
    }
    if (fromStage === 'extract') {
      setErOutput(null);
      setImportOutput(null);
      setProgress((prev) => ({ ...prev, er: 0, import: 0 }));
    }
    if (fromStage === 'er') {
      setImportOutput(null);
      setProgress((prev) => ({ ...prev, import: 0 }));
    }
  }

  async function handleFileSelect(event) {
    const files = Array.from(event.target.files || []).filter((file) => file.name.toLowerCase().endsWith('.md'));
    event.target.value = '';
    if (files.length === 0 || activeStage) return;

    const formData = new FormData();
    formData.append('output_dir', directories.input.output);
    files.forEach((file) => formData.append('files', file));

    setActiveStage('input');
    setError('');
    appendLog('input', `Uploading ${files.length} file(s) to ${directories.input.output}.`);

    try {
      const result = await pipelineApi.uploadStageFiles(formData);
      const uploaded = result.uploaded.map((name) => ({ name, origin: 'Upload', state: 'Ready' }));
      const skipped = result.skipped.map((name) => ({ name, origin: 'Upload', state: 'Skipped' }));
      setSourceFiles((prev) => uniqueByName([...prev, ...uploaded, ...skipped]));
      resetDownstream('input');
      updateStageDirsAfterInput(result.output_dir);
      appendLog('input', `Uploaded ${result.uploaded.length}; skipped ${result.skipped.length}.`);
    } catch (err) {
      setError(err.message || 'Upload failed');
      appendLog('input', `Upload failed: ${err.message}`);
    } finally {
      setActiveStage(null);
    }
  }

  async function handleAddUrls() {
    const urls = urlInput.split('\n').map((line) => line.trim()).filter(Boolean);
    if (urls.length === 0 || activeStage) return;

    setActiveStage('input');
    setError('');
    appendLog('input', `Crawling ${urls.length} URL(s) into ${directories.input.output}.`);

    try {
      const result = await pipelineApi.crawlStageUrls({ urls, output_dir: directories.input.output });
      const files = result.files_created.map((name) => ({ name, origin: 'Crawl', state: 'Ready' }));
      setSourceFiles((prev) => uniqueByName([...prev, ...files]));
      setUrlInput('');
      resetDownstream('input');
      updateStageDirsAfterInput(result.output_dir);
      appendLog('input', `Crawler created ${result.files_created.length} file(s).`);
      result.errors.forEach((item) => appendLog('input', `Crawler warning: ${item}`));
    } catch (err) {
      setError(err.message || 'Crawl failed');
      appendLog('input', `Crawl failed: ${err.message}`);
    } finally {
      setActiveStage(null);
    }
  }

  function removeSource(name) {
    setSourceFiles((prev) => prev.filter((file) => file.name !== name));
    resetDownstream('input');
    appendLog('input', `${name} removed from UI selection. File on disk is unchanged.`);
  }

  function clearSources() {
    setSourceFiles([]);
    resetDownstream('input');
    appendLog('input', 'Source list cleared in UI. Files on disk are unchanged.');
  }

  function handleExtractEvent(event) {
    if (event.type === 'log') {
      appendLog(event.step || 'extract', event.message);
      return;
    }
    if (event.type !== 'status') return;

    const pct = event.progress_pct ?? event.progress ?? progress.extract;
    setProgress((prev) => ({ ...prev, extract: pct }));

    if (event.extraction) {
      const detail = event.extraction;
      if (event.file_status === 'completed') {
        extractTotalsRef.current.nodes += detail.node_count || 0;
        extractTotalsRef.current.relationships += detail.relation_count || 0;
      }
      setExtractOutput({
        files: detail.successful || detail.processed || 0,
        nodes: extractTotalsRef.current.nodes,
        relationships: extractTotalsRef.current.relationships,
      });
    }

    if (event.file && event.file_status) {
      appendLog('extract', `${event.file_status}: ${event.file}`);
    }

    if (event.status === 'completed') {
      setProgress((prev) => ({ ...prev, extract: 100 }));
      setActiveStage(null);
      setActiveRunId(null);
      updateStageDirsAfterExtract(event.output_dir || directories.extract.output);
      appendLog('extract', `Completed. Output: ${event.output_dir || directories.extract.output}`);
      if (eventSourceRef.current) eventSourceRef.current.close();
    }

    if (event.status === 'failed') {
      setActiveStage(null);
      setActiveRunId(null);
      setError(event.error_message || event.error || 'Extract failed');
      appendLog('extract', `Failed: ${event.error_message || event.error || 'Unknown error'}`);
      if (eventSourceRef.current) eventSourceRef.current.close();
    }
  }

  async function runExtract() {
    if (!sourceCount || activeStage) return;
    setError('');
    resetDownstream('extract');
    setExtractOutput(null);
    extractTotalsRef.current = { nodes: 0, relationships: 0 };
    setProgress((prev) => ({ ...prev, extract: 0 }));
    setActiveStage('extract');
    appendLog('extract', `Starting backend extract from ${directories.extract.input} to ${directories.extract.output}.`);

    try {
      const result = await pipelineApi.runExtractStage({
        input_dir: directories.extract.input,
        output_dir: directories.extract.output,
        skip_existing: skipExisting,
      });
      setActiveRunId(result.run_id);
      appendLog('extract', `Run created: ${result.run_id}`);
      if (eventSourceRef.current) eventSourceRef.current.close();
      eventSourceRef.current = pipelineApi.streamRunEvents(result.run_id, handleExtractEvent);
      eventSourceRef.current.onerror = () => {
        appendLog('extract', 'SSE connection lost. Check run history or backend logs.');
      };
    } catch (err) {
      setActiveStage(null);
      setActiveRunId(null);
      setError(err.message || 'Extract failed to start');
      appendLog('extract', `Start failed: ${err.message}`);
    }
  }

  function handleEntityResolutionEvent(event) {
    if (event.type === 'log') {
      appendLog(event.step || 'entity_resolution', event.message);
      return;
    }
    if (event.type !== 'status') return;

    const pct = event.progress_pct ?? event.progress ?? progress.er;
    setProgress((prev) => ({ ...prev, er: pct }));

    if (event.status === 'completed') {
      const metrics = event.entity_resolution || {};
      const outputDir = event.output_dir || directories.er.output;
      const outputGraphDir = event.output_graph_dir || `${outputDir}/stage3/output_graph`;
      setErOutput({
        files: metrics.files || 0,
        nodes: metrics.nodes || 0,
        relationships: metrics.relationships || 0,
        outputGraphDir,
      });
      setProgress((prev) => ({ ...prev, er: 100 }));
      setActiveStage(null);
      setActiveRunId(null);
      updateStageDirsAfterEr(outputDir, outputGraphDir);
      appendLog('entity_resolution', `Completed. Graph output: ${outputGraphDir}`);
      if (eventSourceRef.current) eventSourceRef.current.close();
    }

    if (event.status === 'failed') {
      setActiveStage(null);
      setActiveRunId(null);
      setError(event.error_message || event.error || 'Entity Resolution failed');
      appendLog('entity_resolution', `Failed: ${event.error_message || event.error || 'Unknown error'}`);
      if (eventSourceRef.current) eventSourceRef.current.close();
    }
  }

  async function runEntityResolution() {
    if (!erInputConfigured || activeStage) return;
    setError('');
    resetDownstream('er');
    setErOutput(null);
    setProgress((prev) => ({ ...prev, er: 0 }));
    setActiveStage('er');
    appendLog('entity_resolution', `Starting Incremental ER from ${directories.er.input}.`);

    try {
      const result = await pipelineApi.runIncrementalERStage({
        input_dir: directories.er.input,
        candidate_top_k: candidateTopK,
        candidate_min_score: candidateMinScore,
        enable_llm_blocking: enableLlmBlocking,
      });
      setActiveRunId(result.run_id);
      appendLog('entity_resolution', `Run created: ${result.run_id}`);
      if (eventSourceRef.current) eventSourceRef.current.close();
      eventSourceRef.current = pipelineApi.streamRunEvents(result.run_id, handleEntityResolutionEvent);
      eventSourceRef.current.onerror = () => {
        appendLog('entity_resolution', 'SSE connection lost. Check run history or backend logs.');
      };
    } catch (err) {
      setActiveStage(null);
      setActiveRunId(null);
      setError(err.message || 'Entity Resolution failed to start');
      appendLog('entity_resolution', `Start failed: ${err.message}`);
    }
  }

  return (
    <div className="pipeline-workflow">
      <div className="workflow-header">
        <div>
          <h1>Pipeline</h1>
          <div className="workflow-run-id">{activeRunId ? `Active run: ${activeRunId}` : 'Stage mode: upload/crawl + extract + ER connected'}</div>
        </div>
        <div className="workflow-header-actions">
          <div className="workflow-summary">
            <Metric label="Raw" value={sourceCount} />
            <Metric label="Extracted" value={extractOutput?.files || 0} />
            <Metric label="Graph Nodes" value={erOutput?.nodes || extractOutput?.nodes || 0} />
          </div>
          <button className="btn-secondary" type="button" onClick={resetDirectories} disabled={!!activeStage}>Reset Dirs</button>
        </div>
      </div>

      <div className="workflow-guardrail">
        <strong>Directory sandbox</strong>
        <span>Upload/crawl, Extract, and Entity Resolution write to backend paths. Defaults use mocktest/* so current data is not touched.</span>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="workflow-steps" aria-label="Pipeline stages">
        {Object.entries(STAGE_LABELS).map(([id, label]) => (
          <div key={id} className={`workflow-step workflow-step-${stageStatuses[id].toLowerCase()}`}>
            <div className="workflow-step-index">{Object.keys(STAGE_LABELS).indexOf(id) + 1}</div>
            <div>
              <strong>{label}</strong>
              <StatusPill status={stageStatuses[id]} />
            </div>
          </div>
        ))}
      </div>

      <div className="workflow-grid">
        <section className="workflow-panel workflow-panel-input">
          <div className="workflow-panel-heading">
            <h2>Upload / Crawl</h2>
            <StatusPill status={stageStatuses.input} />
          </div>

          <DirectoryFields
            stage="input"
            dirs={directories.input}
            disabled={!!activeStage}
            inputLabel="Input source"
            outputLabel="Raw output dir"
            onChange={updateDirectory}
          />

          <div className="workflow-actions-row">
            <button className="btn-primary" type="button" onClick={() => fileInputRef.current?.click()} disabled={!!activeStage}>Choose .md</button>
            <button className="btn-secondary" type="button" onClick={clearSources} disabled={!!activeStage || sourceCount === 0}>Clear List</button>
            <input ref={fileInputRef} type="file" accept=".md" multiple hidden onChange={handleFileSelect} />
          </div>

          <div className="workflow-url-row">
            <textarea
              value={urlInput}
              onChange={(event) => setUrlInput(event.target.value)}
              rows={4}
              placeholder="https://uet.vnu.edu.vn/..."
              disabled={!!activeStage}
            />
            <button className="btn-secondary" type="button" onClick={handleAddUrls} disabled={!!activeStage || !urlInput.trim()}>Crawl URLs</button>
          </div>

          <div className="workflow-file-list">
            <div className="workflow-list-header">
              <span>Source</span>
              <span>Origin</span>
              <span>Status</span>
              <span />
            </div>
            {sourceFiles.map((file) => (
              <div className="workflow-file-row" key={`${file.origin}-${file.name}`}>
                <span title={file.name}>{file.name}</span>
                <span>{file.origin}</span>
                <span>{file.state}</span>
                <button className="workflow-icon-button" type="button" onClick={() => removeSource(file.name)} disabled={!!activeStage} aria-label={`Remove ${file.name}`}>x</button>
              </div>
            ))}
            {sourceFiles.length === 0 && <div className="workflow-empty-row">No source staged</div>}
          </div>
        </section>

        <section className="workflow-panel">
          <div className="workflow-panel-heading">
            <h2>Extract</h2>
            <StatusPill status={stageStatuses.extract} />
          </div>
          <DirectoryFields stage="extract" dirs={directories.extract} disabled={!!activeStage} onChange={updateDirectory} />
          <div className="workflow-toggle-row">
            <label>
              <input
                type="checkbox"
                checked={skipExisting}
                onChange={(event) => setSkipExisting(event.target.checked)}
                disabled={!!activeStage}
              />
              Skip existing output
            </label>
          </div>
          <div className="workflow-progress-line">
            <span>{progress.extract}%</span>
            <div className="workflow-progress-track"><div style={{ width: `${progress.extract}%` }} /></div>
          </div>
          <div className="workflow-metrics-row">
            <Metric label="Files" value={extractOutput?.files || sourceCount} />
            <Metric label="Nodes" value={extractOutput?.nodes || 0} />
            <Metric label="Relations" value={extractOutput?.relationships || 0} />
          </div>
          <button className="btn-primary" type="button" onClick={runExtract} disabled={!sourceCount || !!activeStage}>Run Extract</button>
        </section>

        <section className="workflow-panel">
          <div className="workflow-panel-heading">
            <h2>Entity Resolution</h2>
            <StatusPill status={stageStatuses.er} />
          </div>
          <DirectoryFields stage="er" dirs={directories.er} disabled={!!activeStage} onChange={updateDirectory} />
          <div className="workflow-dir-box" style={{ marginTop: '10px' }}>
            <label>
              <span>Candidate Top K</span>
              <input type="number" value={candidateTopK} onChange={(e) => setCandidateTopK(parseInt(e.target.value, 10))} disabled={!!activeStage} />
            </label>
            <label>
              <span>Min Vector Score</span>
              <input type="number" step="0.01" value={candidateMinScore} onChange={(e) => setCandidateMinScore(parseFloat(e.target.value))} disabled={!!activeStage} />
            </label>
          </div>
          <div className="workflow-toggle-row">
            <label>
              <input type="checkbox" checked={enableLlmBlocking} onChange={(e) => setEnableLlmBlocking(e.target.checked)} disabled={!!activeStage} />
              Enable LLM Blocking
            </label>
          </div>
          <div className="workflow-stage-stack">
            {['Embedding', 'Candidate Retrieval', 'Clustering', 'Resolution', 'Neo4j Upsert'].map((stage) => (
              <div key={stage} className={`workflow-stage-row ${erOutput ? 'done' : ''}`}>
                <span>{stage}</span>
                <span>{erOutput ? 'Done' : activeStage === 'er' ? 'Running' : 'Next'}</span>
              </div>
            ))}
          </div>
          <div className="workflow-progress-line">
            <span>{progress.er}%</span>
            <div className="workflow-progress-track"><div style={{ width: `${progress.er}%` }} /></div>
          </div>
          <div className="workflow-metrics-row">
            <Metric label="Files" value={erOutput?.files || 0} />
            <Metric label="Nodes" value={erOutput?.nodes || 0} />
            <Metric label="Relations" value={erOutput?.relationships || 0} />
          </div>
          <button className="btn-primary" type="button" onClick={runEntityResolution} disabled={!erInputConfigured || !!activeStage}>Run Entity Resolution</button>
        </section>

        <section className="workflow-panel">
          <div className="workflow-panel-heading">
            <h2>Update Neo4j</h2>
            <StatusPill status={stageStatuses.import} />
          </div>
          <DirectoryFields
            stage="import"
            dirs={directories.import}
            disabled={!!activeStage}
            inputLabel="Graph input dir"
            outputLabel="Neo4j target"
            onChange={updateDirectory}
          />
          <div className="workflow-progress-line">
            <span>{progress.import}%</span>
            <div className="workflow-progress-track"><div style={{ width: `${progress.import}%` }} /></div>
          </div>
          <div className="workflow-import-source">
            <span>Source</span>
            <strong>{erOutput ? 'Resolved graph ready' : extractOutput ? 'Extracted graph ready' : 'None'}</strong>
          </div>
          <div className="workflow-metrics-row">
            <Metric label="Nodes" value={0} />
            <Metric label="Relations" value={0} />
          </div>
          <button className="btn-secondary" type="button" disabled>Connect Neo4j next</button>
        </section>
      </div>

      <section className="workflow-log-panel">
        <div className="workflow-panel-heading">
          <h2>Run Events</h2>
          <button className="btn-secondary" type="button" onClick={() => setLogs([])} disabled={!!activeStage || logs.length === 0}>Clear Log</button>
        </div>
        <div className="workflow-log-output">
          {logs.map((log, index) => (
            <div className="workflow-log-line" key={`${log.stage}-${index}`}>
              <span>{log.stage}</span>
              <p>{log.message}</p>
            </div>
          ))}
          {logs.length === 0 && <div className="workflow-log-empty">No events</div>}
        </div>
      </section>
    </div>
  );
}
