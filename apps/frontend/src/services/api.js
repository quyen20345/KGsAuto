// src/services/api.js
// Graph/Admin API. VITE_API_BASE_URL is kept as a backward-compatible alias.
const GRAPH_API_BASE = import.meta.env.VITE_GRAPH_API_BASE_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

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

  mergeEntities: async ({ canonical_id, merge_ids }) => {
    const res = await fetch(`${GRAPH_API_BASE}/api/entity/merge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ canonical_id, merge_ids }),
    });
    return res.json();
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
};
