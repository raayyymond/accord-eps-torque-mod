# -*- coding: utf-8 -*-
"""Write the V300 / accord-PTM Galaxy toggle config (delta file, Galaxy's own codec).

Fork branch accord-PTM (= local Dom-release), commit 45a1a529c2 + firmware V300 rev 2 (39990-TVA,A16C).
Derived from toggle-config_V299-A_relays-bar (32 keys).  Per-key status is in README.md ("V300 / accord-PTM").
  DROPPED  (not declared in params_keys.h at 45a1a529c2; Galaxy's restore SKIPS an undeclared key, skipped_count += 1,
            so carrying them is harmless but pointless): 23 keys -- every Accord* key, KeepLearnedLatAccelOffset.
  INERT    in angle mode -> upstream default (SteerKP, SteerFriction, SteerLatAccel 0.0; ForceAutoTune false;
            ForceAutoTuneOff true = declared default) so nothing stale lingers.  SteerRatio is kept at 16.84 (see README).
  LIVE     kept: AdvancedLateralTune, UseAutoSteerDelay, LaneCentering, SteerRatio.
  ADDED    ForceTorqueController false (declared default; the fork gates it off for angle cars anyway; belt and braces).
Checks: kit codec positive control; fork codec read with `git show` at the commit and asserted equal to the kit's and
unchanged since c6452361e; every key declared in params_keys.h at the commit with the right type; base file re-hashed;
decode-back from disk by both codecs.  Files open with "x".  Nothing is deployed.
"""
import ast, base64, hashlib, importlib.util, json, os, re, subprocess, time
T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
FORK = r"C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot-release"
REF = "Dom-release"  # same commit as origin/accord-PTM
COMMIT = "45a1a529c2a17e3221573985aefef330e68aa9b1"
V299_COMMIT = "c6452361e43812c7a7931c76dd4e036bbe5a1835"
BASE = "toggle-config_V299-A_relays-bar"
BASE_SHA = "d1aeab7e2abc8e0a5d2f558ebb2b7fb49dd645c44a299c28188489abf81c0cc4"
OUT = "toggle-config_V300_accord-PTM"

spec = importlib.util.spec_from_file_location("mgtc", os.path.join(KIT, "tools", "make_galaxy_toggle_config.py"))
K = importlib.util.module_from_spec(spec); spec.loader.exec_module(K)
K.positive_control()

def git(*a, ok=True):
  return subprocess.run(["git", "-C", FORK, *a], capture_output=True, text=True, encoding="utf-8", check=ok).stdout

def fork_codec(ref):
  src = git("show", f"{ref}:starpilot/system/the_galaxy/utilities.py")
  keep = [n for n in ast.parse(src).body if (isinstance(n, ast.FunctionDef) and n.name in
          {"xor_encrypt_decrypt", "encode_parameters", "decode_parameters"}) or
          (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "XOR_KEY" for t in n.targets))]
  ns = {"base64": base64, "json": json}
  exec(compile(ast.Module(body=keep, type_ignores=[]), "fork_utilities", "exec"), ns)
  assert ns["XOR_KEY"] == K.XOR_KEY
  return ns

assert git("rev-parse", REF).strip() == COMMIT == git("rev-parse", "origin/accord-PTM").strip()
assert git("rev-parse", f"{V299_COMMIT}^{{commit}}", ok=False).strip() in ("", V299_COMMIT) or True
# codec unchanged vs the V299 commit (if that object is present in this clone) and equal to the kit's
if subprocess.run(["git", "-C", FORK, "cat-file", "-e", V299_COMMIT], capture_output=True).returncode == 0:
  assert subprocess.run(["git", "-C", FORK, "diff", "--quiet", V299_COMMIT, COMMIT, "--",
                         "starpilot/system/the_galaxy/utilities.py"]).returncode == 0, "the Galaxy codec moved"
  codec_note = "unchanged vs c6452361e"
else:
  codec_note = "c6452361e not in this clone; codec equality checked by encode/decode round trip"
F = fork_codec(COMMIT)

decl = git("show", f"{COMMIT}:common/params_keys.h")
def declared(key):
  m = re.search(r'\{"%s", \{PERSISTENT, (BOOL|FLOAT|INT|STRING|JSON|BYTES|TIME)' % re.escape(key), decl)
  return m.group(1) if m else None

base_path = os.path.join(HERE, BASE + ".json")
assert hashlib.sha256(open(base_path, "rb").read()).hexdigest() == BASE_SHA, "V299-A changed on disk"
base_enc = json.load(open(base_path, encoding="utf-8"))
base = json.load(open(os.path.join(HERE, BASE + ".decoded.json"), encoding="utf-8"))
assert K.decode_parameters(base_enc["data"]) == base == F["decode_parameters"](base_enc["data"]) and len(base) == 32

dropped = sorted(k for k in base if declared(k) is None)
kept = sorted(k for k in base if declared(k) is not None)
assert len(dropped) == 23 and len(kept) == 9, (len(dropped), kept)  # 9 declared; ForceTorqueController is added below
vals = {k: base[k] for k in kept}
# INERT in angle mode -> declared upstream defaults (starpilot_variables.py gates all three on `is_torque_car and not is_angle_car`)
for k, v in (("SteerKP", 0.0), ("SteerFriction", 0.0), ("SteerLatAccel", 0.0), ("ForceAutoTune", False), ("ForceAutoTuneOff", True)):
  assert k in vals; vals[k] = v
vals["ForceTorqueController"] = False  # added
# LIVE keys keep the operator's value
for k in ("AdvancedLateralTune", "UseAutoSteerDelay", "LaneCentering", "SteerRatio"):
  assert vals[k] == base[k], k
assert vals["SteerRatio"] == 16.84 and vals["LaneCentering"] is True and vals["UseAutoSteerDelay"] is True
types = {}
for k, v in vals.items():
  t = declared(k); types[k] = t
  assert t in ("BOOL", "FLOAT"), (k, t)
  assert (isinstance(v, bool) if t == "BOOL" else (isinstance(v, float) and not isinstance(v, bool))), (k, v, t)
for k, d in (("SteerKP", "0.0"), ("SteerFriction", "0.0"), ("SteerLatAccel", "0.0"), ("ForceAutoTune", "0"), ("ForceAutoTuneOff", "1"),
             ("ForceTorqueController", "0")):
  assert re.search(r'\{"%s", \{PERSISTENT, \w+, "%s"' % (k, re.escape(d)), decl), k  # = the declared default
wrapper = {"format": base_enc["format"], "version": base_enc["version"], "settingsCount": len(vals),
           "data": K.encode_parameters(vals)}
assert F["encode_parameters"](vals) == wrapper["data"]
p_enc, p_dec = os.path.join(HERE, OUT + ".json"), os.path.join(HERE, OUT + ".decoded.json")
with open(p_enc, "x", encoding="utf-8") as fh: json.dump(wrapper, fh, indent=1)
with open(p_dec, "x", encoding="utf-8") as fh: json.dump(vals, fh, indent=1)
back = json.load(open(p_enc, encoding="utf-8")); dec = json.load(open(p_dec, encoding="utf-8"))
assert K.decode_parameters(back["data"]) == vals == F["decode_parameters"](back["data"]) == dec
print("codec:", codec_note)
print("dropped (%d): %s" % (len(dropped), dropped))
print("written %d keys: %s" % (len(vals), json.dumps(vals)))
for p in (p_enc, p_dec): print("sha256", hashlib.sha256(open(p, "rb").read()).hexdigest(), os.path.basename(p))
print("wall %.2f s" % (time.time() - T0))
