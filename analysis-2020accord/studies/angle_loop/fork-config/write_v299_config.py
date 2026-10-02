# -*- coding: utf-8 -*-
"""Write the V299 Galaxy toggle configs (delta files, Galaxy's own codec), from the V298 drive-1 config on disk.

  toggle-config_V299-A_relays-bar.json  = V298 drive-1 (29 keys: V295 r2's 26 + AccordEpsAngleLoop true,
                                           UseAutoSteerDelay true, SteerRatio 16.84)
                                           + AccordAngleBarFromEps true + AccordAngleMaxRate 120.0 + AccordAngleClipScale 1.0
                                           -> DRIVE 2 (V299's first drive).  MaxRate/ClipScale = their defaults = V298; the
                                           only live change vs V298 in the toggles is the torque bar from the EPS.
  toggle-config_V299-B_cap250.json      = config A with AccordAngleMaxRate 250.0 ONLY.  OPTIONAL / LATER DOSE: never on
                                           V299's first drive; one dose per drive (rev 2 brief, section 7 X3).
  toggle-config_V299_REVERT_to_V298.json = the V298 drive-1 values + the three new keys at their V298 defaults
                                           (AccordAngleBarFromEps false, AccordAngleMaxRate 120.0, AccordAngleClipScale 1.0).
                                           A REVERT ALSO NEEDS the re-headered V298 rwd AND fork Dom 2712e1336 (the override
                                           removal is code, not a toggle).
(+ a .decoded.json beside each; B's decoded copy carries a "_comment" label, which is NOT in the encoded file.)

Checks: the V298 base file is re-hashed (3e6c7b64...) and decoded by the kit codec AND the fork's own utilities.py codec
(git show, never the working tree) and must equal its .decoded.json; every key must be declared in the fork's
params_keys.h AT THE V299 COMMIT (git show); the fork codec must be unchanged from 20d24ab79 to that commit; every
written file is decoded back FROM DISK by both codecs.  Files open with "x": never overwrite.  Python = the kit's
bin_decompile env, invoked as `python`.  Nothing is deployed; restoring a config in Galaxy is the operator's action.
"""
import ast, base64, hashlib, importlib.util, json, os, re, subprocess, time

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
FORK = r"C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot"
V299_COMMIT = "c6452361e43812c7a7931c76dd4e036bbe5a1835"  # Dom, local: the V299 angle interface (no override, bar, family, params)
BASE = "toggle-config_V298_angle_loop"
BASE_SHA = "3e6c7b64ea9c8727fd7597720fcf015e3a3c7803fbc5711a1e84c96feb71078d"
OUT_A = "toggle-config_V299-A_relays-bar"
OUT_B = "toggle-config_V299-B_cap250"
OUT_R = "toggle-config_V299_REVERT_to_V298"
NEW_DEFAULTS = {"AccordAngleBarFromEps": False, "AccordAngleMaxRate": 120.0, "AccordAngleClipScale": 1.0}
B_LABEL = ("OPTIONAL / LATER DOSE -- NOT for V299's first drive. Config A with AccordAngleMaxRate 250 only (the setpoint "
           "rate cap 120 -> 250 deg/s). One dose per drive; stop it if hands-off 1229-freeze onsets reach >= 50 % of "
           "turn-ins at <= 8 m/s or stall-surges per turn double (rev 2 brief, section 7 X3). This _comment key is not in "
           "the encoded file.")

spec = importlib.util.spec_from_file_location("mgtc", os.path.join(KIT, "tools", "make_galaxy_toggle_config.py"))
K = importlib.util.module_from_spec(spec); spec.loader.exec_module(K)
K.positive_control()


def git(*args):
  return subprocess.run(["git", "-C", FORK, *args], capture_output=True, text=True, encoding="utf-8", check=True).stdout


def fork_codec(commit):
  src = git("show", f"{commit}:starpilot/system/the_galaxy/utilities.py")
  keep = [n for n in ast.parse(src).body if (isinstance(n, ast.FunctionDef) and n.name in
          {"xor_encrypt_decrypt", "encode_parameters", "decode_parameters"}) or
          (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "XOR_KEY" for t in n.targets))]
  ns = {"base64": base64, "json": json}
  exec(compile(ast.Module(body=keep, type_ignores=[]), "fork_utilities", "exec"), ns)
  assert ns["XOR_KEY"] == K.XOR_KEY
  return ns


