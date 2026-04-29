"""
RAG Testset Generation Pipeline
================================
Generates a synthetic evaluation testset from local Markdown documents
using the Ragas library.

Steps:
  1. Load Markdown docs from a local folder
  2. Configure LLM (OpenAI-compatible) + Embeddings (NVIDIA NIM)
  3. Build & enrich a KnowledgeGraph
  4. Generate a testset with multi-hop query distribution
  5. Export results to CSV / pandas

Requirements:
  pip install ragas langchain-community openai

Security note:
  Avoid hardcoding API keys in source files.
  Prefer environment variables or a .env file (python-dotenv).
"""

# ─────────────────────────────────────────────
# 1. LOAD DOCUMENTS
# ─────────────────────────────────────────────
from langchain_community.document_loaders import DirectoryLoader, TextLoader

DOCS_PATH = "/home/quyen/Documents/KGsAuto/data/rawtest"   # <-- change this to your folder path

# TextLoader avoids the `unstructured[md]` dependency and correctly
# handles UTF-8 Vietnamese characters in filenames/content.
loader = DirectoryLoader(
    DOCS_PATH,
    glob="**/*.md",
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"},
    silent_errors=True,   # skip unreadable files instead of crashing
)
docs = loader.load()
print(f"Loaded {len(docs)} documents from '{DOCS_PATH}'")


# ─────────────────────────────────────────────
# 2. CONFIGURE LLM & EMBEDDINGS
# ─────────────────────────────────────────────
import os
import time
import typing as t
from openai import OpenAI
from ragas.llms import llm_factory
from ragas.embeddings.base import BaseRagasEmbeddings

# ── LLM: OpenAI-compatible endpoint (cx/gpt-5.2) ─────────────────────
os.environ["CX_API_KEY"] = "---"

llm_client = OpenAI(
    api_key=os.environ["CX_API_KEY"],
    base_url="http://localhost:20128/v1",
)

generator_llm = llm_factory(
    model="cx/gpt-5.2",
    client=llm_client,
)

# ── Embeddings: NVIDIA NIM (llama-3.2-nemoretriever-300m-embed-v1) ────
# NVIDIA's API is OpenAI-compatible — no extra SDK needed.
os.environ["NVIDIA_API_KEY"] = "---"

NVIDIA_EMBED_MODEL  = "nvidia/llama-3.2-nemoretriever-300m-embed-v1"
NVIDIA_BASE_URL     = "https://integrate.api.nvidia.com/v1"
EMBED_DELAY_SECONDS = 0.5  

nvidia_embed_client = OpenAI(
    api_key=os.environ["NVIDIA_API_KEY"],
    base_url=NVIDIA_BASE_URL,
)

import asyncio
class NvidiaEmbeddings(BaseRagasEmbeddings):
    """
    Ragas-compatible wrapper around NVIDIA NIM embedding endpoint.
    Includes proper handling for asymmetric models (query vs. passage).
    """
    def _sync_embed(self, text: str, input_type: str) -> t.List[float]:
        """Internal synchronous method to handle the actual API call."""
        time.sleep(EMBED_DELAY_SECONDS)
        response = nvidia_embed_client.embeddings.create(
            model=NVIDIA_EMBED_MODEL,
            input=text,
            encoding_format="float",
            # THE FIX: Asymmetric models require the input_type parameter
            extra_body={"input_type": input_type} 
        )
        return response.data[0].embedding

    def embed_documents(self, texts: t.List[str]) -> t.List[t.List[float]]:
        # Documents are stored as "passages"
        return [self._sync_embed(t_, input_type="passage") for t_ in texts]

    def embed_query(self, text: str) -> t.List[float]:
        # Search queries are embedded as "queries"
        return self._sync_embed(text, input_type="query")

    # ── ASYNC METHODS REQUIRED BY RAGAS ─────────────────────
    
    async def aembed_query(self, text: str) -> t.List[float]:
        return await asyncio.to_thread(self._sync_embed, text, "query")

    async def aembed_documents(self, texts: t.List[str]) -> t.List[t.List[float]]:
        return await asyncio.to_thread(self.embed_documents, texts)

    # Note: Ragas specifically awaits `embed_text` during the EmbeddingExtractor phase.
    # Making this an async def prevents an 'awaiting a list' TypeError.
    async def embed_text(self, text: str) -> t.List[float]:
        # During the extraction phase, it is embedding document chunks (passages)
        return await asyncio.to_thread(self._sync_embed, text, "passage")

generator_embeddings = NvidiaEmbeddings()


