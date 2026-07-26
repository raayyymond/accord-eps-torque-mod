"""
Wind/Unwind + unwind-strength analysis for lat-B tune (2026-05-28 drive).
Report-only. Reads carState / controlsState(pidState) / carControl across segments.
ROBUST: catches capnp.KjException per segment.
"""
import sys, math
from pathlib import Path
import capnp
sys.path.insert(0, str(Path(__file__).parent))
from rlog_parse import read_messages

ROUTES = {
    "mall_route0": [f"D:/drivedata/00000000--74efcd1ee3--{i}/rlog.zst" for i in range(6)],
    "road_route1": [f"D:/drivedata/00000001--638fd75d31--{i}/rlog.zst" for i in range(9)],
    "road_route2": [f"D:/drivedata/00000002--a6fcb0a223--{i}/rlog.zst" for i in range(5)],
}


def collect(seg_paths):
    """Return list of time-sorted sample dicts merged from carState/controlsState/carControl.
    We bucket by logMonoTime and forward-fill the most recent of each stream onto controlsState ticks."""
    rows = []  # (t_ns, stream, payload)
    for sp in seg_paths:
        if not Path(sp).exists():
            continue
        try:
            for evt in read_messages(sp):
                w = evt.which()
                t = evt.logMonoTime
                if w == "carState":
                    cs = evt.carState
                    rows.append((t, "cs", dict(
                        vEgo=cs.vEgo,
                        sAngle=cs.steeringAngleDeg,
                        sRate=cs.steeringRateDeg,
                        sTorque=cs.steeringTorque,
                        sTorqueEps=cs.steeringTorqueEps,
                        sPressed=cs.steeringPressed,
                        yaw=cs.yawRate,
                    )))
                elif w == "controlsState":
                    lcs = evt.controlsState.lateralControlState
                    if lcs.which() != "pidState":
                        continue
                    ps = lcs.pidState
                    rows.append((t, "ps", dict(
                        active=ps.active,
                        p=ps.p, i=ps.i, f=ps.f, output=ps.output,
                        angleError=ps.angleError,
                        saturated=ps.saturated,
                        psAngle=ps.steeringAngleDeg,
                        psDesired=ps.steeringAngleDesiredDeg,
                        psRate=ps.steeringRateDeg,
                        desiredCurv=evt.controlsState.desiredCurvature,
                        curv=evt.controlsState.curvature,
                    )))
                elif w == "carControl":
                    cc = evt.carControl
                    act = cc.actuators
                    rows.append((t, "cc", dict(
                        latActive=cc.latActive,
                        torque=act.torque,
                        torqueOutputCan=act.torqueOutputCan,
                        ccAngle=act.steeringAngleDeg,
                    )))
        except capnp.KjException as e:
            sys.stderr.write(f"  [skip truncated tail] {sp}: {e}\n")
        except Exception as e:
            sys.stderr.write(f"  [skip seg] {sp}: {e}\n")
    rows.sort(key=lambda r: r[0])

    # forward-fill onto a unified timeline anchored at controlsState (ps) ticks (~100Hz)
    last_cs, last_cc = {}, {}
    samples = []
    for t, stream, pay in rows:
        if stream == "cs":
            last_cs = pay
        elif stream == "cc":
            last_cc = pay
        elif stream == "ps":
            if not last_cs:
                continue
            s = {"t": t / 1e9}
            s.update({f"cs_{k}": v for k, v in last_cs.items()})
            s.update({f"cc_{k}": v for k, v in last_cc.items()})
            s.update({f"ps_{k}": v for k, v in pay.items()})
            samples.append(s)
    return samples


def engaged_segments(samples, min_len=30):
    """Split samples into contiguous engaged (latActive) runs."""
    runs, cur = [], []
    for s in samples:
        eng = s.get("cc_latActive", False) and s.get("ps_active", False)
        if eng:
            cur.append(s)
        else:
            if len(cur) >= min_len:
                runs.append(cur)
            cur = []
    if len(cur) >= min_len:
        runs.append(cur)
    return runs


def pctl(xs, q):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    f = math.floor(k); c = math.ceil(k)
    if f == c:
        return xs[int(k)]
    return xs[f] * (c - k) + xs[c] * (k - f)


def stats(xs):
    if not xs:
        return dict(n=0)
    n = len(xs)
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / n
    return dict(n=n, mean=m, std=var ** 0.5, p50=pctl(xs, .5),
                p90=pctl(xs, .9), p95=pctl(xs, .95), p99=pctl(xs, .99),
                mn=min(xs), mx=max(xs))


