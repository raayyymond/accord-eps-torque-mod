# -*- coding: utf-8 -*-
"""aw1_codec_wiring.py -- ADV "wiring+observability", part (a)+(b): how the fork at Dom 20d24ab79 actually IMPORTS and READS
the V295 r2 / r2alt toggle configs.  Criteria: ../ADV-wiring-r2-CRITERIA.md (written before this ran).

Everything fork-side is read with `git show 20d24ab79:<path>` (object store only; the fork working tree is not touched).
Independent of the designer's fc_codec.py / f8 / f9: the codec is re-derived here two ways
  M1 = the fork's OWN functions (xor_encrypt_decrypt / decode_parameters / encode_parameters) cut out of utilities.py by
       source text and exec'd;
  M2 = a hand-written decoder (b64 -> XOR with the key string regex-read from utilities.py -> json).
Then the Galaxy restore path (the_galaxy.py restore_toggle_values / _restore_toggle_values / _coerce_toggle_restore_value /
_get_toggle_backup_keys) is SIMULATED on each file, with the key table parsed from common/params_keys.h @20d24ab79,
and starpilot_variables.update()'s get_value clamps are re-evaluated from their own source text on r71b's CarParams.
ANALYSIS ONLY: sends nothing, flashes nothing, writes nothing outside ./out.
"""
import ast
import base64
import hashlib
import json
import math
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
REF = os.path.join(KIT, "analysis-2020accord", "reference")
FORK = r"C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot"
C = "20d24ab79"
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
LOG = []


def pr(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


def show(path, binary=False):
    r = subprocess.run(["git", "-C", FORK, "show", "%s:%s" % (C, path)], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode("utf-8")


def sha(b):
    return hashlib.sha256(b).hexdigest()


FILES = {
    "r1_flown": "toggle-config_V294_accel-trim_r1",
    "r2": "toggle-config_V295_r2",
    "r2_REV": "toggle-config_V295_r2_REVERT_to_V294_r1",
    "r2alt": "toggle-config_V295_r2alt_KiHigh0.8_GATE-FAIL-G4-G8",
    "r2alt_REV": "toggle-config_V295_r2alt_KiHigh0.8_GATE-FAIL-G4-G8_REVERT_to_V294_r1",
}
FAIL = []

# ---------------------------------------------------------------------------------------------------------------- codec
util_src = show("starpilot/system/the_galaxy/utilities.py")
pr("fork utilities.py @%s sha256 %s" % (C, sha(util_src.encode())[:16]))
tree = ast.parse(util_src)
seg = {}
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in ("xor_encrypt_decrypt", "decode_parameters", "encode_parameters"):
        seg[node.name] = ast.get_source_segment(util_src, node)
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "XOR_KEY" for t in node.targets):
        seg["XOR_KEY"] = ast.get_source_segment(util_src, node)
assert set(seg) == {"xor_encrypt_decrypt", "decode_parameters", "encode_parameters", "XOR_KEY"}, seg.keys()
ns = {"base64": base64, "json": json}
exec("\n\n".join(seg[k] for k in ("XOR_KEY", "xor_encrypt_decrypt", "decode_parameters", "encode_parameters")), ns)
KEY = re.search(r'^XOR_KEY\s*=\s*"([^"]+)"', util_src, re.M).group(1)
pr("XOR_KEY (regex) == XOR_KEY (exec):", KEY == ns["XOR_KEY"])


def m2_decode(data):
    raw = base64.b64decode(data).decode("utf-8")
    return json.loads("".join(chr(ord(c) ^ ord(KEY[i % len(KEY)])) for i, c in enumerate(raw)))


# ------------------------------------------------------------------------------------------- the restore path (source)
gal_src = show("starpilot/system/the_galaxy/the_galaxy.py")
TOGGLE_BACKUP_FORMAT = re.search(r'^TOGGLE_BACKUP_FORMAT\s*=\s*"([^"]+)"', gal_src, re.M).group(1)
TOGGLE_BACKUP_VERSION = int(re.search(r'^TOGGLE_BACKUP_VERSION\s*=\s*(\d+)', gal_src, re.M).group(1))
MAXB = int(re.search(r'^TOGGLE_BACKUP_MAX_ENCODED_BYTES\s*=\s*([\d_]+)', gal_src, re.M).group(1).replace("_", ""))
restore_body = gal_src[gal_src.index("def restore_toggle_values"):gal_src.index("def _restore_toggle_values")]
pr("restore: format must be None or %r ; version int <= %d ; data str <= %d bytes ; settingsCount read by restore: %s"
   % (TOGGLE_BACKUP_FORMAT, TOGGLE_BACKUP_VERSION, MAXB, "settingsCount" in restore_body))
rt_body = gal_src[gal_src.index("def _restore_toggle_values"):gal_src.index("def _restore_toggle_values") + 6000]
pr("_restore_toggle_values: onroad/parked lock applies to non-personality keys: %s (lock only when profile is not None or "
   "parked_personality_keys)" % ("_personality_settings_write_locked()" in rt_body and "parked_personality_keys" in rt_body))

# params_keys.h table
pk = show("common/params_keys.h")
KT = {}
for m in re.finditer(r'\{"([A-Za-z0-9_]+)",\s*\{([^}]*)\}\}', pk):
    fields = [f.strip() for f in m.group(2).split(",")]
    KT[m.group(1)] = fields
var_src = show("starpilot/common/starpilot_variables.py")
excl = set(re.findall(r'"([A-Za-z0-9_]+)"', var_src[var_src.index("EXCLUDED_KEYS = {"):var_src.index("}", var_src.index("EXCLUDED_KEYS = {"))]))
renames = var_src[var_src.index("LEGACY_STARPILOT_PARAM_RENAMES = {"):var_src.index("}", var_src.index("LEGACY_STARPILOT_PARAM_RENAMES = {"))]
so = show("common/params_pyx.so", binary=True)


def coerce(key, value):
    """the_galaxy._coerce_toggle_restore_value, BOOL / INT / FLOAT branches (the only types these keys have)."""
    t = KT[key][1]
    if t == "BOOL":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str) and value.strip().lower() in {"1", "true", "yes", "on", "0", "false", "no", "off", ""}:
            return value.strip().lower() in {"1", "true", "yes", "on"}
        raise ValueError("bool")
    if t == "INT":
        if isinstance(value, bool):
            raise ValueError("int")
        return int(float(value))
    if t == "FLOAT":
        if isinstance(value, bool):
            raise ValueError("float from bool -> SKIPPED by the restore")
        r = float(value)
        if not math.isfinite(r):
            raise ValueError("nonfinite")
        return r
    raise ValueError("type %s not handled here" % t)


