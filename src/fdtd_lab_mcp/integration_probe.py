from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from fdtd_lab_mcp.adapters import make_adapter
from fdtd_lab_mcp.adapters.real_base import REAL_ENABLE_ENV


def main() -> None:
    parser = argparse.ArgumentParser(description="Company-local Lumerical integration probe for fdtd-lab-mcp")
    parser.add_argument("--adapter", choices=["ansys_core", "lumapi", "fake"], default=os.environ.get("FDTD_LAB_ADAPTER", "ansys_core"))
    parser.add_argument("--fsp", default=os.environ.get("FDTD_LAB_SAMPLE_FSP"), help="Non-sensitive sample .fsp path")
    parser.add_argument("--open", action="store_true", help=f"Actually open the .fsp; requires {REAL_ENABLE_ENV}=1 for real adapters")
    parser.add_argument("--list", action="store_true", help="List objects after opening")
    args = parser.parse_args()

    adapter = make_adapter(args.adapter)
    report = {"adapter": args.adapter, "status": adapter.status()}

    if args.open:
        if not args.fsp:
            raise SystemExit("--fsp or FDTD_LAB_SAMPLE_FSP is required with --open")
        handle = adapter.open_project(str(Path(args.fsp).expanduser()), readonly=True)
        report["opened"] = handle.__dict__
        if args.list:
            report["objects"] = adapter.list_objects(handle.project_id)
        adapter.close(handle.session_id)

    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
