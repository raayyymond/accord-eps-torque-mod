# -*- coding: utf-8 -*-
r"""m4_setpoint.py -- M4 mechanisms (2) the SETPOINT STAIRCASE and (3) the 100 Hz ANGLE HOLD, plus the record's
scale-free ratchet measure (rate concentration), on route 79 (V298).

    python m4_setpoint.py         (~6 s)

(2) STAIRCASE.  (i) the 0xE4 raw per-frame increment histogram on the native bus-129 axis (te4), engaged, O1 override
    frames excluded, stratified by the 0.2 s mean setpoint rate; the measured share of zero-increment frames vs the
    share a smooth ramp quantised at 0.1 deg would give (1 - q, q = mean counts per frame, q < 1).  (ii) the 20 Hz
    MODEL CADENCE: every controls frame is phased by the frames elapsed since the latest modelV2 message (fork cache
    t_md / t_cc); mean |d(desired angle)| per phase.  (iii) does the WHEEL follow the 20 Hz steps: a SYNCHRONOUS
    average (phase-locked to modelV2 arrival, 10 ms bins) of the setpoint rate, the 0x18F wheel rate and the 0x1AB tap,
    sign-normalised by the turn direction, in turning windows; the 20 Hz Fourier component of each phase profile.
(3) HOLD.  (i) the 0x14A angle-count flicker rate (a +-1 count step undone within <= 5 frames while the setpoint is
    unchanged), per band; (ii) the 0x18F rate integrated vs the 0x14A angle over 1 s windows (gain, residual rms).
RATCHET MEASURE.  v293_symptom_instruments.rate_concentration (4 s windows binned by their own rms rate; the q75-90 bin
    is the record's headline) on every route; on r79 the same measure on the setpoint rate (the "inherited vs
    generated" control).
"""
from __future__ import annotations

import contextlib
import io
import json

import numpy as np
from scipy import signal

import m4_common as C


def staircase(G, L):
    t, eng = G["t"], G["eng"]
    stg = C.zoh(L["t"], L["stage"], t, fill=0)
    te4, raw, req = G["te4"], np.round(G["cmd_e4"]), G["req_e4"]
    # map the native 0xE4 frames onto the engaged / stage masks of the grid
    gi = np.clip(np.searchsorted(t, te4) - 1, 0, len(t) - 1)
    ok = eng[gi] & (req > 0.5) & (stg[gi] != 3)
    d = np.diff(raw)
    okd = ok[1:] & ok[:-1] & (np.diff(te4) < 0.015)
    # 0.2 s centred mean setpoint rate (deg/s) on the native axis
    sp = -raw / 10.0
    r20 = np.convolve(np.gradient(sp) * 100.0, np.ones(20) / 20, "same")
    rr = np.abs(r20[1:])
    out = {}
    strata = ((0, 1), (1, 5), (5, 20), (20, 60), (60, 1e9))
    edges = np.array([-0.5, 0.5, 1.5, 2.5, 3.5, 5.5, 11.5, 12.5, 1e9])
    for lo, hi in strata:
        m = okd & (rr >= lo) & (rr < hi)
        ad = np.abs(d[m])
        h, _ = np.histogram(ad, edges)
        q = ad.mean() if len(ad) else np.nan
        out["%g-%g" % (lo, hi)] = dict(n=int(m.sum()), mean_counts=float(q),
                                      zero_frac=float(np.mean(ad == 0)) if len(ad) else np.nan,
                                      zero_frac_smooth=float(max(0.0, 1.0 - q)) if np.isfinite(q) else np.nan,
                                      hist=dict(zip(["0", "1", "2", "3", "4-5", "6-11", "12", ">12"],
                                                    (h / max(1, h.sum())).round(4).tolist())),
                                      at_cap_frac=float(np.mean(ad == 12)) if len(ad) else np.nan)
    tot = okd.sum()
    return dict(strata=out, n=int(tot), max_abs_step=float(np.abs(d[okd]).max()))


