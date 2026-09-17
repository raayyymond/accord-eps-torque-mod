#!/usr/bin/env python3
"""instr_jerk.py -- INSTRUMENT 3: jerk, commanded and delivered.   STREAM TAG: instr

WHICH OPERATOR NOTE
  Note 4: "LARGE-ANGLE control is still very jerky, not smooth and gradual."
  The complaint is about DISCRETE jerkiness, not broadband roughness, so this instrument reports two
  different things and never conflates them:
     (a) CONTINUOUS   RMS and p95 of three rate-of-change channels, binned by |angle| and speed
     (b) DISCRETE     a JERK-EVENT CENSUS -- isolated jumps above a threshold, with a refractory
                      window, counted per minute, with their size distribution, at 3 thresholds

CHANNELS
  cmd_rate   d(output torque)/dt        [output units per s]   -- what the controller asks for
  mod_jerk   d(la_model)/dt             [m/s^3]   -- the jerk THE MODEL demands (desiredCurvature*v^2,
                                                     post-lane-centring, PRE delay-comp and ref filter)
  dem_jerk   d(la_des)/dt               [m/s^3]   -- the jerk the tracked SETPOINT demands
                                                     (cs_la_des is `setpoint`, POST ref filter)
  lat_jerk   d(la_act)/dt               [m/s^3]                -- what the body feels
  wheel_acc  d2(steering angle)/dt2     [deg/s^2]              -- what the wheel does
  The first two are the fork's own doing; the last two are the fork's doing convolved with the plant.
  A rise in cmd_rate with no rise in lat_jerk is a command the EPS swallowed; the reverse is plant.
  *** The ROUGHNESS RATIO rms(lat_jerk)/rms(mod_jerk) is the headline. *** Raw delivered jerk rises
  with |angle| simply because large angles carry large commanded rates; the ratio removes that and
  asks the operator's actual question -- is the DELIVERED motion rougher than the DEMANDED one?
  Both ratios are printed: ROUGH_m against the MODEL demand (the operator's goal) and ROUGH_s
  against the tracked SETPOINT (the controller's own job).  They differ by the reference filter.

DERIVATIVE CONVENTION -- two, deliberately
  CONTINUOUS statistics use the same Savitzky-Golay derivative as the other two instruments
  (0.15 s, order 2), because a raw difference of a 0.1 deg-quantised angle is ~10 deg/s of pure LSB.
  The DISCRETE census uses the RAW frame-to-frame difference, because an SG filter SMEARS a step
  across its whole window and would turn one jump into a low broad bump.  Control N2 below asserts
  exactly this: the census must find a step that the SG channel has already smoothed away.

THRESHOLDS
  Absolute, printed, and swept over three values, because an adaptive threshold (e.g. a percentile
  of the route's own distribution) cannot show a build getting better -- it moves with the build.
  The sweep is reported so a future comparison can pick the one where both routes have counts.

NOISE FLOOR
  Reported three ways: bootstrap 95% CI over RUNS for every continuous statistic and for the event
  rate; odd/even split-half; and the QUANTISATION FLOOR -- the RMS each channel would read from the
  sensor LSB alone with a stationary wheel, printed beside the measured value.  A bin whose measured
  RMS is near its quantisation floor is measuring the sensor, not the car.

CONTROLS (asserted)
  P1  census recovers N=40 injected steps of known size on a smooth carrier: count 40 +/- 1,
      median recovered size within 5% of the injected size
  N1  smooth carrier + white noise at 1/3 of the threshold: census returns 0 events (no false alarms)
  N2  the SAME 40 steps read through the SG (continuous) channel produce a p95 well below the step
      size, i.e. the continuous channel alone CANNOT see them -> the census is not redundant
  P3  continuous RMS of a pure sinusoid a*sin(2 pi f t) equals a*2 pi f / sqrt(2) within 2%

LANE CENTRING: ON (route 76 initData LaneCentering='1').
ROUTE 76 IS REV 5 (gitCommit e44b6cd3).  Numbers from it are REV 5 BASELINES, not rev 6.4.

USAGE
    python3 instr_jerk.py                 # controls only
    python3 instr_jerk.py r76_v293        # controls + route 76 (rev 5 baseline)
"""
import sys
import numpy as np
import instr_common as IC

