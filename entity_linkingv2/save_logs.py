import json
import time 
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Any, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def ensure_parent(path: Path) -> None:
    """ Ensure the parent directory of the given path exists. Create it if it doesn't."""
    path.parent.mkdir(parents=True, exist_ok=True)
        
def write_json_atomic(path: Path, obj: Any) -> None:
    """ Write a JSON object to a file atomically. """
    ensure_parent(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False))
        f.write("\n")
        
@dataclass 
class LogEvent:
    seed_id: str
    
    @staticmethod 
    def make() -> "LogEvent":
        return LogEvent(seed_id="")
    
    
@dataclass 
class checkpoint:
    run_id: str
    created_at: str
    finished_at: Optional[str]
    source_dir: str
    output_dir: str 
    seed_total: int = 0
    processed: int = 0
    cursor: int = 0
    
class SaveLogs:
    def __init__(self, output_dir: str | Path, run_id: str, source_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logs_path = self.output_dir / "entity_linking_logs.jsonl"
        self.remap_path = self.output_dir / "id_remap.json"
        self.checkpoint_path = self.output_dir / "checkpoint.json"
        self.new_nodes_path = self.output_dir / "new_nodes.jsonl"
        
        self._cp = checkpoint(
            run_id=run_id,
            created_at=utc_now(),
            finished_at=None,
            source_dir=str(source_dir),
            output_dir=str(self.output_dir),
            seed_total=0,
            processed=0,
            cursor=0,
        )
        self._save_checkpoint()
        
    # public methods
    def set_seed_total(self, n: int) -> None:
        """ Set the total number of seed entities to process. This is used for tracking progress in the checkpoint."""
        self._cp.seed_total = int(n)
        self._save_checkpoint() 
        
    def set_cursor(self, cursor: int) -> None:
        self._cp.cursor = int(cursor)
        
    def append_event() -> None:
        pass 
    
    def append_remap() -> None:
        pass 
    
    def append_new_nodes() -> None:
        pass
    
    def save_checkpoint(self, finished: bool = False) -> None:
        if finished: self._cp.finished_at = utc_now()
        self._save_checkpoint()
        
    def close(self) -> None:
        """ Finalize the logs. Mark checkpoint as finished."""
        self.save_checkpoint(finished=True)
        
    # helpers
    def _save_checkpoint(self) -> None:
        """ Save the current checkpoint to a JSON file. """
        write_json_atomic(self.checkpoint_path, asdict(self._cp))
        
    # static methods for ... 
    @staticmethod 
    def load_id_remap_map():
        pass 
    
    @staticmethod
    def load_new_nodes_latest():
        pass 