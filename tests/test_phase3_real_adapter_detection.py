from pathlib import Path

import pytest

from fdtd_lab_mcp.adapters.ansys_core import AnsysCoreAdapter
from fdtd_lab_mcp.adapters.lumapi import LumapiAdapter
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
