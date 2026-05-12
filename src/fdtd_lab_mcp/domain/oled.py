from __future__ import annotations

def classify_role(name: str, obj_type: str) -> str:
    n=name.lower()
    if 'monitor' in n or obj_type == 'monitor': return 'monitor'
    if 'source' in n or obj_type == 'source': return 'source'
    if n in {'htl','eml','etl'}: return f'oled_layer:{n.upper()}'
    if obj_type == 'simulation_region': return 'simulation_region'
    return 'unknown'

def sweep_layer_thickness(layer_name: str, thickness_nm_list: list[float]) -> dict:
    return {"object_name": layer_name, "property_name": "z span", "values": [v*1e-9 for v in thickness_nm_list], "unit": "m"}

def find_peak_wavelength(wavelengths: list[float], values: list[float]) -> dict:
    if not wavelengths or not values: return {"wavelength_m": None, "value": None}
    i=max(range(min(len(wavelengths), len(values))), key=lambda idx: values[idx])
    return {"wavelength_m": wavelengths[i], "value": values[i]}
