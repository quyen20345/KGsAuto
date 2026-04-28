from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import RunConfig
from .pipelines.stage1_pipeline import run_stage1
from .pipelines.stage2_pipeline import run_stage2
from .pipelines.stage3_pipeline import run_stage3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Entity Resolution Pipeline")
    p.add_argument("--input-dir", default="mock_data")
    p.add_argument("--artifacts-dir", default="data/entity_resolution/artifacts")
    p.add_argument("--run-id", default=None)
    p.add_argument("--collection-name", default=None)

    # Storage
    p.add_argument("--store-backend", default="qdrant", choices=["qdrant", "memory"])
    p.add_argument("--qdrant-url", default="http://localhost:6333")

    # Embedding
    p.add_argument("--embedding-model", default="paraphrase-multilingual-mpnet-base-v2")
    p.add_argument("--embedding-dim", type=int, default=768)

    # Clustering
    p.add_argument("--min-cluster-size", type=int, default=2)
    p.add_argument("--min-samples", type=int, default=1)
    p.add_argument("--cluster-threshold", type=float, default=0.6) # 0.72
    p.add_argument("--enable-llm-blocking", action="store_true", default=None,
                   help="Use LLM to determine blocking strategy (default: True)")
    p.add_argument("--no-llm-blocking", action="store_false", dest="enable_llm_blocking",
                   help="Use hard-coded primary_type blocking instead of LLM")

    # LLM Configuration
    p.add_argument("--llm-provider", default="OpenAICompatible", choices=["openai", "anthropic", "OpenAICompatible"])
    p.add_argument("--llm-model", default="cx/gpt-5.3-codex")
    p.add_argument("--llm-api-key", help="API key for LLM provider")

    # Stage selection
    p.add_argument("--stage", default="all", choices=["stage1", "stage2", "stage3", "all"])
    return p


def main() -> None:
    args = build_parser().parse_args()
    cfg = RunConfig(
        input_dir=Path(args.input_dir),
        artifacts_dir=Path(args.artifacts_dir),
        run_id=args.run_id or RunConfig(input_dir=Path(args.input_dir)).run_id,
        collection_name=args.collection_name,

        # Embedding
        embedding_model=args.embedding_model,
        embedding_dim=args.embedding_dim,

        # Clustering
        min_cluster_size=args.min_cluster_size,
        min_samples=args.min_samples,
        cluster_similarity_threshold=args.cluster_threshold,
        enable_llm_blocking=args.enable_llm_blocking if args.enable_llm_blocking is not None else True,

        # Storage
        store_backend=args.store_backend,
        qdrant_url=args.qdrant_url,

        # LLM
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_api_key=args.llm_api_key,
    )

    outputs: dict[str, dict] = {}
    if args.stage in {"stage1", "all"}:
        s1 = run_stage1(cfg)
        outputs["stage1"] = s1.__dict__
    if args.stage in {"stage2", "all"}:
        s2 = run_stage2(cfg)
        outputs["stage2"] = s2.__dict__
    if args.stage in {"stage3", "all"}:
        s3 = run_stage3(cfg)
        outputs["stage3"] = s3.__dict__

    print(json.dumps({"run_id": cfg.run_id, "outputs": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
