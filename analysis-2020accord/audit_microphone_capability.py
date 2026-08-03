#!/usr/bin/env python3
"""audit_microphone_capability.py -- what the comma microphone CAN and CANNOT settle.

The microphone is the only instrument in this kit without a ~50 Hz ceiling, so it is the only
existing evidence that can speak to a >50 Hz highway symptom. This script establishes, from the
LOGGED DATA rather than from assumption, exactly how much it can resolve.

WHAT micd.py ACTUALLY DOES (read from the StarPilot checkout, `system/micd.py`):

    SAMPLE_RATE  = 16000        audio Nyquist 8000 Hz  -- no mechanical-band ceiling at all
    FFT_SAMPLES  = 1600         soundPressure = RMS over exactly 100.0 ms, RECTANGULAR, NON-overlapping
    SAMPLE_BUFFER= 800          audio callback every 50 ms
    RATE         = 10           publish rate; `update()` re-reads whatever the callback last stored

⇒ THE INSTRUMENT IS AN ENVELOPE DETECTOR, NOT A SPECTROMETER. One scalar RMS per 100 ms. The audio
carrier frequency is DESTROYED by the RMS; only its ENERGY survives. So the microphone can bound an
amplitude but can NEVER name a frequency. That distinction decides whether it can root-cause.

Two consequences that are measured, not assumed, below:
  (a) the 100 ms boxcar is a sinc envelope filter, first null at 10.0 Hz, -3 dB at 4.43 Hz;
  (b) the publish grid is 10 Hz => envelope Nyquist 5.00 Hz.
So amplitude MODULATION is recoverable only below 5 Hz, and a STEADY tone contributes only a DC
level shift -- which is confounded with road noise and is why speed-matched controls are mandatory.

🛑 The publish loop and the audio callback run on DIFFERENT clocks (Ratekeeper vs the codec), so
some published values are verbatim repeats of the previous block and some blocks are never
published. The repeat fraction is measured here -- it is the honest effective update rate.

Usage:  python audit_microphone_capability.py            # r47 + r2b + r4a
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rlog-tools"))
RLOG = ROOT / "analysis-2020accord" / "rlogs"

ROUTES = {"r47": ("75604b0a432fdc89_00000047--3e0b6134c0", range(26), "V67"),
          "r2b": ("75604b0a432fdc89_0000002b--7926e8f7e5", range(14), "stock Kd=1.00"),
          "r4a": ("75604b0a432fdc89_0000004a--346bf31d97", range(20, 26), "V67 route 2")}
FFT_SAMPLES, SAMPLE_RATE, PUBRATE = 1600, 16000, 10.0
BLOCK_S = FFT_SAMPLES / SAMPLE_RATE


def lattice_rate(t):
    dt = np.diff(np.asarray(t, float))
    dt = dt[dt > 0]
    if len(dt) < 8:
        return np.nan, np.nan
    p = float(np.median(dt))
    for _ in range(6):
        k = np.round(dt / p)
        ok = (k >= 1) & (k <= 20) & (np.abs(dt / p - k) < 0.35)
        if ok.sum() < 8:
            break
        p = float(dt[ok].sum() / k[ok].sum())
    k = np.round(dt / p)
    ok = (k >= 1) & (k <= 20) & (np.abs(dt / p - k) < 0.35)
    return 1 / p, float(np.std((dt[ok] / p - k[ok]) * p))


def ensure_sound(tag):
    """Extract the soundPressure stream for any segment that has a CAN cache but no _snd cache."""
    route, segs, _ = ROUTES[tag]
    out = ROOT / f"_cache_{tag}"
    made = 0
    for s in segs:
        f = out / f"{tag}s{s}_snd.npz"
        can = out / f"{tag}s{s}.npz"
        if f.exists() or not can.exists():
            continue
        p = RLOG / f"{route}--{s}--rlog.zst"
        if not p.exists():
            continue
        from rlog_parse import read_messages
        z = np.load(can)
        t0 = float(z["t0_mono"][0])
        t, u, w, db = [], [], [], []
        for evt in read_messages(p):
            try:
                if evt.which() != "soundPressure":
                    continue
            except Exception:
                continue
            m = evt.soundPressure
            t.append(evt.logMonoTime * 1e-9 - t0)
            u.append(float(m.soundPressure))
            w.append(float(m.soundPressureWeighted))
            db.append(float(m.soundPressureWeightedDb))
        np.savez_compressed(f, t=np.array(t), unw=np.array(u), wt=np.array(w), db=np.array(db))
        made += 1
    if made:
        print(f"  ({tag}: extracted {made} new sound caches)")


def load(tag):
    """Sound stream + speed, per segment, on the segment's own t0."""
    route, segs, _ = ROUTES[tag]
    out = ROOT / f"_cache_{tag}"
    segd = []
    for s in segs:
        f, can = out / f"{tag}s{s}_snd.npz", out / f"{tag}s{s}.npz"
        if not (f.exists() and can.exists()):
            continue
        d = np.load(f)
        k = "unw" if "unw" in d.files else "sp"
        kw = "wt" if "wt" in d.files else "spw"
        z = np.load(can)
        v = np.interp(d["t"], z["t"], z["cs_v"])           # speed at each sound sample
        segd.append(dict(seg=s, t=d["t"], sp=d[k], spw=d[kw], v=v))
    return segd


