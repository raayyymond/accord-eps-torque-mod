#!/usr/bin/env python3
"""Route `4f` (V69) HIGHWAY: the order veto, the band contrasts, and P1/P3/P4.

🛑🛑 THE STRUCTURAL FACT THAT DECIDES WHAT THIS ROUTE CAN TEST, STATED FIRST.
V69's rate-lane dose is a FUNCTION OF SPEED and is **EXACTLY 1.000x -- byte-identical to stock --
at and above 50 km/h (13.9 m/s)**, because >= 50 km/h reads only rec2/rec3 and V69 leaves those
untouched. V68, the build immediately before it, ran **2.00x at EVERY speed whenever LKAS applied**.
So on the highway arm:

        route 4e  (V68, engaged highway)  ==  Kd = 2.00x
        route 4f  (V69, engaged highway)  ==  Kd = 1.000x  (stock rate lane)

⇒ 4f is a **NEW Kd = 1 HIGHWAY MANEUVER SAMPLE**, which is precisely what
HANDOFF-2026-08-03 §8 said the 26-30 Hz dose ratio needed: its Kd = 1 maneuver arm held only 39
windows in 17 blocks (~50 s of active maneuvering), which is why the 3.334x point estimate sat
inside a [0.33, 3.36] split-half null.
★ AND 4f FIXES THAT POOL'S OTHER DEFECT. The prior Kd = 1 maneuver pool was DRIVER-steered (4c
manual, r2b); 4f's is **openpilot ALC**, the same excitation as the Kd = 2 pool. The
"driver-initiated and ALC-initiated maneuvers are not the same excitation" confound is removed.

⚠ AND WHAT 4f CANNOT DO. Its highway arm is 100.0% engaged, so there is **no within-route
disengaged highway control**. Every cross-dose number here is CROSS-ROUTE (different road, different
day) and is caveated in place. The within-arm maneuver/control contrast is the one that carries
weight, exactly as on 4e.

METHOD -- the rules that have each retracted a claim in this kit:
  AVERAGE FIRST, PEAK-FIND AFTER. The reverse manufactures a line at band centre (dBIC 249-460).
  PER-WINDOW CENSUS. The band-centre test is necessary but NOT sufficient -- it passed the
      withdrawn "engaged-only 28 Hz line", which a per-window census then killed.
  SPEED DISTRIBUTIONS MUST MATCH before two routes' averaged spectra are compared: a moving wheel
      order concentrates in a narrow-speed route and smears in a wide one.
  EPISODES, never windows. SPLIT-HALF NULL beside every ratio.
  fs = the LATTICE MEAN RATE (`_r4f_lib.fs_lattice`), not 1/median(dt).

Usage:  python r4f_highway_bands.py [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G                                          # noqa: E402
import _r4f_lib as L                                             # noqa: E402
from _r31_common import load, periodogram, runs_of, sustained    # noqa: E402

# ★ 26-30 Hz is V68's headline band and is NOT in `_grind2_lib.BANDS`. Added to the module dict
# BEFORE any record is cut so it is computed by the same `win_env` / `locate` as every other band.
# Process-local; the on-disk record pickles are not shared with this script (it builds its own).
G.BANDS["26-30"] = (26.0, 30.0)
BANDORDER = ["1-4", "18-22", "24-28", "26-30", "30-40", "40-49"]

NFFT, HOP = G.NFFT, G.HOP
HWY = 20.0                       # m/s -- the kit's highway cut, and 4e/4c's
CIRC_LO, CIRC_HI = 2.073, 2.088  # measured wheel circumference (accord-v57-confirms-wheel-order)
ORD1_LO, ORD1_HI = 1 / CIRC_HI, 1 / CIRC_LO     # 0.4789 .. 0.4824 Hz per m/s
LINE_CRIT = 4.0                  # the kit's prominence criterion for "a line exists"

# V68's absolute maneuver/control cut pair, reused unchanged so the two routes are comparable.
MV_HI, MV_LO = 19.0, 11.0

ROUTES = {
    "4f/V69": dict(cache=ROOT / "_cache_r4f", pfx="r4fs", segs=list(range(8)), kd_hwy=1.000),
    "4e/V68": dict(cache=ROOT / "_cache_v68", pfx="4es", segs=[31, 32, 33, 34], kd_hwy=2.000),
}
RES: dict = {}


def hdr(s):
    print(f"\n{'=' * 112}\n{s}\n{'=' * 112}")


def segs_of(route):
    B = ROUTES[route]
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if p.exists():
            yield s, load(s, B["cache"], B["pfx"])


# ------------------------------------------------------------------ records ---------------------
def wrecs(route, chan="tq"):
    """`_grind2_lib.wrecs` specialised to these two caches: lattice fs, the 26-30 band, the blinker
    channel, and `ratepk` (the maneuver covariate)."""
    out = []
    for s, d in segs_of(route):
        fs = L.fs_lattice(d)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        taper = np.hanning(NFFT) + 1e-3
        cw = slice(int(0.2 * NFFT), int(0.8 * NFFT))
        le = d["cc_lat"] > 0.5
        has_rpm = "rpm" in d
        for eng, mask in ((1, le), (0, ~le)):
            for a, b in runs_of(mask, d["t"], NFFT):
                x = np.asarray(d[chan][a:b], float)
                nwin = 0
                for i in range(0, len(x) - NFFT + 1, HOP):
                    P = periodogram(x[i:i + NFFT], fs, NFFT, True)
                    if P is None:
                        continue
                    sl = slice(a + i, a + i + NFFT)
                    xw = x[i:i + NFFT]
                    R = G.prom_spectrum(f, P)
                    r = dict(route=route, seg=int(s), eng=eng, fs=fs,
                             ep=(route, int(s), int(a), int(b)), t0=float(d["t"][a + i]))
                    for k, bd in G.BANDS.items():
                        r["e_" + k] = G.win_env(xw, fs, *bd, taper, cw)
                        r["f_" + k], r["p_" + k] = G.locate(f, P, *bd, R=R)
                    r["p_30-49.5"] = G.locate(f, P, 30.0, 49.5, R=R)[1]
                    r["v"] = float(np.mean(np.abs(d["cs_v"][sl])))
                    r["ang"] = float(np.mean(np.abs(d["ang"][sl])))
                    r["eff"] = float(np.mean(np.abs(sustained(d["tq"][sl], fs))))
                    r["rate"] = float(np.mean(np.abs(d["rate_c"][sl])))
                    r["ratepk"] = float(np.max(np.abs(d["rate_c"][sl])))
                    r["lat"] = float(np.mean(d["cc_lat"][sl] > 0.5))
                    r["blink"] = float(np.mean(d["cs_lchg"][sl])) if "cs_lchg" in d else 0.0
                    r["rpm"] = float(np.mean(d["rpm"][sl])) if has_rpm else np.nan
                    r["cell"] = (G.binof(r["v"], G.V_BINS), G.binof(r["eff"], G.E_BINS),
                                 G.binof(r["rate"], G.R_BINS))
                    r["blk"] = r["ep"] + (nwin // 8,)
                    nwin += 1
                    out.append(r)
    return out


# ------------------------------------------------------------------ statistics ------------------
def boot_ratio(rsA, rsB, key, rng, nboot=4000, agg=np.median):
    epA, epB = G.episodes(rsA), G.episodes(rsB)
    if not epA or not epB:
        return np.nan, (np.nan, np.nan)
    point = agg(G.col(rsA, key)) / agg(G.col(rsB, key))
    out = []
    for _ in range(nboot):
        a = np.concatenate([G.col(epA[i], key) for i in rng.integers(0, len(epA), len(epA))])
        b = np.concatenate([G.col(epB[i], key) for i in rng.integers(0, len(epB), len(epB))])
        if len(a) and len(b) and agg(b) > 0:
            out.append(agg(a) / agg(b))
    if not out:
        return float(point), (np.nan, np.nan)
    return float(point), (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def split_null(rs, key, rng, nrep=800, agg=np.median):
    """Halve the SAME pool's episodes at random and ratio the halves -- the floor below which no
    ratio computed with this estimator is a finding."""
    ep = G.episodes(rs)
    if len(ep) < 4:
        return (np.nan, np.nan)
    out = []
    for _ in range(nrep):
        idx = rng.permutation(len(ep))
        h = len(ep) // 2
        a = np.concatenate([G.col(ep[i], key) for i in idx[:h]])
        b = np.concatenate([G.col(ep[i], key) for i in idx[h:]])
        if len(a) and len(b) and agg(b) > 0:
            out.append(agg(a) / agg(b))
    return ((float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))) if out
            else (np.nan, np.nan))


# ------------------------------------------------------------------ order veto ------------------
def avg_spec(route, vlo, vhi, eng=True):
    """Averaged periodogram over every qualifying window, plus the per-window prominence census."""
    acc, n, fref, vs, rp = None, 0, None, [], []
    proms = []
    for s, d in segs_of(route):
        fs = L.fs_lattice(d)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        le = d["cc_lat"] > 0.5
        has_rpm = "rpm" in d
        for a, b in runs_of(le if eng else ~le, d["t"], NFFT):
            for i in range(0, (b - a) - NFFT + 1, HOP):
                sl = slice(a + i, a + i + NFFT)
                v = float(np.mean(d["cs_v"][sl]))
                if not (vlo <= v < vhi):
                    continue
                P = periodogram(d["tq"][a + i:a + i + NFFT], fs, NFFT, True)
                if P is None:
                    continue
                if acc is None:
                    acc, fref = np.zeros_like(P), f
                if len(P) != len(acc):
                    continue
                acc += P; n += 1; vs.append(v)
                rp.append(float(np.mean(d["rpm"][sl])) if has_rpm else np.nan)
                Rw = G.prom_spectrum(f, P)
                proms.append(G.locate(f, P, 30.0, 49.5, R=Rw)[1])
    if not n:
        return None
    Pm = acc / n
    R = G.prom_spectrum(fref, Pm)
    fhi, phi = G.locate(fref, Pm, 30.0, 49.5, R=R)
    flo, plo = G.locate(fref, Pm, 8.0, 30.0, R=R)
    pr = np.array(proms, float)
    pr = pr[np.isfinite(pr)]
    return dict(n=n, vmean=float(np.mean(vs)), vsd=float(np.std(vs)),
                rpm=float(np.nanmean(rp)) if np.isfinite(rp).any() else np.nan,
                f_hi=float(fhi), prom_hi=float(phi), f_lo=float(flo), prom_lo=float(plo),
                win_med_prom=float(np.median(pr)) if len(pr) else np.nan,
                win_frac_gt4=float(np.mean(pr > LINE_CRIT)) if len(pr) else np.nan,
                win_max_prom=float(np.max(pr)) if len(pr) else np.nan)


# =================================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "_r4f_highway.json"))
    a = ap.parse_args()
    rng = np.random.default_rng(20260804)
    G.EPKEY = "blk"       # ~10.2 s blocks; `ep` leaves 3-6 units here and the null goes degenerate

    hdr("0.  THE SAMPLE-RATE LATTICE, AND THE EXPOSURE THIS ROUTE ACTUALLY HAS")
    for route in ROUTES:
        for s, d in segs_of(route):
            fl, fm = L.fs_lattice(d), 1.0 / np.median(np.diff(d["t"]))
            print(f"   {route} s{s}: lattice fs {fl:.4f} Hz   1/median(dt) {fm:.4f} Hz   "
                  f"legacy bias {100 * (fm / fl - 1):+.2f}%")
    W = {r: wrecs(r) for r in ROUTES}
    print()
    ARM = {}
    for r in ROUTES:
        ON = [w for w in W[r] if w["eng"] and w["v"] >= HWY]
        OFF = [w for w in W[r] if not w["eng"] and w["v"] >= HWY]
        ARM[r] = (ON, OFF)
        print(f"   {r}: {len(W[r])} windows total | highway>={HWY:.0f} m/s  "
              f"ENGAGED {len(ON)} win / {len(G.episodes(ON))} blocks   "
              f"DISENGAGED {len(OFF)} win / {len(G.episodes(OFF))} blocks")
        if ON:
            print(f"        engaged speed  p10/p50/p90 = "
                  f"{np.percentile(G.col(ON, 'v'), [10, 50, 90]).round(1)} m/s   "
                  f"|rate|pk p50 {np.median(G.col(ON, 'ratepk')):.1f}   "
                  f"eff p50 {np.median(G.col(ON, 'eff')):.0f}")
    RES["exposure"] = {r: dict(n_on=len(ARM[r][0]), n_off=len(ARM[r][1]),
                               blk_on=len(G.episodes(ARM[r][0]))) for r in ROUTES}

    # ---------------------------------------------------------------- 1 -------------------------
    hdr("1.  THE ORDER VETO -- averaged periodogram per speed bin, THEN peak-find")
    print(f"   criterion: a real line needs prominence > {LINE_CRIT:.0f}. 8-30 Hz is the POSITIVE")
    print(f"   CONTROL: wheel order 1 = v / CIRC, CIRC = {CIRC_LO}-{CIRC_HI} m "
          f"=> {ORD1_LO:.4f}-{ORD1_HI:.4f} Hz per m/s.")
    print("   Engine orders are computed from this route's OWN measured rpm, not assumed.\n")
    print(f"   {'route':8s} {'v bin':9s} {'n':>5s} {'v mean':>7s} {'rpm':>6s} "
          f"{'30-49.5 f0':>10s} {'prom':>6s} {'8-30 f0':>8s} {'prom':>6s} "
          f"{'ord1':>6s} {'ord2':>6s} {'eng1':>6s} {'eng2':>6s}  per-window 30-49.5")
    RES["veto"] = {}
    for route in ROUTES:
        for vlo, vhi in ((20, 23), (23, 26), (26, 32)):
            o = avg_spec(route, vlo, vhi, eng=True)
            if not o:
                continue
            o1 = o["vmean"] / ((CIRC_LO + CIRC_HI) / 2)
            e1 = o["rpm"] / 60.0 if np.isfinite(o["rpm"]) else np.nan
            RES["veto"][f"{route}_{vlo}-{vhi}"] = o
            print(f"   {route:8s} {f'{vlo}-{vhi}':9s} {o['n']:5d} {o['vmean']:7.2f} "
                  f"{o['rpm']:6.0f} {o['f_hi']:10.2f} {o['prom_hi']:6.2f} "
                  f"{o['f_lo']:8.2f} {o['prom_lo']:6.2f} {o1:6.2f} {2 * o1:6.2f} "
                  f"{e1:6.2f} {2 * e1:6.2f}  "
                  f"med {o['win_med_prom']:.2f} max {o['win_max_prom']:.2f} "
                  f">{LINE_CRIT:.0f} in {100 * o['win_frac_gt4']:.1f}%"
                  + ("   *** LINE" if o["prom_hi"] > LINE_CRIT else ""))
        print()
    print("   🛑 The per-window census is printed beside the averaged prominence deliberately: the")
    print("     band-centre test alone once survived on a line that a per-window census killed.")

    # ---------------------------------------------------------------- 2 -------------------------
    hdr("2.  WITHIN-ARM MANEUVER CONTRAST -- one ABSOLUTE cut pair, a null for every ratio")
    print(f"   maneuver = |rate|pk >= {MV_HI:.1f} deg/s, control = |rate|pk <= {MV_LO:.1f} deg/s.")
    print("   V68's own absolute pair, reused unchanged so 4f and 4e are the same measurement.")
    print("   🛑 P3 (40-49 Hz does not move) and P4 (1-4 Hz does not move) are the NEGATIVE")
    print("     CONTROLS: if they move, the edit did something other than intended.\n")
    RES["maneuver"] = {}
    for route in ROUTES:
        ON = ARM[route][0]
        mv = [w for w in ON if w["ratepk"] >= MV_HI]
        ct = [w for w in ON if w["ratepk"] <= MV_LO]
        kd = ROUTES[route]["kd_hwy"]
        print(f"   --- {route}  ENGAGED HIGHWAY, rate-lane dose at this speed = {kd:.3f}x ---")
        print(f"       {len(mv)} maneuver windows ({len(G.episodes(mv))} blocks) vs "
              f"{len(ct)} controls ({len(G.episodes(ct))} blocks)")
        if len(mv) < 5 or len(ct) < 5:
            print("       too few windows for an episode bootstrap")
            continue
        RES["maneuver"][route] = {}
        print(f"       {'band':8s} {'mv med':>9s} {'ct med':>9s} {'ratio':>8s} {'[95% CI]':>18s} "
              f"{'null(ct)':>16s} {'null(arm)':>16s}")
        for band in BANDORDER:
            k = "e_" + band
            pt, ci = boot_ratio(mv, ct, k, rng)
            n_ct = split_null(ct, k, rng)
            n_arm = split_null(ON, k, rng)
            sig = ""
            if np.isfinite(ci[0]) and np.isfinite(n_ct[1]) and ci[0] > n_ct[1]:
                sig = "  *** clears its null"
            RES["maneuver"][route][band] = dict(ratio=pt, ci=ci, null_ct=n_ct, null_arm=n_arm,
                                                n_mv=len(mv), n_ct=len(ct))
            print(f"       {band:8s} {np.median(G.col(mv, k)):9.1f} "
                  f"{np.median(G.col(ct, k)):9.1f} {pt:8.3f} [{ci[0]:7.3f}, {ci[1]:7.3f}] "
                  f"[{n_ct[0]:6.2f},{n_ct[1]:6.2f}] [{n_arm[0]:6.2f},{n_arm[1]:6.2f}]{sig}")
        print()

    # ---------------------------------------------------------------- 3 -------------------------
    hdr("3.  P1 -- THE CROSS-BUILD HIGHWAY DOSE CONTRAST, 4f (Kd=1.000) vs 4e (Kd=2.000)")
    print("   V68's §7 measured the dose ratio Kd=2 / Kd=1 on MANEUVER windows at 26-30 Hz as")
    print("   3.334 [1.201, 6.492] against a split-half null of [0.33, 3.36] -- it did NOT clear")
    print("   its floor. 4f supplies a fresh Kd = 1 highway maneuver arm, ALC-excited, so this is")
    print("   the direct replication. Ratio here is 4e / 4f, i.e. Kd=2 over Kd=1, same direction.\n")
    onF, onE = ARM["4f/V69"][0], ARM["4e/V68"][0]
    print("   🛑 SPEED-DISTRIBUTION MATCH FIRST -- an averaged/pooled comparison of two routes is")
    print("     only legitimate if the speed distributions overlap (a moving wheel order smears in")
    print("     one route and concentrates in the other).")
    for nm, arm in (("4f/V69", onF), ("4e/V68", onE)):
        v = G.col(arm, "v")
        print(f"     {nm}: n={len(arm)}  v p10/p50/p90 = {np.percentile(v, [10, 50, 90]).round(2)}"
              f"  min {v.min():.1f} max {v.max():.1f}")
    lo = max(np.percentile(G.col(onF, "v"), 5), np.percentile(G.col(onE, "v"), 5))
    hi = min(np.percentile(G.col(onF, "v"), 95), np.percentile(G.col(onE, "v"), 95))
    print(f"     common speed window used for the matched contrast: {lo:.2f} - {hi:.2f} m/s")
    RES["p1"] = dict(vwin=[float(lo), float(hi)])
    for tag, selF, selE in (
            ("ALL highway windows", lambda w: True, lambda w: True),
            (f"MATCHED {lo:.1f}-{hi:.1f} m/s", lambda w: lo <= w["v"] <= hi,
             lambda w: lo <= w["v"] <= hi)):
        mvF = [w for w in onF if w["ratepk"] >= MV_HI and selF(w)]
        mvE = [w for w in onE if w["ratepk"] >= MV_HI and selE(w)]
        ctF = [w for w in onF if w["ratepk"] <= MV_LO and selF(w)]
        ctE = [w for w in onE if w["ratepk"] <= MV_LO and selE(w)]
        print(f"\n   --- {tag} ---")
        print(f"   maneuver windows: 4f {len(mvF)} ({len(G.episodes(mvF))} blk) | "
              f"4e {len(mvE)} ({len(G.episodes(mvE))} blk)      "
              f"controls: 4f {len(ctF)} | 4e {len(ctE)}")
        if min(len(mvF), len(mvE)) < 4:
            print("   too few maneuver windows on one side")
            continue
        print(f"   {'band':8s} {'4e/4f MANEUVER':>22s} {'split-half null':>18s} "
              f"{'4e/4f CONTROL':>22s}   note")
        RES["p1"][tag] = {}
        for band in BANDORDER:
            k = "e_" + band
            pt, ci = boot_ratio(mvE, mvF, k, rng)
            nl = split_null(mvE + mvF, k, rng)
            pc, cc = boot_ratio(ctE, ctF, k, rng) if min(len(ctE), len(ctF)) >= 4 \
                else (np.nan, (np.nan, np.nan))
            note = ""
            if np.isfinite(ci[0]) and np.isfinite(nl[1]):
                note = "CLEARS null" if ci[0] > nl[1] else "inside null"
            RES["p1"][tag][band] = dict(mv_ratio=pt, mv_ci=ci, null=nl, ct_ratio=pc, ct_ci=cc)
            print(f"   {band:8s} {f'{pt:6.3f} [{ci[0]:.3f}, {ci[1]:.3f}]':>22s} "
                  f"{f'[{nl[0]:.2f}, {nl[1]:.2f}]':>18s} "
                  f"{f'{pc:6.3f} [{cc[0]:.3f}, {cc[1]:.3f}]':>22s}   {note}")

    # ---------------------------------------------------------------- 4 -------------------------
    hdr("4.  THE SAME CONTRAST AT CREEP -- where V69's dose is actually 4.000x")
    print("   The highway rows above test a dose CUT (2.00x -> 1.000x). V69's 4x lives BELOW")
    print("   50 km/h, so the creep rows are where a 4x effect would show. Route 4f engaged creep")
    print("   vs route 4e has no creep arm, so this is 4f's own maneuver/control contrast only.\n")
    crF = [w for w in W["4f/V69"] if w["eng"] and 0.3 < w["v"] < 4.0]
    mv = [w for w in crF if w["ratepk"] >= MV_HI]
    ct = [w for w in crF if w["ratepk"] <= MV_LO]
    print(f"   4f engaged creep: {len(crF)} windows, maneuver {len(mv)} "
          f"({len(G.episodes(mv))} blk) / control {len(ct)} ({len(G.episodes(ct))} blk)")
    RES["creep_maneuver"] = {}
    if len(mv) >= 5 and len(ct) >= 5:
        print(f"   {'band':8s} {'ratio':>8s} {'[95% CI]':>20s} {'null(ct)':>18s}")
        for band in BANDORDER:
            k = "e_" + band
            pt, ci = boot_ratio(mv, ct, k, rng)
            nl = split_null(ct, k, rng)
            RES["creep_maneuver"][band] = dict(ratio=pt, ci=ci, null=nl)
            print(f"   {band:8s} {pt:8.3f} [{ci[0]:8.3f}, {ci[1]:8.3f}] "
                  f"[{nl[0]:7.2f}, {nl[1]:7.2f}]"
                  + ("  *** clears" if np.isfinite(ci[0]) and np.isfinite(nl[1])
                     and ci[0] > nl[1] else ""))
    else:
        print("   too few windows for an episode bootstrap")

    Path(a.json).write_text(json.dumps(RES, indent=1, default=str))
    print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
