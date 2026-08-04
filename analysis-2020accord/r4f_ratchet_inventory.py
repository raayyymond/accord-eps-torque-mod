#!/usr/bin/env python3
"""r4f_ratchet_inventory.py -- the RATCHET on route `4f` (V69), characterised from the analog bus.

WHY THIS EXISTS ALONGSIDE `r4f_v69_readout.py`
----------------------------------------------
That file reads V69's PROBE and prices bit6's positive control. Its ratchet section scores only
the DECODER'S CELL -- engaged + creep (v <= 4 m/s) + hands-off -- because that is the cell
`decode_v69_ratchet.py` defines. On this route that cell is 71.7 s of 481.7 s, and a first pass
over the WHOLE route finds the four loudest 6-9 Hz windows sitting at 1.2, 2.2, 2.6 and **12.7
m/s** -- i.e. the cell excludes the loudest instance outright. So the inventory here is
ROUTE-WIDE and the cell is a stratum, not a filter.

🛑 WHAT THE PROBE RETURNED, STATED UP FRONT so nothing below is read as probe evidence:
byte4 == 0x87 on 47,990/47,990 frames. bit7 (liveness) SET, bits 6/5/4 CLEAR, bit3 CLEAR. All
three rungs are CONSTANT, so none of them has a time series, a duty, a spectrum or a phase.
Deliverable "the probe correlation" is therefore VACUOUS BY MEASUREMENT, and section 6 states
what the three zeros do and do not bound.

METHOD, and why each choice (all from docs/STATE.md METHODOLOGY + the memories)
------------------------------------------------------------------------------
  * fs is the MEAN rate over the segment, (n-1)/(t[-1]-t[0]), on an index lattice. `1/median(dt)`
    is wrong here: CAN frames are timestamped per log packet.
  * DISJOINT 2.56 s windows (NFFT = 256, 0.39 Hz bins). No overlap, so window counts are sample
    counts.
  * The locator is the PROMINENCE argmax (peak / local +/-6 Hz median floor excluding +/-1.5 Hz),
    never the raw-power argmax -- a power argmax on `tq` lands on the driver's own 1-3 Hz input.
  * Every prominence is reported beside a PHYSICAL amplitude (6-9 Hz analytic envelope p99, in
    torque counts; peak-to-peak = 2x that).
  * THE NULL IS COMPUTED FIRST, two ways, and the larger is used.
  * EPISODES, never windows, are the unit of inference. Bootstrap resamples episodes.
  * ENGAGEMENT is LATERAL (`carControl.latActive`). HANDS-OFF is |lowpass(tq, 3 Hz)| < 300.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from _r31_common import band_envelope, peak_prom, periodogram, q_of, sustained  # noqa: E402

NFFT = 256
RATCH = (6.0, 9.0)          # the ratchet presence band
FREE = (5.0, 12.0)          # free locator range
CTRL_A = (10.5, 13.5)       # control band 1 -- same 3 Hz width, clear of 2f0 = 14.8-15.6
CTRL_B = (24.0, 27.0)       # control band 2 -- between grind #1 (18-22) and grind #2 (40-49)
GRIND1 = (18.0, 22.0)
HANDS_OFF = 300.0           # sustained |tq| counts
CREEP = 4.0                 # m/s
CIRC = (2.073, 2.088)       # measured tyre circumference range, m  (memories: r4f/V56/V57)

SEGS = list(range(8))


def load(seg, cache="_cache_r4f", pfx="r4fs"):
    return {k: v for k, v in np.load(ROOT / cache / f"{pfx}{seg}.npz").items()}


def fs_mean(d):
    t = d["t"]
    return (len(t) - 1) / (t[-1] - t[0])


def skew(x):
    x = np.asarray(x, float)
    x = x - x.mean()
    s = x.std()
    return float(np.mean(x ** 3) / s ** 3) if s > 0 else np.nan


def scan(d, fs, seg, tag):
    """Disjoint-window records over a whole segment, with covariates."""
    t, tq = d["t"], d["tq"]
    n = len(t)
    f = np.fft.rfftfreq(NFFT, 1 / fs)
    env = band_envelope(tq, fs, *RATCH)
    eff = np.abs(sustained(tq, fs))
    lat = d["cc_lat"] > 0.5
    v = np.abs(d["cs_v"])
    rpm = None
    p = ROOT / "_cache_r4f" / f"{pfx_of(tag)}{seg}_rpm.npz"
    if p.exists():
        rpm = np.load(p)["rpm"]
    out = []
    for i in range(0, n - NFFT + 1, NFFT):
        w = slice(i, i + NFFT)
        P = periodogram(tq[w], fs, NFFT)
        if P is None:
            continue
        fr, pr = peak_prom(f, P, *FREE)
        fb, pb = peak_prom(f, P, *RATCH)                 # strict-band presence
        _, pca = peak_prom(f, P, *CTRL_A)
        _, pcb = peak_prom(f, P, *CTRL_B)
        fg, pg = peak_prom(f, P, *GRIND1)
        r = dict(tag=tag, seg=seg, i0=i, t0=float(t[i]), fs=fs,
                 fr=fr, pr=pr, fb=fb, pb=pb, pca=pca, pcb=pcb, fg=fg, pg=pg,
                 env99=float(np.percentile(env[w], 99)),
                 Q=q_of(f, P, fb, *RATCH) if np.isfinite(fb) else np.nan,
                 v=float(v[w].mean()), vmin=float(v[w].min()), vmax=float(v[w].max()),
                 ang=float(np.mean(d["ang"][w])), angabs=float(np.mean(np.abs(d["ang"][w]))),
                 rate90=float(np.percentile(np.abs(d["rate_c"][w]), 90)),
                 eff=float(np.median(eff[w])), effmax=float(eff[w].max()),
                 lat=float(lat[w].mean()), sstat=sorted(set(d["sstat"][w].astype(int))),
                 rpm=float(np.median(rpm[w])) if rpm is not None else np.nan,
                 e4=float(np.max(np.abs(d["e4tq"][w]))) if "e4tq" in d else np.nan)
        out.append(r)
    return out


_PFX = {"V69 r4f": "r4fs"}


def pfx_of(tag):
    return _PFX.get(tag, "r4fs")


def hdr(s):
    print("\n" + "=" * 102)
    print(s)
    print("=" * 102)


def col(rs, k):
    return np.array([r[k] for r in rs], float)


# ---------------------------------------------------------------- 1. probe, stated first --------
def probe_state():
    hdr("1.  THE PROBE -- stated first, because everything after it is the ANALOG bus, not V69")
    tot = {}
    live = cls = 0
    n = 0
    for s in SEGS:
        d = load(s)
        b4 = d["raw14_b4"][:len(d["t"])].astype(int)
        for x in b4:
            tot[int(x)] = tot.get(int(x), 0) + 1
        live += int(np.count_nonzero(b4 & 0x80))
        cls += int(np.count_nonzero(b4 & 0x08))
        n += len(b4)
    print(f"   byte4 histogram over {n} frames: "
          + "  ".join(f"{hex(k)} x{v}" for k, v in sorted(tot.items())))
    print(f"   bit7 LIVENESS set  {live}/{n}   bit3 (V68 marker, must be 0) set {cls}/{n}")
    for bit, name in ((0x40, "bit6 gp-0x6ada  r24 lane out, post +/-0x2000 SAT clip"),
                      (0x20, "bit5 gp-0x6b62  return-to-centre, +/-0x2000 ZERO gate"),
                      (0x10, "bit4 gp-0x6ad4  unfiltered residual, +/-0x2800 ZERO gate")):
        k = sum(v for b, v in tot.items() if b & bit)
        # one-sided 95% upper bound on a zero-count binomial: 1 - 0.05**(1/n)
        ub = 1 - 0.05 ** (1.0 / n)
        print(f"   {name:58s} set {k}/{n}   duty 0  (95% UB {ub:.2e})")
    print("   🛑 ALL THREE RUNGS ARE CONSTANT ⇒ no time series, no duty, no spectrum, no phase.")
    print("      Deliverable 2 (probe-vs-bar coherence at the episode frequency) IS UNANSWERABLE")
    print("      ON THIS ROUTE. Section 6 says what the three zeros bound.")


# ---------------------------------------------------------------- 2. route-wide scan ------------
def route_scan():
    recs = []
    for s in SEGS:
        d = load(s)
        recs += scan(d, fs_mean(d), s, "V69 r4f")
    return recs


def nulls(recs):
    hdr("2.  THE NULL, COMPUTED BEFORE ANY DETECTION IS QUOTED")
    pca, pcb = col(recs, "pca"), col(recs, "pcb")
    a = pca[np.isfinite(pca)]
    b = pcb[np.isfinite(pcb)]
    print(f"   NULL-A  control band {CTRL_A[0]}-{CTRL_A[1]} Hz, same 3 Hz width, clear of 2*f0")
    print(f"           n={len(a)}  median {np.median(a):7.2f}  p95 {np.percentile(a, 95):8.2f}  "
          f"p99 {np.percentile(a, 99):9.2f}  max {a.max():9.2f}")
    print(f"   NULL-B  control band {CTRL_B[0]}-{CTRL_B[1]} Hz (between grind #1 and grind #2)")
    print(f"           n={len(b)}  median {np.median(b):7.2f}  p95 {np.percentile(b, 95):8.2f}  "
          f"p99 {np.percentile(b, 99):9.2f}  max {b.max():9.2f}")
    fa, fb_ = float(np.percentile(a, 95)), float(np.percentile(b, 95))
    floor = float(max(fa, fb_))
    print(f"\n   ⇒ DETECTION FLOOR = max of the two p95 = {floor:.2f}  (a 6-9 Hz prominence below")
    print("     this is indistinguishable from what an empty 3 Hz band produces on this route)")
    print(f"   ⚠ NULL-A is CONTAMINATED and therefore CONSERVATIVE: this route carries real")
    print("     10.5-13.5 Hz lines at 18-25 m/s (highway), so its p95 over-states the noise")
    print(f"     floor. The permissive floor (NULL-B alone) is {fb_:.2f}. Both are reported")
    print("     below; every headline number uses the CONSERVATIVE floor.")
    return floor, fb_


def scan_report(recs, floor, loose):
    hdr("3.  ROUTE-WIDE 6-9 Hz SCAN -- disjoint 2.56 s windows, all 8 segments")
    pb = col(recs, "pb")
    det = pb >= floor
    print(f"   windows {len(recs)}   detections {int(det.sum())} ({100 * det.mean():.1f}%) "
          f"at the CONSERVATIVE floor {floor:.1f}")
    dl = pb >= loose
    print(f"   {'':21s}         {int(dl.sum())} ({100 * dl.mean():.1f}%) "
          f"at the permissive floor {loose:.1f}")
    lat = col(recs, "lat") > 0.5
    v = col(recs, "v")
    print(f"   detections engaged {int((det & lat).sum())}/{int(lat.sum())} "
          f"= {100 * (det & lat).sum() / max(lat.sum(), 1):.1f}%   "
          f"manual {int((det & ~lat).sum())}/{int((~lat).sum())} "
          f"= {100 * (det & ~lat).sum() / max((~lat).sum(), 1):.1f}%")
    print("\n   by speed bin (per-window census -- a moving wheel order would concentrate here):")
    edges = [0, 1, 2, 4, 7, 11, 16, 30]
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (v >= lo) & (v < hi)
        if m.sum() == 0:
            continue
        f0s = col(recs, "fb")[m & det]
        print(f"     {lo:2d}-{hi:2d} m/s  n={int(m.sum()):3d}  det {int((m & det).sum()):3d} "
              f"({100 * (m & det).sum() / m.sum():5.1f}%)  "
              f"f0 med {np.median(f0s) if len(f0s) else float('nan'):5.2f} Hz  "
              f"env99 med {np.median(col(recs, 'env99')[m]):6.0f}  "
              f"wheel-order-1 = {np.mean([lo, hi]) / CIRC[0]:5.2f} Hz")

    hdr("3b. THE 30 LOUDEST 6-9 Hz WINDOWS ON THE ROUTE, by prominence")
    order = np.argsort(-np.nan_to_num(pb, nan=-1))
    print(f"   {'seg':>3s} {'t0':>6s} {'f0':>5s} {'prom':>9s} {'Q':>5s} {'env99':>6s} {'pp':>6s} "
          f"{'|v|':>5s} {'ang':>7s} {'|rt|90':>6s} {'eff':>5s} {'effmx':>6s} {'lat':>4s} "
          f"{'rpm':>5s} {'g1Hz':>5s} {'g1pr':>6s}")
    for j in order[:30]:
        r = recs[j]
        print(f"   {r['seg']:3d} {r['t0']:6.1f} {r['fb']:5.2f} {r['pb']:9.1f} {r['Q']:5.1f} "
              f"{r['env99']:6.0f} {2 * r['env99']:6.0f} {r['v']:5.2f} {r['ang']:7.1f} "
              f"{r['rate90']:6.0f} {r['eff']:5.0f} {r['effmax']:6.0f} {r['lat']:4.2f} "
              f"{r['rpm']:5.0f} {r['fg']:5.2f} {r['pg']:6.1f}")
    return det


# ---------------------------------------------------------------- 4. episodes -------------------
def episodes(recs, det):
    """Contiguous runs of detected windows within one segment = one physical episode."""
    eps, cur = [], []
    for r, dd in zip(recs, det):
        if dd and (not cur or (r["seg"] == cur[-1]["seg"] and r["i0"] == cur[-1]["i0"] + NFFT)):
            cur.append(r)
        else:
            if cur:
                eps.append(cur)
            cur = [r] if dd else []
    if cur:
        eps.append(cur)
    return eps


def episode_report(eps):
    hdr("4.  EPISODE INVENTORY -- the deliverable. One row per physical episode.")
    print("   f0 CI = 2.5/97.5 pct of a 2,000-draw bootstrap over the episode's own WINDOWS")
    print("   (within an episode the windows are the only replicates there are; the ROUTE-level")
    print("    statistics in section 7 bootstrap over EPISODES, which is the unit of inference).")
    print(f"\n   {'ep':>2s} {'seg':>3s} {'t start-end':>13s} {'dur':>5s} {'f0':>5s} "
          f"{'f0 CI':>13s} {'prom':>8s} {'Q':>5s} {'pp cnt':>7s} {'|v| m/s':>13s} "
          f"{'ang deg':>8s} {'|rt|90':>6s} {'eff':>5s} {'lat':>4s} {'ST':>4s}")
    for k, e in enumerate(eps):
        fb = col(e, "fb")
        if len(fb) > 1:
            bs = [np.median(np.random.choice(fb, len(fb))) for _ in range(2000)]
            ci = f"[{np.percentile(bs, 2.5):.2f},{np.percentile(bs, 97.5):.2f}]"
        else:
            ci = "  (n=1 win)  "
        t0, t1 = e[0]["t0"], e[-1]["t0"] + NFFT / e[-1]["fs"]
        st = sorted({int(x) for r in e for x in r["sstat"]})
        print(f"   {k:2d} {e[0]['seg']:3d} {t0:6.1f}-{t1:6.1f} {t1 - t0:5.2f} "
              f"{np.median(fb):5.2f} {ci:>13s} {np.median(col(e, 'pb')):8.1f} "
              f"{np.nanmedian(col(e, 'Q')):5.1f} {2 * np.max(col(e, 'env99')):7.0f} "
              f"{np.min(col(e, 'vmin')):5.2f}-{np.max(col(e, 'vmax')):5.2f}  "
              f"{np.median(col(e, 'ang')):8.1f} {np.max(col(e, 'rate90')):6.0f} "
              f"{np.median(col(e, 'eff')):5.0f} {np.mean(col(e, 'lat')):4.2f} {str(st):>4s}")
    print("\n   eff = median sustained |lowpass(tq,3Hz)| in counts. HANDS-OFF is eff < 300.")
    print("   ST  = the set of STEER_STATUS values seen (0x18F byte4 bits 7:4).")
    return eps


AMP_MIN = 600.0     # 6-9 Hz envelope p99, counts. pp = 2x this = 1200 counts.


def amplitude_inventory(recs):
    hdr("4b. ★ AMPLITUDE-FIRST INVENTORY -- this is the one that matches the OPERATOR's report")
    print("   🛑 WHY A SECOND INVENTORY. The operator reports the ratchet 'mostly in segments 0")
    print("      and 1'. Section 4's PROMINENCE detector puts only one episode in seg 0 and NONE")
    print("      in seg 1 -- because in those segments he was actively steering (|angle| to 276")
    print("      deg, sustained effort to 2617 counts), and active steering raises the local")
    print("      broadband floor that prominence divides by. Prominence measures SPECTRAL PURITY;")
    print("      what a driver feels is AMPLITUDE. Both are reported; neither is discarded.")
    print(f"\n   criterion: 6-9 Hz envelope p99 >= {AMP_MIN:.0f} counts (peak-to-peak >= "
          f"{2 * AMP_MIN:.0f}).")
    print("   zcHz = upward zero-crossing rate of the 6-9 Hz bandpass -- an f0 estimate with no")
    print("   FFT bin in it at all, so it is an INDEPENDENT confirmation of the line frequency.")
    print(f"\n   {'seg':>3s} {'t0':>6s} {'f0':>5s} {'zcHz':>5s} {'prom':>7s} {'pp cnt':>7s} "
          f"{'|v|':>5s} {'ang':>7s} {'|rt|90':>6s} {'eff':>5s} {'lat':>4s} {'rail':>5s} "
          f"{'|cmd|p99':>8s}")
    cache = {}
    hits = []
    for r in recs:
        if r["env99"] < AMP_MIN:
            continue
        s = r["seg"]
        if s not in cache:
            cache[s] = load(s)
        d = cache[s]
        fs = r["fs"]
        w = slice(r["i0"], r["i0"] + NFFT)
        y = d["tq"][w]
        z = y - y.mean()
        X = np.fft.rfft(z)
        ff = np.fft.rfftfreq(len(z), 1 / fs)
        X[(ff < RATCH[0]) | (ff > RATCH[1])] = 0
        b = np.fft.irfft(X, n=len(z))
        sg = np.signbit(b)
        idx = np.flatnonzero(sg[:-1] & ~sg[1:])
        zc = fs / np.mean(np.diff(idx)) if len(idx) >= 3 else np.nan
        rail = float(np.mean(np.abs(d["e4tq"][w]) >= 4000))
        cmd = float(np.percentile(np.abs(d["e4tq"][w]), 99))
        hits.append((r, zc, rail, cmd))
        print(f"   {s:3d} {r['t0']:6.1f} {r['fb']:5.2f} {zc:5.2f} {r['pb']:7.1f} "
              f"{2 * r['env99']:7.0f} {r['v']:5.2f} {r['ang']:7.1f} {r['rate90']:6.0f} "
              f"{r['eff']:5.0f} {r['lat']:4.2f} {rail:5.2f} {cmd:8.0f}")
    zcs = np.array([h[1] for h in hits], float)
    zcs = zcs[np.isfinite(zcs)]
    lat = np.array([h[0]["lat"] for h in hits])
    print(f"\n   {len(hits)} windows ({2.56 * len(hits):.0f} s) at or above {2 * AMP_MIN:.0f} "
          f"counts peak-to-peak.  ENGAGED in {int((lat > 0.9).sum())} of them, "
          f"MANUAL in {int((lat < 0.1).sum())}.")
    print(f"   ZERO-CROSSING f0 over those windows: median {np.median(zcs):.2f} Hz, "
          f"mean {zcs.mean():.2f} +/- {zcs.std(ddof=1):.2f}, range "
          f"[{zcs.min():.2f}, {zcs.max():.2f}] Hz")
    print("   ⇒ compare with the record: 7.56 +/- 0.36 Hz (route 2c), within-run sd 0.07-0.10.")
    rails = np.array([h[2] for h in hits])
    cmds = np.array([h[3] for h in hits])
    print(f"   openpilot |command| p99 in those windows: median {np.median(cmds):.0f} of a "
          f"+/-4096 rail; AT the rail (>= 4000) in {int((cmds >= 4000).sum())}/{len(hits)}")
    print(f"   command-rail DUTY in those windows: median {np.median(rails):.2f}")
    return hits


# ---------------------------------------------------------------- 5. order veto -----------------
def order_veto(eps):
    hdr("5.  ORDER VETO -- wheel order and engine order, per episode, with the arithmetic shown")
    print(f"   CIRC = {CIRC[0]}-{CIRC[1]} m (measured, V56/V57).  wheel order k = k*v/CIRC")
    print("   engine order k = k*rpm/60.  A line is vetoed if an order lands within +/-0.4 Hz.")
    print(f"\n   {'ep':>2s} {'f0':>5s} {'|v|':>5s} {'w1':>5s} {'w2':>5s} {'w3':>5s} {'w6':>5s} "
          f"{'rpm':>5s} {'e0.5':>5s} {'e1':>5s} {'e2':>5s}  verdict")
    for k, e in enumerate(eps):
        f0 = float(np.median(col(e, "fb")))
        v = float(np.median(col(e, "v")))
        rpm = float(np.nanmedian(col(e, "rpm")))
        w = [j * v / CIRC[0] for j in (1, 2, 3, 6)]
        en = [q * rpm / 60.0 for q in (0.5, 1, 2)]
        hits = [f"w{j}" for j, x in zip((1, 2, 3, 6), w) if abs(x - f0) < 0.4] + \
               [f"e{q}" for q, x in zip((0.5, 1, 2), en) if abs(x - f0) < 0.4]
        print(f"   {k:2d} {f0:5.2f} {v:5.2f} " + " ".join(f"{x:5.2f}" for x in w) +
              f" {rpm:5.0f} " + " ".join(f"{x:5.2f}" for x in en) +
              ("  🛑 " + ",".join(hits) if hits else "  ✅ no order within 0.4 Hz"))
    f0s = col([r for e in eps for r in e], "fb")
    vs = col([r for e in eps for r in e], "v")
    ok = np.isfinite(f0s) & np.isfinite(vs)
    if ok.sum() > 3:
        s, b = np.polyfit(vs[ok], f0s[ok], 1)
        print(f"\n   ★ f0 vs speed regression over all detected windows: "
              f"f0 = {s:+.4f}*v + {b:.2f} Hz   (n={int(ok.sum())}, r={np.corrcoef(vs[ok], f0s[ok])[0,1]:+.3f})")
        print(f"     A WHEEL ORDER would have slope 1/CIRC = {1 / CIRC[0]:.3f} Hz per m/s "
              f"(order 1), {2 / CIRC[0]:.3f} (order 2), {6 / CIRC[0]:.3f} (order 6).")
        print(f"     Measured slope is {s:+.4f}. ⇒ the line is SPEED-INVARIANT over "
              f"{vs[ok].min():.1f}-{vs[ok].max():.1f} m/s.")


# ---------------------------------------------------------------- 6. waveform -------------------
def hp(x, fs, fc=4.0):
    """High-pass, NOT band-pass. `analyze_r37_waveform.py`'s method and its reason: a 6-9 Hz
    BANDPASS sinusoidalises any waveform by construction, so every shape metric taken on one is
    identically that of a sine (skew 0.000, kurt 1.5) and measures nothing."""
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f < fc] = 0
    return np.fft.irfft(X, n=len(x))


def waveform(eps):
    hdr("6.  WAVEFORM -- the describing-function evidence, on the HIGH-PASSED bar (>4 Hz)")
    print("   🛑 Metrics are taken on hp(tq, 4 Hz), never on a 6-9 Hz bandpass -- a bandpass")
    print("      sinusoidalises any waveform and returns skew 0.000 for a square wave too.")
    print("      Method and thresholds are `analyze_r37_waveform.py`'s, unchanged.")
    print("   CREST peak/RMS: sine 1.414, sawtooth ~1.73, impulsive stick-slip > 2.")
    print("   RISE FRAC d/dt>0 fraction: sine 0.500; slow-build/fast-collapse >> 0.5.")
    print("   DSKEW skew(d/dt): sine 0; asymmetric collapse |skew| >> 0.")
    print("   ⚠ FLAT-TOPPING is what a hard SATURATION looks like: it pushes crest BELOW 1.414")
    print("     (a square wave is 1.000). Nothing here is flat-topped -- see the column.")
    print(f"\n   {'ep':>2s} {'seg':>3s} {'t0':>6s} {'f0':>5s} {'RMS':>7s} {'crest':>6s} "
          f"{'rise':>6s} {'dskew':>7s} {'xskew':>7s} {'Q':>6s}")
    cache = {}
    rows = []
    for k, e in enumerate(eps):
        s = e[0]["seg"]
        if s not in cache:
            cache[s] = load(s)
        d = cache[s]
        fs = e[0]["fs"]
        a, b = e[0]["i0"], e[-1]["i0"] + NFFT
        y = hp(d["tq"][a:b], fs)
        dv = np.diff(y)
        crest = float(np.max(np.abs(y)) / max(np.sqrt(np.mean(y ** 2)), 1e-9))
        rise = float(np.mean(dv > 0))
        rows.append((crest, rise, skew(dv), skew(y)))
        print(f"   {k:2d} {s:3d} {e[0]['t0']:6.1f} {np.median(col(e, 'fb')):5.2f} "
              f"{np.sqrt(np.mean(y ** 2)):7.1f} {crest:6.2f} {rise:6.3f} {skew(dv):+7.2f} "
              f"{skew(y):+7.2f} {np.nanmedian(col(e, 'Q')):6.1f}")
    a = np.array(rows)
    print(f"\n   MEDIAN over {len(a)} episodes: crest {np.median(a[:, 0]):.2f}  "
          f"rise_frac {np.median(a[:, 1]):.3f}  skew(dx/dt) {np.median(a[:, 2]):+.2f}  "
          f"skew(x) {np.median(a[:, 3]):+.2f}")
    print("   (record, prior builds: skew(x) -0.16..+0.06 against a -3.27 sawtooth calibration)")


# ---------------------------------------------------------------- 6b. is it in the COMMAND? -----
def csd(x, y, fs, nfft=NFFT):
    """Welch cross-spectrum over disjoint Hann windows. Returns f, coherence, phase(y rel. x)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    w = np.hanning(nfft)
    Pxx = Pyy = Pxy = 0.0
    k = 0
    for i in range(0, len(x) - nfft + 1, nfft // 2):
        a = (x[i:i + nfft] - x[i:i + nfft].mean()) * w
        b = (y[i:i + nfft] - y[i:i + nfft].mean()) * w
        A, B = np.fft.rfft(a), np.fft.rfft(b)
        Pxx = Pxx + np.abs(A) ** 2
        Pyy = Pyy + np.abs(B) ** 2
        Pxy = Pxy + np.conj(A) * B
        k += 1
    if k < 2:
        return None
    f = np.fft.rfftfreq(nfft, 1 / fs)
    coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-300)
    return f, coh, np.angle(Pxy), k


