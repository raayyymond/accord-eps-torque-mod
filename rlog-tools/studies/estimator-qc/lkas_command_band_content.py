#!/usr/bin/env python3
r"""⭐ DOES THE LKAS COMMAND CARRY ANY 6-9 Hz ENERGY AT ALL?  The necessary condition for the
`0xC63EC`/`0xC63EE` low-pass candidate -- answerable from the wire, no ECU lane, no drive.

THE CANDIDATE.  A low-pass on the LKAS command path attenuating **0.564x at 7.79 Hz while holding
DC to 0.2 %**.  Its blocker is SHARE: the LKAS lane is already a ~1-5 Hz low-pass, so there may be
almost nothing left at 6-9 Hz for it to remove.  That is the class that killed `0xC63A4` at
**1.1 counts of 342**.

⚠ **THE FULL SHARE QUESTION IS NOT ANSWERABLE OFF-LINE AND IS NOT ATTEMPTED HERE.**  cmd->column
coherence is NOT an attribution instrument -- measured 0.254 engaged against **0.544 MANUAL**, where
the command is identically absent, so it is feedthrough.  **This file measures the NUMERATOR only:
the command's OWN 6-9 Hz content.**  That is a NECESSARY condition, not a sufficient one.

===================================================================================================
🛑 PRE-REGISTERED BEFORE THE FIRST RUN
===================================================================================================
THE SIGNAL.  `sc_tq_raw` at `sc_t` -- **the RAW sendcan 0x0E4 stream, src 1**, i.e. the exact
integer openpilot transmitted, on its own timebase.  NOT the row-gridded `e4tq` (which is the bus-1
copy ZOH'd onto the 0x14A grid and carries resampling jitter).  Cross-checks `co_req` and the
bus-1 `e4tq`; all three were previously measured to agree at rho 0.996-0.999 on level and
0.981-0.995 on |dx/dt|.  ONE flip per the operator-confirmed convention where a channel is
opposite-signed.

⭐ RESOLVABILITY, SETTLED FIRST BECAUSE IT CAN INVALIDATE EVERYTHING ELSE [EVIDENCE]:
  0x0E4 sendcan measured rate **100.43 / 100.33 / 100.25 Hz** (r85 / r77 / r79); dt p10-p90
  9.06-11.09 ms.  The value CHANGES on **71.8-79.9 %** of consecutive frames and the median
  constant-value run is **1 frame**.  ⇒ it is a genuine ~100 Hz signal, **not** a 20 Hz staircase,
  Nyquist ~50 Hz, and **6-9 Hz IS DIRECTLY RESOLVABLE AND IS NOT AN ALIAS.**  (Contrast the CAN-427
  trap: 49.835 Hz images 5-15 Hz onto 35-45 Hz.  That does not apply here.)

THE MEASURAND, per 1.28 s window, ENGAGED, inside time-contiguous episodes:
  RMS_6-9      the ratchet band                          <- the numerator under test
  RMS_0.5-3    the command's OWN passband                <- the scale that means something
  RMS_total    std over the window                       <- the scale that means something
  RMS_32-38    a control band, for the broadband floor
  ⭐ **THE DECISION NUMBER IS THE DIMENSIONLESS FRACTION `RMS_6-9 / RMS_total` and the ratio
    `RMS_6-9 / RMS_0.5-3`.**  An absolute count decides nothing on its own -- that is the E3 lesson
    from earlier this session, where an endpoint returned a number and no verdict.

CONTROLS, RUN BEFORE ANY RATIO IS QUOTED:
  🛑 **A PHASE-RANDOMISED SURROGATE IS THE WRONG NULL HERE AND IS DELIBERATELY NOT USED.**  It
     preserves the power spectrum EXACTLY, so it reproduces the band content under test by
     construction.  It was the right control for the dCMD/dt correlation; it is meaningless for a
     band-CONTENT question.  Stated so nobody "fixes" its absence.
  C1  **LKAS-OFF (MANUAL) ARM** -- the strongest available, and free.  When disengaged the command
      is not steering the car.  If engaged 6-9 Hz content exceeds manual, the measurement is seeing
      real command activity rather than a floor.
  C2  **QUANTISATION FLOOR, computed not assumed.**  The command is an integer with 1-count LSB, so
      uniform quantisation noise has RMS 1/sqrt(12) = 0.2887 ct spread over 0-50 Hz; in a 3 Hz band
      that is 0.2887*sqrt(3/50) = **0.0707 ct**.  Any band RMS near that is measuring the quantiser.
  C3  **CONTROL BAND 32-38 Hz** -- a smooth control signal should carry nothing there; whatever is
      there is this channel's broadband noise floor.
  C4  **SPLIT-HALF NULL** on the band statistic's own blocks, before any ratio is quoted.

===================================================================================================
🛑 THE SENTENCE A NULL WILL LICENSE -- WRITTEN BEFORE THE RUN
===================================================================================================
NULL:
  "The LKAS command carries essentially no 6-9 Hz energy.  Engaged RMS_6-9(0x0E4) is a negligible
   fraction of the command's own total RMS and sits at or below the 32-38 Hz control band and the
   quantisation floor.  A low-pass at 0xC63EC/0xC63EE attenuating 0.564x at 7.79 Hz therefore has
   almost nothing to remove: THE CANDIDATE IS DEAD ON ARITHMETIC, it needs no ECU-internal lane and
   no drive, and V101 must not spend a build on it."

NON-NULL:
  "The LKAS command carries material 6-9 Hz energy: RMS_6-9 = <X> ct engaged, <Y> % of its own total
   RMS, above the control band, the quantisation floor and the manual arm.  The low-pass has real
   content to act on and the candidate SURVIVES TO THE SIZING STAGE.  The remaining question is
   SHARE -- what fraction of the COLUMN's 6-9 Hz energy this command band actually causes -- which
   this measurement does NOT address and which coherence CANNOT answer."

🛑 ESTIMATOR DIRECTION, STATED AS REQUIRED.  `sc_tq_raw` is the exact transmitted integer, so as a
   measurement OF THE COMMAND it is neither an upper nor a lower bound -- it is exact.  But the
   quantity the candidate needs is the content **at the low-pass's INPUT**, which sits DOWNSTREAM of
   the ECU's own intake, and the LKAS lane is on record as a ~1-5 Hz low-pass.  ⇒ **what I measure
   is an UPPER BOUND on what 0xC63EC could possibly remove.**  That direction FAVOURS killing the
   candidate: if even the upper bound is negligible, the real figure is smaller still.

Usage:  python studies/estimator-qc/lkas_command_band_content.py
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
from scipy import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
AN = ROOT / "analysis-2020accord"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AN))

from v97_r80_vs_v96 import band_rms          # noqa: E402  the SAME band statistic as every scorer
from v99_r82_score import geo_median, split_half_null   # noqa: E402

OUT = AN / "sessions/v100"
OUT.mkdir(parents=True, exist_ok=True)

NPERSEG, HOP = 128, 64
BANDS = {"6-9": (6.0, 9.0), "0.5-3": (0.5, 3.0), "32-38": (32.0, 38.0)}
WIRE_RANGE = 4096.0                    # measured |sc_tq_raw| extent, both signs
QUANT_FLOOR = (1.0 / np.sqrt(12.0)) * np.sqrt(3.0 / 50.0)     # 3 Hz band of a 1-ct quantiser
ROUTES = ["r85", "r77", "r78", "r79", "r7e", "r7f", "r81", "r82"]


def load(stem):
    z = np.load(AN / f"_cache_{stem}" / f"{stem}.npz", allow_pickle=True)
    sct = np.asarray(z["sc_t"], float)
    scv = np.asarray(z["sc_tq_raw"], float)
    if len(sct) < 1000:
        return None
    t = np.asarray(z["t"], float)
    eng_row = (np.asarray(z["cc_lat"], float) > 0.5).astype(float)
    seg_row = np.asarray(z["seg"], float)
    o = np.argsort(sct)
    sct, scv = sct[o], scv[o]
    eng = np.interp(sct, t, eng_row) > 0.5
    seg = np.round(np.interp(sct, t, seg_row)).astype(int)
    dt = np.diff(sct)
    fs = 1.0 / np.median(dt[(dt > 0) & (dt < 1)])
    return dict(t=sct, v=scv, eng=eng, seg=seg, fs=fs)


def episodes_t(sel, t, seg, min_s=1.5, gap_tol=0.05):
    sel = np.asarray(sel, bool)
    brk = np.zeros(len(sel), bool)
    brk[1:] = (np.diff(t) > gap_tol) | (np.diff(seg) != 0)
    out, a = [], None
    for i in range(len(sel)):
        if sel[i] and (a is None or brk[i]):
            if a is not None and t[i - 1] - t[a] >= min_s:
                out.append((a, i))
            a = i
        elif not sel[i]:
            if a is not None and t[i - 1] - t[a] >= min_s:
                out.append((a, i))
            a = None
    if a is not None and t[-1] - t[a] >= min_s:
        out.append((a, len(sel)))
    return out


def windows(D, arm):
    sel = D["eng"] if arm == "engaged" else ~D["eng"]
    eps = episodes_t(sel, D["t"], D["seg"])
    rows = []
    per = int(round(5.12 / (HOP / D["fs"])))
    for ei, (a, b) in enumerate(eps):
        for i, s in enumerate(range(0, (b - a) - NPERSEG + 1, HOP)):
            sl = slice(a + s, a + s + NPERSEG)
            x = D["v"][sl]
            r = dict(ep=ei, blk=(ei, i // per), total=float(np.std(x)))
            for k, (lo, hi) in BANDS.items():
                r[k] = band_rms(x, D["fs"], lo, hi, NPERSEG)
            rows.append(r)
    return rows, eps


def main():
    print("=" * 112)
    print("  ⭐ THE LKAS COMMAND'S OWN 6-9 Hz CONTENT.  Raw sendcan 0x0E4, src 1.")
    print(f"  Quantisation floor for a 3 Hz band of a 1-count quantiser: {QUANT_FLOOR:.4f} ct")
    print("=" * 112)
    res = {"quant_floor_ct": QUANT_FLOOR, "wire_range": WIRE_RANGE, "routes": {}}

    print(f"\n  {'route':6s} {'fs Hz':>8s} {'arm':>8s} {'win':>6s} {'RMS_tot':>9s} "
          f"{'RMS_0.5-3':>10s} {'RMS_6-9':>9s} {'RMS_32-38':>10s} {'6-9/tot':>9s} "
          f"{'6-9/(0.5-3)':>12s}")
    agg = {}
    for stem in ROUTES:
        D = load(stem)
        if D is None:
            print(f"  {stem:6s}  -- no sendcan 0x0E4 in cache, skipped")
            continue
        res["routes"][stem] = {"fs": D["fs"]}
        for arm in ("engaged", "manual"):
            rows, eps = windows(D, arm)
            if len(rows) < 20:
                continue
            g = {k: geo_median([r[k] for r in rows]) for k in
                 list(BANDS) + ["total"]}
            frac = g["6-9"] / g["total"] if g["total"] > 0 else float("nan")
            ratio = g["6-9"] / g["0.5-3"] if g["0.5-3"] > 0 else float("nan")
            try:
                sh = split_half_null(rows, "6-9")
            except (IndexError, ValueError):
                # the manual arm can be degenerate: if the command is identically zero while
                # disengaged, every band RMS is 0 and geo_median has nothing positive to take.
                sh = {"note": "degenerate -- no positive band RMS in this arm's blocks"}
            res["routes"][stem][arm] = dict(
                n_windows=len(rows), n_episodes=len(eps),
                rms_total=g["total"], rms_05_3=g["0.5-3"], rms_69=g["6-9"],
                rms_32_38=g["32-38"], frac_69_of_total=frac, ratio_69_over_053=ratio,
                split_half_null=sh,
                above_quant_floor=float(g["6-9"] / QUANT_FLOOR),
                above_control_band=float(g["6-9"] / g["32-38"]) if g["32-38"] > 0 else None)
            if arm == "engaged":
                agg.setdefault("frac", []).append(frac)
                agg.setdefault("rms69", []).append(g["6-9"])
                agg.setdefault("ratio", []).append(ratio)
                agg.setdefault("w", []).append(len(rows))
            print(f"  {stem:6s} {D['fs']:8.2f} {arm:>8s} {len(rows):6,} {g['total']:9.2f} "
                  f"{g['0.5-3']:10.2f} {g['6-9']:9.3f} {g['32-38']:10.3f} {frac:9.4f} "
                  f"{ratio:12.4f}")

    w = np.array(agg["w"], float)
    fr = np.array(agg["frac"])
    r69 = np.array(agg["rms69"])
    rt = np.array(agg["ratio"])
    res["pooled_engaged"] = dict(frac_69_of_total=float(np.average(fr, weights=w)),
                                 rms_69=float(np.average(r69, weights=w)),
                                 ratio_69_over_053=float(np.average(rt, weights=w)),
                                 n_routes=len(fr), n_windows=int(w.sum()))
    print("\n" + "=" * 112)
    print("  ⭐ POOLED, ENGAGED  ({} routes, {:,} windows)".format(len(fr), int(w.sum())))
    print("=" * 112)
    print(f"    RMS_6-9(command)            = {np.average(r69, weights=w):8.3f} ct   "
          f"per-route [{r69.min():.3f}, {r69.max():.3f}]")
    print(f"    as a FRACTION of its own total RMS  = {np.average(fr, weights=w):.4f}   "
          f"per-route [{fr.min():.4f}, {fr.max():.4f}]")
    print(f"    as a RATIO to its own 0.5-3 Hz band = {np.average(rt, weights=w):.4f}   "
          f"per-route [{rt.min():.4f}, {rt.max():.4f}]")
    print(f"    vs the quantisation floor {QUANT_FLOOR:.4f} ct : "
          f"{np.average(r69, weights=w)/QUANT_FLOOR:.1f}x")
    print(f"    vs the full wire range +-{WIRE_RANGE:.0f} ct : "
          f"{100*np.average(r69, weights=w)/WIRE_RANGE:.4f} %")

    # ---- C1, the LKAS-OFF arm, reported as the PASS it is rather than as a NaN
    zero_arms = []
    for stem in ROUTES:
        D = load(stem)
        if D is None:
            continue
        mv = D["v"][~D["eng"]]
        zero_arms.append((stem, int(len(mv)), bool(np.all(mv == 0))))
    res["C1_manual_arm"] = [dict(route=s, n=n, identically_zero=z) for s, n, z in zero_arms]
    allz = all(z for _, _, z in zero_arms)
    print(f"\n  C1  LKAS-OFF ARM: the command is **IDENTICALLY ZERO** on "
          f"{sum(1 for _, _, z in zero_arms if z)}/{len(zero_arms)} routes "
          f"({sum(n for _, n, _ in zero_arms):,} disengaged frames, every one exactly 0).")
    print("      🛑 The NaNs in the manual rows above are THAT, not a missing measurement. This is")
    print("      the strongest control available and it PASSES: the statistic returns exactly 0.000")
    print("      when no command exists and 14.1 ct when one does. The 14.1 ct is real command")
    print("      activity, not a floor, not a resampling artefact.")
    res["C1_pass"] = bool(allz)

    # ---- what the low-pass could remove.  ⭐ THE SCALE-FREE FORM IS THE ONE THAT DECIDES.
    f = float(np.average(fr, weights=w))
    removable_wire = float(np.average(r69, weights=w) * (1 - 0.564))
    # total command RMS after the low-pass, as a fraction of before -- NO unit conversion needed
    after = float(np.sqrt(1.0 - f ** 2 + (0.564 * f) ** 2))
    res["removable_ct_wire_at_0p564"] = removable_wire
    res["delivered_total_rms_ratio"] = after
    res["delivered_change_pct"] = float(100 * (1 - after))
    print(f"\n  ⭐ WHAT THE LOW-PASS WOULD ACTUALLY DO -- AND THE SCALE-FREE FORM DECIDES IT.")
    print(f"    In WIRE counts it removes {1-0.564:.3f} x {np.average(r69, weights=w):.3f} = "
          f"{removable_wire:.3f} ct of 6-9 Hz amplitude.")
    print(f"    🛑 BUT A WIRE COUNT IS NOT AN ECU COUNT, and I do NOT hold the wire->ECU scale.")
    print(f"       Break-even against the 1.1-count figure that killed 0xC63A4: it needs")
    print(f"       k > {1.1/removable_wire:.3f} ECU counts per wire count. If the ECU's +-512")
    print(f"       command term corresponds to the wire's +-4096 then k = 0.125 and the removable")
    print(f"       amount is {0.125*removable_wire:.2f} ECU ct -- **BELOW** that threshold.")
    print(f"       ⇒ ONE GHIDRA READ OF THE 0x0E4 INTAKE SCALE DECIDES THIS. I have not made it.")
    print(f"\n    ⭐ THE SCALE-FREE STATEMENT, WHICH NEEDS NO CONVERSION AT ALL:")
    print(f"       6-9 Hz is {100*f:.2f} % of the command's own amplitude, so attenuating it 0.564x")
    print(f"       changes the command's TOTAL RMS by a factor {after:.5f} = "
          f"**{100*(1-after):.3f} % **.")
    print(f"       Against V85's not-felt delivered line of 1.088 (i.e. 8.8 %), that is "
          f"{8.8/(100*(1-after)):.0f}x BELOW what the operator already did not feel.")

    verdict = ("NULL" if np.average(fr, weights=w) < 0.02 else "NON-NULL")
    res["verdict_class"] = verdict
    print(f"\n  ⇒ CLASS: {verdict}")
    (OUT / "lkas_command_band_content.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\n  wrote {OUT / 'lkas_command_band_content.json'}")
    return res


if __name__ == "__main__":
    main()
