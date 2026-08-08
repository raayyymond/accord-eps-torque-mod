#!/usr/bin/env python3
"""T4f -- isolate and characterise route 67's HIGHWAY LIMIT-CYCLE EVENTS, and redo T5b's
turn-direction test with the steering offset removed.

WHY THIS FILE EXISTS
  T4a showed V81's >80 km/h band envelopes with enormous upper CIs (e_26-31 = 63.2 counts with a
  97.5% bound of 1707) over only 6 blocks: the highway energy is CONCENTRATED IN A MINORITY OF
  WINDOWS, so a median over the stratum understates it by more than an order of magnitude. T4b then
  found exactly one clean >80 km/h disengagement whose pre-edge 18-31 Hz p90 envelope was 2469
  counts -- V80-magnitude. This file finds every such burst, times it, and identifies its line.

  T5b's yawRate check returned NaN (openpilot does not populate carState.yawRate on this car), so
  the turn-direction verdict there is VOID. The sign convention is re-established here from the
  WHEEL SPEEDS -- in a left turn the right-hand wheels travel further -- and the steering ZERO
  OFFSET is estimated and removed before any left/right split, because a ~4 deg offset alone put
  407 windows in the "left" pool and 40 in the "right" pool.

🛑 fs = 100.5 Hz, so every f below is indistinguishable from 100.5 - f.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _grind2_lib as G  # noqa: E402
import _r31_common as C31  # noqa: E402
from r67_v81_t4t5 import (BANDS, CIRC, ORDER, ROUTES, env, hdr, lowpass,  # noqa: E402
                          medspec, ratio_null, runs_of, segs, top_lines, windows, col)

KMH = 1.0 / 3.6
NFFT = G.NFFT
BURST_BAND = (18.0, 31.0)     # the band that carries both the 21 Hz and the 27.9 Hz mode
OUT = {}


def smooth(x, fs, win=0.25):
    """Boxcar over `win` seconds. 🛑 REQUIRED: the analytic envelope of a 13 Hz-wide band BEATS --
    it dips to zero between components several times a second, so a bare `env > thr` test yields
    hundreds of 1-sample runs and NO run survives a 0.5 s minimum. The first cut of this file
    reported '0 bursts on every build' for exactly that reason, while T4b was simultaneously
    measuring a 2469-count pre-disengagement envelope."""
    n = max(3, int(win * fs))
    k = np.ones(n) / n
    y = np.asarray(x, float).copy()
    bad = ~np.isfinite(y)
    if bad.any():
        y[bad] = 0.0
    return np.convolve(y, k, mode="same")


def burst_events(build, thr=400.0, minlen=0.4, band=BURST_BAND):
    """Contiguous runs where the SMOOTHED 18-31 Hz torsion-bar envelope exceeds `thr` counts."""
    ev = []
    for s, d in segs(build):
        fs = C31.fs_of(d)
        e = smooth(env(d["tq"], fs, *band), fs)
        lat = d["cc_lat"] > 0.5
        tq_lf = np.abs(lowpass(d["tq"], fs))
        for a, b in runs_of(e > thr):
            if (b - a) / fs < minlen:
                continue
            sl = slice(a, b)
            ev.append(dict(
                build=build, seg=int(s), t0=float(d["t"][a]), t1=float(d["t"][b - 1]),
                dur=float((b - a) / fs), peak=float(np.max(e[sl])), p90=float(np.percentile(e[sl], 90)),
                v=float(np.mean(np.abs(d["cs_v"][sl]))), vmax=float(np.max(np.abs(d["cs_v"][sl]))),
                lat=float(lat[sl].mean()), eff=float(np.median(tq_lf[sl])),
                ang=float(np.mean(np.abs(d["ang"][sl]))),
                lchg=float(np.max(d["cs_lchg"][sl])) if "cs_lchg" in d else np.nan,
                brake=float(np.mean(d["cs_brake"][sl] > 0.5)) if "cs_brake" in d else np.nan,
                i0=int(a), i1=int(b), fs=float(fs)))
    return ev


def event_spectrum(build, seg, i0, i1, pad=0):
    """Welch-style median periodogram over 2.56 s sub-blocks of one event (hop 64)."""
    cache, pfx, _, _ = ROUTES[build]
    d = {k: v for k, v in np.load(cache / f"{pfx}{seg}.npz").items()}
    fs = C31.fs_of(d)
    x = np.asarray(d["tq"], float)
    a, b = max(0, i0 - pad), min(len(x), i1 + pad)
    if b - a < NFFT:
        c = (a + b) // 2
        a, b = max(0, c - NFFT // 2), max(0, c - NFFT // 2) + NFFT
        if b > len(x):
            return None
    Ps = []
    f = np.fft.rfftfreq(NFFT, 1 / fs)
    for i in range(a, b - NFFT + 1, 64):
        P = C31.periodogram(x[i:i + NFFT], fs, NFFT, True)
        if P is not None:
            Ps.append(P)
    if not Ps:
        return None
    P = np.median(np.array(Ps), axis=0)
    R = G.prom_spectrum(f, P)
    f0, prom = G.locate(f, P, 5.0, 49.0, R=R)
    return dict(f=f, P=P, R=R, f0=f0, prom=prom, Q=G.q_of(f, P, f0), nblk=len(Ps),
                pp=float(2 * np.percentile(env(x[a:b], fs, *BURST_BAND), 99)))


def main():
    hdr("T4f-1  BURST CENSUS -- contiguous runs with the 18-31 Hz torsion-bar envelope > 400 ct\n"
        "       (i.e. >= 800 counts peak-to-peak), at least 0.5 s long.")
    ALL = {}
    print(f"  {'build':10s} {'n':>4s} {'tot s':>7s} {'eng%':>5s} | "
          f"{'longest s':>9s} {'peak ct':>8s} | at >80 km/h: n / tot s / longest / peak")
    for b in ORDER:
        ev = burst_events(b)
        ALL[b] = ev
        if not ev:
            print(f"  {b:10s}    0")
            continue
        hw = [e for e in ev if e["v"] >= 80 * KMH]
        print(f"  {b:10s} {len(ev):4d} {sum(e['dur'] for e in ev):7.1f} "
              f"{100 * np.mean([e['lat'] for e in ev]):5.1f} | "
              f"{max(e['dur'] for e in ev):9.2f} {max(e['peak'] for e in ev):8.0f} | "
              f"{len(hw):3d} / {sum(e['dur'] for e in hw):6.1f} s / "
              f"{max((e['dur'] for e in hw), default=0):5.2f} s / "
              f"{max((e['peak'] for e in hw), default=0):7.0f}")
        OUT.setdefault("census", {})[b] = dict(
            n=len(ev), tot=sum(e["dur"] for e in ev),
            eng=float(np.mean([e["lat"] for e in ev])),
            longest=max(e["dur"] for e in ev), peak=max(e["peak"] for e in ev),
            hw_n=len(hw), hw_tot=sum(e["dur"] for e in hw))

    hdr("T4f-2  THE TOP ROUTE-67 EVENTS by peak envelope -- what they are, and their spectra.")
    ev67 = sorted(ALL["V81/r67"], key=lambda e: -e["peak"])[:12]
    print(f"  {'seg':>3s} {'t0..t1 (s)':>16s} {'dur':>6s} {'peak':>7s} {'p90':>7s} "
          f"{'v kmh':>7s} {'eng':>4s} {'eff':>6s} {'|ang|':>6s} {'blink':>5s} {'brk':>4s} | "
          f"{'f0':>6s} {'prom':>7s} {'Q':>5s} {'pp ct':>7s}")
    OUT["top"] = []
    for e in ev67:
        sp = event_spectrum(e["build"], e["seg"], e["i0"], e["i1"], pad=64)
        f0 = sp["f0"] if sp else np.nan
        pr = sp["prom"] if sp else np.nan
        q = sp["Q"] if sp else np.nan
        pp = sp["pp"] if sp else np.nan
        print(f"  {e['seg']:3d} {e['t0']:7.2f}..{e['t1']:7.2f} {e['dur']:6.2f} {e['peak']:7.0f} "
              f"{e['p90']:7.0f} {e['v'] * 3.6:7.1f} {e['lat']:4.2f} {e['eff']:6.0f} "
              f"{e['ang']:6.1f} {e['lchg']:5.1f} {e['brake']:4.1f} | {f0:6.2f} {pr:7.2f} "
              f"{q:5.1f} {pp:7.0f}")
        OUT["top"].append(dict(seg=e["seg"], t0=e["t0"], t1=e["t1"], dur=e["dur"],
                               peak=e["peak"], v=e["v"] * 3.6, lat=e["lat"], eff=e["eff"],
                               lchg=e["lchg"], brake=e["brake"], f0=float(f0), prom=float(pr),
                               Q=float(q), pp=float(pp)))

    hdr("T4f-3  THE HIGHWAY EVENT(S) IN FULL -- every route-67 burst above 80 km/h, with the\n"
        "       envelope trace either side and the engagement state through it.")
    hw = sorted([e for e in ALL["V81/r67"] if e["v"] >= 80 * KMH], key=lambda e: -e["peak"])
    OUT["hw"] = []
    for e in hw[:6]:
        cache, pfx, _, _ = ROUTES["V81/r67"]
        d = {k: v for k, v in np.load(cache / f"{pfx}{e['seg']}.npz").items()}
        fs = C31.fs_of(d)
        en = smooth(env(d["tq"], fs, *BURST_BAND), fs)
        lat = d["cc_lat"] > 0.5
        W = int(6 * fs)
        a, b = max(0, e["i0"] - W), min(len(en), e["i1"] + W)
        sp = event_spectrum("V81/r67", e["seg"], e["i0"], e["i1"], pad=64)
        print(f"\n  seg{e['seg']}  t {e['t0']:.2f}..{e['t1']:.2f} s  dur {e['dur']:.2f} s  "
              f"peak {e['peak']:.0f} ct (pp {2 * e['peak']:.0f})  v {e['v'] * 3.6:.1f} km/h  "
              f"engaged {100 * e['lat']:.0f}%  blinker {e['lchg']:.0f}  "
              f"driver |tq_lf| {e['eff']:.0f} ct")
        if sp:
            print(f"       f0 = {sp['f0']:.2f} Hz (prominence {sp['prom']:.1f}, Q {sp['Q']:.1f}) "
                  f"over {sp['nblk']} sub-blocks; alias twin {100.5 - sp['f0']:.2f} Hz")
            print("       top lines: "
                  + "  ".join(f"{x:5.2f} ({p:5.2f})" for x, p in top_lines(sp["f"], sp["R"], 5)))
            print(f"       wheel order 1 at this speed = {e['v'] / CIRC:.2f} Hz, "
                  f"order 2 = {2 * e['v'] / CIRC:.2f} Hz")
        # envelope trace at 1 s resolution around the event
        tr = []
        for k in range(a, b, int(fs)):
            sl = slice(k, min(k + int(fs), b))
            tr.append((float(d["t"][k] - e["t0"]), float(np.percentile(en[sl], 90)),
                       float(lat[sl].mean()), float(np.mean(np.abs(d["cs_v"][sl])) * 3.6)))
        print("       t-t0 / env90 / engaged / kmh : "
              + "  ".join(f"{a_:+5.1f}:{b_:6.0f}:{c_:3.1f}:{v_:5.1f}" for a_, b_, c_, v_ in tr))
        OUT["hw"].append(dict(seg=e["seg"], t0=e["t0"], dur=e["dur"], peak=e["peak"],
                              v=e["v"] * 3.6, lat=e["lat"],
                              f0=float(sp["f0"]) if sp else None,
                              prom=float(sp["prom"]) if sp else None,
                              trace=tr))

    hdr("T4f-4  IS ROUTE 67's HIGHWAY LINE THE SAME LINE AS V80's?  Both located on their own\n"
        "       >80 km/h bursts with the identical estimator.")
    for b in ("V81/r67", "V80/r66"):
        hwb = sorted([e for e in ALL[b] if e["v"] >= 80 * KMH], key=lambda e: -e["peak"])[:8]
        f0s, proms, pps, vs = [], [], [], []
        for e in hwb:
            sp = event_spectrum(b, e["seg"], e["i0"], e["i1"], pad=64)
            if sp and np.isfinite(sp["f0"]):
                f0s.append(sp["f0"]); proms.append(sp["prom"])
                pps.append(sp["pp"]); vs.append(e["v"] * 3.6)
        if not f0s:
            print(f"  {b:10s} -- no >80 km/h burst")
            continue
        print(f"  {b:10s} n={len(f0s)}  f0 median {np.median(f0s):6.2f} Hz  "
              f"[{np.min(f0s):.2f}, {np.max(f0s):.2f}]   prominence median {np.median(proms):7.1f}"
              f"   p-p median {np.median(pps):8.0f} ct   v {np.median(vs):.1f} km/h")
        OUT.setdefault("line", {})[b] = dict(f0=list(map(float, f0s)),
                                             prom=list(map(float, proms)),
                                             pp=list(map(float, pps)))

    hdr("T5b-REDO  TURN DIRECTION, with the steering ZERO OFFSET removed and the sign\n"
        "          convention taken from the WHEEL SPEEDS (left turn => right wheels faster).")
    W = {"V81/r67": windows("V81/r67")}
    cache, pfx, ss, parked = ROUTES["V81/r67"]
    num = den = 0.0
    offs = []
    for s, d in segs("V81/r67"):
        fs = C31.fs_of(d)
        rl = np.gradient(lowpass(d["ang"], fs)) * fs
        straight = (np.abs(d["cs_v"]) > 40 * KMH) & (np.abs(rl) < 1.0)
        if straight.sum() > 200:
            offs.append(float(np.median(d["ang"][straight])))
        turn = (np.abs(d["ang"]) > 15) & (np.abs(d["cs_v"]) > 2.0)
        if turn.sum() > 100:
            dw = (d["ws_fr"] - d["ws_fl"])[turn]
            num += float(np.nansum(np.sign(d["ang"][turn]) * dw))
            den += float(np.nansum(np.abs(dw)))
    offset = float(np.median(offs)) if offs else 0.0
    print(f"  steering zero offset (median angle while straight above 40 km/h, per segment): "
          f"{offset:+.2f} deg   [{np.min(offs):+.2f}, {np.max(offs):+.2f}] over {len(offs)} segs")
    print(f"  sign( angle ) . ( ws_fr - ws_fl ) summed over |angle| > 15 deg: {num / den:+.3f}")
    LEFTPOS = num / den > 0
    print(f"  => a POSITIVE steering angle is a {'LEFT' if LEFTPOS else 'RIGHT'} turn "
          f"[EVIDENCE: outer (right) wheels run faster in a left turn]")
    OUT["sign"] = dict(offset=offset, ws_score=num / den, left_is_positive=bool(LEFTPOS))

    rs = [r for r in W["V81/r67"] if r["eng"] == 1]
    for r in rs:
        r["angc"] = r["angs"] - offset
    for lab, sel in (("turning, |angle| > 10 deg", lambda r: abs(r["angc"]) > 10),
                     ("low-speed turning", lambda r: abs(r["angc"]) > 10 and r["v"] < 15 * KMH),
                     ("cruise turning", lambda r: abs(r["angc"]) > 10 and r["v"] >= 15 * KMH)):
        pool = [r for r in rs if sel(r)]
        L = [r for r in pool if (r["angc"] > 0) == LEFTPOS]
        Rt = [r for r in pool if (r["angc"] > 0) != LEFTPOS]
        print(f"\n  {lab:26s} n left {len(L)}  right {len(Rt)}")
        if len(L) < 8 or len(Rt) < 8:
            print("     -- too few for a direction test")
            continue
        print(f"     |angle-offset| median  left {np.median(np.abs(col(L,'angc'))):6.1f} deg  "
              f"right {np.median(np.abs(col(Rt,'angc'))):6.1f} deg   "
              f"speed left {np.median(col(L,'v'))*3.6:5.1f} right "
              f"{np.median(col(Rt,'v'))*3.6:5.1f} km/h")
        for k in ("6-9", "18-22", "26-31", "40-49"):
            (ra, lo, hi), nl = ratio_null(Rt, L, "e_" + k)
            v = ("OUTSIDE null" if (np.isfinite(nl[1]) and (ra < nl[1] or ra > nl[2]))
                 else "inside null")
            print(f"     {k:6s} RIGHT/LEFT {ra:6.3f} [{lo:6.3f},{hi:6.3f}]  "
                  f"null [{nl[1]:6.3f},{nl[2]:6.3f}]  {v}")
            OUT.setdefault("t5b", {})[f"{lab}|{k}"] = dict(ratio=[ra, lo, hi], null=list(nl),
                                                           n=[len(Rt), len(L)])

    (ROOT / "_cache_r67x" / "r67_t4f.json").write_text(
        json.dumps(OUT, indent=1, default=lambda o: str(o)))
    print(f"\nwrote {ROOT / '_cache_r67x' / 'r67_t4f.json'}")


if __name__ == "__main__":
    main()
