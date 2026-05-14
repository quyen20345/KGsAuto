"""Command-line interface for Knowledge Graph Extraction Service"""

import argparse
import sys
from pathlib import Path

from services.config import ConfigValidationError, validate_settings
from services.extraction.config import ExtractionConfig
from services.extraction.extract import KGExtractor


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for extraction CLI"""
    parser = argparse.ArgumentParser(
        description="Knowledge Graph Extraction from Markdown Documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract with default settings
  python -m services.extraction.cli

  # Extract with custom directories
  python -m services.extraction.cli --input-dir data/raw/uet --output-dir data/extracted

  # Use different LLM provider
  python -m services.extraction.cli --provider gemini --model gemini-pro

  # Force re-extraction of existing files
  python -m services.extraction.cli --no-skip-existing
        """
    )

    # Input/Output
    parser.add_argument(
        "--input-dir",
        type=str,
        default="data/raw/uet",
        help="Input directory containing markdown files (default: data/raw/uet)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/extracted",
        help="Output directory for extracted JSON files (default: data/extracted)"
    )

    # LLM Configuration
    parser.add_argument(
        "--provider",
        type=str,
        default="OpenAICompatible",
        choices=["OpenAICompatible", "gemini", "ollama"],
        help="LLM provider (default: OpenAICompatible)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="cx/gpt-5.3-codex",
        help="Model name (default: cx/gpt-5.3-codex)"
    )

    # Extraction Behavior
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts on failure (default: 3)"
    )
    parser.add_argument(
        "--save-failed",
        action="store_true",
        default=True,
        help="Save failed responses for debugging (default: True)"
    )
    parser.add_argument(
        "--no-save-failed",
        action="store_false",
        dest="save_failed",
        help="Do not save failed responses"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip files that already have output (default: True)"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_false",
        dest="skip_existing",
        help="Re-extract files even if output exists"
    )
    parser.add_argument(
        "--cluster-max-workers",
        type=int,
        default=1,
        help="Number of clusters to process in parallel (default: 1)"
    )
    parser.add_argument(
        "--cluster-similarity-threshold",
        type=float,
        default=0.3,
        help="Filename-token similarity threshold for clustering (default: 0.3)"
    )

    # Directories
    parser.add_argument(
        "--failed-dir",
        type=str,
        default="data/failed_responses",
        help="Directory for failed responses (default: data/failed_responses)"
    )

    return parser


def main():
    """Main entry point for CLI"""
    parser = build_parser()
    args = parser.parse_args()

    # Validate input directory exists
    input_path = Path(args.input_dir)
    if not input_path.exists():
        print(f"Error: Input directory does not exist: {args.input_dir}")
        sys.exit(1)

    if not input_path.is_dir():
        print(f"Error: Input path is not a directory: {args.input_dir}")
        sys.exit(1)

    try:
        validate_settings("extraction")
    except ConfigValidationError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Create configuration
    config = ExtractionConfig(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        provider=args.provider,
        model_name=args.model,
        max_retries=args.max_retries,
        save_failed=args.save_failed,
        skip_existing=args.skip_existing,
        cluster_max_workers=args.cluster_max_workers,
        cluster_similarity_threshold=args.cluster_similarity_threshold,
        failed_dir=args.failed_dir,
    )

    # Run extraction
    try:
        extractor = KGExtractor(config)
        extractor.extract_from_dir()
    except KeyboardInterrupt:
        print("\n\nExtraction interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFatal error: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
