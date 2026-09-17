#!/usr/bin/env python3
"""instr_rate_tracking.py -- INSTRUMENT 2: rate-transient tracking.   STREAM TAG: instr

WHICH OPERATOR NOTE
  Note 5: "Control of slow, steady angle rates is decent, but MEDIUM TO LARGE ANGLE RATE TRANSIENTS
  are still not handled well."   (also bears on note 3, since on route 76 every large-angle frame is
  a transient -- see the data budget printed by instr_hold_error.py)

WHAT IT MEASURES
  Episodes are cut from the DESIRED wheel-rate trace (d/dt of the wire-derived desired angle; see
  instr_common header for how the desired angle is obtained without a vehicle model).  An episode is
  a contiguous, single-signed span with |rate_des| above a floor, merged across gaps under 0.1 s,
  and kept only if it lies wholly inside one engaged run.  For each episode:

    lag   = argmax of the FIXED-OVERLAP cross-correlation between rate_des and rate_act over the
            padded episode window, searched over -0.15 .. +0.70 s, parabolic sub-sample peak.
    gain  = lag-aligned projection   sum(rd * ra_shifted) / sum(rd^2)      (1.0 = perfect tracking)
    peak  = max|rate_act| / max|rate_des|, both taken over the LAG-ALIGNED EPISODE SPAN only (not
            the padding), so a bump seconds away cannot enter.  p95 = the same ratio on the 95th
            percentile instead of the max, which is insensitive to a single sample.
  gain and peak answer different questions.  gain ~ 1 with peak >> 1 means the wheel delivers the
  right AVERAGE rate in bursts that overshoot the commanded peak -- smoothness, not authority.

  Size classes are PERCENTILES of the episode peak |rate_des| (so the split adapts to the route),
  and the boundaries are printed in deg/s.  Results are reported per size class and per speed bin,
  always with the episode count.

  *** PEAK RATE CONFLATES AMPLITUDE WITH FREQUENCY. ***  A big slow ramp and a small fast wiggle can
  share a peak rate and are attenuated completely differently by any lag.  Control P4 below shows the
  effect explicitly (a pure 0.25 s lag reads gain 0.67 on the SMALL class and 0.91 on the LARGE one,
  purely from frequency content).  Every table therefore also prints the class median DURATION,
  ANGLE EXCURSION and characteristic frequency f_char = 1/(2*dur), so gain can be read against
  bandwidth and not against amplitude.  Read the f_char column before comparing classes.

POSITIVE CONTROLS (asserted)
  P1  pure delay+gain   rate_act = 0.80 * rate_des(t - 0.30 s)
                        -> gain 0.800 +/- 0.030, lag 0.300 +/- 0.020 s, in EVERY size class
  P2  single-frequency first-order lag, tau = 0.25 s, at f = 0.10 / 0.30 / 1.00 Hz
                        -> gain == |H| == 1/sqrt(1+(2 pi f tau)^2)      within 3%
                           lag  == phase delay == atan(2 pi f tau)/(2 pi f)  within 20 ms
                        This is an EXACT prediction, not a plausibility check.
  P3  identity          rate_act = rate_des  -> gain 1.000 +/- 0.005, lag 0.000 +/- 0.010 s
  P4  broadband first-order lag: DEMONSTRATION (not a pass/fail) that the peak-rate size class is
                        confounded with frequency; asserted only as Spearman(gain, f_char) < -0.3.
  P3 is the operator's own positive control in synthetic form: if slow steady rates do not come out
  near 1.0 on real data while P3 passes, the shortfall is the car, not the metric.

LANE CENTRING: ON (route 76 initData LaneCentering='1'); the demand is post-lane-centring.
ROUTE 76 IS REV 5 (gitCommit e44b6cd3).  Numbers from it are REV 5 BASELINES, not rev 6.4.

USAGE
    python3 instr_rate_tracking.py                # controls only
    python3 instr_rate_tracking.py r76_v293       # controls + route 76 (rev 5 baseline)
"""
import sys
import numpy as np
import instr_common as IC

