import { useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import '../styles/GraphCanvas.css';

const NODE_COLORS = {
  'UNIVERSITY': '#4A90E2',
  'STUDENT': '#50C878',
  'ORGANIZATION': '#F5A623',
  'LOCATION': '#E94B3C',
  'RESEARCH': '#9013FE',
  'CONTACT_DETAILS': '#E67E22',
  'STUDY_PROGRAM': '#16A085',
  'APPLICATION': '#8E44AD',
  'SERVICE': '#2980B9',
  'Default': '#95A5A6'
};

const LINK_COLORS = {
  'HAS_ORGANIZATION': '#F39C12',
  'HAS_LOCATION': '#E74C3C',
  'STUDIES_AT': '#3498DB',
  'HAS_APPLICATION': '#2ECC71',
  'HAS_SERVICE': '#9B59B6',
  'HAS_CONTACT_DETAILS': '#E67E22',
  'HAS_INSTITUTION': '#1ABC9C',
  'HAS_PARTNERSHIPS': '#34495E',
  'HAS_SCHOLARSHIPS': '#F1C40F',
  'Default': '#BDC3C7'
};

function GraphCanvas({ graphData }) {
  const navigate = useNavigate();
  const fgRef = useRef();

  useEffect(() => {
    if (fgRef.current && graphData.nodes.length > 0) {
      fgRef.current.zoomToFit(400, 50);
    }
  }, [graphData]);

  const handleNodeClick = (node) => {
    navigate(`/entity/${encodeURIComponent(node.id)}`);
  };

  const getNodeColor = (node) => {
    return NODE_COLORS[node.label] || NODE_COLORS.Default;
  };

  const getLinkColor = (link) => {
    return LINK_COLORS[link.type] || LINK_COLORS.Default;
  };

  return (
    <div className="graph-canvas-container">
      <div className="graph-canvas">
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          nodeLabel={(node) => `${node.name} (${node.label})`}
          nodeColor={getNodeColor}
          nodeRelSize={6}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const label = node.name;
            const fontSize = 12/globalScale;
            ctx.font = `${fontSize}px Sans-Serif`;
            const textWidth = ctx.measureText(label).width;
            const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);

            // Draw node circle
            ctx.fillStyle = getNodeColor(node);
            ctx.beginPath();
            ctx.arc(node.x, node.y, 6, 0, 2 * Math.PI, false);
            ctx.fill();

            // Draw label background
            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y + 8, bckgDimensions[0], bckgDimensions[1]);

            // Draw label text
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillStyle = '#333';
            ctx.fillText(label, node.x, node.y + 10);
          }}
          linkLabel={(link) => link.type}
          linkColor={getLinkColor}
          linkWidth={2}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          onNodeClick={handleNodeClick}
          cooldownTicks={100}
          onEngineStop={() => fgRef.current?.zoomToFit(400, 50)}
        />
      </div>

      <div className="graph-legend">
        <h4>Legend</h4>
        <div className="legend-section">
          <h5>Node Labels</h5>
          {Object.entries(NODE_COLORS).filter(([key]) => key !== 'Default').map(([label, color]) => (
            <div key={label} className="legend-item">
              <span className="legend-color" style={{ backgroundColor: color }}></span>
              <span>{label}</span>
            </div>
          ))}
        </div>
        <div className="legend-section">
          <h5>Relationship Types</h5>
          {Object.entries(LINK_COLORS).filter(([key]) => key !== 'Default').map(([type, color]) => (
            <div key={type} className="legend-item">
              <span className="legend-color" style={{ backgroundColor: color }}></span>
              <span>{type}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default GraphCanvas;
