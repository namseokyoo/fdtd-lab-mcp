from __future__ import annotations
import csv
from pathlib import Path
from typing import Any

def export_monitor_csv(rows: list[dict[str, Any]], path: str) -> dict[str, Any]:
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames=['run_id','case_id','object','property','value','monitor','result','wavelength_m','result_value','status']
    with p.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fieldnames); w.writeheader()
        for row in rows: w.writerow({k: row.get(k) for k in fieldnames})
    return {"path": str(p), "rows": len(rows)}
