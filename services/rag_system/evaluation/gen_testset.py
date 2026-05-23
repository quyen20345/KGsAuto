"""Generate a synthetic RAG evaluation testset with Ragas.

This manual script can either load an existing Ragas knowledge graph or rebuild
one from local Markdown files. Credentials are read from environment variables;
do not hardcode API keys in this file.
"""

from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

import pandas as pd
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from openai import OpenAI
from ragas.embeddings.base import BaseRagasEmbeddings
from ragas.llms import llm_factory
from ragas.run_config import RunConfig
from ragas.testset import TestsetGenerator
from ragas.testset.graph import KnowledgeGraph, Node, NodeType, Relationship
from ragas.testset.persona import Persona
from ragas.testset.synthesizers import (
    MultiHopAbstractQuerySynthesizer,
    MultiHopSpecificQuerySynthesizer,
    SingleHopSpecificQuerySynthesizer,
)
from ragas.testset.transforms import (
    CosineSimilarityBuilder,
    EmbeddingExtractor,
    HeadlineSplitter,
    HeadlinesExtractor,
    KeyphrasesExtractor,
    SummaryExtractor,
    apply_transforms,
)

from services.config import settings


DEFAULT_INPUT_DIR = Path("data/evaluation/corpus/docs")
DEFAULT_GRAPH_PATH = Path("data/evaluation/ragas_kg/knowledge_graph.json")
DEFAULT_OUTPUT_PATH = Path("data/evaluation/testset/questions.csv")
DEFAULT_TESTSET_SIZE = 150
DEFAULT_GENERATOR_MODEL = settings.evaluation.ragas_llm_model or "cx/gpt-5.2"
DEFAULT_GENERATOR_BASE_URL = settings.evaluation.ragas_llm_base_url or "http://localhost:20128/v1"
DEFAULT_EMBED_MODEL = settings.evaluation.ragas_embedding_model
DEFAULT_EMBED_BASE_URL = settings.evaluation.ragas_embedding_base_url
HEADLINE_SPLITTER_MIN_TOKENS = 200
VIETNAMESE_CHARS = set("ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")


def require_value(value: str | None, *names: str) -> str:
    if value:
        return value
    raise SystemExit(f"Missing required environment variable: {' or '.join(names)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Ragas testset for RAG evaluation.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--graph-path", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--rebuild-graph", action="store_true", help="Build and save a new knowledge graph first.")
    parser.add_argument(
        "--resume-from-checkpoint",
        action="store_true",
        help="Resume graph rebuild from the latest transform checkpoint for the same graph path.",
    )
    parser.add_argument("--testset-size", type=int, default=DEFAULT_TESTSET_SIZE)
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--embed-delay-seconds", type=float, default=0.5)
    parser.add_argument(
        "--generator-model",
        default=DEFAULT_GENERATOR_MODEL,
    )
    parser.add_argument(
        "--generator-base-url",
        default=DEFAULT_GENERATOR_BASE_URL,
    )
    parser.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL)
    parser.add_argument("--embed-base-url", default=DEFAULT_EMBED_BASE_URL)
    return parser.parse_args()


class NvidiaEmbeddings(BaseRagasEmbeddings):
    """Ragas-compatible wrapper around NVIDIA's OpenAI-compatible embedding API."""

    def __init__(self, client: OpenAI, model: str, delay_seconds: float) -> None:
        self.client = client
        self.model = model
        self.delay_seconds = delay_seconds

    def _sync_embed(self, text: str, input_type: str) -> list[float]:
        time.sleep(self.delay_seconds)
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
            encoding_format="float",
            extra_body={"input_type": input_type},
        )
        return response.data[0].embedding

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._sync_embed(text, input_type="passage") for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._sync_embed(text, input_type="query")

    async def aembed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._sync_embed, text, "query")

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_documents, texts)

    async def embed_text(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._sync_embed, text, "passage")


def load_markdown_documents(input_dir: Path):
    loader = DirectoryLoader(
        str(input_dir),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        silent_errors=True,
    )
    docs = loader.load()
    print(f"Loaded {len(docs)} markdown documents from '{input_dir}'")
    return docs


def create_generator_llm(model: str, base_url: str):
    api_key = require_value(settings.evaluation.ragas_llm_api_key, "OPENAI_API_KEY", "OPENAI_COMPATIBLE_API_KEY", "CX_API_KEY")
    client = OpenAI(api_key=api_key, base_url=base_url)
    return llm_factory(model=model, client=client)


def create_embeddings(model: str, base_url: str, delay_seconds: float) -> NvidiaEmbeddings:
    api_key = require_value(settings.evaluation.ragas_embedding_api_key, "RAGAS_EMBEDDING_API_KEY", "NVIDIA_API_KEY")
    client = OpenAI(api_key=api_key, base_url=base_url)
    return NvidiaEmbeddings(client=client, model=model, delay_seconds=delay_seconds)


def make_run_config(max_workers: int) -> RunConfig:
    return RunConfig(max_retries=10, max_wait=120, timeout=180, max_workers=max_workers)


