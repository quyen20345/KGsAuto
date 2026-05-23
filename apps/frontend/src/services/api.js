// src/services/api.js
// Graph/Admin API. VITE_API_BASE_URL is kept as a backward-compatible alias.
const GRAPH_API_BASE = import.meta.env.VITE_GRAPH_API_BASE_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const CHAT_API_BASE = import.meta.env.VITE_CHAT_API_BASE_URL || 'http://localhost:8002';

// Pipeline API
const PIPELINE_API_BASE = import.meta.env.VITE_PIPELINE_API_BASE_URL || 'http://localhost:8001';

async function jsonOrThrow(res, fallback) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    throw new Error((typeof detail === 'string' ? detail : detail?.detail) || fallback || `Request failed (${res.status})`);
  }
  return data;
}

export const pipelineApi = {
  listRawFiles: async () => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/files/raw`);
    return jsonOrThrow(res, 'Failed to load raw files');
  },

  listExtractedFiles: async () => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/files/extracted`);
    return jsonOrThrow(res);
  },

  listResolvedRuns: async () => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/files/resolved`);
    return jsonOrThrow(res);
  },

  uploadFiles: async (formData) => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/files/upload`, {
      method: 'POST',
      body: formData,
    });
    return jsonOrThrow(res);
  },

  deleteRawFile: async (name) => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/files/raw/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    });
    return jsonOrThrow(res);
  },

  crawlUrls: async (urls) => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/crawl`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urls }),
    });
    return jsonOrThrow(res);
  },

  triggerRun: async (config) => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/pipeline/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    return jsonOrThrow(res, 'Pipeline trigger failed');
  },

  listRuns: async () => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/pipeline/runs`);
    return jsonOrThrow(res);
  },

  getRun: async (id) => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/pipeline/runs/${encodeURIComponent(id)}`);
    return jsonOrThrow(res);
  },

  cancelRun: async (id) => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/pipeline/runs/${encodeURIComponent(id)}/cancel`, {
      method: 'POST',
    });
    return jsonOrThrow(res);
  },

  streamRunEvents: (id, onEvent) => {
    const es = new EventSource(`${PIPELINE_API_BASE}/api/pipeline/runs/${encodeURIComponent(id)}/events`);
    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type !== 'ping') onEvent(data);
    };
    return es;
  },
};

export const api = {
  // Home page - Random triplets
  getRandomTriplets: async (limit = 8) => {
    const res = await fetch(`${GRAPH_API_BASE}/api/random_triplets?limit=${limit}`);
    return jsonOrThrow(res);
  },

  // Search page - Entity search
  search: async (query) => {
    const res = await fetch(`${GRAPH_API_BASE}/api/search?q=${encodeURIComponent(query)}`);
    return jsonOrThrow(res);
  },

  searchLexical: async (query, topK = 10, labelFilter = null) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    try {
      let url = `${GRAPH_API_BASE}/api/search/lexical?q=${encodeURIComponent(query)}&top_k=${topK}`;
      if (labelFilter) {
        url += `&label_filter=${encodeURIComponent(labelFilter)}`;
      }

      const res = await fetch(url, {
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`Search request failed with status ${res.status}`);
      }

      return await res.json();
    } catch (error) {
      if (error?.name === 'AbortError') {
        throw new Error('Search timed out after 30 seconds.');
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  },

  searchHybrid: async (query, topK = 10, labelFilter = null) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    try {
      let url = `${GRAPH_API_BASE}/api/search/hybrid?q=${encodeURIComponent(query)}&top_k=${topK}`;
      if (labelFilter) {
        url += `&label_filter=${encodeURIComponent(labelFilter)}`;
      }

      const res = await fetch(url, {
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`Search request failed with status ${res.status}`);
      }

      return await res.json();
    } catch (error) {
      if (error?.name === 'AbortError') {
        throw new Error('Search took too long. The first request may need extra time while the embedding model loads in the Graph API.');
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  },

  // Entity page - Entity details
  getEntity: async (id) => {
    const res = await fetch(`${GRAPH_API_BASE}/api/entity/${encodeURIComponent(id)}`);
    return jsonOrThrow(res);
  },

  mergeEntities: async ({ canonical_id, merge_ids, canonical_name, canonical_new_id }) => {
    const body = { canonical_id, merge_ids };
    if (canonical_name) body.canonical_name = canonical_name;
    if (canonical_new_id) body.canonical_new_id = canonical_new_id;
    const res = await fetch(`${GRAPH_API_BASE}/api/entity/merge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return jsonOrThrow(res);
  },

  compareEntities: async ({ entity_id_a, entity_id_b }) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    try {
      const res = await fetch(`${GRAPH_API_BASE}/api/entity/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id_a, entity_id_b }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`Compare request failed (${res.status})`);
      return await res.json();
    } catch (error) {
      if (error?.name === 'AbortError') {
        throw new Error('Comparison timed out after 120 seconds.');
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  },

  // Run custom Cypher query
  runCypher: async (cypher) => {
    const res = await fetch(`${GRAPH_API_BASE}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cypher }),
    });
    return jsonOrThrow(res);
  },

  // Get graph metadata (labels and relationship types)
  getGraphMetadata: async () => {
    const res = await fetch(`${GRAPH_API_BASE}/api/graph/metadata`);
    return jsonOrThrow(res);
  },

  getChatModes: async () => {
    const res = await fetch(`${CHAT_API_BASE}/modes`);
    if (!res.ok) throw new Error(`Failed to load chat modes (${res.status})`);
    return jsonOrThrow(res);
  },

  sendChatMessage: async ({ message, mode = 'semantic_search', topK = 5, includeEvidence = true, conversationId = null }) => {
    const res = await fetch(`${CHAT_API_BASE}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        mode,
        top_k: topK,
        include_evidence: includeEvidence,
        conversation_id: conversationId,
      }),
    });
    return jsonOrThrow(res, 'Chat request failed');
  },

  streamChatMessage: async ({ message, mode = 'semantic_search', topK = 5, includeEvidence = true, conversationId = null, signal, onEvent }) => {
    const res = await fetch(`${CHAT_API_BASE}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: mode,
        mode,
        messages: [{ role: 'user', content: message }],
        stream: true,
        top_k: topK,
        include_evidence: includeEvidence,
        conversation_id: conversationId,
      }),
      signal,
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `Chat request failed (${res.status})`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const item of events) {
        const line = item.split('\n').find((part) => part.startsWith('data: '));
        if (!line) continue;
        const data = line.slice(6);
        if (data === '[DONE]') return;
        onEvent(JSON.parse(data));
      }
    }
  },
};
