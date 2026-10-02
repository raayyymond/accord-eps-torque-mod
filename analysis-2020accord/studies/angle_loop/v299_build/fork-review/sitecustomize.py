import os, sys, types
ROOT = r"C:\Users\dudei\Desktop\Projects\openpilots\raayyymond-StarPilot\StarPilot"
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capnp_fix")
for p in (ROOT + r"\opendbc_repo", ROOT):
  if p not in sys.path:
    sys.path.insert(0, p)
m = types.ModuleType("openpilot"); m.__path__ = [ROOT]
sys.modules["openpilot"] = m
import capnp
capnp.remove_import_hook()
c = types.ModuleType("cereal"); c.__path__ = [os.path.join(ROOT, "cereal")]; c.__file__ = os.path.join(ROOT, "cereal", "__init__.py")
c.CEREAL_PATH = FIX.replace("\\", "/")
c.log = capnp.load(os.path.join(FIX, "log.capnp"))
c.car = capnp.load(os.path.join(FIX, "car.capnp"))
c.custom = capnp.load(os.path.join(FIX, "custom.capnp"))
sys.modules["cereal"] = c
for _n in ("fcntl", "termios", "resource"):
  if _n not in sys.modules:
    try:
      __import__(_n)
    except ImportError:
      _s = types.ModuleType(_n)
      _s.__getattr__ = lambda name: (lambda *a, **k: 0)
      sys.modules[_n] = _s
_hw = types.ModuleType("openpilot.system.hardware"); _hw.__path__ = [os.path.join(ROOT, "system", "hardware")]
_hw.PC = True; _hw.TICI = False; _hw.AGNOS = False
class _HW:
  def __getattr__(self, name):
    return lambda *a, **k: None
_hw.HARDWARE = _HW()
sys.modules["openpilot.system.hardware"] = _hw
