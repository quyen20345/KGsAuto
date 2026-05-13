function formatGraphItem(item) {
  if (item.subject && item.predicate && item.object) {
    return `${item.subject} — ${item.predicate} → ${item.object}`;
  }
  if (item.fact_text) return item.fact_text;
  if (item.entity_name) return item.entity_name;
  return null;
}

export default function EvidencePanel({ evidence }) {
  const chunks = evidence?.markdown_chunks || [];
  const graph = evidence?.graph_evidence || evidence?.graph || [];

  if (!evidence || (!chunks.length && !graph.length)) return null;

  return (
    <details className="chat-evidence">
      <summary>Bằng chứng ({chunks.length + graph.length})</summary>
      {chunks.length > 0 && (
        <div className="chat-evidence-section">
          <strong>Đoạn văn bản</strong>
          {chunks.slice(0, 4).map((chunk, index) => (
            <div key={chunk.chunk_id || index} className="chat-evidence-card">
              <div className="chat-evidence-meta">
                {chunk.title || chunk.doc_id || 'Tài liệu'} {chunk.score ? `· ${Number(chunk.score).toFixed(3)}` : ''}
              </div>
              <div className="chat-evidence-text">{chunk.text}</div>
            </div>
          ))}
        </div>
      )}
      {graph.length > 0 && (
        <div className="chat-evidence-section">
          <strong>Bằng chứng từ đồ thị</strong>
          {graph.slice(0, 4).map((item, index) => {
            const formatted = formatGraphItem(item);
            return (
              <div key={item.entity_id || index} className="chat-evidence-card">
                <div className="chat-evidence-meta">{item.entity_name || item.fact_type || 'Graph'}</div>
                {formatted ? (
                  <div className="chat-evidence-text">{formatted}</div>
                ) : (
                  <details className="chat-evidence-raw">
                    <summary>Chi tiết</summary>
                    <pre>{JSON.stringify(item, null, 2)}</pre>
                  </details>
                )}
              </div>
            );
          })}
        </div>
      )}
    </details>
  );
}
