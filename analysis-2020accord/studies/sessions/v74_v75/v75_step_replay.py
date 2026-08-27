#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75_step_replay.py -- route-5d exposure + step replay for the V74 -> V75 damper delta.

Answers, in order:
  A. PIPELINE VALIDITY   -- replayed (gp-0x6bd0 != 0) vs the ON-CAR probe bit `damp_nz`.
  B. RELAY-PLATEAU OCCUPANCY -- frames/seconds at gp-0x6ac0 >= 400 (V74 entry) vs >= 200 (V75).
  C. DWELL + SIGN-FLIP STRUCTURE inside the plateau.
  D. THE 4000-COUNT / 849 deg/s CORNER -- max, p99.9, p99.99 of gp-0x6ac0, and the bandwidth caveat.
  E. PER-TICK STEP |d gp-0x6bd0| -- kept as a cheap confirmation of the independent refutation.
  F. LAUNCH EVENTS -- n, and the resulting power.

Everything integer-exact via v75_fault_exact_model (instruction-annotated mirror of FUN_00034350).
Run:  ACCORD_FIRMWARE_ROOT=... python studies/sessions/v74_v75/v75_step_replay.py
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

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))

import v75_step_lib as L  # noqa: E402

OUT = HERE / "_scratch/out/_v75_step_results.json"
RNG = np.random.default_rng(20260806)

ENTRY_V74, ENTRY_V75 = 400, 200        # FactorE X[1] -- the relay-plateau entry, in gp-0x6ac0 counts
CORNER = 4000                          # FactorE X[3]
CREEP_MS = 4.0
FLAT_C_CTS = 2240                      # FactorC X[0] == 35 km/h == 9.7222 m/s


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


