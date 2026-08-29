#!/usr/bin/env python3
r"""score/score_v102.py -- THE STANDING POST-FLIGHT SCORER FOR V102 (6x LKAS gain, `0xC6CD0` = 5346).

    python score/score_v102.py <route>          e.g.  python score/score_v102.py 96
    python score/score_v102.py --selftest       runs the whole pipeline on r95 under V101's identity rule,
                                          to prove the machinery works before the drive exists

Everything is PRE-REGISTERED here, before the flight.  Baselines are RECOMPUTED from `_scratch/cache/r85`
(V100, 4x) and `_scratch/cache/r95` (V101, 8x) at run time by the same estimator, so no stored constant can
go stale; the orchestrator's pre-registered numbers are printed alongside as the record.

=====================================================================================================
THE PREDICTION BEING TESTED
=====================================================================================================
    22-26 Hz shape at 6x  =  0.61x [0.57 - 0.66] of V101, i.e. ~2.0x of V100
    wheel rate under a hard command  =  0.78x [0.74 - 0.81] of V101, i.e. ~1.43x of V100
    from  A(m) ~ m^1.74 [1.43-1.96]  and  authority(m) ~ m^0.88 [0.75-1.04]
    🛑 p = 1.74 IS AN EMPIRICAL EXPONENT FROM **TWO POINTS** (4x and 8x), NOT A PHYSICAL LAW.
       No 1x or 2x route survives with usable channels.  It is untested outside 4x-8x.

    DECISION RULE, pre-registered:
      shape(V102)/shape(V101) <= ~0.7  =>  the dose-response HOLDS; 6x is on the curve.
      shape(V102)/shape(V101) ~= 1.0   =>  🛑 THE GAIN IS NOT THE CARRIER and this session's
                                            attribution is REFUTED.  Say so plainly.
      anything INSIDE the placebo floor =>  NOT A RESULT.  Do not report a direction.

=====================================================================================================
V102 CAVE  (byte4; identity in byte7[7:6])
=====================================================================================================
    b7 0x80 = gp-0x6b4c < 0                      -- sign for the 427 lane (427 REPOINTED to 6b4c)
    b6 0x40 = |gp-0x6ada| >= |gp-0x6adc|         -- COMPARATOR: r24 vs r26
    b5 0x20 = |gp-0x6ae2| >= |gp-0x6b26|         -- COMPARATOR: friction vs inertia
    b4 0x10 = gp-0x6ada < 0                      -- sign of r24
    b3 0x08 = 0  (IDENTITY)                      -- 🛑 SEE THE HAZARD BELOW
    byte7[7:6] = 3

🛑🛑 IDENTITY HAZARD -- READ BEFORE TRUSTING THE GATE.
    V101 is `byte7[7:6]==3 AND b3==1`.  V102 is `byte7[7:6]==3 AND b3==0`.  **They share the byte7
    code**, so byte7 alone cannot separate them, and V102's half of the discriminator is the
    ABSENCE of a bit.  Every prior identity in this kit asserted a bit SET; a stuck-low bit, a
    dropped store or a mask that clears b3 would forge V102's identity while V101 is on the car.
    ⇒ This scorer therefore ALSO requires that at least one of b6/b5/b4 is non-constant (V101's b4
      and b7 are live too, so that is not decisive on its own) AND prints the byte4 field histogram
      so a human can see the cave is doing new work.  **If b3 is the only thing that changed, treat
      the identity as UNPROVEN and say so.**  A future build should go back to a SET bit.

🛑 427 IS NOT COMPARABLE ACROSS THIS PAIR.  V100/V101 pack `gp-0x6b94` (`sar 6`); V102 packs
   `gp-0x6b4c` (`sar 6`).  Same scale, DIFFERENT CELL.  The reconstructed lane is emitted as
   `x6b4c` and is scored WITHIN V102 only.  Any x6b4c-to-x6b94 ratio would be meaningless.

GUARDRAILS baked in: matched (speed x wheel-rate) cells with a printed per-cell census; 15 s block
bootstrap inside cells (episodes too, where they exist); `imu_vert` as the channel control; the
SHAPE FLOOR measured from the V89 placebo pair (r75 vs r76, byte-identical firmware); and a refusal
to report a direction for any ratio inside that floor.  Band statistics are Parseval-normalised FFT
band-RMS over a Hann window -- there is NO envelope anywhere in this file, so the
`_r2b_common.band_envelope` defect (one-sided `H=2*X` + `irfft` => rectified, not analytic) cannot
touch these numbers.


🛑 BETWEEN-BUILD NOISE FLOOR: 20-36x.  Six routes with IDENTICAL control cals
   (gain 3564, a2 22, knee 600, K1 204) span 2.60 to 51.81 = 19.9x; another six span 36.2x.
   => NO comparison of two BUILDS on this endpoint carries information below ~36x.
   This scorer is valid for WITHIN-DRIVE engaged-vs-manual contrast only.  Do NOT use it
   to rank builds against each other; the operator report is the only instrument with the
   resolution to do that.
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
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NFFT, HOP = 256, 128
NFFT_Q = 1024
VB = [(5, 20), (20, 35), (35, 50), (50, 65)]
RB = [(1, 8), (8, 20), (20, 45), (45, 120)]
CH = ("tq", "rate_c", "cs_ang", "imu_lat", "imu_vert")
RAIL, LIGHT = 4096.0, 400.0
COUNTS_PER_LSB = 12.8

# the two shape conventions, both scored so nothing is ambiguous
CONV = {"A  21.5-25.5 / 2.5-4.5": ((21.5, 25.5), (2.5, 4.5)),
        "B  22-26 / 32-38": ((22.0, 26.0), (32.0, 38.0))}
# the orchestrator's pre-registered reference values, printed but never used in a computation
PREREG = {"A  21.5-25.5 / 2.5-4.5": dict(v101_over_v100=5.07, v100=0.62),
          "B  22-26 / 32-38": dict(v101_over_v100=3.34, v100=1.00)}
PRED_LO, PRED_MID, PRED_HI = 0.57, 0.61, 0.66      # V102 / V101, 22-26 Hz shape
PRED_AUTH = (0.74, 0.78, 0.81)                     # V102 / V101, wheel rate under a hard command

MASK = dict(b7=0x80, b6=0x40, b5=0x20, b4=0x10, b3=0x08)
_fail = []


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


def gate(ok, msg):
    print("   %s %s" % ("[PASS]" if ok else "[FAIL]", msg))
    if not ok:
        _fail.append(msg)
    return ok


# =====================================================================================================
def add_shape(route, recs):
    """Attach both shape conventions for every channel, computed from each window's own samples."""
    win = np.hanning(NFFT)
    for r in recs:
        blk, sl = r["_blk"], r["_sl"]
        for ch in CH:
            if ch not in blk:
                continue
            x = blk[ch][sl]
            for name, ((lo, hi), (clo, chi)) in CONV.items():
                num = L.bandrms(x, L.FS, lo, hi, win)
                den = L.bandrms(x, L.FS, clo, chi, win)
                if den > 0:
                    r["sh:%s|%s" % (ch, name)] = num / den
    return recs


