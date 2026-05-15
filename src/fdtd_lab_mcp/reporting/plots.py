from __future__ import annotations

import csv
import math
import struct
import zlib
from pathlib import Path
from typing import Any, Iterable

from fdtd_lab_mcp.errors import ValidationError

Number = int | float


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_DEFAULT_COLORS = [
    (31, 119, 180),
    (255, 127, 14),
    (44, 160, 44),
    (214, 39, 40),
    (148, 103, 189),
    (140, 86, 75),
]


def _validate_png_path(path: str, *, overwrite: bool) -> Path:
    p = Path(path).expanduser()
    if p.suffix.lower() != ".png":
        raise ValidationError(f"expected .png export path, got: {path}")
    if p.exists() and not overwrite:
        raise ValidationError(f"export path already exists: {path}")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _finite_float(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValidationError(f"{label} must be numeric, got bool")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} must be numeric, got {value!r}") from exc
    if not math.isfinite(number):
        raise ValidationError(f"{label} must be finite, got {value!r}")
    return number


def _as_1d_numbers(values: Any, label: str) -> list[float]:
    if not isinstance(values, (list, tuple)):
        raise ValidationError(f"{label} must be a list of numeric values")
    return [_finite_float(value, f"{label}[{index}]") for index, value in enumerate(values)]


def _as_2d_numbers(values: Any, label: str) -> list[list[float]]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ValidationError(f"{label} must be a non-empty 2D numeric list")
    matrix = [_as_1d_numbers(row, f"{label}[{row_index}]") for row_index, row in enumerate(values)]
    width = len(matrix[0])
    if width == 0:
        raise ValidationError(f"{label} rows must not be empty")
    if any(len(row) != width for row in matrix):
        raise ValidationError(f"{label} rows must all have the same length")
    return matrix


def normalize_monitor_result(result: dict[str, Any]) -> dict[str, Any]:
    """Normalize the stable 1D monitor-result shape used by plot/export tools.

    Supported stable schema:
    - result["axes"]["wavelength_m"]["values"] is a 1D numeric list
    - result["values"] is a same-length 1D numeric list
    - metadata.normalized is not False

    Raw real-adapter payloads are rejected until a company-local sample establishes
    a safe schema mapping.
    """
    if not isinstance(result, dict):
        raise ValidationError("monitor result must be a dictionary")
    if result.get("metadata", {}).get("normalized") is False:
        warnings = result.get("warnings") or []
        detail = f" Warnings: {'; '.join(map(str, warnings))}" if warnings else ""
        raise ValidationError("monitor result is raw/un-normalized and cannot be plotted safely." + detail)

    axes = result.get("axes")
    if not isinstance(axes, dict) or "wavelength_m" not in axes:
        raise ValidationError("monitor result must include axes.wavelength_m.values")
    wavelength_axis = axes["wavelength_m"]
    if not isinstance(wavelength_axis, dict):
        raise ValidationError("axes.wavelength_m must be an object with values/unit")
    x_values = _as_1d_numbers(wavelength_axis.get("values"), "axes.wavelength_m.values")
    y_values = _as_1d_numbers(result.get("values"), "values")
    if len(x_values) != len(y_values):
        raise ValidationError("wavelength and result value arrays must have the same length")
    if not x_values:
        raise ValidationError("monitor result arrays must not be empty")
    return {
        "x": x_values,
        "y": y_values,
        "x_label": f"wavelength ({wavelength_axis.get('unit', 'm')})",
        "y_label": str(result.get("result_name") or "result"),
        "monitor_name": result.get("monitor_name"),
        "result_name": result.get("result_name"),
        "points": len(x_values),
    }


def normalize_sweep_rows(rows: list[dict[str, Any]], *, x_key: str, y_key: str, series_key: str) -> list[dict[str, Any]]:
    if not rows:
        raise ValidationError("sweep rows must not be empty")
    grouped: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValidationError(f"rows[{index}] must be a dictionary")
        label = str(row.get(series_key))
        if label in {"", "None"}:
            raise ValidationError(f"rows[{index}] is missing series key {series_key!r}")
        point = (_finite_float(row.get(x_key), f"rows[{index}].{x_key}"), _finite_float(row.get(y_key), f"rows[{index}].{y_key}"))
        grouped.setdefault(label, {"label": label, "points": []})["points"].append(point)
    series = []
    for label, payload in grouped.items():
        points = sorted(payload["points"], key=lambda item: item[0])
        series.append({"label": label, "x": [p[0] for p in points], "y": [p[1] for p in points]})
    return series


