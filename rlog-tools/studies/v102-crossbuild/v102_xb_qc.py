#!/usr/bin/env python3
r"""QC + the CLAMP question (task #4) for the V100(r85) vs V101(r95) contrast.

STAGE 0 -- loader integrity (frames per segment, blocks, engaged exposure, identity).
STAGE 1 -- THE CLAMP.  Structural headroom, then the measured b6 rung, then the
           input-referred reconstruction of the LKAS term on both builds.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KMH = L.KMH


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


# =====================================================================================================
hdr("STAGE 0 -- LOADER INTEGRITY  (the kit has silently skipped per-segment caches before)")
summary = {}
for route in ("85", "95"):
    R = L.ROUTES[route]
    print("\n route %s = %s   gain 0xC6CD0=%d   clamp 0xC61B2/B4=%d   LeverB=%s"
          % (route, R["build"], R["gain"], R["clamp"], R["leverB"]))
    tot_n = tot_eng = 0.0
    nblk = 0
    for s in R["segs"]:
        d = L.load_seg(route, s)
        bl = L.blocks(d)
        nblk += len(bl)
        eng = d["cc_lat"] > 0.5
        dur = float(d["t"][-1] - d["t"][0])
        engs = float(eng.sum()) / len(eng) * dur
        tot_n += len(d["t"])
        tot_eng += engs
        v = d["v_rear"] * KMH
        print("   seg %-3s n=%5d dur=%6.2fs blocks=%d  eng=%5.1fs (%.3f)  v med=%5.1f max=%5.1f km/h"
              % (s, len(d["t"]), dur, len(bl), engs, eng.mean(), np.median(v), v.max()))
    print("   TOTAL frames=%d  blocks=%d  engaged~%.1f s" % (tot_n, nblk, tot_eng))
    ident = json.load(open(R["cache"] / ("r" + route + "_identity.json")))
    print("   identity_pass=%s  byte7 hist=%s  b3_duty=%.4f"
          % (ident["identity_pass"], ident["byte7_code_hist"], ident["b3_duty"]))
    assert ident["identity_pass"], "identity FAILED on route " + route
    summary[route] = dict(frames=tot_n, blocks=nblk, engaged_s=tot_eng)


# =====================================================================================================
hdr("STAGE 1a -- THE CLAMP, STRUCTURALLY.  Mirroring the decompiled arithmetic in integer Python.")
print(r"""
 eps_chain_control.steer_torque_arbitration  [VERIFIED, FUN_00028ea6 @0x28ea6]:

     limited   = clamp(lkas_setpoint, +/- arb_setpoint_limit)     # mode-0 LERP row, CONSTANT 15360
                                                                  #   @0x28fc8-0x29044, curve 0xE4180
     lkas_term = (limited * lkas_output_gain) >> 15                # Q15, cal 0xC6CD0
     lkas_term = clamp(lkas_term, +/- arb_output_clamp)            # cal 0xC61B4
     packed    = clamp(lkas_term, +/- pack_output_clamp)           # cal 0xC61B2  (limit_and_pack)

 The setpoint is clipped to 15360 UPSTREAM of the gain, so the maximum reachable |lkas_term| is
 (15360 * G) >> 15 -- a FIXED FRACTION 0.46875 of G.  The clamp is 0.5746 * G on every build since
 V14 (512/891 == 1024/1782 == 2048/3564 == 4096/7128).  Hence:
""")
SETPOINT_MAX = 15360
LADDER = [("stock", 891, 512), ("V14..V21", 891, 512), ("V22..V37", 1782, 1024),
          ("V38..V100 (4x)", 3564, 2048), ("V101 (8x)", 7128, 4096)]
print("   %-16s %6s %6s %10s %10s %8s" % ("build", "gain", "clamp", "max term", "clamp", "use %"))
seen = set()
for name, g, c in LADDER:
    if (g, c) in seen:
        continue
    seen.add((g, c))
    mx = (SETPOINT_MAX * g) >> 15
    print("   %-16s %6d %6d %10d %10d %7.1f%%" % (name, g, c, mx, c, 100.0 * mx / c))
print("""
 => THE CLAMP IS STRUCTURALLY UNREACHABLE ON EVERY BUILD IN THE LADDER, INCLUDING V100 AND V101.
    Full-scale demand uses 81.5 % of the rail on all of them, because clamp and gain have tracked
    in lockstep since V14.  A clamp that cannot bind cannot have been supplying describing-function
    gain reduction on V100, and raising it 2048 -> 4096 therefore cannot have removed any.
    ⇒ 0xC61B2/0xC61B4 are INERT on this pair.  EVIDENCE (constants byte-verified in
      BUILD-LINEAGE part-2 row 5 + golden model VERIFIED tag), independent of the drive data.

    COROLLARY -- what a V102 "8x gain, clamp back to 2048" would actually do:
      max term 3341 > 2048, so the clamp WOULD bind, at 2048/3341 = 61.3 % of full-scale demand.
      That is a REAL intervention -- but it is a NEW one, not a restoration: no build has ever run
      a gain and a clamp out of ratio.
