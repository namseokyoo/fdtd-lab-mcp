import fdtd_lab_mcp
from fdtd_lab_mcp.server import create_server
from fdtd_lab_mcp import tools


def test_status_fake_ok():
    s = tools.lumerical_status()
    assert s['ok'] is True
    assert s['api'] == 'fake'


def test_status_all_non_invasive():
    s = tools.lumerical_status(adapter='all')
    assert set(s) == {'fake', 'ansys_core', 'lumapi'}
    assert s['fake']['ok'] is True


def test_reset_state_can_select_adapter_and_reports_active():
    try:
        selected = tools.reset_state(adapter='fake')
        assert selected['adapter'] == 'fake'
        assert tools.active_adapter()['adapter'] == 'fake'
    finally:
        tools.reset_state(adapter='fake')


def test_reset_state_uses_env_default(monkeypatch):
    monkeypatch.setenv('FDTD_LAB_ADAPTER', 'fake')
    try:
        selected = tools.reset_state()
        assert selected['adapter'] == 'fake'
        active = tools.active_adapter()
        assert active['adapter'] == 'fake'
        assert active['env_default'] == 'fake'
    finally:
        tools.reset_state(adapter='fake')


def test_server_info_exposes_package_version():
    info = tools.server_info()
    assert info['server_name'] == 'fdtd-lab-mcp'
    assert info['version'] == fdtd_lab_mcp.__version__
    assert info['active_adapter'] == tools.active_adapter()['adapter']
    assert info['real_lumerical']['env'] == 'FDTD_LAB_ENABLE_REAL_LUMERICAL'
    assert set(info['adapter_status_keys']) == {'fake', 'ansys_core', 'lumapi'}


def test_server_constructs():
    assert create_server() is not None


def test_server_registers_close_project_tools():
    server = create_server()
    registered = set(server._tool_manager._tools)
    assert "close_project" in registered
    assert "close" in registered
    assert "export_monitor_plot" in registered
    assert "export_sweep_plot" in registered
    assert "export_field_image" in registered