def main():
    R = {}
    D = L.load_route()
    n = len(D["t"])
    dt = np.diff(D["t"], prepend=D["t"][0] - 0.01)
    dt = np.clip(dt, 0.0, 0.05)
    W = 1.0 / 100.0009                                  # fs_lattice, per the extractor's summary

    # ---------------- channels ---------------------------------------------------------------------
    # gp-0x6ac0 = |gp-0x6a56| * 2048/3477, gp-0x6a56 = 10 * rate_f  (0x18F, the FINE field)
    a6a56 = np.rint(D["rate_f"] * 10.0)                 # exact: rate_f is that halfword x 0.1
    r_signed = np.trunc(a6a56 * 2048.0 / 3477.0).astype(np.int64)     # gp-0x6abe, +-1 count
    r_cts = np.abs(r_signed)                                          # gp-0x6ac0
    r_cts_coarse = np.rint(np.abs(D["rate_c"]) * L.CTS_PER_DEGS).astype(np.int64)
    sp_cts = np.rint(D["cs_v"] * L.MS_TO_CTS).astype(np.int64)
    lat = D["cc_lat"] > 0.5
    in26, in24, amb = L.mode_masks(D["cc_lat"], D["t"])
    mode = np.where(in26, L.MODE_ENGAGED, L.MODE_MANUAL).astype(np.int64)

    hdr("0.  ROUTE, CHANNELS, AND THE RATE RECONSTRUCTION")
    print(f"  frames {n}   span {D['t'][-1]:.2f} s   dt median {np.median(np.diff(D['t'])):.5f} s")
    print(f"  latActive {lat.mean()*100:.2f}%   mode26 in force {in26.mean()*100:.2f}%   "
          f"mode24 byte-stock {in24.mean()*100:.2f}%   ambiguous(dropped from arms) {amb.mean()*100:.2f}%")
    print(f"  gp-0x6ac0 via 0x18F FINE field  : max {r_cts.max()}  counts")
    print(f"  gp-0x6ac0 via 0x14A COARSE field: max {r_cts_coarse.max()} counts  "
          f"(cross-check, 8x coarser LSB)")
    agree = np.mean(np.abs(r_cts - r_cts_coarse) <= 6)
    print(f"  two-method agreement within +-6 counts: {agree*100:.3f}% of frames")
    R["channels"] = dict(n=n, span_s=float(D["t"][-1]), lat_pct=float(lat.mean() * 100),
                         mode26_pct=float(in26.mean() * 100), mode24_pct=float(in24.mean() * 100),
                         amb_pct=float(amb.mean() * 100),
                         r_max_fine=int(r_cts.max()), r_max_coarse=int(r_cts_coarse.max()),
                         two_method_agree_pct=float(agree * 100))

    # ---------------- A. pipeline validity against the on-car probe bit ------------------------------
    hdr("A.  PIPELINE VALIDITY -- replayed (gp-0x6bd0 != 0) vs the ON-CAR probe bit `damp_nz`")
    rp74 = L.Replay("v74")
    rp75 = L.Replay("v75")
    o74 = rp74.run(sp_cts, r_signed, mode)
    o75 = rp75.run(sp_cts, r_signed, mode)
    obs = D["damp_nz"] > 0.5
    pred = o74 != 0
    ok = np.isfinite(D["damp_nz"])
    acc = float((pred[ok] == obs[ok]).mean())
    print(f"  route-wide agreement           : {acc*100:.3f}%   "
          f"(observed duty {obs[ok].mean()*100:.3f}%, predicted {pred[ok].mean()*100:.3f}%)")
    for nm, m in (("engaged (mode 26 in force)", in26), ("manual  (mode 24 byte-stock)", in24)):
        mm = m & ok
        print(f"  {nm:30s} : agree {(pred[mm]==obs[mm]).mean()*100:7.3f}%   "
              f"observed duty {obs[mm].mean()*100:7.3f}%   predicted {pred[mm].mean()*100:7.3f}%")
    mc = in24 & (D["cs_v"] <= 2.0) & ok
    print(f"  manual creep (<=2 m/s)         : observed {obs[mc].mean()*100:.4f}%  "
          f"predicted {pred[mc].mean()*100:.4f}%   <- stock mode-24 FactorC Y[0]=0 forces a HARD ZERO")
    R["validity"] = dict(route_agree_pct=acc * 100,
                         obs_duty_pct=float(obs[ok].mean() * 100),
                         pred_duty_pct=float(pred[ok].mean() * 100),
                         eng_agree_pct=float((pred[in26 & ok] == obs[in26 & ok]).mean() * 100),
                         man_agree_pct=float((pred[in24 & ok] == obs[in24 & ok]).mean() * 100))

    print(f"\n  replayed |gp-0x6bd0| max, mode-gated : V74 {np.abs(o74).max():4d}   V75 {np.abs(o75).max():4d}")
    o74a = rp74.run(sp_cts, r_signed, np.full(n, L.MODE_ENGAGED))
    o75a = rp75.run(sp_cts, r_signed, np.full(n, L.MODE_ENGAGED))
    print(f"  replayed |gp-0x6bd0| max, mode-26 EVERYWHERE (the clip check's own sweep): "
          f"V74 {np.abs(o74a).max():4d}   V75 {np.abs(o75a).max():4d}")
    R["magnitude"] = dict(gated_v74=int(np.abs(o74).max()), gated_v75=int(np.abs(o75).max()),
                          m26_v74=int(np.abs(o74a).max()), m26_v75=int(np.abs(o75a).max()))

    # ---------------- B. relay-plateau occupancy -----------------------------------------------------
    hdr("B.  RELAY-PLATEAU OCCUPANCY -- gp-0x6ac0 >= 400 (V74 entry) vs >= 200 (V75 entry)")
    strata = [
        ("ALL frames", np.ones(n, bool)),
        ("ENGAGED (mode 26 in force)", in26),
        ("ENGAGED creep  (< 4.0 m/s)", in26 & (D["cs_v"] < CREEP_MS)),
        ("ENGAGED 0-35 km/h (FactorC flat)", in26 & (sp_cts < FLAT_C_CTS)),
        ("MANUAL (mode 24 byte-stock)", in24),
    ]
    print(f"  {'stratum':34s} {'n':>7s} {'sec':>8s} | {'>=200 n':>8s} {'>=200 s':>8s} {'%':>7s} |"
          f" {'>=400 n':>8s} {'>=400 s':>8s} {'%':>7s} | {'ratio':>6s}")
    print("  " + "-" * 118)
    occ = {}
    for nm, m in strata:
        tot = int(m.sum())
        s200 = m & (r_cts >= ENTRY_V75)
        s400 = m & (r_cts >= ENTRY_V74)
        n2, n4 = int(s200.sum()), int(s400.sum())
        rat = (n2 / n4) if n4 else float("inf")
        print(f"  {nm:34s} {tot:7d} {tot*W:8.2f} | {n2:8d} {n2*W:8.2f} {100*n2/max(tot,1):7.3f} |"
              f" {n4:8d} {n4*W:8.2f} {100*n4/max(tot,1):7.3f} | {rat:6.2f}")
        occ[nm] = dict(n=tot, s=tot * W, n200=n2, s200=n2 * W, n400=n4, s400=n4 * W,
                       pct200=100 * n2 / max(tot, 1), pct400=100 * n4 / max(tot, 1), ratio=rat)
    R["occupancy"] = occ

    # ---------------- C. dwell + sign-flip structure --------------------------------------------------
    hdr("C.  DWELL STRUCTURE INSIDE THE PLATEAU, and the full-amplitude SIGN FLIPS")

    def runs(mask):
        idx = np.flatnonzero(mask)
        if not len(idx):
            return []
        brk = np.flatnonzero(np.diff(idx) > 1)
        return np.split(idx, brk + 1)

    dwell = {}
    for nm, m in strata[:4]:
        for entry, lab in ((ENTRY_V75, "V75>=200"), (ENTRY_V74, "V74>=400")):
            rr = runs(m & (r_cts >= entry))
            dur = np.array([len(r) * W for r in rr])
            if not len(dur):
                continue
            key = f"{nm} | {lab}"
            dwell[key] = dict(n_runs=len(dur), med_ms=float(np.median(dur) * 1e3),
                              p90_ms=float(np.percentile(dur, 90) * 1e3),
                              max_ms=float(dur.max() * 1e3), total_s=float(dur.sum()))
            print(f"  {key:48s} runs {len(dur):5d}  median {np.median(dur)*1e3:6.1f} ms  "
                  f"p90 {np.percentile(dur,90)*1e3:7.1f} ms  max {dur.max()*1e3:8.1f} ms  "
                  f"total {dur.sum():7.2f} s")
    R["dwell"] = dwell

    print("\n  FULL-AMPLITUDE SIGN FLIPS: a transition from (rate <= -entry) to (rate >= +entry) or")
    print("  the reverse. Inside the plateau the damper magnitude is CONSTANT, so each flip is a")
    print("  full 2x|plateau| swing of the term. `traverse` is the time spent out of the band between.")
    flips = {}
    for nm, m in strata[:4] + [strata[4]]:
        for entry, lab, amp in ((ENTRY_V75, "V75>=200", 297), (ENTRY_V74, "V74>=400", 225)):
            hi = m & (r_signed >= entry)
            lo = m & (r_signed <= -entry)
            ev = np.zeros(n, np.int8)
            ev[hi] = 1
            ev[lo] = -1
            idx = np.flatnonzero(ev != 0)
            if len(idx) < 2:
                continue
            sgn = ev[idx]
            ch = np.flatnonzero(np.diff(sgn) != 0)
            trav = D["t"][idx[ch + 1]] - D["t"][idx[ch]]
            inband = float((m & (r_cts >= entry)).sum()) * W
            walls = float(m.sum()) * W
            key = f"{nm} | {lab}"
            flips[key] = dict(n_flips=int(len(ch)), inband_s=inband,
                              per_s_inband=len(ch) / inband if inband else float("nan"),
                              per_s_wall=len(ch) / walls if walls else float("nan"),
                              trav_med_ms=float(np.median(trav) * 1e3) if len(trav) else None,
                              swing_counts=2 * amp)
            print(f"  {key:48s} flips {len(ch):5d}  {len(ch)/max(inband,1e-9):6.3f}/s in-band  "
                  f"{len(ch)/max(walls,1e-9):6.4f}/s wall  traverse median "
                  f"{np.median(trav)*1e3 if len(trav) else float('nan'):7.1f} ms  swing {2*amp} cts")
    R["flips"] = flips

    # ---------------- D. the 4000-count corner --------------------------------------------------------
    hdr("D.  THE 4000-COUNT / 849 deg/s CORNER -- does route 5d ever come close?")
    for lab, x in (("gp-0x6ac0 (0x18F fine)", r_cts), ("gp-0x6ac0 (0x14A coarse)", r_cts_coarse)):
        print(f"  {lab:26s}  p99 {np.percentile(x,99):7.1f}  p99.9 {np.percentile(x,99.9):7.1f}  "
              f"p99.99 {np.percentile(x,99.99):7.1f}  MAX {x.max():7.0f}")
    for lab, m in (("engaged", in26), ("engaged 0-35 km/h", in26 & (sp_cts < FLAT_C_CTS))):
        x = r_cts[m]
        print(f"  {'  '+lab:26s}  p99 {np.percentile(x,99):7.1f}  p99.9 {np.percentile(x,99.9):7.1f}  "
              f"p99.99 {np.percentile(x,99.99):7.1f}  MAX {x.max():7.0f}")
    print(f"\n  MAX = {r_cts.max()} counts = {r_cts.max()/L.CTS_PER_DEGS:.1f} column deg/s "
          f"= {100.0*r_cts.max()/CORNER:.1f}% of the {CORNER}-count corner "
          f"({CORNER/L.CTS_PER_DEGS:.0f} deg/s).")
    print(f"  frames at >= {CORNER}: {int((r_cts>=CORNER).sum())};  "
          f"at >= 2500 (FactorE X[2]): {int((r_cts>=2500).sum())};  "
          f"at >= 1555: {int((r_cts>=1555).sum())}")
    R["corner"] = dict(max_cts=int(r_cts.max()), max_degs=float(r_cts.max() / L.CTS_PER_DEGS),
                       p99=float(np.percentile(r_cts, 99)), p999=float(np.percentile(r_cts, 99.9)),
                       p9999=float(np.percentile(r_cts, 99.99)),
                       pct_of_corner=float(100.0 * r_cts.max() / CORNER),
                       n_ge_4000=int((r_cts >= CORNER).sum()),
                       n_ge_2500=int((r_cts >= 2500).sum()),
                       n_ge_1555=int((r_cts >= 1555).sum()))

    # ---------------- E. per-tick step ---------------------------------------------------------------
    hdr("E.  PER-TICK STEP |d gp-0x6bd0| (kept as a cheap confirmation of the refutation)")
    same = np.diff(D["seg"]) == 0
    gooddt = (np.diff(D["t"]) >= 0.005) & (np.diff(D["t"]) <= 0.015)
    pair = same & gooddt
    print(f"  usable consecutive pairs: {int(pair.sum())} of {n-1} "
          f"({100*pair.mean():.3f}%; rejected = segment joins + timestamp collisions)")
    steps = {}
    for lab, a, b in (("mode-gated", o74, o75), ("mode-26 everywhere", o74a, o75a)):
        for bn, o in (("V74", a), ("V75", b)):
            s = np.abs(np.diff(o))[pair]
            st = L.q(s)
            st["gt205"] = int((s > L.SLEW_TIGHT).sum())
            st["gt512"] = int((s > L.SLEW_LOOSE).sum())
            steps[f"{lab}|{bn}"] = st
            print(f"  {lab:20s} {bn}  p50 {st['p50']:6.1f}  p90 {st['p90']:6.1f}  p99 {st['p99']:6.1f}"
                  f"  p99.9 {st['p999']:6.1f}  MAX {st['max']:6.0f} | >205: {st['gt205']:6d}"
                  f"  >512: {st['gt512']:6d}")
    R["steps"] = steps

    # ---------------- F. launch events ---------------------------------------------------------------
    hdr("F.  LAUNCH EVENTS -- speed from < 1 km/h to > 20 km/h")
    v = D["cs_v"]
    LO, HI = 1.0 / 3.6, 20.0 / 3.6
    ev = []
    i = 0
    while i < n:
        if v[i] < LO:
            j = i
            while j < n and v[j] < HI:
                if v[j] < LO:
                    last_lo = j
                j += 1
            if j < n and D["seg"][j] == D["seg"][i]:
                k = last_lo
                ev.append((k, j))
                i = j
            else:
                i = j if j > i else i + 1
        else:
            i += 1
    ev = [(a, b) for a, b in ev if D["t"][b] - D["t"][a] < 30.0 and D["seg"][a] == D["seg"][b]]
    print(f"  n launch events found (any engagement state): {len(ev)}")
    eng_ev = [(a, b) for a, b in ev if in26[a:b + 1].mean() > 0.5]
    print(f"  ... of which ENGAGED (mode 26 in force for >50% of the ramp): {len(eng_ev)}")
    print(f"\n  {'#':>3s} {'seg':>4s} {'t0':>8s} {'dur':>6s} {'eng%':>6s} {'maxrate':>8s} "
          f"{'|o74|max':>9s} {'|o75|max':>9s} {'d74max':>7s} {'d75max':>7s} {'s200':>6s} {'s400':>6s}")
    lev = []
    for c, (a, b) in enumerate(ev):
        sl = slice(a, b + 1)
        pm = pair[a:b]
        d74 = np.abs(np.diff(o74[sl]))[pm] if pm.sum() else np.array([0])
        d75 = np.abs(np.diff(o75[sl]))[pm] if pm.sum() else np.array([0])
        row = dict(seg=int(D["seg"][a]), t0=float(D["t_seg"][a]), dur=float(D["t"][b] - D["t"][a]),
                   engpct=float(in26[sl].mean() * 100), maxrate=int(r_cts[sl].max()),
                   o74=int(np.abs(o74[sl]).max()), o75=int(np.abs(o75[sl]).max()),
                   d74=int(d74.max()), d75=int(d75.max()),
                   s200=float((r_cts[sl] >= ENTRY_V75).sum() * W),
                   s400=float((r_cts[sl] >= ENTRY_V74).sum() * W))
        lev.append(row)
        print(f"  {c:3d} {row['seg']:4d} {row['t0']:8.2f} {row['dur']:6.2f} {row['engpct']:6.1f} "
              f"{row['maxrate']:8d} {row['o74']:9d} {row['o75']:9d} {row['d74']:7d} {row['d75']:7d} "
              f"{row['s200']:6.2f} {row['s400']:6.2f}")
    R["launch"] = dict(n=len(ev), n_engaged=len(eng_ev), events=lev)

    # ---------------- G. episode bootstrap + split-half null -------------------------------------------
    hdr("G.  EPISODE-LEVEL BOOTSTRAP AND THE SPLIT-HALF NULL  (rule: episodes, not windows)")
    eps = L.episodes(D["cc_lat"], D["t"])
    print(f"  engagement episodes n = {len(eps)}  (extractor's own definition; its summary says 9)")
    print(f"  durations (s): {[round(float(D['t'][e[-1]]-D['t'][e[0]]),1) for e in eps]}")

    def occ_ratio(idxs):
        x = r_cts[idxs]
        n4 = int((x >= ENTRY_V74).sum())
        n2 = int((x >= ENTRY_V75).sum())
        return (n2 / n4) if n4 else np.nan, n2, n4

    per_ep = [occ_ratio(e) for e in eps]
    print(f"\n  per-episode >=200/>=400 occupancy ratio: "
          f"{[None if np.isnan(r) else round(r,2) for r,_,_ in per_ep]}")
    B = 20000
    boot = []
    for _ in range(B):
        pick = RNG.integers(0, len(eps), len(eps))
        n2 = sum(per_ep[i][1] for i in pick)
        n4 = sum(per_ep[i][2] for i in pick)
        boot.append(n2 / n4 if n4 else np.nan)
    boot = np.array(boot, float)
    boot = boot[np.isfinite(boot)]
    pt = sum(p[1] for p in per_ep) / max(sum(p[2] for p in per_ep), 1)
    ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
    print(f"  POINT ESTIMATE (engaged episodes pooled): {pt:.3f}   "
          f"episode bootstrap 95% CI [{ci[0]:.3f}, {ci[1]:.3f}]   B={B}, n_episodes={len(eps)}")

    print("\n  SPLIT-HALF NULL (the noise floor). Randomly split the 9 episodes into two halves and")
    print("  form the SAME statistic in each; the spread of halfA/halfB is what 'no difference'")
    print("  looks like on this route with this n.")
    nulls = []
    for _ in range(20000):
        perm = RNG.permutation(len(eps))
        h1, h2 = perm[: len(eps) // 2], perm[len(eps) // 2:]
        def stat(h):
            n2 = sum(per_ep[i][1] for i in h)
            n4 = sum(per_ep[i][2] for i in h)
            return n2 / n4 if n4 else np.nan
        a, b = stat(h1), stat(h2)
        if np.isfinite(a) and np.isfinite(b) and b > 0:
            nulls.append(a / b)
    nulls = np.array(nulls, float)
    print(f"  split-half null on the ratio-of-ratios: median {np.median(nulls):.3f}  "
          f"2.5/97.5 pct [{np.percentile(nulls,2.5):.3f}, {np.percentile(nulls,97.5):.3f}]  "
          f"(n_draws {len(nulls)})")
    R["bootstrap"] = dict(n_episodes=len(eps), point=float(pt), ci95=ci,
                          null_median=float(np.median(nulls)),
                          null_ci=[float(np.percentile(nulls, 2.5)), float(np.percentile(nulls, 97.5))])

    OUT.write_text(json.dumps(R, indent=1, default=float))
    print(f"\n  wrote {OUT}")


if __name__ == "__main__":
    main()