def read_sweep_csv(path: str) -> list[dict[str, Any]]:
    p = Path(path).expanduser()
    if not p.exists():
        raise ValidationError(f"sweep CSV does not exist: {path}")
    with p.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _try_matplotlib_xy(series: list[dict[str, Any]], path: Path, *, title: str, x_label: str, y_label: str) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False

    fig, ax = plt.subplots(figsize=(7.0, 4.5), dpi=140)
    for item in series:
        ax.plot(item["x"], item["y"], marker="o", linewidth=1.8, markersize=3.5, label=item.get("label"))
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.3)
    if len(series) > 1:
        ax.legend(title="series", fontsize="small")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return True


def export_xy_plot(series: list[dict[str, Any]], path: str, *, title: str, x_label: str, y_label: str, overwrite: bool = False) -> dict[str, Any]:
    p = _validate_png_path(path, overwrite=overwrite)
    if not series:
        raise ValidationError("at least one plot series is required")
    for index, item in enumerate(series):
        x_values = _as_1d_numbers(item.get("x"), f"series[{index}].x")
        y_values = _as_1d_numbers(item.get("y"), f"series[{index}].y")
        if len(x_values) != len(y_values):
            raise ValidationError(f"series[{index}] x/y lengths differ")
        if not x_values:
            raise ValidationError(f"series[{index}] must not be empty")
        item["x"] = x_values
        item["y"] = y_values

    backend = "matplotlib" if _try_matplotlib_xy(series, p, title=title, x_label=x_label, y_label=y_label) else "builtin_png"
    if backend == "builtin_png":
        _draw_builtin_xy(series, p)
    return {"path": str(p), "format": "png", "backend": backend, "series": len(series), "points": sum(len(item["x"]) for item in series)}


def _write_png(path: Path, width: int, height: int, pixels: list[bytearray]) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(row) for row in pixels)
    payload = _PNG_SIGNATURE
    payload += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += chunk(b"IDAT", zlib.compress(raw, level=9))
    payload += chunk(b"IEND", b"")
    path.write_bytes(payload)


def _set_pixel(pixels: list[bytearray], x: int, y: int, color: tuple[int, int, int]) -> None:
    if y < 0 or y >= len(pixels) or x < 0 or x >= len(pixels[0]) // 3:
        return
    offset = x * 3
    pixels[y][offset : offset + 3] = bytes(color)


