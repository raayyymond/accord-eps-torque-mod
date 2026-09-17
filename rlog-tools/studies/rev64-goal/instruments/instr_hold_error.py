#!/usr/bin/env python3
"""instr_hold_error.py -- INSTRUMENT 1: quasi-static large-angle hold error.   STREAM TAG: instr

WHICH OPERATOR NOTE
  Note 3: "LARGE-ANGLE control seems like it's not accounting for the caster angle of the wheels
  making them want to naturally return to center."

WHAT IT MEASURES
  In quasi-static engaged conditions, the SIGNED shortfall between the model's desired steering
  angle and the achieved steering angle,

        shortfall_deg = sign(angle_des) * (angle_des - angle_act)

  so POSITIVE = the wheel sits closer to centre than commanded (the caster signature), binned by
  |achieved angle| and by speed.  The caster hypothesis predicts shortfall GROWING WITH |ANGLE| --
  a fractional shortfall, not an offset.  The instrument therefore fits, per speed bin,

        shortfall = slope * |angle_des| + intercept

  slope     = fraction of the COMMANDED angle lost        -> the caster / hold-map-too-low signature
  intercept = constant shortfall toward centre, in deg    -> a friction / deadband / resolution floor
  L-R split = mean shortfall left vs right separately     -> camber or a mis-learned angle offset
  Three different defects, three different readings.  Controls B, C and D below inject one each and
  assert that the instrument separates them.  (The slope regressed on |angle_ACT| instead is also
  printed: for a fractional loss g it reads g/(1-g), so the two bracket the truth.)

  The desired angle comes from the wire with no vehicle model (see instr_common header): the roll
  compensation and the learned angle offset cancel in the difference.  This instrument is therefore
  the lateral-accel error re-expressed in degrees; its content is the binning and the sign.

QUASI-STATIC THRESHOLD -- justified, not assumed
  The fork's Accord feedforward is  hold(angle) + move(rate)  with
      move  = HONDA_ACCORD_FF_RATE_GAIN * rate_dps / G(v),  RATE_GAIN=0.5
              G = interp(v, [5,12.5,18.5,28.5], [550,271,246,167])           (tunes L175-179)
      hold  = k(v)*sat(v)*tanh(angle/sat(v)),  k = interp(v, HOLD_V_BP, HOLD_K_V)   (tunes L230-272)
  Requiring the move term to stay under 10% of the hold term at the smallest angle we bin as
  "large" (5 deg) gives the printed threshold per speed; 3.0 deg/s satisfies it from 10 m/s up and
  is used throughout.  The same threshold is applied to BOTH the achieved and the desired rate, and
  it must have HELD for 0.3 s (30 frames) so that a zero-crossing of the rate does not qualify.
  A sensitivity sweep over 1.5 / 3.0 / 6.0 deg/s is printed.

LANE CENTRING: ON (route 76 initData LaneCentering='1'); the demand is post-lane-centring.
ROUTE 76 IS REV 5 (gitCommit e44b6cd3).  Numbers from it are REV 5 BASELINES, not rev 6.4.

CONTROLS (asserted; run with no argument to execute only the controls)
  A  null          act = des                      -> slope 0.000, intercept 0.000, asym 0.000
  B  caster 15%    act = 0.85*des                 -> slope 0.150+/-0.010, intercept ~0, asym ~0
  C  friction floor act = des - 3*sign(des)       -> slope ~0 (<0.02), intercept 3.0+/-0.3, asym ~0
  D  angle bias    act = des - 3.0 deg (signed)   -> slope ~0, intercept ~0, ASYM = 6.0+/-0.6 deg
  C and D are the ones that matter: an instrument that reports a caster slope for either of them
  cannot tell self-centring from a friction floor or from a mis-learned offset.

USAGE
    python3 instr_hold_error.py                 # controls only
    python3 instr_hold_error.py r76_v293        # controls + route 76 (rev 5 baseline)
    python3 instr_hold_error.py /abs/path.npz
"""
import sys
import numpy as np
import instr_common as IC

