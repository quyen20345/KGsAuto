#!/usr/bin/env python3
"""Generate HTML Q&A viewers for evaluation JSONL files.

Creates one self-contained HTML file per evaluation mode,
showing questions, answers, and the full retrieval/reasoning process.
"""

import json
import html as html_module
from pathlib import Path

EVAL_DIR = Path(__file__).parent.parent / "data" / "evaluation"
OUTPUT_DIR = EVAL_DIR

MODES = ["semantic_search", "naive_grag", "graph_search", "hybrid"]
MODE_LABELS = {
    "semantic_search": "Semantic Search",
    "naive_grag": "Naive GraphRAG",
    "graph_search": "Graph Search",
    "hybrid": "Hybrid",
}
MODE_ICONS = {
    "semantic_search": "🔍",
    "naive_grag": "🧠",
    "graph_search": "🕸️",
    "hybrid": "⚡",
}
MODE_DESCRIPTIONS = {
    "semantic_search": "Vector similarity search over document chunks",
    "naive_grag": "Knowledge Graph entities + relationships + document chunks",
    "graph_search": "Pure Knowledge Graph traversal search",
    "hybrid": "Combined KG + Semantic Search",
}


def read_jsonl(filepath: Path) -> list[dict]:
    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def extract_semantic_data(entry: dict) -> dict:
    """Extract viewer data from semantic_search entry."""
    retrieval = entry.get("retrieval_evidence", {})
    chunks = retrieval.get("markdown_chunks", [])

    return {
        "id": entry.get("id", ""),
        "question": entry.get("question", ""),
        "reference": entry.get("reference", ""),
        "answer": entry.get("answer", ""),
        "tags": entry.get("tags", []),
        "chunks": [
            {
                "chunk_id": c.get("chunk_id", ""),
                "text": c.get("text", ""),
                "score": round(c.get("score", 0), 4),
                "rank": c.get("metadata", {}).get("rank", 0),
            }
            for c in chunks
        ],
    }


def extract_kg_data(entry: dict) -> dict:
    """Extract viewer data from KG-based entry."""
    retrieval_evidence = entry.get("retrieval_evidence", [])

    entities = []
    relationships = []
    document_chunks = []
    sources = []

    if isinstance(retrieval_evidence, list) and len(retrieval_evidence) > 0:
        ev = retrieval_evidence[0]
        ctx = ev.get("context_structured", {})
        if ctx:
            entities = ctx.get("entities", [])
            relationships = ctx.get("relationships", [])
            document_chunks = ctx.get("document_chunks", [])
            sources = ctx.get("sources", [])

    return {
        "id": entry.get("id", ""),
        "question": entry.get("question", ""),
        "reference": entry.get("reference", ""),
        "answer": entry.get("answer", ""),
        "tags": entry.get("tags", []),
        "entities": [
            {
                "name": e.get("entity_name", ""),
                "type": e.get("entity_type", ""),
                "description": e.get("description", ""),
                "score": e.get("retrieval_score", 0),
                "aliases": e.get("aliases", []),
            }
            for e in entities
        ],
        "relationships": [
            {
                "src": r.get("src_id", ""),
                "tgt": r.get("tgt_id", ""),
                "keywords": r.get("keywords", ""),
                "description": r.get("description", ""),
            }
            for r in relationships
        ],
        "chunks": [
            {
                "chunk_id": c.get("chunk_id", ""),
                "content": c.get("content", ""),
                "score": round(c.get("score", 0), 4) if c.get("score") else 0,
            }
            for c in document_chunks
        ],
        "sources": sources,
    }