def build_knowledge_graph(
    input_dir: Path,
    graph_path: Path,
    generator_llm,
    embeddings: NvidiaEmbeddings,
    config: RunConfig,
    resume_from_checkpoint: bool = False,
) -> KnowledgeGraph:
    transforms = [
        ("headlines", HeadlinesExtractor(llm=generator_llm)),
        ("headline_split", HeadlineSplitter(min_tokens=HEADLINE_SPLITTER_MIN_TOKENS)),
        ("summary", SummaryExtractor(llm=generator_llm)),
        ("keyphrases", KeyphrasesExtractor(llm=generator_llm)),
        ("embeddings", EmbeddingExtractor(embedding_model=embeddings)),
        ("cosine_similarity", CosineSimilarityBuilder(threshold=0.85)),
    ]

    latest_checkpoint = find_latest_transform_checkpoint(graph_path, len(transforms)) if resume_from_checkpoint else None
    if latest_checkpoint:
        completed_index, checkpoint_path = latest_checkpoint
        kg = KnowledgeGraph.load(str(checkpoint_path))
        start_index = completed_index
        print(f"Resuming graph rebuild from checkpoint '{checkpoint_path}'")
    else:
        docs = load_markdown_documents(input_dir)
        if not docs:
            raise SystemExit(f"No markdown documents found in {input_dir}")

        kg = KnowledgeGraph()
        for doc in docs:
            kg.nodes.append(
                Node(
                    type=NodeType.DOCUMENT,
                    properties={"page_content": doc.page_content, "document_metadata": doc.metadata},
                )
            )
        start_index = 0

    print("Applying Ragas transforms with per-stage checkpoints. This can take several minutes...")
    for index, (name, transform) in enumerate(transforms[start_index:], start=start_index + 1):
        print(f"Applying transform {index}/{len(transforms)}: {name}")
        apply_transforms(kg, transform, run_config=config)
        checkpoint_path = transform_checkpoint_path(graph_path, index, name)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        kg.save(str(checkpoint_path))
        print(f"Saved transform checkpoint to '{checkpoint_path}'")

    graph_path.parent.mkdir(parents=True, exist_ok=True)
    kg.save(str(graph_path))
    print(f"Saved knowledge graph to '{graph_path}'")
    return kg


def transform_checkpoint_path(graph_path: Path, index: int, transform_name: str) -> Path:
    suffix = graph_path.suffix or ".json"
    return graph_path.with_name(f"{graph_path.stem}.{index:02d}_{transform_name}{suffix}")


def find_latest_transform_checkpoint(graph_path: Path, transform_count: int) -> tuple[int, Path] | None:
    for index in range(transform_count, 0, -1):
        matches = sorted(graph_path.parent.glob(f"{graph_path.stem}.{index:02d}_*{graph_path.suffix or '.json'}"))
        if matches:
            return index, matches[-1]
    return None


def load_knowledge_graph(graph_path: Path) -> KnowledgeGraph:
    if not graph_path.exists():
        raise SystemExit(f"Knowledge graph not found: {graph_path}. Use --rebuild-graph first.")
    kg = KnowledgeGraph.load(str(graph_path))
    print(f"Loaded knowledge graph from '{graph_path}': {kg}")
    return kg


def prepare_multihop_compatibility_graph(kg: KnowledgeGraph) -> None:
    for node in kg.nodes:
        keyphrases = node.get_property("keyphrases")
        if keyphrases and not node.get_property("themes"):
            node.properties["themes"] = keyphrases

    existing_pairs = {
        frozenset((rel.source.id, rel.target.id))
        for rel in kg.relationships
        if rel.type == "keyphrases_overlap"
    }
    added = 0

    for rel in list(kg.relationships):
        if rel.type != "cosine_similarity":
            continue

        similarity = rel.get_property("cosine_similarity")
        if similarity is not None and not rel.get_property("summary_similarity"):
            rel.properties["summary_similarity"] = similarity

        source_keyphrases = set(rel.source.get_property("keyphrases") or [])
        target_keyphrases = set(rel.target.get_property("keyphrases") or [])
        overlapped_items = sorted(source_keyphrases & target_keyphrases)
        pair_key = frozenset((rel.source.id, rel.target.id))

        if overlapped_items and pair_key not in existing_pairs:
            kg.relationships.append(
                Relationship(
                    type="keyphrases_overlap",
                    source=rel.source,
                    target=rel.target,
                    bidirectional=rel.bidirectional,
                    properties={"overlapped_items": overlapped_items},
                )
            )
            existing_pairs.add(pair_key)
            added += 1

    print(f"Added {added} keyphrase-overlap relationships for multi-hop generation")


