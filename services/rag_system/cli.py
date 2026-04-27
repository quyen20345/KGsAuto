"""Command-line interface for RAG System"""

from pathlib import Path
from pprint import pformat

import click
from services.rag_system.config import RAGConfig


def _format_score(value):
    return f"{value:.3f}" if isinstance(value, (int, float)) else None


def _preview_text(item, *keys, limit=120):
    for key in keys:
        value = item.get(key)
        if value:
            text = str(value)
            return text[:limit] + ("..." if len(text) > limit else "")
    return pformat(item, compact=True)[:limit]


@click.group()
def cli():
    """RAG System CLI - Retrieval-Augmented Generation for UET Knowledge Base"""
    pass


@cli.command()
@click.option("--collection", default=None, help="Qdrant collection name (default: from config)")
def create_collection(collection):
    """Create Qdrant collection for markdown chunks"""
    from services.rag_system.storage import DocumentStore

    config = RAGConfig()
    if collection:
        config.markdown_collection = collection

    store = DocumentStore(config)
    store.create_collection()


@cli.command()
@click.option("--collection", default=None, help="Qdrant collection name (default: from config)")
def delete_collection(collection):
    """Delete Qdrant collection"""
    from services.rag_system.storage import DocumentStore

    config = RAGConfig()
    if collection:
        config.markdown_collection = collection

    if click.confirm(f"Are you sure you want to delete collection '{config.markdown_collection}'?"):
        store = DocumentStore(config)
        store.delete_collection()


@cli.command()
@click.option("--limit", default=None, type=int, help="Limit number of files to index")
@click.option("--force", is_flag=True, help="Force re-indexing (delete existing collection)")
def index(limit, force):
    """Index markdown documents to Qdrant"""
    from services.rag_system.retrieval import MarkdownIndexer

    config = RAGConfig()
    indexer = MarkdownIndexer(config)

    click.echo("Starting indexing...")
    click.echo()

    try:
        stats = indexer.index_all(limit=limit, force=force)
        click.echo()
        click.echo("✓ Indexing completed successfully!")
    except Exception as e:
        click.echo(f"✗ Indexing failed: {e}")
        raise


@cli.command()
@click.option("--question", required=True, help="Question to ask")
@click.option(
    "--mode",
    type=click.Choice(["semantic_search", "graph_search", "naive_grag", "hybrid"]),
    default="semantic_search",
)
@click.option("--top-k", default=5, help="Number of results to retrieve")
@click.option("--show-evidence", is_flag=True, help="Show retrieved evidence")
def query(question, mode, top_k, show_evidence):
    """Query the unified retrieval system"""
    from services.rag_system.core import UnifiedRetrievalPipeline

    config = RAGConfig()
    pipeline = UnifiedRetrievalPipeline(config)

    click.echo(f"Question: {question}")
    click.echo(f"Mode: {mode}")
    click.echo(f"Top-K: {top_k}")
    click.echo()

    try:
        # Query pipeline
        result = pipeline.query(
            question=question,
            mode=mode,
            top_k=top_k,
            include_evidence=show_evidence
        )

        # Display answer
        click.echo("="*60)
        click.echo("Answer:")
        click.echo("="*60)
        click.echo(result["answer"])
        click.echo()

        # Display citations
        if result.get("citations"):
            click.echo("Citations:")
            for citation in result["citations"]:
                click.echo(f"  - [{citation}]")
            click.echo()

        # Display metadata
        click.echo("Metadata:")
        click.echo(f"  Mode: {result['mode']}")
        if result.get("retrieval_time_ms"):
            click.echo(f"  Retrieval time: {result['retrieval_time_ms']:.2f} ms")
        if result.get("synthesis_time_ms"):
            click.echo(f"  Synthesis time: {result['synthesis_time_ms']:.2f} ms")
        click.echo(f"  Total time: {result['total_time_ms']:.2f} ms")
        if result.get("token_usage"):
            click.echo(f"  Token usage: {result['token_usage']}")
        click.echo()

        # Display evidence if requested
        if show_evidence and result.get("evidence"):
            evidence = result["evidence"]
            markdown_chunks = evidence.get("markdown_chunks") or []
            graph_facts = evidence.get("graph_facts") or []
            graph_context = evidence.get("graph_context")
            click.echo("Retrieved Evidence:")
            if markdown_chunks:
                click.echo(f"  {len(markdown_chunks)} markdown chunks")
                for i, chunk in enumerate(markdown_chunks[:3], 1):
                    label = chunk.get("chunk_id") or chunk.get("doc_id") or chunk.get("title") or "chunk"
                    section = chunk.get("section")
                    suffix = f" - {section}" if section else ""
                    click.echo(f"\n  [{i}] {label}{suffix}")
                    score = _format_score(chunk.get("score"))
                    if score:
                        click.echo(f"      Score: {score}")
                    click.echo(f"      Text: {_preview_text(chunk, 'text', 'content', limit=100)}")
            if graph_facts:
                click.echo(f"  {len(graph_facts)} graph facts")
                for i, fact in enumerate(graph_facts[:3], 1):
                    label = fact.get("entity_name") or fact.get("entity_id") or "entity"
                    fact_type = fact.get("fact_type") or "fact"
                    click.echo(f"\n  [{i}] {label} - {fact_type}")
                    score = _format_score(fact.get("score"))
                    if score:
                        click.echo(f"      Score: {score}")
                    click.echo(f"      Fact: {_preview_text(fact, 'fact_text', 'description', 'text')}")
            if graph_context:
                click.echo("  GraphSearch context available")

    except Exception as e:
        click.echo(f"✗ Query failed: {e}")
        raise


