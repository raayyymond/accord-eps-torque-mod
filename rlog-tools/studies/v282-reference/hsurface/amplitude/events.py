# -*- coding: utf-8 -*-
"""SECTION P -- the amplitude question in the TIME DOMAIN, on the shared library's own events.

A third, independent estimator: v282cmp.jerk_events / accel_events define the events, and the
tracking quality of each event is measured directly on the time series.  Events are then STRATIFIED
BY THEIR OWN SIZE, which is the amplitude axis in its most literal form.  A saturating actuator must
degrade the BIG events; a friction/deadband must degrade the SMALL ones.

Metrics per event (no spectra, no model):
  gain        v282cmp.event_metrics regression of achieved on lag-aligned desired
  nrms        RMS(achieved - desired) / RMS(desired - its mean) over the window  (scale free)
  resid       mean (achieved - desired) over +1.5..+2.5 s after the jerk peak, divided by the step
              -- the REPORT's "still +14 % of the step standing at 1.5-2.5 s" statistic
  railfr      fraction of the event window at |output| >= 0.98

ANALYSIS ONLY.  Run: python events.py
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dflib as D            # noqa: E402
import v282cmp as C          # noqa: E402

GROUPS = {"V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
          "V282old": ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4"],
          "TQall": ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
                    "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]}
LOG = []


def pr(s=""):
    print(s, flush=True)
    LOG.append(s)


def collect(rk, ach="la_pose", vmin=5.0):
    S = C.load(rk)
    out = np.abs(np.nan_to_num(S["out"]))
    ev, j = C.jerk_events(S, jerk_thr=0.8, vmin=vmin)
    rows = []
    for e in ev:
        k = e["idx"]
        i0, i1 = k - int(1.5 * C.FS), k + int(3.0 * C.FS)
        m = C.event_metrics(S, i0, i1, ach_key=ach)
        x = np.nan_to_num(S["model"][i0:i1]); y = np.nan_to_num(S[ach][i0:i1])
        sd = float(np.std(x - x.mean()))
        a, b = k + int(1.5 * C.FS) - i0, k + int(2.5 * C.FS) - i0
        step = e["la_step"]
        rows.append(dict(route=rk, v=e["v"], jerk=abs(e["jerk_peak"]), step=abs(step),
                         peak=e["la_peak"], gain=m["gain"],
                         nrms=float(np.sqrt(np.mean((y - x) ** 2)) / max(sd, 1e-6)),
                         resid=(float(np.mean(y[a:b] - x[a:b])) / step if abs(step) > 0.2 else np.nan),
                         railfr=float((out[i0:i1] >= 0.98).mean()),
                         outmax=float(out[i0:i1].max())))
    del S
    return rows


ALL = {}
for g, rks in GROUPS.items():
    ALL[g] = [r for rk in rks for r in collect(rk)]

pr("=" * 128)
pr("SECTION P   HIGH-JERK EVENT TRACKING, STRATIFIED BY EVENT SIZE (time domain, no spectra)")
pr("=" * 128)
pr("Events: local peaks of |d/dt of the 2 Hz-lowpassed model lateral accel| >= 0.8 m/s^3, v >= 5 m/s,")
pr("whole [-1.5, +3.0] s window laterally engaged, hands off, no clock gap (v282cmp.jerk_events).")
pr("Achieved = livePose yaw x v.  Strata are terciles of the event's own |step| pooled over groups.")
pr("")
pool = [r["step"] for g in ALL for r in ALL[g]]
ed = [0.0] + [float(q) for q in np.percentile(pool, [33, 67, 90])] + [1e9]
pr(f"{'|step| m/s2':>14s} {'group':>8s} {'n':>5s} {'med step':>9s} {'med jerk':>9s} {'gain':>6s} "
   f"{'nrms':>6s} {'resid@1.5-2.5s':>15s} {'rail%':>7s} {'max|out|':>9s} {'med v':>6s}")
for k in range(len(ed) - 1):
    for g in ("V282", "V282old", "TQall"):
        rs = [r for r in ALL[g] if ed[k] <= r["step"] < ed[k + 1]]
        if len(rs) < 5:
            pr(f"{f'{ed[k]:.2f}-{min(ed[k+1],99):.2f}':>14s} {g:>8s} {len(rs):5d}   -- n too thin --")
            continue
        res = [r["resid"] for r in rs if not np.isnan(r["resid"])]
        pr(f"{f'{ed[k]:.2f}-{min(ed[k+1],99):.2f}':>14s} {g:>8s} {len(rs):5d} "
           f"{np.median([r['step'] for r in rs]):9.2f} {np.median([r['jerk'] for r in rs]):9.2f} "
           f"{np.median([r['gain'] for r in rs]):6.2f} {np.median([r['nrms'] for r in rs]):6.2f} "
           f"{(np.median(res) if res else float('nan')):+15.3f} "
           f"{100*np.mean([r['railfr'] > 0 for r in rs]):7.2f} "
           f"{np.max([r['outmax'] for r in rs]):9.3f} {np.median([r['v'] for r in rs]):6.1f}")
    pr("")

pr("Same, split by speed as well (>=15 m/s only -- the band the REPORT's event numbers came from):")
pr(f"{'|step| m/s2':>14s} {'group':>8s} {'n':>5s} {'gain':>6s} {'nrms':>6s} {'resid':>8s} "
   f"{'max|out|':>9s}")
for k in range(len(ed) - 1):
    for g in ("V282", "TQall"):
        rs = [r for r in ALL[g] if ed[k] <= r["step"] < ed[k + 1] and r["v"] >= 15]
        if len(rs) < 5:
            continue
        res = [r["resid"] for r in rs if not np.isnan(r["resid"])]
        pr(f"{f'{ed[k]:.2f}-{min(ed[k+1],99):.2f}':>14s} {g:>8s} {len(rs):5d} "
           f"{np.median([r['gain'] for r in rs]):6.2f} {np.median([r['nrms'] for r in rs]):6.2f} "
           f"{(np.median(res) if res else float('nan')):+8.3f} "
           f"{np.max([r['outmax'] for r in rs]):9.3f}")
pr("")
pr("Correlation of the tracking metrics with event size WITHIN each group (Spearman rho):")
for g in ("V282", "V282old", "TQall"):
    rs = ALL[g]
    s = np.array([r["step"] for r in rs])
    for k in ("gain", "nrms"):
        y = np.array([r[k] for r in rs])
        ok = np.isfinite(y)
        rk1 = np.argsort(np.argsort(s[ok])); rk2 = np.argsort(np.argsort(y[ok]))
        rho = float(np.corrcoef(rk1, rk2)[0, 1])
        pr(f"   {g:8s} n={int(ok.sum()):4d}  rho(|step|, {k:5s}) = {rho:+.3f}")
pr("")
pr("Number of events whose window contains ANY railed frame, and the largest |output| reached:")
for g in ("V282", "V282old", "TQall"):
    rs = ALL[g]
    pr(f"   {g:8s} {len(rs):4d} events, {sum(1 for r in rs if r['railfr']>0):3d} contain a railed frame, "
       f"max |output| over all events {max(r['outmax'] for r in rs):.3f}")

with open(os.path.join(HERE, "EVENTS-OUT.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG) + "\n")
