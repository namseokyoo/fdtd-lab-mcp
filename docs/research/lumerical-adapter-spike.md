# Lumerical Adapter Spike — Phase 3

## Goal

Check real adapter paths without making normal tests depend on Ansys Lumerical installation or a license.

## Result

Phase 3 is implemented as non-invasive detection adapters:

- `AnsysCoreAdapter.status()` lazily imports `ansys.lumerical.core` and reports package/module details when available.
- `LumapiAdapter.status()` lazily imports direct `lumapi` and reports availability when available.
- Both real adapters intentionally refuse `open_project()` in Phase 3 to prevent accidental license-consuming or mutating operations before a real `.fsp` and local installation are confirmed.
- Normal implementation uses `FakeLumericalAdapter` by default.

## Next real-integration questions for 형

1. Which company local-network machine has Ansys Lumerical installed and licensed?
2. Use `ansys-lumerical-core` as the first real adapter path; use direct `lumapi` only as fallback if core cannot inspect/run the required workflows.
3. Can we use a non-sensitive sample `.fsp` for the first integration test?
4. Should real integration run with GUI hidden/headless or visible first for safety?

## Gated test policy

Normal CI/test command:

```bash
python -m pytest
```

Real integration should later use:

```bash
python -m pytest -m lumerical
```

No real `.fsp` mutation/run should be enabled until adapter capability is confirmed against a sample file.