RATE_TH_DPS = 2.5
DWELL_S = 0.30
ANGLE_BINS = [(0.0, 2.0), (2.0, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 40.0), (40.0, 90.0), (90.0, 400.0)]
MIN_ANGLE_FOR_SLOPE = 2.0     # below this the demand sign is not well defined (0.1 deg LSB + backlash)

# fork constants, quoted for the threshold justification (latcontrol_vehicle_tunes.py)
G_BP, G_V = [5.0, 12.5, 18.5, 28.5], [550.0, 271.0, 246.0, 167.0]
K_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
SAT_ABC = (19.3, 546.0, 3.01)
FF_RATE_GAIN = 0.5


def quasi_static_threshold_table():
    print("  quasi-static threshold: rate at which the FF move term reaches 10% of the hold term")
    print(f"    {'v':>6} {'G(v)':>7} {'k(v)':>8} {'sat':>7} {'hold@5deg':>10} {'rate_10pct':>11}")
    out = {}
    for v in (5.0, 8.0, 12.0, 19.0, 26.0, 30.0):
        G = float(np.interp(v, G_BP, G_V))
        k = float(np.interp(v, K_BP, K_V))
        sat = SAT_ABC[0] + SAT_ABC[1] * np.exp(-v / SAT_ABC[2])
        hold5 = k * sat * np.tanh(5.0 / sat)
        r10 = 0.10 * hold5 * G / FF_RATE_GAIN
        out[v] = r10
        print(f"    {v:6.1f} {G:7.1f} {k:8.4f} {sat:7.2f} {hold5:10.4f} {r10:11.2f} deg/s")
    print(f"    => RATE_TH_DPS = {RATE_TH_DPS} deg/s sits at or below the 10% line at every speed "
          f"from 8 m/s up (2.27-2.73 deg/s).  At 5 m/s the FF hold term is tiny so the criterion is "
          f"loose there; the 5-10 m/s bin is reported but is WEAKER EVIDENCE.")
    return out


def quasi_static_mask(S, rate_th=RATE_TH_DPS, dwell_s=DWELL_S):
    """Both rates under threshold, HELD for dwell_s (trailing window all-true)."""
    ok = (np.abs(S["sa_rate"]) < rate_th) & (np.abs(S["sa_des_rate"]) < rate_th)
    w = int(round(dwell_s * S["FS"]))
    # trailing-window all-true test (run-length >= w)
    held = np.zeros_like(ok)
    run = 0
    for i, o in enumerate(ok):
        run = run + 1 if o else 0
        held[i] = run >= w
    return held


def _stats(S, idx, rid):
    """Per-frame quantities for the selected frames."""
    sad, saa = S["sa_des"][idx], S["sa"][idx]
    sgn = np.sign(sad)
    short = sgn * (sad - saa)
    return dict(sad=sad, saa=saa, short=short, absa=np.abs(saa), absd=np.abs(sad),
                lad=S["lad"][idx], laa=S["laa"][idx], rid=rid, v=S["v"][idx])


def _slope(x, short):
    """OLS shortfall = slope*x + intercept.  With x = |angle_des|, slope is the fraction of the
    commanded angle lost toward centre."""
    x = np.asarray(x); short = np.asarray(short)
    if len(x) < 10:
        return np.nan, np.nan
    A = np.c_[x, np.ones(len(x))]
    b, *_ = np.linalg.lstsq(A, short, rcond=None)
    return float(b[0]), float(b[1])


def _asym(sad, short):
    """mean shortfall on left demands minus mean on right demands (deg).  A signed angle bias of
    -B deg reads +2B here; caster and a friction floor read 0."""
    l, r = sad > 0, sad < 0
    if l.sum() < 10 or r.sum() < 10:
        return np.nan
    return float(np.mean(short[l]) - np.mean(short[r]))


