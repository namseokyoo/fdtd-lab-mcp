from fdtd_lab_mcp.adapters.ansys_core import AnsysCoreAdapter
from fdtd_lab_mcp.adapters.lumapi import LumapiAdapter

def test_ansys_core_detection_is_non_invasive():
    s=AnsysCoreAdapter().status()
    assert s['api'] == 'ansys-lumerical-core'
    assert 'products' in s

def test_lumapi_detection_is_non_invasive():
    s=LumapiAdapter().status()
    assert s['api'] == 'lumapi'
    assert 'products' in s
