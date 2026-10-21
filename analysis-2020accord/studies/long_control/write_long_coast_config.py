# -*- coding: utf-8 -*-
"""Write the 2026-10-20 "long-coast" Galaxy toggle config (delta) and its revert, Galaxy's own codec.

Fork accord-PTM @ 311c4cc0 (the commit on the device).  Only the four Aggressive* MPC-weight keys change:
the live personality is 0 = aggressive (longitudinal_personality_profiles.py:active_personality_id) and the
jerk keys are NOT covered by the LongitudinalPersonalityProfiles JSON (it holds accel/braking/following only),
so these scalars are live whenever CustomPersonalities=1.  Every key is checked declared FLOAT in
common/params_keys.h at the commit, the fork codec is read with `git show` and asserted equal to the kit's,
and both files decode back from disk.  Files open with "x".  Nothing is deployed.
"""
import ast, base64, hashlib, importlib.util, json, os, re, subprocess, time
T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
FORK = r"C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot"
COMMIT = "311c4cc0"

spec = importlib.util.spec_from_file_location("mgtc", os.path.join(KIT, "tools", "make_galaxy_toggle_config.py"))
K = importlib.util.module_from_spec(spec); spec.loader.exec_module(K)
K.positive_control()

def git(*a):
  return subprocess.run(["git", "-C", FORK, *a], capture_output=True, text=True, encoding="utf-8", check=True).stdout

src = git("show", f"{COMMIT}:starpilot/system/the_galaxy/utilities.py")
keep = [n for n in ast.parse(src).body if (isinstance(n, ast.FunctionDef) and n.name in
        {"xor_encrypt_decrypt", "encode_parameters", "decode_parameters"}) or
        (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "XOR_KEY" for t in n.targets))]
F = {"base64": base64, "json": json}
exec(compile(ast.Module(body=keep, type_ignores=[]), "fork_utilities", "exec"), F)
assert F["XOR_KEY"] == K.XOR_KEY

decl = git("show", f"{COMMIT}:common/params_keys.h")
def declared(key):
  m = re.search(r'\{"%s", \{PERSISTENT, (\w+), "([^"]*)"' % re.escape(key), decl)
  return (m.group(1), m.group(2)) if m else None

# live device values read over ssh 2026-10-20 (before) -> proposed (after)
CHANGE = {
  "AggressiveJerkAcceleration":  (50.0, 100.0),
  "AggressiveJerkDeceleration":  (150.0, 100.0),
  "AggressiveJerkSpeedDecrease": (150.0, 100.0),
  "AggressiveJerkDanger":        (30.0, 100.0),
}
for k in CHANGE:
  d = declared(k); assert d is not None and d[0] == "FLOAT", (k, d)
  for v in CHANGE[k]: assert 25.0 <= v <= 200.0  # Galaxy/validate_personality_advanced_value bounds
after = {k: float(v[1]) for k, v in CHANGE.items()}
before = {k: float(v[0]) for k, v in CHANGE.items()}

def write(name, vals):
  wrapper = {"format": "starpilot-toggle-backup", "version": 1, "settingsCount": len(vals),
             "data": K.encode_parameters(vals)}
  assert F["encode_parameters"](vals) == wrapper["data"]
  pe, pd = os.path.join(HERE, name + ".json"), os.path.join(HERE, name + ".decoded.json")
  with open(pe, "x", encoding="utf-8") as fh: json.dump(wrapper, fh, indent=1)
  with open(pd, "x", encoding="utf-8") as fh: json.dump(vals, fh, indent=1)
  back = json.load(open(pe, encoding="utf-8"))
  assert K.decode_parameters(back["data"]) == vals == F["decode_parameters"](back["data"]) == json.load(open(pd, encoding="utf-8"))
  for p in (pe, pd): print("sha256", hashlib.sha256(open(p, "rb").read()).hexdigest(), os.path.basename(p))

write("toggle-config_long-coast_2026-10-20", after)
write("toggle-config_long-coast_2026-10-20_REVERT", before)
print("declared defaults:", {k: declared(k)[1] for k in CHANGE})
print("wall %.2f s" % (time.time() - T0))