def analyze_route(name, samples):
    out = []
    out.append(f"\n## {name}")
    if not samples:
        out.append("  (no samples)")
        return "\n".join(out), {}
    dur = samples[-1]["t"] - samples[0]["t"]
    out.append(f"  total controlsState samples: {len(samples)}  span: {dur:.1f}s")
    vego = [s["cs_vEgo"] for s in samples]
    out.append(f"  vEgo m/s mean {sum(vego)/len(vego):.2f} ({sum(vego)/len(vego)*2.237:.1f} mph), max {max(vego):.2f}")
    sang = [s["cs_sAngle"] for s in samples]
    out.append(f"  steeringAngleDeg std {stats(sang)['std']:.1f}, range [{min(sang):.0f},{max(sang):.0f}]")

    runs = engaged_segments(samples)
    eng_n = sum(len(r) for r in runs)
    out.append(f"  engaged (latActive&active) runs: {len(runs)}, engaged samples: {eng_n} ({100*eng_n/len(samples):.0f}%)")
    if not runs:
        out.append("  NO ENGAGED LATERAL DATA on this route.")
        return "\n".join(out), {}

    eng = [s for r in runs for s in r]

    # ---- desired vs actual rate / lag ----
    # actual slew from carState rate; desired slew from derivative of psDesired
    abs_actual_rate = [abs(s["cs_sRate"]) for s in eng]
    # desired rate via finite diff within each run
    desired_rate = []
    actual_rate_fd = []
    lag_err = [abs(s["ps_angleError"]) for s in eng]
    for r in runs:
        for k in range(1, len(r)):
            dt = r[k]["t"] - r[k-1]["t"]
            if dt <= 0 or dt > 0.1:
                continue
            dd = (r[k]["ps_psDesired"] - r[k-1]["ps_psDesired"]) / dt
            da = (r[k]["ps_psAngle"] - r[k-1]["ps_psAngle"]) / dt
            desired_rate.append(abs(dd))
            actual_rate_fd.append(abs(da))

    out.append("\n  --- SLEW RATES (engaged) ---")
    sa = stats(abs_actual_rate)
    out.append(f"  |actual steeringRateDeg| (carState):  mean {sa['mean']:.1f}  p90 {sa['p90']:.1f}  p99 {sa['p99']:.1f}  max {sa['mx']:.1f}  deg/s")
    sd = stats(desired_rate)
    sf = stats(actual_rate_fd)
    out.append(f"  |desired angle slew| (d/dt psDesired): mean {sd['mean']:.1f}  p90 {sd['p90']:.1f}  p99 {sd['p99']:.1f}  deg/s")
    out.append(f"  |actual angle slew| (d/dt psAngle):    mean {sf['mean']:.1f}  p90 {sf['p90']:.1f}  p99 {sf['p99']:.1f}  deg/s")
    out.append(f"  angleError |deg|: mean {stats(lag_err)['mean']:.2f}  p90 {stats(lag_err)['p90']:.2f}  p99 {stats(lag_err)['p99']:.2f}")

    # ---- wind vs unwind separation ----
    # wind = |desired| increasing (moving away from 0); unwind = |desired| decreasing (toward 0)
    wind_err, unwind_err = [], []
    wind_aslew, unwind_aslew = [], []
    wind_dslew, unwind_dslew = [], []
    wind_out, unwind_out = [], []
    wind_p, unwind_p = [], []
    wind_i, unwind_i = [], []
    wind_f, unwind_f = [], []
    # unwind tracking ratio: actual slew / desired slew when returning toward center
    unwind_track = []
    wind_track = []
    for r in runs:
        for k in range(1, len(r)):
            dt = r[k]["t"] - r[k-1]["t"]
            if dt <= 0 or dt > 0.1:
                continue
            des0 = r[k-1]["ps_psDesired"]; des1 = r[k]["ps_psDesired"]
            ddes = (abs(des1) - abs(des0))  # >0 winding, <0 unwinding
            if abs(des1) < 2.0:  # ignore near-center noise
                pass
            dd = abs((des1 - des0) / dt)
            da = abs((r[k]["ps_psAngle"] - r[k-1]["ps_psAngle"]) / dt)
            s = r[k]
            if ddes > 0.05:   # winding
                wind_err.append(abs(s["ps_angleError"]))
                wind_aslew.append(da); wind_dslew.append(dd)
                wind_out.append(abs(s["ps_output"])); wind_p.append(abs(s["ps_p"]))
                wind_i.append(abs(s["ps_i"])); wind_f.append(abs(s["ps_f"]))
                if dd > 1.0:
                    wind_track.append(da / dd)
            elif ddes < -0.05:  # unwinding
                unwind_err.append(abs(s["ps_angleError"]))
                unwind_aslew.append(da); unwind_dslew.append(dd)
                unwind_out.append(abs(s["ps_output"])); unwind_p.append(abs(s["ps_p"]))
                unwind_i.append(abs(s["ps_i"])); unwind_f.append(abs(s["ps_f"]))
                if dd > 1.0:
                    unwind_track.append(da / dd)

    out.append("\n  --- WIND vs UNWIND (desired-angle direction split) ---")
    out.append(f"  WIND   samples {len(wind_err)}:  angleErr mean {stats(wind_err).get('mean',0):.2f} p90 {stats(wind_err).get('p90',0):.2f} | "
               f"desiredSlew p90 {stats(wind_dslew).get('p90',0):.1f} actualSlew p90 {stats(wind_aslew).get('p90',0):.1f} deg/s")
    out.append(f"  UNWIND samples {len(unwind_err)}:  angleErr mean {stats(unwind_err).get('mean',0):.2f} p90 {stats(unwind_err).get('p90',0):.2f} | "
               f"desiredSlew p90 {stats(unwind_dslew).get('p90',0):.1f} actualSlew p90 {stats(unwind_aslew).get('p90',0):.1f} deg/s")
    out.append(f"  WIND   slew-tracking ratio (actual/desired, desiredSlew>1): mean {stats(wind_track).get('mean',float('nan')):.2f} p50 {stats(wind_track).get('p50',float('nan')):.2f}")
    out.append(f"  UNWIND slew-tracking ratio (actual/desired, desiredSlew>1): mean {stats(unwind_track).get('mean',float('nan')):.2f} p50 {stats(unwind_track).get('p50',float('nan')):.2f}")
    out.append(f"  WIND   PID:  |p| mean {stats(wind_p).get('mean',0):.4f} | |i| mean {stats(wind_i).get('mean',0):.4f} | |f| mean {stats(wind_f).get('mean',0):.4f} | |out| mean {stats(wind_out).get('mean',0):.4f} p99 {stats(wind_out).get('p99',0):.4f}")
    out.append(f"  UNWIND PID:  |p| mean {stats(unwind_p).get('mean',0):.4f} | |i| mean {stats(unwind_i).get('mean',0):.4f} | |f| mean {stats(unwind_f).get('mean',0):.4f} | |out| mean {stats(unwind_out).get('mean',0):.4f} p99 {stats(unwind_out).get('p99',0):.4f}")

    # ---- saturation ----
    sat = sum(1 for s in eng if s.get("ps_saturated"))
    out.append(f"\n  saturation: {sat}/{len(eng)} engaged samples ({100*sat/len(eng):.1f}%)")
    # output near clamp
    near_clamp = sum(1 for s in eng if abs(s["ps_output"]) > 0.95)
    out.append(f"  |output|>0.95 (near +/-1.0 clamp): {near_clamp} ({100*near_clamp/len(eng):.1f}%)")
    out_stats = stats([abs(s["ps_output"]) for s in eng])
    out.append(f"  |output| overall: mean {out_stats['mean']:.4f} p90 {out_stats['p90']:.4f} p99 {out_stats['p99']:.4f} max {out_stats['mx']:.4f}")

    # ---- unwind STRENGTH: return-to-center events ----
    # find peaks where |desired| crosses a high threshold then returns; measure time-to-center & residual.
    out.append("\n  --- UNWIND STRENGTH: return-to-center events ---")
    rtc = return_to_center(runs)
    if rtc["events"]:
        out.append(f"  detected {rtc['n']} return events (peak |desired|>={rtc['thresh']:.0f} deg)")
        out.append(f"  time peak->within 5deg of center: mean {rtc['t_mean']:.2f}s p90 {rtc['t_p90']:.2f}s")
        out.append(f"  mean |actual-desired| during return (trailing lag): {rtc['lag_mean']:.2f} deg")
        out.append(f"  events where actual TRAILED desired back to center (actual slower): {rtc['trail_frac']*100:.0f}%")
        out.append(f"  residual |actual angle| 0.5s after desired<5deg: mean {rtc['resid_mean']:.2f} deg p90 {rtc['resid_p90']:.2f}")
        out.append(f"  unwind output |out| during return: mean {rtc['out_mean']:.4f}  (sign-correct-toward-center frac {rtc['out_correct']*100:.0f}%)")
    else:
        out.append("  no clean return-to-center events found at threshold.")

    metrics = dict(
        vego_mean=sum(vego)/len(vego), eng_n=eng_n,
        wind_dslew_p90=stats(wind_dslew).get('p90',0), wind_aslew_p90=stats(wind_aslew).get('p90',0),
        unwind_dslew_p90=stats(unwind_dslew).get('p90',0), unwind_aslew_p90=stats(unwind_aslew).get('p90',0),
        wind_track=stats(wind_track).get('mean',float('nan')), unwind_track=stats(unwind_track).get('mean',float('nan')),
        wind_err=stats(wind_err).get('mean',0), unwind_err=stats(unwind_err).get('mean',0),
        wind_out=stats(wind_out).get('mean',0), unwind_out=stats(unwind_out).get('mean',0),
        sat_frac=sat/len(eng), nearclamp=near_clamp/len(eng),
        rtc=rtc,
    )
    return "\n".join(out), metrics


