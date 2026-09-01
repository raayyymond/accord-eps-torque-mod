#!/usr/bin/env python3
"""Re-score the ENTIRE flown corpus in the 2-4 Hz band -- the LKAS lane's own closed-loop
band, which the kit has used for a year only as a NORMALISING CONTROL and never as a target.

WHY: operator flashed V276 and reports a large self-exciting 2-4 Hz oscillation, LKAS-engaged
only, all speeds, straight roads.  Every "no effect" null in the corpus was computed over band
sets whose lowest edge is 5 or 6 Hz (`BANDS=[(6,9),(9,12),(15,22),(22,30)]`).  The pipeline is
NOT blind -- FS=100, no high-pass, no detrend anywhere in rlog-tools/score or /lib, caches raw
100 Hz -- so the whole corpus can be re-scored at 2-4 Hz with no new data.

METHOD NOTE / DELIBERATE DEVIATION FROM THE HOUSE SCORER:
  `studies/impedance/rez_by_band_all_routes.py` masks by ZEROING (`np.where(m, x, 0)`) and
  welches the whole route.  At 6-9 Hz that is tolerable; at 2-4 Hz it is NOT -- every mask edge
  is a step, and step energy is ~1/f^2, i.e. concentrated exactly in 2-4 Hz.  Here we instead
  extract CONTIGUOUS runs of each mask (>= NPS samples), welch each run separately, and
  average the PSDs weighted by run length.  Bands, FS, NPS, overlap and the mean-removal are
  otherwise the house values so the numbers stay comparable.

CHANNELS
  cs_ang    carState.steeringAngleDeg          the RESPONSE (deg)
  cs_rate   carState.steeringRateDeg           the RESPONSE rate (deg/s)  [CAN 0x18F]
  cs_tq     carState.steeringTorque            driver torque (counts)
  co_req    carOutput.actuatorsOutput.torque   openpilot's COMMAND  <-- the discriminator
  e4tq      CAN 0x0E4 STEER_TORQUE on the wire the DELIVERED command

THE DISCRIMINATOR (task item 3): 2-4 Hz power in the COMMAND vs in the RESPONSE, plus
coherence and phase between them.
  command oscillating  => instability in openpilot's OUTER loop  => fix is comma-side
  command smooth, angle oscillating => instability in the EPS INNER loop => fix is firmware

Usage:  python rlog-tools/studies/osc-2to4/rescore_2to4hz_all_routes.py [--json OUT]
"""
import numpy as np, glob, os, sys, json
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view

FS   = 100.0
NPS  = 512          # house value; bin width 0.1953 Hz, window 5.12 s
NOV  = NPS // 2
BAND_T = (2.0, 4.0)     # the target band
BAND_R = (6.0, 9.0)     # the familiar reference band
CH = ("ang", "rate_f", "tq", "co_req", "e4tq")

CACHE_ROOTS = ("_scratch/cache", "analysis-2020accord/_scratch/cache")

# route -> build.  `probe_build` in the npz is authoritative where it is not UNVERIFIED/'?';
# these four are resolved from docs/BUILD-LINEAGE-CATCHUP-V76-V100.md (grep "FLEW AS ROUTE").
BUILD_OVERRIDE = {"r71": "V87", "r73": "V88", "r75": "V89", "r76": "V89"}


def runs_of(mask, minlen):
    """Contiguous True runs of `mask` at least `minlen` long, as (i0, i1) half-open."""
    m = np.asarray(mask, bool).astype(np.int8)
    d = np.diff(np.concatenate(([0], m, [0])))
    starts, stops = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return [(a, b) for a, b in zip(starts, stops) if b - a >= minlen]


def welch_runs(x, segs):
    """Length-weighted average Welch PSD over the given contiguous runs.  Mean removed per
    run (the house scorers do `x - x.mean()`; done per run here because runs are disjoint)."""
    P, W, f = None, 0.0, None
    for a, b in segs:
        s = np.nan_to_num(np.asarray(x[a:b], float))
        f, p = signal.welch(s - s.mean(), FS, nperseg=NPS, noverlap=NOV)
        w = float(b - a)
        P = p * w if P is None else P + p * w
        W += w
    return (f, P / W) if W else (None, None)


