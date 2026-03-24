import { useState, useEffect } from 'react';
import { api } from '../services/api';
import GraphFilters from '../components/GraphFilters';
import GraphCanvas from '../components/GraphCanvas';
import '../styles/Visualize.css';

function Visualize() {
  const [metadata, setMetadata] = useState({ labels: [], relationship_types: [] });
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadMetadata();
    loadInitialGraph();
  }, []);

  const loadMetadata = async () => {
    try {
      const data = await api.getGraphMetadata();
      if (data.error) {
        setError(data.error);
      } else {
        setMetadata(data);
      }
    } catch (err) {
      setError('Failed to load metadata: ' + err.message);
    }
  };

  const loadInitialGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getGraphVisualization('all', '', '', 100);
      if (data.error) {
        setError(data.error);
      } else {
        setGraphData(data);
      }
    } catch (err) {
      setError('Failed to load graph: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyFilters = async (filters) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getGraphVisualization(
        filters.mode,
        filters.labels,
        filters.relationships,
        filters.limit
      );
      if (data.error) {
        setError(data.error);
      } else {
        setGraphData(data);
      }
    } catch (err) {
      setError('Failed to load graph: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="visualize-page">
      <div className="visualize-header">
        <h1>Graph Visualization</h1>
        <p>Explore the knowledge graph with interactive visualization</p>
      </div>

      <div className="visualize-content">
        <GraphFilters metadata={metadata} onApplyFilters={handleApplyFilters} />

        <div className="visualize-main">
          {loading && <div className="loading">Loading graph...</div>}
          {error && <div className="error">Error: {error}</div>}
          {!loading && !error && graphData.nodes.length === 0 && (
            <div className="empty">No data to display. Try adjusting your filters.</div>
          )}
          {!loading && !error && graphData.nodes.length > 0 && (
            <GraphCanvas graphData={graphData} />
          )}
        </div>
      </div>
    </div>
  );
}

export default Visualize;
