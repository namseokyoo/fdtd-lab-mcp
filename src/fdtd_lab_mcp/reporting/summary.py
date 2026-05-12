from __future__ import annotations
from pathlib import Path
from typing import Any

def generate_summary(path: str, *, run_id: str, parameter: dict[str, Any], result_rows: list[dict[str, Any]], warnings: list[str] | None = None) -> dict[str, Any]:
    warnings=warnings or []
    vals=[r for r in result_rows if isinstance(r.get('result_value'), (int,float))]
    best=max(vals, key=lambda r: r['result_value']) if vals else None
    lines=[f"# FDTD Sweep Summary: {run_id}", "", "## Parameter", f"- Object: `{parameter.get('object')}`", f"- Property: `{parameter.get('property')}`", f"- Values: `{parameter.get('values')}`", "", "## Results", f"- Rows: {len(result_rows)}"]
    if best: lines += [f"- Best case: `{best.get('case_id')}` value `{best.get('value')}` result `{best.get('result_value')}`"]
    if warnings: lines += ["", "## Warnings"] + [f"- {w}" for w in warnings]
    lines += ["", "## Basic interpretation", "- Fake/Phase-3 output validates workflow shape; physics interpretation requires real Lumerical integration."]
    p=Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding='utf-8')
    return {"path": str(p), "best_case": best}
