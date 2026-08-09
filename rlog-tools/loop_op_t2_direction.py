#!/usr/bin/env python3
"""T2 -- DIRECTION, by three methods that fail differently.

The V85 brief asks for at least two independent direction measures.  Four are run here:

  A. SIGN ANCHOR (0.4-2 Hz).  Resolves the 180 deg ambiguity between the corpus's negated `bar`
     and the raw `cmd`, so that absolute phase elsewhere is readable at all.  Below 2 Hz openpilot's
     exogenous lane demand dominates the loop (H1 -> G) and an 18 ms delay is only 13 deg.

  B. PHASE SLOPE / GROUP DELAY -- in T1.  Recapped here per band against openpilot's OWN measured
     reaction lag from `ang -> cmd`, because the prediction is quantitative, not just a sign:
     if the bar drives and openpilot echoes, H1(cmd->bar) -> 1/C and its group delay must be
     MINUS the ang->cmd delay, to within the CI.  Two numbers measured on different channel pairs
     that must agree in magnitude and disagree in sign.

  C. SPECTRAL GRANGER CAUSALITY (Geweke 1982), bivariate VAR on the broadband pair.
     🛑 Assumptions, stated because they are the weak point:
        (i)  linear, wide-sense stationary within an episode -- episodes are <= 20.5 s and are
             speed-stratified in the report;
        (ii) VAR order large enough to span the true lags -- swept p in {4, 8, 12}, i.e. 40-120 ms,
             against measured lags of 6-20 ms;
        (iii) NO UNMEASURED COMMON DRIVER.  This is the real exposure: the road, and the EPS's own
             state, drive both channels.  A common driver inflates BOTH directions, so the
             DIFFERENCE (net GC) is the statistic quoted, not either direction alone;
        (iv) no instantaneous causation -- handled by Geweke's normalisation transform, which is
             why the raw VAR residual covariance is rotated before the decomposition.
     🛑 Granger is NOT run on band-passed data.  Band-passing before a VAR is a known generator of
     spurious causality (the filter's own phase response becomes the "lag"); the VAR is fitted
     broadband and the causality is READ OUT per frequency, which is the whole point of Geweke.

  D. ENVELOPE LEAD/LAG.  Cross-correlation of the two channels' 26-31 Hz (and 18-22 Hz) analytic
     ENVELOPES.  This asks a different question from the carrier phase -- when a burst STARTS,
     which channel's amplitude rises first -- and is immune to both the 180 deg ambiguity and to
     any constant delay in the carrier.  A rate-limited or amplitude-triggered mechanism shows up
     here even if the carrier phase is ambiguous.

  E. ENGAGEMENT EDGES.  At `latActive` rising edges the command switches from a constant zero to
     live.  Whichever channel's band envelope rises first, does so before the other by an actuator
     delay or not at all.

Writes `_cache_loop_op/t2_direction.json`.
"""
import json
import sys

import numpy as np

import loop_op_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAXFILL = 0.02      # episodes with >2% forward-filled bar are excluded from the TIME-DOMAIN tests
GBANDS = [("18-22", 18.0, 22.0), ("26-31", 26.0, 31.0), ("6-9", 6.0, 9.0)]


# ================================================================= C. spectral Granger ===========
def var_fit(X, p):
    """OLS VAR(p) on X (n, m).  Returns (A list of (m,m), Sigma (m,m), n_used)."""
    n, m = X.shape
    Y = X[p:]
    Z = np.hstack([X[p - k - 1:n - k - 1] for k in range(p)])
    Z = np.hstack([Z, np.ones((len(Z), 1))])
    beta, *_ = np.linalg.lstsq(Z, Y, rcond=None)
    E = Y - Z @ beta
    Sig = (E.T @ E) / (len(Y) - Z.shape[1])
    A = [beta[k * m:(k + 1) * m, :].T for k in range(p)]
    return A, Sig, len(Y)