def return_to_center(runs, thresh=15.0):
    events = []
    times, lags, resids, outs = [], [], [], []
    trail_cnt = 0
    out_correct_cnt = 0
    out_total = 0
    for r in runs:
        des = [s["ps_psDesired"] for s in r]
        i = 1
        n = len(r)
        while i < n - 1:
            # find a local peak in |desired| above thresh
            if abs(des[i]) >= thresh and abs(des[i]) >= abs(des[i-1]) and abs(des[i]) > abs(des[i+1]):
                peak = i
                sign = 1 if des[peak] > 0 else -1
                # walk forward until |desired| < 5
                j = peak
                while j < n - 1 and abs(des[j]) > 5.0:
                    j += 1
                if j <= peak or (r[j]["t"] - r[peak]["t"]) <= 0:
                    i = peak + 1
                    continue
                t_return = r[j]["t"] - r[peak]["t"]
                if t_return > 6.0:  # not a clean return
                    i = j
                    continue
                # lag during return: actual angle vs desired
                seg = r[peak:j+1]
                lag_vals = [abs(s["ps_psAngle"] - s["ps_psDesired"]) for s in seg]
                lag_mean = sum(lag_vals) / len(lag_vals)
                # did actual trail (|actual|>|desired|, i.e. wheel still out while desired came back)?
                trailing = sum(1 for s in seg if abs(s["ps_psAngle"]) > abs(s["ps_psDesired"]) + 1.0)
                if trailing > len(seg) * 0.5:
                    trail_cnt += 1
                # output sign during return should oppose current angle (push toward center)
                for s in seg:
                    if abs(s["ps_output"]) > 0.01:
                        out_total += 1
                        # toward center => output sign opposite to actual angle sign
                        if (s["ps_output"] * s["ps_psAngle"]) < 0:
                            out_correct_cnt += 1
                out_mean = sum(abs(s["ps_output"]) for s in seg) / len(seg)
                # residual 0.5s after reaching <5 desired
                k = j
                while k < n - 1 and (r[k]["t"] - r[j]["t"]) < 0.5:
                    k += 1
                resid = abs(r[k]["ps_psAngle"])
                events.append(1)
                times.append(t_return); lags.append(lag_mean)
                resids.append(resid); outs.append(out_mean)
                i = j
            else:
                i += 1
    if not events:
        return dict(events=[], n=0, thresh=thresh)
    def m(x): return sum(x)/len(x) if x else float('nan')
    return dict(
        events=events, n=len(events), thresh=thresh,
        t_mean=m(times), t_p90=pctl(times, .9),
        lag_mean=m(lags), trail_frac=trail_cnt/len(events),
        resid_mean=m(resids), resid_p90=pctl(resids, .9),
        out_mean=m(outs), out_correct=(out_correct_cnt/out_total if out_total else float('nan')),
    )


def main():
    report = ["# Wind/Unwind extraction (raw stats) — 2026-05-28 lat-B drive"]
    allm = {}
    for name, segs in ROUTES.items():
        sys.stderr.write(f"collecting {name}...\n")
        samples = collect(segs)
        txt, m = analyze_route(name, samples)
        report.append(txt)
        allm[name] = m
    print("\n".join(report))


if __name__ == "__main__":
    main()