def get_html_template(mode: str, data_json: str) -> str:
    """Generate the full HTML page for a mode."""
    label = MODE_LABELS[mode]
    icon = MODE_ICONS[mode]
    desc = MODE_DESCRIPTIONS[mode]
    is_kg = mode != "semantic_search"

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{label} — Q&A Viewer</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#0f1117;--bg-card:#1a1d27;--bg-card-hover:#1e2130;--bg-section:#141620;
  --bg-code:#0d0f16;--bg-highlight:#252a3a;
  --text:#e4e6ed;--text-dim:#8b8fa3;--text-muted:#5c5f72;
  --accent:#6c8aff;--accent-dim:#4a63c9;--accent-glow:rgba(108,138,255,0.1);
  --green:#4ade80;--green-dim:rgba(74,222,128,0.12);
  --amber:#fbbf24;--amber-dim:rgba(251,191,36,0.12);
  --purple:#a78bfa;--purple-dim:rgba(167,139,250,0.12);
  --cyan:#22d3ee;--cyan-dim:rgba(34,211,238,0.12);
  --red:#f87171;--red-dim:rgba(248,113,113,0.12);
  --border:#2a2d3a;--border-light:#353849;
  --radius:12px;--radius-sm:8px;--radius-xs:6px;
  --shadow:0 4px 24px rgba(0,0,0,0.3);
  --transition:0.2s cubic-bezier(0.4,0,0.2,1);
}}
html{{scroll-behavior:smooth}}
body{{
  font-family:'Inter',system-ui,-apple-system,sans-serif;
  background:var(--bg);color:var(--text);
  line-height:1.6;min-height:100vh;
}}
/* HEADER */
.header{{
  position:sticky;top:0;z-index:100;
  background:rgba(15,17,23,0.85);backdrop-filter:blur(20px);
  border-bottom:1px solid var(--border);
  padding:16px 32px;
  display:flex;align-items:center;gap:20px;flex-wrap:wrap;
}}
.header-title{{
  display:flex;align-items:center;gap:12px;
  font-size:20px;font-weight:700;white-space:nowrap;
}}
.header-title .icon{{font-size:28px}}
.header-desc{{color:var(--text-dim);font-size:13px;flex:1;min-width:200px}}
.header-count{{
  background:var(--accent-glow);border:1px solid var(--accent-dim);
  color:var(--accent);padding:6px 14px;border-radius:20px;
  font-size:13px;font-weight:600;white-space:nowrap;
}}
.search-box{{
  display:flex;align-items:center;gap:8px;
  background:var(--bg-card);border:1px solid var(--border);
  border-radius:var(--radius-sm);padding:8px 14px;
  min-width:280px;
}}
.search-box svg{{color:var(--text-muted);flex-shrink:0}}
.search-box input{{
  background:none;border:none;outline:none;color:var(--text);
  font-size:14px;width:100%;font-family:inherit;
}}
.search-box input::placeholder{{color:var(--text-muted)}}
/* MAIN */
.main{{max-width:1200px;margin:0 auto;padding:24px 32px 80px}}
/* QA CARD */
.qa-card{{
  background:var(--bg-card);border:1px solid var(--border);
  border-radius:var(--radius);margin-bottom:16px;
  overflow:hidden;transition:border-color var(--transition);
}}
.qa-card:hover{{border-color:var(--border-light)}}
.qa-card.expanded{{border-color:var(--accent-dim)}}
.qa-header{{
  padding:20px 24px;cursor:pointer;
  display:flex;align-items:flex-start;gap:16px;
  transition:background var(--transition);
}}
.qa-header:hover{{background:var(--bg-card-hover)}}
.qa-num{{
  background:var(--accent-glow);border:1px solid var(--accent-dim);
  color:var(--accent);min-width:40px;height:40px;
  border-radius:var(--radius-xs);font-size:14px;font-weight:700;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
}}
.qa-question{{flex:1;font-size:15px;font-weight:500;line-height:1.5}}
.qa-toggle{{
  color:var(--text-muted);transition:transform var(--transition);
  flex-shrink:0;margin-top:4px;
}}
.qa-card.expanded .qa-toggle{{transform:rotate(180deg)}}
.qa-tags{{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}}
.qa-tag{{
  font-size:11px;padding:2px 8px;border-radius:10px;
  background:var(--bg-highlight);color:var(--text-dim);
}}
/* QA BODY */
.qa-body{{
  display:none;border-top:1px solid var(--border);
}}
.qa-card.expanded .qa-body{{display:block}}
/* SECTION */
.section{{padding:20px 24px;border-bottom:1px solid var(--border)}}
.section:last-child{{border-bottom:none}}
.section-label{{
  display:flex;align-items:center;gap:8px;
  font-size:12px;font-weight:700;text-transform:uppercase;
  letter-spacing:0.08em;margin-bottom:12px;
}}
.section-label .dot{{
  width:8px;height:8px;border-radius:50%;flex-shrink:0;
}}
.section-label.reference .dot{{background:var(--green)}}
.section-label.answer .dot{{background:var(--accent)}}
.section-label.entities .dot{{background:var(--purple)}}
.section-label.relationships .dot{{background:var(--amber)}}
.section-label.chunks .dot{{background:var(--cyan)}}
.section-content{{
  font-size:14px;line-height:1.7;color:var(--text);
  white-space:pre-wrap;word-break:break-word;
}}
.section-content.dim{{color:var(--text-dim)}}
/* COLLAPSIBLE */
.collapsible-header{{
  cursor:pointer;display:flex;align-items:center;gap:8px;
  user-select:none;
}}
.collapsible-header .arrow{{
  color:var(--text-muted);transition:transform var(--transition);
  font-size:12px;
}}
.collapsible.open .collapsible-header .arrow{{transform:rotate(90deg)}}
.collapsible-body{{display:none;margin-top:12px}}
.collapsible.open .collapsible-body{{display:block}}
/* ENTITY CARD */
.entity-grid{{display:flex;flex-direction:column;gap:10px}}
.entity-card{{
  background:var(--bg-section);border:1px solid var(--border);
  border-radius:var(--radius-sm);padding:14px 16px;
}}
.entity-name{{
  font-weight:600;font-size:14px;color:var(--purple);
  display:flex;align-items:center;gap:8px;
}}
.entity-type{{
  font-size:11px;padding:2px 8px;border-radius:10px;
  background:var(--purple-dim);color:var(--purple);font-weight:500;
}}
.entity-desc{{font-size:13px;color:var(--text-dim);margin-top:6px;line-height:1.5}}
.entity-aliases{{font-size:12px;color:var(--text-muted);margin-top:4px;font-style:italic}}
/* RELATIONSHIP */
.rel-grid{{display:flex;flex-direction:column;gap:8px}}
.rel-card{{
  background:var(--bg-section);border:1px solid var(--border);
  border-radius:var(--radius-sm);padding:12px 16px;
}}
.rel-flow{{
  display:flex;align-items:center;gap:8px;flex-wrap:wrap;
  font-size:13px;font-weight:500;
}}
.rel-node{{
  background:var(--purple-dim);color:var(--purple);
  padding:4px 10px;border-radius:var(--radius-xs);
  max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}}
