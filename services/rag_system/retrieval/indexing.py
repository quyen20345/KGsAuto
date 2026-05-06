"""Markdown document indexing"""

from typing import Optional

from tqdm import tqdm

from services.rag_system.retrieval.chunking import MarkdownChunker
from services.rag_system.retrieval.document import DocumentStore


class MarkdownIndexer:
    """Index markdown documents to Qdrant"""

    def __init__(self, config):
        self.config = config
        self.chunker = MarkdownChunker(config)

    def index_all(self, limit: Optional[int] = None, force: bool = False) -> dict:
        store = DocumentStore(self.config)

        if force and store.collection_exists():
            print(f"Force re-indexing: deleting existing collection '{self.config.markdown_collection}'")
            store.delete_collection()

        if not store.collection_exists():
            store.create_collection()

        markdown_files = sorted(self.config.markdown_dir.rglob("*.md"))
        if limit:
            markdown_files = markdown_files[:limit]

        if not markdown_files:
            print(f"No markdown files found in {self.config.markdown_dir}")
            return {"files_processed": 0, "chunks_created": 0, "chunks_indexed": 0}

        print(f"Found {len(markdown_files)} markdown files to index")

        all_chunks = []
        files_processed = 0

        print("\n1. Chunking markdown files...")
        for md_path in tqdm(markdown_files, desc="Chunking"):
            try:
                chunks = self.chunker.chunk_file(md_path)
                all_chunks.extend(chunks)
                files_processed += 1
            except Exception as e:
                print(f"\n✗ Error chunking {md_path.name}: {e}")

        print(f"✓ Created {len(all_chunks)} chunks from {files_processed} files")

        print("\n2. Preparing chunks for indexing...")
        chunk_payloads = []
        for chunk in all_chunks:
            payload = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "source_path": chunk.source_path,
                "title": chunk.title,
                "section": chunk.section,
                "text": chunk.text,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "chunk_index": chunk.chunk_index,
                **chunk.metadata,
            }
            chunk_payloads.append(payload)

        print("\n3. Indexing to Qdrant...")
        chunks_indexed = store.upsert_chunks(chunk_payloads, show_progress=True)

        stats = {
            "files_processed": files_processed,
            "chunks_created": len(all_chunks),
            "chunks_indexed": chunks_indexed,
        }

        print("\n" + "=" * 60)
        print("Indexing Complete!")
        print("=" * 60)
        print(f"Files processed: {stats['files_processed']}")
        print(f"Chunks created: {stats['chunks_created']}")
        print(f"Chunks indexed: {stats['chunks_indexed']}")
        print(f"Collection: {self.config.markdown_collection}")
        print("=" * 60)

        return stats
