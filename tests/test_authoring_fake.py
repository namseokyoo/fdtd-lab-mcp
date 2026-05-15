from pathlib import Path

import pytest

from fdtd_lab_mcp import tools


@pytest.fixture(autouse=True)
def reset():
    tools.reset_state(adapter="fake")


def test_new_project_starts_empty():
    opened = tools.new_project()

    assert opened["adapter"] == "fake"
    assert opened["readonly"] is False
    assert opened["path"] == "<unsaved>"
    assert tools.list_objects(opened["project_id"])["objects"] == []


def test_add_authoring_primitives_to_fake_project():
    opened = tools.new_project()
    project_id = opened["project_id"]

    tools.add_fdtd_region(project_id, "FDTD", {"x span": 1e-6, "mesh accuracy": 1})
    tools.add_rectangle(project_id, "block", {"material": "Si", "z span": 1e-7})
    tools.add_dipole_source(project_id, "source", {"wavelength start": 4e-7, "wavelength stop": 7e-7})
    tools.add_power_monitor(project_id, "T_monitor", {"monitor type": "2D Z-normal"})

    objects = tools.list_objects(project_id)["objects"]
    names = {o["name"] for o in objects}
    types = {o["name"]: o["type"] for o in objects}
    assert names == {"FDTD", "block", "source", "T_monitor"}
    assert types == {
        "FDTD": "simulation_region",
        "block": "structure",
        "source": "source",
        "T_monitor": "monitor",
    }


def test_duplicate_object_name_rejected():
    opened = tools.new_project()
    project_id = opened["project_id"]

    tools.add_rectangle(project_id, "block", {})
    with pytest.raises(Exception) as exc:
        tools.add_rectangle(project_id, "block", {})

    assert "already exists" in str(exc.value)


def test_unsafe_object_name_rejected():
    opened = tools.new_project()

    with pytest.raises(Exception) as exc:
        tools.add_rectangle(opened["project_id"], 'bad";deleteall;', {})

    assert "unsafe object name" in str(exc.value)


def test_save_project_as_writes_fsp(tmp_path: Path):
    opened = tools.new_project()
    path = tmp_path / "smoke.fsp"

    out = tools.save_project_as(opened["project_id"], str(path))

    assert path.exists()
    assert out["path"] == str(path)
    assert out["adapter"] == "fake"


def test_save_project_as_rejects_overwrite_without_flag(tmp_path: Path):
    opened = tools.new_project()
    path = tmp_path / "smoke.fsp"
    path.write_bytes(b"existing")

    with pytest.raises(Exception) as exc:
        tools.save_project_as(opened["project_id"], str(path))

    assert "already exists" in str(exc.value)


def test_delete_object_removes_existing_object():
    opened = tools.new_project()
    project_id = opened["project_id"]
    tools.add_rectangle(project_id, "block", {})

    out = tools.delete_object(project_id, "block")

    assert out["deleted"] is True
    assert tools.list_objects(project_id)["objects"] == []


def test_create_tiny_smoke_project(tmp_path: Path):
    path = tmp_path / "tiny.fsp"

    out = tools.create_tiny_smoke_project(str(path))

    assert path.exists()
    assert out["path"] == str(path)
    names = {o["name"] for o in out["objects"]}
    assert {"FDTD", "block", "source", "T_monitor"}.issubset(names)
    assert out["description"]["project_type_guess"].startswith("OLED")
    assert any("not a production" in warning for warning in out["warnings"])


def test_run_tiny_smoke_project_uses_existing_project(tmp_path: Path):
    path = tmp_path / "tiny.fsp"
    tools.create_tiny_smoke_project(str(path))

    out = tools.run_tiny_smoke_project(str(path), timeout_sec=120)

    assert out["path"] == str(path)
    assert out["run"]["status"] == "completed"
    assert out["result"]["monitor_name"] == "T_monitor"


