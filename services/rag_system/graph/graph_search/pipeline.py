"""Neo4j-only GraphSearch reasoning used by the unified retrieval pipeline."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Protocol


def _looks_negative(verification: str) -> bool:
    lowered = " ".join(normalize(verification))
    return lowered.startswith("no") or " no" in lowered

from services.rag_system.graph.graph_search.components import (
    answer_generation,
    answer_generation_deep,
    evidence_verification,
    kg_query_completer,
    kg_summary,
    query_completer,
    query_expansion,
    question_decomposition_deep,
    question_decomposition_deep_kg,
    text_summary,
)
from services.rag_system.graph.graph_search.parsing import (
    parse_expanded_queries,
    parse_relational_sub_queries,
    parse_semantic_sub_queries,
    relational_query_to_retrieval_text,
)
from services.rag_system.graph.neo4j_context_adapter import Neo4jAdapter
from services.rag_system.graph.graph_search.utils import format_history_context, normalize


SUPPORTED_MODES = {"naive_grag", "graph_search"}
MODE_ALIASES = {
    "grag": "naive_grag",
    "naive-grag": "naive_grag",
    "graphsearch": "graph_search",
    "graph-search": "graph_search",
}
MAX_SUB_QUERIES = int(os.getenv("GRAPHSEARCH_MAX_SUB_QUERIES", "5"))
MAX_EXPANDED_QUERIES = int(os.getenv("GRAPHSEARCH_MAX_EXPANDED_QUERIES", "3"))


class GraphSearchMethod(Protocol):
    top_k: int

    async def aquery_context(self, question: str) -> str:
        ...

    async def aquery_answer(self, question: str, context: str | None = None) -> str:
        ...

    def context_filter(self, context_data: str, filter_type: str) -> str:
        ...


def canonical_mode(mode: str) -> str:
    canonical = MODE_ALIASES.get(mode.strip().lower(), mode.strip().lower())
    if canonical not in SUPPORTED_MODES:
        supported = ", ".join(sorted(SUPPORTED_MODES | set(MODE_ALIASES)))
        raise ValueError(f"Unsupported GraphSearch mode: {mode}. Supported modes: {supported}")
    return canonical


async def naive_grag_reasoning(question: str, grag_method: GraphSearchMethod) -> dict[str, Any]:
    retrieval_start = time.perf_counter()
    context = await grag_method.aquery_context(question=question)
    retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1000

    synthesis_start = time.perf_counter()
    answer = await grag_method.aquery_answer(question=question, context=context)
    synthesis_time_ms = (time.perf_counter() - synthesis_start) * 1000

    return {
        "answer": answer,
        "context": context,
        "evidence": {"context": context},
        "mode": "naive_grag",
        "citations": [],
        "retrieval_time_ms": retrieval_time_ms,
        "synthesis_time_ms": synthesis_time_ms,
        "metadata": {"top_k": getattr(grag_method, "top_k", None)},
    }


async def graph_search_reasoning(question: str, grag_method: GraphSearchMethod) -> dict[str, Any]:
    logging.info("Starting graph search reasoning")
    start_time = time.perf_counter()
    module_timings_ms: dict[str, float] = {}
    retrieval_time_ms = 0.0
    synthesis_time_ms = 0.0

    async def timed(label: str, awaitable, bucket: str):
        nonlocal retrieval_time_ms, synthesis_time_ms
        phase_start = time.perf_counter()
        result = await awaitable
        elapsed = (time.perf_counter() - phase_start) * 1000
        module_timings_ms[label] = module_timings_ms.get(label, 0.0) + elapsed
        if bucket == "retrieval":
            retrieval_time_ms += elapsed
        elif bucket == "synthesis":
            synthesis_time_ms += elapsed
        return result

    initial_context = await timed("CR.initial_context_retrieval", grag_method.aquery_context(question=question), "retrieval")
    text_initial_summary = await timed("CR.initial_text_summary", text_summary(question, initial_context), "synthesis")
    kg_initial_summary = await timed("CR.initial_kg_summary", kg_summary(question, initial_context), "synthesis")

    logging.info("[QD] Decomposing semantic and relational queries")
    semantic_decomposition = await timed("QD.semantic_decomposition", question_decomposition_deep(question), "synthesis")
    relational_decomposition = await timed("QD.relational_decomposition", question_decomposition_deep_kg(question), "synthesis")

    sub_queries = parse_semantic_sub_queries(semantic_decomposition, max_items=MAX_SUB_QUERIES)
    sub_kg_queries = parse_relational_sub_queries(relational_decomposition, max_items=MAX_SUB_QUERIES)

    text_query_history: list[tuple[str, str, str]] = []
    text_expanded_queries: list[str] = []
    for sub_query in sub_queries:
        text_query_history_str = format_history_context(text_query_history)
        if "#" in sub_query:
            completed = await timed(
                "QG.semantic_query_grounding",
                query_completer(sub_query, semantic_decomposition + "\n\n" + text_query_history_str),
                "synthesis",
            )
            sub_query = completed or sub_query

        sub_query_context = await timed("CR.semantic_subquery_retrieval", grag_method.aquery_context(question=sub_query), "retrieval")
        sub_query_context = grag_method.context_filter(context_data=sub_query_context, filter_type="semantic")
        sub_query_context_summary = await timed("CR.semantic_context_refinement", text_summary(sub_query, sub_query_context), "synthesis")
        sub_query_context_data = text_query_history_str + "\n\n" + sub_query_context_summary
        sub_query_answer = await timed("QG.semantic_intermediate_answer", answer_generation(sub_query, sub_query_context_data), "synthesis")
        text_query_history.append((sub_query, sub_query_context_summary, sub_query_answer))

    text_query_history_str = format_history_context(text_query_history)
    logging.info("[LD] Drafting semantic reasoning chain")
    text_final_answer = await timed("LD.semantic_logic_drafting", answer_generation_deep(question, text_query_history_str), "synthesis")

    logging.info("[EV] Verifying semantic evidence")
    text_verification_result = await timed(
        "EV.semantic_evidence_verification",
        evidence_verification(question, text_query_history_str, text_final_answer),
        "synthesis",
    )

    if _looks_negative(text_verification_result):
        logging.info("[QE] Expanding semantic queries")
        query_expansion_result = await timed(
            "QE.semantic_query_expansion",
            query_expansion(question, text_query_history_str, text_final_answer, text_verification_result),
            "synthesis",
        )
        expanded_queries = parse_expanded_queries(query_expansion_result, max_items=MAX_EXPANDED_QUERIES)
        text_expanded_queries.extend(expanded_queries)

        for expanded_query in expanded_queries:
            expanded_query_context = await timed("CR.semantic_expansion_retrieval", grag_method.aquery_context(question=expanded_query), "retrieval")
            expanded_query_context = grag_method.context_filter(context_data=expanded_query_context, filter_type="semantic")
            expanded_summary = await timed("CR.semantic_expansion_refinement", text_summary(expanded_query, expanded_query_context), "synthesis")
            text_query_history.append((expanded_query, expanded_summary, ""))

        text_query_history_str = format_history_context(text_query_history)

    kg_query_history: list[tuple[str, str, str]] = []
    kg_expanded_queries: list[str] = []
    for index, sub_kg_query in enumerate(sub_kg_queries):
        kg_query_history_str = format_history_context(kg_query_history)
        if index > 0:
            completed = await timed(
                "QG.relational_query_grounding",
                kg_query_completer(sub_kg_query, relational_decomposition + "\n\n" + kg_query_history_str),
                "synthesis",
            )
            sub_kg_query = completed or sub_kg_query

        sub_kg_query_cleaned = relational_query_to_retrieval_text(sub_kg_query)
        if not sub_kg_query_cleaned:
            continue
        sub_kg_query_context = await timed("CR.relational_subquery_retrieval", grag_method.aquery_context(question=sub_kg_query_cleaned), "retrieval")
        sub_kg_query_context = grag_method.context_filter(context_data=sub_kg_query_context, filter_type="relational")
        sub_kg_query_summary = await timed("CR.relational_context_refinement", kg_summary(sub_kg_query, sub_kg_query_context), "synthesis")
        sub_kg_query_context_data = kg_query_history_str + "\n\n" + sub_kg_query_summary
        sub_kg_query_answer = await timed("QG.relational_intermediate_answer", answer_generation(sub_kg_query, sub_kg_query_context_data), "synthesis")
        kg_query_history.append((sub_kg_query, sub_kg_query_summary, sub_kg_query_answer))

    kg_query_history_str = format_history_context(kg_query_history)
    logging.info("[LD] Drafting relational reasoning chain")
    kg_final_answer = await timed("LD.relational_logic_drafting", answer_generation_deep(question, kg_query_history_str), "synthesis")

    logging.info("[EV] Verifying relational evidence")
    kg_verification_result = await timed(
        "EV.relational_evidence_verification",
        evidence_verification(question, kg_query_history_str, kg_final_answer),
        "synthesis",
    )

    if _looks_negative(kg_verification_result):
        logging.info("[QE] Expanding relational queries")
        query_expansion_result = await timed(
            "QE.relational_query_expansion",
            query_expansion(question, kg_query_history_str, kg_final_answer, kg_verification_result),
            "synthesis",
        )
        expanded_queries = parse_expanded_queries(query_expansion_result, max_items=MAX_EXPANDED_QUERIES)
        kg_expanded_queries.extend(expanded_queries)

        for expanded_query in expanded_queries:
            expanded_context = await timed("CR.relational_expansion_retrieval", grag_method.aquery_context(question=expanded_query), "retrieval")
            expanded_context = grag_method.context_filter(context_data=expanded_context, filter_type="relational")
            expanded_summary = await timed("CR.relational_expansion_refinement", kg_summary(expanded_query, expanded_context), "synthesis")
            kg_query_history.append((expanded_query, expanded_summary, ""))

        kg_query_history_str = format_history_context(kg_query_history)

    combined_history = (
        "Background information:\n"
        + text_initial_summary
        + "\n"
        + kg_initial_summary
        + "\n\n"
        + text_query_history_str
        + "\n\n"
        + kg_query_history_str
    )
    final_answer = await timed("LD.final_answer_generation", answer_generation_deep(question, combined_history), "synthesis")
    total_time_ms = (time.perf_counter() - start_time) * 1000

    return {
        "answer": final_answer,
        "citations": [],
        "reasoning_steps": {
            "text_queries": text_query_history,
            "kg_queries": kg_query_history,
            "text_verification": text_verification_result,
            "kg_verification": kg_verification_result,
            "text_expanded_queries": text_expanded_queries,
            "kg_expanded_queries": kg_expanded_queries,
        },
        "evidence": {
            "initial_context": initial_context,
            "text_summary": text_initial_summary,
            "kg_summary": kg_initial_summary,
        },
        "mode": "graph_search",
        "retrieval_time_ms": retrieval_time_ms,
        "synthesis_time_ms": synthesis_time_ms,
        "total_time_ms": total_time_ms,
        "metadata": {
            "top_k": getattr(grag_method, "top_k", None),
            "module_timings_ms": module_timings_ms,
            "max_sub_queries": MAX_SUB_QUERIES,
            "max_expanded_queries": MAX_EXPANDED_QUERIES,
        },
    }


async def run_graphsearch_query(
    question: str,
    mode: str,
    backend: str = "neo4j",
    top_k: int = 5,
    grag_method: GraphSearchMethod | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Run the Neo4j-only GraphSearch modes.

    Extra keyword arguments are accepted for compatibility with the previous
    benchmark runner, but V1 only supports the Neo4j backend.
    """
    if backend != "neo4j":
        raise ValueError("V1 GraphSearch runtime only supports backend='neo4j'.")

    start_time = time.perf_counter()
    canonical = canonical_mode(mode)
    method = grag_method or Neo4jAdapter(top_k=top_k)

    if canonical == "naive_grag":
        result = await naive_grag_reasoning(question, method)
    else:
        result = await graph_search_reasoning(question, method)

    result.setdefault("mode", canonical)
    result.setdefault("citations", [])
    result.setdefault("retrieval_time_ms", None)
    result.setdefault("synthesis_time_ms", None)
    result.setdefault("total_time_ms", (time.perf_counter() - start_time) * 1000)
    if not isinstance(result.get("metadata"), dict):
        result["metadata"] = {}
    result["metadata"].update({"top_k": top_k, "backend": backend})
    return json.loads(json.dumps(result, ensure_ascii=False, default=str))
