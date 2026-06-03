"""Knowledge Graph Extraction from Markdown Documents"""

import asyncio
import json
import logging
import random
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Awaitable, Callable, Iterable, Optional

from apps.pipeline_api.core.extraction.cluster_state import ClusterState
from apps.pipeline_api.core.extraction.clustering import cluster_markdown_files
from apps.pipeline_api.core.extraction.config import ExtractionConfig
from apps.pipeline_api.core.extraction.metrics import ExtractionMetrics
from apps.pipeline_api.core.extraction.prompt import get_extraction_prompt
from apps.pipeline_api.core.config import settings, validate_settings
from apps.pipeline_api.core.extraction.validation import validate_and_log
from apps.pipeline_api.core.llms import get_llm


ProgressEvent = dict[str, Any]
ProgressCallback = Callable[[ProgressEvent], None]
AsyncProgressCallback = Callable[[ProgressEvent], Awaitable[None]]
CancelCallback = Callable[[], bool]


def setup_logger(config: ExtractionConfig) -> logging.Logger:
    """Setup logger with console and file handlers"""
    logger = logging.getLogger("extraction")
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console.setFormatter(console_formatter)
    logger.addHandler(console)

    log_file = config.log_file_path()
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    logger.info(f"Logging to: {log_file}")

    return logger