RATE_FLOOR_DPS = 2.0      # an episode must exceed this; below it the 0.1 deg angle LSB dominates
MERGE_S = 0.10            # gaps shorter than this do not split an episode
MIN_EP_S = 0.15           # an episode shorter than this is a glitch, not a transient
PRE_S, POST_S = 0.50, 1.30   # padding, sized so the fixed-overlap correlation below always fits
LAG_MIN_S, LAG_MAX_S = -0.15, 0.70
PCTL = (50.0, 85.0)       # small | medium | large boundaries, percentiles of episode peak rate

# Which "desired" to track.  cs_la_des is the POST-reference-filter SETPOINT (latcontrol_torque.py:839),
# so "sa_des_rate" answers "does the wheel follow its own setpoint".  "sa_mod_rate" is built from
# desiredCurvature (post-lane-centring, PRE delay-comp and ref filter) and answers the operator's
# actual goal, "does the wheel follow THE MODEL".  Both are reported.
REF = "sa_des_rate"


# ------------------------------------------------------------------ episode cutting

def episodes(S, vlo=0.0, vhi=99.0):
    """Return a list of dicts, one per desired-rate transient inside an engaged run."""
    FS = S["FS"]
    idx, rid, rs = IC.run_index(S, vlo, vhi, minlen_s=0.5)
    eps = []
    merge_n = int(round(MERGE_S * FS))
    pre, post = int(round(PRE_S * FS)), int(round(POST_S * FS))
    for a, b in rs:
        rd = S[REF][a:b]
        hot = np.abs(rd) > RATE_FLOOR_DPS
        sgn = np.sign(rd)
        i = 0
        n = b - a
        while i < n:
            if not hot[i]:
                i += 1
                continue
            s0 = i
            sg = sgn[i]
            j = i
            gap = 0
            while j + 1 < n:
                if hot[j + 1] and sgn[j + 1] == sg:
                    j += 1
                    gap = 0
                elif gap < merge_n and sgn[j + 1] != -sg:
                    j += 1
                    gap += 1
                else:
                    break
            j -= gap
            if (j - s0 + 1) / FS >= MIN_EP_S:
                w0, w1 = max(a, a + s0 - pre), min(b, a + j + 1 + post)
                pk = float(np.max(np.abs(rd[s0:j + 1])))
                dur = (j - s0 + 1) / FS
                eps.append(dict(i0=a + s0, i1=a + j + 1, w0=w0, w1=w1, peak=pk,
                                sign=float(sg), dur=dur, fchar=0.5 / max(dur, 1e-6),
                                exc=float(abs(S[REF[:-5]][a + j] - S[REF[:-5]][a + s0])),
                                v=float(np.mean(S["v"][a + s0:a + j + 1])),
                                ang=float(np.mean(np.abs(S["sa"][a + s0:a + j + 1])))))
            i = j + 1
    return eps


def _xcorr_lag_gain(rd, ra, FS):
    """Lag (s) and lag-aligned gain.  rd/ra are the desired/achieved rate over the padded window.

    FIXED-OVERLAP correlation: the desired segment is held constant at indices [K, n-K) for every
    trial lag, so the number of paired samples does not change with the lag.  A sliding-overlap
    xcorr biases the peak (measured: 25 ms low on a 0.1 Hz sinusoid, control P2) because truncating
    a partial cycle changes the correlation as much as the lag does.
    """
    lo, hi = int(round(LAG_MIN_S * FS)), int(round(LAG_MAX_S * FS))
    K = max(abs(lo), abs(hi))
    n = len(rd)
    if n < 2 * K + 40:
        return np.nan, np.nan
    base = slice(K, n - K)
    x = rd[base] - rd[base].mean()
    sxx = float(np.sum(x * x))
    if sxx <= 0:
        return np.nan, np.nan
    vals = {}
    best, bl = -np.inf, 0
    for L in range(lo, hi + 1):
        y = ra[K + L:n - K + L]
        y = y - y.mean()
        den = np.sqrt(sxx * np.sum(y * y))
        c = float(np.sum(x * y) / den) if den > 0 else -np.inf
        vals[L] = c
        if c > best:
            best, bl = c, L
    lag = float(bl)
    if lo < bl < hi:
        y0, y1, y2 = vals[bl - 1], vals[bl], vals[bl + 1]
        den = (y0 - 2 * y1 + y2)
        if np.isfinite(den) and np.isfinite(y0) and np.isfinite(y2) and den != 0:
            cand = bl - 0.5 * (y2 - y0) / den
            if np.isfinite(cand) and lo <= cand <= hi:
                lag = float(cand)
    if not np.isfinite(lag):
        return np.nan, np.nan
    L = int(round(lag))
    y = ra[K + L:n - K + L]
    g = float(np.sum(x * (y - y.mean())) / sxx)
    return lag / FS, g


