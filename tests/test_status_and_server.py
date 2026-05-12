from fdtd_lab_mcp.server import create_server
from fdtd_lab_mcp import tools

def test_status_fake_ok():
    s=tools.lumerical_status()
    assert s['ok'] is True
    assert s['api'] == 'fake'

def test_status_all_non_invasive():
    s=tools.lumerical_status(adapter='all')
    assert set(s) == {'fake','ansys_core','lumapi'}
    assert s['fake']['ok'] is True

def test_server_constructs():
    assert create_server() is not None
