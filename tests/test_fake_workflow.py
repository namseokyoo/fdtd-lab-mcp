import json
from pathlib import Path
import pytest
from fdtd_lab_mcp import tools
from fdtd_lab_mcp.safety.run_manager import sha256_file

@pytest.fixture(autouse=True)
def reset():
    tools.reset_state()

def sample_fsp(tmp_path: Path) -> Path:
    p=tmp_path/'base.fsp'
    p.write_bytes(b'fake fsp bytes')
    return p

def test_missing_fsp_fails(tmp_path):
    with pytest.raises(Exception) as exc:
        tools.open_fsp(str(tmp_path/'missing.fsp'))
    assert 'does not exist' in str(exc.value)

def test_inspect_fsp_lists_oled_objects(tmp_path):
    out=tools.inspect_fsp(str(sample_fsp(tmp_path)))
    names={o['name'] for o in out['objects']}
    assert {'FDTD','source','ETL','T_monitor'}.issubset(names)
    assert out['description']['project_type_guess'].startswith('OLED')
    assert any(c['object']=='ETL' for c in out['description']['sweep_candidates'])

def test_property_read_write_records_before_after(tmp_path):
    opened=tools.open_fsp(str(sample_fsp(tmp_path)), readonly=False)
    before=tools.get_object_property(opened['project_id'], 'ETL', 'z span')
    change=tools.set_object_property(opened['project_id'], 'ETL', 'z span', 4e-8)
    after=tools.get_object_property(opened['project_id'], 'ETL', 'z span')
    assert before['value'] == 3e-8
    assert change == {'object_name':'ETL','property_name':'z span','before':3e-8,'after':4e-8}
    assert after['value'] == 4e-8

def test_create_run_dir_preserves_checksum(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base=sample_fsp(tmp_path)
    before=sha256_file(base)
    run=tools.create_run_dir(str(base), 'etl thickness sweep')
    assert Path(run['working_fsp']).exists()
    assert Path(run['provenance_path']).exists()
    assert sha256_file(base) == before == run['original_checksum']

def test_parameter_sweep_outputs_artifacts_and_preserves_base(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base=sample_fsp(tmp_path)
    before=sha256_file(base)
    out=tools.run_parameter_sweep(str(base), 'etl_sweep', 'ETL', 'z span', [2e-8,3e-8,4e-8], 'T_monitor', 'T')
    assert out['base_checksum_unchanged'] is True
    assert sha256_file(base) == before
    assert Path(out['results_csv']).exists()
    assert Path(out['summary_md']).exists()
    prov=json.loads(Path(out['provenance_json']).read_text())
    assert prov['run_status'] == 'completed'
    assert len(prov['changed_variables']) == 3
    assert out['rows'] == 12

def test_plan_and_validate(tmp_path):
    base=sample_fsp(tmp_path)
    plan=tools.propose_experiment_plan(str(base), 'etl', 'ETL', 'z span', [1e-8], 'T_monitor', 'T')
    assert plan['dry_run'] is True
    assert tools.validate_experiment_plan(plan)['ok'] is True


def test_low_level_open_fsp_leaves_handle_until_explicit_close(tmp_path):
    opened = tools.open_fsp(str(sample_fsp(tmp_path)))

    assert opened["project_id"] in tools._ADAPTER.projects

    tools.close_project(opened["project_id"])
    assert opened["project_id"] not in tools._ADAPTER.projects


def test_inspect_fsp_auto_closes_on_success(tmp_path):
    out = tools.inspect_fsp(str(sample_fsp(tmp_path)))

    assert out["project_id"] not in tools._ADAPTER.projects
    assert tools._ADAPTER.projects == {}


def test_inspect_fsp_auto_closes_on_failure(tmp_path, monkeypatch):
    def fail_describe(project_id: str):
        raise RuntimeError("forced inspect failure")

    monkeypatch.setattr(tools, "describe_project", fail_describe)

    with pytest.raises(RuntimeError, match="forced inspect failure"):
        tools.inspect_fsp(str(sample_fsp(tmp_path)))

    assert tools._ADAPTER.projects == {}


def test_parameter_sweep_auto_closes_on_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base = sample_fsp(tmp_path)

    out = tools.run_parameter_sweep(str(base), "etl_sweep_autoclose", "ETL", "z span", [2e-8], "T_monitor", "T")

    assert out["base_checksum_unchanged"] is True
    assert tools._ADAPTER.projects == {}


def test_parameter_sweep_auto_closes_on_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base = sample_fsp(tmp_path)

    with pytest.raises(Exception, match="object 'DOES_NOT_EXIST' not found"):
        tools.run_parameter_sweep(str(base), "etl_sweep_failure", "DOES_NOT_EXIST", "z span", [2e-8], "T_monitor", "T")

    assert tools._ADAPTER.projects == {}