def measure(S, eps):
    """Attach lag / gain / peak-ratio to each episode."""
    FS = S["FS"]
    out = []
    for e in eps:
        rd = S[REF][e["w0"]:e["w1"]]
        ra = S["sa_rate"][e["w0"]:e["w1"]]
        lag, g = _xcorr_lag_gain(rd, ra, FS)
        L = int(round(lag * FS)) if np.isfinite(lag) else 0
        a0, a1 = e["i0"] + L, e["i1"] + L
        a0, a1 = max(a0, e["w0"]), min(a1, e["w1"])
        if a1 - a0 < 5:
            a0, a1 = e["i0"], e["i1"]
        rda = S[REF][e["i0"]:e["i1"]]
        raa = S["sa_rate"][a0:a1]
        pk = float(np.max(np.abs(raa)) / max(np.max(np.abs(rda)), 1e-9))
        p95r = float(np.percentile(np.abs(raa), 95) / max(np.percentile(np.abs(rda), 95), 1e-9))
        e = dict(e, lag=lag, gain=g, peakratio=pk, p95ratio=p95r)
        if np.isfinite(lag) and np.isfinite(g):
            out.append(e)
    return out


# ------------------------------------------------------------------ reporting

def _classes(eps):
    pk = np.array([e["peak"] for e in eps])
    b1, b2 = np.percentile(pk, PCTL)
    return b1, b2


