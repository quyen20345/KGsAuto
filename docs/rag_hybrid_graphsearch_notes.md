# RAG Hybrid / Deep GraphSearch Notes

## Current observed behavior

Diagnostic question:

```text
Ai là viện trưởng của Viện Trí tuệ nhân tạo, Trường Đại học Công nghệ, Đại học Quốc gia Hà Nội?
```

Observed behavior:

- A standalone `graph_search` run can answer that the director is `Trần Quốc Long`.
- A `hybrid` run may answer conditionally: markdown evidence supports `TS. Trần Quốc Long`, but the internal GraphSearch execution inside `hybrid` may report that graph evidence is insufficient.

This does not necessarily mean `hybrid` is still using the old shallow graph retriever. The public `hybrid` mode is now intended to combine:

```text
semantic_search + deep graph_search
```

The issue is that the internal deep GraphSearch execution used by `hybrid` can produce a different result from a previous standalone `graph_search` run.

## Why `graph_search` and `hybrid` can disagree

`graph_search` and `hybrid` do not share one execution result.

When running:

```bash
python -m services.rag_system.cli query --mode graph_search ...
```

and then running:

```bash
python -m services.rag_system.cli query --mode hybrid ...
```

these are separate executions. `hybrid` runs a fresh internal deep GraphSearch call and then synthesizes that graph result together with markdown evidence.

Deep GraphSearch is LLM-driven, so these steps can vary between runs:

- question decomposition
- generated text queries
- generated KG queries
- evidence verification
- query expansion
- final graph answer generation

Because of that, a standalone `graph_search` run can find enough evidence, while the internal GraphSearch run inside `hybrid` may decide that evidence is insufficient.

The current CLI evidence display also makes this harder to inspect. It can show that GraphSearch context and reasoning are available, but it does not clearly print the internal GraphSearch answer that `hybrid` used during final synthesis.

## Confirmed diagnostics

Known findings from the investigation:

- Neo4j contains the relevant person/entity data for `node_tran_quoc_long`.
- Neo4j contains the relevant institute/office data for `node_van_phong_vien_tri_tue_nhan_tao`.
- The graph contains relevant relationships from Trần Quốc Long to the institute/office node, including `LEADS` and `WORKS_AT`.
- The institute node has useful aliases such as:
  - `Viện Trí tuệ nhân tạo`
  - `Institute for Artificial Intelligence`
  - `IAI`
  - `Viện TTNT`
  - `Viện AI`
  - `Văn phòng Viện`
- Accented vs unaccented Vietnamese queries can strongly affect markdown retrieval quality.
- Basic graph substring search can miss unaccented variants when stored aliases and names are accented.
- The previous shallow `GraphRetriever` path was not sufficient for public `hybrid`; it could return unrelated graph facts such as unrelated institutes.
- The current public `hybrid` architecture is better because it uses deep GraphSearch, but deep GraphSearch can still be unstable because retrieval and verification depend on generated intermediate queries.

## Constraints and non-goals

Do not fix this by hard-coding role-specific relationship priorities for one question type.

Avoid rules like:

```text
If the question asks “viện trưởng”, prioritize LEADS / WORKS_AT / HEAD_OF / DIRECTOR_OF.
```

That would likely overfit to this one diagnostic question. The preferred direction is to improve general retrieval and observability:

- better Vietnamese normalization
- better alias and phrase matching
- better evidence coverage
- clearer debugging output
- more stable GraphSearch execution

## Optimization opportunities

Future improvements to consider:

1. Expose hybrid’s internal GraphSearch answer
   - Store or display the internal `graph_search` answer used by `hybrid`.
   - This would make it clear whether final synthesis is disagreeing with graph evidence or whether graph evidence was missing upstream.

2. Improve debug visibility
   - Add a debug mode that shows extracted keywords, generated text queries, generated KG queries, retrieved graph context, verification decisions, query expansions, and the final graph answer.

3. Improve deterministic behavior
   - Consider lower-temperature or deterministic settings for GraphSearch helper calls if the LLM provider supports them.
   - This can reduce disagreement between repeated runs of the same question.

4. Improve Vietnamese normalization
   - Normalize accented and unaccented forms consistently for graph entity and alias lookup.
   - Consider similar normalization for markdown query handling if the embedding model or query formulation is accent-sensitive.

5. Improve phrase-level matching
   - Preserve and search important noun phrases such as `Viện Trí tuệ nhân tạo`.
   - Avoid relying only on token fragments like `viện`, `trí`, `tuệ`, or `nhân tạo`.

6. Consider optional result reuse during debugging
   - When comparing modes interactively, it may be useful to cache or reuse a previous `graph_search` result for the same question.
   - This should be optional and explicit, because normal runtime should still execute each mode independently.

7. Strengthen evaluation coverage
   - Add evaluation questions that compare all four modes on the same inputs:
     - `semantic_search`
     - `graph_search`
     - `naive_grag`
     - `hybrid`
   - Include both accented and unaccented Vietnamese variants.
   - Track whether answers are supported by markdown evidence, graph evidence, or both.

## Suggested future verification commands

Run the same diagnostic question through each relevant mode.

```bash
python -m services.rag_system.cli query \
  --question "Ai là viện trưởng của Viện Trí tuệ nhân tạo, Trường Đại học Công nghệ, Đại học Quốc gia Hà Nội?" \
  --mode semantic_search \
  --top-k 5 \
  --show-evidence
```

```bash
python -m services.rag_system.cli query \
  --question "Ai là viện trưởng của Viện Trí tuệ nhân tạo, Trường Đại học Công nghệ, Đại học Quốc gia Hà Nội?" \
  --mode graph_search \
  --top-k 5 \
  --show-evidence
```

```bash
python -m services.rag_system.cli query \
  --question "Ai là viện trưởng của Viện Trí tuệ nhân tạo, Trường Đại học Công nghệ, Đại học Quốc gia Hà Nội?" \
  --mode hybrid \
  --top-k 5 \
  --show-evidence
```

Also compare with the unaccented form:

```bash
python -m services.rag_system.cli query \
  --question "Ai la vien truong vien tri tue nhan tao dai hoc cong nghe - vnu?" \
  --mode hybrid \
  --top-k 5 \
  --show-evidence
```

## Expected direction

The next improvement should not be a question-specific heuristic. It should make the system easier to inspect and make retrieval more robust across equivalent Vietnamese query forms.

A good first code improvement later would be observability: expose the internal GraphSearch answer and reasoning details used by `hybrid`, so disagreements can be diagnosed directly instead of inferred from the final synthesized answer.