def test_readonly_project_rejects_mutating_operations(tmp_path: Path):
    path = tmp_path / "base.fsp"
    path.write_bytes(b"fake")
    opened = tools.open_fsp(str(path), readonly=True)
    project_id = opened["project_id"]

    mutators = [
        lambda: tools.save_project_as(project_id, str(tmp_path / "copy.fsp")),
        lambda: tools.add_rectangle(project_id, "new_block", {}),
        lambda: tools.delete_object(project_id, "ETL"),
        lambda: tools.set_object_property(project_id, "ETL", "z span", 4e-8),
        lambda: tools.run_simulation(project_id),
    ]

    for mutate in mutators:
        with pytest.raises(Exception, match="requires a writable project handle"):
            mutate()


def test_unsafe_property_and_result_names_rejected():
    opened = tools.new_project()
    project_id = opened["project_id"]
    tools.add_rectangle(project_id, "block", {"z span": 1e-7})
    tools.add_power_monitor(project_id, "T_monitor", {})

    with pytest.raises(Exception, match="unsafe property name"):
        tools.set_object_property(project_id, "block", 'z span";deleteall;', 2e-7)
    with pytest.raises(Exception, match="unsafe result name"):
        tools.get_monitor_result(project_id, "T_monitor", 'T";deleteall;')


def test_list_properties_includes_capability_metadata():
    opened = tools.new_project()
    project_id = opened["project_id"]
    tools.add_rectangle(project_id, "block", {"z span": 1e-7})

    payload = tools.list_properties(project_id, "block")

    assert payload["properties"] == ["z span"]
    assert payload["verified"] is True
    assert payload["capability_source"] == "adapter_dynamic_or_fixture"
    assert payload["warnings"] == []


def test_close_project_closes_fake_project_by_project_id():
    opened = tools.new_project()
    project_id = opened["project_id"]

    out = tools.close_project(project_id)

    assert out["closed"] is True
    assert out["project_id"] == project_id
    assert out["session_id"] == opened["session_id"]
    assert out["adapter"] == "fake"
    with pytest.raises(Exception, match="unknown project_id"):
        tools.list_objects(project_id)


def test_legacy_close_still_closes_by_session_id():
    opened = tools.new_project()

    out = tools.close(opened["session_id"])

    assert out["closed"] is True
    assert out["session_id"] == opened["session_id"]
    assert opened["project_id"] in out["project_ids"]
    with pytest.raises(Exception, match="unknown project_id"):
        tools.list_objects(opened["project_id"])


def test_low_level_new_project_leaves_handle_until_explicit_close():
    opened = tools.new_project()

    assert opened["project_id"] in tools._ADAPTER.projects

    tools.close_project(opened["project_id"])
    assert opened["project_id"] not in tools._ADAPTER.projects


def test_create_tiny_smoke_project_auto_closes_on_success(tmp_path: Path):
    path = tmp_path / "tiny-autoclose.fsp"

    out = tools.create_tiny_smoke_project(str(path))

    assert path.exists()
    assert out["project_id"] not in tools._ADAPTER.projects
    assert tools._ADAPTER.projects == {}


def test_create_tiny_smoke_project_auto_closes_on_failure(tmp_path: Path):
    path = tmp_path / "tiny-existing.fsp"
    path.write_bytes(b"existing")

    with pytest.raises(Exception, match="already exists"):
        tools.create_tiny_smoke_project(str(path))

    assert tools._ADAPTER.projects == {}


def test_run_tiny_smoke_project_auto_closes_on_success(tmp_path: Path):
    path = tmp_path / "tiny-run-autoclose.fsp"
    tools.create_tiny_smoke_project(str(path))

    out = tools.run_tiny_smoke_project(str(path), timeout_sec=120)

    assert out["project_id"] not in tools._ADAPTER.projects
    assert tools._ADAPTER.projects == {}


def test_run_tiny_smoke_project_auto_closes_on_failure(tmp_path: Path, monkeypatch):
    path = tmp_path / "tiny-run-failure.fsp"
    tools.create_tiny_smoke_project(str(path))

    def fail_result(project_id: str, monitor_name: str, result_name: str):
        raise RuntimeError("forced monitor failure")

    monkeypatch.setattr(tools, "get_monitor_result", fail_result)

    with pytest.raises(RuntimeError, match="forced monitor failure"):
        tools.run_tiny_smoke_project(str(path), timeout_sec=120)

    assert tools._ADAPTER.projects == {}
