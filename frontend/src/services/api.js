// src/services/api.js
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const api = {
  getRandomTriplets: async (limit = 8) => {
    const res = await fetch(`${API_BASE}/api/random_triplets?limit=${limit}`);
    return res.json();
  },
  search: async (query) => {
    const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`);
    return res.json();
  },
  getEntity: async (id) => {
    const res = await fetch(`${API_BASE}/api/entity/${encodeURIComponent(id)}`);
    return res.json();
  },
  queryCypher: async (cypher) => {
    const res = await fetch(`${API_BASE}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cypher })
    });
    return res.json();
  },
  getGraphVisualization: async (mode, labels, relationships, limit) => {
    const params = new URLSearchParams({ mode, limit });
    if (labels) params.append('labels', labels);
    if (relationships) params.append('relationships', relationships);
    const res = await fetch(`${API_BASE}/api/graph/visualize?${params}`);
    return res.json();
  },
  getGraphMetadata: async () => {
    const res = await fetch(`${API_BASE}/api/graph/metadata`);
    return res.json();
  },

  // --- Linking v3 ---
  initLinkingV3Run: async (payload) => {
    const res = await fetch(`${API_BASE}/api/linking/v3/init`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  },
  getLinkingV3State: async () => {
    const res = await fetch(`${API_BASE}/api/linking/v3/state`);
    return res.json();
  },
  listLinkingV3Pairs: async (limit = 50, offset = 0) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    const res = await fetch(`${API_BASE}/api/linking/v3/pairs?${params.toString()}`);
    return res.json();
  },
  getLinkingV3Pair: async (pairId) => {
    const res = await fetch(`${API_BASE}/api/linking/v3/pairs/${pairId}`);
    return res.json();
  },
  decideLinkingV3Pair: async (pairId, payload) => {
    const res = await fetch(`${API_BASE}/api/linking/v3/pairs/${pairId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  },
  applyLinkingV3: async (payload) => {
    const res = await fetch(`${API_BASE}/api/linking/v3/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  },
  resetLinkingV3: async (payload = { drop_collection: true }) => {
    const res = await fetch(`${API_BASE}/api/linking/v3/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  }
};