@cli.group()
def evaluate():
    """Generate and score RAGAS evaluation data"""
    pass


@evaluate.command("generate-dataset")
@click.option("--input-dir", type=click.Path(path_type=Path), default=Path("data/raw/uet"))
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/evaluation/uet_ragas_dataset.jsonl"))
@click.option("--max-questions", default=120, type=int)
@click.option("--min-context-chars", default=80, type=int)
@click.option("--single-hop", default=70, type=int)
@click.option("--long-document", default=25, type=int)
@click.option("--multi-hop", default=15, type=int)
@click.option("--unanswerable", default=10, type=int)
def evaluate_generate_dataset(input_dir, output, max_questions, min_context_chars, single_hop, long_document, multi_hop, unanswerable):
    """Generate a JSONL evaluation dataset from markdown files"""
    from services.rag_system.evaluation.ragas_eval import (
        DatasetGenerationConfig,
        QuestionTypeTargets,
        generate_dataset_from_markdown,
    )

    samples = generate_dataset_from_markdown(
        DatasetGenerationConfig(
            input_dir=input_dir,
            output=output,
            max_questions=max_questions,
            min_context_chars=min_context_chars,
            targets=QuestionTypeTargets(single_hop, long_document, multi_hop, unanswerable),
        )
    )
    click.echo(f"Wrote {len(samples)} samples to {output}")


@evaluate.command("generate-pilot")
@click.option("--input-dir", type=click.Path(path_type=Path), default=Path("data/raw/uet"))
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/evaluation/uet_v1_pilot.jsonl"))
@click.option("--max-questions", default=40, type=int)
@click.option("--min-context-chars", default=80, type=int)
@click.option("--single-hop", default=12, type=int)
@click.option("--relationship", default=12, type=int)
@click.option("--multi-hop", default=10, type=int)
@click.option("--unanswerable", default=6, type=int)
def evaluate_generate_pilot(input_dir, output, max_questions, min_context_chars, single_hop, relationship, multi_hop, unanswerable):
    """Generate the V1 manual-comparison pilot dataset"""
    from services.rag_system.evaluation.ragas_eval import (
        PilotDatasetGenerationConfig,
        PilotQuestionTypeTargets,
        generate_pilot_dataset_from_markdown,
    )

    samples = generate_pilot_dataset_from_markdown(
        PilotDatasetGenerationConfig(
            input_dir=input_dir,
            output=output,
            max_questions=max_questions,
            min_context_chars=min_context_chars,
            targets=PilotQuestionTypeTargets(single_hop, relationship, multi_hop, unanswerable),
        )
    )
    click.echo(f"Wrote {len(samples)} pilot samples to {output}")


@evaluate.command("run")
@click.option("--dataset", type=click.Path(path_type=Path), required=True)
@click.option("--output", type=click.Path(path_type=Path), required=True)
@click.option(
    "--mode",
    type=click.Choice(["semantic_search", "graph_search", "naive_grag", "hybrid"]),
    default="semantic_search",
)
@click.option("--top-k", default=5, type=int)
def evaluate_run(dataset, output, mode, top_k):
    """Run the unified retrieval pipeline over an evaluation dataset"""
    from services.rag_system.evaluation.ragas_eval import (
        iter_jsonl,
        run_unified_pipeline,
        samples_from_rows,
        write_jsonl,
    )

    samples = samples_from_rows(iter_jsonl(dataset))
    results = run_unified_pipeline(samples, mode=mode, top_k=top_k)
    write_jsonl(output, results)
    click.echo(f"Wrote {len(results)} results to {output}")


