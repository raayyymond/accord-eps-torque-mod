# -*- coding: utf-8 -*-
"""studies/osc-highangle/v283_ki_risetime.py -- (g) the WINDUP RISE-TIME fit of Ki (0xC63E6), and the
adjudication of the "Ki nearer 20 than 50" reading.  Subagent v283read, 2026-09-03.

Four estimators of the SAME quantity, ordered by how many modelling assumptions they carry:

  E1  DIFFERENCE REGRESSION (the reading two other agents quoted): slope of
      (T_meas - T_sim[Ki=0]) on (T_sim[Ki=50] - T_sim[Ki=0]).  Slope 1.00 = Ki is 50.
      Carries the modelled accumulator's ABSOLUTE level, so it inherits every open-loop integration
      error AND the +-10240 anti-windup clamp -- both of which push the slope DOWN, never up.
  E2  E1 with the clamp-bound frames removed.  Isolates how much of E1's shortfall is the clamp.
  E3  PROFILE over Ki with the REAL clamped accumulator, de-meaned per engagement episode
      (removes the drifting offset, keeps the shape), bootstrapped over episodes.
  E3b PROFILE vs CHUNK LENGTH -- the decisive test of the drift diagnosis.  The SAME SSE estimator as E3,
      run over fixed chunks of 1/2/4/8/16 s instead of whole engagement episodes.
  E4  RISE TIME: the tap's slope in the first 0.5 s after a held error establishes.
      *** E4 IS BROKEN AND ITS OUTPUT MUST NOT BE USED. *** It reads Ki_hat 51.5 on r35 and 77.9 on r34,
      both of which ship Ki = 0.  Cause: at the ONSET of a held error the P term is itself ramping, so
      d|T|/dt is dominated by dP/dt, and E4 attributes all of it to the integrator.  It is kept here only
      because it is the instrument the orchestrator asked for and the record should show why it fails --
      and because the Ki-0 CONTROLS are the only reason the failure was caught.

Run: python v283_ki_risetime.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v283_read_r36_r38 as M  # noqa: E402

V, ST = M.V, M.ST
FS, CPD = M.FS, M.CPD
ALL = M.ALL
RAMP_K = 0.15650                      # (254/256)(5346/32768) * lag_DC(0.99) * (1000/1024)
LINES = []


def pr(s=""):
    print(s); LINES.append(s)


def episodes_of(eng, minlen):
    d = np.diff(np.r_[0, eng.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


def main():
    routes = {t: V.Route(t) for t in ALL}
    R0 = {t: M.sim(routes[t], M.KP_OF[t], 0) for t in ALL}
    R50 = {t: M.sim(routes[t], M.KP_OF[t], 50) for t in ALL}

    # =============================================================================== E1 / E2
    pr("=" * 165)
    pr("E1 / E2 -- THE DIFFERENCE REGRESSION, AND WHAT THE ANTI-WINDUP CLAMP DOES TO IT")
    pr("  slope of (T_meas - T_sim[Ki=0]) on (T_sim[Ki=50] - T_sim[Ki=0]).  slope 1.00 <=> Ki = 50.")
    pr("  E1 = all engaged hands-light idx>0 frames (the reading quoted at 0.65-0.76).")
    pr("  E2 = the same, dropping frames where the MODELLED accumulator is at its +-10240 rail or the sum clamp binds.")
    pr("=" * 165)
    pr("  %-5s | %-28s | %-28s | %s" % ("route", "E1 slope / corr (n)", "E2 slope / corr (n)", "modelled I railed / sum-clamped"))
    for tag in ALL:
        r = routes[tag]
        base = r.eng & (r.idx > 0) & (np.abs(r.tq_raw) < 512)
        x = (R50[tag]["T"] - R0[tag]["T"])[r.i100]
        y = r.T_meas - R0[tag]["T"][r.i100]
        I50 = R50[tag]["I"][r.i100]
        Sraw = R50[tag]["S_raw"][r.i100]
        railed = np.abs(I50) >= M.I_CLAMP - 1
        sclamp = np.abs(Sraw) >= V.SUM_CLAMP
        out = []
        for m in (base, base & ~railed & ~sclamp & (np.abs(r.T_meas) < ST.CAP - 8)):
            if m.sum() < 200 or np.sum(x[m] ** 2) < 1e-6:
                out.append("--"); continue
            sl = np.sum(x[m] * y[m]) / np.sum(x[m] ** 2)
            c = np.corrcoef(x[m], y[m])[0, 1] if x[m].std() > 0 else np.nan
            out.append("%6.3f / %+.3f (%6d)" % (sl, c, m.sum()))
        pr("  %-5s | %-28s | %-28s | I railed %.3f, sum clamp %.3f"
           % (tag, out[0], out[1], float(np.mean(railed[base])), float(np.mean(sclamp[base]))))

    # =============================================================================== E3
    pr("\n" + "=" * 165)
    pr("E3 -- PROFILE OVER Ki with the REAL clamped accumulator, de-meaned per engagement episode.")
    pr("  For each candidate Ki the whole chain is re-run (accumulator, its rail, the sum clamp, the lag);")
    pr("  T_sim and T_meas are de-meaned inside each engagement episode >= 4 s, then pooled.  The Ki minimising")
    pr("  the SSE is the estimate; the CI is a bootstrap over EPISODES (the independent unit).")
    pr("=" * 165)
    KIS = np.arange(0, 121, 5)
    pr("  %-5s | %-46s | %s" % ("route", "SSE-minimising Ki  [95% CI, bootstrap over episodes]", "SSE curve, normalised to its minimum"))
    for tag in ALL:
        r = routes[tag]
        eps = [(a, b) for a, b in episodes_of(r.eng, int(4 * FS))]
        ok = (r.idx > 0) & (np.abs(r.tq_raw) < 512) & (np.abs(r.T_meas) < ST.CAP - 8)
        per_ep = []                                   # SSE per episode per Ki
        sims = {}
        for ki in KIS:
            sims[ki] = (M.sim(r, M.KP_OF[tag], int(ki))["T"])[r.i100]
        for a, b in eps:
            m = ok[a:b]
            if m.sum() < int(2 * FS):
                continue
            y = r.T_meas[a:b][m]; y = y - y.mean()
            row = []
            for ki in KIS:
                x = sims[ki][a:b][m]; x = x - x.mean()
                row.append(np.sum((y - x) ** 2))
            per_ep.append(row)
        if len(per_ep) < 5:
            pr("  %-5s | only %d episodes" % (tag, len(per_ep))); continue
        A = np.array(per_ep)
        tot = A.sum(axis=0)
        khat = KIS[int(np.argmin(tot))]
        rng = np.random.default_rng(11)
        bs = [KIS[int(np.argmin(A[rng.integers(0, len(A), len(A))].sum(axis=0)))] for _ in range(2000)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        curve = tot / tot.min()
        show = "  ".join("%d:%.3f" % (k, curve[i]) for i, k in enumerate(KIS) if k in (0, 20, 30, 40, 50, 60, 80, 100))
        pr("  %-5s | Ki = %3d   [%3.0f, %3.0f]   (%d episodes)          | %s" % (tag, khat, lo, hi, len(A), show))

    # =============================================================================== E3b
    pr("\n" + "=" * 165)
    pr("E3b -- THE SAME SSE PROFILE, over FIXED CHUNKS of increasing length.  THE DECISIVE TEST of the drift")
    pr("  diagnosis: a leak-free integrator's open-loop reconstruction error grows without bound, so if that is")
    pr("  why E3 returned 0, the estimate must be ~50 on r36/r37/r38 for SHORT chunks and decay as the chunk")
    pr("  lengthens -- while the Ki-0 CONTROLS stay pinned at 0 at EVERY chunk length.")
    pr("=" * 165)
    pr("  %-5s | %s" % ("route", " | ".join("%-14s" % ("%.0f s chunks" % L) for L in (1.0, 2.0, 4.0, 8.0))))
    for tag in ALL:
        r = routes[tag]
        sims = {int(k): (M.sim(r, M.KP_OF[tag], int(k))["T"])[r.i100] for k in KIS}
        ok = r.eng & (r.idx > 0) & (np.abs(r.tq_raw) < 512) & (np.abs(r.T_meas) < ST.CAP - 8)
        cells = []
        for L in (1.0, 2.0, 4.0, 8.0):
            n = int(L * FS); tot = np.zeros(len(KIS)); nch = 0
            for a in range(0, len(ok) - n, n):
                m = ok[a:a + n]
                if m.mean() < 0.98:
                    continue
                y = r.T_meas[a:a + n][m]; y = y - y.mean()
                if y.std() < 4:
                    continue
                for i, k in enumerate(KIS):
                    x = sims[int(k)][a:a + n][m]; x = x - x.mean()
                    tot[i] += np.sum((y - x) ** 2)
                nch += 1
            cells.append("Ki %3d (n%4d)" % (KIS[int(np.argmin(tot))], nch) if nch >= 10 else "  -- (n%d)" % nch)
        pr("  %-5s | %s" % (tag, " | ".join("%-14s" % c for c in cells)))

    # =============================================================================== E4
    pr("\n" + "=" * 165)
    pr("E4 -- RISE TIME.  *** BROKEN -- DO NOT USE ITS OUTPUT.  It reads Ki_hat 51.5 on r35 and 77.9 on r34,")
    pr("  both Ki = 0 builds: at the ONSET of a held error the P term is itself ramping, so d|T|/dt is dominated")
    pr("  by dP/dt and E4 charges all of it to the integrator.  Shown because it is the instrument that was")
    pr("  asked for, and because the Ki-0 controls are the only reason the failure was caught. ***")
    pr("  It does NOT depend on the")
    pr("  accumulator's absolute level: in the FIRST 0.5 s after a held error establishes -- before the wheel")
    pr("  has responded and before the accumulator can approach its rail -- the delivered torque must ramp at")
    pr("  0.15650 * |excess| * Ki counts/s.  Ki_hat = measured ramp / (0.15650 * |excess|), per onset.")
    pr("  Onsets: engaged, hands-light, |excess| >= 8 and same-signed across the window, |I_model| < 5000")
    pr("  (well clear of the rail), tap unrailed, and the 0.5 s BEFORE the onset not already in a held error.")
    pr("=" * 165)
    pr("  %-5s | %-44s | %-22s | %s" % ("route", "Ki_hat from rise time: median [95% CI]", "IQR", "n onsets / |excess| p50 / ramp p50"))
    for tag in ALL:
        r = routes[tag]
        Rm = R50[tag] if M.KI_OF[tag] else R0[tag]
        ex = M.excess_of(Rm["E"])[r.i100]
        Imod = np.abs(Rm["I"][r.i100])
        live = r.eng & (np.abs(r.tq_raw) < 512) & (np.abs(r.T_meas) < ST.CAP - 8)
        held = live & (np.abs(ex) >= 8)
        n = int(0.5 * FS)
        khats, exs, ramps = [], [], []
        for a, b in episodes_of(held, n):
            if a < n:
                continue
            # the 0.5 s before this onset must NOT have been a held error (so the accumulator starts low)
            if np.mean(np.abs(ex[a - n:a]) >= 8) > 0.2:
                continue
            sl = slice(a, a + n)
            if live[sl].mean() < 0.99 or abs(np.sign(ex[sl]).mean()) < 0.99 or Imod[sl].max() >= 5000:
                continue
            sg = np.sign(np.median(ex[sl]))
            t = np.arange(n) / FS
            ramp = np.polyfit(t, -sg * r.T_meas[sl], 1)[0]
            e50 = float(np.median(np.abs(ex[sl])))
            khats.append(ramp / (RAMP_K * e50)); exs.append(e50); ramps.append(ramp)
        if len(khats) < 8:
            pr("  %-5s | only %d qualifying onsets" % (tag, len(khats))); continue
        k = np.array(khats)
        rng = np.random.default_rng(13)
        bs = np.array([np.median(rng.choice(k, len(k))) for _ in range(4000)])
        pr("  %-5s | Ki_hat %6.1f   [%6.1f, %6.1f]                 | [%6.1f, %6.1f]       | n %3d, |excess| %3.0f, ramp %5.0f ct/s"
           % (tag, np.median(k), np.percentile(bs, 2.5), np.percentile(bs, 97.5),
              np.percentile(k, 25), np.percentile(k, 75), len(k), np.median(exs), np.median(ramps)))

    # =============================================================================== (h)
    pr("\n" + "=" * 165)
    pr("(h) HANDS-ON OVERRIDE AT idx 40-84 -- an independent second read (safety-relevant).")
    pr("  'Hands on' = |tq_raw| >= 1000 raw.  Reported: tap |T| percentiles, the fraction at/near the 2462 tap cap,")
    pr("  P(|T| >= 2400), and the driver-torque jerk p95 (d|bar|/dt) in the same frames.")
    pr("=" * 165)
    pr("  %-5s | %-52s | %-30s | %s" % ("route", "tap |T| p50 / p90 / p95 / max  (secs)", "P(|T|>=2400) / P(>=2000)", "bar jerk p95 raw/s"))
    for tag in ALL:
        r = routes[tag]
        m = r.eng & (r.idx >= 40) & (r.idx < 84) & (np.abs(r.tq_raw) >= 1000)
        if m.sum() < 30:
            pr("  %-5s | only %.1f s" % (tag, m.sum() / FS)); continue
        T = np.abs(r.T_meas[m])
        jerk = np.abs(np.gradient(np.abs(r.tq_raw), 1 / FS))[m]
        pr("  %-5s | %6.0f / %6.0f / %6.0f / %6.0f   (%5.1f s)          | %.4f / %.4f              | %6.0f"
           % (tag, np.median(T), np.percentile(T, 90), np.percentile(T, 95), T.max(), m.sum() / FS,
              float(np.mean(T >= 2400)), float(np.mean(T >= 2000)), np.percentile(jerk, 95)))
    pr()
    pr("  Same, with the STRONG-TURN gate the other agent used (|angle| >= 30) so the two reads are comparable:")
    pr("  %-5s | %-52s | %-30s | %s" % ("route", "tap |T| p50 / p90 / p95 / max  (secs)", "P(|T|>=2400) / P(>=2000)", "bar jerk p95 raw/s"))
    for tag in ALL:
        r = routes[tag]
        m = r.eng & (r.idx >= 40) & (r.idx < 84) & (np.abs(r.tq_raw) >= 1000) & (np.abs(r.ang) >= 30)
        if m.sum() < 30:
            pr("  %-5s | only %.1f s" % (tag, m.sum() / FS)); continue
        T = np.abs(r.T_meas[m])
        jerk = np.abs(np.gradient(np.abs(r.tq_raw), 1 / FS))[m]
        pr("  %-5s | %6.0f / %6.0f / %6.0f / %6.0f   (%5.1f s)          | %.4f / %.4f              | %6.0f"
           % (tag, np.median(T), np.percentile(T, 90), np.percentile(T, 95), T.max(), m.sum() / FS,
              float(np.mean(T >= 2400)), float(np.mean(T >= 2000)), np.percentile(jerk, 95)))

    out = os.path.join(HERE, "_scratch", "v283_ki_risetime.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
