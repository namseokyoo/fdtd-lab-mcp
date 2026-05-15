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


def test_eval_error_includes_phase_context_and_sanitized_snippet():
    class FailingSession:
        def eval(self, script):
            raise RuntimeError("boom")

    adapter = ScriptSessionAdapter()
    adapter.projects["project-1"] = {"session_id": "session-1", "session": FailingSession(), "path": "sample.fsp", "readonly": True}

    with pytest.raises(AdapterUnavailable) as exc:
        adapter._eval("project-1", "selectall; password = topsecret; " + "x" * 400, phase="unit-test-phase")

    message = str(exc.value)
    assert "phase=unit-test-phase" in message
    assert "adapter=script_session" in message
    assert "project_id=project-1" in message
    assert "session_id=session-1" in message
    assert "topsecret" not in message
    assert len(message) < 700


def test_real_set_property_uses_documented_named_methods_not_raw_eval():
    class RecordingSession:
        def __init__(self):
            self.calls = []
            self.scripts = []
            self.values = {("valid object", "x span"): 1}

        def eval(self, script):
            self.scripts.append(script)

        def switchtolayout(self):
            self.calls.append(("switchtolayout",))

        def getnamed(self, object_name, property_name):
            self.calls.append(("getnamed", object_name, property_name))
            return self.values[(object_name, property_name)]

        def setnamed(self, object_name, property_name, value):
            self.calls.append(("setnamed", object_name, property_name, value))
            self.values[(object_name, property_name)] = value

    adapter = ScriptSessionAdapter()
    session = RecordingSession()
    adapter.projects["project-1"] = {"session_id": "session-1", "session": session, "path": "sample.fsp", "readonly": False}

    result = adapter.set_property("project-1", "valid object", "x span", 2)

    assert result == {"object_name": "valid object", "property_name": "x span", "before": 1, "after": 2}
    assert session.calls == [
        ("getnamed", "valid object", "x span"),
        ("switchtolayout",),
        ("setnamed", "valid object", "x span", 2),
        ("getnamed", "valid object", "x span"),
    ]
    assert session.scripts == []


def test_real_get_property_uses_getnamed_and_validates_paths():
    class RecordingSession:
        def __init__(self):
            self.calls = []

        def getnamed(self, object_name, property_name):
            self.calls.append(("getnamed", object_name, property_name))
            return 1

    adapter = ScriptSessionAdapter()
    session = RecordingSession()
    adapter.projects["project-1"] = {"session_id": "session-1", "session": session, "path": "sample.fsp", "readonly": False}

    adapter.get_property("project-1", "valid object", "x span")

    assert session.calls == [("getnamed", "valid object", "x span")]
    with pytest.raises(Exception, match="unsafe object name"):
        adapter.get_property("project-1", 'bad";delete;', "x span")
    with pytest.raises(Exception, match="unsafe property name"):
        adapter.get_property("project-1", "valid object", 'x";delete;')


def test_real_set_property_error_includes_method_phase_object_property():
    class FailingSession:
        def getnamed(self, object_name, property_name):
            return 1

        def switchtolayout(self):
            pass

        def setnamed(self, object_name, property_name, value):
            raise RuntimeError("underlying LumApiError text")

    adapter = ScriptSessionAdapter()
    adapter.projects["project-1"] = {"session_id": "session-1", "session": FailingSession(), "path": "sample.fsp", "readonly": False}

    with pytest.raises(AdapterUnavailable) as exc:
        adapter.set_property("project-1", "FDTD", "x span", 2)

    message = str(exc.value)
    assert "phase=set_property:setnamed:FDTD:x span" in message
    assert "method=setnamed" in message
    assert "FDTD" in message
    assert "x span" in message
    assert "underlying LumApiError text" in message


def test_real_list_properties_returns_unverified_static_candidates():
    class RecordingSession:
        def __init__(self):
            self.scripts = []

        def eval(self, script):
            self.scripts.append(script)

    adapter = ScriptSessionAdapter()
    session = RecordingSession()
    adapter.projects["project-1"] = {"session_id": "session-1", "session": session, "path": "sample.fsp", "readonly": True}

    payload = adapter.list_properties("project-1", "ETL")

    assert payload["verified"] is False
    assert payload["capability_source"] == "static_common_candidates"
    assert "z span" in payload["properties"]
    assert payload["warnings"]
    assert session.scripts == ['select("ETL");']


def test_raw_monitor_result_is_marked_and_sweep_guard_rejects():
    from fdtd_lab_mcp import tools

    raw = {
        "metadata": {"normalized": False},
        "axes": {},
        "values": [],
        "warnings": ["raw sample"],
    }

    with pytest.raises(RuntimeError, match="raw/un-normalized"):
        tools._require_normalized_monitor_result(raw)


def test_describe_project_labels_unverified_static_candidates(monkeypatch):
    from fdtd_lab_mcp import tools

    class StaticCandidateAdapter:
        name = "static"

        def list_objects(self, project_id):
            return [{"name": "ETL", "type": "structure"}]

        def list_properties(self, project_id, object_name):
            return {
                "properties": ["z span", "material"],
                "verified": False,
                "capability_source": "static_common_candidates",
                "warnings": ["static only"],
            }

    monkeypatch.setattr(tools, "_ADAPTER", StaticCandidateAdapter())

    description = tools.describe_project("project-1")

    assert description["sweep_candidates"] == [
        {"object": "ETL", "property": "z span", "reason": "unverified static candidate", "verified": False, "capability_source": "static_common_candidates"}
    ]
    assert description["warnings"]
