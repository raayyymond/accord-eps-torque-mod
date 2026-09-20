# -*- coding: utf-8 -*-
"""p4 -- INTERLOCKS.  Is the probe provably bounded, or only small?

Measured on the raw per-route cache, ONE ROUTE AT A TIME (RAM).  For every interlock the
question is the same: how much headroom exists TODAY, so that a probe of amplitude a_u
(command units) is bounded to consume a known fraction of it.

  1. |output| rail at 1.0            -- distribution of |out|, and P(|out| > 1 - a_u)
  2. Honda command rate limit        -- 0.03 per 10 ms frame on the normalised command.
                                        distribution of |d out| per frame, and the headroom.
  3. steer_limited_by_safety / sat   -- how often the command is already being cut
  4. driver torque / hands-on        -- how fast a hands-on event arrives, i.e. how long the
                                        probe can still be running after the driver grabs the wheel
  5. disengage                       -- what fraction of engaged runs end in a disengage, and the
                                        state the probe would have to reset
  6. |out| step at engage/disengage  -- the existing worst-case transient the probe must not add to
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402

FS = 100.0
RATE_LIMIT = 0.03            # per frame, normalised command units (brief: 0.03/frame = 3 torque/s)
ROUTES_T = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
            "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
ROUTES_V = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
VMIN = 15.0


def q(x, p):
    return float(np.percentile(x, p)) if len(x) else float("nan")


def do(route):
    S = V.load(route)
    t, v = S["t"], S["v"]
    eng = S["active"]
    m = eng & ~S["pressed"] & (v >= VMIN) & np.isfinite(S["out"])
    out = np.nan_to_num(S["out"])
    dout = np.diff(out, prepend=out[0])
    dok = np.concatenate([[False], np.diff(t) < 0.02]) & m
    au = np.abs(out[m])
    du = np.abs(dout[dok])
    sat = S["sat"]
    # hands-on arrival: for each engaged >=15 m/s hands-off run, how long until pressed goes true
    hands = []
    for a, b in V.runs(eng & (v >= VMIN), t, min_s=2.0):
        p = S["pressed"][a:b]
        if p.any():
            k = int(np.argmax(p))
            if k > 0:
                hands.append(float(t[a + k] - t[a]))
    # disengage transient: |out| in the last frame before active goes false
    dis = []
    ai = np.where(np.diff(eng.astype(int)) == -1)[0]
    for k in ai:
        if v[k] >= VMIN and np.isfinite(out[k]):
            dis.append(abs(float(out[k])))
    r = dict(route=route, group=S["meta"].get("group", "?"), n=int(m.sum()), sec=float(m.sum() / FS),
             out_p50=q(au, 50), out_p99=q(au, 99), out_p999=q(au, 99.9), out_max=float(au.max()) if len(au) else np.nan,
             frac_gt_090=float(np.mean(au > 0.90)), frac_gt_095=float(np.mean(au > 0.95)),
             frac_gt_0999=float(np.mean(au > 0.999)),
             du_p50=q(du, 50), du_p99=q(du, 99), du_p999=q(du, 99.9),
             du_max=float(du.max()) if len(du) else np.nan,
             frac_du_gt_lim=float(np.mean(du >= RATE_LIMIT - 1e-9)),
             frac_du_gt_half=float(np.mean(du >= 0.5 * RATE_LIMIT)),
             sat_frac=float(np.mean(sat[m])) if m.any() else np.nan,
             n_hands=len(hands), hands_p05=q(hands, 5), hands_p50=q(hands, 50),
             n_diseng=len(dis), dis_p50=q(dis, 50), dis_max=max(dis) if dis else np.nan,
             storque_p99=q(np.abs(np.nan_to_num(S["storque"][m])), 99))
    del S
    return r


def main():
    print("=" * 132)
    print("INTERLOCK HEADROOM, engaged + hands off + >= 15 m/s")
    hdr = (f"{'route':22s} {'grp':6s} {'sec':>7s} | {'|u|p50':>7s} {'p99':>6s} {'p99.9':>6s} {'max':>6s}"
           f" {'>.95':>7s} {'>.999':>7s} | {'|du|p50':>8s} {'p99':>7s} {'p99.9':>7s} {'max':>7s}"
           f" {'>=lim':>7s} {'>=lim/2':>8s} | {'sat':>6s}")
    print(hdr)
    rows = []
    for r in ROUTES_T + ROUTES_V:
        try:
            R = do(r)
        except Exception as e:  # noqa: BLE001
            print(f"{r}: {e}")
            continue
        rows.append(R)
        print(f"{R['route']:22s} {R['group']:6s} {R['sec']:7.1f} | {R['out_p50']:7.3f} {R['out_p99']:6.3f}"
              f" {R['out_p999']:6.3f} {R['out_max']:6.3f} {R['frac_gt_095']:7.5f} {R['frac_gt_0999']:7.5f}"
              f" | {R['du_p50']:8.5f} {R['du_p99']:7.5f} {R['du_p999']:7.5f} {R['du_max']:7.5f}"
              f" {R['frac_du_gt_lim']:7.5f} {R['frac_du_gt_half']:8.5f} | {R['sat_frac']:6.4f}")

    print()
    print("=" * 132)
    print("HANDS-ON / DISENGAGE")
    print(f"{'route':22s} {'grp':6s} {'n_hands':>8s} {'t_p05 s':>8s} {'t_p50 s':>8s}"
          f" {'n_diseng':>9s} {'|u|@dis p50':>12s} {'max':>6s} {'|Tdrv| p99':>11s}")
    for R in rows:
        print(f"{R['route']:22s} {R['group']:6s} {R['n_hands']:8d} {R['hands_p05']:8.2f} {R['hands_p50']:8.2f}"
              f" {R['n_diseng']:9d} {R['dis_p50']:12.3f} {R['dis_max']:6.3f} {R['storque_p99']:11.4f}")

    print()
    print("=" * 132)
    print("WHAT A PROBE OF COMMAND AMPLITUDE a_u COSTS EACH INTERLOCK")
    print("  rail:  needs  |u| + a_u < 1.0    -> the binding statistic is P(|u| > 1 - a_u)")
    print("  slew:  needs  |du| + 2*pi*f*a_u/100 < 0.03  at f = 2.0 Hz -> per-frame cost = a_u * 0.1257")
    tg = [R for R in rows if R["group"] in ("T64", "T64B", "T5", "T4")]
    au_p999 = max(R["out_p999"] for R in tg)
    du_p999 = max(R["du_p999"] for R in tg)
    print(f"\n  worst torque-mode p99.9 over the five routes: |u| = {au_p999:.3f},  |du| = {du_p999:.5f} /frame")
    print(f"  {'a_u':>7s} {'rail margin':>12s} {'slew add/frame':>15s} {'slew total p99.9':>17s} {'% of 0.03':>10s}")
    for a_u in (0.002, 0.005, 0.01, 0.02, 0.05, 0.10):
        slew_add = a_u * 2 * np.pi * 2.0 / FS
        print(f"  {a_u:7.3f} {1.0 - au_p999 - a_u:12.3f} {slew_add:15.5f} {du_p999 + slew_add:17.5f}"
              f" {100 * (du_p999 + slew_add) / RATE_LIMIT:10.1f}")


if __name__ == "__main__":
    main()
