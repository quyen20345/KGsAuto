import { useState } from 'react';
import { pipelineApi } from '../../services/api';

export default function CrawlForm({ onClose, onDone }) {
  const [urls, setUrls] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  async function handleCrawl() {
    const urlList = urls.split('\n').map(u => u.trim()).filter(Boolean);
    if (urlList.length === 0) return;
    setLoading(true);
    try {
      const res = await pipelineApi.crawlUrls(urlList);
      setResult(res);
      if (res.files_created.length > 0) {
        setTimeout(onDone, 2000);
      }
    } catch (e) {
      setResult({ files_created: [], errors: [e.message] });
    }
    setLoading(false);
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h3>Crawl URLs</h3>
        <p>Enter URLs to crawl (one per line):</p>
        <textarea
          value={urls}
          onChange={e => setUrls(e.target.value)}
          rows={5}
          placeholder="https://uet.vnu.edu.vn/example-page/"
          disabled={loading}
        />
        {result && (
          <div className="crawl-result">
            {result.files_created.length > 0 && (
              <p style={{ color: '#4caf50' }}>Created: {result.files_created.join(', ')}</p>
            )}
            {result.errors.length > 0 && (
              <p style={{ color: '#f44336' }}>Errors: {result.errors.join(', ')}</p>
            )}
          </div>
        )}
        <div className="modal-actions">
          <button className="btn-primary" onClick={handleCrawl} disabled={loading}>
            {loading ? 'Crawling...' : 'Crawl'}
          </button>
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
