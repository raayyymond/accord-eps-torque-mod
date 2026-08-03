#!/usr/bin/env python3
"""THE >28 m/s LANE -- where the events actually are, and the one place the order test is well posed.

`highway_imu_followup.py` established that the IMU 30-49 Hz events concentrate ABOVE 28 m/s:
15/17 (ay), 14/15 (gz), 13/13 (gx). It also established the confound: 627.8 s of the corpus's
786.2 s above 28 m/s (79.9%) is ONE route, 47 / V67, and the Kd=1 pool holds 39.3 s (5.0%).

🛑 WHY THE ORDER TEST IS ONLY WELL POSED HERE. A 40-49 Hz detector run over 12-33 m/s cannot
falsify "wheel order 3": order 3 spans 17.3 Hz at 12 m/s to 48.2 Hz at 33.4, so over most of that
range the order line is OUTSIDE the band and the band edge, not the physics, sets f0. A flat
f0-vs-speed slope inside a 9 Hz band is therefore NOT evidence of a mode -- the previous section's
"MODE" verdicts on 30-40 and 40-49 are band-censored and are withdrawn here.
   Above 28 m/s the geometry inverts. Order 3 runs 40.4 Hz (28.0 m/s) to 48.2 Hz (33.4 m/s) -- a
7.8 Hz sweep entirely INSIDE the band, resolvable at 0.39 Hz bins. So restricted to v > 28 the
test has teeth: slope 1.442 Hz/(m/s) = order 3, slope ~0 = a mode.

Sections
  1  the >28 m/s population and its exposure, per route
  2  ORDER TEST over ALL windows (n in the hundreds), not just events -- f0 vs speed
  3  ORDER TEST on the events themselves, IMU and torsion bar
  4  event characterisation at >28: hands-on?, steering rate, LKAS command, rail duty
  5  event RATE by dose above 28 m/s, with the honest power
  6  what precedes an event: 3 s look-back vs matched controls
  7  command <-> bar coherence at the event frequency (grind #1's mechanism was 0.917 at 21.09 Hz)

Usage:  python highway_fast_lane.py
"""
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

import _grind2_lib as G          # noqa: E402
import _r47_imu_lib as I         # noqa: E402
import highway_event_hunt as H   # noqa: E402

RNG = np.random.default_rng(20260803)
OUT = HERE / "_hwy_fast_lane.json"
VFAST = 28.0
CIRC = H.CIRC
NFFT = 256


def poisson_p0(mu):
    return float(np.exp(-mu))