assert git("rev-parse", V299_COMMIT).strip() == V299_COMMIT
assert subprocess.run(["git", "-C", FORK, "diff", "--quiet", "20d24ab79", V299_COMMIT, "--",
                       "starpilot/system/the_galaxy/utilities.py"]).returncode == 0, "the Galaxy codec moved"
F = fork_codec(V299_COMMIT)
fork_keys = set(re.findall(r'\{"(\w+)", \{', git("show", f"{V299_COMMIT}:common/params_keys.h")))
assert set(NEW_DEFAULTS) <= fork_keys, set(NEW_DEFAULTS) - fork_keys
decl = git("show", f"{V299_COMMIT}:common/params_keys.h")
for key, typ, default in (("AccordAngleMaxRate", "FLOAT", "120.0"), ("AccordAngleClipScale", "FLOAT", "1.0"),
                          ("AccordAngleBarFromEps", "BOOL", "0")):
  assert f'{{"{key}", {{PERSISTENT, {typ}, "{default}", "{default}", 2, SETTINGS_SIMPLE}}}}' in decl, key

base_path = os.path.join(HERE, BASE + ".json")
assert hashlib.sha256(open(base_path, "rb").read()).hexdigest() == BASE_SHA, "the V298 drive-1 config changed on disk"
base_enc = json.load(open(base_path, encoding="utf-8"))
base = json.load(open(os.path.join(HERE, BASE + ".decoded.json"), encoding="utf-8"))
assert K.decode_parameters(base_enc["data"]) == base == F["decode_parameters"](base_enc["data"]) and len(base) == 29
assert base["AccordEpsAngleLoop"] is True and base["UseAutoSteerDelay"] is True and base["SteerRatio"] == 16.84
assert not set(NEW_DEFAULTS) & set(base)

A = dict(base, AccordAngleBarFromEps=True, AccordAngleMaxRate=120.0, AccordAngleClipScale=1.0)
B = dict(A, AccordAngleMaxRate=250.0)
R = dict(base, **NEW_DEFAULTS)
configs = {OUT_A: (A, None), OUT_B: (B, B_LABEL), OUT_R: (R, None)}
assert {k: v for k, v in B.items() if A.get(k) != v} == {"AccordAngleMaxRate": 250.0}  # B = A + the one dose
shas = {}
for name, (vals, label) in configs.items():
  assert set(vals) <= fork_keys, set(vals) - fork_keys
  assert {k: v for k, v in vals.items() if k in base and v != base[k]} == {}, "a V298 drive-1 value moved"
  assert 120.0 <= vals["AccordAngleMaxRate"] <= 250.0 and vals["AccordAngleClipScale"] == 1.0  # inside the fork clamps
  wrapper = {"format": base_enc["format"], "version": base_enc["version"], "settingsCount": len(vals),
             "data": K.encode_parameters(vals)}
  assert F["encode_parameters"](vals) == wrapper["data"]
  p_enc, p_dec = os.path.join(HERE, name + ".json"), os.path.join(HERE, name + ".decoded.json")
  with open(p_enc, "x", encoding="utf-8") as fh:
    json.dump(wrapper, fh, indent=1)
  with open(p_dec, "x", encoding="utf-8") as fh:
    json.dump(({"_comment": label} | vals) if label else vals, fh, indent=1)
  back = json.load(open(p_enc, encoding="utf-8"))
  dec = json.load(open(p_dec, encoding="utf-8"))
  dec.pop("_comment", None)
  assert K.decode_parameters(back["data"]) == vals == F["decode_parameters"](back["data"]) == dec
  shas[name] = (hashlib.sha256(open(p_enc, "rb").read()).hexdigest(), hashlib.sha256(open(p_dec, "rb").read()).hexdigest())
  print("wrote %s.json (%d keys) sha256 %s; decoded %s; vs V298 drive-1: %s" % (
        name, len(vals), shas[name][0], shas[name][1], {k: (base.get(k, "<absent>"), v) for k, v in vals.items()
                                                         if base.get(k, "<absent>") != v}))
print("wall %.2f s" % (time.time() - T0))