def command_test(eps):
    hdr("6b. ★ IS THE 7.4-8.2 Hz LINE IN THE openpilot COMMAND? -- the loop-location test")
    print("   `e4tq` is openpilot's own commanded torque, read off sendcan 0x0E4 bytes 0:1 (src")
    print("   129) -- i.e. the LKAS request BEFORE the EPS sees it. `tq` is the torsion bar.")
    print("   If the command carries the line AND LEADS the bar, the loop closes through the")
    print("   device and the EPS is following. If the bar leads, the command is reacting.")
    print("   🛑 Phase is (bar relative to command). +ve = bar LAGS command = command leads.")
    print("   A one-way delay of D seconds shows as phase = -2*pi*f0*D.")
    print(f"\n   {'ep':>2s} {'seg':>3s} {'f0':>5s} {'cmd prom':>9s} {'cmd pk':>7s} "
          f"{'rate prom':>10s} {'coh':>6s} {'phase':>8s} {'implied lag':>12s} {'nseg':>5s}")
    cache = {}
    for k, e in enumerate(eps):
        s = e[0]["seg"]
        if s not in cache:
            cache[s] = load(s)
        d = cache[s]
        fs = e[0]["fs"]
        # widen to >= 512 samples so the cross-spectrum has >= 2 half-overlapped segments
        a = max(0, e[0]["i0"] - NFFT // 2)
        b = min(len(d["t"]), e[-1]["i0"] + NFFT + NFFT // 2)
        f0 = float(np.median(col(e, "fb")))
        ff = np.fft.rfftfreq(NFFT, 1 / fs)
        Pc = periodogram(d["e4tq"][a:a + NFFT], fs, NFFT)
        Pr = periodogram(d["rate_c"][a:a + NFFT], fs, NFFT)
        fc, pc = peak_prom(ff, Pc, *RATCH) if Pc is not None else (np.nan, np.nan)
        _, pr = peak_prom(ff, Pr, *RATCH) if Pr is not None else (np.nan, np.nan)
        out = csd(d["e4tq"][a:b], d["tq"][a:b], fs)
        if out is None:
            print(f"   {k:2d} {s:3d} {f0:5.2f}  (too short for a cross-spectrum)")
            continue
        fx, coh, ph, nk = out
        j = int(np.argmin(np.abs(fx - f0)))
        lag = -ph[j] / (2 * np.pi * f0) * 1000.0
        print(f"   {k:2d} {s:3d} {f0:5.2f} {pc:9.1f} {fc:7.2f} {pr:10.1f} {coh[j]:6.3f} "
              f"{np.degrees(ph[j]):+8.1f} {lag:+9.1f} ms {nk:5d}")
    print("\n   ⚠ Coherence from n half-overlapped segments has a bias floor ~1/n; with n = 2-4")
    print("     a coherence below ~0.5 is NOT evidence of coupling. Read the COMMAND PROMINENCE")
    print("     column first: if the command has no 6-9 Hz line at all, phase is meaningless.")


def sideband_test(eps):
    hdr("6c. GRIND #1 CO-OCCURRENCE -- is the 20 Hz line MODULATED at the ratchet frequency?")
    print("   Every one of the loudest ratchet windows also carries a 18-22 Hz line. If grind #1")
    print("   were amplitude-modulated at f0 the spectrum would show SIDEBANDS at fg +/- f0 and")
    print("   the ratchet would be a modulation envelope, not an independent mode.")
    print(f"\n   {'ep':>2s} {'seg':>3s} {'f0':>5s} {'fg':>5s} {'fg prom':>8s} "
          f"{'P(fg-f0)/P(fg)':>15s} {'P(fg+f0)/P(fg)':>15s} {'2f0 prom':>9s} {'fg/f0':>6s}")
    cache = {}
    for k, e in enumerate(eps):
        s = e[0]["seg"]
        if s not in cache:
            cache[s] = load(s)
        d = cache[s]
        fs = e[0]["fs"]
        i = e[0]["i0"]
        P = periodogram(d["tq"][i:i + NFFT], fs, NFFT)
        if P is None:
            continue
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        f0 = float(np.median(col(e, "fb")))
        fg, pg = peak_prom(f, P, *GRIND1)
        if not np.isfinite(fg):
            continue

        def at(x):
            return float(P[int(np.argmin(np.abs(f - x)))])
        _, p2 = peak_prom(f, P, 2 * f0 - 0.8, 2 * f0 + 0.8)
        print(f"   {k:2d} {s:3d} {f0:5.2f} {fg:5.2f} {pg:8.1f} "
              f"{at(fg - f0) / max(at(fg), 1e-9):15.4f} {at(fg + f0) / max(at(fg), 1e-9):15.4f} "
              f"{p2:9.1f} {fg / f0:6.2f}")
    print("\n   A true AM sideband pair sits within a factor ~4 of each other and well above the")
    print("   local floor. Ratios of 1e-2 or below on both sides mean the two lines are")
    print("   INDEPENDENT modes that merely co-occur.")


# ---------------------------------------------------------------- 7. cross-build ----------------
BUILDS = [
    ("V59 r2c", "_cache_r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12]),
    ("V61 r31", "_cache_r31", "r31s", [0, 1, 2, 3]),
    ("V62 r37", "_cache_r37", "r37s", list(range(0, 15))),
    ("V64 r35", "_cache_r35", "r35s", [0, 1, 2]),
    ("V65 r3a", "_cache_r3a", "r3as", None),
    ("V67 r47", "_cache_r47", "r47s", None),
    ("V68 r4c", "_cache_v68", "4cs", None),
    ("V69 r4f", "_cache_r4f", "r4fs", SEGS),
]


def build_cell(name, cache, pfx, segs, vcap=CREEP):
    """6-9 Hz records in the RATCHET CELL: engaged + v <= vcap + hands-off."""
    import glob
    if segs is None:
        fs_ = sorted(glob.glob(str(ROOT / cache / f"{pfx}*.npz")))
        segs = []
        for p in fs_:
            b = Path(p).stem[len(pfx):]
            if b.isdigit():
                segs.append(int(b))
        segs.sort()
    out = []
    for s in segs:
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = {k: v for k, v in np.load(p).items()}
        if "tq" not in d or len(d["t"]) < NFFT * 2:
            continue
        fs = fs_mean(d)
        eff = np.abs(sustained(d["tq"], fs))
        sel = (d["cc_lat"] > 0.5) & (np.abs(d["cs_v"]) <= vcap) & (eff < HANDS_OFF)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        env = band_envelope(d["tq"], fs, *RATCH)
        # contiguous runs of the cell, disjoint windows inside each run = one episode per run
        idx = np.flatnonzero(sel)
        if not len(idx):
            continue
        runs, a = [], idx[0]
        for i in range(1, len(idx)):
            if idx[i] != idx[i - 1] + 1:
                runs.append((a, idx[i - 1] + 1))
                a = idx[i]
        runs.append((a, idx[-1] + 1))
        for ri, (a, b) in enumerate(runs):
            if b - a < NFFT:
                continue
            for i in range(a, b - NFFT + 1, NFFT):
                P = periodogram(d["tq"][i:i + NFFT], fs, NFFT)
                if P is None:
                    continue
                fb, pb = peak_prom(f, P, *RATCH)
                _, pca = peak_prom(f, P, *CTRL_A)
                out.append(dict(tag=name, ep=(s, ri), fb=fb, pb=pb, pca=pca,
                                env99=float(np.percentile(env[i:i + NFFT], 99)),
                                v=float(np.abs(d["cs_v"][i:i + NFFT]).mean())))
    return out


def boot_ep(recs, key, n=4000):
    """Episode-clustered bootstrap of the median of `key`."""
    eps = {}
    for r in recs:
        eps.setdefault(r["ep"], []).append(r)
    ks = list(eps)
    if not ks:
        return np.nan, np.nan, np.nan, 0
    vals = []
    for _ in range(n):
        pick = [eps[ks[j]] for j in np.random.randint(0, len(ks), len(ks))]
        flat = [x[key] for g in pick for x in g if np.isfinite(x[key])]
        if flat:
            vals.append(np.median(flat))
    obs = np.median([r[key] for r in recs if np.isfinite(r[key])])
    return obs, np.percentile(vals, 2.5), np.percentile(vals, 97.5), len(ks)


def cross_build():
    hdr("7.  CROSS-BUILD -- the ratchet cell (engaged + creep + hands-off), episode-clustered")
    print("   ⚠ Different routes, different exposure. This is an OBSERVATIONAL comparison across")
    print("     builds, not a controlled A/B, and the speed census is printed so a shifted")
    print("     distribution cannot masquerade as a build effect.")
    for vcap, lbl in ((CREEP, f"CELL A: engaged + |v| <= {CREEP} m/s + hands-off  (the "
                              "decoder's own cell)"),
                      (8.0, "CELL B: engaged + |v| <= 8.0 m/s + hands-off  (wider -- route 4f's "
                            "loudest episodes reach 12.7 m/s)")):
        print(f"\n   {lbl}")
        print(f"   {'build':10s} {'eps':>4s} {'win':>5s} {'secs':>6s} {'f0':>5s} {'prom':>8s} "
              f"{'prom CI':>19s} {'env99 pp':>9s} {'pp CI':>19s} {'|v| p10/50/90':>16s}")
        for name, cache, pfx, segs in BUILDS:
            r = build_cell(name, cache, pfx, segs, vcap)
            if not r:
                print(f"   {name:10s}  -- no cell windows")
                continue
            o1, l1, h1, ne = boot_ep(r, "pb")
            o2, l2, h2, _ = boot_ep(r, "env99")
            v = col(r, "v")
            print(f"   {name:10s} {ne:4d} {len(r):5d} {len(r) * NFFT / 100:6.1f} "
                  f"{np.nanmedian(col(r, 'fb')):5.2f} {o1:8.1f} "
                  f"[{l1:7.1f},{h1:8.1f}] {2 * o2:9.0f} [{2 * l2:7.0f},{2 * h2:8.0f}] "
                  f"{np.percentile(v, 10):4.2f}/{np.percentile(v, 50):4.2f}/"
                  f"{np.percentile(v, 90):4.2f}")
    print("\n   pp = peak-to-peak torsion-bar counts in the 6-9 Hz band (2 x envelope p99).")
    print("   🛑 CIs overlap everywhere. Read this table as EXPOSURE + a rough level, not as a")
    print("      dose-response: no pair of builds is separated by it.")


def main():
    np.random.seed(20260804)
    print(__doc__)
    probe_state()
    recs = route_scan()
    floor, loose = nulls(recs)
    det = scan_report(recs, floor, loose)
    eps = episode_report(episodes(recs, det))
    amplitude_inventory(recs)
    order_veto(eps)
    waveform(eps)
    command_test(eps)
    sideband_test(eps)
    cross_build()


if __name__ == "__main__":
    main()