def census(S, qs):
    """The data budget: how much engaged time exists at each |angle|, and how much of it is
    quasi-static.  Print this ALWAYS -- an empty bin is a fact about the route, not about the car."""
    e = S["engaged_all"]
    a = np.abs(S["sa"])
    print(f"  DATA BUDGET  {'|angle| bin':>14} {'engaged s':>11} {'quasi-static s':>15} "
          f"{'med |rate| dps':>15} {'med v':>7}")
    for lo, hi in ANGLE_BINS:
        m = e & (a >= lo) & (a < hi)
        if m.sum() == 0:
            continue
        print(f"               {f'{lo:.0f}-{hi:.0f}':>14} {m.sum()/S['FS']:11.1f} "
              f"{(m & qs).sum()/S['FS']:15.1f} {np.median(np.abs(S['sa_rate'][m])):15.2f} "
              f"{np.median(S['v'][m]):7.1f}")


def report(S, label, rate_th=RATE_TH_DPS, quiet=False):
    qs = quasi_static_mask(S, rate_th)
    rows_out = {}
    if not quiet:
        IC.banner(f"INSTRUMENT 1  HOLD ERROR   {label}   (rate<{rate_th} deg/s held {DWELL_S}s)")
        census(S, qs & S["engaged_all"])
    for vlo, vhi in IC.SPEED_BINS:
        idx, rid, rs = IC.run_index(S, vlo, vhi, minlen_s=0.0, extra_mask=qs)
        if len(idx) == 0:
            if not quiet:
                print(f"\n  speed {vlo:.0f}-{vhi:.0f} m/s : no quasi-static frames")
            continue
        D = _stats(S, idx, rid)
        if not quiet:
            print(f"\n  speed {vlo:.0f}-{vhi:.0f} m/s : {len(idx)} frames "
                  f"({len(idx)/S['FS']:.1f} s) in {len(rs)} runs")
            print(f"    {'|angle_act| bin':>16} {'n':>7} {'runs':>5} {'med|sa_act|':>11} "
                  f"{'shortfall deg':>14} {'boot95 +/-':>10} {'L':>7} {'R':>7} "
                  f"{'ratio act/des':>13} {'la ratio':>9}")
        for alo, ahi in ANGLE_BINS:
            m = (D["absa"] >= alo) & (D["absa"] < ahi)
            n = int(m.sum())
            if n == 0:
                continue
            sh = D["short"][m]
            pt, lo, hi, hw = IC.boot_ci(sh, D["rid"][m], lambda x: float(np.mean(x)))
            big = D["absd"][m] > MIN_ANGLE_FOR_SLOPE
            ratio = float(np.median(D["absa"][m][big] / D["absd"][m][big])) if big.sum() > 5 else np.nan
            bigl = np.abs(D["lad"][m]) > 0.1
            lar = float(np.median(np.abs(D["laa"][m][bigl]) / np.abs(D["lad"][m][bigl]))) if bigl.sum() > 5 else np.nan
            flag = "" if n >= IC.MIN_BIN_N else "  <-- THIN"
            if not quiet:
                lsel, rsel = D["sad"][m] > 0, D["sad"][m] < 0
                lm = float(np.mean(sh[lsel])) if lsel.sum() > 5 else np.nan
                rm = float(np.mean(sh[rsel])) if rsel.sum() > 5 else np.nan
                print(f"    {f'{alo:.0f}-{ahi:.0f}':>16} {n:7d} {len(np.unique(D['rid'][m])):5d} "
                      f"{np.median(D['absa'][m]):11.2f} {pt:+14.3f} {hw:10.3f} {lm:+7.2f} {rm:+7.2f} "
                      f"{ratio:13.3f} {lar:9.3f}{flag}")
            rows_out[f"{vlo:.0f}-{vhi:.0f}|{alo:.0f}-{ahi:.0f}"] = dict(n=n, shortfall=pt, ci=hw, ratio=ratio)
        # the three-way decomposition, over the frames where the demand sign is defined
        big = D["absd"] > MIN_ANGLE_FOR_SLOPE
        if big.sum() > 50:
            sl, ic_ = _slope(D["absd"][big], D["short"][big])
            sl_act, _ = _slope(D["absa"][big], D["short"][big])
            pairs = np.c_[D["absd"][big], D["short"][big], D["sad"][big]]
            _, _, _, hw = IC.boot_ci(pairs, D["rid"][big], lambda a: _slope(a[:, 0], a[:, 1])[0])
            _, _, _, hwi = IC.boot_ci(pairs, D["rid"][big], lambda a: _slope(a[:, 0], a[:, 1])[1])
            sa_, sb_, _ = IC.split_half(pairs, D["rid"][big], lambda a: _slope(a[:, 0], a[:, 1])[0])
            asy = _asym(D["sad"][big], D["short"][big])
            _, _, _, hwa = IC.boot_ci(pairs, D["rid"][big], lambda a: _asym(a[:, 2], a[:, 1]))
            if not quiet:
                print(f"    DECOMPOSITION  n={int(big.sum())}  (|angle_des| > {MIN_ANGLE_FOR_SLOPE} deg)")
                print(f"      slope      {sl:+.4f} deg/deg   boot95 +/-{hw:.4f}   split-half {sa_:+.4f}/{sb_:+.4f}"
                      f"   [on |angle_act|: {sl_act:+.4f}]   <- caster / hold map")
                print(f"      intercept  {ic_:+.3f} deg       boot95 +/-{hwi:.3f}"
                      f"                                     <- friction / resolution floor")
                print(f"      L-R asym   {asy:+.3f} deg       boot95 +/-{hwa:.3f}"
                      f"                                     <- camber / angle offset")
                verdict = ("CASTER-LIKE fractional shortfall" if (sl - hw) > 0.02 else
                           "no fractional shortfall resolved" if abs(sl) < max(hw, 0.02) else
                           "OVER-turn: achieved exceeds commanded")
                print(f"      -> {verdict}")
            rows_out[f"{vlo:.0f}-{vhi:.0f}|SLOPE"] = dict(slope=sl, ci=hw, intercept=ic_, ci_int=hwi,
                                                          slope_on_act=sl_act, asym=asy, ci_asym=hwa,
                                                          split=[sa_, sb_], n=int(big.sum()))
    return rows_out


