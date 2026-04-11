import json
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import time

from services.llms import get_llm
from services.extraction.prompt import get_extraction_prompt


class KGExtractorV2:
    def __init__(self, provider: str, model_name: str, max_retries: int = 3, save_failed: bool = True):
        self.llm = get_llm(provider, model_name=model_name)
        self.model_name = model_name
        self.max_retries = max_retries
        self.save_failed = save_failed

    def extract_from_text(self, text: str, doc_id: str, file_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        start_time = datetime.now()

        for attempt in range(self.max_retries):
            try:
                prompt = get_extraction_prompt(text, doc_id, self.model_name)
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

                processing_time = datetime.now() - start_time
                node_count = len(kg_data.get("nodes", []))
                relation_count = len(kg_data.get("relationships", []))

                return {
                    "LLM": model,
                    "File": file_path or f"doc_{doc_id}",
                    "Processing Time": str(processing_time),
                    "Node count": node_count,
                    "Relation count": relation_count,
                    "nodes": kg_data.get("nodes", []),
                    "relationships": kg_data.get("relationships", []),
                    "doc_id": doc_id,
                    "model": model,
                    "usage_tokens": usage_tokens,
                }

            except json.JSONDecodeError as e:
                if self.save_failed and attempt == self.max_retries - 1:
                    failed_dir = Path("data/failed_responses")
                    failed_dir.mkdir(parents=True, exist_ok=True)
                    failed_file = failed_dir / f"{doc_id}_failed_v2.txt"

                    with open(failed_file, "w", encoding="utf-8") as f:
                        f.write(f"Error: {e}\n\n")
                        f.write(f"Raw content:\n{raw_content if 'raw_content' in locals() else 'N/A'}")

                    print(f"JSON parse failed: {file_path or doc_id}")
                    print(f"Saved failed response to: {failed_file}")
                    return None

                time.sleep(2 ** attempt)

            except Exception as e:
                if attempt == self.max_retries - 1:
                    print(f"Error extracting from {file_path or doc_id}: {type(e).__name__}: {e}")
                    return None

                time.sleep(2 ** attempt)

        return None

    def extract_from_markdown(self, file_path: Path) -> Optional[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        doc_id = file_path.stem
        return self.extract_from_text(text=content, doc_id=doc_id, file_path=str(file_path))

    def extract_from_dir(self, input_dir: str = "data/raw/uet", output_dir: str = "data/extracted"):
        in_dir = Path(input_dir)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        md_files = list(in_dir.glob("*.md"))
        success_count = 0
        failed_files = []

        print(f"Starting extraction from: {input_dir}")
        print(f"Found {len(md_files)} markdown files")

        for idx, md_file in enumerate(md_files, 1):
            output_path = out_dir / f"{md_file.stem}_kg_v2.json"

            if output_path.exists():
                print(f"[{idx}/{len(md_files)}] Skipped -> {md_file.name}")
                continue

            print(f"[{idx}/{len(md_files)}] Processing -> {md_file.name}")

            try:
                result = self.extract_from_markdown(md_file)

                if result:
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)

                    success_count += 1
                    print(f"[{idx}/{len(md_files)}] Saved -> {output_path.name}")
                else:
                    failed_files.append(md_file.name)
                    print(f"[{idx}/{len(md_files)}] Failed -> {md_file.name}")

            except Exception as e:
                failed_files.append(md_file.name)
                print(f"[{idx}/{len(md_files)}] Error -> {md_file.name}: {e}")

        print("\n" + "=" * 60)
        print("Batch Process Complete!")
        print(f"Success: {success_count}/{len(md_files)} files")

        if failed_files:
            print(f"Failed files ({len(failed_files)}):")
            for failed_file in failed_files:
                print(f"  - {failed_file}")

        print("=" * 60)


if __name__ == "__main__":
    extractor = KGExtractorV2(
        provider="proxypal",
        model_name="gpt-5",
        max_retries=3,
        save_failed=True,
    )

    extractor.extract_from_dir(
        input_dir="data/raw/uet",
        output_dir="data/extracted",
    )