def report():
    print(__doc__.split("Usage:")[0].rstrip())
    print("\n" + "=" * 100)
    print("1. WHAT IS LOGGED, AND AT WHAT RATE (measured)")
    print("=" * 100)
    print(f"{'route':>6s} {'build':>16s} {'n':>7s} {'span_s':>9s} {'latt_Hz':>9s} {'jit_ms':>7s} "
          f"{'repeat%':>8s} {'fields':>34s}")
    ALL = {}
    for tag in ROUTES:
        ensure_sound(tag)
        segd = load(tag)
        if not segd:
            print(f"{tag:>6s}   no cached sound")
            continue
        ALL[tag] = segd
        n = sum(len(d["t"]) for d in segd)
        span = sum(d["t"][-1] - d["t"][0] for d in segd)
        f, jit = lattice_rate(np.concatenate([d["t"] for d in segd if len(d["t"]) > 8][:1]))
        # repeat fraction: consecutive published values BITWISE identical => the 10 Hz publish loop
        # re-sent a block the audio callback had not yet replaced.
        rep = np.mean(np.concatenate([np.diff(d["sp"]) == 0 for d in segd]))
        print(f"{tag:>6s} {ROUTES[tag][2]:>16s} {n:7d} {span:9.1f} {f:9.4f} {1e3 * jit:7.3f} "
              f"{100 * rep:8.3f} {'soundPressure/Weighted/WeightedDb':>34s}")
    print("\n  soundPressure is a Float32 SCALAR. log.capnp `struct SoundPressure` has THREE float")
    print("  fields and nothing else -- no spectrum, no bins, no raw samples. => AMPLITUDE ONLY.")
    print(f"  repeat% is the fraction of published samples that repeat the previous block verbatim;")
    print(f"  it is the mismatch between the {BLOCK_S * 1e3:.1f} ms audio block and the "
          f"{1000 / PUBRATE:.0f} ms publish tick.")

    print("\n" + "=" * 100)
    print("2. ENVELOPE BANDWIDTH -- the 100 ms rectangular RMS window (sinc), then 10 Hz sampling")
    print("=" * 100)
    print(f"  {'f_mod Hz':>9s} {'|sinc(fT)|':>11s} {'dB':>8s}   note")
    for fm in (0.5, 1, 2, 3, 4, 5, 6, 8, 10, 10.0):
        x = np.pi * fm * BLOCK_S
        g = 1.0 if x == 0 else abs(np.sin(x) / x)
        note = ("" if fm < 5 else ("<- envelope NYQUIST" if fm == 5 else "<- ALIASED, unusable"))
        if abs(fm - 1 / BLOCK_S) < 1e-9:
            note = "<- first sinc NULL"
        print(f"  {fm:9.2f} {g:11.4f} {20 * np.log10(max(g, 1e-9)):8.2f}   {note}")
    print(f"\n  => usable modulation band 0 .. {PUBRATE / 2:.2f} Hz, worst-case window droop "
          f"{20 * np.log10(abs(np.sin(np.pi * 5 * BLOCK_S) / (np.pi * 5 * BLOCK_S))):.2f} dB.")
    print("  A STEADY tone at any frequency (50, 80, 150, 500 Hz) modulates NOTHING: it only raises")
    print("  the DC level. Only a BURSTING or BEATING vibration under 5 Hz leaves an AC signature.")

    print("\n" + "=" * 100)
    print("3. DYNAMIC RANGE AND THE HIGHWAY NOISE FLOOR")
    print("=" * 100)
    rng = np.random.default_rng(11)
    for tag, segd in ALL.items():
        sp = np.concatenate([d["sp"] for d in segd])
        v = np.concatenate([d["v"] for d in segd])
        hw = v > 25.0                                        # >90 km/h
        cr = (v > 0.3) & (v < 6.0)
        # ⚠ micd initialises sound_pressure = 0 and publishes it until the first audio block
        # arrives, so exact zeros are STARTUP, not a measured silence. Excluded from the range.
        nz = int((sp == 0).sum())
        pos = sp[sp > 0]
        print(f"\n  {tag} ({ROUTES[tag][2]})   n={len(sp)}  ({nz} exact-zero startup samples excluded)")
        print(f"    all speeds : min {pos.min():.6f}  p1 {np.percentile(pos, 1):.6f}  "
              f"med {np.median(pos):.6f}  p99 {np.percentile(pos, 99):.6f}  max {pos.max():.6f}")
        print(f"    dynamic range max/min = {pos.max() / pos.min():.1f}x "
              f"({20 * np.log10(pos.max() / pos.min()):.1f} dB); "
              f"float32 => quantisation is NOT the limit")
        for lab, m in (("HIGHWAY v>25 m/s", hw), ("creep 0.3-6 m/s", cr)):
            if m.sum() < 50:
                print(f"    {lab:16s}  n={m.sum()} -- too few")
                continue
            x = sp[m]
            print(f"    {lab:16s}  n={m.sum():6d}  med {np.median(x):.6f}  "
                  f"IQR {np.percentile(x, 75) - np.percentile(x, 25):.6f}  "
                  f"p90/med {np.percentile(x, 90) / np.median(x):.3f}  "
                  f"sd/med {x.std() / np.median(x):.4f}")
        # the honest detection threshold: split the HIGHWAY samples into random 10 s blocks and
        # bootstrap the p90 ratio between two halves. Nothing real distinguishes the halves, so the
        # spread IS the noise floor of the "maneuver vs control" estimator this kit uses.
        if hw.sum() > 400:
            xs = sp[hw]
            nb = len(xs) // 100                              # 100 samples = 10 s blocks
            blocks = np.array([np.percentile(xs[i * 100:(i + 1) * 100], 90) for i in range(nb)])
            r = []
            for _ in range(4000):
                p = rng.permutation(nb)
                h = nb // 2
                r.append(np.median(blocks[p[:h]]) / np.median(blocks[p[h:2 * h]]))
            lo, hi = np.percentile(r, [2.5, 97.5])
            phi_lo = hi ** 2 - 1                             # s ~ sqrt(P): ratio^2 - 1 = P_vib/P_road
            print(f"    SPLIT-HALF NULL on 10 s blocks (n={nb}): p90 ratio 95% [{lo:.3f}, {hi:.3f}]")
            print(f"      => minimum detectable ACOUSTIC POWER fraction phi = ratio^2 - 1 = "
                  f"{100 * phi_lo:.1f}% of road-noise power ({10 * np.log10(1 + phi_lo):.2f} dB)")

    print("\n" + "=" * 100)
    print("4. IS THERE ANY AC (MODULATION) SIGNATURE AT HIGHWAY? -- PSD of the soundPressure series")
    print("=" * 100)
    print("  Windows are CONTIGUOUS highway runs (v>25 m/s, >=25.6 s), Welch-averaged. The floor is\n"
          "  taken ABOVE 0.5 Hz because cabin noise is red: the 0.04-0.4 Hz bins are road-surface and\n"
          "  throttle drift, not a vibration line, and using them as the baseline hides everything.")
    for tag, segd in ALL.items():
        # contiguous highway runs, spliced per segment so a segment join never enters a window
        runs = []
        for d in segd:
            m = d["v"] > 25.0
            i = 0
            while i < len(m):
                if not m[i]:
                    i += 1
                    continue
                j = i
                while j < len(m) and m[j]:
                    j += 1
                if j - i >= 256:
                    runs.append(d["sp"][i:j])
                i = j
        if not runs:
            print(f"  {tag}: no contiguous highway run >= 25.6 s")
            continue
        P, nw = None, 0
        for x in runs:
            for i in range(len(x) // 256):
                w = x[i * 256:(i + 1) * 256]
                w = (w - w.mean()) * np.hanning(256)
                p = np.abs(np.fft.rfft(w)) ** 2
                P = p if P is None else P + p
                nw += 1
        P /= nw
        fr = np.fft.rfftfreq(256, 1 / PUBRATE)
        hi = fr >= 0.5
        base = np.median(P[hi])
        idx = np.arange(len(fr))[hi]
        pk = idx[np.argmax(P[hi])]
        print(f"\n  {tag} ({ROUTES[tag][2]}): {len(runs)} runs, {nw} x 25.6 s windows, "
              f"resolution {fr[1]:.4f} Hz, total {nw * 25.6:.0f} s")
        print(f"    strongest bin ABOVE 0.5 Hz: {fr[pk]:.3f} Hz at {P[pk] / base:.2f}x the "
              f"0.5-5 Hz median floor")
        print(f"    (chi2_2 noise over {hi.sum()} bins gives a max/median of ~"
              f"{-np.log(1 - 0.5 ** (1 / hi.sum())) / np.log(2):.1f}x by chance alone => "
              f"{'NO LINE' if P[pk] / base < 8 else 'CANDIDATE LINE'})")
        top = idx[np.argsort(P[hi])[::-1][:4]]
        print("    top 4 bins >0.5 Hz: " + "  ".join(f"{fr[i]:.2f}Hz {P[i] / base:.1f}x" for i in top))
        print(f"    red-noise check: P(0.04-0.4 Hz)/P(>0.5 Hz) = "
              f"{P[(fr > 0.03) & (fr < 0.4)].mean() / base:.1f}x  <- drift, expected")

    print("\n" + "=" * 100)
    print("5. MINIMUM DETECTABLE MODULATION DEPTH (the concrete power estimate)")
    print("=" * 100)
    print("  Model: acoustic power P = P_road*(1 + phi*(1 + m*cos(2*pi*f_m*t))), soundPressure")
    print("  s = sqrt(P). For small phi, s/s_road ~ 1 + phi/2 + (phi*m/2)*cos(...).")
    print("  An FFT over N samples of the 10 Hz series concentrates a line against a white floor,")
    print("  gaining sqrt(N/2) in amplitude SNR. Require a 4-sigma line to call a detection.")
    for tag, segd in ALL.items():
        sp = np.concatenate([d["sp"] for d in segd])
        v = np.concatenate([d["v"] for d in segd])
        x = sp[v > 25]
        if len(x) < 400:
            continue
        # residual after removing slow trend: the broadband part the line must beat
        k = 21
        trend = np.convolve(x, np.ones(k) / k, mode="same")
        r = (x - trend)[k:-k]
        sig = float(np.std(r) / np.median(x))                # fractional broadband noise
        for D in (60.0, 227.0, 900.0):
            N = D * PUBRATE
            amp_min = 4.0 * sig / np.sqrt(N / 2)             # detectable fractional AC amplitude
            print(f"  {tag:>4s}  frac broadband noise sd/med = {sig:.4f}   D={D:6.0f}s  N={N:6.0f}  "
                  f"min detectable AC amp {100 * amp_min:.3f}%  => phi*m > {200 * amp_min:.3f}% "
                  f"of road-noise POWER")
        print()
    print("  READ IT THIS WAY, and note the two thresholds differ by ~5x:")
    print("   - STEADY tone, seen only as a DC level shift  => needs ~25% of road-noise acoustic")
    print("     power (section 3 split-half null). A weak bound.")
    print("   - MODULATED (<5 Hz) event, seen as an AC line  => needs ~6% over 227 s, ~3% over 15 min.")
    print("   - Either way the microphone returns ONE NUMBER PER 100 ms. It can bound an amplitude.")
    print("     It can NEVER report the vibration's frequency, so it cannot root-cause anything.")




def tactile_bound():
    """🛑 RE-SCOPED 2026-08-02: the operator FEELS the highway event and does NOT hear it.

    That inverts the question. The mic is no longer a candidate instrument -- it is a null whose
    WEIGHT has to be stated honestly. Three numbers do that, and all three are bad for the null.
    """
    print("\n" + "=" * 100)
    print("6. HOW MUCH WEIGHT CAN THE MICROPHONE NULL BEAR ON A *TACTILE* EVENT?")
    print("=" * 100)
    # (i) the only validated positive control vs the bound the null is being asked to enforce
    pos = 4.14                      # grind #2, soundPressure p95 maneuver/control (docs/HANDOFF 2026-08-02)
    thr = 1.119                     # this script's measured split-half null upper bound, r47 highway
    print(f"  (i) VALIDATION GAP")
    print(f"      only validated positive control : {pos:.2f}x amplitude => excess power phi = "
          f"{pos ** 2 - 1:.2f} ({100 * (pos ** 2 - 1):.0f}% of control)")
    print(f"      bound the highway null enforces : {thr:.3f}x amplitude => phi = {thr ** 2 - 1:.3f} "
          f"({100 * (thr ** 2 - 1):.1f}%)")
    print(f"      => the ONE positive control this instrument has sits "
          f"{(pos ** 2 - 1) / (thr ** 2 - 1):.0f}x ABOVE the smallest event the null excludes.")
    print(f"      Nothing has ever been demonstrated in between. The null is an EXTRAPOLATION over")
    print(f"      {(pos ** 2 - 1) / (thr ** 2 - 1):.0f}x of unvalidated dynamic range.")
    # (ii) the positive control was at CREEP; highway road noise is far louder
    creep, hwy = 0.019267, 0.060629     # r47 medians, section 3
    print(f"\n  (ii) NOISE-FLOOR TRANSFER")
    print(f"      grind #2 was validated at CREEP (median soundPressure {creep:.5f}); the highway")
    print(f"      floor is {hwy:.5f} = {hwy / creep:.2f}x in amplitude, {(hwy / creep) ** 2:.1f}x in POWER.")
    print(f"      The validation does not transfer: the same absolute event is {(hwy / creep) ** 2:.1f}x")
    print(f"      harder to see at highway than where the instrument was proven.")
    # (iii) noise bandwidth -- the mic sums 0-8 kHz into one number; the ear resolves critical bands
    BW_MIC, F0, FRAC = 8000.0, 80.0, 2 ** (1 / 3)
    bw_ear = F0 * (FRAC ** 0.5 - FRAC ** -0.5)
    print(f"\n  (iii) BANDWIDTH PENALTY vs THE EAR (the operator is the better instrument here)")
    print(f"      soundPressure is ONE RMS over the whole {BW_MIC:.0f} Hz audio band. A tone must")
    print(f"      therefore compete with ALL of it. The ear resolves ~1/3-octave critical bands:")
    print(f"      at {F0:.0f} Hz that is {bw_ear:.1f} Hz wide.")
    print(f"      noise-bandwidth penalty = 10*log10({BW_MIC:.0f}/{bw_ear:.1f}) = "
          f"{10 * np.log10(BW_MIC / bw_ear):.1f} dB, BEFORE any masking-threshold advantage.")
    print(f"\n  ⇒ VERDICT ON THE NULL. The operator reports the event is INAUDIBLE. His ear is roughly")
    print(f"    {10 * np.log10(BW_MIC / bw_ear):.0f} dB more sensitive than this channel for a tone in noise, it was")
    print(f"    listening in the right place, and it heard nothing. The microphone agreeing with him")
    print(f"    is NOT independent evidence -- it is a strictly weaker instrument reproducing a")
    print(f"    stronger one's null. 🛑 THE MICROPHONE NULL CARRIES ESSENTIALLY NO WEIGHT ON A")
    print(f"    TACTILE EVENT, and it never could have. It bounds AUDIBLE energy only.")


if __name__ == "__main__":
    report()
    tactile_bound()