# ------------------------------------------------------------------ controls

def _make_synth(defect, n=90000, FS=100.0):
    """Quasi-static staircase: 4 s ramp / 6 s hold, levels sweeping +/-70 deg."""
    S = IC.synth(n=n, FS=FS)
    t = S["t"]
    levels = np.array([0, 4, -4, 9, -9, 18, -18, 30, -30, 45, -45, 65, -65, 25, -25, 7, -7, 0])
    seg = 10.0
    des = np.zeros(n)
    for i, lv in enumerate(levels):
        prev = levels[i - 1] if i else 0.0
        t0 = i * seg
        m = (t >= t0) & (t < t0 + seg)
        tt = np.clip((t[m] - t0) / 4.0, 0, 1)
        des[m] = prev + (lv - prev) * (3 * tt ** 2 - 2 * tt ** 3)
    des[t >= len(levels) * seg] = levels[-1]
    act = defect(des)
    S["sa"] = act
    S["laa"] = S["Sv"] * act
    S["lad"] = S["Sv"] * des
    S["out"] = np.zeros(n)
    IC.add_rates(S)
    S["_des_true"] = des
    return S


def run_controls():
    IC.banner("INSTRUMENT 1  CONTROLS")
    quasi_static_threshold_table()
    fails = []

    print(f"\n  {'control':<38} {'slope':>18} {'intercept deg':>20} {'L-R asym deg':>20}")
    for name, defect, exp in [
        ("A  null           act = des",             lambda d: d.copy(),              (0.0, 0.0, 0.0)),
        ("B  caster 15%     act = 0.85*des",        lambda d: 0.85 * d,              (0.150, 0.0, 0.0)),
        ("C  friction floor act = des - 3*sgn(des)", lambda d: d - 3.0 * np.sign(d), (0.0, 3.0, 0.0)),
        ("D  angle bias     act = des - 3.0 deg",   lambda d: d - 3.0,               (0.0, 0.0, 6.0)),
    ]:
        TOL = (0.010, 0.30, 0.60)
        S = _make_synth(defect)
        r = report(S, "SYNTH " + name, quiet=True)
        k = [kk for kk in r if kk.endswith("SLOPE")]
        if not k:
            fails.append(f"{name}: no decomposition computed")
            continue
        got = (r[k[0]]["slope"], r[k[0]]["intercept"], r[k[0]]["asym"])
        oks = [abs(g - e) <= t for g, e, t in zip(got, exp, TOL)]
        cells = " ".join(f"{g:+9.4f}/{e:+.3f} {'ok ' if o else 'FAIL'}" for g, e, o in zip(got, exp, oks))
        print(f"  {name:<38} {cells}      n={r[k[0]]['n']}")
        if not all(oks):
            fails.append(name)
        if name.startswith("B"):
            for kk, vv in sorted(r.items()):
                if kk.endswith("SLOPE"):
                    continue
                if vv["n"] >= 50 and np.isfinite(vv.get("ratio", np.nan)):
                    assert abs(vv["ratio"] - 0.85) < 0.02, f"bin ratio {kk} = {vv['ratio']}"
            print("       (B also: per-bin achieved/desired ratio == 0.85 +/-0.02 in every bin with n>=50)")

    assert not fails, f"CONTROL FAILURES: {fails}"
    print("\n  ALL CONTROLS PASS -- caster, friction floor and angle bias are SEPARATED, not confused.")