class KGExtractor:
    """Knowledge Graph Extractor using LLM"""

    def __init__(self, config: ExtractionConfig):
        self.config = config
        self.logger = setup_logger(config)
        self.llm = get_llm(config.provider, model_name=config.model_name)
        self.metrics = ExtractionMetrics()
        self._random = random.Random(config.random_seed)
        self._metrics_lock = Lock()
        self._failed_files_lock = Lock()

        self.logger.info("Initialized KGExtractor")
        self.logger.info(f"  Provider: {config.provider}")
        self.logger.info(f"  Model: {config.model_name}")
        self.logger.info(f"  Input: {config.input_dir}")
        self.logger.info(f"  Output: {config.output_dir}")
        self.logger.info(f"  Max retries: {config.max_retries}")
        self.logger.info(f"  Skip existing: {config.skip_existing}")

    def extract_from_text(
        self,
        text: str,
        chunk_id: str,
        file_path: Optional[str] = None,
        core_pack: Optional[str] = None,
        local_context: Optional[str] = None,
        rolling_summary: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        start_time = datetime.now()

        for attempt in range(self.config.max_retries):
            try:
                prompt = get_extraction_prompt(
                    text,
                    chunk_id,
                    self.config.model_name,
                    core_pack=core_pack,
                    local_context=local_context,
                    rolling_summary=rolling_summary,
                    context_char_budget=self.config.context_char_budget,
                    truncation_suffix=self.config.truncation_suffix,
                )

                self.logger.debug(
                    f"Calling LLM for {chunk_id} (attempt {attempt + 1}/{self.config.max_retries})"
                )
                response = self.llm.generate(prompt)

                raw_content = response.content
                model = response.model
                usage_tokens = response.usage_tokens

                cleaned_content = raw_content.replace("```json", "").replace("```", "").strip()
                if "<think>" in cleaned_content and "</think>" in cleaned_content:
                    cleaned_content = cleaned_content.split("</think>", 1)[1].strip()

                kg_data = json.loads(cleaned_content)
                if "nodes" not in kg_data or "relationships" not in kg_data:
                    raise ValueError("Missing 'nodes' or 'relationships' in response")

                is_valid = validate_and_log(kg_data, chunk_id, self.logger)
                if not is_valid:
                    self.logger.warning(f"Validation warnings for {chunk_id}, but continuing...")

                processing_time = datetime.now() - start_time
                node_count = len(kg_data.get("nodes", []))
                relation_count = len(kg_data.get("relationships", []))

                self.logger.info(
                    f"Extracted {node_count} nodes, {relation_count} relationships from {chunk_id}"
                )

                return {
                    "LLM": model,
                    "File": file_path or f"doc_{chunk_id}",
                    "Processing Time": str(processing_time),
                    "Node count": node_count,
                    "Relation count": relation_count,
                    "nodes": kg_data.get("nodes", []),
                    "relationships": kg_data.get("relationships", []),
                    "chunk_id": chunk_id,
                    "model": model,
                    "usage_tokens": usage_tokens,
                }

            except json.JSONDecodeError as e:
                self.logger.warning(
                    f"JSON parse error for {chunk_id} (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )

                if self.config.save_failed and attempt == self.config.max_retries - 1:
                    failed_file = self.config.failed_dir / f"{chunk_id}_failed_v2.txt"
                    with open(failed_file, "w", encoding="utf-8") as f:
                        f.write(f"Error: {e}\n\n")
                        f.write(
                            f"Raw content:\n{raw_content if 'raw_content' in locals() else 'N/A'}"
                        )

                    self.logger.error(f"Saved failed response to: {failed_file}")
                    return None

                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(sleep_time)

            except Exception as e:
                self.logger.warning(
                    f"Error extracting from {chunk_id} (attempt {attempt + 1}/{self.config.max_retries}): {type(e).__name__}: {e}"
                )

                if attempt == self.config.max_retries - 1:
                    self.logger.error(
                        f"Failed to extract from {chunk_id} after {self.config.max_retries} attempts"
                    )
                    return None

                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(sleep_time)

        return None

    def extract_from_markdown(self, file_path: Path) -> Optional[dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        chunk_id = file_path.stem
        return self.extract_from_text(text=content, chunk_id=chunk_id, file_path=str(file_path))

    def _cluster_markdown_files(self, md_files: list[Path]) -> list[list[Path]]:
        return cluster_markdown_files(md_files, self.config.cluster_similarity_threshold)

    def _create_cluster_state(self, cluster_name: str) -> ClusterState:
        return ClusterState(cluster_name=cluster_name)

    def _build_core_pack(self) -> Optional[str]:
        if not self.config.core_pack_enabled:
            return None
        return self.config.core_pack_text

    def _build_local_context(self, state: ClusterState) -> Optional[str]:
        if not self.config.local_context_enabled:
            return None

        records = state.sample_entity_records(self.config.local_context_top_k)
        if not records:
            return None

        selected = list(records)
        self._random.shuffle(selected)
        return "\n".join(selected)

    def _build_rolling_summary(self, state: ClusterState) -> Optional[str]:
        if not self.config.rolling_summary_enabled:
            return None

        facts = state.get_summary(self.config.rolling_summary_max_items)
        if not facts:
            return None

        return "\n".join(facts)

    def _update_metrics(self, result: dict[str, Any], processing_time: float) -> None:
        self.metrics.successful += 1
        self.metrics.total_nodes += result.get("Node count", 0)
        self.metrics.total_relationships += result.get("Relation count", 0)
        self.metrics.total_tokens += result.get("usage_tokens") or 0
        self.metrics.total_processing_time += processing_time

    def _record_progress(self, total_files: int, output_name: str | None = None, failed_name: str | None = None) -> None:
        processed = self.metrics.successful + self.metrics.failed + self.metrics.skipped
        if output_name:
            self.logger.info(f"[{processed}/{total_files}] Saved: {output_name}")
        if failed_name:
            self.logger.error(f"[{processed}/{total_files}] Failed: {failed_name}")
        if (processed % self.config.progress_log_every == 0) or processed == total_files:
            self.logger.info(
                "Progress: %s/%s files processed (%s success, %s failed, %s skipped)"
                % (
                    processed,
                    total_files,
                    self.metrics.successful,
                    self.metrics.failed,
                    self.metrics.skipped,
                )
            )

    def _emit_progress(
        self,
        progress_callback: ProgressCallback | None,
        total_files: int,
        file_path: Path,
        status: str,
        output_path: Path | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        if not progress_callback:
            return

        processed = self.metrics.successful + self.metrics.failed + self.metrics.skipped
        event: ProgressEvent = {
            "file": file_path.name,
            "path": str(file_path),
            "status": status,
            "processed": processed,
            "total": total_files,
            "successful": self.metrics.successful,
            "failed": self.metrics.failed,
            "skipped": self.metrics.skipped,
            "progress_pct": int((processed / total_files) * 100) if total_files else 100,
        }
        if output_path is not None:
            event["output_file"] = output_path.name
            event["output_path"] = str(output_path)
        if result is not None:
            event["node_count"] = result.get("Node count", 0)
            event["relation_count"] = result.get("Relation count", 0)
            event["usage_tokens"] = result.get("usage_tokens")

        progress_callback(event)

    def _process_cluster(
        self,
        cluster_index: int,
        cluster_files: list[Path],
        total_files: int,
        failed_files: list[str],
        progress_callback: ProgressCallback | None = None,
        should_cancel: CancelCallback | None = None,
    ) -> None:
        state = self._create_cluster_state(f"cluster_{cluster_index}")
        core_pack = self._build_core_pack()

        for md_file in cluster_files:
            if should_cancel and should_cancel():
                self.logger.info(f"Extraction cancelled before processing: {md_file.name}")
                break

            output_path = self.config.output_dir / f"{md_file.stem}_kg.json"
            if self.config.skip_existing and output_path.exists():
                with self._metrics_lock:
                    self.metrics.skipped += 1
                    self.logger.info(f"Skipped (exists): {md_file.name}")
                    self._record_progress(total_files)
                    self._emit_progress(progress_callback, total_files, md_file, "skipped", output_path=output_path)
                continue

            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            start_time = time.time()
            result = self.extract_from_text(
                text=content,
                chunk_id=md_file.stem,
                file_path=str(md_file),
                core_pack=core_pack,
                local_context=self._build_local_context(state),
                rolling_summary=self._build_rolling_summary(state),
            )
            processing_time = time.time() - start_time

            if result:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                state.add_result(result)
                with self._metrics_lock:
                    self._update_metrics(result, processing_time)
                    self._record_progress(total_files, output_name=output_path.name)
                    self._emit_progress(
                        progress_callback,
                        total_files,
                        md_file,
                        "completed",
                        output_path=output_path,
                        result=result,
                    )
            else:
                with self._failed_files_lock:
                    failed_files.append(md_file.name)
                with self._metrics_lock:
                    self.metrics.failed += 1
                    self._record_progress(total_files, failed_name=md_file.name)
                    self._emit_progress(progress_callback, total_files, md_file, "failed")

    def _sort_markdown_files(self, files: Iterable[Path]) -> list[Path]:
        input_dir = self.config.input_dir.resolve()

        def sort_key(path: Path) -> str:
            try:
                return str(path.resolve().relative_to(input_dir))
            except ValueError:
                return str(path)

        return sorted((Path(path) for path in files if Path(path).suffix.lower() == ".md"), key=sort_key)

    def extract_from_files(
        self,
        files: Iterable[Path],
        progress_callback: ProgressCallback | None = None,
        should_cancel: CancelCallback | None = None,
    ) -> ExtractionMetrics:
        md_files = self._sort_markdown_files(files)
        self.metrics = ExtractionMetrics(total_files=len(md_files))

        self.logger.info("=" * 60)
        self.logger.info(f"Starting extraction from explicit file set under: {self.config.input_dir}")
        self.logger.info(f"Found {len(md_files)} markdown files")
        self.logger.info("=" * 60)

        if not md_files:
            self.metrics.save_to_file(self.config.summary_file_path())
            return self.metrics

        clusters = self._cluster_markdown_files(md_files)
        self.logger.info(f"Formed {len(clusters)} clusters")

        failed_files: list[str] = []
        max_workers = max(1, min(self.config.cluster_max_workers, len(clusters)))
        if max_workers == 1:
            for cluster_index, cluster_files in enumerate(clusters, start=1):
                if should_cancel and should_cancel():
                    self.logger.info("Extraction cancelled before next cluster")
                    break
                self._process_cluster(
                    cluster_index,
                    cluster_files,
                    len(md_files),
                    failed_files,
                    progress_callback=progress_callback,
                    should_cancel=should_cancel,
                )
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(
                        self._process_cluster,
                        index,
                        cluster_files,
                        len(md_files),
                        failed_files,
                        progress_callback,
                        should_cancel,
                    )
                    for index, cluster_files in enumerate(clusters, start=1)
                ]
                for future in as_completed(futures):
                    future.result()

        self.logger.info("=" * 60)
        self.logger.info("Batch Process Complete!")
        self.logger.info(f"Success: {self.metrics.successful}/{self.metrics.total_files} files")
        self.logger.info(f"Failed: {self.metrics.failed}/{self.metrics.total_files} files")
        self.logger.info(f"Skipped: {self.metrics.skipped}/{self.metrics.total_files} files")

        if failed_files:
            self.logger.warning(f"Failed files ({len(failed_files)}):")
            for failed_file in failed_files:
                self.logger.warning(f"  - {failed_file}")

        self.metrics.save_to_file(self.config.summary_file_path())
        self.logger.info(f"\nMetrics saved to: {self.config.summary_file_path()}")
        self.logger.info(str(self.metrics))
        self.logger.info("=" * 60)
        return self.metrics

    def extract_from_dir(
        self,
        progress_callback: ProgressCallback | None = None,
        should_cancel: CancelCallback | None = None,
    ) -> ExtractionMetrics:
        in_dir = self.config.input_dir
        md_files = sorted(in_dir.rglob("*.md"), key=lambda path: str(path.relative_to(in_dir)))
        return self.extract_from_files(
            md_files,
            progress_callback=progress_callback,
            should_cancel=should_cancel,
        )


async def run_extraction(
    *,
    input_dir: Path,
    output_dir: Path,
    files: Iterable[Path] | None = None,
    run_id: str | None = None,
    progress_callback: AsyncProgressCallback | None = None,
    should_cancel: CancelCallback | None = None,
    skip_existing: bool = True,
    failed_dir: Path | None = None,
    provider: str | None = None,
    model_name: str | None = None,
    max_retries: int = 3,
    cluster_max_workers: int = 1,
    cluster_similarity_threshold: float = 0.3,
) -> ExtractionMetrics:
    validate_settings("extraction")

    config_kwargs: dict[str, Any] = {
        "input_dir": input_dir,
        "output_dir": output_dir,
        "provider": provider or settings.llm.provider,
        "model_name": model_name or settings.llm.model,
        "max_retries": max_retries,
        "save_failed": True,
        "skip_existing": skip_existing,
        "cluster_max_workers": cluster_max_workers,
        "cluster_similarity_threshold": cluster_similarity_threshold,
        "failed_dir": failed_dir or Path("data/failed_responses"),
    }
    if run_id:
        config_kwargs["run_id"] = run_id

    config = ExtractionConfig(**config_kwargs)
    extractor = KGExtractor(config)

    selected_files = [Path(file) for file in files] if files is not None else None
    pending_callbacks: list[Future] = []
    loop = asyncio.get_running_loop()

    def emit_progress(event: ProgressEvent) -> None:
        if progress_callback is None:
            return
        pending_callbacks.append(asyncio.run_coroutine_threadsafe(progress_callback(event), loop))

    if selected_files is None:
        metrics = await asyncio.to_thread(
            extractor.extract_from_dir,
            progress_callback=emit_progress,
            should_cancel=should_cancel,
        )
    else:
        metrics = await asyncio.to_thread(
            extractor.extract_from_files,
            selected_files,
            progress_callback=emit_progress,
            should_cancel=should_cancel,
        )

    for future in pending_callbacks:
        await asyncio.wrap_future(future)

    return metrics


if __name__ == "__main__":
    config = ExtractionConfig(
        input_dir="data/raw/uet",
        output_dir="data/extracted",
        provider="OpenAICompatible",
        model_name="cx/gpt-5.3-codex",
    )

    extractor = KGExtractor(config)
    extractor.extract_from_dir()
