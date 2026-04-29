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
            graph_reasoning = evidence.get("graph_reasoning")
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
            if graph_reasoning:
                text_queries = graph_reasoning.get("text_queries") or []
                kg_queries = graph_reasoning.get("kg_queries") or []
                click.echo(
                    f"  GraphSearch reasoning available: {len(text_queries)} text queries, {len(kg_queries)} KG queries"
                )

    except Exception as e:
        click.echo(f"✗ Query failed: {e}")
        raise


@cli.group()
def evaluate():
    """Run simple RAG evaluation datasets."""
    pass


RAG_MODES = ["semantic_search", "graph_search", "naive_grag", "hybrid"]


@evaluate.command("run")
@click.option(
    "--dataset",
    type=click.Path(path_type=Path),
    default=Path("services/rag_system/evaluation/mock_questions.jsonl"),
    help="Input JSONL evaluation dataset",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path("data/evaluation/rag_eval_results.jsonl"),
    help="Output JSONL path; CSV is written next to it",
)
@click.option(
    "--mode",
    type=click.Choice(RAG_MODES),
    default="semantic_search",
)
@click.option("--top-k", default=5, type=int, help="Number of results to retrieve")
def evaluate_run(dataset, output, mode, top_k):
    """Run one RAG mode over a JSONL question set."""
    from services.rag_system.evaluation.runner import run_dataset

    click.echo(f"Dataset: {dataset}")
    click.echo(f"Mode: {mode}")
    click.echo(f"Output: {output}")
    results = run_dataset(dataset, output, mode=mode, top_k=top_k)
    click.echo(f"Wrote {len(results)} results to {output}")
    click.echo(f"Wrote CSV results to {output.with_suffix('.csv')}")


@evaluate.command("run-comparison")
@click.option(
    "--dataset",
    type=click.Path(path_type=Path),
    default=Path("services/rag_system/evaluation/mock_questions.jsonl"),
    help="Input JSONL evaluation dataset",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path("data/evaluation/rag_eval_comparison.jsonl"),
    help="Output JSONL path; CSV is written next to it",
)
@click.option(
    "--mode",
    "modes",
    type=click.Choice(RAG_MODES),
    multiple=True,
    help="Mode to run; repeat for multiple modes. Defaults to all modes.",
)
@click.option("--top-k", default=5, type=int, help="Number of results to retrieve")
def evaluate_run_comparison(dataset, output, modes, top_k):
    """Run multiple RAG modes over a JSONL question set."""
    from services.rag_system.evaluation.runner import ALL_MODES, run_dataset_for_modes

    selected_modes = list(modes) or ALL_MODES
    click.echo(f"Dataset: {dataset}")
    click.echo(f"Modes: {', '.join(selected_modes)}")
    click.echo(f"Top-K: {top_k}")
    click.echo(f"Output: {output}")
    results = run_dataset_for_modes(dataset, output, modes=selected_modes, top_k=top_k)
    click.echo(f"Wrote {len(results)} results to {output}")
    click.echo(f"Wrote CSV results to {output.with_suffix('.csv')}")


@evaluate.command("score")
@click.option(
    "--results",
    type=click.Path(path_type=Path),
    required=True,
    help="Generated evaluation JSONL from evaluate run or run-comparison",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path("data/evaluation/rag_eval_scored.jsonl"),
    help="Scored JSONL path; CSV and summary CSV are written next to it",
)
@click.option(
    "--metric",
    "metrics",
    multiple=True,
    help="RAGAS metric to run; repeat for multiple metrics. Defaults to the standard metric set.",
)
def evaluate_score(results, output, metrics):
    """Score saved RAG outputs with RAGAS."""
    from services.rag_system.evaluation.scoring import RagasScoringError, RagasUnavailableError, score_results, summarize_scores

    click.echo(f"Results: {results}")
    click.echo(f"Output: {output}")
    try:
        scored = score_results(results, output, metrics=list(metrics) or None)
    except (RagasScoringError, RagasUnavailableError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Wrote {len(scored)} scored rows to {output}")
    click.echo(f"Wrote CSV results to {output.with_suffix('.csv')}")
    click.echo(f"Wrote summary CSV to {output.with_suffix('.summary.csv')}")
    click.echo("Summary:")
    for mode, row in summarize_scores(scored).items():
        click.echo(
            f"  {mode}: total={row['total_samples']}, ok={row['successful_samples']}, scored={row['scored_samples']}"
        )


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