# ─────────────────────────────────────────────
# 3. BUILD & ENRICH THE KNOWLEDGE GRAPH
# ─────────────────────────────────────────────
from ragas.testset.graph import KnowledgeGraph, Node, NodeType, Relationship
from ragas.testset.transforms import (
    apply_transforms,
    HeadlinesExtractor,
    HeadlineSplitter,
    SummaryExtractor,
    KeyphrasesExtractor,
    EmbeddingExtractor,
    CosineSimilarityBuilder,
)
from ragas.run_config import RunConfig

# RunConfig controls retry/backoff for all LLM calls during transforms.
# max_workers=2 is safe for most endpoints; raise to 4 for higher throughput.
run_config = RunConfig(
    max_retries=10,
    max_wait=120,
    timeout=180,
    max_workers=2,
)

# # ── Option A: Build graph from scratch ────────────────────────────────
# Use this on first run or whenever you add/change documents.
# Delete these lines and switch to Option B for subsequent runs.
# print("Building KnowledgeGraph...")
# kg = KnowledgeGraph()
# for doc in docs:
#     kg.nodes.append(
#         Node(
#             type=NodeType.DOCUMENT,
#             properties={
#                 "page_content": doc.page_content,
#                 "document_metadata": doc.metadata,
#             },
#         )
#     )
# print(f"  Initial graph: {kg}")

# print("Applying transforms (this may take several minutes)...")
# transforms = [
#     # Extracts markdown H1/H2/H3 headlines from each document.
#     # Documents without headers are silently skipped by HeadlineSplitter.
#     HeadlinesExtractor(llm=generator_llm),

#     # Splits documents into per-section chunk nodes.
#     # min_tokens=100 avoids tiny, low-quality chunks.
#     HeadlineSplitter(min_tokens=100),

#     # Generates a short summary for every node (documents + chunks).
#     SummaryExtractor(llm=generator_llm),

#     # Extracts key phrases for retrieval-aware query generation.
#     KeyphrasesExtractor(llm=generator_llm),

#     # Embeds every node using NVIDIA NIM.
#     EmbeddingExtractor(embedding_model=generator_embeddings),

#     # Builds cosine-similarity edges between semantically related nodes.
#     # 0.5 balances relationship density vs. quality for a mixed corpus.
#     # Lower → denser graph, more multi-hop paths.
#     # Higher → fewer but higher-quality relationships.
#     CosineSimilarityBuilder(threshold=0.85),
# ]
# apply_transforms(kg, transforms, run_config=run_config)
# print(f"  Enriched graph: {kg}")

# GRAPH_PATH = "~/Documents/KGsAuto/services/rag_system/evaluation/knowledge_graph.json"

# kg.save(GRAPH_PATH)
# print(f"  Graph saved to '{GRAPH_PATH}'")

# ── Option B: Load a previously saved graph ───────────────────────────
# Uncomment these two lines and comment out Option A above to skip
# re-enrichment on subsequent runs — saves significant time and API cost.
#
GRAPH_PATH = "knowledge_graph.json"
kg = KnowledgeGraph.load(GRAPH_PATH)
print(f"  Loaded graph: {kg}")


def prepare_multihop_compatibility_graph(kg: KnowledgeGraph) -> None:
    for node in kg.nodes:
        keyphrases = node.get_property("keyphrases")
        if keyphrases and not node.get_property("themes"):
            node.properties["themes"] = keyphrases

    existing_keyphrase_pairs = {
        frozenset((rel.source.id, rel.target.id))
        for rel in kg.relationships
        if rel.type == "keyphrases_overlap"
    }
    added_overlap_relationships = 0

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
        if overlapped_items and pair_key not in existing_keyphrase_pairs:
            kg.relationships.append(
                Relationship(
                    type="keyphrases_overlap",
                    source=rel.source,
                    target=rel.target,
                    bidirectional=rel.bidirectional,
                    properties={"overlapped_items": overlapped_items},
                )
            )
            existing_keyphrase_pairs.add(pair_key)
            added_overlap_relationships += 1

    print(f"  Added keyphrase-overlap relationships for multi-hop generation: {added_overlap_relationships}")


prepare_multihop_compatibility_graph(kg)


# # ─────────────────────────────────────────────
# # 4. GENERATE THE TESTSET
# # ─────────────────────────────────────────────
# from ragas.testset import TestsetGenerator
# from ragas.testset.synthesizers import (
#     SingleHopSpecificQuerySynthesizer,
#     MultiHopAbstractQuerySynthesizer,
#     MultiHopSpecificQuerySynthesizer,
# )
# from ragas.testset.persona import Persona