# -------------------------------------------------------------------------------------------------------- the files
dec = {}
for tag, stem in FILES.items():
    pj, pd = os.path.join(REF, stem + ".json"), os.path.join(REF, stem + ".decoded.json")
    bj, bd = open(pj, "rb").read(), open(pd, "rb").read()
    w = json.loads(bj)
    d_file = json.loads(bd)
    d1 = ns["decode_parameters"](w["data"])
    d2 = m2_decode(w["data"])
    ok_codec = (d1 == d2 == d_file) and all(type(d1[k]) is type(d_file[k]) for k in d1)
    reenc = ns["encode_parameters"](d1) == w["data"]
    # wrapper checks exactly as restore_toggle_values
    ok_wrap = (w.get("format") in (None, TOGGLE_BACKUP_FORMAT) and isinstance(w.get("version", 1), int)
               and w.get("version", 1) <= TOGGLE_BACKUP_VERSION and isinstance(w.get("data"), str)
               and w["data"].strip() != "" and len(w["data"].encode()) <= MAXB and isinstance(d1, dict))
    pr("\n[%s] %s.json sha256 %s ; decoded sha256 %s" % (tag, stem, sha(bj), sha(bd)))
    pr("   wrapper keys %s ; format %r version %r settingsCount %r (len %d)" % (sorted(w), w.get("format"), w.get("version"),
                                                                             w.get("settingsCount"), len(d1)))
    pr("   M1 fork decode == M2 hand decode == .decoded.json (values AND JSON types): %s ; fork re-encode == data: %s ; "
       "restore wrapper gate: %s" % (ok_codec, reenc, ok_wrap))
    if not (ok_codec and ok_wrap):
        FAIL.append("W5 codec/wrapper %s" % tag)
    # key-level restore simulation
    rows = []
    for k, v in d1.items():
        f = KT.get(k)
        known = f is not None
        persistent = known and "PERSISTENT" in f[0]
        dontlog = known and "DONT_LOG" in f[0]
        has_default = known and len(f) >= 3 and f[2].startswith('"')
        allowed = known and persistent and not dontlog and has_default and k not in excl and ('"%s"' % k) not in renames
        in_so = k.encode() in so
        try:
            cv = coerce(k, v)
            cerr = None
        except ValueError as e:
            cv, cerr = None, str(e)
        rows.append((k, v, f[1] if known else None, allowed, in_so, cv, cerr))
        if not allowed or cerr or cv != v or not in_so:
            FAIL.append("W5 key %s in %s: allowed %s in_so %s coerce %r err %s" % (k, tag, allowed, in_so, cv, cerr))
    pr("   restore sim: %d/%d keys ALLOWED (params_keys.h PERSISTENT, !DONT_LOG, default, !EXCLUDED, !renamed), "
       "%d/%d present in the committed common/params_pyx.so, %d/%d coerce to the same value with no error"
       % (sum(r[3] for r in rows), len(rows), sum(r[4] for r in rows), len(rows),
          sum(1 for r in rows if r[6] is None and r[5] == r[1]), len(rows)))
    dec[tag] = d1

