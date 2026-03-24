"""
Simple CLI to run the entity linking pipeline
Run with:

python -m entity_linking.cli
"""

import os
import logging
from entity_linking.pipeline import run_pipeline
from llms import get_llm

def main():
    # ----- configuration -----
    kg_dir = os.getenv("EL_KG_DIR", "data/extracted")
    output_dir = os.getenv("EL_OUTPUT_DIR", "data/import_linked")
    model = os.getenv("EL_MODEL", "gpt-5")
    provider = os.getenv("EL_PROVIDER", "proxypal")

    max_iterations = int(os.getenv("EL_MAX_ITERATIONS", "10"))
    score_threshold = float(os.getenv("EL_SCORE_THRESHOLD", "0.85"))
    limit = int(os.getenv("EL_LIMIT", "10"))
    max_workers = int(os.getenv("EL_MAX_WORKERS", "8"))
    log_level = os.getenv("EL_LOG_LEVEL", "INFO").upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # ----- show configuration -----
    print("Starting Entity Linking Pipeline")
    print("Input folder:", kg_dir)
    print("Output folder:", output_dir)
    print("Model:", model)
    print("Provider:", provider)
    print("Score threshold:", score_threshold)
    print("Max workers:", max_workers)
    print()

    llm = get_llm(provider, model_name=model)

    stats = run_pipeline(
        kg_dir=kg_dir,
        output_dir=output_dir,
        llm=llm,
        max_iterations=max_iterations,
        limit=limit,
        score_threshold=score_threshold,
        max_workers=max_workers,
    )
    # ----- print results -----
    print("\nPipeline finished\n")

    print("Files processed:", stats.get("files_processed", 0))
    print("Total merges:", stats.get("total_merges", 0))
    print("Iterations:", stats.get("iterations", 0))
    print("Remaining entities:", stats.get("remaining_entities", 0))

    # ----- show merged IDs -----
    if "id_remap" in stats:
        print("\nMerged entities:")
        for old_id in stats["id_remap"]:
            new_id = stats["id_remap"][old_id]
            print(old_id, "->", new_id)


if __name__ == "__main__":
    main()