def main():
    store = {}
    runs = H.collect_envelopes("tq")
    irecs = H.collect_imu()
    print(f"[{len(runs)} CAN engagement runs, {len(irecs)} IMU segments]")

    # ============================================================ 1. the population ==============
    G.hdr("1.  THE >28 m/s ENGAGED POPULATION")
    exp_rt, exp_kd = {}, {}
    for r in runs:
        m = r["v"] >= VFAST
        exp_rt[r["route"]] = exp_rt.get(r["route"], 0.0) + float(m.sum()) / r["fs"]
        exp_kd[r["kd"]] = exp_kd.get(r["kd"], 0.0) + float(m.sum()) / r["fs"]
    tot = sum(exp_kd.values())
    for rt in sorted(exp_rt):
        print(f"    route {rt:<4} {H.BUILD[rt]:<5} Kd={H.KD[rt]:.2f}   {exp_rt[rt]:8.1f} s "
              f"({100 * exp_rt[rt] / tot:5.1f}% of the corpus above {VFAST:g} m/s)")
    print(f"    {'':>10}{'':>11}TOTAL   {tot:8.1f} s")
    print(f"\n    Kd pools: " + "   ".join(f"Kd={k:.2f}: {v:.1f} s" for k, v in
                                           sorted(exp_kd.items())))
    store["exposure_fast"] = {"by_route": {k: round(v, 1) for k, v in exp_rt.items()},
                              "by_kd": {str(k): round(v, 1) for k, v in exp_kd.items()}}

    # ============================================================ 2. order test, all windows =====
    G.hdr("2.  ORDER TEST OVER ALL WINDOWS above 22 m/s -- the high-n version.\n"
          "    For every 2.56 s window: the most PROMINENT line in 30-49.5 Hz, vs speed.\n"
          "    order 3 => slope 1.442 Hz/(m/s);  a mode => slope 0.")
    W = []
    for ri, r in enumerate(runs):
        fs, n = r["fs"], len(r["tq"])
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        for i in range(0, n - NFFT + 1, NFFT // 2):
            vv = float(np.mean(r["v"][i:i + NFFT]))
            if vv < 22.0:
                continue
            P = G.periodogram(r["tq"][i:i + NFFT], fs, NFFT, True)
            if P is None:
                continue
            R = G.prom_spectrum(f, P)
            f0, pr = G.locate(f, P, 30.0, 49.5, R=R)
            fl, pl = G.locate(f, P, 8.0, 30.0, R=R)
            W.append(dict(run=ri, i=i, route=r["route"], kd=r["kd"], v=vv, f0=f0, prom=pr,
                          f_lo=fl, prom_lo=pl,
                          eff=float(np.mean(r["eff"][i:i + NFFT])),
                          press=float(np.mean(r["press"][i:i + NFFT] > 0.5)),
                          rate=float(np.max(r["rate"][i:i + NFFT]))))
    print(f"    n = {len(W)} windows, speed {min(w['v'] for w in W):.1f}"
          f"-{max(w['v'] for w in W):.1f} m/s")
    for lab, sub in (("all >22 m/s", W), (">28 m/s only", [w for w in W if w["v"] >= VFAST]),
                     (">28, PROMINENT only (prom>4)",
                      [w for w in W if w["v"] >= VFAST and w["prom"] > 4])):
        if len(sub) < 10:
            print(f"    {lab:<32} n={len(sub)} -- too few")
            continue
        v = np.array([w["v"] for w in sub])
        f0 = np.array([w["f0"] for w in sub])
        s, lo, hi, ic, n = H.theil_sen(v, f0, RNG, 600)
        od = f0 * CIRC / v
        print(f"    {lab:<32} n={n:5d}  slope {s:+7.4f} [{lo:+7.4f},{hi:+7.4f}] "
              f"icpt {ic:6.2f}  f0 p50 {np.median(f0):5.2f}  order p50 {np.median(od):5.2f} "
              f"sd {np.std(od):4.2f}")
        print(f"    {'':32}   order3 slope 1.442 "
              f"{'INSIDE' if lo <= 1.442 <= hi else 'EXCLUDED'};  "
              f"mode slope 0 {'INSIDE' if lo <= 0 <= hi else 'EXCLUDED'}")
        store.setdefault("order_all_windows", {})[lab] = dict(
            n=n, slope=s, lo=lo, hi=hi, icpt=ic, f0_p50=float(np.median(f0)),
            order_p50=float(np.median(od)))
    # the same for the 8-30 Hz line, where the kit already knows 10-16 Hz is wheel order 1
    sub = [w for w in W if w["v"] >= 22.0 and np.isfinite(w["f_lo"])]
    v = np.array([w["v"] for w in sub])
    fl = np.array([w["f_lo"] for w in sub])
    s, lo, hi, ic, n = H.theil_sen(v, fl, RNG, 600)
    print(f"\n    POSITIVE CONTROL -- the 8-30 Hz line (the kit's known wheel order 1):")
    print(f"      n={n}  slope {s:+.4f} [{lo:+.4f},{hi:+.4f}]  order p50 "
          f"{np.median(fl * CIRC / v):.2f}   (order 1 slope = 0.481)")
    store["order_control_8_30"] = dict(n=n, slope=s, lo=lo, hi=hi,
                                       order_p50=float(np.median(fl * CIRC / v)))

    # ============================================================ 3. order test, events ==========
    G.hdr("3.  ORDER TEST ON THE EVENTS THEMSELVES, above 28 m/s")
    ev = []
    for ax, band in (("ay", "40-49"), ("gz", "40-49"), ("gx", "40-49"), ("ay", "30-40"),
                     ("gz", "30-40"), ("az", "30-40")):
        f50 = H.imu_floor(irecs, ax, band, q=50)
        for e in H.imu_events(irecs, ax, band, {i: 10 * f50[i] for i in f50}):
            if e["v"] < VFAST:
                continue
            r = irecs[e["rec"]]
            g = ax[0]
            u = r.get("_u_" + ax)
            if u is None:
                cd = dict((x[0], x[1]) for x in H.ROUTES)[r["route"]]
                pf = dict((x[0], x[2]) for x in H.ROUTES)[r["route"]]
                di = dict(np.load(ROOT / cd / f"{pf}{r['seg']}_imu.npz"))
                u = I.uniform(di["at"] if g == "a" else di["gt"], di[ax])[0]
                r["_u_" + ax] = u
            fs = r[ax + "_odr"]
            a0 = max(0, min(len(u) - NFFT, e["ipk"] - NFFT // 2))
            P = I.periodogram(u[a0:a0 + NFFT], fs, NFFT, True)
            if P is None:
                continue
            f = np.fft.rfftfreq(NFFT, 1 / fs)
            lo_b, hi_b = H.BANDS[band]
            f0, pr = I.locate(f, P, lo_b, hi_b)
            e2 = dict(e)
            e2.update(f0=f0, prom=pr, Q=I.q_of(f, P, f0), order=f0 * CIRC / e["v"],
                      order3=3 * e["v"] / CIRC, axband=f"{ax}|{band}")
            ev.append(e2)
    print(f"    n = {len(ev)} IMU events above {VFAST:g} m/s "
          f"(all axes/bands, before dedupe)")
    if len(ev) >= 8:
        v = np.array([e["v"] for e in ev])
        f0 = np.array([e["f0"] for e in ev])
        s, lo, hi, ic, n = H.theil_sen(v, f0, RNG, 600)
        print(f"    in-band f0 vs speed: slope {s:+.4f} [{lo:+.4f},{hi:+.4f}]  icpt {ic:.2f}  "
              f"f0 p50 {np.median(f0):.2f} Hz sd {np.std(f0):.2f}")
        print(f"      order 3 (slope 1.442): "
              f"{'INSIDE' if lo <= 1.442 <= hi else 'EXCLUDED BY'} the CI")
        print(f"      pure mode (slope 0):   "
              f"{'INSIDE' if lo <= 0 <= hi else 'EXCLUDED BY'} the CI")
        print(f"      per-event implied order: p50 {np.median(f0 * CIRC / v):.2f}  "
              f"sd {np.std(f0 * CIRC / v):.2f}   (a true order 3 would read 3.00 +/- ~0.1)")
        store["order_events_fast"] = dict(n=n, slope=s, lo=lo, hi=hi, icpt=ic,
                                          f0_p50=float(np.median(f0)),
                                          order_p50=float(np.median(f0 * CIRC / v)),
                                          order_sd=float(np.std(f0 * CIRC / v)))

    # ============================================================ 4. characterisation ============
    G.hdr("4.  THE >28 m/s IMU EVENTS, CHARACTERISED (deduped by instant; top 20 by z)")
    dd = []
    for e in sorted(ev, key=lambda x: -x["z"]):
        if any(k["route"] == e["route"] and k["seg"] == e["seg"] and abs(k["t"] - e["t"]) < 1.0
               for k in dd):
            continue
        dd.append(e)
    can = {}
    for rt, cd, pfx, segs, bld, kd in H.ROUTES:
        for s in segs:
            d = H.load_seg(cd, pfx, s)
            if d is not None:
                can[(rt, s)] = d
    print(f"    {len(dd)} distinct instants above {VFAST:g} m/s")
    print(f"{'#':<3}{'rt':<4}{'sg':>4}{'t(s)':>8}{'axis|band':>11}{'amp':>9}{'z':>6}{'dur':>6}"
          f"{'rise':>6}{'f0':>7}{'Q':>6}{'ord':>6}{'v':>6}{'eff':>7}{'prs':>5}{'rate':>7}"
          f"{'ang':>7}{'e4mx':>7}{'rail':>6}{'barHF':>7}")
    rows = []
    for i, e in enumerate(dd[:20]):
        d = can.get((e["route"], e["seg"]))
        cov = {}
        if d is not None:
            fsc = 1.0 / float(np.median(np.diff(d["t"])))
            j = int(np.argmin(np.abs(d["t"] - e["t"])))
            sl = slice(max(0, j - NFFT // 2), max(0, j - NFFT // 2) + NFFT)
            from _r31_common import sustained as _sus
            cov["eff"] = float(np.mean(np.abs(_sus(d["tq"][sl], fsc))))
            cov["press"] = float(np.mean(d.get("cs_press", np.zeros(len(d["t"])))[sl] > 0.5))
            cov["rate"] = float(np.max(np.abs(d["rate_c"][sl])))
            cov["ang"] = float(np.mean(np.abs(d["ang"][sl])))
            cov["e4max"] = float(np.max(np.abs(d["e4tq"][sl])))
            cov["rail"] = float(np.mean(np.abs(d["cc_req"][sl]) > 0.95))
            tap = np.hanning(NFFT) + 1e-3
            cw = slice(int(0.2 * NFFT), int(0.8 * NFFT))
            x = np.asarray(d["tq"][sl], float)
            cov["barhf"] = (G.win_env(x, fsc, 40.0, 49.0, tap, cw) if len(x) == NFFT else np.nan)
        print(f"{i + 1:<3}{e['route']:<4}{e['seg']:>4}{e['t']:>8.1f}{e['axband']:>11}"
              f"{e['amp']:>9.3g}{e['z']:>6.1f}{e['dur']:>6.2f}"
              f"{e['f0']:>7.2f}{e['Q']:>6.1f}{e['order']:>6.2f}"
              f"{e['v']:>6.1f}{cov.get('eff', np.nan):>7.0f}{cov.get('press', np.nan):>5.2f}"
              f"{cov.get('rate', np.nan):>7.1f}{cov.get('ang', np.nan):>7.1f}"
              f"{cov.get('e4max', np.nan):>7.0f}{cov.get('rail', np.nan):>6.2f}"
              f"{cov.get('barhf', np.nan):>7.1f}")
        rows.append({**{k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                        for k, v in e.items() if k not in ("rec",)}, **cov})
    store["fast_events"] = rows
    if rows:
        eff = np.array([r.get("eff", np.nan) for r in rows], float)
        prs = np.array([r.get("press", np.nan) for r in rows], float)
        print(f"\n    HANDS-OFF CHECK over these {len(rows)} events: "
              f"effort |lowpass(tq,3Hz)| p50 {np.nanmedian(eff):.0f} counts "
              f"(kit's hands-off criterion is <= 200); steeringPressed duty p50 "
              f"{np.nanmedian(prs):.2f}; fraction with effort<=200 AND press==0: "
              f"{np.mean((eff <= 200) & (prs < 0.02)):.2f}")

    # ============================================================ 5. rate by dose above 28 =======
    G.hdr("5.  EVENT RATE ABOVE 28 m/s BY DOSE -- and the honest power")
    iexp = {}
    for r in irecs:
        n = min(len(r["a_v"]), len(r["a_lat"]))
        m = (r["a_v"][:n] >= VFAST) & (r["a_lat"][:n] > 0.5)
        iexp[r["kd"]] = iexp.get(r["kd"], 0.0) + float(m.sum()) / r["ax_odr"]
    print(f"    IMU exposure above {VFAST:g} m/s: "
          + "   ".join(f"Kd={k:.2f}: {v:.1f} s" for k, v in sorted(iexp.items())))
    for ax, band in (("ay", "40-49"), ("gz", "40-49"), ("gx", "40-49"), ("ay", "30-40"),
                     ("gz", "30-40")):
        f50 = H.imu_floor(irecs, ax, band, q=50)
        evs = [e for e in H.imu_events(irecs, ax, band, {i: 10 * f50[i] for i in f50})
               if e["v"] >= VFAST]
        cnt = {}
        for e in evs:
            cnt[e["kd"]] = cnt.get(e["kd"], 0) + 1
        r244 = 3600 * cnt.get(2.44, 0) / max(iexp.get(2.44, 1e-9), 1e-9)
        line = "  ".join(f"Kd{k:.2f}: {cnt.get(k, 0):2d} ev / {iexp.get(k, 0):6.1f} s = "
                         f"{3600 * cnt.get(k, 0) / max(iexp.get(k, 1e-9), 1e-9):6.1f}/h"
                         for k in sorted(iexp))
        print(f"\n    {ax} {band:>6} Hz   {line}")
        for k in (1.0, 2.0):
            mu = r244 * iexp.get(k, 0.0) / 3600.0
            print(f"        if Kd={k:.2f} had the SAME rate as V67, it would show "
                  f"{mu:.2f} events in its {iexp.get(k, 0):.0f} s; it shows {cnt.get(k, 0)}. "
                  f"P(0 | same rate) = {poisson_p0(mu):.3f}"
                  + ("  => NOT informative" if poisson_p0(mu) > 0.10 else "  => informative"))
        store.setdefault("rate_fast", {})[f"{ax}|{band}"] = dict(
            counts={str(k): int(v) for k, v in cnt.items()},
            expo={str(k): round(v, 1) for k, v in iexp.items()},
            p0_kd1=poisson_p0(r244 * iexp.get(1.0, 0) / 3600),
            p0_kd2=poisson_p0(r244 * iexp.get(2.0, 0) / 3600))

    # ============================================================ 6. look-back ===================
    G.hdr("6.  WHAT PRECEDES AN EVENT -- 3 s look-back vs matched non-event controls")
    lag = np.arange(-3.0, 1.01, 0.25)
    prof, ctrl = {k: [] for k in ("v", "rate", "eff", "ang", "e4", "rail")}, {
        k: [] for k in ("v", "rate", "eff", "ang", "e4", "rail")}
    for e in dd:
        d = can.get((e["route"], e["seg"]))
        if d is None:
            continue
        fsc = 1.0 / float(np.median(np.diff(d["t"])))
        for tgt, store_ in ((e["t"], prof), (e["t"] + 25.0, ctrl)):
            j = int(np.argmin(np.abs(d["t"] - tgt)))
            if j < int(4 * fsc) or j > len(d["t"]) - int(2 * fsc):
                continue
            if abs(d["cs_v"][j]) < VFAST or d["cc_lat"][j] < 0.5:
                continue
            idx = (j + (lag * fsc)).astype(int)
            store_["v"].append(np.abs(d["cs_v"][idx]))
            store_["rate"].append(np.abs(d["rate_c"][idx]))
            store_["ang"].append(np.abs(d["ang"][idx]))
            store_["e4"].append(np.abs(d["e4tq"][idx]))
            store_["rail"].append((np.abs(d["cc_req"][idx]) > 0.95).astype(float))
            from _r31_common import sustained as _s2
            store_["eff"].append(np.abs(_s2(d["tq"][max(0, j - 400):j + 200], fsc))[
                np.clip((idx - max(0, j - 400)), 0, None)])
    print(f"    {len(prof['v'])} event look-backs, {len(ctrl['v'])} controls (+25 s offset)")
    print(f"    {'lag s':>7}" + "".join(f"{k:>11}" for k in ("v", "|rate|", "eff", "|ang|",
                                                             "|e4|", "rail"))
          + "     (event  |  control)")
    for i, L in enumerate(lag):
        if abs(L * 4 - round(L * 4)) > 1e-6 or (i % 2):
            continue
        row = []
        for k in ("v", "rate", "eff", "ang", "e4", "rail"):
            a = np.median([x[i] for x in prof[k]]) if prof[k] else np.nan
            b = np.median([x[i] for x in ctrl[k]]) if ctrl[k] else np.nan
            row.append(f"{a:5.1f}/{b:<5.1f}")
        print(f"    {L:>7.2f}" + "".join(f"{r:>11}" for r in row))
    store["lookback"] = {k: [float(np.median([x[i] for x in prof[k]])) if prof[k] else None
                             for i in range(len(lag))] for k in prof}

    # ============================================================ 7. coherence ===================
    G.hdr("7.  COMMAND <-> BAR COHERENCE.  Grind #1's mechanism was a closed-loop LKAS\n"
          "    instability with command->bar coherence 0.917 at 21.09 Hz. Is that repeated here?")
    def coh(x, y, fs, nfft=128):
        n = min(len(x), len(y))
        Sxy = Sxx = Syy = 0
        w = np.hanning(nfft)
        for a in range(0, n - nfft + 1, nfft // 2):
            X = np.fft.rfft((x[a:a + nfft] - np.mean(x[a:a + nfft])) * w)
            Y = np.fft.rfft((y[a:a + nfft] - np.mean(y[a:a + nfft])) * w)
            Sxy = Sxy + X * np.conj(Y)
            Sxx = Sxx + np.abs(X) ** 2
            Syy = Syy + np.abs(Y) ** 2
        f = np.fft.rfftfreq(nfft, 1 / fs)
        return f, np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-300)
    accE, accQ, nE, nQ = None, None, 0, 0
    fax = None
    for r in runs:
        m = np.flatnonzero(r["v"] >= VFAST)
        if len(m) < 1024:
            continue
        for a in range(m[0], m[-1] - 512, 512):
            f, C = coh(r["e4"][a:a + 512], r["tq"][a:a + 512], r["fs"])
            fax = f
            accQ = C if accQ is None else accQ + C
            nQ += 1
    for e in dd:
        d = can.get((e["route"], e["seg"]))
        if d is None:
            continue
        fsc = 1.0 / float(np.median(np.diff(d["t"])))
        j = int(np.argmin(np.abs(d["t"] - e["t"])))
        a = max(0, min(len(d["t"]) - 512, j - 256))
        f, C = coh(d["e4tq"][a:a + 512], d["tq"][a:a + 512], fsc)
        accE = C if accE is None else accE + C
        nE += 1
    if nE and nQ:
        CE, CQ = accE / nE, accQ / nQ
        print(f"    magnitude-squared coherence, 0x0E4 LKAS command -> 0x18F torsion bar")
        print(f"    {'band':>10}{'  event windows':>18}{'  all >28 windows':>20}")
        for lo, hi in ((1, 4), (6, 9), (10, 16), (18, 22), (24, 28), (30, 40), (40, 49)):
            m = (fax >= lo) & (fax <= hi)
            print(f"    {f'{lo}-{hi} Hz':>10}{np.mean(CE[m]):>18.3f}{np.mean(CQ[m]):>20.3f}")
            store.setdefault("coherence", {})[f"{lo}-{hi}"] = [float(np.mean(CE[m])),
                                                               float(np.mean(CQ[m]))]
        print(f"    (n = {nE} event windows, {nQ} background windows; 5.12 s each, "
              f"nfft 128 = 1.28 s)")
        print("    🛑 e4tq is HELD-LAST onto the 0x14A grid, so coherence above ~30 Hz carries a\n"
              "       zero-order-hold artefact. Read the 40-49 Hz row as an upper bound.")

    OUT.write_text(json.dumps(store, indent=1, default=float))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
