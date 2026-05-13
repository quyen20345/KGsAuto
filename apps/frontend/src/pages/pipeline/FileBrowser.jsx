import { useState, useEffect, useRef } from 'react';
import { pipelineApi } from '../../services/api';
import CrawlForm from './CrawlForm';

export default function FileBrowser() {
  const [tab, setTab] = useState('raw');
  const [rawFiles, setRawFiles] = useState([]);
  const [extractedFiles, setExtractedFiles] = useState([]);
  const [resolvedRuns, setResolvedRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCrawl, setShowCrawl] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => { loadFiles(); }, [tab]);

  async function loadFiles() {
    setLoading(true);
    try {
      if (tab === 'raw') setRawFiles(await pipelineApi.listRawFiles());
      else if (tab === 'extracted') setExtractedFiles(await pipelineApi.listExtractedFiles());
      else setResolvedRuns(await pipelineApi.listResolvedRuns());
    } catch (e) {
      console.error('Failed to load files:', e);
    }
    setLoading(false);
  }

  async function handleUpload(e) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const formData = new FormData();
    for (const f of files) formData.append('files', f);
    try {
      const result = await pipelineApi.uploadFiles(formData);
      alert(`Uploaded: ${result.uploaded.length} files. Skipped: ${result.skipped.length}`);
      loadFiles();
    } catch (err) {
      alert('Upload failed: ' + err.message);
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function handleDelete(filename) {
    if (!confirm(`Delete ${filename}?`)) return;
    try {
      await pipelineApi.deleteRawFile(filename);
      loadFiles();
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  }

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  return (
    <div className="file-browser">
      <div className="file-tabs">
        <button className={tab === 'raw' ? 'active' : ''} onClick={() => setTab('raw')}>Raw ({rawFiles.length})</button>
        <button className={tab === 'extracted' ? 'active' : ''} onClick={() => setTab('extracted')}>Extracted ({extractedFiles.length})</button>
        <button className={tab === 'resolved' ? 'active' : ''} onClick={() => setTab('resolved')}>Resolved ({resolvedRuns.length})</button>
      </div>

      {tab === 'raw' && (
        <div className="file-actions">
          <button className="btn-primary" onClick={() => fileInputRef.current?.click()}>Upload .md</button>
          <button className="btn-secondary" onClick={() => setShowCrawl(true)}>Crawl URL</button>
          <input ref={fileInputRef} type="file" accept=".md" multiple hidden onChange={handleUpload} />
        </div>
      )}

      {showCrawl && <CrawlForm onClose={() => setShowCrawl(false)} onDone={() => { setShowCrawl(false); loadFiles(); }} />}

      {loading ? <div className="pipeline-loading">Loading...</div> : (
        <div className="file-list">
          {tab === 'raw' && (
            <table>
              <thead><tr><th>Name</th><th>Size</th><th>Extracted</th><th>Actions</th></tr></thead>
              <tbody>
                {rawFiles.map(f => (
                  <tr key={f.name}>
                    <td>{f.name}</td>
                    <td>{formatSize(f.size)}</td>
                    <td>{f.has_extraction ? '✓' : '—'}</td>
                    <td><button className="btn-danger-sm" onClick={() => handleDelete(f.name)}>Delete</button></td>
                  </tr>
                ))}
                {rawFiles.length === 0 && <tr><td colSpan={4}>No files</td></tr>}
              </tbody>
            </table>
          )}

          {tab === 'extracted' && (
            <table>
              <thead><tr><th>Name</th><th>Nodes</th><th>Relations</th><th>Size</th></tr></thead>
              <tbody>
                {extractedFiles.map(f => (
                  <tr key={f.name}>
                    <td>{f.name}</td>
                    <td>{f.node_count ?? '—'}</td>
                    <td>{f.rel_count ?? '—'}</td>
                    <td>{formatSize(f.size)}</td>
                  </tr>
                ))}
                {extractedFiles.length === 0 && <tr><td colSpan={4}>No files</td></tr>}
              </tbody>
            </table>
          )}

          {tab === 'resolved' && (
            <table>
              <thead><tr><th>Run ID</th><th>Stage 1</th><th>Stage 2</th><th>Stage 3</th><th>Output Files</th></tr></thead>
              <tbody>
                {resolvedRuns.map(r => (
                  <tr key={r.run_id}>
                    <td>{r.run_id}</td>
                    <td>{r.has_stage1 ? '✓' : '—'}</td>
                    <td>{r.has_stage2 ? '✓' : '—'}</td>
                    <td>{r.has_stage3 ? '✓' : '—'}</td>
                    <td>{r.output_file_count}</td>
                  </tr>
                ))}
                {resolvedRuns.length === 0 && <tr><td colSpan={5}>No runs</td></tr>}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