def model_cadence(F):
    tc, des, lat = F["t_cc"], F["cc_ang"].astype(float), F["cc_latActive"].astype(bool)
    tmd = F["t_md"]
    j = np.clip(np.searchsorted(tmd, tc, side="right") - 1, 0, None)
    k = np.searchsorted(tc, tmd[j], side="left")
    ph = np.arange(len(tc)) - k
    d = np.abs(np.diff(des))
    m = lat[1:] & lat[:-1]
    rows = {}
    tot = d[m].sum()
    for p in range(6):
        sel = m & (ph[1:] == p)
        rows[p] = dict(n=int(sel.sum()), mean_abs_ddes=float(d[sel].mean()) if sel.any() else 0.0,
                       share=float(d[sel].sum() / tot) if tot else 0.0)
    # in turns only (|0.5 s mean desired rate| > 5 deg/s)
    r50 = np.abs(np.convolve(np.gradient(des) * 100.0, np.ones(50) / 50, "same"))[1:]
    tt = m & (r50 > 5)
    tot2 = d[tt].sum()
    rows_turn = {p: float(d[tt & (ph[1:] == p)].sum() / tot2) for p in range(6)} if tot2 else {}
    return dict(all=rows, turn_share=rows_turn, md_dt_p50=float(np.median(np.diff(tmd))))


def synchronous(G, F, L):
    """phase-locked (to modelV2 arrival) averages of setpoint rate, wheel rate, tap, in turning windows."""
    t, eng = G["t"], G["eng"]
    stg = C.zoh(L["t"], L["stage"], t, fill=0)
    tmd = F["t_md"]
    j = np.clip(np.searchsorted(tmd, t, side="right") - 1, 0, None)
    phi = (t - tmd[j]) % 0.05                      # s since the latest model message, folded at 50 ms
    pb = np.minimum((phi / 0.01).astype(int), 4)   # 5 bins of 10 ms
    sp = G["theta_sp"]
    sprate = np.gradient(sp) * 100.0
    s50 = np.convolve(sprate, np.ones(50) / 50, "same")
    sgn = np.sign(s50)
    w = G["w18"]
    tap = G["tap"]
    res = {}
    for nm, lo, hi in (("all", 0.0, 99.0),) + C.SYM_BANDS:
        for rlo, rhi in ((5.0, 20.0), (20.0, 1e9)):
            m = eng & (stg != 3) & (np.abs(s50) >= rlo) & (np.abs(s50) < rhi) & (G["vego"] >= lo) & (G["vego"] < hi)
            if m.sum() < 500:
                continue
            prof = {}
            for key, x in (("sp_rate", sprate), ("w18", w), ("tap", tap)):
                y = x * sgn
                pr = np.array([np.mean(y[m & (pb == p)]) for p in range(5)])
                c20 = np.sum(pr * np.exp(-2j * np.pi * np.arange(5) / 5)) * 2 / 5   # 20 Hz component amplitude
                prof[key] = dict(profile=pr.round(3).tolist(), mean=float(pr.mean()), a20=float(abs(c20)),
                                 ph20_deg=float(np.degrees(np.angle(c20))),
                                 depth=float(abs(c20) / max(abs(pr.mean()), 1e-9)))
            prof["n"] = int(m.sum())
            prof["wheel_over_sp_20Hz"] = prof["w18"]["a20"] / max(prof["sp_rate"]["a20"], 1e-9)
            res["%s|%g-%g" % (nm, rlo, rhi)] = prof
    return res