.rel-edge{{
  background:var(--amber-dim);color:var(--amber);
  padding:4px 10px;border-radius:var(--radius-xs);font-size:11px;
  font-weight:700;text-transform:uppercase;
}}
.rel-arrow{{color:var(--text-muted);font-size:16px}}
.rel-desc{{font-size:12px;color:var(--text-dim);margin-top:6px;line-height:1.4}}
/* CHUNK */
.chunk-grid{{display:flex;flex-direction:column;gap:10px}}
.chunk-card{{
  background:var(--bg-section);border:1px solid var(--border);
  border-radius:var(--radius-sm);overflow:hidden;
}}
.chunk-header{{
  padding:10px 16px;background:var(--bg-highlight);
  display:flex;align-items:center;justify-content:space-between;
  font-size:12px;gap:8px;
}}
.chunk-id{{
  font-family:'JetBrains Mono',monospace;color:var(--cyan);
  font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  flex:1;
}}
.chunk-rank{{
  color:var(--text-muted);font-weight:600;white-space:nowrap;
}}
.chunk-text{{
  padding:14px 16px;font-size:13px;line-height:1.6;
  color:var(--text-dim);white-space:pre-wrap;word-break:break-word;
  max-height:300px;overflow-y:auto;
}}
.chunk-text::-webkit-scrollbar{{width:4px}}
.chunk-text::-webkit-scrollbar-thumb{{background:var(--border-light);border-radius:2px}}
/* NO RESULTS */
.no-results{{
  text-align:center;padding:60px 20px;color:var(--text-muted);
  font-size:15px;
}}
.no-results svg{{margin-bottom:12px;opacity:0.4}}
/* EMPTY */
.empty-note{{
  color:var(--text-muted);font-size:13px;font-style:italic;
  padding:12px 0;
}}
/* BACK TO TOP */
.back-top{{
  position:fixed;bottom:24px;right:24px;
  width:44px;height:44px;border-radius:50%;
  background:var(--accent);color:#fff;border:none;
  cursor:pointer;font-size:18px;
  display:flex;align-items:center;justify-content:center;
  box-shadow:var(--shadow);opacity:0;pointer-events:none;
  transition:opacity var(--transition);z-index:50;
}}
.back-top.visible{{opacity:1;pointer-events:auto}}
.back-top:hover{{background:var(--accent-dim)}}
/* RESPONSIVE */
@media(max-width:768px){{
  .header{{padding:12px 16px;gap:12px}}
  .main{{padding:16px}}
  .search-box{{min-width:100%;order:10}}
  .qa-header{{padding:16px}}
  .section{{padding:16px}}
  .rel-flow{{font-size:12px}}
  .rel-node{{max-width:180px}}
}}
</style>
</head>
<body>

