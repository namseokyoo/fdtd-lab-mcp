# Lumerical real adapter usage audit and hardening plan (2026-05-15)

## Official API basis

- Ansys Optics, **Script Commands as Methods - Python API**: almost all Lumerical script commands are exposed as Python methods on a session object; examples use `fdtd.set("x span", 1e-6)` and object constructors such as `fdtd.addfdtd(...)` rather than composing script strings.
- Ansys Optics, **Lumerical Python API Reference**: `eval`, `getv`, and `putv` are low-level script workspace methods and are not recommended unless a specific function requires them; `close` is the default method for closing a session.
- Ansys Optics, **getnamed / setnamed / switchtolayout script commands**: `getnamed(name, property)` reads named-object properties, `setnamed(name, property, value)` mutates named-object properties, and mutation after a run requires `switchtolayout` because analysis mode rejects object edits.
- PyLumerical, **Basic Session Management**: sessions can and should be closed with `fdtd.close()` or a context manager so the Lumerical application exits.

Reference URLs:

- https://optics.ansys.com/hc/en-us/articles/360041579954-Script-Commands-as-Methods-Python-API
- https://optics.ansys.com/hc/en-us/articles/38660003331859-Lumerical-Python-API-Reference
- https://optics.ansys.com/hc/en-us/articles/360034408574-getnamed-Script-command
- https://optics.ansys.com/hc/en-us/articles/360034928793-setnamed-Script-command
- https://optics.ansys.com/hc/en-us/articles/360034923993-switchtolayout-Script-command
- https://lumerical.docs.pyansys.com/version/stable/examples/Sessions_and_Objects/basic_session_management.html

## Corrected code sections

- `src/fdtd_lab_mcp/adapters/real_base.py::ScriptSessionAdapter.get_property`
  - Was: `eval('select(...); fdtd_lab_property_value=get(...);')` plus `getv`.
  - Now: validates object/property names, calls documented wrapper method `session.getnamed(object_name, property_name)`, JSON-normalizes return value.

- `src/fdtd_lab_mcp/adapters/real_base.py::ScriptSessionAdapter.set_property`
  - Was: `putv("fdtd_lab_new_value", value)` plus raw `eval('select(...); set(..., fdtd_lab_new_value);')`.
  - Now: validates and gates writability, reads before/after with `getnamed`, calls `switchtolayout` before mutation, and mutates via `setnamed(object_name, property_name, value)`.
  - Diagnostics now include phase, adapter/project/session context, method name, object/property/value args, and the underlying exception string.

- `src/fdtd_lab_mcp/adapters/real_base.py::_add_object` and `_set_properties`
  - Was: raw `eval('<add command>; set("name", ...);')` and raw `eval('set(... fdtd_lab_new_value)')` after `putv` for property assignment.
  - Now: uses session methods `switchtolayout`, `addfdtd`/`addrect`/`adddipole`/`addpower`, and positional `set(property, value)` wrapper calls for selected new object setup.

- `src/fdtd_lab_mcp/adapters/base.py::LumericalAdapter`
  - Added `close_project(project_id)` to the adapter protocol while keeping legacy `close(session_id)`.

- `src/fdtd_lab_mcp/adapters/fake.py::FakeLumericalAdapter.close_project`
  - Added in-memory project/session deletion by `project_id`, returning `{project_id, session_id, closed, adapter}`.

- `src/fdtd_lab_mcp/adapters/real_base.py::ScriptSessionAdapter.close_project`
  - Added project-id lifecycle close: calls documented `session.close()`, deletes project record, returns `{project_id, session_id, closed, adapter}`.

- `src/fdtd_lab_mcp/tools.py` and `src/fdtd_lab_mcp/server.py`
  - Added and registered MCP tools `close_project(project_id)` and legacy `close(session_id)`.

## Remaining raw `eval` hotspots

These remain because they are not the reported named-object property mutation path and need real-project samples before replacing safely:

- `save_project_as`: still calls `_eval('save(...)')`; should become wrapper `session.save(path)` after confirming both `ansys.lumerical.core` and direct `lumapi` path behavior.
- `delete_object`: still calls `_eval('select(...); delete;')`; candidate wrapper sequence is `select(name)` then `delete()` or object handle deletion, but needs duplicate-name/group-path validation.
- `list_objects`: still uses `selectall`, `getnumber`, and indexed `get(...)` through `_eval`/`getv`; retained because object-tree enumeration differs across Lumerical versions.
- `list_properties`: still selects the object only to validate path and returns static common candidates; dynamic real property discovery remains unimplemented.
- `run`: still calls `_eval('run;')`; candidate wrapper is `session.run()`.
- `get_monitor_result`: still calls `_eval('fdtd_lab_result = getresult(...)')` plus `getv`; candidate wrapper is `session.getresult(monitor, result)` with result normalization.

## Manual real-Lumerical smoke checklist

Run only inside the company-local writable Lumerical environment:

1. `export FDTD_LAB_ADAPTER=ansys_core` and `export FDTD_LAB_ENABLE_REAL_LUMERICAL=1`.
2. Open a writable non-sensitive `.fsp`: `open_fsp(path, readonly=False)`.
3. Call `set_object_property(project_id, "FDTD", "x span", <new span>)`.
4. Confirm logs/errors show `switchtolayout`, `getnamed`, and `setnamed` phases if failure occurs; no `select(...); set(... fdtd_lab_new_value)` mutation should be used.
5. Call `run_simulation(project_id)`.
6. Call `close_project(project_id)`.
7. Verify the FDTD application exits from the system tray/task manager and the license is released.

## Internal helper lifecycle follow-up (2026-05-15)

High-level tools that internally open or create a project have been audited for project/session ownership:

| Tool | Lifecycle choice | Rationale |
| --- | --- | --- |
| `open_fsp(path, readonly=...)` | Leaves project open; caller must invoke `close_project(project_id)` | Low-level handle factory explicitly returns a project handle for further operations. |
| `new_project()` | Leaves project open; caller must invoke `close_project(project_id)` | Low-level authoring handle factory explicitly returns a project handle for further operations. |
| `inspect_fsp(path, readonly=...)` | Auto-closes internally opened project after object/description collection, including failure cleanup | One-shot inspection helper does not need to return a live handle. |
| `create_tiny_smoke_project(path, overwrite=...)` | Auto-closes internally created project after save/description collection, including failure cleanup | One-shot smoke authoring helper only returns saved file metadata and objects. |
| `run_tiny_smoke_project(path, timeout_sec=...)` | Auto-closes internally opened writable project after run/result collection, including failure cleanup | One-shot smoke execution helper only returns run/result payloads. |
| `run_parameter_sweep(...)` | Auto-closes internally opened working-copy project after artifacts are written, including failure cleanup | Sweep helper opens a copied `.fsp` for internal iteration and does not expose that `project_id`; leaving it open could keep FDTD in the system tray and consume a license. |

Cleanup implementation detail: one-shot helpers call `close_project(project_id)` on the internally opened/created project. If the main operation fails and close also fails, the close failure is attached as an exception note so the original failure remains primary. If the main operation succeeds but close fails, the helper raises a cleanup failure because the user-facing operation did not safely release the real Lumerical session/license.

Fake tests now assert that one-shot helpers leave no fake adapter projects after success/failure, while low-level `open_fsp()` and `new_project()` keep handles alive until explicit `close_project(project_id)`.