def report(S, label, quiet=False):
    allep = measure(S, episodes(S))
    if not allep:
        print("  no episodes")
        return {}
    b1, b2 = _classes(allep)
    if not quiet:
        IC.banner(f"INSTRUMENT 2  RATE TRACKING   {label}")
        print(f"  {len(allep)} episodes from {S['engaged_all'].sum()/S['FS']:.0f} s engaged.  "
              f"Episode = |rate_des| > {RATE_FLOOR_DPS} deg/s, single sign, >= {MIN_EP_S}s, merged over {MERGE_S}s.")
        print(f"  SIZE CLASSES (percentiles {PCTL[0]:.0f} / {PCTL[1]:.0f} of episode peak |rate_des|):")
        print(f"     SMALL   peak <  {b1:6.2f} deg/s")
        print(f"     MEDIUM  peak {b1:6.2f} - {b2:6.2f} deg/s")
        print(f"     LARGE   peak >  {b2:6.2f} deg/s")
        print(f"  peak |rate_des| distribution: p10 {np.percentile([e['peak'] for e in allep],10):.1f}  "
              f"p50 {np.percentile([e['peak'] for e in allep],50):.1f}  "
              f"p90 {np.percentile([e['peak'] for e in allep],90):.1f}  "
              f"max {max(e['peak'] for e in allep):.1f} deg/s")
    out = {}

    def block(title, sel_eps):
        if not quiet:
            print(f"\n  {title}")
            print(f"    {'class':>8} {'n_ep':>5} {'med peak':>9} {'dur s':>7} {'exc deg':>8} "
                  f"{'f_char':>7} {'gain':>8} {'boot95':>8} {'split':>13} {'lag s':>8} {'boot95':>8} "
                  f"{'peakratio':>10} {'boot95':>8} {'p95ratio':>9} {'med|ang|':>9}")
        for cname, lo, hi in (("SMALL", -1, b1), ("MEDIUM", b1, b2), ("LARGE", b2, 1e9)):
            E = [e for e in sel_eps if lo <= e["peak"] < hi]
            if not E:
                continue
            gv = np.array([e["gain"] for e in E])
            lv = np.array([e["lag"] for e in E])
            pv = np.array([e["peakratio"] for e in E])
            qv = np.array([e["p95ratio"] for e in E])
            gid = np.arange(len(E))          # bootstrap unit = the EPISODE
            _, _, _, ghw = IC.boot_ci(gv, gid, lambda x: float(np.median(x)))
            _, _, _, lhw = IC.boot_ci(lv, gid, lambda x: float(np.median(x)))
            ga, gb, _ = IC.split_half(gv, gid, lambda x: float(np.median(x)))
            _, _, _, phw = IC.boot_ci(pv, gid, lambda x: float(np.median(x)))
            flag = "" if len(E) >= 20 else "  <-- THIN"
            if not quiet:
                print(f"    {cname:>8} {len(E):5d} {np.median([e['peak'] for e in E]):9.2f} "
                      f"{np.median([e['dur'] for e in E]):7.2f} {np.median([e['exc'] for e in E]):8.2f} "
                      f"{np.median([e['fchar'] for e in E]):7.2f} "
                      f"{np.median(gv):8.3f} {ghw:8.3f} {f'{ga:.2f}/{gb:.2f}':>13} "
                      f"{np.median(lv):8.3f} {lhw:8.3f} {np.median(pv):10.3f} {phw:8.3f} "
                      f"{np.median(qv):9.3f} {np.median([e['ang'] for e in E]):9.1f}{flag}")
            out[f"{title}|{cname}"] = dict(n=len(E), gain=float(np.median(gv)), gain_ci=ghw,
                                           lag=float(np.median(lv)), lag_ci=lhw,
                                           peakratio=float(np.median(pv)), peak_ci=phw,
                                           p95ratio=float(np.median(qv)),
                                           dur=float(np.median([e["dur"] for e in E])),
                                           exc=float(np.median([e["exc"] for e in E])),
                                           fchar=float(np.median([e["fchar"] for e in E])),
                                           peak=float(np.median([e["peak"] for e in E])))

    block("ALL SPEEDS", allep)

    # FREQUENCY-MATCHED block: fixed absolute f_char edges, so two routes can be compared without
    # the peak-rate size class silently comparing a slow ramp on one against a fast wiggle on the
    # other (control P4).  THIS is the block to use for a build-vs-build comparison.
    if not quiet:
        print(f"\n  FREQUENCY-MATCHED (fixed f_char edges -- use THIS to compare two builds)")
        print(f"    {'f_char band':>14} {'n_ep':>5} {'med peak':>9} {'gain':>8} {'boot95':>8} "
              f"{'lag s':>8} {'boot95':>8} {'peakratio':>10} {'boot95':>8}")
        for flo, fhi in ((0.0, 0.4), (0.4, 0.8), (0.8, 1.6), (1.6, 99.0)):
            E = [e for e in allep if flo <= e["fchar"] < fhi]
            if len(E) < 5:
                continue
            gv = np.array([e["gain"] for e in E]); lv = np.array([e["lag"] for e in E])
            pv = np.array([e["peakratio"] for e in E]); gid = np.arange(len(E))
            _, _, _, ghw = IC.boot_ci(gv, gid, lambda x: float(np.median(x)))
            _, _, _, lhw = IC.boot_ci(lv, gid, lambda x: float(np.median(x)))
            _, _, _, phw = IC.boot_ci(pv, gid, lambda x: float(np.median(x)))
            flag = "" if len(E) >= 20 else "  <-- THIN"
            print(f"    {f'{flo:.1f}-{fhi:.1f} Hz':>14} {len(E):5d} "
                  f"{np.median([e['peak'] for e in E]):9.2f} {np.median(gv):8.3f} {ghw:8.3f} "
                  f"{np.median(lv):8.3f} {lhw:8.3f} {np.median(pv):10.3f} {phw:8.3f}{flag}")
            out[f"FCHAR|{flo}-{fhi}"] = dict(n=len(E), gain=float(np.median(gv)), gain_ci=ghw,
                                             lag=float(np.median(lv)), lag_ci=lhw,
                                             peakratio=float(np.median(pv)), peak_ci=phw)

    # SURROGATE NULL: the achieved-rate trace circularly shifted by 37 s.  Any part of peakratio that
    # is ambient road/plant activity rather than a response to THIS demand survives the shift.
    if not quiet:
        Sn = dict(S)
        sh = int(round(37.0 * S["FS"]))
        Sn["sa_rate"] = np.roll(S["sa_rate"], sh)
        nullep = measure(Sn, episodes(S))
        if nullep:
            gv = np.array([e["gain"] for e in nullep])
            pv = np.array([e["peakratio"] for e in nullep])
            qv = np.array([e["p95ratio"] for e in nullep])
            print(f"\n  SURROGATE NULL (achieved rate circularly shifted 37 s, same episodes): "
                  f"n={len(nullep)}  gain {np.median(gv):+.3f}  peakratio {np.median(pv):.3f}  "
                  f"p95ratio {np.median(qv):.3f}")
            print(f"    -> gain must collapse toward 0; whatever peakratio remains here is ambient "
                  f"plant/road activity, NOT a response to the demand.  Subtract it mentally.")
            out["SURROGATE_NULL"] = dict(n=len(nullep), gain=float(np.median(gv)),
                                         peakratio=float(np.median(pv)), p95ratio=float(np.median(qv)))
    for vlo, vhi in IC.SPEED_BINS:
        E = [e for e in allep if vlo <= e["v"] < vhi]
        if len(E) >= 5:
            block(f"speed {vlo:.0f}-{vhi:.0f} m/s", E)
    return out