ANGLE_BINS = [(0.0, 2.0), (2.0, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 400.0)]
REFRACTORY_S = 0.20

# absolute census thresholds per channel, swept
THRESH = {
    "cmd_rate": (0.010, 0.020, 0.040),      # |d out| per frame, output units  (out is in [-1, 1])
    "mod_jerk": (0.010, 0.020, 0.040),      # |d la_model| per frame, m/s^2 per frame
    "dem_jerk": (0.010, 0.020, 0.040),      # |d la_des| per frame, m/s^2 per frame
    "lat_jerk": (0.010, 0.020, 0.040),      # |d la_act| per frame, m/s^2 per frame
    "wheel_acc": (0.20, 0.40, 0.80),        # |d rate| per frame, deg/s per frame
}
# sensor LSBs -> the quantisation floor of each channel
LSB = {"sa_deg": 0.1, "sr_deg": 1.0}


def channels(S):
    """Continuous (SG) and discrete (raw difference) versions of each channel."""
    FS = S["FS"]
    cont = dict(
        cmd_rate=S["out_rate"],
        mod_jerk=S["lam_rate"],
        dem_jerk=S["lad_rate"],
        lat_jerk=S["laa_rate"],
        wheel_acc=IC.sg_deriv(S["sa"], FS, S["rate_win_s"], order=2, deriv=2),
    )
    d = lambda x: np.concatenate([[0.0], np.diff(x)])
    disc = dict(cmd_rate=d(S["out"]), mod_jerk=d(S["lam"]), dem_jerk=d(S["lad"]), lat_jerk=d(S["laa"]),
                wheel_acc=d(S["sa_rate"]))
    return cont, disc


def quant_floor(S):
    """RMS each SG channel reads from sensor LSB alone (uniform LSB -> sigma = LSB/sqrt(12))."""
    FS, w = S["FS"], S["rate_win_s"]
    n = int(round(w * FS))
    n = max(n + (n + 1) % 2, 5)
    from scipy import signal as sps
    imp = np.zeros(4 * n + 1)
    imp[2 * n] = 1.0
    g1 = sps.savgol_filter(imp, n, 2, deriv=1, delta=1.0 / FS, mode="interp")
    g2 = sps.savgol_filter(imp, n, 2, deriv=2, delta=1.0 / FS, mode="interp")
    s_ang = LSB["sa_deg"] / np.sqrt(12.0)
    out = dict(
        wheel_acc=float(s_ang * np.sqrt(np.sum(g2 ** 2))),
        sa_rate=float(s_ang * np.sqrt(np.sum(g1 ** 2))),
    )
    # la_act is a linear function of the angle, so its LSB scales by |S(v)|
    out["lat_jerk_per_absS"] = float(s_ang * np.sqrt(np.sum(g1 ** 2)))
    return out


def census(x, thr, FS, refr_s=REFRACTORY_S):
    """Discrete jump census on a raw per-frame difference trace.
    An event is a local maximum of |x| above thr, with no other accepted event within refr_s."""
    a = np.abs(x)
    cand = np.flatnonzero(a > thr)
    if len(cand) == 0:
        return np.zeros(0, int), np.zeros(0)
    order = cand[np.argsort(-a[cand])]       # greedy: largest first
    refr = int(round(refr_s * FS))
    taken = []
    occupied = np.zeros(len(a), bool)
    for i in order:
        if occupied[i]:
            continue
        taken.append(i)
        occupied[max(0, i - refr):i + refr + 1] = True
    taken = np.array(sorted(taken))
    return taken, x[taken]