def csd_runs(x, y, segs):
    """Length-weighted Pxy, Pxx, Pyy over the same runs -> coherence and phase."""
    A = B = C = None; W = 0.0; f = None
    for a, b in segs:
        u = np.nan_to_num(np.asarray(x[a:b], float)); u = u - u.mean()
        v = np.nan_to_num(np.asarray(y[a:b], float)); v = v - v.mean()
        f, pxy = signal.csd(u, v, FS, nperseg=NPS, noverlap=NOV)
        _, pxx = signal.welch(u, FS, nperseg=NPS, noverlap=NOV)
        _, pyy = signal.welch(v, FS, nperseg=NPS, noverlap=NOV)
        w = float(b - a)
        A = pxy * w if A is None else A + pxy * w
        B = pxx * w if B is None else B + pxx * w
        C = pyy * w if C is None else C + pyy * w
        W += w
    if not W:
        return None
    return f, A / W, B / W, C / W


def bandpow(f, P, band):
    """Integrated PSD over the band (units^2), trapezoid over the bins in band."""
    if P is None:
        return float("nan")
    m = (f >= band[0]) & (f < band[1])
    return float(np.trapezoid(P[m], f[m])) if m.sum() > 1 else float("nan")


def peak_in(f, P, lo, hi, ref=(1.0, 10.0)):
    """Peak inside [lo,hi): centre freq, prominence over the local median, and Q from the
    -3 dB (half-power) width.  Returns (fc, prom, Q) with NaNs if no interior peak."""
    if P is None:
        return (np.nan, np.nan, np.nan)
    m = (f >= lo) & (f < hi)
    if m.sum() < 3:
        return (np.nan, np.nan, np.nan)
    fb, pb = f[m], P[m]
    i = int(np.argmax(pb))
    base = np.median(P[(f >= ref[0]) & (f < ref[1])])
    prom = float(pb[i] / max(base, 1e-30))
    gi = int(np.flatnonzero(m)[i]); half = P[gi] / 2.0
    lo_i = gi
    while lo_i > 0 and P[lo_i] > half:
        lo_i -= 1
    hi_i = gi
    while hi_i < len(P) - 1 and P[hi_i] > half:
        hi_i += 1
    bw = f[hi_i] - f[lo_i]
    Q = float(f[gi] / bw) if bw > 0 else np.nan
    return (float(fb[i]), prom, Q)


def load_route(f):
    z = np.load(f, allow_pickle=True)
    need = ("cs_v", "cc_lat", "ang", "rate_f", "tq")
    if any(k not in z.files for k in need):
        return None
    d = {k: np.nan_to_num(np.asarray(z[k], float)) for k in need}
    for k in ("co_req", "e4tq"):
        d[k] = np.nan_to_num(np.asarray(z[k], float)) if k in z.files else None
    tag = os.path.basename(os.path.dirname(f))
    pb = str(z["probe_build"][0]) if "probe_build" in z.files else "?"
    d["_tag"], d["_build"] = tag, BUILD_OVERRIDE.get(tag, pb)
    return d