# ------------------------------------------------------------------ controls

def _synth_base(n=120000, FS=100.0, seed=3):
    """A desired-angle trace with transients spanning three decades of rate."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / FS
    des = np.zeros(n)
    # sum of sines: slow lane-centring + mid corrections + fast transients
    for f, a in ((0.05, 25.0), (0.13, 9.0), (0.31, 3.0), (0.7, 1.2), (1.4, 0.4)):
        des += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))
    # plus discrete large steps (smoothed), to populate the LARGE class
    for k in range(40):
        c = rng.integers(2000, n - 2000)
        w = int(rng.integers(30, 120))
        amp = rng.uniform(-40, 40)
        ramp = np.clip((np.arange(n) - c) / w, 0, 1)
        des += amp * (3 * ramp ** 2 - 2 * ramp ** 3) * np.exp(-np.abs(np.arange(n) - c) / 900.0)
    return t, des


def _build(des, act, FS=100.0):
    S = IC.synth(n=len(des), FS=FS)
    S["sa"] = act
    S["laa"] = S["Sv"] * act
    S["lad"] = S["Sv"] * des
    IC.add_rates(S)
    return S


def run_controls():
    IC.banner("INSTRUMENT 2  CONTROLS")
    FS = 100.0
    t, des = _synth_base(FS=FS)
    fails = []

    # P3 identity
    S = _build(des, des.copy(), FS)
    r = report(S, "P3 identity", quiet=True)
    for k, v in r.items():
        if not k.startswith("ALL"):
            continue
        ok = abs(v["gain"] - 1.0) <= 0.005 and abs(v["lag"]) <= 0.010
        print(f"  P3 identity      {k.split('|')[1]:>7}: gain {v['gain']:.4f} (exp 1.000+/-0.005)  "
              f"lag {v['lag']:+.4f}s (exp 0.000+/-0.010)  n={v['n']}  {'PASS' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"P3 {k}")

    # P1 pure delay + gain
    D = int(round(0.30 * FS))
    act = np.concatenate([np.full(D, des[0]), des[:-D]]) * 0.80
    S = _build(des, act, FS)
    r = report(S, "P1 delay+gain", quiet=True)
    for k, v in r.items():
        if not k.startswith("ALL"):
            continue
        ok = abs(v["gain"] - 0.80) <= 0.030 and abs(v["lag"] - 0.30) <= 0.020
        print(f"  P1 delay 0.30 gain 0.80  {k.split('|')[1]:>7}: gain {v['gain']:.4f} "
              f"lag {v['lag']:+.4f}s  n={v['n']}  {'PASS' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"P1 {k}")

    # P2 single-frequency first-order lag -- EXACT theory
    tau = 0.25
    print(f"\n  P2  single-frequency 1-pole lag, tau = {tau} s   (exact theory)")
    print(f"     {'f Hz':>6} {'amp deg':>8} {'gain':>8} {'|H| exp':>8} {'lag s':>8} {'phase-delay exp':>16} {'n_ep':>5}")
    for f, amp in ((0.10, 40.0), (0.30, 14.0), (1.00, 4.0)):
        d = amp * np.sin(2 * np.pi * f * t)
        al = (1.0 / FS) / (tau + 1.0 / FS)
        a_ = np.empty_like(d); x = d[0]
        for i, u in enumerate(d):
            x += al * (u - x); a_[i] = x
        Sx = _build(d, a_, FS)
        rr = report(Sx, "", quiet=True)
        v = [vv for kk, vv in rr.items() if kk.startswith("ALL")]
        g = float(np.median([x_["gain"] for x_ in v])); lg = float(np.median([x_["lag"] for x_ in v]))
        nn = sum(x_["n"] for x_ in v)
        w = 2 * np.pi * f
        Hm = 1.0 / np.sqrt(1.0 + (w * tau) ** 2)
        pd = np.arctan(w * tau) / w
        okg, okl = abs(g - Hm) <= 0.03 * max(Hm, 0.2), abs(lg - pd) <= 0.020
        print(f"     {f:6.2f} {amp:8.1f} {g:8.4f} {Hm:8.4f} {lg:8.4f} {pd:16.4f} {nn:5d}  "
              f"{'PASS' if (okg and okl) else 'FAIL'}")
        if not (okg and okl):
            fails.append(f"P2 f={f}")

    # P4 broadband 1-pole: the amplitude/frequency confound, demonstrated
    al = (1.0 / FS) / (tau + 1.0 / FS)
    act = np.empty_like(des); x = des[0]
    for i, u in enumerate(des):
        x += al * (u - x); act[i] = x
    S = _build(des, act, FS)
    eps = measure(S, episodes(S))
    gv = np.array([e["gain"] for e in eps]); fv = np.array([e["fchar"] for e in eps])
    from scipy.stats import spearmanr
    rho = float(spearmanr(fv, gv).statistic)
    r = report(S, "P4", quiet=True)
    got = {k.split("|")[1]: v for k, v in r.items() if k.startswith("ALL")}
    print(f"\n  P4  broadband 1-pole tau=0.25: gain by PEAK-RATE class "
          f"SMALL {got['SMALL']['gain']:.3f} (f_char {got['SMALL']['fchar']:.2f}) / "
          f"MEDIUM {got['MEDIUM']['gain']:.3f} ({got['MEDIUM']['fchar']:.2f}) / "
          f"LARGE {got['LARGE']['gain']:.3f} ({got['LARGE']['fchar']:.2f})")
    print(f"      -> the peak-rate class ORDERING IS THE OPPOSITE of the frequency ordering. "
          f"Spearman(f_char, gain) = {rho:+.3f}  {'PASS' if rho < -0.3 else 'FAIL'}")
    print(f"      READ f_char, NOT the class name, when comparing gains.")
    if not (rho < -0.3):
        fails.append("P4")

    assert not fails, f"CONTROL FAILURES: {fails}"
    print("\n  ALL CONTROLS PASS -- gain and lag are recovered and are separable.")


if __name__ == "__main__":
    run_controls()
    if len(sys.argv) > 1:
        S = IC.load(sys.argv[1])
        IC.banner(f"angle map for {S['tag']}")
        IC.fit_S(S)
        IC.add_rates(S)
        out = report(S, f"{sys.argv[1]}  vs its own SETPOINT (post ref-filter)  [rev 5 baseline if r76]")
        globals()["REF"] = "sa_mod_rate"
        out2 = report(S, f"{sys.argv[1]}  vs THE MODEL DEMAND (desiredCurvature*v^2, pre ref-filter)")
        out = {"vs_setpoint": out, "vs_model": out2}
        IC.dump_json(f"instr_rate_tracking_{sys.argv[1].replace('/','_')}.json", out)
