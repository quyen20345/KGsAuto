import json
import argparse
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import time

from llms import get_llm
from extract.prompt import get_extraction_prompt

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class KGExtractor:
    def __init__(self, provider: str = "gemini", model_name: str = "gemma-3-27b-it", max_retries: int = 3, save_failed: bool = True):
        self.llm = get_llm(provider, model_name=model_name)
        self.max_retries = max_retries
        self.save_failed = save_failed
        self.logger = logging.getLogger(__name__)
        
    def extract_from_text(self, text: str, doc_id: int, file_path: Optional[str] = None)-> Optional[Dict[str, Any]]:
        """
        Extracts entities and relationships directly from a string of text.
        Includes retry logic for transient failures.
        """
        start_time = datetime.now()

        for attempt in range(self.max_retries):
            try:
                prompt = get_extraction_prompt(text, doc_id)
                response = self.llm.generate(prompt)

                # Clean and parse the response
                raw_content = response.content
                model = response.model
                usage_tokens = response.usage_tokens

                # Remove markdown code blocks
                cleaned_content = raw_content.replace("```json", "").replace("```", "").strip()

                # Remove <think> tags if present
                if "<think>" in cleaned_content and "</think>" in cleaned_content:
                    # Extract content after </think> tag
                    cleaned_content = cleaned_content.split("</think>", 1)[1].strip()

                # Parse the cleaned string into a JSON object
                kg_data = json.loads(cleaned_content)

                # Calculate processing time
                end_time = datetime.now()
                processing_time = end_time - start_time

                # Count nodes and relationships
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
                self.logger.error(f"JSON parsing error for {file_path or doc_id} (attempt {attempt + 1}/{self.max_retries}): {e}")
                self.logger.debug(f"Raw response content (first 500 chars): {cleaned_content[:500]}")

                # Save failed response to file for debugging
                if self.save_failed and attempt == self.max_retries - 1:
                    failed_dir = Path("data/failed_responses")
                    failed_dir.mkdir(parents=True, exist_ok=True)
                    failed_file = failed_dir / f"{doc_id}_failed.txt"
                    with open(failed_file, "w", encoding="utf-8") as f:
                        f.write(f"Error: {e}\n\n")
                        f.write(f"Raw content:\n{cleaned_content}")
                    self.logger.error(f"Failed response saved to {failed_file}")
                    return None
                # Wait before retry
                time.sleep(2 ** attempt)

            except Exception as e:
                self.logger.error(f"Error extracting from {file_path or doc_id} (attempt {attempt + 1}/{self.max_retries}): {type(e).__name__}: {e}")
                if attempt == self.max_retries - 1:
                    return None
                # Wait before retry (exponential backoff)
                time.sleep(2 ** attempt)

        return None
        
       
    
    def extract_from_markdown(self, file_path: Path) -> Optional[Dict[str, Any]]:
            """
            reads markdown file and extracts knowledge graph data.
            """
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Auto-generate doc_id from filename.
            doc_id = file_path.stem

            return self.extract_from_text(text=content, doc_id=doc_id, file_path=str(file_path))


    def extract_from_dir(self, input_dir: str = "data/raw/uet", output_dir: str = "data/extracted"):
        in_dir = Path(input_dir)
        out_dir = Path(output_dir)

        # Check directory exists.
        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)
        md_files = list(in_dir.glob("*.md")) # Gets list files to extract.

        success_count = 0
        failed_files = []

        self.logger.info(f"Starting extraction from {input_dir}")
        self.logger.info(f"Found {len(md_files)} markdown files")

        for idx, md_file in enumerate(md_files, 1):
            output_path = out_dir / f"{md_file.stem}_kg.json"

            if output_path.exists():
                self.logger.info(f"[{idx}/{len(md_files)}] Skipped (already extracted) -> {md_file.name}")
                continue

            self.logger.info(f"[{idx}/{len(md_files)}] Processing -> {md_file.name}")

            try:
                result = self.extract_from_markdown(md_file)
                if result:
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=4)
                    success_count += 1
                    self.logger.info(f"[{idx}/{len(md_files)}] ✓ Saved -> {output_path.name}")
                else:
                    failed_files.append(md_file.name)
                    self.logger.warning(f"[{idx}/{len(md_files)}] ✗ Failed -> {md_file.name}")
            except Exception as e:
                failed_files.append(md_file.name)
                self.logger.error(f"[{idx}/{len(md_files)}] ✗ Error processing {md_file.name}: {e}")

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Batch Process Complete!")
        self.logger.info(f"Success: {success_count}/{len(md_files)} files")
        if failed_files:
            self.logger.warning(f"Failed files ({len(failed_files)}):")
            for failed_file in failed_files:
                self.logger.warning(f"  - {failed_file}")
        self.logger.info(f"{'='*60}")
    
            

if __name__ == "__main__":
    # Setup Argument Parser
    parser = argparse.ArgumentParser(description="Extract KG from a directory of Markdown files.")
    parser.add_argument("--dir", type=str, default="data/raw/uet", help="Input directory containing .md files")
    parser.add_argument("--out", type=str, default="data/extracted", help="Output directory for JSON files")
    args = parser.parse_args()

    # extractor = KGExtractor(provider="gemini", model_name="gemma-3-27b-it")
    # extractor = KGExtractor(provider="gemini", model_name="gemini-2.5-flash")
    extractor = KGExtractor(provider="proxypal", model_name="gpt-5")
    # extractor = KGExtractor(provider="proxypal", model_name="qwen3-coder-plus")
    extractor.extract_from_dir(input_dir=args.dir, output_dir=args.out)
        