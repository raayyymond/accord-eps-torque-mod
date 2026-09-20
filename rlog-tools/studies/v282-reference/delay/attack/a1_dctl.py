"""ADVERSARY a1: re-derive D_ctl from the raw message chain, my own way.

D_ctl := t(sendcan of the 0xE4 computed from carState j) - t(carState j)
Split as   [t(controlsState) - t(carState consumed)]  +  [t(sendcan) - t(controlsState)]
Leg 2 is pinned by EXACT VALUE IDENTITY (cs_out -> e4). Leg 1 by a lag test on the measurement
content of controlsState (d(error) vs -d(angle)), two statistics (sign agreement and correlation).
Also: carState cadence, frame census, the naive "latest carState" reading, and the 0xE4 TX echo bound.
"""
import sys
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent / "out"
np.set_printoptions(suppress=True)


def main(route):
    D = np.load(OUT / f"raw_{route}.npz")
    t_cst, sa, sr, v, sp = D["t_cst"], D["sa"], D["sr"], D["v"], D["spress"]
    t_cs, cs_out, cs_act, cs_err = D["t_cs"], D["cs_out"], D["cs_act"], D["cs_err"]
    t_cc, cc_tq, cc_tqcan, cc_lat = D["t_cc"], D["cc_tq"], D["cc_tqcan"], D["cc_lat"]
    t_e4, e4 = D["t_e4"], D["e4"]
    print(f"=== {route} ===")
    print(f"n carState={len(t_cst)} controlsState={len(t_cs)} carControl={len(t_cc)} sendcan0xE4={len(t_e4)}")

    # ---------- cadence ----------
    for nm, tt in (("carState", t_cst), ("controlsState", t_cs), ("carControl", t_cc), ("sendcan", t_e4)):
        d = np.diff(tt) * 1e3
        d = d[(d > 1) & (d < 40)]
        print(f"cadence {nm:14s} median {np.median(d):.3f} ms  mean {d.mean():.3f}  p5 {np.percentile(d,5):.2f} p95 {np.percentile(d,95):.2f}")

    # ---------- leg 2: exact value identity cs_out -> carControl -> sendcan ----------
    # controlsState -> carControl: float-exact match, per-index
    n = min(len(t_cs), len(t_cc))
    for k in (0, 1, -1):
        a = cs_out[max(0, k):n + min(0, k)]
        b = cc_tq[max(0, -k):n + min(0, -k)]
        m = min(len(a), len(b))
        eq = np.mean(a[:m] == b[:m])
        print(f"  cs_out == cc_torque at index offset {k:+d}: exact-equal fraction {eq:.5f}  dt median "
              f"{np.median(t_cc[max(0,-k):n+min(0,-k)][:m] - t_cs[max(0,k):n+min(0,k)][:m])*1e3:+.3f} ms")

    # sendcan e4 vs carControl torqueOutputCan (int) -- find the producer offset by exact match
    # build per-send the nearest-preceding carControl within 20 ms, then test identity at 0/1/2 cycles back
    j = np.searchsorted(t_cc, t_e4, side="right") - 1
    ok = (j >= 2) & (np.abs(e4) > 0.5)          # engaged sends only; zeros match trivially
    print(f"  nonzero-e4 sends: {ok.sum()} of {len(e4)}; carControl.torqueOutputCan nonzero frac "
          f"{np.mean(np.abs(cc_tqcan) > 0.5):.4f}")
    best = None
    for k in (0, 1, 2):
        jj = j[ok] - k
        sc = np.sum(e4[ok] * cc_tq[jj]) / max(np.sum(cc_tq[jj] ** 2), 1e-12)     # LS scale, no intercept
        r = e4[ok] - sc * cc_tq[jj]
        frac = np.mean(np.abs(r) <= 1.0)
        dt = np.median(t_e4[ok] - t_cc[jj]) * 1e3
        print(f"  e4 vs {k}-back carControl.actuators.torque: LS scale {sc:9.3f}  |resid|<=1LSB {frac:.5f}  "
              f"rms resid {np.sqrt(np.mean(r**2)):8.2f}   t_e4-t_cc median {dt:+.3f} ms")
        if best is None or frac > best[1]:
            best = (k, frac, dt)
    kbest = best[0]
    jj = j[ok] - kbest
    print(f"  producer = {kbest}-back carControl, |resid|<=1LSB {best[1]:.5f}")
    # leg2: sendcan minus the controlsState that produced it (same index as the producing carControl)
    leg2 = (t_e4[ok] - t_cs[np.clip(jj, 0, len(t_cs) - 1)]) * 1e3
    print(f"  LEG2 t(sendcan) - t(controlsState producing it): median {np.median(leg2):.3f} ms "
          f"[p5 {np.percentile(leg2,5):.2f}, p95 {np.percentile(leg2,95):.2f}]")

    # ---------- leg 1: which carState did controlsState consume? ----------
    # controlsState.error high-frequency content is -measurement; test against -d(sa)
    i = np.searchsorted(t_cst, t_cs, side="right") - 1   # newest carState published before this controlsState
    m = (i >= 3) & (i < len(t_cst) - 3)
    m[-1] = False
    de = np.concatenate([[np.nan], np.diff(cs_err)])      # de[k] = cs_err[k]-cs_err[k-1]
    dsa = np.concatenate([[np.nan], np.diff(sa)])         # dsa[n] = sa[n]-sa[n-1]
    print("  leg1 lag test (d(cs_err) vs -d(sa) of the L-back carState):")
    stats = {}
    for L in (0, 1, 2, 3):
        v1 = de[m]
        v2 = -dsa[np.clip(i[m] - L, 1, len(sa) - 1)]
        g = np.isfinite(v1) & np.isfinite(v2) & (np.abs(v1) > 1e-6) & (np.abs(v2) > 1e-9)
        sign = np.mean(np.sign(v1[g]) == np.sign(v2[g]))
        cc = np.corrcoef(v1[g], v2[g])[0, 1]
        stats[L] = (sign, cc)
        print(f"    L={L}: sign agreement {sign:.3f} (|anti|={1-sign:.3f})  corr {cc:+.3f}")
    Lbest = max(stats, key=lambda k: abs(stats[k][1]))    # MAGNITUDE: the sign convention of cs_err is not assumed
    leg1 = (t_cs[m] - t_cst[np.clip(i[m] - Lbest, 0, len(t_cst) - 1)]) * 1e3
    print(f"  LEG1 consumed carState is L={Lbest} back: t(controlsState)-t(carState) median {np.median(leg1):.3f} ms "
          f"[p5 {np.percentile(leg1,5):.2f}, p95 {np.percentile(leg1,95):.2f}]")
    print(f"  ==> D_ctl = LEG1 + LEG2 = {np.median(leg1)+np.median(leg2):.3f} ms")

    # direct end-to-end version: for each send, the carState that fed the producing controlsState
    ics = np.clip(jj, 0, len(t_cs) - 1)
    icst = np.clip(i[ics] - Lbest, 0, len(t_cst) - 1)
    dctl = (t_e4[ok] - t_cst[icst]) * 1e3
    print(f"  ==> D_ctl end-to-end per send: median {np.median(dctl):.3f} ms  mean {dctl.mean():.3f} "
          f"[p5 {np.percentile(dctl,5):.2f}, p95 {np.percentile(dctl,95):.2f}]  n={len(dctl)}")
    # engaged-only
    eng = (cs_act[ics] > 0.5) & (cc_lat[jj] > 0.5) & (sp[icst] < 0.5)
    print(f"  engaged hands-off only (n={eng.sum()}): median {np.median(dctl[eng]):.3f} ms")
    # speed bins
    for lo, hi in ((0, 8), (8, 15), (15, 99)):
        s = eng & (v[icst] >= lo) & (v[icst] < hi)
        if s.sum() > 100:
            print(f"    v {lo}-{hi}: {np.median(dctl[s]):.3f} ms  n={s.sum()}")
    # the naive reading: how stale is the newest carState at the moment of the send?
    inew = np.searchsorted(t_cst, t_e4[ok], side="right") - 1
    stale = inew - icst
    vals, cnts = np.unique(stale, return_counts=True)
    print(f"  staleness of the send vs the NEWEST carState at send time (cycles): "
          f"{dict(zip(vals.tolist(), (cnts/cnts.sum()).round(3).tolist()))}")
    print(f"  naive 'latest carState' delta would read {np.median((t_e4[ok]-t_cst[inew])*1e3):.3f} ms")

    # ---------- 0xE4 TX echo bound on sendcan -> on-bus ----------
    cb, addr, src, bi = D["cb"], D["cf_addr"], D["cf_src"], D["cf_bi"]
    u, c = np.unique(np.stack([addr, src]), axis=1, return_counts=True)
    print("  can frame census (addr,src)->n:", {f"0x{a:X}/{s}": int(k) for (a, s), k in zip(u.T, c)})
    for s_ in np.unique(src[addr == 0xE4]):
        te = cb[bi[(addr == 0xE4) & (src == s_)]]
        if len(te) < 5000:
            continue
        k = np.clip(np.searchsorted(te, t_e4), 0, len(te) - 1)
        d = (te[k] - t_e4) * 1e3
        d = d[(d >= -1) & (d < 30)]
        print(f"    echo src {s_}: n={len(te)} first-batch-after-send delay median {np.median(d):.3f} ms "
              f"p5 {np.percentile(d,5):.2f} p95 {np.percentile(d,95):.2f}")
    db = np.diff(cb) * 1e3
    db = db[(db > 0) & (db < 40)]
    print(f"    can batch interval median {np.median(db):.3f} ms  p95 {np.percentile(db,95):.2f}  n={len(db)+1}")

    # ---------- SAMPLE AGE: which 0x14A does carState carry, and how old is it? ----------
    s14 = (addr == 0x14A) & (src == 1)
    tb14 = cb[bi[s14]]
    ang14 = D["cf_b0"][s14] * 0.1
    k = np.searchsorted(tb14, t_cst, side="right") - 1
    g = k >= 2
    for L in (0, 1, 2):
        r = np.abs(sa[g] - ang14[k[g] - L])
        print(f"  carState.steeringAngleDeg == 0.1*i16(0x14A[0:2]) of the {L}-back frame: "
              f"frac|err|<0.001 {np.mean(r < 1e-3):.5f}  median |err| {np.median(r):.4f} deg")
    # EPS transmit clock by lower-envelope (LP) fit: t_true(k) = a + T*k <= t_batch(k)
    gaps = np.diff(tb14)
    Tg = np.median(gaps)
    idx = np.concatenate([[0], np.cumsum(np.maximum(1, np.round(gaps / Tg)))])   # re-index across drops
    bestT, bestres, besta = None, np.inf, None
    for T in np.arange(Tg - 8e-4, Tg + 8e-4, 2e-7):
        a = np.min(tb14 - T * idx)
        res = np.mean(tb14 - T * idx - a)
        if res < bestres:
            bestT, bestres, besta = T, res, a
    ttrue = besta + bestT * idx
    lag = (tb14 - ttrue) * 1e3
    print(f"  0x14A EPS transmit period (LP fit) {bestT*1e3:.4f} ms = {1/bestT:.2f} Hz; batch stamp minus "
          f"true arrival: mean {lag.mean():.3f} median {np.median(lag):.3f} p95 {np.percentile(lag,95):.2f} "
          f"max {lag.max():.2f} ms")
    age = (t_cst[g] - ttrue[k[g]]) * 1e3
    print(f"  ==> SAMPLE AGE at the carState stamp: mean {age.mean():.3f} median {np.median(age):.3f} "
          f"[p5 {np.percentile(age,5):.2f}, p95 {np.percentile(age,95):.2f}] ms")
    print(f"  (0x14A batch stamp to carState publish: median {np.median((t_cst[g]-tb14[k[g]])*1e3):.3f} ms)")


if __name__ == "__main__":
    main(sys.argv[1])