<div class="header">
  <div class="header-title">
    <span class="icon">{icon}</span>
    <span>{label}</span>
  </div>
  <div class="header-desc">{desc}</div>
  <div class="header-count" id="countBadge"></div>
  <div class="search-box">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <input type="text" id="searchInput" placeholder="Tìm kiếm câu hỏi..." autocomplete="off">
  </div>
</div>

<div class="main" id="main"></div>

<button class="back-top" id="backTop" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>

<script>
const DATA = {data_json};
const IS_KG = {'true' if is_kg else 'false'};

function escapeHtml(s) {{
  if (!s) return '';
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}}

function truncate(s, n) {{
  if (!s) return '';
  return s.length > n ? s.slice(0, n) + '…' : s;
}}

function renderChunks(chunks, isKg) {{
  if (!chunks || chunks.length === 0) return '<div class="empty-note">Không có document chunks.</div>';
  return '<div class="chunk-grid">' + chunks.map((c, i) => {{
    const id = c.chunk_id || c.id || ('chunk-' + i);
    const text = isKg ? (c.content || '') : (c.text || '');
    const rank = c.rank || (i + 1);
    return `<div class="chunk-card">
      <div class="chunk-header">
        <span class="chunk-id" title="${{escapeHtml(id)}}">${{escapeHtml(id)}}</span>
        <span class="chunk-rank">#${{rank}}</span>
      </div>
      <div class="chunk-text">${{escapeHtml(text)}}</div>
    </div>`;
  }}).join('') + '</div>';
}}

function renderEntities(entities) {{
  if (!entities || entities.length === 0) return '<div class="empty-note">Không có entities.</div>';
  return '<div class="entity-grid">' + entities.map(e => {{
    const aliases = (e.aliases && e.aliases.length > 0) ? 
      `<div class="entity-aliases">Aliases: ${{e.aliases.map(a => escapeHtml(a)).join(', ')}}</div>` : '';
    return `<div class="entity-card">
      <div class="entity-name">
        ${{escapeHtml(e.name)}}
        <span class="entity-type">${{escapeHtml(e.type)}}</span>
      </div>
      <div class="entity-desc">${{escapeHtml(e.description)}}</div>
      ${{aliases}}
    </div>`;
  }}).join('') + '</div>';
}}

function renderRelationships(rels) {{
  if (!rels || rels.length === 0) return '<div class="empty-note">Không có relationships.</div>';
  return '<div class="rel-grid">' + rels.map(r => {{
    return `<div class="rel-card">
      <div class="rel-flow">
        <span class="rel-node" title="${{escapeHtml(r.src)}}">${{escapeHtml(truncate(r.src, 35))}}</span>
        <span class="rel-arrow">→</span>
        <span class="rel-edge">${{escapeHtml(r.keywords || '?')}}</span>
        <span class="rel-arrow">→</span>
        <span class="rel-node" title="${{escapeHtml(r.tgt)}}">${{escapeHtml(truncate(r.tgt, 35))}}</span>
      </div>
      <div class="rel-desc">${{escapeHtml(r.description)}}</div>
    </div>`;
  }}).join('') + '</div>';
}}