@evaluate.command("run-comparison")
@click.option("--dataset", type=click.Path(path_type=Path), required=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/evaluation/v1_comparison"))
@click.option("--backend", default="neo4j")
@click.option("--top-k", default=5, type=int)
def evaluate_run_comparison(dataset, output_dir, backend, top_k):
    """Run semantic_search, graph_search, naive_grag, and hybrid over the same dataset"""
    from services.rag_system.evaluation.ragas_eval import (
        iter_jsonl,
        run_v1_comparison,
        samples_from_rows,
        write_jsonl,
        write_manual_scoring_csv,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    samples = samples_from_rows(iter_jsonl(dataset))
    results_by_mode = run_v1_comparison(samples, top_k=top_k, backend=backend)

    for mode, results in results_by_mode.items():
        write_jsonl(output_dir / f"{mode}.jsonl", results)

    manual_csv = output_dir / "manual_scoring.csv"
    write_manual_scoring_csv(manual_csv, samples, results_by_mode)
    click.echo(f"Wrote comparison results to {output_dir}")
    click.echo(f"Wrote manual scoring CSV to {manual_csv}")


@evaluate.command("score")
@click.option("--dataset", type=click.Path(path_type=Path), required=True)
@click.option("--results", type=click.Path(path_type=Path), required=True)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/evaluation/ragas_scores.csv"))
def evaluate_score(dataset, results, output):
    """Score pipeline results with RAGAS"""
    from services.rag_system.evaluation.ragas_eval import (
        build_ragas_rows,
        iter_jsonl,
        samples_from_rows,
        score_with_ragas,
        write_scores_csv,
    )

    rows = build_ragas_rows(samples_from_rows(iter_jsonl(dataset)), list(iter_jsonl(results)))
    scores = score_with_ragas(rows)
    write_scores_csv(output, scores)
    click.echo(f"Wrote RAGAS scores to {output}")


@cli.command()
def test_connections():
    """Test connections to Qdrant and Neo4j"""
    from services.rag_system.storage import DocumentStore, GraphStore

    config = RAGConfig()

    click.echo("Testing connections...")
    click.echo()

    # Test Qdrant
    click.echo("1. Testing Qdrant connection...")
    try:
        store = DocumentStore(config)
        if store.collection_exists():
            count = store.count()
            click.echo(f"   ✓ Qdrant connected: Collection '{config.markdown_collection}' exists with {count} chunks")
        else:
            click.echo(f"   ✓ Qdrant connected: Collection '{config.markdown_collection}' does not exist yet")
    except Exception as e:
        click.echo(f"   ✗ Qdrant connection failed: {e}")

    click.echo()

    # Test Neo4j
    click.echo("2. Testing Neo4j connection...")
    try:
        graph_store = GraphStore(config)
        if graph_store.test_connection():
            count = graph_store.get_entity_count()
            click.echo(f"   ✓ Neo4j connected: {count} entities in graph")
        else:
            click.echo("   ✗ Neo4j connection failed")
    except Exception as e:
        click.echo(f"   ✗ Neo4j connection failed: {e}")

    click.echo()
    click.echo("Connection test complete!")


@cli.command()
def info():
    """Show RAG system configuration"""
    config = RAGConfig()

    click.echo("RAG System Configuration:")
    click.echo()
    click.echo("Data Paths:")
    click.echo(f"  Markdown dir: {config.markdown_dir}")
    click.echo(f"  Output dir: {config.output_dir}")
    click.echo()
    click.echo("Qdrant:")
    click.echo(f"  URL: {config.qdrant_url}")
    click.echo(f"  Collection: {config.markdown_collection}")
    click.echo()
    click.echo("Neo4j:")
    click.echo(f"  URI: {config.neo4j_uri}")
    click.echo(f"  User: {config.neo4j_user}")
    click.echo()
    click.echo("LLM:")
    click.echo(f"  Provider: {config.llm_provider}")
    click.echo(f"  Model: {config.llm_model}")
    click.echo()
    click.echo("Retrieval:")
    click.echo(f"  Top-K Markdown: {config.top_k_markdown}")
    click.echo(f"  Top-K Graph: {config.top_k_graph}")
    click.echo(f"  Max Graph Depth: {config.max_graph_depth}")
    click.echo()
    click.echo("Evaluation:")
    click.echo(f"  Pilot size: {config.eval_pilot_size} questions")
    click.echo(f"  Full size: {config.eval_full_size} questions")


if __name__ == "__main__":
    cli()
