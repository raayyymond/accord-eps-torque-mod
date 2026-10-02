# -*- coding: utf-8 -*-
r"""m4_dwell.py -- M4 (a): the DWELL-THEN-JUMP census, re-derived VECTORISED, on route 79 (V298) and the references
(r6c, r39 = V282; r71b_v294 = V294), per speed band, in the same units on every route.

    python m4_dwell.py            (~10 s; grids cached by m4_common under _scratch/out/r79/m4/)

THREE DETECTORS (each re-derived here from its source; (b) and (a) are cross-checked against the kit's own code):
  (b) SYMPTOM  v293_symptom_instruments.dwells: 0.10 s moving mean of |0x18F rate| < th for >= 0.20 s inside an
               engaged run >= 2 s (band stratum >= 5 s); snap = the 0x14A angle change from one dwell's end to the
               next dwell's start (th 0.50).  Per minute at th 0.25 / 0.50 / 1.00 / 2.00 deg/s.
  (a) HARNESS  nl_sim/harness_time.dwell_jump with ref = theta_sp (r79 only -- the references' 0xE4 is a torque /
               rate command, not an angle): dwell = 0.1 s mean |rate| < 0.25 for >= 0.10 s WHILE the reference moved
               >= 0.1 deg; EVENT if the wheel's change from the dwell end to the next dwell start (<= 0.5 s) >=
               max(2 x the reference's change, 0.2 deg).  Jump = that change; SNAP RATIO = jump / |ref change|.
  (a') PROXY   (a) with ref = the 0.5 Hz zero-phase low-pass of the wheel angle itself (4th-order Butterworth,
               sosfiltfilt per run) -- the SAME definition on every route, so V298 and V282 compare like for like.
Vectorisation: the per-run moving mean is ONE np.convolve over the runs concatenated with 10-frame zero gaps (exactly
'same'-mode-per-run); dwell runs are np.diff edges; only the (few thousand) dwell RUNS are visited, never samples.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys

import numpy as np
from scipy import signal

import m4_common as C

KER = 10
BANDS = C.SYM_BANDS


def moving_mean_runs(x, segs, k=KER):
    """'same'-mode 0.1 s moving mean of x computed independently per segment (zero-padded at each run edge, as the
    record's per-run np.convolve does), returned as (concat_values, concat_index_into_x, run_id, pos_in_run)."""
    lens = segs[:, 1] - segs[:, 0]
    pad = k
    tot = int(lens.sum() + pad * (len(segs) + 1))
    buf = np.zeros(tot)
    valid = np.zeros(tot, bool)
    src = np.full(tot, -1, np.int64)
    off = pad
    for (a, b) in segs:               # loop over RUNS (tens), not samples
        n = b - a
        buf[off:off + n] = x[a:b]
        valid[off:off + n] = True
        src[off:off + n] = np.arange(a, b)
        off += n + pad
    # np.convolve 'same' for even k centres at offset k//2 - (1 - k % 2)... replicate exactly by convolving per run is
    # equivalent to one full convolution with 'same' alignment because each run is isolated by >= k zeros.
    full = np.convolve(buf, np.ones(k) / k, "full")
    # numpy 'same' returns full[(k-1)//2 : (k-1)//2 + n] for len(v)=k <= len(a)
    s0 = (k - 1) // 2
    same = full[s0:s0 + tot]
    return same, valid, src


def dwell_runs(mask_valid, minlen):
    r = C.runs(mask_valid, minlen)
    return r


def symptom_dwells(G, mask, ths=(0.25, 0.50, 1.00, 2.00)):
    """(b), re-derived.  Returns per band: per-min at each threshold, dwell p50/p90, snap p50/p90 (th 0.50)."""
    out = {}
    v = G["vego"]
    rate = np.abs(G["w18"])
    ang = G["theta"]
    for nm, lo, hi in BANDS:
        m = mask & (v >= lo) & (v < hi)
        segs = C.runs(m, 200)
        tot = int((segs[:, 1] - segs[:, 0]).sum()) if len(segs) else 0
        if tot < 500:
            out[nm] = dict(sec=tot / C.FS, scored=False)
            continue
        rs, valid, src = moving_mean_runs(rate, segs)
        row = dict(sec=tot / C.FS, scored=True)
        for th in ths:
            dw = C.runs(valid & (rs < th), 20)
            row["pm_%.2f" % th] = 60.0 * len(dw) / (tot / C.FS)
            if th == 0.50:
                dl = (dw[:, 1] - dw[:, 0]) / C.FS
                # snap: next dwell in the SAME run (src indices contiguous and the gap holds no pad frame)
                if len(dw) > 1:
                    j0 = dw[:-1, 1]; i1 = dw[1:, 0]
                    inv = np.r_[0, np.cumsum(~valid)]
                    same_run = (inv[i1] - inv[j0]) == 0
                    sn = np.abs(ang[src[i1]] - ang[src[j0 - 1]])[same_run & (i1 > j0)]
                else:
                    sn = np.zeros(0)
                row.update(n050=len(dw), dwell_p50=float(np.percentile(dl, 50)) if len(dl) else np.nan,
                           dwell_p90=float(np.percentile(dl, 90)) if len(dl) else np.nan,
                           snap_p50=float(np.percentile(sn, 50)) if len(sn) else np.nan,
                           snap_p90=float(np.percentile(sn, 90)) if len(sn) else np.nan)
        out[nm] = row
    return out


def dwell_setpoint_split(G, mask, th=0.25):
    """route 79 only: the (b) dwells at th split by whether the SETPOINT moved >= 0.1 deg (one count) during the dwell
    (a stuck wheel under a moving reference) or stayed (a held wheel under a held reference -- a position hold, not a
    ratchet), and by the 0.5 s O1/limiter context is left to m4_episodes."""
    out = {}
    v = G["vego"]
    sp = G["theta_sp"]
    for nm, lo, hi in BANDS:
        m = mask & (v >= lo) & (v < hi)
        segs = C.runs(m, 200)
        tot = int((segs[:, 1] - segs[:, 0]).sum()) if len(segs) else 0
        if tot < 500:
            continue
        rs, valid, src = moving_mean_runs(np.abs(G["w18"]), segs)
        dw = C.runs(valid & (rs < th), 20)
        a, b = src[dw[:, 0]], src[dw[:, 1] - 1]
        moved = np.abs(sp[b] - sp[a]) >= 0.1
        spr = np.abs(sp[b] - sp[a]) / np.maximum((b - a) / C.FS, 1e-9)
        out[nm] = dict(n=int(len(dw)), per_min=60.0 * len(dw) / (tot / C.FS),
                       per_min_sp_moving=60.0 * moved.sum() / (tot / C.FS),
                       per_min_sp_still=60.0 * (~moved).sum() / (tot / C.FS),
                       sp_rate_in_moving_p50=float(np.median(spr[moved])) if moved.any() else np.nan)
    return out


def harness_dwell_jump(G, mask, ref, bands=BANDS, min_run=200, label="a"):
    """(a) / (a'), re-derived.  ref = the reference series on the grid (theta_sp, or the low-passed angle).
    Returns per-band stats and the EVENT list (grid indices)."""
    v = G["vego"]
    rate = np.abs(G["w18"])
    th = G["theta"]
    out, events = {}, []
    for nm, lo, hi in bands:
        m = mask & (v >= lo) & (v < hi)
        segs = C.runs(m, min_run)
        tot = int((segs[:, 1] - segs[:, 0]).sum()) if len(segs) else 0
        n_ev, n_dw, jumps, ratios = 0, 0, [], []
        for (a, b) in segs:               # loop over RUNS
            x = rate[a:b]
            rs = np.convolve(x, np.ones(KER) / KER, "same")
            dw = C.runs(rs < 0.25, 10)
            if not len(dw):
                continue
            n = b - a
            rf = ref[a:b]
            tt = th[a:b]
            A, B = dw[:, 0], dw[:, 1]
            ok = (B + 2 < n) & (np.abs(rf[np.maximum(B - 1, 0)] - rf[A]) >= 0.1)
            nxt = np.r_[A[1:], n - 1]
            E = np.minimum(np.minimum(nxt, B + 50), n - 1)
            Bc = np.minimum(B, n - 1)
            jump = np.abs(tt[E] - tt[Bc])
            dref = np.abs(rf[E] - rf[Bc])
            ev = ok & (jump >= np.maximum(2.0 * dref, 0.2))
            n_dw += int(ok.sum())
            n_ev += int(ev.sum())
            jumps += list(jump[ev]); ratios += list(jump[ev] / np.maximum(dref[ev], 0.05))
            for q in np.flatnonzero(ev):
                events.append(dict(band=nm, i_dw0=int(a + A[q]), i_dw1=int(a + B[q]), i_end=int(a + E[q]),
                                   jump=float(jump[q]), dref=float(dref[q]),
                                   ref_dw=float(rf[max(B[q] - 1, 0)] - rf[A[q]])))
        secs = tot / C.FS
        out[nm] = dict(secs=secs, n_dw_refmoving=n_dw, n=n_ev, per_min=(60.0 * n_ev / secs if secs else np.nan),
                       jump_p50=float(np.median(jumps)) if jumps else np.nan,
                       jump_p90=float(np.percentile(jumps, 90)) if jumps else np.nan,
                       jmax=float(max(jumps)) if jumps else 0.0,
                       ratio_p50=float(np.median(ratios)) if ratios else np.nan)
    return out, events


def lpf_ref(G, mask, fc=0.5):
    """0.5 Hz zero-phase LPF of the wheel angle, per engaged run (so no filter crosses an engage edge)."""
    sos = signal.butter(4, fc, "lowpass", fs=C.FS, output="sos")
    ref = np.array(G["theta"], float)
    for a, b in C.runs(mask, 200):
        ref[a:b] = signal.sosfiltfilt(sos, G["theta"][a:b])
    return ref


def crosscheck(G, tag):
    """second method: the kit's OWN functions on the same grid (SI.dwells; NS.dwell_jump for r79)."""
    with contextlib.redirect_stdout(io.StringIO()):
        import v293_symptom_instruments as SI
    si = SI.dwells(np.abs(G["wire"]) / 8.0, G["theta"], G["vego"], G["eng"])
    res = {nm: (si[nm].get("per_min_025"), si[nm].get("per_min_050")) for nm, _, _ in BANDS}
    nsr = None
    if tag == C.TAG79:
        with contextlib.redirect_stdout(io.StringIO()):
            import nl_sim as NS
        nsr = {}
        for nm, lo, hi in C.CP_BANDS:
            m = G["eng"] & (G["vego"] >= lo) & (G["vego"] < hi)
            n = 0
            for a, b in C.runs(m, 200):
                ev, jm = NS.dwell_jump(G["w18"][a:b, None], G["theta"][a:b, None], G["theta_sp"][a:b, None])[:2]
                n += int(ev[0])
            nsr[nm] = n
    return res, nsr


def main():
    tm = C.timer()
    res = {}
    for tag in (C.TAG79,) + C.REFS:
        G = C.build_grid(tag)
        eng = G["eng"]
        R = dict(build=C.REF_BUILD[tag], eng_s=float(eng.sum() / C.FS))
        R["b"] = symptom_dwells(G, eng)
        ref_lp = lpf_ref(G, eng)
        R["a_proxy"], ev_p = harness_dwell_jump(G, eng, ref_lp, label="a'")
        if tag == C.TAG79:
            R["a"], ev_a = harness_dwell_jump(G, eng, G["theta_sp"])
            R["a_cp"], _ = harness_dwell_jump(G, eng, G["theta_sp"], bands=C.CP_BANDS)
            R["events_a"] = ev_a
            R["events_proxy"] = ev_p
            R["b_split"] = dwell_setpoint_split(G, eng)
        si, nsr = crosscheck(G, tag)
        R["xcheck_SI"] = si
        R["xcheck_NS"] = nsr
        res[tag] = R
    res["wall_s"] = tm()
    with open(C.OUT / "m4_dwell.json", "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    # ---- print
    print("M4 DWELL CENSUS  (wall %.1f s)" % res["wall_s"])
    hdr = "%-10s %-5s %6s | %6s %6s %6s %6s | %5s %5s | %5s %5s %5s %5s %5s" % (
        "route", "band", "sec", "b.25", "b.50", "b1.0", "b2.0", "sn50", "sn90", "a'/m", "aJ50", "aJ90", "aR50", "a/m")
    print(hdr)
    for tag in (C.TAG79,) + C.REFS:
        R = res[tag]
        for nm, _, _ in BANDS:
            b = R["b"][nm]; p = R["a_proxy"][nm]; a = R.get("a", {}).get(nm, {})
            if not b.get("scored"):
                print("%-10s %-5s %6.1f   (not scored)" % (tag[:10], nm, b["sec"])); continue
            print("%-10s %-5s %6.1f | %6.2f %6.2f %6.2f %6.2f | %5.2f %5.2f | %5.2f %5.2f %5.2f %5.2f %5s" % (
                tag[:10], nm, b["sec"], b["pm_0.25"], b["pm_0.50"], b["pm_1.00"], b["pm_2.00"], b["snap_p50"],
                b["snap_p90"], p["per_min"], p["jump_p50"], p["jump_p90"], p["ratio_p50"],
                ("%.2f" % a["per_min"]) if a else "-"))
        print("   xcheck SI.dwells (per_min 0.25, 0.50):", {k: tuple(round(x, 2) for x in v) for k, v in R["xcheck_SI"].items()})
        if R["xcheck_NS"] is not None:
            print("   xcheck NS.dwell_jump counts (CP bands):", R["xcheck_NS"], " mine:",
                  {k: v["n"] for k, v in R["a_cp"].items()})
    print("r79 (b) dwells @0.25 split by setpoint motion during the dwell (per min): ",
          {k: (round(x["per_min"], 2), round(x["per_min_sp_moving"], 2), round(x["per_min_sp_still"], 2), round(x["sp_rate_in_moving_p50"], 2))
           for k, x in res[C.TAG79]["b_split"].items()})
    print("wall %.1f s" % tm())


if __name__ == "__main__":
    main()