r1 = dec["r1_flown"]
pr("\nIDENTITY CLAIMS")
b = {t: open(os.path.join(REF, s + ".json"), "rb").read() for t, s in FILES.items()}
for t in ("r2", "r2_REV", "r2alt_REV"):
    same = b[t] == b["r1_flown"]
    pr("   %s.json byte-identical to the flown r1 .json: %s" % (t, same))
    if not same:
        FAIL.append("W6 %s not byte-identical to r1" % t)
diff = {k: (r1.get(k), dec["r2alt"].get(k)) for k in set(r1) | set(dec["r2alt"]) if r1.get(k) != dec["r2alt"].get(k)}
pr("   r2alt vs r1 (union of keys): %s ; same key SET: %s" % (diff, set(r1) == set(dec["r2alt"])))
if diff != {"AccordTorqueKiHigh": (0.0, 0.8)} or set(r1) != set(dec["r2alt"]):
    FAIL.append("W6 r2alt delta is not exactly KiHigh")
pr("   REVERT names every key r2alt set (delta-format safety): %s" % (set(dec["r2alt"]) <= set(dec["r2alt_REV"])))

# ---------------------------------------------------------------------------------- starpilot_variables clamps (source)
pr("\nstarpilot_variables.update() @%s: each key's get_value condition / default / clamp, evaluated on r71b's CarParams" % C)
meta = json.load(open(os.path.join(KIT, "_scratch", "cache", "75604b0a432fdc89_00000071--a7b8ba5d9d", "meta.json")))
cp = meta["carparams"]
pr("   r71b carParams.lateralTuning:", cp["lateralTuning"])
lt = cp["lateralTuning"]
lt = lt.get("torque", lt) if isinstance(lt, dict) else {}
EV = dict(latAccelFactor=float(lt.get("latAccelFactor", 1.689333438873291)), friction=float(lt.get("friction", 0.2120497077703476)),
          steerKp=0.6, steerRatio=float(cp["steerRatio"]), STEER_KP_MIN=0.05, STEER_KP_MAX_MULT=5.0,
          LAT_ACCEL_FACTOR_MAX_MULT=10.0)
assert re.search(r"^STEER_KP_MIN = 0\.05", var_src, re.M) and re.search(r"^STEER_KP_MAX_MULT = 5\.0", var_src, re.M)
assert re.search(r"^LAT_ACCEL_FACTOR_MAX_MULT = 10\.0", var_src, re.M)
tq_src = show("selfdrive/controls/lib/latcontrol_torque.py")
assert re.search(r"^KP = 0\.6$", tq_src, re.M), "KP"
toggles_expected = {}
for k, v in r1.items():
    pat = re.compile(r'self\.get_value\("%s"(.*?)\)(\]\])?\s*$' % k, re.M)
    mm = [m for m in pat.finditer(var_src)]
    line = mm[0].group(0) if mm else None
    mn = re.search(r"min=([^,)]+)", line) if line else None
    mx = re.search(r"max=([^,)]+)", line) if line else None
    cond = re.search(r"condition=([^=]+?)(?:, default|, min|, max|\)$)", line) if line else None
    lo = eval(mn.group(1), {}, EV) if mn else None
    hi = eval(mx.group(1), {}, EV) if mx else None
    for vv in (v, dec["r2alt"][k]):
        if isinstance(vv, bool) or lo is None:
            continue
        if not (lo <= vv <= hi):
            FAIL.append("W4 %s=%r outside [%r, %r]" % (k, vv, lo, hi))
    pr("   %-26s file %-6s r2alt %-6s clamp [%s, %s]  condition: %s" % (
        k, v, dec["r2alt"][k], None if lo is None else round(lo, 5), None if hi is None else round(hi, 5),
        cond.group(1).strip() if cond else ("(no get_value line found)" if not line else "(none)")))
    if not line:
        pr("      !! no get_value(\"%s\") in starpilot_variables.py -- see the grep below" % k)