def make_personas() -> list[Persona]:
    return [
        Persona(
            name="Sinh viên UET",
            role_description=(
                "Một sinh viên Trường Đại học Công nghệ cần hỏi bằng tiếng Việt có dấu về thông tin trong tài liệu. "
                "Ưu tiên câu hỏi tự nhiên về khoa, viện, phòng ban, chương trình đào tạo, học bổng, công tác sinh viên, "
                "nhân sự, nghiên cứu và hợp tác. Không hỏi về metadata kỹ thuật như URL, ID, slug, loại bài viết, "
                "ngày đăng hoặc ngày sửa."
            ),
        ),
        Persona(
            name="Chuyên gia tri thức UET",
            role_description=(
                "Một chuyên gia kiểm định tri thức đặt câu hỏi chính xác bằng tiếng Việt có dấu để kiểm tra khả năng "
                "truy xuất và suy luận từ tài liệu UET. Câu hỏi phải bám vào nội dung nghiệp vụ như chức năng, nhiệm vụ, "
                "quan hệ trực thuộc, đơn vị phụ trách, chương trình đào tạo, người liên quan, địa chỉ liên hệ, học bổng, "
                "nghiên cứu hoặc hợp tác. Không hỏi về metadata kỹ thuật như URL, ID, slug, loại bài viết, ngày đăng hoặc ngày sửa."
            ),
        ),
    ]


def make_query_distribution(generator_llm):
    return [
        (SingleHopSpecificQuerySynthesizer(llm=generator_llm, property_name="keyphrases"), 0.5),
        (
            MultiHopAbstractQuerySynthesizer(
                llm=generator_llm,
                relation_property="summary_similarity",
                abstract_property_name="themes",
            ),
            0.25,
        ),
        (
            MultiHopSpecificQuerySynthesizer(
                llm=generator_llm,
                property_name="keyphrases",
                relation_type="keyphrases_overlap",
            ),
            0.25,
        ),
    ]


def validate_graph_for_generation(kg: KnowledgeGraph) -> None:
    nodes_with_keyphrases = sum(
        1 for node in kg.nodes if node.type.name in {"CHUNK", "DOCUMENT"} and node.get_property("keyphrases")
    )
    if nodes_with_keyphrases == 0:
        raise SystemExit("The knowledge graph has no nodes with `keyphrases`. Rebuild it first.")
    print(f"Nodes available for single-hop generation: {nodes_with_keyphrases}")


def generate_testset(
    kg: KnowledgeGraph,
    generator_llm,
    embeddings: NvidiaEmbeddings,
    config: RunConfig,
    testset_size: int,
) -> pd.DataFrame:
    validate_graph_for_generation(kg)
    generator = TestsetGenerator(
        llm=generator_llm,
        embedding_model=embeddings,
        knowledge_graph=kg,
        persona_list=make_personas(),
    )

    print(f"Generating testset with target size {testset_size}...")
    testset = generator.generate(
        testset_size=testset_size,
        query_distribution=make_query_distribution(generator_llm),
        run_config=config,
    )

    df: pd.DataFrame = testset.to_pandas()
    if df.empty:
        raise SystemExit("Ragas generated an empty testset. Check endpoint output and graph quality.")
    return df


def print_generation_summary(df: pd.DataFrame, target_size: int) -> None:
    question_column = "user_input" if "user_input" in df.columns else "question" if "question" in df.columns else None
    actual_size = len(df)

    print("\nGeneration summary:")
    print(f"Target size: {target_size}")
    print(f"Actual rows: {actual_size}")
    if actual_size < target_size:
        print(f"Warning: Ragas returned {actual_size}/{target_size} rows after internal filtering.")

    if not question_column:
        print("Vietnamese question ratio: unavailable (no user_input/question column)")
        return

    questions = [str(value) for value in df[question_column].dropna().tolist()]
    if not questions:
        print("Vietnamese question ratio: unavailable (no questions)")
        return

    vietnamese_count = sum(1 for question in questions if looks_vietnamese(question))
    print(f"Vietnamese question ratio: {vietnamese_count}/{len(questions)} ({vietnamese_count / len(questions):.1%})")


def looks_vietnamese(text: str) -> bool:
    normalized = text.lower()
    return any(char in normalized for char in VIETNAMESE_CHARS)


def main() -> None:
    args = parse_args()
    generator_llm = create_generator_llm(args.generator_model, args.generator_base_url)
    embeddings = create_embeddings(args.embed_model, args.embed_base_url, args.embed_delay_seconds)
    config = make_run_config(args.max_workers)

    kg = (
        build_knowledge_graph(
            args.input_dir,
            args.graph_path,
            generator_llm,
            embeddings,
            config,
            resume_from_checkpoint=args.resume_from_checkpoint,
        )
        if args.rebuild_graph
        else load_knowledge_graph(args.graph_path)
    )
    prepare_multihop_compatibility_graph(kg)

    df = generate_testset(kg, generator_llm, embeddings, config, args.testset_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print_generation_summary(df, args.testset_size)

    print("\nTestset preview:")
    print("Columns:", df.columns.tolist())
    print(df.head())
    print(f"\nSaved testset to '{args.output}'")


if __name__ == "__main__":
    main()