def report(S, label, quiet=False):
    cont, disc = channels(S)
    qf = quant_floor(S)
    out = {}
    if not quiet:
        IC.banner(f"INSTRUMENT 3  JERK   {label}")
        print(f"  SG window {S['rate_win_s']*1000:.0f} ms order 2.  Quantisation floor from the "
              f"{LSB['sa_deg']} deg angle LSB: wheel_acc {qf['wheel_acc']:.3f} deg/s^2 RMS, "
              f"angle-rate {qf['sa_rate']:.3f} deg/s RMS,")
        print(f"  lat_jerk floor = {qf['lat_jerk_per_absS']:.3f} * |S(v)| m/s^3 "
              f"(= {qf['lat_jerk_per_absS']*0.087:.4f} at 19 m/s, {qf['lat_jerk_per_absS']*0.172:.4f} at 27 m/s).")

    # ---------------- continuous, binned
    for vlo, vhi in IC.SPEED_BINS:
        idx, rid, rs = IC.run_index(S, vlo, vhi, minlen_s=0.5)
        if len(idx) < 100:
            continue
        if not quiet:
            print(f"\n  speed {vlo:.0f}-{vhi:.0f} m/s   {len(idx)/S['FS']:.0f} s engaged in {len(rs)} runs")
            print(f"    {'|angle| bin':>12} {'n':>7} {'runs':>5} "
                  f"{'cmd_rate rms':>13} {'p95':>8} {'mod rms':>8} {'dem rms':>8} "
                  f"{'lat_jerk rms':>13} {'p95':>8} "
                  f"{'ROUGH_m':>8} {'boot95':>7} {'ROUGH_s':>8} {'wheel_acc rms':>14} {'p95':>9} {'qfl':>6}")
        a = np.abs(S["sa"][idx])
        for alo, ahi in ANGLE_BINS:
            m = (a >= alo) & (a < ahi)
            n = int(m.sum())
            if n == 0:
                continue
            sel = idx[m]
            gid = rid[m]
            cells, rec = [], {}
            for ch in ("cmd_rate", "mod_jerk", "dem_jerk", "lat_jerk", "wheel_acc"):
                x = cont[ch][sel]
                _, _, _, rhw = IC.boot_ci(x, gid, IC.rms)
                _, _, _, phw = IC.boot_ci(x, gid, IC.p95)
                ra, rb, _ = IC.split_half(x, gid, IC.rms)
                cells.append((IC.rms(x), rhw, IC.p95(x), phw))
                rec[ch] = dict(rms=IC.rms(x), rms_ci=rhw, p95=IC.p95(x), p95_ci=phw, split=[ra, rb])
            f_ = lambda a: IC.rms(a[:, 0]) / max(IC.rms(a[:, 1]), 1e-9)
            pr = np.c_[cont["lat_jerk"][sel], cont["mod_jerk"][sel]]
            rough = f_(pr)
            _, _, _, rghw = IC.boot_ci(pr, gid, f_)
            rsa, rsb, _ = IC.split_half(pr, gid, f_)
            ps = np.c_[cont["lat_jerk"][sel], cont["dem_jerk"][sel]]
            rough_s = f_(ps)
            rec["roughness_vs_model"] = dict(ratio=rough, ci=rghw, split=[rsa, rsb])
            rec["roughness_vs_setpoint"] = dict(ratio=rough_s)
            qfl = qf["wheel_acc"]
            flag = "" if n >= IC.MIN_BIN_N else "  <-- THIN"
            if not quiet:
                print(f"    {f'{alo:.0f}-{ahi:.0f}':>12} {n:7d} {len(np.unique(gid)):5d} "
                      f"{cells[0][0]:8.4f}+-{cells[0][1]:.4f} {cells[0][2]:8.4f} "
                      f"{cells[1][0]:8.4f} {cells[2][0]:8.4f} "
                      f"{cells[3][0]:8.4f}+-{cells[3][1]:.4f} {cells[3][2]:8.4f} "
                      f"{rough:8.2f} {rghw:7.2f} {rough_s:8.2f} "
                      f"{cells[4][0]:9.2f}+-{cells[4][1]:.2f} {cells[4][2]:9.2f} {qfl:6.2f}{flag}")
            out[f"{vlo:.0f}-{vhi:.0f}|{alo:.0f}-{ahi:.0f}"] = dict(n=n, **rec)

    # ---------------- discrete census
    if not quiet:
        IC.banner("JERK-EVENT CENSUS (raw per-frame jumps, "
                  f"{REFRACTORY_S*1000:.0f} ms refractory, engaged only)")
    for vlo, vhi in IC.NOTE_BINS:
        idx, rid, rs = IC.run_index(S, vlo, vhi, minlen_s=0.5)
        if len(idx) < 200:
            continue
        mins = len(idx) / S["FS"] / 60.0
        if not quiet:
            print(f"\n  speed {vlo:.0f}-{vhi:.0f} m/s   {mins*60:.0f} s engaged")
            print(f"    {'channel':>10} {'thresh':>8} {'events':>7} {'per min':>8} {'boot95':>8} "
                  f"{'med size':>9} {'p90 size':>9} {'max':>9} {'med |angle|':>11}")
        for ch in ("cmd_rate", "mod_jerk", "dem_jerk", "lat_jerk", "wheel_acc"):
            for thr in THRESH[ch]:
                # census run by run so a run break cannot create an event
                ev_i, ev_s, ev_run = [], [], []
                for k, (a0, b0) in enumerate(rs):
                    ii, ss = census(disc[ch][a0:b0], thr, S["FS"])
                    ev_i += list(ii + a0)
                    ev_s += list(ss)
                    ev_run += [k] * len(ii)
                ev_i, ev_s, ev_run = np.array(ev_i, int), np.array(ev_s), np.array(ev_run, int)
                rate = len(ev_i) / max(mins, 1e-9)
                # bootstrap the rate over runs
                durs = np.array([(b0 - a0) / S["FS"] / 60.0 for a0, b0 in rs])
                cnts = np.array([int((ev_run == k).sum()) for k in range(len(rs))])
                pairs = np.c_[cnts, durs]
                _, _, _, hw = IC.boot_ci(pairs, np.arange(len(rs)),
                                         lambda p: float(p[:, 0].sum() / max(p[:, 1].sum(), 1e-9)))
                if not quiet:
                    if len(ev_s):
                        print(f"    {ch:>10} {thr:8.3f} {len(ev_i):7d} {rate:8.2f} {hw:8.2f} "
                              f"{np.median(np.abs(ev_s)):9.4f} {np.percentile(np.abs(ev_s),90):9.4f} "
                              f"{np.max(np.abs(ev_s)):9.4f} {np.median(np.abs(S['sa'][ev_i])):11.1f}")
                    else:
                        print(f"    {ch:>10} {thr:8.3f} {0:7d} {0.0:8.2f}")
                out[f"CENSUS|{vlo:.0f}-{vhi:.0f}|{ch}|{thr}"] = dict(
                    n=len(ev_i), per_min=rate, ci=hw,
                    med=float(np.median(np.abs(ev_s))) if len(ev_s) else None)
        # angle split of the census at the middle threshold -- the operator's note is LARGE angle
        if not quiet:
            print(f"\n    census by |angle|, middle threshold, cmd_rate + lat_jerk:")
            print(f"      {'|angle| bin':>12} {'s engaged':>10} {'cmd ev/min':>11} {'lat ev/min':>11}")
            a = np.abs(S["sa"][idx])
            for alo, ahi in ANGLE_BINS:
                m = (a >= alo) & (a < ahi)
                if m.sum() < 50:
                    continue
                secs = m.sum() / S["FS"]
                cells = []
                for ch in ("cmd_rate", "lat_jerk"):
                    thr = THRESH[ch][1]
                    tot = 0
                    for k, (a0, b0) in enumerate(rs):
                        ii, _ = census(disc[ch][a0:b0], thr, S["FS"])
                        ii = ii + a0
                        tot += int(((np.abs(S["sa"][ii]) >= alo) & (np.abs(S["sa"][ii]) < ahi)).sum())
                    cells.append(tot / (secs / 60.0))
                print(f"      {f'{alo:.0f}-{ahi:.0f}':>12} {secs:10.1f} {cells[0]:11.2f} {cells[1]:11.2f}")
    return out