def cells(A, B, vbins=VB):
    out = []
    for vlo, vhi in vbins:
        for rlo, rhi in RB:
            a = L.sel(L.sel(A, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
            b = L.sel(L.sel(B, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
            if len(a) >= 5 and len(b) >= 5:
                out.append(((vlo, vhi), (rlo, rhi), a, b))
    return out


def ratio(pack, key, nboot=3000, seed=1):
    """B/A: min(n)-weighted mean of per-cell log ratios; 15 s blocks resampled inside each cell."""
    rng = np.random.default_rng(seed)
    P = []
    for _, _, a, b in pack:
        ga, gb = {}, {}
        for r in a:
            v = r.get(key, np.nan)
            if np.isfinite(v) and v > 0:
                ga.setdefault((r["arm"], r["seg"], int(r["t0"] // 15.0)), []).append(v)
        for r in b:
            v = r.get(key, np.nan)
            if np.isfinite(v) and v > 0:
                gb.setdefault((r["arm"], r["seg"], int(r["t0"] // 15.0)), []).append(v)
        if len(ga) >= 2 and len(gb) >= 2:
            P.append(([np.array(v) for v in ga.values()], [np.array(v) for v in gb.values()]))
    if not P:
        return None

    def stat(Q):
        num = den = 0.0
        for A_, B_ in Q:
            va, vb = np.concatenate(A_), np.concatenate(B_)
            w = min(len(va), len(vb))
            num += w * np.log(np.median(vb) / np.median(va))
            den += w
        return float(np.exp(num / den)) if den else np.nan
    pt = stat(P)
    out = [stat([([A_[j] for j in rng.integers(0, len(A_), len(A_))],
                  [B_[j] for j in rng.integers(0, len(B_), len(B_))]) for A_, B_ in P])
           for _ in range(nboot)]
    out = np.array([o for o in out if np.isfinite(o)])
    lo, hi = np.percentile(out, [2.5, 97.5])
    return dict(r=pt, lo=float(lo), hi=float(hi), cells=len(P))


def verdict(res, floor):
    if res is None:
        return "n/a"
    if 1.0 / floor <= res["r"] <= floor:
        return "INSIDE THE FLOOR -- NOT A RESULT"
    return "outside the floor"


# =====================================================================================================
def main(route, ident_b3=0, ident_code=3, label="V102"):
    print(__doc__.split("=====", 1)[0])
    print("SCORING ROUTE %s AS %s   (identity: byte7[7:6]==%d AND b3==%d)"
          % (route, label, ident_code, ident_b3))

    cdir = L._cache_dir(route)
    if not cdir.exists() or not L._segs(route):
        print("\n🛑 NO CACHE at %s.  Build it first with the `decode/extract_r95.py` pattern:" % cdir)
        print("   add a ROUTES row + call `extract_r7d.extract_route`, so the instrument is")
        print("   bit-identical to the one that produced every number this script compares against.")
        return 2
    L.ROUTES[route] = L._mk(route, label, gain=5346, clamp=2048, leverB=False,
                            idcode=ident_code, bits="v102")

    # ------------------------------------------------------------------ 1. IDENTITY + FAULT GATE
    hdr("1 -- IDENTITY AND FAULT GATE.  Nothing below may be reported if this fails.")
    z = np.load(cdir / ("r" + route + ".npz"), allow_pickle=True)
    probe = np.asarray(z["probe"], int) & 0xFF
    if "raw14_b7" in z and "row2raw14" in z:
        b7b = (np.asarray(z["raw14_b7"], int) & 0xFF)[np.asarray(z["row2raw14"], int)]
        assert np.all((np.asarray(z["raw14_b4"], int) & 0xFF)[np.asarray(z["row2raw14"], int)]
                      == probe), "raw14 pairing broken -- the off-by-one guard fired"
    else:
        b7b = np.full(len(probe), -1)
    code = (b7b & 0xC0) >> 6
    bits = {k: (probe & m) != 0 for k, m in MASK.items()}
    eng = np.asarray(z["cc_lat"], float)[:len(probe)] > 0.5

    d_code = float((code == ident_code).mean())
    d_b3 = float((bits["b3"] == bool(ident_b3)).mean())
    d_joint = float(((code == ident_code) & (bits["b3"] == bool(ident_b3))).mean())
    gate(d_code > 0.999, "byte7[7:6] == %d  duty %.6f  (hist %s)"
         % (ident_code, d_code, dict(zip(*[list(x) for x in np.unique(code, return_counts=True)]))))
    gate(d_b3 > 0.999, "b3 == %d  duty %.6f" % (ident_b3, d_b3))
    gate(d_joint > 0.999, "JOINT identity duty %.6f over %d frames" % (d_joint, len(probe)))
    fld = probe & 0xF8
    hist = dict(zip(*[list(x) for x in np.unique(fld, return_counts=True)]))
    print("   byte4[7:3] histogram: %s" % hist)
    live = sum(1 for k in ("b6", "b5", "b4") if 0.001 < bits[k].mean() < 0.999)
    gate(live >= 1, "at least one of b6/b5/b4 is NON-CONSTANT (%d of 3) -- the cave is doing new work"
         % live)
    if ident_b3 == 0:
        print("   🛑 V102's identity rests on the ABSENCE of b3.  If b6/b5/b4 look like V101's")
        print("      (b6 constant 0, b5 ~0.45, b4 ~0.50), treat the identity as UNPROVEN.")

    for k, nm in (("sentinels", "sentinels"), ("dtc_active", "DTC active")):
        if k in z:
            v = np.asarray(z[k], float)
            gate(float(np.nansum(v)) == 0, "%s == 0 (sum %.0f)" % (nm, float(np.nansum(v))))
    if "sstat" in z:
        u = np.unique(np.asarray(z["sstat"], int))
        gate(not set(u.tolist()) & {4, 7}, "STEER_STATUS never 4/7 (values %s)" % u.tolist())
    for k, nm, want in (("ab_config_valid", "CONFIG_VALID", 1.0), ("ab_output_disabled",
                                                                   "OUTPUT_DISABLED", 0.0)):
        if k in z:
            d = float(np.asarray(z[k], float).mean())
            gate(abs(d - want) < 0.01, "%s duty %.5f (want %.0f)" % (nm, d, want))
    print("\n   engaged %.1f s of %.1f s" % (eng.sum() / L.FS, len(eng) / L.FS))
    if _fail:
        print("\n🛑🛑 GATE FAILED -- %d check(s). NOTHING BELOW MAY BE REPORTED." % len(_fail))
        for f in _fail:
            print("     - " + f)
        return 1

    # ------------------------------------------------------------------ 2. THE FLOOR
    hdr("2 -- THE PLACEBO SHAPE FLOOR, recomputed now: r75 vs r76, BOTH V89, identical firmware")
    P75 = add_shape("75", L.windows("75", NFFT, HOP, engaged=True, keep_raw=True))
    P76 = add_shape("76", L.windows("76", NFFT, HOP, engaged=True, keep_raw=True))
    for x in P75:
        x["arm"] = "75"
    for x in P76:
        x["arm"] = "76"
    pl = cells(P75, P76)
    FLOOR = {}
    for name in CONV:
        vals = []
        for ch in ("tq", "rate_c", "cs_ang"):
            r = ratio(pl, "sh:%s|%s" % (ch, name), nboot=1500, seed=7)
            if r:
                vals.append(max(r["hi"], 1.0 / max(r["lo"], 1e-9)))
                print("   %-24s %-8s %.2fx [%.2f, %.2f]" % (name, ch, r["r"], r["lo"], r["hi"]))
        FLOOR[name] = max(vals) if vals else 1.5
    print("\n   FLOOR: " + "   ".join("%s = %.2fx" % (k, v) for k, v in FLOOR.items()))
    print("   Any ratio inside its floor is NOT A RESULT and no direction may be reported for it.")

    # ------------------------------------------------------------------ 3. PRIMARY
    hdr("3 -- 🛑 PRIMARY: the 22-26 Hz shape ratio, V102 vs V101 and vs V100")
    W = {}
    for r in dict.fromkeys((route, "95", "85")):
        W[r] = add_shape(r, L.windows(r, NFFT, HOP, engaged=True, keep_raw=True))
        for x in W[r]:
            x["arm"] = r
    for name in CONV:
        print("\n   convention %s   (pre-registered reference: V101/V100 = %.2f)"
              % (name, PREREG[name]["v101_over_v100"]))
        for base, blab in (("95", "V101 8x"), ("85", "V100 4x")):
            pack = cells(W[base], W[route])
            if not pack:
                print("      vs %-8s NO MATCHED CELLS" % blab)
                continue
            print("      vs %s   cells=%d   census:" % (blab, len(pack)))
            for (vlo, vhi), (rlo, rhi), a, b in pack:
                print("         %-11s %-11s  %s n=%-4d  %s n=%-4d"
                      % ("%d-%d km/h" % (vlo, vhi), "%d-%d deg/s" % (rlo, rhi),
                         blab.split()[0], len(a), label, len(b)))
            for ch in CH:
                r = ratio(pack, "sh:%s|%s" % (ch, name), seed=abs(hash((ch, name, base))) % 9999)
                if r is None:
                    continue
                tag = "  <- CHANNEL CONTROL, should not move" if ch == "imu_vert" else ""
                print("         %-9s %6.2fx [%5.2f, %5.2f]   %s%s"
                      % (ch, r["r"], r["lo"], r["hi"], verdict(r, FLOOR[name]), tag))
                if ch == "tq" and base == "95":
                    ok = r["r"] <= 0.70
                    amb = 1.0 / FLOOR[name] <= r["r"] <= FLOOR[name]
                    print("            >>> PRE-REGISTERED PREDICTION %.2fx [%.2f-%.2f]"
                          % (PRED_MID, PRED_LO, PRED_HI))
                    if amb:
                        print("            >>> VERDICT: INSIDE THE FLOOR -- UNINTERPRETABLE, "
                              "report no direction.")
                    elif ok:
                        print("            >>> VERDICT: DOSE-RESPONSE HOLDS. 6x is on the curve.")
                    elif r["r"] > 0.85:
                        print("            >>> 🛑 VERDICT: THE GAIN IS NOT THE CARRIER. The "
                              "session's attribution is REFUTED. Say so plainly.")
                    else:
                        print("            >>> VERDICT: partial -- between the prediction and null.")

    # ------------------------------------------------------------------ 4. PROTECTED METRIC
    hdr("4 -- 🛑 PROTECTED: wheel-angle rate under a hard LKAS command  (predicted %.2fx of V101)"
        % PRED_AUTH[1])
    RAW = {}
    for r in dict.fromkeys((route, "95", "85")):
        acc = {}
        for s in L.ROUTES[r]["segs"]:
            d = L.load_seg(r, s)
            for k in ("t", "cc_lat", "v_rear", "rate_c", "cs_tq", "e4tq"):
                acc.setdefault(k, []).append(d[k])
            acc.setdefault("seg", []).append(np.full(len(d["t"]), s, float))
        d = {k: np.concatenate(v) for k, v in acc.items()}
        d["eng"] = d["cc_lat"] > 0.5
        d["v"] = d["v_rear"] * 3.6
        d["ar"] = np.abs(d["rate_c"])
        d["unit"] = d["seg"] * 1e6 + np.floor(d["t"] / 15.0)
        RAW[r] = d
    print("   (a) FRAME-LEVEL, engaged AND |e4tq| at the 4096 rail AND hands-light, 5-30 km/h")
    sel = {}
    for r in dict.fromkeys((route, "95", "85")):
        d = RAW[r]
        m = (d["eng"] & (d["v"] >= 5) & (d["v"] < 30) & (np.abs(d["e4tq"]) >= RAIL)
             & (np.abs(d["cs_tq"]) < LIGHT))
        sel[r] = m
        if m.sum() < 25:
            print("      r%-4s n=%4d  🛑 TOO THIN -- do not quote" % (r, m.sum()))
            continue
        print("      r%-4s n=%5d (%5.1f s)  |wheel rate| p50=%6.1f p90=%6.1f p99=%6.1f deg/s"
              % (r, m.sum(), m.sum() / L.FS, *np.percentile(d["ar"][m], [50, 90, 99])))
    for base in ("95", "85"):
        if sel[route].sum() >= 25 and sel[base].sum() >= 25:
            for q in (50, 90):
                a, b = RAW[base]["ar"][sel[base]], RAW[route]["ar"][sel[route]]
                print("      %s/V%s p%-2d = %.2fx" % (label, base, q,
                                                      np.percentile(b, q) / np.percentile(a, q)))
    print("\n   (b) EVENT-LEVEL: command ramps |e4tq| 500 -> 3000 within 1.0 s.")
    print("       🛑 openpilot NEVER steps its command; edges must be CROSSINGS, not one-sample jumps.")
    for r in dict.fromkeys((route, "95", "85")):
        d = RAW[r]
        e = np.abs(d["e4tq"])
        last_lo, ramp, wr, pk = None, [], [], []
        for i in range(1, len(e)):
            if d["seg"][i] != d["seg"][i - 1]:
                last_lo = None
                continue
            if e[i] < 500:
                last_lo = i
            if e[i] >= 3000 and e[i - 1] < 3000 and d["eng"][i] and last_lo is not None \
                    and 0 < i - last_lo <= 100:
                j = min(i + 50, len(e))
                if d["seg"][j - 1] == d["seg"][i] and j - i >= 40:
                    ramp.append((i - last_lo) / L.FS * 1000.0)
                    wr.append(float(np.percentile(d["ar"][i:j], 90)))
                    pk.append(float(d["ar"][i:j].max()))
                last_lo = None
        if len(ramp) < 5:
            print("      r%-4s %d events -- TOO FEW, do not quote" % (r, len(ramp)))
            continue
        print("      r%-4s %3d events  cmd ramp p50=%4.0f ms (CONTROL)  wheel p90 p50=%6.1f  "
              "peak p50=%6.1f deg/s" % (r, len(ramp), np.median(ramp), np.median(wr), np.median(pk)))

    # ------------------------------------------------------------------ 5. SECONDARY
    hdr("5 -- SECONDARY: peak frequency, the two comparators, and the 427 lane")
    win = np.hanning(NFFT_Q)
    print("   peak in 20-28 Hz (V100 measured 20.2-20.3 Hz; V101 23.05 Hz -- does 6x walk it back?)")
    for r in dict.fromkeys((route, "95", "85")):
        P, n = [], 0
        for b in L.all_blocks(r):
            m = (b["cc_lat"] > 0.5) & (b["v_rear"] * 3.6 >= 5) & (b["v_rear"] * 3.6 < 65)
            i = 0
            while i + NFFT_Q <= len(m):
                if m[i:i + NFFT_Q].mean() >= 0.98:
                    P.append(L.psd(b["tq"][i:i + NFFT_Q], L.FS, win)[1])
                    n += 1
                i += NFFT_Q // 2
        if n < 3:
            print("      r%-4s only %d windows -- peak NOT QUOTED" % (r, n))
            continue
        f = L.psd(np.zeros(NFFT_Q), L.FS, win)[0]
        pm = np.median(np.asarray(P), axis=0)
        bnd = (f >= 19) & (f <= 27)
        k = int(np.argmax(pm[bnd]))
        base = np.median(pm[(f >= 15) & (f <= 32)])
        print("      r%-4s %2d win   f0 = %5.2f Hz   prominence %5.2f" % (r, n, f[bnd][k],
                                                                          pm[bnd][k] / base))
    print("""
   🛑 Q IS NOT AN ENDPOINT AND MUST NOT CARRY A CONCLUSION.  The two independent measurements of
      this session DISAGREE IN SIGN:  this analyst measured Q FALLING 4x->8x (tq 34.5 -> 23.6,
      peak taller AND broader); `rlog-v101` measured Q RISING 31.4 -> 47.4 (taller and narrower).
      Both sit at a resolution where 3 bins decide it and the half-height point moves when the
      broadband floor moves (it moves ~2x).  Report the frequency shift, not the width.""")
    print("\n   comparators, engaged:")
    for k, desc in (("b6", "|gp-0x6ada| >= |gp-0x6adc|   r24 vs r26"),
                    ("b5", "|gp-0x6ae2| >= |gp-0x6b26|   friction vs inertia"),
                    ("b4", "gp-0x6ada < 0                 sign of r24"),
                    ("b7", "gp-0x6b4c < 0                 sign of the 427 lane")):
        d = float(bits[k][eng].mean())
        note = "  🛑 CONSTANT -- a comparator at duty 0 or 1 decided nothing" \
            if (d < 0.001 or d > 0.999) and k in ("b6", "b5") else ""
        print("      d(%s) = %.6f   %s%s" % (k, d, desc, note))
    if "mag427" in z:
        mag = np.asarray(z["mag427"], float)[:len(probe)]
        sgn = np.where(bits["b7"], -1.0, 1.0)
        x = np.abs(sgn * mag * COUNTS_PER_LSB)
        print("\n   427 lane = gp-0x6b4c (REPOINTED; NOT comparable to V100/V101's gp-0x6b94):")
        print("      |gp-0x6b4c| engaged  p50=%.0f p90=%.0f p99=%.0f max=%.0f counts"
              % tuple(np.percentile(x[eng], [50, 90, 99, 100])))
        print("      wire ceiling checks: >=800 (structural) %d frames, >=1023 (field) %d frames"
              % (int((mag[eng] >= 800).sum()), int((mag[eng] >= 1023).sum())))
        print("      🛑 gp-0x6b4c's own clamp is +-10240 => max reachable wire code 800, NOT 1023.")

    hdr("DONE.  Report the PRIMARY verdict first, in the operator's words, and say plainly which")
    print("numbers are inside the floor.  A ratio inside the floor is not a small effect -- it is")
    print("no measurement at all.")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--selftest" in sys.argv:
        print("SELFTEST: running the pipeline on r95 under V101's identity rule "
              "(byte7==3 AND b3==1).\n")
        sys.exit(main("95", ident_b3=1, ident_code=3, label="V101"))
    if not args:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0]))
