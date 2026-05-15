from pathlib import Path

import pytest

from fdtd_lab_mcp import tools
from fdtd_lab_mcp.reporting.plots import normalize_monitor_result


@pytest.fixture(autouse=True)
def reset():
    tools.reset_state(adapter="fake")


def sample_fsp(tmp_path: Path) -> Path:
    path = tmp_path / "base.fsp"
    path.write_bytes(b"fake fsp bytes")
    return path


def assert_png(path: Path) -> None:
    assert path.exists()
    assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_export_monitor_plot_from_fake_result(tmp_path: Path):
    opened = tools.open_fsp(str(sample_fsp(tmp_path)))
    output = tmp_path / "monitor.png"

    out = tools.export_monitor_plot(opened["project_id"], "T_monitor", "T", str(output))

    assert out["path"] == str(output)
    assert out["format"] == "png"
    assert out["points"] == 4
    assert out["monitor_name"] == "T_monitor"
    assert_png(output)


def test_export_sweep_plot_from_rows_and_parameter_sweep(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base = sample_fsp(tmp_path)

    sweep = tools.run_parameter_sweep(str(base), "etl_plot_sweep", "ETL", "z span", [2e-8, 3e-8], "T_monitor", "T")

    assert Path(sweep["results_csv"]).exists()
    assert_png(Path(sweep["sweep_plot_png"]))

    overlay = tmp_path / "overlay.png"
    out = tools.export_sweep_plot(str(overlay), csv_path=sweep["results_csv"])

    assert out["series"] == 2
    assert out["points"] == 8
    assert_png(overlay)


def test_export_field_image_fake_2d_component_subset(tmp_path: Path):
    opened = tools.open_fsp(str(sample_fsp(tmp_path)))
    output = tmp_path / "field.png"

    out = tools.export_field_image(opened["project_id"], "T_monitor", "E", str(output), component="Ex", plane="xy")

    assert out["component"] == "Ex"
    assert out["plane"] == "xy"
    assert out["width"] == 4
    assert out["height"] == 3
    assert_png(output)


def test_export_rejects_non_png_and_overwrite_without_flag(tmp_path: Path):
    opened = tools.open_fsp(str(sample_fsp(tmp_path)))

    with pytest.raises(Exception, match="expected .png export path"):
        tools.export_monitor_plot(opened["project_id"], "T_monitor", "T", str(tmp_path / "bad.csv"))

    output = tmp_path / "monitor.png"
    output.write_bytes(b"existing")
    with pytest.raises(Exception, match="already exists"):
        tools.export_monitor_plot(opened["project_id"], "T_monitor", "T", str(output))

    out = tools.export_monitor_plot(opened["project_id"], "T_monitor", "T", str(output), overwrite=True)
    assert out["path"] == str(output)
    assert_png(output)


def test_normalized_monitor_result_schema_rejections():
    with pytest.raises(Exception, match="raw/un-normalized"):
        normalize_monitor_result({"metadata": {"normalized": False}, "warnings": ["raw fixture"]})

    with pytest.raises(Exception, match="axes.wavelength_m"):
        normalize_monitor_result({"metadata": {"normalized": True}, "axes": {}, "values": [1.0]})

    with pytest.raises(Exception, match="same length"):
        normalize_monitor_result({"metadata": {"normalized": True}, "axes": {"wavelength_m": {"values": [1, 2]}}, "values": [3]})


def test_field_image_rejects_unsupported_plane(tmp_path: Path):
    opened = tools.open_fsp(str(sample_fsp(tmp_path)))

    with pytest.raises(Exception, match="plane must be"):
        tools.export_field_image(opened["project_id"], "T_monitor", "E", str(tmp_path / "field.png"), component="Ex", plane="rt")
