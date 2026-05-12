from __future__ import annotations
import hashlib, json, shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

def sha256_file(path: str | Path) -> str:
    h=hashlib.sha256(); p=Path(path)
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def slugify(text: str) -> str:
    return ''.join(c.lower() if c.isalnum() else '-' for c in text).strip('-') or 'run'

@dataclass
class RunInfo:
    run_id: str
    run_dir: str
    working_fsp: str
    provenance_path: str
    original_checksum: str

class RunManager:
    def __init__(self, runs_root: str | Path = 'runs') -> None:
        self.runs_root=Path(runs_root)
    def create_run_dir(self, base_fsp: str, run_name: str) -> RunInfo:
        base=Path(base_fsp).expanduser()
        if not base.exists(): raise FileNotFoundError(f"base_fsp does not exist: {base_fsp}")
        checksum=sha256_file(base)
        stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
        run_id=f"{stamp}_{slugify(run_name)}"
        run_dir=self.runs_root / run_id
        counter=1
        while run_dir.exists():
            run_dir=self.runs_root / f"{run_id}-{counter}"; counter+=1
        base_dir=run_dir/'base'; case_dir=run_dir/'cases'/'case_0001'; results_dir=run_dir/'results'
        for d in (base_dir, case_dir, results_dir): d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(base, base_dir/'original_copy.fsp')
        working=case_dir/'working.fsp'; shutil.copy2(base, working)
        prov={"run_id": run_dir.name, "base_fsp": str(base), "original_checksum": checksum, "created_at": datetime.now().isoformat(), "changed_variables": [], "adapter": None, "run_status": "created"}
        prov_path=run_dir/'provenance.json'; prov_path.write_text(json.dumps(prov, indent=2), encoding='utf-8')
        return RunInfo(run_dir.name, str(run_dir), str(working), str(prov_path), checksum)
    def append_change(self, provenance_path: str, change: dict) -> None:
        p=Path(provenance_path); data=json.loads(p.read_text(encoding='utf-8')); data.setdefault('changed_variables', []).append(change); p.write_text(json.dumps(data, indent=2), encoding='utf-8')
    def update_status(self, provenance_path: str, status: str, adapter: str | None = None) -> None:
        p=Path(provenance_path); data=json.loads(p.read_text(encoding='utf-8')); data['run_status']=status
        if adapter: data['adapter']=adapter
        p.write_text(json.dumps(data, indent=2), encoding='utf-8')