def wheel_20hz_line(G, mask, nper=128):
    """w18 PSD in the mask's >= 1.28 s runs; 20 Hz bin vs the +-3 Hz shoulder (dB), and the 18-22 Hz rms (deg/s)."""
    segs = C.runs(mask, nper)
    win = np.hanning(nper)
    P = []
    for a, b in segs:
        x = G["w18"][a:b]
        for s in range(0, len(x) - nper + 1, nper // 2):
            q = x[s:s + nper] - x[s:s + nper].mean()
            P.append(np.abs(np.fft.rfft(q * win)) ** 2)
    if len(P) < 8:
        return None
    Pm = np.mean(P, 0) / ((win ** 2).sum() * C.FS) * 2
    f = np.fft.rfftfreq(nper, 1 / C.FS)
    i20 = int(np.argmin(abs(f - 20)))
    sh = (np.abs(f - 20) >= 2.5) & (np.abs(f - 20) <= 5)
    ex = 10 * np.log10(Pm[i20] / np.median(Pm[sh]))
    bb = (f >= 18) & (f <= 22)
    return dict(n=len(P), ex20_db=float(ex), rms1822=float(np.sqrt(Pm[bb].sum() * (f[1] - f[0]))))


def flicker(G, mask):
    """0x14A angle-count flicker on the NATIVE 0x14A axis: a +-1 count step undone within <= 5 frames with the
    setpoint unchanged over the same frames."""
    t14, a14 = G["t14"], np.round(G["ang14"] * 10).astype(int)
    gi = np.clip(np.searchsorted(G["t"], t14) - 1, 0, len(G["t"]) - 1)
    ok = mask[gi]
    sp = np.round(G["theta_sp"][gi] * 10).astype(int)
    d = np.diff(a14)
    out = {}
    v = G["vego"][gi]
    for nm, lo, hi in C.SYM_BANDS:
        mb = ok & (v >= lo) & (v < hi)
        n_fl = 0
        idx = np.flatnonzero((np.abs(d) == 1) & mb[1:])
        for lag in range(1, 6):
            jj = idx + lag
            jj = jj[jj < len(d)]
            ii = jj - lag
            undone = (d[jj] == -d[ii])
            # no other angle change between, setpoint unchanged over [ii, jj+1]
            if lag > 1:
                cs = np.r_[0, np.cumsum(d != 0)]
                quiet = (cs[jj] - cs[ii + 1]) == 0
            else:
                quiet = np.ones(len(jj), bool)
            spc = sp[jj + 1] == sp[ii]
            n_fl += int(np.sum(undone & quiet & spc))
        secs = mb.sum() / C.FS
        out[nm] = dict(secs=float(secs), per_min=float(60.0 * n_fl / secs) if secs > 5 else np.nan)
    return out


def rate_vs_angle(G, mask):
    """theta/rate consistency: over 1 s non-overlapping engaged windows, delta(0x14A angle) vs integral(0x18F rate)."""
    segs = C.runs(mask, 100)
    X, Y = [], []
    for a, b in segs:
        for s in range(a, b - 100 + 1, 100):
            X.append(np.sum(G["w18"][s:s + 100]) * C.DT)
            Y.append(G["theta"][s + 99] - G["theta"][s])
    X, Y = np.array(X), np.array(Y)
    big = np.abs(Y) > 2
    g = float(np.sum(X[big] * Y[big]) / np.sum(X[big] ** 2)) if big.any() else np.nan
    return dict(n=len(X), gain_angle_per_intrate=g, resid_rms_small=float(np.std(Y[~big] - g * X[~big])))


def concentration(G, use_sp=False):
    with contextlib.redirect_stdout(io.StringIO()):
        import v293_symptom_instruments as SI
    rate = G["w18"]
    cmd = G["theta_sp"] * 10.0 if use_sp else G["raw"]
    r = SI.rate_concentration(rate, cmd, G["vego"], G["eng"])
    return r


def main():
    tm = C.timer()
    G = C.build_grid(C.TAG79)
    F = C.fork_cache()
    L = C.limiter_reconstruct(F)
    R = {}
    R["staircase"] = staircase(G, L)
    R["cadence"] = model_cadence(F)
    R["sync"] = synchronous(G, F, L)
    stg = C.zoh(L["t"], L["stage"], G["t"], fill=0)
    s50 = np.abs(np.convolve(np.gradient(G["theta_sp"]) * 100.0, np.ones(50) / 50, "same"))
    turn = G["eng"] & (stg != 3) & (s50 > 5)
    straight = G["eng"] & (stg != 3) & (s50 < 1)
    R["w20"] = dict(r79_turn=wheel_20hz_line(G, turn), r79_straight=wheel_20hz_line(G, straight),
                    r79_disengaged=wheel_20hz_line(G, ~G["eng"] & (G["vego"] > 3)))
    R["flicker"] = flicker(G, G["eng"] & (stg != 3))
    R["rate_vs_angle"] = rate_vs_angle(G, G["eng"])
    R["conc"] = {C.TAG79: concentration(G)}
    R["conc_sp_r79"] = concentration(G, use_sp=True)
    for tag in C.REFS:
        Gr = C.build_grid(tag)
        R["conc"][tag] = concentration(Gr)
        sr = np.abs(np.convolve(np.gradient(Gr["theta"]) * 100.0, np.ones(50) / 50, "same"))
        R["w20"][tag + "_turn"] = wheel_20hz_line(Gr, Gr["eng"] & (sr > 5))
        R["flicker_" + tag] = flicker(Gr, Gr["eng"])
    R["wall_s"] = tm()
    with open(C.OUT / "m4_setpoint.json", "w") as fh:
        json.dump(R, fh, indent=1, default=float)
    # ---- print
    print("M4 SETPOINT / HOLD  (wall %.1f s)" % R["wall_s"])
    print("(2i) 0xE4 raw increments, engaged, O1 excluded; n %d, max |step| %d counts" % (R["staircase"]["n"],
                                                                                          R["staircase"]["max_abs_step"]))
    for k, v in R["staircase"]["strata"].items():
        print("   |sp rate| %-8s deg/s n %6d  mean %.2f cnt/frame  zero %.3f (smooth-ramp %.3f)  cap12 %.4f  hist %s" % (
            k, v["n"], v["mean_counts"], v["zero_frac"], v["zero_frac_smooth"], v["at_cap_frac"], v["hist"]))
    print("(2ii) model cadence: frames since modelV2 -> mean |d des| deg/frame, share of desired-angle travel")
    for p, v in R["cadence"]["all"].items():
        print("   phase %d  n %6d  mean %.3f  share %.3f   (turning share %.3f)" % (
            p, v["n"], v["mean_abs_ddes"], v["share"], R["cadence"]["turn_share"].get(p, np.nan)))
    print("(2iii) synchronous average (phase-locked to modelV2, 10 ms bins), sign-normalised by turn direction")
    for k, v in R["sync"].items():
        print("   %-16s n %6d  sp_rate %s a20 %.2f | w18 %s a20 %.2f depth %.2f | tap %s a20 %.2f | wheel/sp @20Hz %.3f" % (
            k, v["n"], v["sp_rate"]["profile"], v["sp_rate"]["a20"], v["w18"]["profile"], v["w18"]["a20"],
            v["w18"]["depth"], v["tap"]["profile"], v["tap"]["a20"], v["wheel_over_sp_20Hz"]))
    print("    w18 20 Hz line:", {k: (None if v is None else (v["n"], round(v["ex20_db"], 2), round(v["rms1822"], 3)))
                                  for k, v in R["w20"].items()})
    print("(3i) angle-count flicker /min:", {k: round(v["per_min"], 2) for k, v in R["flicker"].items()},
          " refs:", {t: {k: round(v["per_min"], 2) for k, v in R["flicker_" + t].items()} for t in C.REFS})
    print("(3ii) angle vs integrated rate:", R["rate_vs_angle"])
    print("RATCHET MEASURE rate concentration (median, per rms-rate bin):")
    for tag, r in R["conc"].items():
        print("   %-10s %s" % (tag[:10], {k: (v["n"], None if v["med"] is None else round(v["med"], 3)) for k, v in r["rate"].items()}))
    print("   r79 setpoint (cmd channel) %s" % {k: (v["n"], None if v["med"] is None else round(v["med"], 3))
                                                 for k, v in R["conc_sp_r79"]["cmd"].items()})
    print("wall %.1f s" % tm())


if __name__ == "__main__":
    main()