def geweke(A, Sig, f, fs):
    """Geweke's pairwise spectral GC for a bivariate VAR.  Returns (gc_1to2, gc_2to1) at each f."""
    m = 2
    z = np.exp(-2j * np.pi * np.asarray(f, float) / fs)
    Af = np.empty((len(f), m, m), complex)
    for i, _ in enumerate(f):
        Ai = np.eye(m, dtype=complex)
        for k, Ak in enumerate(A):
            Ai -= Ak * z[i] ** (k + 1)
        Af[i] = Ai
    H = np.linalg.inv(Af)
    s11, s12, s22 = Sig[0, 0], Sig[0, 1], Sig[1, 1]
    # 2 -> 1 : remove instantaneous causality from 1's innovation
    P = np.array([[1.0, 0.0], [-s12 / s11, 1.0]])
    Ht = H @ np.linalg.inv(P)
    St = P @ Sig @ P.T
    S11 = (np.abs(Ht[:, 0, 0]) ** 2 * St[0, 0] + np.abs(Ht[:, 0, 1]) ** 2 * St[1, 1])
    gc21 = np.log(np.maximum(S11, 1e-300) /
                  np.maximum(np.abs(Ht[:, 0, 0]) ** 2 * St[0, 0], 1e-300))
    # 1 -> 2
    Q = np.array([[1.0, -s12 / s22], [0.0, 1.0]])
    Hb = H @ np.linalg.inv(Q)
    Sb = Q @ Sig @ Q.T
    S22 = (np.abs(Hb[:, 1, 0]) ** 2 * Sb[0, 0] + np.abs(Hb[:, 1, 1]) ** 2 * Sb[1, 1])
    gc12 = np.log(np.maximum(S22, 1e-300) /
                  np.maximum(np.abs(Hb[:, 1, 1]) ** 2 * Sb[1, 1], 1e-300))
    return gc12, gc21


def granger_episodes(eps, p, fs=100.0, nf=257):
    """Per-episode Geweke GC; returns f, list of (gc_xy, gc_yx)."""
    f = np.linspace(0, fs / 2, nf)
    out = []
    for x, y in eps:
        X = np.column_stack([x - x.mean(), y - y.mean()])
        sd = X.std(0)
        if np.any(sd <= 0):
            continue
        X = X / sd
        try:
            A, Sig, _ = var_fit(X, p)
            g12, g21 = geweke(A, Sig, f, fs)
        except np.linalg.LinAlgError:
            continue
        if not (np.all(np.isfinite(g12)) and np.all(np.isfinite(g21))):
            continue
        out.append((g12, g21))
    return f, out


def band_mean(f, y, lo, hi):
    s = (f >= lo) & (f <= hi)
    return float(np.mean(y[s]))


def boot_net(f, gcs, lo, hi, nboot=2000, seed=8585):
    """Episode bootstrap of the NET GC (x->y minus y->x) in a band."""
    rng = np.random.default_rng(seed)
    net = np.array([band_mean(f, a, lo, hi) - band_mean(f, b, lo, hi) for a, b in gcs])
    xy = np.array([band_mean(f, a, lo, hi) for a, b in gcs])
    yx = np.array([band_mean(f, b, lo, hi) for a, b in gcs])
    if len(net) < 4:
        return net.mean(), (np.nan, np.nan), xy.mean(), yx.mean()
    bs = [net[rng.integers(0, len(net), len(net))].mean() for _ in range(nboot)]
    return (float(net.mean()), (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))),
            float(xy.mean()), float(yx.mean()))