# # ── Personas ───────────────────────────────────────────────────────────
# # Tailor role descriptions to match your document domain.
# persona_list = [
#     Persona(
#         name="Curious Student",
#         role_description="A student seeking to understand key concepts and facts from the documents.",
#     ),
#     Persona(
#         name="Domain Expert",
#         role_description="An expert who asks precise, detailed questions to verify specific information.",
#     ),
#     Persona(
#         name="General Reader",
#         role_description="A non-specialist who asks broad, conceptual questions about the topic.",
#     ),
# ]

# # ── Query distribution ─────────────────────────────────────────────────
# # With 10+ documents, all three synthesizers are active.
# # Weights must sum to 1.0.
# #
# #   SingleHopSpecific → direct fact retrieval    (tests recall & precision)
# #   MultiHopAbstract  → cross-doc reasoning      (tests conceptual depth)
# #   MultiHopSpecific  → multi-doc fact chaining  (tests multi-hop retrieval)
# query_distribution = [
#     # (SingleHopSpecificQuerySynthesizer(llm=generator_llm), 0.5),
#     # (MultiHopAbstractQuerySynthesizer(llm=generator_llm),  0.25),
#     # (MultiHopSpecificQuerySynthesizer(llm=generator_llm),  0.25),
# ]

# generator = TestsetGenerator(
#     llm=generator_llm,
#     embedding_model=generator_embeddings,
#     knowledge_graph=kg,
#     persona_list=persona_list,
# )

# # Rule of thumb: 3–5 samples per document.
# #   10 docs  → TESTSET_SIZE = 30–50
# #   20 docs  → TESTSET_SIZE = 60–100
# TESTSET_SIZE = 10

# print(f"Generating testset ({TESTSET_SIZE} samples)...")
# testset = generator.generate(
#     testset_size=TESTSET_SIZE,
#     query_distribution=query_distribution,
#     run_config=run_config,
# )

# ─────────────────────────────────────────────
# 4. GENERATE THE TESTSET
# ─────────────────────────────────────────────
from ragas.testset import TestsetGenerator
from ragas.testset.synthesizers import (
    SingleHopSpecificQuerySynthesizer,
    MultiHopAbstractQuerySynthesizer,
    MultiHopSpecificQuerySynthesizer,
)
from ragas.testset.persona import Persona

# 1. Explicit Personas (Prevents the 'ValueError: No nodes that satisfied...' crash)
persona_list = [
    Persona(name="Curious Student", role_description="A student seeking to understand key concepts."),
    Persona(name="Domain Expert", role_description="An expert who asks precise, detailed questions."),
]

nodes_with_keyphrases = sum(
    1 for node in kg.nodes if node.type.name in {"CHUNK", "DOCUMENT"} and node.get_property("keyphrases")
)
if nodes_with_keyphrases == 0:
    raise ValueError(
        "The loaded knowledge graph has no nodes with `keyphrases`. "
        "Rebuild it with KeyphrasesExtractor before generating a testset."
    )
print(f"  Nodes available for single-hop generation: {nodes_with_keyphrases}")

# 2. Explicit Distribution
#   SingleHopSpecific → direct fact retrieval
#   MultiHopAbstract  → cross-section / cross-document reasoning
#   MultiHopSpecific  → fact chaining through shared keyphrases
query_distribution = [
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

# 3. Initialize Generator
generator = TestsetGenerator(
    llm=generator_llm,
    embedding_model=generator_embeddings,
    knowledge_graph=kg,
    persona_list=persona_list, 
)

# 4. Set a high buffer. Ragas aggressively drops questions if the LLM 
# formats the JSON slightly wrong or judges the question as "too vague".
# Asking for 30 gives the system enough runway to output at least a few valid rows.
TESTSET_SIZE = 30

print(f"Generating testset (Targeting {TESTSET_SIZE} samples)...")
testset = generator.generate(
    testset_size=TESTSET_SIZE,
    query_distribution=query_distribution,
    run_config=run_config,
)


# ─────────────────────────────────────────────
# 5. EXPORT & INSPECT RESULTS
# ─────────────────────────────────────────────
import pandas as pd

df: pd.DataFrame = testset.to_pandas()
if df.empty:
    raise RuntimeError(
        "Ragas generated an empty testset. Check the LLM endpoint output and rerun with "
        "with_debugging_logs=True in generator.generate() for dropped-question details."
    )

print("\n── Testset Preview ──────────────────────────────")
# Print the exact column names Ragas generated so you know what you have
print("Available columns:", df.columns.tolist())

# Safely print the first few rows of the entire dataframe
print(df.head())

CSV_PATH = "~/Documents/KGsAuto/services/rag_system/evaluation/testset.csv"
df.to_csv(CSV_PATH, index=False)
print(f"\nFull testset saved to '{CSV_PATH}'")

# Optional: convert to HuggingFace Dataset for Ragas evaluation
# from datasets import Dataset
# hf_dataset = Dataset.from_pandas(df)