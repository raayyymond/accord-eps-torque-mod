#!/usr/bin/env python3
r"""Extract route `9e` (**V103**) into `analysis-2020accord/_scratch/cache/r9e/`.

THE INSTRUMENT IS NOT REIMPLEMENTED.  Exactly the `decode/extract_r96_r97.py` pattern: add a row to
`decode_v84_probe_r6d.ROUTES`, then call `extract_r7d.extract_route()` -- the SAME code that wrote
every cache since `_scratch/cache/r6d/`.  Field names, ZOH/interp convention, sentinel definition, the
0x1AB full tap, the 0x14A byte-7 tap and the `row2raw14` off-by-one fix all come along unchanged.

===================================================================================================
ROUTE 9e == V103.  V102 BASE + Honda's dormant biquad armed engaged-only (4 B) + a 164 B cave.
===================================================================================================
    cal 0xC6CD0  5346    THE 6x LKAS FORWARD GAIN (stock 891)   -- FROZEN, same as V102
    cal 0xC61B2  3072    forward-path clamp                     -- FROZEN
    cal 0xC61B4  3072    arb-output clamp                       -- FROZEN
    cal 0xC649B  00->01  arms Honda's dormant biquad in FUN_000352b4
    0x35A06/0x35A12/0x35A18   arm SOURCE gp-0x671a -> gp-0x6806 (LKAS engaged), setfnc -> setfne

    byte4 b7 0x80 = gp-0x6b4c < 0                 sign for the 427 lane (427 source = 6b4c)
    byte4 b6 0x40 = |gp-0x6ada| >= |gp-0x6adc|    COMPARATOR: r24 vs r26
    byte4 b5 0x20 = |gp-0x6ae2| >= |gp-0x6b26|    COMPARATOR: friction vs inertia
    byte4 b4 0x10 = gp-0x6ada < 0                 sign of r24
    byte4 b3 0x08 = gp-0x3680 < 0                 *** NEW *** D_state (PID D-term) SIGN
    byte7[7:6]    = 3   (SAME CODE as V101/V102 -- NOT a unique identity witness)

    427 (0x1AB) = clamp(|gp-0x6b4c| * 5 >> 6, 0, 0x3FF)   => counts = wire * 12.8   [as V102]

🛑 IDENTITY.  V103 is the first build since V85 with NO single-frame identity witness: `byte7[7:6]`
   has all four codes allocated and `b3`'s two constant values are already claimed (V101 pins it 1,
   V102 pins it 0).  `builds/v80_v107/build_v103_tva.py`'s CONCRETE RULE FOR THE SCORER:
       **`b3` MUST VARY.**  A toggling b3 is categorically impossible on any predecessor.
       A constant `b3` means it is not V103, or the rung is dead -- STOP and report.

Usage:
    python decode/extract_r9e.py                 # full pipeline
    python decode/extract_r9e.py extract
    python decode/extract_r9e.py derive
    python decode/extract_r9e.py identity
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
    "9e": ("75604b0a432fdc89_0000009e--54bb0788af", 11,
           "analysis-2020accord/_scratch/cache/r9e", "r9es", "r9e", "V103"),
}
for _k, _v in NEW.items():
    D.ROUTES[_k] = _v

# ---- V103 427 spec: IDENTICAL to V102 -- same source (gp-0x6b4c), same packer (sar 6).
X.WIRE_SCALE["9e"] = 64.0 / 5.0
X.WIRE_SOURCE["9e"] = "gp-0x6b4c (11-SLOT ASSIST SUM), sar 6  [V102 repoint, carried unchanged]"

M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08
X.BITNAMES["9e"] = {
    "b7_sign_6b4c_neg": M_B7,
    "b6_CMP_absr24_ge_absr26": M_B6,
    "b5_CMP_absfriction_ge_absinertia": M_B5,
    "b4_sign_r24_neg": M_B4,
    "b3_sign_Dstate_neg": M_B3,          # *** NEW on V103 ***
}

IDENT_MASK = 0xC0
COUNTS_PER_LSB = 64.0 / 5.0
WIRE_SAT_FIELD = 1023
WIRE_SAT_STRUCT = 800          # (10240*5)>>6 -- the +-10240 writer clamp

DERIVED = ["v103_b7", "v103_b6", "v103_b5", "v103_b4", "v103_b3",
           "v102_b7", "v102_b6", "v102_b5", "v102_b4", "v102_b3",
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


def extract_route(route="9e"):
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


def derive(route="9e"):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    f = ROOT / cdir / (stem + ".npz")
    z = dict(np.load(f, allow_pickle=True))
    t = np.asarray(z["t"], float)
    n = len(t)

    p = np.asarray(z["probe"], int) & 0xFF
    assert len(p) == n, "probe/t length mismatch -- the pairing contract is broken"
    for nm, m in (("b7", M_B7), ("b6", M_B6), ("b5", M_B5), ("b4", M_B4), ("b3", M_B3)):
        z["v103_" + nm] = ((p & m) != 0).astype(float)
        z["v102_" + nm] = z["v103_" + nm]      # alias: b7/b6/b5/b4 are byte-identical to V102

    abt = np.asarray(z["ab_t1ab"], float)
    mt = np.asarray(z["ab_mt"], int)
    j = np.clip(np.searchsorted(abt, t, side="right") - 1, 0, len(mt) - 1)
    mag = mt[j].astype(float)
    sgn = np.where(z["v103_b7"] > 0.5, -1.0, 1.0)
    z["mag427"] = mag
    z["sgn427"] = sgn
    z["x6b4c"] = sgn * mag * COUNTS_PER_LSB
    # alias so `v102_xb_lib.CH` ("x6b94") finds a lane; IT IS A DIFFERENT CELL on r9e.
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
    print("    v103_b7..b3 decoded from `probe` (%d rows, SAFE pairing with `t`)" % n)
    print("    mag427  nonzero %.2f %%  distinct %d  max %.0f   sat@1023 %.4f %%  sat@800 %.4f %%"
          % (100 * np.mean(mag > 0), len(np.unique(mag)), mag.max(),
             100 * np.mean(mag >= 1023), 100 * np.mean(mag >= 800)))
    print("    v_rear  median %.2f km/h   lp_yaw finite %.1f %%"
          % (np.nanmedian(z["v_rear"]), 100 * np.mean(np.isfinite(z["lp_yaw"]))))
    return z


def identity(route="9e"):
    """V103 rule -- `builds/v80_v107/build_v103_tva.py`, verbatim: byte7[7:6]==3 (as V101/V102) AND **b3 VARIES**.
    No predecessor can produce a varying b3 (V101 pins 1, V102 pins 0), so a toggling b3 is a
    CATEGORICAL distinction.  A constant b3 => NOT V103, or the rung is dead => STOP."""
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
    live = {k: float(bits[k].mean()) for k in bits}
    b3_duty = live["b3"]
    b3_varies = bool(0.0005 < b3_duty < 0.9995)
    nlive = sum(1 for k in ("b6", "b5", "b4") if 0.001 < live[k] < 0.999)
    out = dict(route=route, build=lab, frames=int(n),
               byte7_code_hist={int(v): int(c) for v, c in zip(cu, cc)},
               byte7_code3_duty=duty3,
               b3_duty=b3_duty, b3_varies=b3_varies,
               b3_n_zero=int((~bits["b3"]).sum()), b3_n_one=int(bits["b3"].sum()),
               byte4_field_hist={int(v): int(c) for v, c in zip(fu, fc)},
               bit_duties=live, n_nonconstant_of_b6b5b4=int(nlive),
               rule="byte7[7:6]==3 at duty>=0.9999 AND b3 TAKES BOTH VALUES (V103's only witness)",
               identity_pass=bool(duty3 >= 0.9999 and b3_varies and nlive >= 1))
    print("\n  === IDENTITY, route %s (expected %s): %d 0x14A frames ===" % (route, lab, n))
    print("    byte7[7:6] code histogram: " +
          "  ".join("%d:%d" % (int(v), int(c)) for v, c in zip(cu, cc)))
    print("    byte7[7:6]==3 duty %.6f" % duty3)
    print("    *** b3 (D_state sign) duty %.6f   zeros %d   ones %d   VARIES=%s ***"
          % (b3_duty, out["b3_n_zero"], out["b3_n_one"], b3_varies))
    print("    byte4 field hist: " + "  ".join("%d:%d" % (int(v), int(c))
                                               for v, c in zip(fu, fc)))
    print("    bit duties (all frames): " +
          "  ".join("%s=%.4f" % (k, v) for k, v in sorted(live.items(), reverse=True)))
    print("    non-constant of b6/b5/b4: %d of 3" % nlive)
    print("    VERDICT: %s" % ("PASS -- this is V103" if out["identity_pass"] else "FAIL"))
    (ROOT / cdir / (stem + "_identity.json")).write_text(json.dumps(out, indent=1, default=float))
    return out


def lane427(route="9e"):
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
        extract_route("9e")
        derive("9e")
        identity("9e")
        lane427("9e")
        X.health("9e")
        X.census("9e")
    else:
        for r in (args[1:] or ["9e"]):
            fns[args[0]](r)