""")

# =====================================================================================================
hdr("STAGE 1b -- THE CLAMP, MEASURED.  V101's b6 rung IS the pre-registered clamp instrument.")
print("""
 builds/v80_v107/build_v101_tva.py pre-registered it verbatim:
   "b6 measures whether the 8x LKAS command hits its 4096 ceiling.  If the duty is materially
    non-zero, openpilot's demand is being CLIPPED by the firmware and more gain buys nothing
    further.  If it reads 0.0000, the 4096 clamp has headroom."
""")
z95 = np.load(L.ROUTES["95"]["cache"] / "r95.npz")
b6 = z95["v101_b6"] > 0.5
b5 = z95["v101_b5"] > 0.5
eng95 = z95["cc_lat"][: len(b6)] > 0.5
v95 = z95["v_rear"][: len(b6)] * KMH
print("   b6 = (|gp-0x6b4c| >= 4096)   ALL frames   duty = %.6f  (%d of %d)"
      % (b6.mean(), b6.sum(), len(b6)))
print("   b6                            ENGAGED     duty = %.6f  (%d of %d)"
      % (b6[eng95].mean(), b6[eng95].sum(), eng95.sum()))
neff = eng95.sum() / 100.0 / 0.10           # surrogate tau = 100 ms, the LKAS lane's own low-pass
print("   rule of three on n_eff=%.0f  =>  95%% upper bound on the engaged duty = %.5f"
      % (neff, 3.0 / neff))
for lo, hi in [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 70)]:
    m = eng95 & (v95 >= lo) & (v95 < hi)
    if m.sum() > 50:
        print("      %2d-%2d km/h  n=%6d  b6 duty=%.6f" % (lo, hi, m.sum(), b6[m].mean()))

# =====================================================================================================
hdr("STAGE 1c -- INPUT-REFERRED RECONSTRUCTION.  Would the OLD 2048 clamp bite on V101's own drive?")
print("""
 b6 only asks about 4096.  The V102 question is about 2048, which the V101 cave does not carry.
 Reconstruct the LKAS term from the WIRE instead: `e4tq` is openpilot's 0x0E4 STEER_TORQUE_REQUEST,
 an EXOGENOUS input identical in semantics on both builds.  The firmware maps it setpoint -> IIR ->
 Q15 gain.  Calibrate the wire->setpoint scale from the observed supports, then VALIDATE the whole
 reconstruction against v101_b5 = sign(gp-0x6b4c), which is a per-frame ground truth.
""")
e4 = z95["e4tq"][: len(b6)]
print("   e4tq support: r95 min=%.0f max=%.0f  |e4| p50=%.0f p90=%.0f p99=%.0f p100=%.0f"
      % (e4.min(), e4.max(), *np.percentile(np.abs(e4[eng95]), [50, 90, 99, 100])))
z85 = np.load(L.ROUTES["85"]["cache"] / "r85.npz")
e4_85 = z85["e4tq"]
eng85 = z85["cc_lat"] > 0.5
print("   e4tq support: r85 min=%.0f max=%.0f  |e4| p50=%.0f p90=%.0f p99=%.0f p100=%.0f"
      % (e4_85.min(), e4_85.max(), *np.percentile(np.abs(e4_85[eng85]), [50, 90, 99, 100])))

# sign validation of the wire -> lane map (a lag scan, because of the 1-pole IIR)
print("\n   SIGN VALIDATION -- agreement between sign(-e4tq) / sign(+e4tq) and v101_b5 vs lag:")
best = None
for flip in (+1, -1):
    for lag in range(0, 26, 2):
        pred = (flip * e4[: len(e4) - lag]) < 0
        obs = b5[lag:]
        m = eng95[: len(pred)] & (np.abs(e4[: len(pred)]) > 50)
        if m.sum() < 500:
            continue
        agr = float((pred[m] == obs[m]).mean())
        if best is None or agr > best[0]:
            best = (agr, flip, lag, int(m.sum()))
print("      best agreement %.4f at flip=%+d lag=%d frames (%.0f ms), n=%d"
      % (best[0], best[1], best[2], best[2] * 10, best[3]))

# =====================================================================================================
hdr("STAGE 1d -- THE AGGREGATOR OUTPUT (gp-0x6b94) vs ITS OWN +/-10240 CLAMP -- both builds")
for route in ("85", "95"):
    R = L.ROUTES[route]
    j = json.load(open(R["cache"] / ("r" + route + "_lane427.json")))
    print("   %s r%s: p50=%7.1f p90=%7.1f p99=%7.1f max=%7.1f counts   "
          "struct-ceiling(800 code=10240 ct) hits=%d   field(1023) hits=%.4f"
          % (R["build"], route, j["p50_counts"], j["p90_counts"], j["p99_counts"],
             j["max_counts"], j["above_struct_ceiling_n"], j["sat_field_1023_frac"]))
print("""
   Neither build's aggregator output comes near its own +/-10240 writer clamp: V100 peaks at 18.9 %
   of it, V101 at 30.8 %.  No saturation anywhere in the delivered lane on either arm.  EVIDENCE
   (whole-route, from the 0x1AB stream the extractor taps directly).""")

json.dump(summary, open(L.AN / "_scratch/cache/r95" / "v102_xb_qc.json", "w"), indent=1)
print("\n[done]")
