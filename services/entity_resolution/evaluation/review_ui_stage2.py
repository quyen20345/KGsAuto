from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _to_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def write_cluster_dashboard(stage_dir: Path, enriched_rows: list[dict[str, Any]], metrics: dict[str, Any] | None = None) -> Path:
    out = stage_dir / "cluster_dashboard.html"

    # Build metrics HTML section
    metrics_html = ""
    if metrics:
        sil = metrics.get("silhouette_score")
        sil_display = f"{sil:.3f}" if sil is not None else "N/A"

        # Color code silhouette score
        if sil is not None:
            if sil > 0.5:
                sil_color = "#10b981"  # green
            elif sil > 0.3:
                sil_color = "#f59e0b"  # orange
            else:
                sil_color = "#ef4444"  # red
        else:
            sil_color = "#6b7280"  # gray

        metrics_html = f"""
        <div class="panel">
          <h2 style="margin: 0 0 12px; font-size: 18px;">Cluster Quality Metrics</h2>
          <div class="stats">
            <div class="stat">
              <div class="muted" style="font-size: 12px;">Silhouette Score</div>
              <div style="font-size: 28px; color: {sil_color}; font-weight: bold; margin: 4px 0;">{sil_display}</div>
              <div class="muted" style="font-size: 11px;">-1 (worst) to 1 (best)</div>
            </div>
            <div class="stat">
              <div class="muted" style="font-size: 12px;">Clusters</div>
              <div style="font-size: 28px; font-weight: bold; margin: 4px 0;">{metrics.get('num_clusters', 0)}</div>
              <div class="muted" style="font-size: 11px;">Non-noise clusters</div>
            </div>
            <div class="stat">
              <div class="muted" style="font-size: 12px;">Noise Points</div>
              <div style="font-size: 28px; font-weight: bold; margin: 4px 0;">{metrics.get('num_noise', 0)}</div>
              <div class="muted" style="font-size: 11px;">Outliers</div>
            </div>
            <div class="stat">
              <div class="muted" style="font-size: 12px;">Avg Cluster Size</div>
              <div style="font-size: 28px; font-weight: bold; margin: 4px 0;">{metrics.get('avg_cluster_size', 0):.1f}</div>
              <div class="muted" style="font-size: 11px;">Mean entities/cluster</div>
            </div>
            <div class="stat">
              <div class="muted" style="font-size: 12px;">Size Range</div>
              <div style="font-size: 20px; font-weight: bold; margin: 4px 0;">{metrics.get('min_cluster_size', 0)} - {metrics.get('max_cluster_size', 0)}</div>
              <div class="muted" style="font-size: 11px;">Min - Max</div>
            </div>
          </div>
          <div style="margin-top: 12px; padding: 12px; background: #eff6ff; border-radius: 8px; font-size: 13px; line-height: 1.6;">
            <b>📊 Interpretation Guide:</b>
            <ul style="margin: 8px 0; padding-left: 20px;">
              <li><b>Silhouette > 0.5:</b> Good clustering - entities are well-separated</li>
              <li><b>Silhouette 0.3-0.5:</b> Acceptable clustering - some overlap exists</li>
              <li><b>Silhouette < 0.3:</b> Poor clustering - consider tuning parameters or using semantic embeddings</li>
            </ul>
          </div>
        </div>
        """

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Stage2 Cluster Dashboard</title>
  <style>
    :root {{
      --bg: #f6f8fa;
      --card: #ffffff;
      --text: #1b2830;
      --muted: #5f7380;
      --line: #dce5ea;
      --accent: #0a7a72;
      --noise: #9aaab5;
    }}
    body {{ margin: 0; background: var(--bg); color: var(--text); font-family: "IBM Plex Sans", "Segoe UI", sans-serif; }}
    .wrap {{ max-width: 1300px; margin: 0 auto; padding: 20px; }}
    h1 {{ margin: 0 0 10px; font-size: 26px; }}
    .panel {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px; margin-bottom: 14px; }}
    .muted {{ color: var(--muted); }}
    .row {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-top: 8px; }}
    input, select {{ border: 1px solid var(--line); border-radius: 8px; padding: 6px 8px; font-size: 13px; }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; }}
    .stat {{ background: #f8fcfd; border: 1px solid var(--line); border-radius: 10px; padding: 10px; }}
    .clusters {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 10px; }}
    .cluster {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 12px; }}
    .cluster.noise {{ border-style: dashed; border-color: var(--noise); }}
    .head {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 8px; }}
    .badge {{ font-size: 11px; background: #e7f4f2; color: var(--accent); padding: 2px 8px; border-radius: 999px; }}
    .item {{ border-top: 1px solid var(--line); padding-top: 6px; margin-top: 6px; font-size: 13px; }}
    .kv b {{ min-width: 85px; display: inline-block; color: var(--muted); }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>Stage2 Cluster Dashboard</h1>
    <div class=\"muted\">Inspect cluster assignments, filter by type, and identify noise candidates.</div>

    {metrics_html}

    <div class=\"panel\">
      <div class=\"stats\" id=\"stats\"></div>
      <div class=\"row\">
        <label>Search node/name <input id=\"q\" type=\"text\" placeholder=\"node_id or name\" /></label>
        <label>Primary type
          <select id=\"ptype\">
            <option value=\"ALL\">ALL</option>
          </select>
        </label>
        <label>Min cluster size <input id=\"minsize\" type=\"number\" min=\"1\" value=\"1\" /></label>
        <label><input id=\"show-noise\" type=\"checkbox\" checked /> Show noise</label>
      </div>
    </div>

    <div class=\"clusters\" id=\"clusters\"></div>
  </div>

  <script id=\"rows-data\" type=\"application/json\">{_to_json(enriched_rows)}</script>
  <script>
    const rows = JSON.parse(document.getElementById('rows-data').textContent || '[]');
    const clustersRoot = document.getElementById('clusters');
    const statsRoot = document.getElementById('stats');
    const qInput = document.getElementById('q');
    const ptypeSelect = document.getElementById('ptype');
    const minSizeInput = document.getElementById('minsize');
    const showNoiseInput = document.getElementById('show-noise');

    const byType = [...new Set(rows.map(x => x.primary_type || 'UNKNOWN'))].sort();
    for (const t of byType) {{
      const opt = document.createElement('option');
      opt.value = t;
      opt.textContent = t;
      ptypeSelect.appendChild(opt);
    }}

    function grouped(inputRows) {{
      const m = new Map();
      for (const r of inputRows) {{
        const key = r.cluster_id || 'noise';
        if (!m.has(key)) m.set(key, []);
        m.get(key).push(r);
      }}
      return m;
    }}

    function render() {{
      const q = (qInput.value || '').toLowerCase().trim();
      const ptype = ptypeSelect.value;
      const minSize = Number(minSizeInput.value || 1);
      const showNoise = showNoiseInput.checked;

      const filtered = rows.filter(r => {{
        if (ptype !== 'ALL' && (r.primary_type || 'UNKNOWN') !== ptype) return false;
        if (!showNoise && r.cluster_id === 'noise') return false;
        if (!q) return true;
        const hay = `${{r.node_id || ''}} ${{r.node_name || ''}}`.toLowerCase();
        return hay.includes(q);
      }});

      const groups = grouped(filtered);
      const clusterEntries = [...groups.entries()]
        .filter(([cid, nodes]) => cid === 'noise' || nodes.length >= minSize)
        .sort((a, b) => b[1].length - a[1].length);

      const totalNodes = filtered.length;
      const noiseNodes = filtered.filter(x => x.cluster_id === 'noise').length;
      const realClusters = clusterEntries.filter(x => x[0] !== 'noise').length;

      statsRoot.innerHTML = `
        <div class=\"stat\"><b>Total rows</b><div>${{totalNodes}}</div></div>
        <div class=\"stat\"><b>Clusters</b><div>${{realClusters}}</div></div>
        <div class=\"stat\"><b>Noise rows</b><div>${{noiseNodes}}</div></div>
        <div class=\"stat\"><b>Primary types</b><div>${{byType.length}}</div></div>
      `;

      clustersRoot.innerHTML = '';
      for (const [cid, nodes] of clusterEntries) {{
        const isNoise = cid === 'noise';
        const card = document.createElement('div');
        card.className = `cluster ${{isNoise ? 'noise' : ''}}`;
        card.innerHTML = `
          <div class=\"head\">
            <b>${{cid}}</b>
            <span class=\"badge\">size=${{nodes.length}}</span>
          </div>
          <div class=\"muted\">primary types: ${{[...new Set(nodes.map(x => x.primary_type || 'UNKNOWN'))].join(', ')}}</div>
          <div>${{nodes.map(n => `
            <div class=\"item\">
              <div class=\"kv\"><b>node_id</b> ${{n.node_id}}</div>
              <div class=\"kv\"><b>name</b> ${{n.node_name || ''}}</div>
              <div class=\"kv\"><b>labels</b> ${{(n.labels || []).join(', ')}}</div>
              <div class=\"kv\"><b>source</b> ${{n.source_file || ''}}</div>
              <div class=\"kv\"><b>prob</b> ${{Number(n.probability || 0).toFixed(3)}}</div>
            </div>
          `).join('')}}</div>
        `;
        clustersRoot.appendChild(card);
      }}
    }}

    qInput.addEventListener('input', render);
    ptypeSelect.addEventListener('change', render);
    minSizeInput.addEventListener('input', render);
    showNoiseInput.addEventListener('change', render);

    render();
  </script>
</body>
</html>
"""

    out.write_text(html, encoding="utf-8")
    return out
