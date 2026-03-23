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
  }
};