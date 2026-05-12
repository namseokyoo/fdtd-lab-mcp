from .fake import FakeLumericalAdapter
from .ansys_core import AnsysCoreAdapter
from .lumapi import LumapiAdapter

def make_adapter(name: str = "fake"):
    if name == "fake": return FakeLumericalAdapter()
    if name == "ansys_core": return AnsysCoreAdapter()
    if name == "lumapi": return LumapiAdapter()
    raise ValueError(f"unknown adapter: {name}")
