#!/usr/bin/env python3
r"""Does the V96 cave SEE the ratchet?

Reconstructs the signed firmware-internal lane from the V96 telemetry --
    gp-0x6b70  =  sign(byte4 b7) * (CAN 427 MOTOR_TORQUE) * 64/5        [50 Hz, LSB 12.8 counts]
-- and asks whether it carries the same 6-9 Hz oscillation the driver's torque sensor does during
the operator's elicitation bursts.

🛑 PAIRING.  The 427 wire is on 0x1AB at 50 Hz; its sign bit is on 0x14A byte 4 at 100 Hz.  The
kit's recorded off-by-one (`t` == `raw14_t[1:]`) means the ONLY safe pairings are `(t, probe)` or
`(raw14_t, raw14_b4)`.  This file uses the latter, then nearest-neighbour joins the 0x1AB frames
onto it with a hard 10 ms tolerance and REPORTS the join residual.

🛑 A 50 Hz series resolves 7.8 Hz with 6.4 samples/cycle -- fine -- but the 427 magnitude is a
`sar 6` quantisation with LSB 12.8 counts, so anything below ~13 counts of gp-0x6b70 is invisible.
The 6-9 Hz floor is stated with every number.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt, hilbert, coherence, welch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
from v96_elicitation_finder import mmss  # noqa: E402

CACHE = {r: ROOT / "analysis-2020accord" / f"_cache_r{r}" / f"r{r}.npz" for r in ("7e", "7f")}
LSB = 64.0 / 5.0
BAND = (6.0, 9.0)


def signed_lane(z, tol=0.010):
    """(t_50, gp-0x6b70 signed counts, join report) on the 0x1AB 50 Hz grid."""
    t14 = np.asarray(z["raw14_t"], float)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    tab = np.asarray(z["ab_t1ab"], float)
    mt = np.asarray(z["ab_mt"], int).astype(float)
    j = np.clip(np.searchsorted(t14, tab), 1, len(t14) - 1)
    j = np.where(np.abs(t14[j - 1] - tab) <= np.abs(t14[j] - tab), j - 1, j)
    resid = np.abs(t14[j] - tab)
    ok = resid <= tol
    sgn = np.where((b4[j] >> 7) & 1, -1.0, 1.0)
    return tab[ok], (sgn * mt * LSB)[ok], dict(
        n=int(ok.sum()), dropped=int((~ok).sum()),
        resid_p50=float(np.median(resid)), resid_p99=float(np.percentile(resid, 99)))


def bp(x, fs, lo=BAND[0], hi=BAND[1]):
    sos = butter(4, [lo / (fs / 2), hi / (fs / 2)], btype="band", output="sos")
    return sosfiltfilt(sos, x - np.mean(x))


def band_rms(x, fs, lo=BAND[0], hi=BAND[1]):
    if len(x) < 32:
        return float("nan")
    f, P = welch(x - np.mean(x), fs=fs, nperseg=min(len(x), int(fs * 2)))
    m = (f >= lo) & (f <= hi)
    return float(np.sqrt(np.trapezoid(P[m], f[m])))


def run(r):
    z = np.load(CACHE[r], allow_pickle=True)
    t = np.asarray(z["t"], float)
    tq = np.asarray(z["tq"], float)
    lat = np.asarray(z["cc_lat"], float) > 0.5
    v = np.abs(np.asarray(z["cs_v"], float)) * 3.6
    t50, lane, rep = signed_lane(z)
    print(f"\n=== route {r} ===")
    print(f"  427<->0x14A join: n={rep['n']:,} dropped={rep['dropped']} "
          f"resid p50 {1000*rep['resid_p50']:.2f} ms p99 {1000*rep['resid_p99']:.2f} ms")
    print(f"  gp-0x6b70 signed: p1 {np.percentile(lane,1):+.0f}  p50 {np.percentile(lane,50):+.0f}  "
          f"p99 {np.percentile(lane,99):+.0f}  |max| {np.abs(lane).max():.0f} counts "
          f"(clamp 8192, LSB {LSB:.1f})")

    blocks_ = json.loads(
        (ROOT / "analysis-2020accord" / "_r7e_r7f_elicitations.json").read_text())[r]
    lat50 = np.interp(t50, t, lat.astype(float)) > 0.5
    v50 = np.interp(t50, t, v)
    inblk50 = np.zeros(len(t50), bool)
    inblk100 = np.zeros(len(t), bool)
    for b in blocks_:
        inblk50 |= (t50 >= b["t0"]) & (t50 <= b["t1"])
        inblk100 |= (t >= b["t0"]) & (t <= b["t1"])

    out = {}
    for arm, m50, m100 in (("ENGAGED", inblk50 & lat50, inblk100 & lat),
                           ("LKAS OFF", inblk50 & ~lat50, inblk100 & ~lat)):
        seg50 = _contig(m50, t50, 2.0)
        seg100 = _contig(m100, t, 2.0)
        r50 = [band_rms(lane[a:b], 50.0) for a, b in seg50]
        r100 = [band_rms(tq[a:b], 100.0) for a, b in seg100]
        r50 = [x for x in r50 if np.isfinite(x)]
        r100 = [x for x in r100 if np.isfinite(x)]
        out[arm] = dict(n_seg_50=len(r50), n_seg_100=len(r100),
                        lane_band_rms_med=float(np.median(r50)) if r50 else float("nan"),
                        tq_band_rms_med=float(np.median(r100)) if r100 else float("nan"),
                        secs=float(m50.sum() / 50.0))
        print(f"  {arm:<9} {out[arm]['secs']:6.1f} s   6-9 Hz band RMS: "
              f"gp-0x6b70 {out[arm]['lane_band_rms_med']:8.1f} ct   "
              f"driver torque {out[arm]['tq_band_rms_med']:8.1f} ct   "
              f"({len(r50)} / {len(r100)} runs)")

    # coherence, engaged elicitation only, on a common 50 Hz grid
    tq50 = np.interp(t50, t, tq)
    m = inblk50 & lat50
    segs = _contig(m, t50, 4.0)
    cohs, cohs_shuf = [], []
    rng = np.random.default_rng(7)
    for a, b in segs:
        if b - a < 128:
            continue
        f, C = coherence(lane[a:b], tq50[a:b], fs=50.0, nperseg=128)
        k = (f >= BAND[0]) & (f <= BAND[1])
        cohs.append(float(np.mean(C[k])))
        sh = lane[a:b].copy()
        rng.shuffle(sh)
        f2, C2 = coherence(sh, tq50[a:b], fs=50.0, nperseg=128)
        cohs_shuf.append(float(np.mean(C2[k])))
    print(f"  6-9 Hz coherence gp-0x6b70 <-> driver torque, engaged elicitation: "
          f"{np.median(cohs):.3f} over {len(cohs)} runs "
          f"(shuffled control {np.median(cohs_shuf):.3f}; 1/nseg bias floor "
          f"~{1/max(1,int(np.median([ (b-a)//64 for a,b in segs if b-a>=128 ]))):.3f})")
    out["coherence_6_9"] = dict(median=float(np.median(cohs)) if cohs else float("nan"),
                                shuffled=float(np.median(cohs_shuf)) if cohs_shuf else float("nan"),
                                n=len(cohs))

    # where is the lane's energy?
    f, P = welch(lane[inblk50 & lat50], fs=50.0, nperseg=256)
    top = f[np.argsort(-P)][:6]
    print(f"  gp-0x6b70 PSD peaks (engaged elicitation): " +
          " ".join(f"{x:.2f}" for x in sorted(top)) + " Hz")
    out["lane_psd_peaks_hz"] = sorted(float(x) for x in top)
    return out


def _contig(mask, t, min_sec):
    d = np.diff(mask.astype(np.int8))
    s = list(np.where(d == 1)[0] + 1)
    e = list(np.where(d == -1)[0] + 1)
    if mask[0]:
        s = [0] + s
    if mask[-1]:
        e = e + [len(mask)]
    return [(a, b) for a, b in zip(s, e) if t[min(b, len(t) - 1)] - t[a] >= min_sec]


if __name__ == "__main__":
    res = {r: run(r) for r in ("7e", "7f")}
    (ROOT / "analysis-2020accord" / "_r7e_r7f_probe_vs_ratchet.json").write_text(
        json.dumps(res, indent=1, default=float))