# the use_custom_* logic (Python precedence: A and B and C or D == (A and B and C) or D)
fr, lf = 0.011, 14.0
ucf = (round(fr, 2) != round(EV["friction"], 2)) and True and not False or True
ucl = (round(lf, 2) != round(EV["latAccelFactor"], 2)) and True and not False or True
pr("   use_custom_friction: round(0.011,2)=%r vs round(stock,2)=%r -> %s even WITHOUT ForceAutoTuneOff ; with FATO -> True"
   % (round(fr, 2), round(EV["friction"], 2), round(fr, 2) != round(EV["friction"], 2)))
pr("   use_custom_latAccelFactor: round(14.0,2) != round(%.4f,2) -> %s ; with FATO -> True" % (EV["latAccelFactor"], ucl))
pr("   toggle.friction keeps the UNROUNDED 0.011 (round() is only in the comparison)")

# ----------------------------------------------------------------------------------------- _sync_stock_param back-fill
pr("\n_sync_stock_param (the route-73 back-fill) re-evaluated for the three synced keys in the files:")


def sync(stock_live, stock_param, cur, unset=False):
    """returns (new_value, new_stock) per starpilot_variables._sync_stock_param @20d24ab79"""
    if math.isclose(stock_live, 0.0, abs_tol=1e-6):
        return cur, stock_param
    stock_known = stock_param is not None and math.isfinite(stock_param)
    cs = stock_param if stock_known else 0.0
    if math.isclose(cs, stock_live, abs_tol=1e-6):
        return cur, stock_param
    upd = unset or (stock_known and math.isclose(cur, cs, abs_tol=1e-6))
    return (stock_live if upd else cur), stock_live


P = meta["init"]["params"]
for key, stock_key, live in (("SteerFriction", "SteerFrictionStock", EV["friction"]), ("SteerKP", "SteerKPStock", 0.6),
                             ("SteerLatAccel", "SteerLatAccelStock", EV["latAccelFactor"])):
    cur = float(r1[key])
    st = float(P[stock_key])
    outs = [sync(live, st, cur), sync(live, None, cur), sync(live, 99.0, cur), sync(1.0, st, cur), sync(live, cur, cur)]
    pr("   %-14s file %-6s stock(initData) %.6g : steady %s ; stock unknown %s ; stock changed %s ; other-platform stock %s ;"
       " [hazard case] stock==file value %s" % (key, cur, st, outs[0][0], outs[1][0], outs[2][0], outs[3][0], outs[4][0]))
    if any(o[0] != cur for o in outs[:4]):
        FAIL.append("W3 back-fill of %s" % key)
sync_src = var_src[var_src.index("def _sync_stock_param"):var_src.index("def _migrate_steer_delay_mode")]
pr("   the fix of 2026-09-14 is present at %s (explicit 0.0 is a user value): %s" % (
    C, "An explicit 0.0 is a user value" in sync_src))
pr("   synced keys at %s: %s" % (C, re.findall(r'self\._sync_stock_param\("([A-Za-z]+)"', var_src)))

# ------------------------------------------------------------------------------------------------ SafeMode / r71b state
sm_src = show("starpilot/common/safe_mode.py")
managed = set(re.findall(r'^\s+"([A-Za-z0-9]+)",$', sm_src[sm_src.index("SAFE_MODE_MANAGED_KEYS"):sm_src.index(")", sm_src.index("SAFE_MODE_MANAGED_KEYS"))], re.M))
pr("\nSafeMode-managed keys among the file's 26: %d/26 ; r71b initData SafeMode=%r ; runtime safe_mode=%r"
   % (len(set(r1) & managed), P.get("SafeMode"), meta["starpilot_toggles"]["first"]["toggles"].get("safe_mode")))

# initData on r71b: every file key present (the device's compiled library knows it) and equal to r1
pr("r71b initData.params: file keys present %d/26 ; equal to r1 %d/26" % (
    sum(k in P for k in r1), sum(k in P and abs(float(P[k]) - (float(v) if not isinstance(v, bool) else float(v))) < 1e-9
                                  for k, v in r1.items())))

pr("\nFAIL list:", FAIL if FAIL else "NONE")
open(os.path.join(OUT, "aw1_codec_wiring_out.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