function renderCard(item, index) {{
  const num = index + 1;
  const tags = (item.tags || []).map(t => `<span class="qa-tag">${{escapeHtml(t)}}</span>`).join('');

  let reasoningSections = '';
  if (IS_KG) {{
    const entCount = (item.entities || []).length;
    const relCount = (item.relationships || []).length;
    const chkCount = (item.chunks || []).length;
    reasoningSections = `
      <div class="section">
        <div class="collapsible open" data-group="ent-${{index}}">
          <div class="collapsible-header" onclick="toggleCollapsible(this.parentElement)">
            <div class="section-label entities"><span class="dot"></span>Entities (${{entCount}})</div>
            <span class="arrow">▶</span>
          </div>
          <div class="collapsible-body">${{renderEntities(item.entities)}}</div>
        </div>
      </div>
      <div class="section">
        <div class="collapsible" data-group="rel-${{index}}">
          <div class="collapsible-header" onclick="toggleCollapsible(this.parentElement)">
            <div class="section-label relationships"><span class="dot"></span>Relationships (${{relCount}})</div>
            <span class="arrow">▶</span>
          </div>
          <div class="collapsible-body">${{renderRelationships(item.relationships)}}</div>
        </div>
      </div>
      <div class="section">
        <div class="collapsible" data-group="chk-${{index}}">
          <div class="collapsible-header" onclick="toggleCollapsible(this.parentElement)">
            <div class="section-label chunks"><span class="dot"></span>Document Chunks (${{chkCount}})</div>
            <span class="arrow">▶</span>
          </div>
          <div class="collapsible-body">${{renderChunks(item.chunks, true)}}</div>
        </div>
      </div>`;
  }} else {{
    const chkCount = (item.chunks || []).length;
    reasoningSections = `
      <div class="section">
        <div class="collapsible open" data-group="chk-${{index}}">
          <div class="collapsible-header" onclick="toggleCollapsible(this.parentElement)">
            <div class="section-label chunks"><span class="dot"></span>Retrieved Chunks (${{chkCount}})</div>
            <span class="arrow">▶</span>
          </div>
          <div class="collapsible-body">${{renderChunks(item.chunks, false)}}</div>
        </div>
      </div>`;
  }}

  return `<div class="qa-card" id="qa-${{index}}" data-search="${{escapeHtml(item.question.toLowerCase())}}">
    <div class="qa-header" onclick="toggleCard(${{index}})">
      <div class="qa-num">${{num}}</div>
      <div style="flex:1">
        <div class="qa-question">${{escapeHtml(item.question)}}</div>
        ${{tags ? '<div class="qa-tags">' + tags + '</div>' : ''}}
      </div>
      <svg class="qa-toggle" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
    </div>
    <div class="qa-body">
      <div class="section">
        <div class="section-label reference"><span class="dot"></span>Câu trả lời tham chiếu (Ground Truth)</div>
        <div class="section-content dim">${{escapeHtml(item.reference)}}</div>
      </div>
      <div class="section">
        <div class="section-label answer"><span class="dot"></span>Câu trả lời hệ thống</div>
        <div class="section-content">${{escapeHtml(item.answer)}}</div>
      </div>
      ${{reasoningSections}}
    </div>
  </div>`;
}}

function toggleCard(index) {{
  const card = document.getElementById('qa-' + index);
  card.classList.toggle('expanded');
}}

function toggleCollapsible(el) {{
  el.classList.toggle('open');
}}

function renderAll(data) {{
  const main = document.getElementById('main');
  if (data.length === 0) {{
    main.innerHTML = '<div class="no-results"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg><div>Không tìm thấy kết quả nào.</div></div>';
    return;
  }}
  main.innerHTML = data.map((item, i) => renderCard(item, i)).join('');
}}

// Search
let searchTimeout;
document.getElementById('searchInput').addEventListener('input', function() {{
  clearTimeout(searchTimeout);
  const q = this.value.trim().toLowerCase();
  searchTimeout = setTimeout(() => {{
    const cards = document.querySelectorAll('.qa-card');
    let visible = 0;
    cards.forEach(card => {{
      const text = card.getAttribute('data-search') || '';
      const show = !q || text.includes(q);
      card.style.display = show ? '' : 'none';
      if (show) visible++;
    }});
    document.getElementById('countBadge').textContent = q ? 
      visible + ' / ' + DATA.length + ' câu hỏi' : DATA.length + ' câu hỏi';
  }}, 200);
}});

// Back to top
window.addEventListener('scroll', () => {{
  document.getElementById('backTop').classList.toggle('visible', window.scrollY > 400);
}});

// Init
document.getElementById('countBadge').textContent = DATA.length + ' câu hỏi';
renderAll(DATA);
</script>
</body>
</html>"""


def main():
    for mode in MODES:
        jsonl_path = EVAL_DIR / f"{mode}.jsonl"
        if not jsonl_path.exists():
            print(f"⚠️  Skipping {mode}: {jsonl_path} not found")
            continue

        print(f"📖 Reading {jsonl_path.name}...")
        entries = read_jsonl(jsonl_path)
        print(f"   Found {len(entries)} entries")

        print(f"🔧 Extracting data for {mode}...")
        if mode == "semantic_search":
            data = [extract_semantic_data(e) for e in entries]
        else:
            data = [extract_kg_data(e) for e in entries]

        print(f"📝 Generating HTML...")
        data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        html_content = get_html_template(mode, data_json)

        output_path = OUTPUT_DIR / f"{mode}_viewer.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"✅ {output_path.name} ({size_mb:.1f} MB)")
        print()

    print("🎉 Done! Generated HTML viewers:")
    for mode in MODES:
        p = OUTPUT_DIR / f"{mode}_viewer.html"
        if p.exists():
            print(f"   → {p}")


if __name__ == "__main__":
    main()