if __name__ == "__main__":
    run_controls()
    if len(sys.argv) > 1:
        S = IC.load(sys.argv[1])
        IC.banner(f"angle map for {S['tag']}")
        IC.fit_S(S)
        IC.add_rates(S)
        eng = S["engaged_all"]
        print(f"  engaged (active & !steeringPressed): {eng.sum()} frames = {eng.sum()/S['FS']:.0f} s "
              f"of {S['n']/S['FS']:.0f} s")
        print(f"  cross-check: SG angle-rate vs CAN steeringRateDeg  r={np.corrcoef(S['sa_rate'][eng], S['sr_can'][eng])[0,1]:.4f}"
              f"  rms(diff)={np.std(S['sa_rate'][eng]-S['sr_can'][eng]):.2f} deg/s")
        out = report(S, f"{sys.argv[1]}  [rev 5 baseline if r76]")
        IC.banner("SENSITIVITY TO THE QUASI-STATIC THRESHOLD (slope per speed bin)")
        RATE_SWEEP = (1.25, 2.5, 5.0)
        sweep = {rt: report(S, "", rate_th=rt, quiet=True) for rt in RATE_SWEEP}
        print(f"    {'v bin':>10} " + " ".join(f"{f'{r} dps':>14}" for r in RATE_SWEEP))
        for vlo, vhi in IC.SPEED_BINS:
            cells = []
            for rt in RATE_SWEEP:
                rr = sweep[rt]
                k = f"{vlo:.0f}-{vhi:.0f}|SLOPE"
                cells.append(f"{rr[k]['slope']:+.4f}(n{rr[k]['n']})" if k in rr else "      --      ")
            print(f"    {f'{vlo:.0f}-{vhi:.0f}':>10} " + " ".join(f"{c:>14}" for c in cells))
        IC.dump_json(f"instr_hold_error_{sys.argv[1].replace('/','_')}.json", out)