def masks(d):
    v, lat = d["cs_v"], d["cc_lat"]
    eng = (lat > 0.5) & (v > 1.0)
    man = (lat < 0.5) & (v > 1.0)
    # STRAIGHT-ROAD subset: the symptom self-excites on straight roads, so hold |angle| small
    # over a 5 s window (median, so a single transient does not disqualify a run).
    w = 501
    pad = np.pad(np.abs(d["ang"]), (w // 2, w - 1 - w // 2), mode="edge")
    ang_med = np.median(sliding_window_view(pad, w), axis=-1)[: len(d["ang"])]
    straight = ang_med < 5.0
    return {"ENG": eng, "MAN": man, "ENG_STRAIGHT": eng & straight}


def score_route(d):
    out = {"route": d["_tag"], "build": d["_build"], "arms": {}}
    for arm, m in masks(d).items():
        segs = runs_of(m, NPS)
        n = sum(b - a for a, b in segs)
        rec = {"secs": n / FS, "n_runs": len(segs)}
        if n < 2 * NPS:
            out["arms"][arm] = rec
            continue
        for ch in CH:
            if d.get(ch) is None:
                continue
            f, P = welch_runs(d[ch], segs)
            fc, prom, Q = peak_in(f, P, 1.5, 5.0)
            rec[ch] = {"p24": bandpow(f, P, BAND_T), "p69": bandpow(f, P, BAND_R),
                       "peak_f": fc, "peak_prom": prom, "peak_Q": Q}
        # DISCRIMINATOR: command -> response, coherence and phase in each band
        for cmdch in ("co_req", "e4tq"):
            if d.get(cmdch) is None:
                continue
            for respch in ("rate_f", "ang"):
                r = csd_runs(d[cmdch], d[respch], segs)
                if r is None:
                    continue
                f, Pxy, Pxx, Pyy = r
                for nm, band in (("24", BAND_T), ("69", BAND_R)):
                    bm = (f >= band[0]) & (f < band[1])
                    coh = float(np.mean(np.abs(Pxy[bm]) ** 2 /
                                        np.maximum(Pxx[bm] * Pyy[bm], 1e-30)))
                    wgt = np.abs(Pxy[bm])   # power-weighted mean phase
                    ph = float(np.degrees(np.angle(np.sum(Pxy[bm] * wgt))))
                    rec["%s->%s_%s" % (cmdch, respch, nm)] = {"coh2": coh, "phase_deg": ph}
        out["arms"][arm] = rec
    return out


def main():
    files = []
    for root in CACHE_ROOTS:
        for f in sorted(glob.glob(os.path.join(root, "*", "*.npz"))):
            tag = os.path.basename(os.path.dirname(f))
            if os.path.basename(f) == tag + ".npz":
                files.append(f)
    res = []
    for f in files:
        d = load_route(f)
        if d is None:
            print("SKIP (schema) %s" % f); continue
        res.append(score_route(d))

    def g(r, arm, ch, k):
        a = r["arms"].get(arm, {})
        return a.get(ch, {}).get(k, float("nan")) if isinstance(a.get(ch), dict) else float("nan")

    print("=" * 132)
    print("2-4 Hz RE-SCORE OF THE FLOWN CORPUS   (FS=%g, nperseg=%d, contiguous-run Welch)" % (FS, NPS))
    print("=" * 132)
    hdr = ("%-5s %-10s %7s %7s | %10s %10s %6s | %10s %10s %6s | %8s %8s" %
           ("route", "build", "engS", "manS", "ANG24_E", "ANG24_M", "E/M",
            "RATE24_E", "RATE24_M", "E/M", "ANG69_E", "RATE69_E"))
    print(hdr); print("-" * len(hdr))
    for r in sorted(res, key=lambda r: r["build"]):
        aE, aM = g(r, "ENG", "ang", "p24"), g(r, "MAN", "ang", "p24")
        rE, rM = g(r, "ENG", "rate_f", "p24"), g(r, "MAN", "rate_f", "p24")
        print("%-5s %-10s %7.0f %7.0f | %10.3f %10.3f %6.2f | %10.1f %10.1f %6.2f | %8.4f %8.2f" %
              (r["route"], r["build"], r["arms"].get("ENG", {}).get("secs", 0),
               r["arms"].get("MAN", {}).get("secs", 0),
               aE, aM, aE / aM if aM else np.nan, rE, rM, rE / rM if rM else np.nan,
               g(r, "ENG", "ang", "p69"), g(r, "ENG", "rate_f", "p69")))

    print("\n" + "=" * 132)
    print("THE DISCRIMINATOR -- is the COMMAND oscillating, or only the RESPONSE?  (ENGAGED arm)")
    print("  R = cmd24 / cmd69 : if the command's OWN spectrum is tilted into 2-4 Hz, the outer loop rings")
    print("  coh/ph = e4tq (wire command) -> cs_rate")
    print("=" * 132)
    hdr2 = ("%-5s %-10s | %11s %11s %6s | %11s %11s %6s | %6s %7s | %6s %7s" %
            ("route", "build", "co_req24", "co_req69", "R", "e4tq24", "e4tq69", "R",
             "coh24", "ph24", "coh69", "ph69"))
    print(hdr2); print("-" * len(hdr2))
    for r in sorted(res, key=lambda r: r["build"]):
        c24, c69 = g(r, "ENG", "co_req", "p24"), g(r, "ENG", "co_req", "p69")
        e24, e69 = g(r, "ENG", "e4tq", "p24"), g(r, "ENG", "e4tq", "p69")
        k = r["arms"].get("ENG", {}).get("e4tq->rate_f_24", {})
        k9 = r["arms"].get("ENG", {}).get("e4tq->rate_f_69", {})
        print("%-5s %-10s | %11.4g %11.4g %6.2f | %11.4g %11.4g %6.2f | %6.3f %7.1f | %6.3f %7.1f" %
              (r["route"], r["build"], c24, c69, c24 / c69 if c69 else np.nan,
               e24, e69, e24 / e69 if e69 else np.nan,
               k.get("coh2", np.nan), k.get("phase_deg", np.nan),
               k9.get("coh2", np.nan), k9.get("phase_deg", np.nan)))

    print("\n" + "=" * 132)
    print("IS THERE A PEAK IN 2-4 Hz, OR JUST BROADBAND POWER?   peak searched in 1.5-5.0 Hz,")
    print("  prominence = PSD(peak) / median PSD over 1-10 Hz;  Q from the half-power width.")
    print("  A SHARP peak at the SAME f across routes = structural resonance.  Moving = not.")
    print("=" * 132)
    hdr3 = ("%-5s %-10s | %6s %6s %6s | %6s %6s %6s | %6s %6s %6s" %
            ("route", "build", "AfE", "ApE", "AQE", "RfE", "RpE", "RQE", "AfM", "ApM", "AQM"))
    print(hdr3); print("-" * len(hdr3))
    for r in sorted(res, key=lambda r: r["build"]):
        print("%-5s %-10s | %6.2f %6.2f %6.2f | %6.2f %6.2f %6.2f | %6.2f %6.2f %6.2f" %
              (r["route"], r["build"],
               g(r, "ENG", "ang", "peak_f"), g(r, "ENG", "ang", "peak_prom"), g(r, "ENG", "ang", "peak_Q"),
               g(r, "ENG", "rate_f", "peak_f"), g(r, "ENG", "rate_f", "peak_prom"), g(r, "ENG", "rate_f", "peak_Q"),
               g(r, "MAN", "ang", "peak_f"), g(r, "MAN", "ang", "peak_prom"), g(r, "MAN", "ang", "peak_Q")))

    print("\n" + "=" * 132)
    print("STRAIGHT-ROAD ENGAGED SUBSET (5 s median |angle| < 5 deg) -- he says it self-excites on straights")
    print("=" * 132)
    hdr4 = ("%-5s %-10s %7s | %10s %10s | %10s %10s | %6s %6s" %
            ("route", "build", "secs", "ANG24", "RATE24", "co_req24", "e4tq24", "pkf", "pkprm"))
    print(hdr4); print("-" * len(hdr4))
    for r in sorted(res, key=lambda r: r["build"]):
        A = "ENG_STRAIGHT"
        print("%-5s %-10s %7.0f | %10.4f %10.2f | %10.4g %10.4g | %6.2f %6.2f" %
              (r["route"], r["build"], r["arms"].get(A, {}).get("secs", 0),
               g(r, A, "ang", "p24"), g(r, A, "rate_f", "p24"),
               g(r, A, "co_req", "p24"), g(r, A, "e4tq", "p24"),
               g(r, A, "rate_f", "peak_f"), g(r, A, "rate_f", "peak_prom")))

    print("\n" + "=" * 132)
    print("RANKING -- flown builds by ENGAGED 2-4 Hz steering-RATE power (was 2-4 Hz already rising?)")
    print("=" * 132)
    rk = sorted([r for r in res if np.isfinite(g(r, "ENG", "rate_f", "p24"))],
                key=lambda r: -g(r, "ENG", "rate_f", "p24"))
    for i, r in enumerate(rk, 1):
        rE, rM = g(r, "ENG", "rate_f", "p24"), g(r, "MAN", "rate_f", "p24")
        print("%2d. %-5s %-10s  rate24_ENG %9.1f   E/M %6.2f   ang24_ENG %8.4f   engS %5.0f"
              % (i, r["route"], r["build"], rE, rE / rM if rM else np.nan,
                 g(r, "ENG", "ang", "p24"), r["arms"].get("ENG", {}).get("secs", 0)))

    if "--json" in sys.argv:
        p = sys.argv[sys.argv.index("--json") + 1]
        json.dump(res, open(p, "w"), indent=1, default=float)
        print("\nwrote %s" % p)


if __name__ == "__main__":
    main()
