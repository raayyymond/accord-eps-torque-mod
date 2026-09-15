# -*- coding: utf-8 -*-
"""v293r5_observer_read.py -- the PRE-REGISTERED read of the rev-5 drive (orchestrator's own, 2026-09-15).
usage: python v293r5_observer_read.py <tag_r5> [<tag_r4 = r75_v293r4>]
Needs the flight read's control-path cache _scratch/cs_<tag>.npz (built by v293_flight_read.py) and the ident cache.

What a PASS licenses (write it down before the drive):
  O1 the observer is ON THE WIRE: |accordObserverTorque| median > 0.002 torque on active frames, frozen < 30 % of hands-off frames.
  O2 "loose" (< 1 Hz): planner-error rms in 0.05-0.3 Hz and 0.3-1 Hz at 8-30 m/s falls >= 30 % vs r75 (hands-off, same bands);
     the integrator's share of the torque falls from ~0.30 to < 0.15.
  O3 "confident": des->act |H| at 0.5 Hz within 0.85-1.15 and at 1 Hz within 0.7-1.3 (r75: 1.07-1.22 / 0.55-2.47) -- no >1.3 overshoot peak.
  O4 "jerky": hard-turn 1.6-3 Hz wheel-rate share at v < 10 NOT above r75's 19 % by more than 10 points; rate sign reversals (this estimator, |rate| > 5 deg/s) <= 1.5 x r75's 77 /min.
     (the sim predicts up to +30 % mode energy in the lightly damped world: if O4 fails while O2/O3 pass, the next move is
      AccordDobHz 0.4 / SteerKP 0.85 by CONFIG, not a fork change.)
  O5 the observer's estimate is physically sensible: sign(dob) == sign(f) on > 60 % of active frames, |dob| p90 < 0.15 torque,
     and it is NOT hunting: 0.2-1 Hz share of the dob spectrum < 40 %.
REVERT (toggle-config_V293_torque_mode_r5_REVERT_to_r4) if: any sustained oscillation the operator feels, a one-sided pull at rest,
  |dob| pinned at the 0.3 clip for > 2 s anywhere, or O3 shows a resonance > 1.5 at 0.5-1.5 Hz.
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v293r3_read as R3
import v293_ident_lib as L
from scipy import signal
FS = 100.0
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []
def pr(s=""):
    print(s, flush=True); OUT.append(s)


def load_cs(tag):
    p = os.path.join(HERE, "_scratch", "cs_%s.npz" % tag)
    if not os.path.exists(p):
        return None
    return dict(np.load(p))


def read(tag):
    g = R3.load_plus(tag)
    C = load_cs(tag)
    t0 = min(g["raw"]["t18"][0], g["raw"]["t_cc"][0])
    ta = g["t"] + t0
    dob = frz = None
    if C is not None and "sp_dob" in C and len(C["t_sp"]):
        dob = L.zoh(ta, C["t_sp"], C["sp_dob"]); frz = L.zoh(ta, C["t_sp"], C["sp_dobfrozen"])
    v, la_des, la_act, err, out, f, p, i, press, rate, ang = (g[k] for k in ("v", "la_des", "la_act", "err", "out", "f", "p", "i", "press", "rate_dps", "ang"))
    eng = g["eng"] & (g["cs_active"] > 0.5)
    w = int(0.5 * FS); pressb = np.convolve((press > 0.5).astype(float), np.ones(2 * w + 1), mode="same") > 0
    ho = eng & ~pressb
    res = {"tag": tag}
    pr("\n" + "=" * 120); pr("OBSERVER READ  %s   (%s)" % (tag, "wire fields present" if dob is not None else "NO observer fields in the cs cache -- rev-4 drive or cache not rebuilt"))
    # O1
    if dob is not None:
        act = ho & np.isfinite(dob) & (np.abs(out) > 1e-3)
        res["dob_med"] = float(np.nanmedian(np.abs(dob[act]))); res["dob_p90"] = float(np.nanpercentile(np.abs(dob[act]), 90))
        res["frozen"] = float(np.nanmean(frz[act])); res["dob_sign"] = float(np.mean(np.sign(dob[act]) == np.sign(-out[act])))
        res["clip_s"] = float(np.sum(np.abs(dob[act]) > 0.29) / FS)
        fd, Pd = signal.welch(np.nan_to_num(dob[act] - np.nanmean(dob[act])), fs=FS, nperseg=1024)
        sel = (fd > 0.02) & (fd < 5); hunt = (fd >= 0.2) & (fd < 1.0)
        res["dob_hunt_share"] = float(np.trapezoid(Pd[hunt], fd[hunt]) / max(np.trapezoid(Pd[sel], fd[sel]), 1e-30))
        pr("O1/O5 observer: |dob| median %.4f p90 %.4f torque | frozen %.1f %% | sign(dob)=sign(u) %.2f | at clip %.1f s | 0.2-1 Hz share of its spectrum %.0f %%"
           % (res["dob_med"], res["dob_p90"], 100 * res["frozen"], res["dob_sign"], res["clip_s"], 100 * res["dob_hunt_share"]))
    # O2 loose: planner error by band, hands-off, 8-30 m/s
    for lo, hi in ((8, 15), (15, 22), (22, 31)):
        m = ho & (v >= lo) & (v < hi) & np.isfinite(la_des) & np.isfinite(la_act)
        st = L.stretches(m, int(10 * FS))
        if not st: continue
        e = np.concatenate([la_des[a:b] - la_act[a:b] for a, b in st]); e = e - e.mean()
        ee = {}
        for (a_, b_) in ((0.05, 0.3), (0.3, 1.0), (1.0, 3.0)):
            ee["%g-%g" % (a_, b_)] = float(np.sqrt(np.mean(L.bandpass(e, a_, b_) ** 2)))
        ish = float(np.median(np.abs(i[m]) / np.maximum(np.abs(p[m]) + np.abs(i[m]) + np.abs(f[m]), 1e-6)))
        res["e_%d_%d" % (lo, hi)] = ee; res["ishare_%d_%d" % (lo, hi)] = ish
        pr("O2 %2d-%2d m/s (%4.0f s): planner-error rms 0.05-0.3 Hz %.3f | 0.3-1 Hz %.3f | 1-3 Hz %.3f m/s^2 | integrator share %.2f"
           % (lo, hi, sum(b - a for a, b in st) / FS, ee["0.05-0.3"], ee["0.3-1"], ee["1-3"], ish))
        # O3 des->act |H|
        dd = np.concatenate([la_des[a:b] - la_des[a:b].mean() for a, b in st]); aa = np.concatenate([la_act[a:b] - la_act[a:b].mean() for a, b in st])
        fx, Pxy = signal.csd(dd, aa, fs=FS, nperseg=1024); _, Pxx = signal.welch(dd, fs=FS, nperseg=1024); fc, Cc = signal.coherence(dd, aa, fs=FS, nperseg=1024)
        H = np.abs(Pxy / Pxx)
        pr("O3 %2d-%2d m/s: des->act |H|/coh at 0.2 %.2f/%.2f  0.5 %.2f/%.2f  1.0 %.2f/%.2f  1.5 %.2f/%.2f  2.0 %.2f/%.2f"
           % (lo, hi, *sum(([np.interp(q, fx, H), np.interp(q, fc, Cc)] for q in (0.2, 0.5, 1.0, 1.5, 2.0)), [])))
    # O4 jerky: hard turns v < 10
    hard = ho & (v >= 2) & (v < 10) & ((np.abs(la_des) > 1.5) | (np.abs(ang) > 60))
    st = L.stretches(hard, int(3 * FS))
    if st:
        rr = np.concatenate([rate[a:b] - rate[a:b].mean() for a, b in st])
        fr, Pr = signal.welch(rr, fs=FS, nperseg=512)
        sel = (fr >= 0.3) & (fr <= 8); md = (fr >= 1.6) & (fr < 3.0)
        share = 100 * np.trapezoid(Pr[md], fr[md]) / max(np.trapezoid(Pr[sel], fr[sel]), 1e-30)
        rev = sum(int(np.sum(np.diff(np.sign(rate[a:b][np.abs(rate[a:b]) > 5])) != 0)) for a, b in st) / (sum(b - a for a, b in st) / FS / 60)
        res["hard_mode_share"] = float(share); res["hard_rev_per_min"] = float(rev)
        pr("O4 hard turns v<10 (%.0f s): 1.6-3 Hz share of the 0.3-8 Hz wheel-rate energy %.0f %% (r75: 19 %%) | rate sign reversals %.1f /min (r75: 77, this estimator)"
           % (sum(b - a for a, b in st) / FS, share, rev))
    return res


def main():
    tags = sys.argv[1:] or ["r75_v293r4"]
    R = [read(t) for t in tags]
    if len(R) >= 2 and "e_15_22" in R[0] and "e_15_22" in R[1]:
        pr("\nCHANGE %s vs %s: 15-22 m/s planner-error 0.05-0.3 Hz %.3f -> %.3f | 0.3-1 Hz %.3f -> %.3f | integrator share %.2f -> %.2f"
           % (R[0]["tag"], R[1]["tag"], R[1]["e_15_22"]["0.05-0.3"], R[0]["e_15_22"]["0.05-0.3"], R[1]["e_15_22"]["0.3-1"], R[0]["e_15_22"]["0.3-1"],
              R[1]["ishare_15_22"], R[0]["ishare_15_22"]))
    out = os.path.join(HERE, "V293-REV5-OBSERVER-READ-%s-2026-09-15.txt" % "-".join(t.split("_")[0] for t in tags))
    open(out, "w", encoding="utf-8").write("\n".join(OUT)); pr("\nwritten " + out)


if __name__ == "__main__":
    main()
