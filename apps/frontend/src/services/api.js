// src/services/api.js
// Graph/Admin API. VITE_API_BASE_URL is kept as a backward-compatible alias.
const GRAPH_API_BASE = import.meta.env.VITE_GRAPH_API_BASE_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const CHAT_API_BASE = import.meta.env.VITE_CHAT_API_BASE_URL || 'http://localhost:8002';

// Pipeline API
const PIPELINE_API_BASE = import.meta.env.VITE_PIPELINE_API_BASE_URL || 'http://localhost:8001';

export const pipelineApi = {
  listRawFiles: async () => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/files/raw`);
    return res.json();
  },

  listExtractedFiles: async () => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/files/extracted`);
    return res.json();
  },

  listResolvedRuns: async () => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/files/resolved`);
    return res.json();
  },

  uploadFiles: async (formData) => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/files/upload`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  deleteRawFile: async (name) => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/files/raw/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    });
    return res.json();
  },

  crawlUrls: async (urls) => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/crawl`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urls }),
    });
    return res.json();
  },

  triggerRun: async (config) => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/pipeline/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `Pipeline trigger failed (${res.status})`);
    }
    return res.json();
  },

  listRuns: async () => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/pipeline/runs`);
    return res.json();
  },

  getRun: async (id) => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/pipeline/runs/${encodeURIComponent(id)}`);
    return res.json();
  },

  cancelRun: async (id) => {
    const res = await fetch(`${PIPELINE_API_BASE}/api/pipeline/runs/${encodeURIComponent(id)}/cancel`, {
      method: 'POST',
    });
    return res.json();
  },

  streamRunEvents: (id, onEvent) => {
    const es = new EventSource(`${PIPELINE_API_BASE}/api/pipeline/runs/${encodeURIComponent(id)}/events`);
    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type !== 'ping') onEvent(data);
    };
    es.onerror = () => es.close();
    return es;
  },
};

export const api = {
  // Home page - Random triplets
  getRandomTriplets: async (limit = 8) => {
    const res = await fetch(`${GRAPH_API_BASE}/api/random_triplets?limit=${limit}`);
    return res.json();
  },

  // Search page - Entity search
  search: async (query) => {
    const res = await fetch(`${GRAPH_API_BASE}/api/search?q=${encodeURIComponent(query)}`);
    return res.json();
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
    return res.json();
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
    return res.json();
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
    return res.json();
  },

  // Get graph metadata (labels and relationship types)
  getGraphMetadata: async () => {
    const res = await fetch(`${GRAPH_API_BASE}/api/graph/metadata`);
    return res.json();
  },

  getChatModes: async () => {
    const res = await fetch(`${CHAT_API_BASE}/modes`);
    if (!res.ok) throw new Error(`Failed to load chat modes (${res.status})`);
    return res.json();
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
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `Chat request failed (${res.status})`);
    }
    return res.json();
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
