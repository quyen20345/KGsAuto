import json
import argparse
from typing import Optional, Dict, Any
from pathlib import Path

from llms import get_llm
from extract.strict_prompt import get_extraction_prompt

class KGExtractor:
    def __init__(self, provider: str = "gemini", model_name: str = "gemma-3-27b-it"):
        self.llm = get_llm(provider, model_name=model_name)
        
    def extract_from_text(self, text: str, doc_id: int)-> Optional[Dict[str, Any]]:
        """ 
        Extracts entities and relationships directly from a string of text.
        """
        prompt = get_extraction_prompt(text, doc_id) # generate the prompt using specific text.
        response = self.llm.generate(prompt) # call llm to generate the output.
        # clean and parse the response.
        raw_content = response.content
        model = response.model
        usage_tokens = response.usage_tokens
        
        cleaned_content = raw_content.replace("```json", "").replace("```", "").strip()
        
        try:
            # Parse the cleaned string into a Json object.
            kg_data = json.loads(cleaned_content)
            return kg_data  # should return content, model, tokens.
        except:
            pass
        
       
    
    def extract_from_markdown(self, file_path: Path) -> Optional[Dict[str, Any]]:
            """
            reads markdown file and extracts knowledge graph data.
            """
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Auto-generate doc_id from filename.
            doc_id = file_path.stem 

            return self.extract_from_text(text=content, doc_id=doc_id)


    def extract_from_dir(self, input_dir: str = "data/raw/uet", output_dir: str = "data/extracted"):
        in_dir = Path(input_dir)
        out_dir = Path(output_dir)

        # Check directory exists.
        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)
        md_files = list(in_dir.glob("*.md")) # Gets list files to extract.

        success_count = 0

        for md_file in md_files:
            result = self.extract_from_markdown(md_file)

            if result:
                output_path = out_dir / f"{md_file.stem}_kg.json"

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)
                success_count += 1
                print(f"Saved -> {output_path.name}")
            else:
                print(f"Failed -> {md_file.name}")

        print(f"Batch Process Complete! Success: {success_count}/{len(md_files)} files.")
    
            

if __name__ == "__main__":
    # Setup Argument Parser
    parser = argparse.ArgumentParser(description="Extract KG from a directory of Markdown files.")
    parser.add_argument("--dir", type=str, default="data/raw/uet", help="Input directory containing .md files")
    parser.add_argument("--out", type=str, default="data/extracted", help="Output directory for JSON files")
    args = parser.parse_args()

    # extractor = KGExtractor(provider="gemini", model_name="gemma-3-27b-it")
    # extractor = KGExtractor(provider="gemini", model_name="gemini-2.5-flash")
    extractor = KGExtractor(provider="proxypal", model_name="gpt-5")
    extractor.extract_from_dir(input_dir=args.dir, output_dir=args.out)
        