# ------------------------------------------------------------------ controls

def run_controls():
    IC.banner("INSTRUMENT 3  CONTROLS")
    FS = 100.0
    n = 60000
    t = np.arange(n) / FS
    rng = np.random.default_rng(7)
    fails = []

    # P3  continuous RMS of a sinusoid
    aA, f = 0.30, 0.40
    S = IC.synth(n=n, FS=FS)
    S["out"] = aA * np.sin(2 * np.pi * f * t)
    S["sa"] = np.zeros(n)
    S["laa"] = np.zeros(n)
    S["lad"] = np.zeros(n)
    IC.add_rates(S)
    got = IC.rms(S["out_rate"][1000:-1000])
    exp = aA * 2 * np.pi * f / np.sqrt(2)
    ok = abs(got - exp) <= 0.02 * exp
    print(f"  P3 continuous RMS of a {f} Hz sinusoid: {got:.5f}  expect {exp:.5f}  "
          f"{'PASS' if ok else 'FAIL'}")
    if not ok:
        fails.append("P3")

    # P1 / N1 / N2  the census
    STEP, NSTEP, THR = 0.060, 40, 0.020
    carrier = 0.25 * np.sin(2 * np.pi * 0.20 * t) + 0.10 * np.sin(2 * np.pi * 0.7 * t + 1.0)
    pos = np.sort(rng.choice(np.arange(500, n - 500, 60), size=NSTEP, replace=False))
    steps = np.zeros(n)
    for p_ in pos:
        steps[p_:] += STEP * (1 if rng.random() < 0.5 else -1)
    noisy = carrier + steps + rng.normal(0, THR / 3.0 / 3.0, n)   # sigma = thr/9 -> ~0 false alarms

    ii, ss = census(np.concatenate([[0.0], np.diff(carrier + steps)]), THR, FS)
    okc = abs(len(ii) - NSTEP) <= 1 and abs(np.median(np.abs(ss)) - STEP) <= 0.05 * STEP
    print(f"  P1 census on {NSTEP} injected steps of {STEP}: found {len(ii)}, "
          f"median size {np.median(np.abs(ss)):.4f}  {'PASS' if okc else 'FAIL'}")
    if not okc:
        fails.append("P1")

    ii0, _ = census(np.concatenate([[0.0], np.diff(carrier + rng.normal(0, THR / 9.0, n))]), THR, FS)
    okn = len(ii0) == 0
    print(f"  N1 census on the carrier + noise, NO steps: found {len(ii0)} (expect 0)  "
          f"{'PASS' if okn else 'FAIL'}")
    if not okn:
        fails.append("N1")

    Sx = IC.synth(n=n, FS=FS)
    Sx["out"] = carrier + steps
    Sx["sa"] = np.zeros(n)
    Sx["laa"] = np.zeros(n)
    Sx["lad"] = np.zeros(n)
    IC.add_rates(Sx)
    sg_p95 = IC.p95(Sx["out_rate"]) / FS      # per-frame equivalent
    okn2 = sg_p95 < 0.5 * STEP
    print(f"  N2 the same steps through the SG channel: p95 per-frame equivalent {sg_p95:.4f} "
          f"vs the {STEP} step -- the continuous channel alone sees {sg_p95/STEP*100:.0f}% of it  "
          f"{'PASS' if okn2 else 'FAIL'}")
    if not okn2:
        fails.append("N2")

    assert not fails, f"CONTROL FAILURES: {fails}"
    print("\n  ALL CONTROLS PASS -- the census finds discrete jumps the continuous channel cannot, "
          "and does not invent them.")


if __name__ == "__main__":
    run_controls()
    if len(sys.argv) > 1:
        S = IC.load(sys.argv[1])
        IC.banner(f"angle map for {S['tag']}")
        IC.fit_S(S)
        IC.add_rates(S)
        print(f"  out (commanded torque) per-frame |diff|: p50 {np.percentile(np.abs(np.diff(S['out'][S['engaged_all']])),50):.5f}  "
              f"p95 {np.percentile(np.abs(np.diff(S['out'][S['engaged_all']])),95):.5f}  "
              f"p99.9 {np.percentile(np.abs(np.diff(S['out'][S['engaged_all']])),99.9):.5f}")
        out = report(S, f"{sys.argv[1]}  [rev 5 baseline if r76]")
        IC.dump_json(f"instr_jerk_{sys.argv[1].replace('/','_')}.json", out)