def _draw_line(pixels: list[bytearray], x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        for ox in (0, 1):
            for oy in (0, 1):
                _set_pixel(pixels, x0 + ox, y0 + oy, color)
        if x0 == x1 and y0 == y1:
            break
        twice = 2 * err
        if twice >= dy:
            err += dy
            x0 += sx
        if twice <= dx:
            err += dx
            y0 += sy


def _bounds(values: Iterable[float]) -> tuple[float, float]:
    vals = list(values)
    lower = min(vals)
    upper = max(vals)
    if lower == upper:
        pad = abs(lower) * 0.05 or 1.0
        return lower - pad, upper + pad
    pad = (upper - lower) * 0.05
    return lower - pad, upper + pad


def _draw_builtin_xy(series: list[dict[str, Any]], path: Path) -> None:
    width, height = 980, 620
    left, right, top, bottom = 80, 40, 40, 70
    pixels = [bytearray([255, 255, 255] * width) for _ in range(height)]
    plot_w = width - left - right
    plot_h = height - top - bottom
    all_x = [x for item in series for x in item["x"]]
    all_y = [y for item in series for y in item["y"]]
    min_x, max_x = _bounds(all_x)
    min_y, max_y = _bounds(all_y)

    def sx(value: float) -> int:
        return left + round((value - min_x) / (max_x - min_x) * plot_w)

    def sy(value: float) -> int:
        return top + plot_h - round((value - min_y) / (max_y - min_y) * plot_h)

    axis = (35, 35, 35)
    grid = (225, 225, 225)
    for i in range(6):
        x = left + round(i * plot_w / 5)
        y = top + round(i * plot_h / 5)
        _draw_line(pixels, x, top, x, top + plot_h, grid)
        _draw_line(pixels, left, y, left + plot_w, y, grid)
    _draw_line(pixels, left, top, left, top + plot_h, axis)
    _draw_line(pixels, left, top + plot_h, left + plot_w, top + plot_h, axis)

    for index, item in enumerate(series):
        color = _DEFAULT_COLORS[index % len(_DEFAULT_COLORS)]
        coords = [(sx(x), sy(y)) for x, y in zip(item["x"], item["y"])]
        for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
            _draw_line(pixels, x0, y0, x1, y1, color)
        for x, y in coords:
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    if dx * dx + dy * dy <= 9:
                        _set_pixel(pixels, x + dx, y + dy, color)
    _write_png(path, width, height, pixels)


def _try_matplotlib_heatmap(matrix: list[list[float]], path: Path, *, title: str, x_label: str, y_label: str) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False

    fig, ax = plt.subplots(figsize=(5.5, 4.8), dpi=150)
    image = ax.imshow(matrix, origin="lower", aspect="auto", cmap="viridis")
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    fig.colorbar(image, ax=ax, label="value")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return True


def export_heatmap(matrix: list[list[float]], path: str, *, title: str, x_label: str = "x", y_label: str = "y", overwrite: bool = False) -> dict[str, Any]:
    p = _validate_png_path(path, overwrite=overwrite)
    normalized = _as_2d_numbers(matrix, "matrix")
    backend = "matplotlib" if _try_matplotlib_heatmap(normalized, p, title=title, x_label=x_label, y_label=y_label) else "builtin_png"
    if backend == "builtin_png":
        _draw_builtin_heatmap(normalized, p)
    return {"path": str(p), "format": "png", "backend": backend, "width": len(normalized[0]), "height": len(normalized)}


def _draw_builtin_heatmap(matrix: list[list[float]], path: Path) -> None:
    rows = len(matrix)
    cols = len(matrix[0])
    scale = max(1, min(32, 768 // max(rows, cols)))
    width = cols * scale
    height = rows * scale
    values = [value for row in matrix for value in row]
    low, high = min(values), max(values)
    span = high - low or 1.0
    pixels = [bytearray([255, 255, 255] * width) for _ in range(height)]
    for row_index, row in enumerate(matrix):
        for col_index, value in enumerate(row):
            ratio = (value - low) / span
            color = _viridis_like(ratio)
            y0 = height - (row_index + 1) * scale
            x0 = col_index * scale
            for y in range(y0, y0 + scale):
                for x in range(x0, x0 + scale):
                    _set_pixel(pixels, x, y, color)
    _write_png(path, width, height, pixels)


def _viridis_like(ratio: float) -> tuple[int, int, int]:
    ratio = max(0.0, min(1.0, ratio))
    stops = [(68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)]
    pos = ratio * (len(stops) - 1)
    idx = min(int(pos), len(stops) - 2)
    frac = pos - idx
    a = stops[idx]
    b = stops[idx + 1]
    return tuple(round(a[channel] + (b[channel] - a[channel]) * frac) for channel in range(3))


def normalize_field_matrix(result: dict[str, Any], *, component: str | None = None, plane: str | None = None, slice_index: int | None = None) -> dict[str, Any]:
    """Normalize the conservative 2D field-image subset.

    Supported stable schema is either `values` as a 2D numeric list or `values` as
    a component dictionary containing a 2D numeric list. 3D stacks are accepted
    only when `slice_index` selects one 2D slice. `plane` is metadata-only for
    now and must be one of xy/xz/yz when supplied.
    """
    if result.get("metadata", {}).get("normalized") is False:
        raise ValidationError("field image export requires normalized result data")
    if plane is not None and plane not in {"xy", "xz", "yz"}:
        raise ValidationError("plane must be one of: xy, xz, yz")
    values = result.get("values")
    selected_component = component
    if isinstance(values, dict):
        selected_component = component or next(iter(values), None)
        if selected_component not in values:
            raise ValidationError(f"component {selected_component!r} not found in field values")
        values = values[selected_component]
    if isinstance(values, (list, tuple)) and values and isinstance(values[0], (list, tuple)) and values[0] and isinstance(values[0][0], (list, tuple)):
        if slice_index is None:
            raise ValidationError("3D field data requires slice_index for conservative image export")
        try:
            values = values[slice_index]
        except IndexError as exc:
            raise ValidationError(f"slice_index out of range: {slice_index}") from exc
    matrix = _as_2d_numbers(values, "field values")
    return {
        "matrix": matrix,
        "component": selected_component,
        "plane": plane or "native-2d",
        "width": len(matrix[0]),
        "height": len(matrix),
    }
