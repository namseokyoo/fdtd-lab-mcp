from pathlib import Path

import pytest

from fdtd_lab_mcp.adapters.ansys_core import AnsysCoreAdapter
from fdtd_lab_mcp.adapters.lumapi import LumapiAdapter
from fdtd_lab_mcp.adapters.real_base import ScriptSessionAdapter, _json_safe
from fdtd_lab_mcp.errors import AdapterUnavailable


def test_ansys_core_detection_is_non_invasive():
    s = AnsysCoreAdapter().status()
    assert s['api'] == 'ansys-lumerical-core'
    assert 'products' in s


def test_lumapi_detection_is_non_invasive():
    s = LumapiAdapter().status()
    assert s['api'] == 'lumapi'
    assert 'products' in s


def test_real_open_requires_explicit_enable_even_with_existing_fsp(tmp_path, monkeypatch):
    monkeypatch.delenv('FDTD_LAB_ENABLE_REAL_LUMERICAL', raising=False)
    fsp = tmp_path / 'sample.fsp'
    fsp.write_bytes(b'fake')
    with pytest.raises(AdapterUnavailable, match='Real Lumerical operations are disabled'):
        AnsysCoreAdapter().open_project(str(fsp))


def test_json_safe_converts_numpy_like_values():
    class ArrayLike:
        def tolist(self):
            return [1, 2, {"x": ScalarLike()}]

    class ScalarLike:
        def item(self):
            return 3.5

    assert _json_safe({"arr": ArrayLike(), "scalar": ScalarLike()}) == {"arr": [1, 2, {"x": 3.5}], "scalar": 3.5}


def test_list_objects_uses_python_loop_not_lumerical_for_syntax():
    class FakeSession:
        def __init__(self):
            self.vars = {}
            self.scripts = []

        def eval(self, script):
            self.scripts.append(script)
            if "getnumber" in script:
                self.vars["fdtd_lab_n"] = 2
            if 'get("name", 1)' in script:
                self.vars["fdtd_lab_object_name"] = "source"
                self.vars["fdtd_lab_object_type"] = "object"
            if 'get("name", 2)' in script:
                self.vars["fdtd_lab_object_name"] = "monitor"
                self.vars["fdtd_lab_object_type"] = "analysis"

        def getv(self, name):
            return self.vars[name]

    adapter = ScriptSessionAdapter()
    adapter.projects["project-1"] = {"session_id": "session-1", "session": FakeSession(), "path": "sample.fsp", "readonly": True}

    assert adapter.list_objects("project-1") == [
        {"name": "source", "type": "object"},
        {"name": "monitor", "type": "analysis"},
    ]
    assert all("for (" not in script for script in adapter.projects["project-1"]["session"].scripts)


@pytest.mark.lumerical
def test_company_local_ansys_core_open_list_smoke(monkeypatch):
    import os

    sample = os.environ.get('FDTD_LAB_SAMPLE_FSP')
    if not sample:
        pytest.skip('FDTD_LAB_SAMPLE_FSP not set')
    monkeypatch.setenv('FDTD_LAB_ENABLE_REAL_LUMERICAL', '1')
    adapter = AnsysCoreAdapter()
    handle = adapter.open_project(sample, readonly=True)
    try:
        objects = adapter.list_objects(handle.project_id)
        assert isinstance(objects, list)
    finally:
        adapter.close(handle.session_id)
