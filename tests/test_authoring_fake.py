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
