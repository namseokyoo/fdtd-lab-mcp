# Real Lumerical Authoring Smoke Check

This check validates the Phase A/B authoring path against a company-local Lumerical installation.

It is **not** a production OLED/FDTD template validation. The tiny project exists only to prove that the MCP can create a blank project, add minimal CAD/source/monitor primitives, save an `.fsp`, reopen it, and optionally run it.

## Prerequisites

- Run only inside the company local-network Lumerical environment.
- A valid Lumerical license must be available.
- Real operations remain gated by `FDTD_LAB_ENABLE_REAL_LUMERICAL=1`.

## Suggested command

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
export FDTD_LAB_ADAPTER=ansys_core
python - <<'PY'
from pathlib import Path
from fdtd_lab_mcp import tools

out_path = Path('/tmp/fdtd_lab_tiny_smoke.fsp')
tools.reset_state(adapter='ansys_core')
created = tools.create_tiny_smoke_project(str(out_path), overwrite=True)
print('created:', created['path'], [o['name'] for o in created['objects']])

inspected = tools.inspect_fsp(str(out_path), readonly=False)
print('inspected:', [o['name'] for o in inspected['objects']])

# Optional: run may fail for environment/material/license reasons. Treat a structured
# failure as a useful diagnostic rather than proof that authoring/save failed.
try:
    run = tools.run_tiny_smoke_project(str(out_path), timeout_sec=120)
    print('run:', run['run']['status'])
except Exception as exc:
    print('run failed structurally:', exc)
PY
```

For direct `lumapi`, use:

```bash
export FDTD_LAB_ADAPTER=lumapi
```
