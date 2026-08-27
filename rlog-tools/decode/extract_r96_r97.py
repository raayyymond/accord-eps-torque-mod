#!/usr/bin/env python3
r"""Extract route `96` (**V102, the 6x LKAS gain**) and route `97` (**V9b, STOCK**) into
`analysis-2020accord/_scratch/cache/r96/` and `_scratch/cache/r97/`.

THE INSTRUMENT IS NOT REIMPLEMENTED.  Exactly the `decode/extract_r95.py` pattern: add a row to
`decode_v84_probe_r6d.ROUTES`, then call `extract_r7d.extract_route()` -- the SAME code that wrote
every cache since `_scratch/cache/r6d/`.  Field names, ZOH/interp convention, sentinel definition, the 0x1AB
full tap, the 0x14A byte-7 tap and the `row2raw14` off-by-one fix all come along unchanged.

===================================================================================================
ROUTE 96 == V102.  V101 BASE + THREE CAL CELLS + a 154 B TWO-COMPARATOR CAVE + 427 -> gp-0x6b4c.
===================================================================================================
    cal 0xC6CD0  7128 -> 5346    THE 6x LKAS FORWARD GAIN (stock 891)
    cal 0xC61B2  4096 -> 3072       forward-path clamp tracking the gain
    cal 0xC61B4  4096 -> 3072       arb-output clamp tracking the gain

    byte4 b7 0x80 = gp-0x6b4c < 0                 sign for the 427 lane (427 REPOINTED to 6b4c)
    byte4 b6 0x40 = |gp-0x6ada| >= |gp-0x6adc|    COMPARATOR: r24 vs r26
    byte4 b5 0x20 = |gp-0x6ae2| >= |gp-0x6b26|    COMPARATOR: friction vs inertia
    byte4 b4 0x10 = gp-0x6ada < 0                 sign of r24
    byte4 b3 0x08 = 0  (IDENTITY -- a CLEARED bit)
    byte7[7:6]    = 3

    427 (0x1AB) = clamp(|gp-0x6b4c| * 5 >> 6, 0, 0x3FF)   => counts = wire * 12.8
                  SOURCE CHANGED vs V100/V101 (which packed gp-0x6b94).  Emitted as `x6b4c`.

===================================================================================================
ROUTE 97 == V9b, HONDA STOCK.  No cave, no repoint, gain 891 (1x).
===================================================================================================
    Measured on segment 0 before this file was written: byte7[7:6] == 0 at duty 1.0000 and
    byte4[7:3] == 0 at duty 1.0000 -- a completely dead cave field, which no modified build in this
    kit emits.  `derive()` still writes the v102_b* columns for r97; they are ALL ZERO BY
    CONSTRUCTION and carry no information.  Do not read them.

Usage:
    python decode/extract_r96_r97.py                 # both routes, full pipeline
    python decode/extract_r96_r97.py extract 96
    python decode/extract_r96_r97.py derive 96 97
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import extract_r7d as X  # noqa: E402
import rlog_parse        # noqa: E402

D = X.D

NEW = {
    "96": ("75604b0a432fdc89_00000096--57f5183b32", 15,
           "analysis-2020accord/_scratch/cache/r96", "r96s", "r96", "V102"),
    "97": ("75604b0a432fdc89_00000097--489d7896b3", 18,
           "analysis-2020accord/_scratch/cache/r97", "r97s", "r97", "V9b-STOCK"),
}
for _k, _v in NEW.items():
    D.ROUTES[_k] = _v

# ---- V102 427 spec: same PACKER (sar 6), DIFFERENT SOURCE.
for _r in ("96", "97"):
    X.WIRE_SCALE[_r] = 64.0 / 5.0
X.WIRE_SOURCE["96"] = "gp-0x6b4c (11-SLOT ASSIST SUM), sar 6  [V102 REPOINT; packer unchanged]"
X.WIRE_SOURCE["97"] = "HONDA STOCK 0x1AB -- not ours, carries no probe"

M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08
X.BITNAMES["96"] = {
    "b7_sign_6b4c_neg": M_B7,
    "b6_CMP_absr24_ge_absr26": M_B6,
    "b5_CMP_absfriction_ge_absinertia": M_B5,
    "b4_sign_r24_neg": M_B4,
    "b3_IDENTITY_const0": M_B3,
}
X.BITNAMES["97"] = dict(X.BITNAMES["96"])

IDENT_MASK = 0xC0
COUNTS_PER_LSB = 64.0 / 5.0
WIRE_SAT_FIELD = 1023
WIRE_SAT_STRUCT = 800          # (10240*5)>>6 -- the +-10240 writer clamp

DERIVED = ["v102_b7", "v102_b6", "v102_b5", "v102_b4", "v102_b3",
           "mag427", "sgn427", "x6b4c", "x6b94", "v_rear", "lp_yaw"]

_TAPPED_READ = rlog_parse.read_messages
MISSING_SEGMENTS = []
LP = {"t": [], "z": []}


def _read_guarded(path):
    p = Path(path)
    if not p.exists():
        MISSING_SEGMENTS.append(p.name)
        print("  segment file ABSENT, skipped: %s" % p.name, flush=True)
        return
    for evt in _TAPPED_READ(path):
        try:
            if evt.which() == "livePose":
                LP["t"].append(evt.logMonoTime * 1e-9)
                LP["z"].append(float(evt.livePose.angularVelocityDevice.z))
        except Exception:
            pass
        yield evt


rlog_parse.read_messages = _read_guarded


def extract_route(route):
    MISSING_SEGMENTS.clear()
    LP["t"].clear()
    LP["z"].clear()
    rep = X.extract_route(route)
    rep["segments_absent"] = list(MISSING_SEGMENTS)
    rep["livePose_samples"] = len(LP["t"])
    print("\n  segments absent from disk: %d   livePose samples: %d"
          % (len(MISSING_SEGMENTS), len(LP["t"])))
    cdir = ROOT / D.ROUTES[route][2]
    np.savez_compressed(cdir / (D.ROUTES[route][4] + "_lp.npz"),
                        t=np.array(LP["t"], float), z=np.array(LP["z"], float))
    return rep


def derive(route):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    f = ROOT / cdir / (stem + ".npz")
    z = dict(np.load(f, allow_pickle=True))
    t = np.asarray(z["t"], float)
    n = len(t)

    p = np.asarray(z["probe"], int) & 0xFF
    assert len(p) == n, "probe/t length mismatch -- the pairing contract is broken"
    for nm, m in (("b7", M_B7), ("b6", M_B6), ("b5", M_B5), ("b4", M_B4), ("b3", M_B3)):
        z["v102_" + nm] = ((p & m) != 0).astype(float)

    abt = np.asarray(z["ab_t1ab"], float)
    mt = np.asarray(z["ab_mt"], int)
    j = np.clip(np.searchsorted(abt, t, side="right") - 1, 0, len(mt) - 1)
    mag = mt[j].astype(float)
    sgn = np.where(z["v102_b7"] > 0.5, -1.0, 1.0)
    z["mag427"] = mag
    z["sgn427"] = sgn
    z["x6b4c"] = sgn * mag * COUNTS_PER_LSB
    # alias so `v102_xb_lib.CH` ("x6b94") finds a lane; IT IS A DIFFERENT CELL on r96.
    z["x6b94"] = z["x6b4c"]

    rl, rr = np.asarray(z["ws_rl"], float), np.asarray(z["ws_rr"], float)
    z["v_rear"] = 0.5 * (rl + rr)

    lpf = ROOT / cdir / (stem + "_lp.npz")
    z["lp_yaw"] = np.full(n, np.nan)
    if lpf.exists():
        L = np.load(lpf)
        lt, lz = np.asarray(L["t"], float), np.asarray(L["z"], float)
        if len(lt) > 1:
            t0 = float(z["t0_mono"][0])
            rel = lt - t0
            o = np.argsort(rel)
            z["lp_yaw"] = np.interp(t, rel[o], lz[o])

    np.savez_compressed(f, **z)
    for k in DERIVED:
        if k not in D.PASS_1D:
            D.PASS_1D.append(k)
    D.split(route)

    print("\n  === DERIVED COLUMNS, route %s (%s) ===" % (route, lab))
    print("    v102_b7..b3 decoded from `probe` (%d rows, SAFE pairing with `t`)" % n)
    print("    mag427  nonzero %.2f %%  distinct %d  max %.0f   sat@1023 %.4f %%  sat@800 %.4f %%"
          % (100 * np.mean(mag > 0), len(np.unique(mag)), mag.max(),
             100 * np.mean(mag >= 1023), 100 * np.mean(mag >= 800)))
    print("    v_rear  median %.2f km/h   lp_yaw finite %.1f %%"
          % (np.nanmedian(z["v_rear"]), 100 * np.mean(np.isfinite(z["lp_yaw"]))))
    return z


def identity(route):
    """V102 rule: byte7[7:6] == 3 AND b3 == 0.  The b3 half asserts an ABSENT bit, so this also
    demands that the byte4 field be doing NEW work (b6 or b5 or b4 non-constant)."""
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / (stem + ".npz"), allow_pickle=True)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    b7 = np.asarray(z["raw14_b7"], int) & 0xFF
    n = len(b4)
    code = (b7 & IDENT_MASK) >> 6
    cu, cc = np.unique(code, return_counts=True)
    field = (b4 >> 3) & 0x1F
    fu, fc = np.unique(field, return_counts=True)
    bits = {k: ((b4 & m) != 0) for k, m in
            (("b7", M_B7), ("b6", M_B6), ("b5", M_B5), ("b4", M_B4), ("b3", M_B3))}
    duty3 = float((code == 3).mean())
    b3z = float((~bits["b3"]).mean())
    joint = float(((code == 3) & ~bits["b3"]).mean())
    live = {k: float(bits[k].mean()) for k in bits}
    nlive = sum(1 for k in ("b6", "b5", "b4") if 0.001 < live[k] < 0.999)
    out = dict(route=route, build=lab, frames=int(n),
               byte7_code_hist={int(v): int(c) for v, c in zip(cu, cc)},
               byte7_code3_duty=duty3, b3_zero_duty=b3z,
               joint_code3_and_b3zero=joint,
               byte4_field_hist={int(v): int(c) for v, c in zip(fu, fc)},
               bit_duties=live, n_nonconstant_of_b6b5b4=int(nlive),
               rule="byte7[7:6]==3 AND b3==0 on the frame, AND >=1 of b6/b5/b4 non-constant",
               identity_pass=bool(duty3 >= 0.9999 and b3z >= 0.9999 and nlive >= 1))
    print("\n  === IDENTITY, route %s (expected %s): %d 0x14A frames ===" % (route, lab, n))
    print("    byte7[7:6] code histogram: " +
          "  ".join("%d:%d" % (int(v), int(c)) for v, c in zip(cu, cc)))
    print("    byte7[7:6]==3 duty %.6f   b3==0 duty %.6f   JOINT %.6f" % (duty3, b3z, joint))
    print("    byte4 field hist: " + "  ".join("%d:%d" % (int(v), int(c))
                                               for v, c in zip(fu, fc)))
    print("    bit duties (all frames): " +
          "  ".join("%s=%.4f" % (k, v) for k, v in sorted(live.items(), reverse=True)))
    print("    non-constant of b6/b5/b4: %d of 3" % nlive)
    print("    VERDICT: %s" % ("PASS" if out["identity_pass"] else "FAIL"))
    (ROOT / cdir / (stem + "_identity.json")).write_text(json.dumps(out, indent=1, default=float))
    return out


def lane427(route):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / (stem + ".npz"), allow_pickle=True)
    mt = np.asarray(z["ab_mt"], int)
    n = len(mt)
    out = dict(route=route, build=lab, frames=int(n), source=X.WIRE_SOURCE[route],
               nonzero_frac=float(np.mean(mt > 0)), distinct=int(len(np.unique(mt))),
               p50=float(np.percentile(mt, 50)), p90=float(np.percentile(mt, 90)),
               p99=float(np.percentile(mt, 99)), max=int(mt.max()),
               sat_field_1023_frac=float(np.mean(mt >= WIRE_SAT_FIELD)),
               sat_struct_800_frac=float(np.mean(mt >= WIRE_SAT_STRUCT)))
    print("\n  === CAN 427 LANE, route %s (%s) ===" % (route, lab))
    print("    source: %s" % out["source"])
    print("    %d frames  nonzero %.2f %%  distinct %d  p50 %.0f  p90 %.0f  p99 %.0f  max %d"
          % (n, 100 * out["nonzero_frac"], out["distinct"], out["p50"], out["p90"],
             out["p99"], out["max"]))
    print("    sat@1023 %.4f %%   sat@800(structural) %.4f %%"
          % (100 * out["sat_field_1023_frac"], 100 * out["sat_struct_800_frac"]))
    (ROOT / cdir / (stem + "_lane427.json")).write_text(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    fns = {"extract": extract_route, "derive": derive, "identity": identity,
           "lane427": lane427, "health": X.health, "census": X.census}
    if not args:
        for r in ("96", "97"):
            extract_route(r)
            derive(r)
            identity(r)
            lane427(r)
            X.health(r)
            X.census(r)
    else:
        for r in (args[1:] or ["96", "97"]):
            fns[args[0]](r)
