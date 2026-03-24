import { useState, useEffect } from 'react';
import '../styles/GraphFilters.css';

function GraphFilters({ metadata, onApplyFilters }) {
  const [mode, setMode] = useState('all');
  const [selectedLabels, setSelectedLabels] = useState([]);
  const [selectedRelationships, setSelectedRelationships] = useState([]);
  const [limit, setLimit] = useState(100);

  const handleApply = () => {
    onApplyFilters({
      mode,
      labels: selectedLabels.join(','),
      relationships: selectedRelationships.join(','),
      limit
    });
  };

  const handleLabelChange = (label) => {
    setSelectedLabels(prev =>
      prev.includes(label)
        ? prev.filter(l => l !== label)
        : [...prev, label]
    );
  };

  const handleRelationshipChange = (rel) => {
    setSelectedRelationships(prev =>
      prev.includes(rel)
        ? prev.filter(r => r !== rel)
        : [...prev, rel]
    );
  };

  return (
    <div className="graph-filters">
      <h3>Visualization Filters</h3>

      <div className="filter-section">
        <label>Mode:</label>
        <div className="radio-group">
          <label>
            <input
              type="radio"
              value="all"
              checked={mode === 'all'}
              onChange={(e) => setMode(e.target.value)}
            />
            Visualize All
          </label>
          <label>
            <input
              type="radio"
              value="labels"
              checked={mode === 'labels'}
              onChange={(e) => setMode(e.target.value)}
            />
            By Node Labels
          </label>
          <label>
            <input
              type="radio"
              value="relationships"
              checked={mode === 'relationships'}
              onChange={(e) => setMode(e.target.value)}
            />
            By Relationship Types
          </label>
        </div>
      </div>

      {mode === 'labels' && (
        <div className="filter-section">
          <label>Select Labels:</label>
          <div className="checkbox-group">
            {metadata.labels && metadata.labels.map(label => (
              <label key={label}>
                <input
                  type="checkbox"
                  checked={selectedLabels.includes(label)}
                  onChange={() => handleLabelChange(label)}
                />
                {label}
              </label>
            ))}
          </div>
        </div>
      )}

      {mode === 'relationships' && (
        <div className="filter-section">
          <label>Select Relationship Types:</label>
          <div className="checkbox-group">
            {metadata.relationship_types && metadata.relationship_types.map(rel => (
              <label key={rel}>
                <input
                  type="checkbox"
                  checked={selectedRelationships.includes(rel)}
                  onChange={() => handleRelationshipChange(rel)}
                />
                {rel}
              </label>
            ))}
          </div>
        </div>
      )}

      <div className="filter-section">
        <label>Node Limit: {limit}</label>
        <input
          type="range"
          min="50"
          max="500"
          step="50"
          value={limit}
          onChange={(e) => setLimit(parseInt(e.target.value))}
        />
      </div>

      <button className="apply-button" onClick={handleApply}>
        Apply Filters
      </button>
    </div>
  );
}

export default GraphFilters;