# ================================================================= D. envelopes ==================
def bp_envelope(x, fs, lo, hi):
    """Analytic envelope inside [lo,hi] via a zero-phase brick-wall FFT band-pass.
    Zero-phase => it introduces NO delay of its own, which is the property the lead/lag test needs.
    """
    n = len(x)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(n, 1 / fs)
    X[(f < lo) | (f > hi)] = 0
    # analytic signal: double the retained positive-frequency content
    Z = np.zeros(n, complex)
    Z[:len(X)] = 2 * X
    Z[0] = X[0]
    if n % 2 == 0:
        Z[n // 2] = X[-1]
    return np.abs(np.fft.ifft(Z))


def xcorr_lag(a, b, fs, maxlag_s=0.25):
    """Lag (s) maximising corr(a[t], b[t+lag]) and the peak value.
    lag > 0 means B follows A, i.e. A LEADS."""
    a = (a - a.mean()) / (a.std() + 1e-300)
    b = (b - b.mean()) / (b.std() + 1e-300)
    n = len(a)
    m = int(maxlag_s * fs)
    c = np.correlate(b, a, mode="full") / n
    lags = np.arange(-(n - 1), n) / fs
    s = np.abs(lags) <= maxlag_s + 1e-9
    c, lags = c[s], lags[s]
    i = int(np.argmax(c))
    return float(lags[i]), float(c[i]), float(c[len(c) // 2])


def main():
    out = {}

    # -------------------------------------------------------------- A. SIGN ANCHOR --------------
    print("=== A. SIGN ANCHOR -- resolving the 180 deg ambiguity")
    segs_all = {r: L.load_route(r) for r in L.ROUTES}
    # channel-sense checks against openpilot's OWN carState/carControl copies
    ca, cc = [], []
    for r, ss in segs_all.items():
        for d in ss:
            m = L.mask_engaged(d)
            if m.sum() < 500:
                continue
            ca.append(np.corrcoef(d["ang"][m], d["cs_ang"][m])[0, 1])
            if np.std(d["cc_rq"][m]) > 0:
                cc.append(np.corrcoef(d["cmd"][m], d["cc_rq"][m])[0, 1])
    print(f"  corr(ang, carState.steeringAngleDeg) = {np.mean(ca):+.4f}  (n={len(ca)} segs)"
          "   => `ang` IS openpilot's angle convention")
    print(f"  corr(cmd, carControl.actuators.torque) = {np.mean(cc):+.4f}  (n={len(cc)} segs)"
          "   => `cmd` IS openpilot's request, unnegated")
    print("  🛑 corr(cmd, cc_rq) is NEGATIVE: the RAW 0x0E4 payload is MINUS openpilot's own "
          "`actuators.torque`.\n     Consistent with the firmware's own `clamp(req * -4, +/-0x4000)` "
          "(`docs/STATE.md` L1288).  `ang` and `bar` both carry the corpus's x-1 and ARE in "
          "openpilot's sense.")
    anchors = {}
    for ych, lbl in (("bar", "cmd->bar"), ("ang", "cmd->ang")):
        recs = []
        for r in L.ROUTES:
            recs += L.collect_native(r, L.mask_engaged, xch="cmd", ych=ych, segs=segs_all[r])
        f, Sxx, Syy, Sxy, K = L.stack(recs)
        a = L.band_stats(f, Sxx, Syy, Sxy, 0.4, 2.0, K)
        _, aci = L.boot_band(recs, 0.4, 2.0, nboot=2000)
        print(f"  0.4-2 Hz {lbl}: g2 = {L.fmt_ci(a['g2'], aci['g2'])}  "
              f"phase = {L.fmt_ci(a['ph'], aci['ph'])} deg  |H| = {a['H']:.3g}   K={K}")
        a["ci"] = {k: list(v) for k, v in aci.items()}
        anchors[lbl] = a
    g2b = anchors["cmd->bar"]["g2"]
    if g2b < 0.5:
        print(f"  🛑 REFUSED: the cmd->bar low-frequency anchor is g2 = {g2b:.4f}, far below the "
              "0.5 floor.\n     openpilot's command and the torsion bar are NOT linearly related "
              "below 2 Hz at all --\n     physically sensible (the bar reads the DRIVER-side "
              "reaction, not the applied motor torque),\n     but it means NO absolute cmd->bar "
              "phase is quotable at any frequency.\n     ⇒ every direction claim below rests on "
              "the phase SLOPE, on Granger, and on the envelopes,\n     all three of which are "
              "invariant to a constant sign.")
    out["sign_anchor"] = dict(corr_ang_csang=float(np.mean(ca)), corr_cmd_ccrq=float(np.mean(cc)),
                              anchors=anchors,
                              verdict=("REFUSED -- g2 below floor; absolute phase not quotable"
                                       if g2b < 0.5 else "usable"))

    # -------------------------------------------------------------- B. slope recap --------------
    print("\n=== B. GROUP DELAY -- the quantitative prediction")
    ac = []
    for r in L.ROUTES:
        ac += L.collect_native(r, L.mask_engaged, xch="ang", ych="cmd", segs=segs_all[r])
    fa, Sa, Sb2, Sab, Ka = L.stack(ac)
    w = L.coh(Sa, Sb2, Sab) * Sa
    tau_C, ph0, r2, nb = L.band_delay(fa, Sab, 5.0, 45.0, wgt=w)
    tau_C2, _, r2b, _ = L.band_delay(fa, Sab, 2.0, 25.0, wgt=w)
    print(f"  openpilot's OWN reaction lag, ang -> cmd:  "
          f"tau_C = {tau_C*1e3:+.2f} ms (5-45 Hz, r2 {r2:.3f}) / "
          f"{tau_C2*1e3:+.2f} ms (2-25 Hz, r2 {r2b:.3f}),  K = {Ka}")
    print(f"  minus the panda TX+bus echo latency (6.51 ms, T0 CAL-2) => openpilot's compute lag "
          f"from angle-on-bus to publish = {tau_C*1e3-6.51:+.2f} ms  (~1 frame)")
    print("  PREDICTION if the bar drives and openpilot echoes: group delay of cmd->bar = "
          f"{-tau_C*1e3:+.2f} ms.  PREDICTION if openpilot drives: >= 0 and >= the actuator lag.")
    out["tau_C_ms"] = dict(b5_45=tau_C * 1e3, r2_5_45=r2, b2_25=tau_C2 * 1e3, r2_2_25=r2b, K=Ka)

    # -------------------------------------------------------------- C/D/E: time domain ----------
    print(f"\n=== C. SPECTRAL GRANGER (Geweke) and D. ENVELOPE LEAD/LAG   "
          f"[episodes with >{MAXFILL*100:.0f}% forward-filled bar excluded]")
    res = {"granger": {}, "envelope": {}, "edges": {}}
    for scope, routes in [("ALL 4 BUILDS", list(L.ROUTES)), ("V80/r66 only", ["V80/r66"]),
                          ("V84/r6d only", ["V84/r6d"])]:
        eps_cb, eps_ac, meta = [], [], []
        for r in routes:
            for d in segs_all[r]:
                fm = L.fill_mask(d, "bar")
                for i0, i1 in L.episodes(d, L.mask_engaged(d)):
                    if fm[i0:i1].mean() > MAXFILL:
                        continue
                    eps_cb.append((d["cmd"][i0:i1].astype(float), d["bar"][i0:i1].astype(float)))
                    eps_ac.append((d["ang"][i0:i1].astype(float), d["cmd"][i0:i1].astype(float)))
                    meta.append(dict(route=r, seg=int(d["_seg"]),
                                     v=float(np.mean(np.abs(d["cs_v"][i0:i1]))),
                                     fs=d["_fs"], i0=i0, i1=i1))
        print(f"\n  --- {scope}:  {len(eps_cb)} clean episodes")
        if len(eps_cb) < 4:
            continue
        sc = {}
        for p in (4, 8, 12):
            fg, gcs = granger_episodes(eps_cb, p)
            row = {}
            for bn, lo, hi in GBANDS:
                net, ci, xy, yx = boot_net(fg, gcs, lo, hi)
                row[bn] = dict(net=net, ci=list(ci), cmd_to_bar=xy, bar_to_cmd=yx, K=len(gcs))
                arrow = "cmd->bar" if net > 0 else "bar->cmd"
                sig = "" if (ci[0] <= 0 <= ci[1]) else "  *"
                print(f"    p={p:2d} {bn:>6}: GC cmd->bar {xy:.4f}  bar->cmd {yx:.4f}  "
                      f"NET {net:+.4f} [{ci[0]:+.4f},{ci[1]:+.4f}] => {arrow}{sig}")
            sc[f"p{p}"] = row
        # ang -> cmd as a POSITIVE CONTROL for the Granger machinery: openpilot demonstrably
        # computes its command from the angle, so this direction must come out strongly positive.
        fg, gcs = granger_episodes(eps_ac, 8)
        ctl = {}
        for bn, lo, hi in GBANDS:
            net, ci, xy, yx = boot_net(fg, gcs, lo, hi)
            ctl[bn] = dict(net=net, ci=list(ci), ang_to_cmd=xy, cmd_to_ang=yx)
            print(f"    CONTROL p=8 {bn:>6}: GC ang->cmd {xy:.4f}  cmd->ang {yx:.4f}  "
                  f"NET {net:+.4f} [{ci[0]:+.4f},{ci[1]:+.4f}]")
        sc["control_ang_cmd_p8"] = ctl
        res["granger"][scope] = sc

        # ------------------------------------------------------ D. envelopes --------------------
        env = {}
        for bn, lo, hi in GBANDS:
            lags, peaks, zero = [], [], []
            for (x, y), mm in zip(eps_cb, meta):
                fs = mm["fs"]
                ex = bp_envelope(x, fs, lo, hi)
                ey = bp_envelope(y, fs, lo, hi)
                lag, pk, z0 = xcorr_lag(ex, ey, fs)
                lags.append(lag); peaks.append(pk); zero.append(z0)
            lags = np.array(lags); peaks = np.array(peaks)
            rng = np.random.default_rng(99)
            bs = [np.median(lags[rng.integers(0, len(lags), len(lags))]) for _ in range(2000)]
            med = float(np.median(lags))
            ci = (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))
            lead = "CMD leads bar" if med > 0 else "BAR leads cmd"
            print(f"    ENV {bn:>6}: median lag(cmd->bar) = {med*1e3:+.1f} ms "
                  f"[{ci[0]*1e3:+.1f},{ci[1]*1e3:+.1f}]  peak r = {np.median(peaks):.3f}  "
                  f"r(lag0) = {np.median(zero):.3f}  => {lead}")
            env[bn] = dict(median_lag_ms=med * 1e3, ci_ms=[ci[0] * 1e3, ci[1] * 1e3],
                           peak_r=float(np.median(peaks)), r_lag0=float(np.median(zero)),
                           n=len(lags))
        res["envelope"][scope] = env

    # -------------------------------------------------------------- E. engagement edges ---------
    print("\n=== E. ENGAGEMENT EDGES -- which band envelope moves first at latActive rising?")
    PRE, POST = 2.0, 3.0
    edge = {bn: {"cmd": [], "bar": [], "n": 0} for bn, _, _ in GBANDS}
    nedge = 0
    for r in L.ROUTES:
        for d in segs_all[r]:
            lat = (d["cc_lat"] > 0.5).astype(int)
            rise = np.flatnonzero(np.diff(lat) == 1) + 1
            fs = d["_fs"]
            fm = L.fill_mask(d, "bar")
            for i in rise:
                a, b = int(i - PRE * fs), int(i + POST * fs)
                if a < 0 or b >= len(lat):
                    continue
                if lat[a:i].any() or not lat[i:b].all():
                    continue
                if fm[a:b].mean() > MAXFILL or np.max(np.diff(d["t"][a:b])) > L.LATTICE_GAP:
                    continue
                if np.mean(np.abs(d["cs_v"][a:b])) < 1.0:
                    continue
                nedge += 1
                for bn, lo, hi in GBANDS:
                    edge[bn]["cmd"].append(bp_envelope(d["cmd"][a:b].astype(float), fs, lo, hi))
                    edge[bn]["bar"].append(bp_envelope(d["bar"][a:b].astype(float), fs, lo, hi))
    print(f"  {nedge} clean rising edges ({PRE:.0f} s before / {POST:.0f} s after, v > 1 m/s)")
    ee = {}
    if nedge >= 4:
        nmin = min(min(len(e) for e in edge[bn]["cmd"]) for bn, _, _ in GBANDS)
        for bn, lo, hi in GBANDS:
            C = np.array([e[:nmin] for e in edge[bn]["cmd"]])
            B = np.array([e[:nmin] for e in edge[bn]["bar"]])
            tt = np.arange(C.shape[1]) / 100.0 - PRE
            mc, mb = C.mean(0), B.mean(0)

            def t_cross(m, frac=0.5):
                pre = m[tt < -0.2].mean()
                post = m[tt > 1.0].mean()
                if post <= pre:
                    return np.nan
                thr = pre + frac * (post - pre)
                k = np.flatnonzero((tt > -0.2) & (m >= thr))
                return float(tt[k[0]]) if len(k) else np.nan
            tc, tb = t_cross(mc), t_cross(mb)
            pre_c = mc[tt < -0.2].mean(); post_c = mc[tt > 1.0].mean()
            pre_b = mb[tt < -0.2].mean(); post_b = mb[tt > 1.0].mean()
            print(f"  {bn:>6}: cmd env {pre_c:8.2f} -> {post_c:8.2f} ct (x{post_c/max(pre_c,1e-9):6.2f}), "
                  f"50% at {tc*1e3 if np.isfinite(tc) else float('nan'):+7.0f} ms | "
                  f"bar env {pre_b:8.2f} -> {post_b:8.2f} ct (x{post_b/max(pre_b,1e-9):5.2f}), "
                  f"50% at {tb*1e3 if np.isfinite(tb) else float('nan'):+7.0f} ms")
            ee[bn] = dict(cmd_pre=float(pre_c), cmd_post=float(post_c), cmd_t50_ms=tc * 1e3,
                          bar_pre=float(pre_b), bar_post=float(post_b), bar_t50_ms=tb * 1e3,
                          n=nedge)
    res["edges"] = ee
    out.update(res)
    (L.CACHE / "t2_direction.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"\n-> {L.CACHE / 't2_direction.json'}")


if __name__ == "__main__":
    main()
