from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "uet"
EXTRACTED_DIR = PROJECT_ROOT / "data" / "extracted"
ER_ARTIFACTS_DIR = PROJECT_ROOT / "data" / "entity_resolution" / "artifacts"
DB_PATH = PROJECT_ROOT / "data" / "pipeline_state.db"
