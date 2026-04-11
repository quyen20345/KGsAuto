from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def write_review_dashboard(
    stage_dir: Path,
    cluster_items: list[dict[str, Any]],
    cluster_decisions: list[dict[str, Any]],
    synthesis_items: list[dict[str, Any]],
    synthesis_decisions: list[dict[str, Any]],
) -> Path:
    out = stage_dir / "review_dashboard.html"

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Entity Linking v4 Review Dashboard</title>
  <style>
    :root {{
      --bg: #f4f7f9;
      --card: #ffffff;
      --text: #1a2a33;
      --muted: #5d7382;
      --accent: #0b6c7f;
      --line: #d8e3ea;
      --warn: #9a5a00;
    }}
    body {{ margin: 0; font-family: "IBM Plex Sans", "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 26px; }}
    .muted {{ color: var(--muted); margin-bottom: 16px; }}
    .panel {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 16px; margin-bottom: 16px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 12px; }}
    .cluster {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px; }}
    .head {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; }}
    .badge {{ padding: 2px 8px; border-radius: 999px; background: #e6f3f6; color: var(--accent); font-size: 12px; }}
    .risk {{ color: var(--warn); font-size: 12px; }}
    .kv {{ font-size: 13px; margin-top: 6px; }}
    .kv b {{ display: inline-block; min-width: 120px; }}
    ul {{ margin: 6px 0 0 18px; padding: 0; }}
    li {{ margin: 2px 0; font-size: 13px; }}
    textarea {{ width: 100%; min-height: 180px; font-family: monospace; font-size: 12px; border: 1px solid var(--line); border-radius: 8px; padding: 8px; }}
    button {{ border: 0; background: var(--accent); color: #fff; padding: 8px 12px; border-radius: 8px; cursor: pointer; }}
    .row {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-top: 8px; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>Entity Linking v4 Review Dashboard</h1>
    <div class=\"muted\">Two-pass workflow: (1) validate cluster, (2) approve canonical entity synthesis.</div>

    <div class=\"panel\">
      <b>How to use</b>
      <ol>
        <li>Inspect cluster validation section and export <code>human_cluster_decisions.json</code>.</li>
        <li>Inspect synthesis section and export <code>human_synthesis_decisions.json</code>.</li>
        <li>Place both files in same stage3 folder.</li>
        <li>Run stage3 again with same run_id to apply overrides.</li>
      </ol>
      <div class=\"row\"><b>Cluster Validation JSON</b></div>
      <div class=\"row\">
        <button id=\"build-cluster-template\">Build Template</button>
        <button id=\"promote-merge-hints\">Promote MERGE Hints</button>
        <button id=\"download-cluster-json\">Download human_cluster_decisions.json</button>
      </div>
      <div class=\"row muted\" id=\"cluster-promote-summary\"></div>
      <div class=\"row\">
        <textarea id=\"cluster-editor\"></textarea>
      </div>
      <div class=\"row\"><b>Synthesis Approval JSON</b></div>
      <div class=\"row\">
        <button id=\"build-synthesis-template\">Build Template</button>
        <button id=\"download-synthesis-json\">Download human_synthesis_decisions.json</button>
      </div>
      <div class=\"row\">
        <textarea id=\"synthesis-editor\"></textarea>
      </div>
    </div>

    <div class=\"panel\">
      <b>Pass 1: Cluster Validation</b>
      <div class=\"muted\">Use decision <code>MERGE</code>, <code>SKIP</code>, or <code>SPLIT</code> with <code>split_groups</code>.</div>
      <div class=\"grid\" id=\"cluster-validation\"></div>
    </div>

    <div class=\"panel\">
      <b>Pass 2: Canonical Entity Synthesis</b>
      <div class=\"muted\">Review LLM recommendation for each candidate group (MERGE or SKIP_SINGLETON).</div>
      <div class=\"grid\" id=\"synthesis-validation\"></div>
    </div>
  </div>

  <script id=\"cluster-items-data\" type=\"application/json\">{_safe_json(cluster_items)}</script>
  <script id=\"cluster-decisions-data\" type=\"application/json\">{_safe_json(cluster_decisions)}</script>
  <script id=\"synthesis-items-data\" type=\"application/json\">{_safe_json(synthesis_items)}</script>
  <script id=\"synthesis-decisions-data\" type=\"application/json\">{_safe_json(synthesis_decisions)}</script>
  <script>
    const clusterItems = JSON.parse(document.getElementById('cluster-items-data').textContent || '[]');
    const clusterDecisions = JSON.parse(document.getElementById('cluster-decisions-data').textContent || '[]');
    const synthesisItems = JSON.parse(document.getElementById('synthesis-items-data').textContent || '[]');
    const synthesisDecisions = JSON.parse(document.getElementById('synthesis-decisions-data').textContent || '[]');

    const byClusterDecision = new Map(clusterDecisions.map(x => [x.cluster_id, x]));
    const byProposalDecision = new Map(synthesisDecisions.map(x => [x.proposal_id, x]));

    function renderClusterValidation() {{
      const root = document.getElementById('cluster-validation');
      root.innerHTML = '';
      for (const item of clusterItems) {{
        const decision = byClusterDecision.get(item.cluster_id) || {{}};
        const hint = item.cluster_hint || {{}};
        const names = (item.candidates || []).map(c => (c.properties || {{}}).name || c.node_id);
        const risk = (hint.risk_flags || []).join(', ');
        const splitGroups = hint.split_groups || [];

        const card = document.createElement('div');
        card.className = 'cluster';
        card.innerHTML = `
          <div class=\"head\">
            <b>${{item.cluster_id}}</b>
            <span class=\"badge\">${{item.primary_type || 'UNKNOWN'}}</span>
          </div>
          <div class=\"kv\"><b>Decision:</b> ${{decision.decision || 'N/A'}} (approved=${{String(decision.approved)}})</div>
          <div class=\"kv\"><b>Hint:</b> ${{hint.decision || ''}} | confidence=${{hint.confidence ?? ''}} | source=${{hint.suggestion_source || ''}}</div>
          <div class=\"kv\"><b>Reasoning:</b> ${{hint.reasoning || ''}}</div>
          <div class=\"kv risk\"><b>Risk flags:</b> ${{risk || 'none'}}</div>
          <div class=\"kv\"><b>Split groups:</b> ${{splitGroups.length}}</div>
          <div class=\"kv\"><b>Candidates:</b></div>
          <ul>${{names.map(n => `<li>${{n}}</li>`).join('')}}</ul>
        `;
        root.appendChild(card);
      }}
    }}

    function renderSynthesisValidation() {{
      const root = document.getElementById('synthesis-validation');
      root.innerHTML = '';
      for (const item of synthesisItems) {{
        const decision = byProposalDecision.get(item.proposal_id) || {{}};
        const sug = item.llm_suggestion || {{}};
        const names = (item.candidates || []).map(c => (c.properties || {{}}).name || c.node_id);
        const risk = (sug.risk_flags || []).join(', ');

        const card = document.createElement('div');
        card.className = 'cluster';
        card.innerHTML = `
          <div class=\"head\">
            <b>${{item.proposal_id}}</b>
            <span class=\"badge\">${{item.primary_type || 'UNKNOWN'}}</span>
          </div>
          <div class=\"kv\"><b>Cluster:</b> ${{item.cluster_id}}</div>
          <div class=\"kv\"><b>Decision:</b> ${{decision.decision || 'N/A'}} (approved=${{String(decision.approved)}})</div>
          <div class=\"kv\"><b>Suggested canonical:</b> ${{sug.canonical_id || ''}}</div>
          <div class=\"kv\"><b>Confidence:</b> ${{sug.confidence ?? ''}} | <b>Source:</b> ${{sug.suggestion_source || 'n/a'}}</div>
          <div class=\"kv\"><b>Reasoning:</b> ${{sug.reasoning || ''}}</div>
          <div class=\"kv risk\"><b>Risk flags:</b> ${{risk || 'none'}}</div>
          <div class=\"kv\"><b>Candidates:</b></div>
          <ul>${{names.map(n => `<li>${{n}}</li>`).join('')}}</ul>
        `;
        root.appendChild(card);
      }}
    }}

    function buildClusterTemplate() {{
      const template = clusterItems.map(item => ({{
        cluster_id: item.cluster_id,
        decision: 'PENDING',
        approved: false,
        split_groups: []
      }}));
      document.getElementById('cluster-editor').value = JSON.stringify(template, null, 2);
      document.getElementById('cluster-promote-summary').textContent = '';
    }}

    function promoteMergeHints() {{
      let promoted = 0;
      const template = clusterItems.map(item => {{
        const hint = item.cluster_hint || {{}};
        const hintDecision = String(hint.decision || '').toUpperCase();

        if (hintDecision === 'MERGE') {{
          promoted += 1;
          return {{
            cluster_id: item.cluster_id,
            decision: 'MERGE',
            approved: true,
            confidence: Number(hint.confidence || 0.7),
            split_groups: []
          }};
        }}

        if (hintDecision === 'SKIP') {{
          return {{
            cluster_id: item.cluster_id,
            decision: 'SKIP',
            approved: false,
            confidence: Number(hint.confidence || 0.5),
            split_groups: []
          }};
        }}

        if (hintDecision === 'SPLIT') {{
          return {{
            cluster_id: item.cluster_id,
            decision: 'SPLIT',
            approved: false,
            confidence: Number(hint.confidence || 0.5),
            split_groups: Array.isArray(hint.split_groups) ? hint.split_groups : []
          }};
        }}

        return {{
          cluster_id: item.cluster_id,
          decision: 'PENDING',
          approved: false,
          split_groups: []
        }};
      }});

      document.getElementById('cluster-editor').value = JSON.stringify(template, null, 2);
      document.getElementById('cluster-promote-summary').textContent = `Promoted ${{promoted}} cluster(s) with MERGE hints to approved=true.`;
    }}

    function buildSynthesisTemplate() {{
      const template = synthesisItems.map(item => {{
        const sug = item.llm_suggestion || {{}};
        const isSingleton = ((item.node_ids || []).length <= 1);
        return {{
          proposal_id: item.proposal_id,
          cluster_id: item.cluster_id,
          decision: isSingleton ? 'SKIP_SINGLETON' : 'PENDING',
          canonical_id: sug.canonical_id || (item.node_ids || [])[0] || null,
          canonical_entity: {{
            labels: sug.labels || [],
            merged_properties: sug.merged_properties || {{}}
          }},
          confidence: Number(sug.confidence || 0.5),
          approved: !isSingleton
        }};
      }});
      document.getElementById('synthesis-editor').value = JSON.stringify(template, null, 2);
    }}

    function downloadJSON(editorId, fileName) {{
      const txt = document.getElementById(editorId).value.trim();
      if (!txt) return;
      const blob = new Blob([txt], {{type: 'application/json'}});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = fileName;
      a.click();
      URL.revokeObjectURL(a.href);
    }}

    document.getElementById('build-cluster-template').addEventListener('click', buildClusterTemplate);
    document.getElementById('promote-merge-hints').addEventListener('click', promoteMergeHints);
    document.getElementById('build-synthesis-template').addEventListener('click', buildSynthesisTemplate);
    document.getElementById('download-cluster-json').addEventListener('click', () => downloadJSON('cluster-editor', 'human_cluster_decisions.json'));
    document.getElementById('download-synthesis-json').addEventListener('click', () => downloadJSON('synthesis-editor', 'human_synthesis_decisions.json'));

    buildClusterTemplate();
    buildSynthesisTemplate();
    renderClusterValidation();
    renderSynthesisValidation();
  </script>
</body>
</html>
"""

    out.write_text(html, encoding="utf-8")
    return out
