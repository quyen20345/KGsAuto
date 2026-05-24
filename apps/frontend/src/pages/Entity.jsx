import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import EntityLink from '../components/EntityLink';
import RelationshipTooltip from '../components/RelationshipTooltip';
import CompareModal from '../components/CompareModal';
import EmptyState from '../components/EmptyState';
import { useToast } from '../context/ToastContext';
import { useBreadcrumb } from '../context/BreadcrumbContext';
import ExpandableText from '../components/ExpandableText';

export default function Entity() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { setBreadcrumbs, setHeaderExtra } = useBreadcrumb();
  const [entityState, setEntityState] = useState({
    id: null,
    entity: null,
    error: false,
  });
  const [duplicates, setDuplicates] = useState([]);
  const [loadingDuplicates, setLoadingDuplicates] = useState(false);
  const [duplicateSearchQuery, setDuplicateSearchQuery] = useState('');
  const [duplicateSearchResults, setDuplicateSearchResults] = useState([]);
  const [duplicateSearchLoading, setDuplicateSearchLoading] = useState(false);
  const [duplicateSearchError, setDuplicateSearchError] = useState(null);
  const [compareTarget, setCompareTarget] = useState(null);

  // States for Ego-Network Explorer
  const [nodeLimit, setNodeLimit] = useState(15);
  const [neighborDepth, setNeighborDepth] = useState(2);

  const loading = entityState.id !== id && !entityState.error;
  const entity = entityState.id === id ? entityState.entity : null;

  useEffect(() => {
    if (entity) {
      setBreadcrumbs([
        { label: 'Home', link: '/' },
        { label: 'Entity', link: null },
        { label: entity.name || entity.id, link: null }
      ]);
    } else {
      setBreadcrumbs([
        { label: 'Home', link: '/' },
        { label: 'Entity', link: null },
        { label: id, link: null }
      ]);
    }
  }, [entity, id, setBreadcrumbs]);

  useEffect(() => {
    if (entity) {
      setHeaderExtra(<GraphExplorerPopover entity={entity} />);
    } else {
      setHeaderExtra(null);
    }
    return () => setHeaderExtra(null);
  }, [entity, setHeaderExtra]);

  useEffect(() => {
    api.getEntity(id)
      .then((data) => {
        setEntityState({ id, entity: data, error: false });
      })
      .catch(() => {
        setEntityState({ id, entity: null, error: true });
      });
  }, [id]);

  useEffect(() => {
    if (!entity?.name) return;

    setLoadingDuplicates(true);
    api.searchLexical(entity.name, 10, null)
      .then((results) => {
        const filtered = results.filter(r => r.id !== entity.id).slice(0, 5);
        setDuplicates(filtered);
        setLoadingDuplicates(false);
      })
      .catch(() => {
        setDuplicates([]);
        setLoadingDuplicates(false);
      });
  }, [entity]);

  const handleDuplicateSearch = (event) => {
    event.preventDefault();
    const query = duplicateSearchQuery.trim();
    if (!query) {
      setDuplicateSearchResults([]);
      setDuplicateSearchError(null);
      return;
    }

    setDuplicateSearchLoading(true);
    setDuplicateSearchError(null);
    api.searchLexical(query, 10, null)
      .then((results) => {
        const filtered = Array.isArray(results)
          ? results.filter(r => r.id !== entity.id)
          : [];
        setDuplicateSearchResults(filtered);
        setDuplicateSearchLoading(false);
      })
      .catch((error) => {
        setDuplicateSearchResults([]);
        setDuplicateSearchError(error?.message || 'Search failed.');
        setDuplicateSearchLoading(false);
      });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    showToast(`Đã sao chép: ${text}`, 'success');
  };

  const handleMergeComplete = (canonicalId) => {
    setCompareTarget(null);
    showToast('Gộp thực thể thành công!', 'success');
    navigate(`/entity/${encodeURIComponent(canonicalId)}`);
    if (canonicalId === entity.id) {
      window.location.reload();
    }
  };

  if (loading) return <main><div>Loading entity...</div></main>;
  if (!entity || entity.error) return (
    <main>
      <EmptyState 
        icon="🔍"
        title="Không tìm thấy thực thể"
        description="Thực thể bạn đang tìm kiếm không tồn tại hoặc đã bị xóa."
        action={
          <button className="btn-primary" onClick={() => navigate('/')}>
            Quay lại trang chủ
          </button>
        }
      />
    </main>
  );

  const outGroups = entity.outgoing.reduce((acc, rel) => {
    acc[rel.type] = acc[rel.type] || [];
    acc[rel.type].push(rel);
    return acc;
  }, {});

  return (
    <main>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap', gap: '20px', marginBottom: '20px' }}>
        <h1 className="entity-title" style={{ margin: 0, textAlign: 'center' }}>{entity.name || entity.id}</h1>
      </div>

      <table>
        <tbody>
          {Object.entries(outGroups).map(([type, rels]) => {
            return (
              <tr key={`out-${type}`}>
                <td className="predicate">
                  <ExpandableText text={`rel:${type}`} maxLength={40} />
                </td>
                <td className="object">
                  {rels.map((r, i) => {
                    const relDescription = r.properties?.description;
                    const relDescriptionText = Array.isArray(relDescription)
                      ? relDescription[0]
                      : relDescription;

                    return (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: i < rels.length - 1 ? '4px' : '0' }}>
                        <RelationshipTooltip
                          relationshipType={type}
                          description={relDescriptionText}
                        >
                          <span className="relationship-dot">•</span>
                        </RelationshipTooltip>
                        <EntityLink entityId={r.target_id}>
                          {r.target_name || r.target_id}
                        </EntityLink>
                      </div>
                    );
                  })}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="statements-header" style={{ marginTop: '40px', textAlign: 'center' }}>Possible Duplicates</div>
      <form onSubmit={handleDuplicateSearch} style={{ marginTop: '12px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <input
            className="merge-input"
            type="text"
            value={duplicateSearchQuery}
            onChange={(event) => setDuplicateSearchQuery(event.target.value)}
            placeholder="Search entities to compare, e.g. UET"
            style={{ flex: 1 }}
          />
          <button className="merge-button" type="submit" disabled={duplicateSearchLoading}>
            Search
          </button>
        </div>
      </form>
      {duplicateSearchLoading && <div style={{ padding: '10px', color: '#666' }}>Searching entities...</div>}
      {duplicateSearchError && <div className="merge-box merge-error">{duplicateSearchError}</div>}
      {!duplicateSearchLoading && duplicateSearchResults.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {duplicateSearchResults.map((dup) => (
            <li key={dup.id} style={{ 
              marginBottom: '16px', 
              padding: '16px', 
              border: '1px solid var(--border)', 
              borderRadius: '8px', 
              background: 'var(--bg-surface)', 
              boxShadow: 'var(--shadow-sm)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}>
              {/* Row 1: Entity Name Link */}
              <div style={{ minWidth: 0 }}>
                <EntityLink entityId={dup.id}>
                  <strong style={{ fontSize: '1.05rem', color: 'var(--text)' }}>{dup.name || dup.id}</strong>
                </EntityLink>
              </div>

              {/* Row 2: Badges (as clean metadata) on left, buttons on right */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                {/* Metadata Line */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ 
                    color: 'var(--text-light)', 
                    fontSize: '0.75rem', 
                    fontWeight: '600',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    {dup.labels?.[0] || 'Unknown'}
                  </span>
                  {typeof dup.score === 'number' && (
                    <span style={{ color: 'var(--border)', fontSize: '0.75rem' }}>•</span>
                  )}
                  {typeof dup.score === 'number' && (
                    <span style={{ 
                      color: '#059669', 
                      fontSize: '0.75rem', 
                      fontWeight: '600'
                    }}>
                      {Math.round(dup.score * 100)}% match
                    </span>
                  )}
                </div>

                {/* Buttons (pushed to the right) */}
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    style={{
                      padding: '4px 10px',
                      fontSize: '0.8rem',
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border)',
                      borderRadius: '6px',
                      color: 'var(--text-light)',
                      cursor: 'pointer',
                      fontWeight: '500',
                      transition: 'var(--transition)'
                    }}
                    onClick={() => copyToClipboard(dup.id)}
                    onMouseOver={(e) => { e.currentTarget.style.background = 'var(--bg)'; e.currentTarget.style.color = 'var(--text)'; }}
                    onMouseOut={(e) => { e.currentTarget.style.background = 'var(--bg-surface)'; e.currentTarget.style.color = 'var(--text-light)'; }}
                  >
                    Copy ID
                  </button>
                  <button
                    style={{
                      padding: '4px 10px',
                      fontSize: '0.8rem',
                      background: 'var(--bg-surface)',
                      border: '1px solid #BFDBFE',
                      borderRadius: '6px',
                      color: '#2563eb',
                      cursor: 'pointer',
                      fontWeight: '600',
                      transition: 'var(--transition)'
                    }}
                    onClick={() => setCompareTarget(dup.id)}
                    onMouseOver={(e) => { e.currentTarget.style.background = 'var(--bg)'; }}
                    onMouseOut={(e) => { e.currentTarget.style.background = 'var(--bg-surface)'; }}
                  >
                    Compare
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
      {loadingDuplicates && <div style={{ padding: '10px', color: '#666' }}>Searching for duplicates...</div>}
      {!loadingDuplicates && duplicates.length === 0 && (
        <div style={{ padding: '10px', color: '#666' }}>No potential duplicates found</div>
      )}
      {!loadingDuplicates && duplicates.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {duplicates.map((dup) => (
            <li key={dup.id} style={{ 
              marginBottom: '16px', 
              padding: '16px', 
              border: '1px solid var(--border)', 
              borderRadius: '8px', 
              background: 'var(--bg-surface)', 
              boxShadow: 'var(--shadow-sm)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}>
              {/* Row 1: Entity Name Link */}
              <div style={{ minWidth: 0 }}>
                <EntityLink entityId={dup.id}>
                  <strong style={{ fontSize: '1.05rem', color: 'var(--text)' }}>{dup.name || dup.id}</strong>
                </EntityLink>
              </div>

              {/* Row 2: Badges (as clean metadata) on left, buttons on right */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                {/* Metadata Line */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ 
                    color: 'var(--text-light)', 
                    fontSize: '0.75rem', 
                    fontWeight: '600',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    {dup.labels?.[0] || 'Unknown'}
                  </span>
                  {typeof dup.score === 'number' && (
                    <span style={{ color: 'var(--border)', fontSize: '0.75rem' }}>•</span>
                  )}
                  {typeof dup.score === 'number' && (
                    <span style={{ 
                      color: '#059669', 
                      fontSize: '0.75rem', 
                      fontWeight: '600'
                    }}>
                      {Math.round(dup.score * 100)}% match
                    </span>
                  )}
                </div>

                {/* Buttons (pushed to the right) */}
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    style={{
                      padding: '4px 10px',
                      fontSize: '0.8rem',
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border)',
                      borderRadius: '6px',
                      color: 'var(--text-light)',
                      cursor: 'pointer',
                      fontWeight: '500',
                      transition: 'var(--transition)'
                    }}
                    onClick={() => copyToClipboard(dup.id)}
                    onMouseOver={(e) => { e.currentTarget.style.background = 'var(--bg)'; e.currentTarget.style.color = 'var(--text)'; }}
                    onMouseOut={(e) => { e.currentTarget.style.background = 'var(--bg-surface)'; e.currentTarget.style.color = 'var(--text-light)'; }}
                  >
                    Copy ID
                  </button>
                  <button
                    style={{
                      padding: '4px 10px',
                      fontSize: '0.8rem',
                      background: 'var(--bg-surface)',
                      border: '1px solid #BFDBFE',
                      borderRadius: '6px',
                      color: '#2563eb',
                      cursor: 'pointer',
                      fontWeight: '600',
                      transition: 'var(--transition)'
                    }}
                    onClick={() => setCompareTarget(dup.id)}
                    onMouseOver={(e) => { e.currentTarget.style.background = 'var(--bg)'; }}
                    onMouseOut={(e) => { e.currentTarget.style.background = 'var(--bg-surface)'; }}
                  >
                    Compare
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <CompareModal
        isOpen={!!compareTarget}
        onClose={() => setCompareTarget(null)}
        entityA={entity}
        duplicateId={compareTarget}
        onMergeComplete={handleMergeComplete}
      />
    </main>
  );
}

function GraphExplorerPopover({ entity }) {
  const [isOpen, setIsOpen] = useState(false);
  const [neighborDepth, setNeighborDepth] = useState(2);
  const [nodeLimit, setNodeLimit] = useState(15);
  const popoverRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleOutsideClick = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isOpen]);

  const neo4jUrl = `http://localhost:7474/browser/?cmd=edit&arg=${encodeURIComponent(
    `MATCH (target) WHERE target.id = '${entity.id}' MATCH (target)-[*1..${neighborDepth}]-(neighbor) RETURN DISTINCT neighbor, target LIMIT ${nodeLimit}`
  )}`;

  return (
    <div style={{ position: 'relative', display: 'inline-block' }} ref={popoverRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: 'none',
          border: 'none',
          color: 'var(--primary)',
          cursor: 'pointer',
          fontWeight: '600',
          fontSize: '0.85rem',
          padding: '6px 12px',
          borderRadius: '4px',
          transition: 'background 0.2s',
          outline: 'none',
        }}
        onMouseOver={(e) => (e.currentTarget.style.background = 'rgba(37, 99, 235, 0.08)')}
        onMouseOut={(e) => (e.currentTarget.style.background = 'none')}
      >
        <span>🎯 Hiển thị graph</span>
        <span style={{ fontSize: '0.7rem', transition: 'transform 0.2s', transform: isOpen ? 'rotate(180deg)' : 'none' }}>▼</span>
      </button>

      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            boxShadow: 'var(--shadow-lg)',
            padding: '16px',
            width: '240px',
            zIndex: 999,
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ fontWeight: '600', fontSize: '0.85rem', color: 'var(--text)', borderBottom: '1px solid var(--border)', paddingBottom: '6px', marginBottom: '2px', textAlign: 'left' }}>
            Thông số Graph
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-start' }}>
            <label style={{ fontSize: '0.8rem', color: '#555', fontWeight: '500' }}>Bước nhảy (Độ sâu):</label>
            <select
              value={neighborDepth}
              onChange={(e) => setNeighborDepth(parseInt(e.target.value))}
              style={{
                width: '100%',
                padding: '6px 8px',
                borderRadius: '4px',
                border: '1px solid var(--border)',
                fontSize: '0.8rem',
                outline: 'none',
                background: 'var(--bg-surface)',
              }}
            >
              <option value={1}>1 bước</option>
              <option value={2}>2 bước</option>
              <option value={3}>3 bước</option>
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-start' }}>
            <label style={{ fontSize: '0.8rem', color: '#555', fontWeight: '500' }}>Giới hạn node:</label>
            <input
              type="number"
              value={nodeLimit}
              onChange={(e) => setNodeLimit(Math.max(1, parseInt(e.target.value) || 1))}
              style={{
                width: '100%',
                padding: '6px 8px',
                borderRadius: '4px',
                border: '1px solid var(--border)',
                fontSize: '0.8rem',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <a
            href={neo4jUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setIsOpen(false)}
            style={{
              textDecoration: 'none',
              fontSize: '0.8rem',
              padding: '8px 12px',
              borderRadius: '4px',
              background: 'var(--primary)',
              color: 'white',
              fontWeight: '600',
              textAlign: 'center',
              display: 'block',
              marginTop: '4px',
              transition: 'opacity 0.2s',
            }}
            onMouseOver={(e) => (e.currentTarget.style.opacity = 0.9)}
            onMouseOut={(e) => (e.currentTarget.style.opacity = 1)}
          >
            Mở trong Neo4j 🌐
          </a>
        </div>
      )}
    </div>
  );
}
