**1. Run the Evaluation (Runner)**
Use the `run-comparison` command (which triggers `runner.py`) to run all 4 RAG modes across your generated `testset.csv`:
```bash
conda run -n py312 python -m services.rag_system.cli evaluate run-comparison \
  --dataset data/evaluation/ragas/testset.csv \
  --output data/evaluation/rag_eval_comparison.jsonl
```
*(You can also pass specific modes using `--mode semantic_search --mode hybrid` etc. if you don't want to run all of them)*

**2. Run the Scoring (Scoring)**
Once the generation finishes, pass the resulting JSONL file into the `score` command (which triggers `scoring.py`) to run the Ragas metrics on them:
```bash
conda run -n py312 python -m services.rag_system.cli evaluate score \
  --results data/evaluation/rag_eval_comparison.jsonl \
  --output data/evaluation/rag_eval_scored.jsonl
```

*(Note: The commands above use `conda run -n py312` as per your project guidelines. If you have already activated your `py312` environment in your terminal via `conda activate py312`, you can omit `conda run -n py312` and just start with `python -m ...`)*

Generate or refresh the Ragas testset with:
```bash
conda run -n py312 python -m services.rag_system.evaluation.gen_testset \
  --graph-path data/evaluation/ragas/knowledge_graph.json \
  --output data/evaluation/ragas/testset.csv
```
