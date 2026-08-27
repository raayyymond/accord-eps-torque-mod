r"""THIRD ACOUSTIC PASS -- built for the GRINDS, which are all SUB-100 Hz.

TARGETS (operator's own numbering, from the orchestrator's brief):
    grind #1   21.0-22.5 Hz   low speed, < 10 mph -- his stated grinding window.  Wheel-rate
                              evidence: line at 21.73 Hz, prominence 39.18 vs null p95 3.07,
                              77.3 % of 15-22 Hz power, ABSENT in manual.
    grind #2   43-45 Hz       creep
    grind #3   45-47 Hz       highway, lane changes.  ⚠ SOFT localisation -- his own words were
                              "maybe this is a grind #3 or #2.5... I am not sure", so this pass
                              stores 10-100 Hz whole and the analysis SEARCHES 35-55 Hz rather
                              than assuming a band.

TWO PASSES OVER THE SAME PCM READ, because the two readings of "grinding" need different tools.

  PASS A -- DIRECT SUB-100 Hz CONTENT.  NFFT 16384 at 16 kHz.
     bin width 0.9766 Hz, window 1.024 s, hop 4096 -> 3.906 Hz frame rate.
     🛑 This is the fix for the defect that made the first pass's 21-28 Hz column read exactly
        0.0: NFFT 1024 gives 15.625 Hz bins and NO bin centre lands in 21-28 Hz.  At 16384 the
        21.0-22.5 Hz target spans ~2 bins and 43-47 Hz spans ~4.  Stores the whole 0-100 Hz
        spectrum (103 bins) so the 35-55 Hz search is not pre-committed to a band.

  PASS B -- AMPLITUDE MODULATION, which is the more likely physical signature.
     A 21 Hz mechanical mode does not radiate a 21 Hz tone into a cabin -- 21 Hz is a 16 m
     wavelength and a steering rack is a hopeless radiator at that frequency.  What a rough,
     sticking mechanism does is MODULATE broadband mechanical noise (stick-slip, gear mesh,
     bearing roughness) at the mode rate.  So the audible signature to hunt is broadband energy
     from a few hundred Hz to a few kHz, AMPLITUDE-MODULATED at 21-47 Hz.
     🛑 FEATURE RATE IS THE BINDING CONSTRAINT AND THE PREVIOUS PASS WAS TOO SLOW.
        `decode/extract_audio_env.py` ran envelopes at 125 Hz behind a 50 Hz low-pass: Nyquist 62.5 Hz,
        but the 50 Hz anti-alias attenuates 43-47 Hz by 1-2 dB and leaves no headroom.
        HERE: envelope low-passed at **200 Hz** and decimated to **500 Hz** -> Nyquist 250 Hz.
        Modulation at 21-47 Hz is resolved with >5x headroom and no filter shaping in the band.

STORED
    sp        (nA, 103) float32   PASS A power spectrum, 0-100 Hz, 0.9766 Hz bins
    sp_f      (103,)              its bin centres
    t_sp      (nA,)               PASS A frame times
    env       (nB, nband) float32 PASS B envelopes at 500 Hz
    env_f     (nband, 2)          carrier band edges
    t_env     (nB,)
    splice    (nB,) bool          PCM discontinuity within +-0.5 s -- filter transient, DROP THESE

usage:  python decode/extract_audio_grind.py            # all six routes
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import rlog_parse  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RLOGS = ROOT / "analysis-2020accord" / "rlogs"
ROUTES = {
    "r97": ("75604b0a432fdc89_00000097--489d7896b3", "STOCK 1x"),
    "r85": ("75604b0a432fdc89_00000085--cad692c3d3", "V100 4x"),
    "r96": ("75604b0a432fdc89_00000096--57f5183b32", "V102 6x"),
    "r9e": ("75604b0a432fdc89_0000009e--54bb0788af", "V103 6x"),
    "ra4": ("75604b0a432fdc89_000000a4--bdd0c0aa4e", "V104 6x"),
    "r95": ("75604b0a432fdc89_00000095--6d7c6deef5", "V101 8x"),
}
SR = 16000
# ---- PASS A
NFFT_A, HOP_A = 16384, 4096
# ---- PASS B
DEC_B = 32                     # -> 500 Hz
ENV_LP = 200.0                 # Hz, envelope anti-alias.  Nyquist after decimation is 250 Hz.
CARRIER = [(200, 600), (600, 1500), (1500, 4000), (4000, 7800),
           (300, 3000), (100, 7800)]


def segments(prefix):
    return sorted(RLOGS.glob("%s--*--rlog.zst" % prefix),
                  key=lambda p: int(p.name.split("--")[2]))


def _sos(lo, hi):
    ny = SR / 2
    return signal.butter(4, [lo / ny, min(hi / ny, 0.99)], btype="band", output="sos")


SOS = [_sos(a, b) for a, b in CARRIER]
LPB = signal.butter(6, ENV_LP / (SR / 2), btype="low", output="sos")
WINA = np.hanning(NFFT_A + 1)[:NFFT_A]
FA = np.fft.rfftfreq(NFFT_A, 1 / SR)
SELA = FA <= 100.5


def extract(tag):
    prefix, label = ROUTES[tag]
    segs = segments(prefix)
    cache = ROOT / "analysis-2020accord" / ("_cache_%s" % tag)
    t0 = float(np.load(cache / ("%s.npz" % tag), allow_pickle=True)["t0_mono"][0])
    print("  %s (%s): %d segments" % (tag, label, len(segs)), flush=True)

    TA, SA, TB, EB, SB = [], [], [], [], []
    n_splice = 0
    for si, p in enumerate(segs):
        blocks, bt = [], []
        for evt in rlog_parse.read_messages(str(p)):
            try:
                if evt.which() != "rawAudioData":
                    continue
            except Exception:
                continue
            blocks.append(np.frombuffer(bytes(evt.rawAudioData.data), dtype="<i2"))
            bt.append(evt.logMonoTime * 1e-9)
        if not blocks:
            continue
        x = np.concatenate(blocks).astype(np.float64)
        ts = np.concatenate([t + np.arange(len(b)) / SR for t, b in zip(bt, blocks)]) - t0
        n = len(blocks[0])
        bad = np.zeros(len(x), bool)
        off = 0
        for k in range(1, len(blocks)):
            off += len(blocks[k - 1])
            if abs(bt[k] - (bt[k - 1] + len(blocks[k - 1]) / SR)) > 0.5 * n / SR:
                bad[max(off - SR // 2, 0):off + SR // 2] = True
                n_splice += 1
        x = x - x.mean()

        # ---------------- PASS A
        for s in range(0, len(x) - NFFT_A + 1, HOP_A):
            seg = x[s:s + NFFT_A]
            X = np.fft.rfft((seg - seg.mean()) * WINA)
            SA.append(((X.conj() * X).real)[SELA])
            TA.append(ts[s:s + NFFT_A].mean())

        # ---------------- PASS B
        ev = np.empty((len(x[::DEC_B]), len(CARRIER)), np.float32)
        for j, sos in enumerate(SOS):
            y = signal.sosfiltfilt(sos, x)
            a = np.abs(signal.hilbert(y))
            ev[:, j] = signal.sosfiltfilt(LPB, a)[::DEC_B]
        TB.append(ts[::DEC_B])
        EB.append(ev)
        SB.append(bad[::DEC_B])
        if si % 4 == 0:
            print("     seg %2d done" % si, flush=True)

    ta = np.array(TA)
    sa = np.array(SA, np.float32)
    oa = np.argsort(ta)
    tb = np.concatenate(TB)
    eb = np.concatenate(EB)
    sb = np.concatenate(SB)
    ob = np.argsort(tb)
    np.savez_compressed(
        cache / ("%s_grind.npz" % tag),
        t_sp=ta[oa], sp=sa[oa], sp_f=FA[SELA],
        t_env=tb[ob], env=eb[ob], splice=sb[ob], env_f=np.array(CARRIER, float),
        meta=np.array([SR, NFFT_A, HOP_A, DEC_B, ENV_LP, SR / DEC_B], float))
    print("  %s: PASS A %d frames @ %.3f Hz (bin %.4f Hz) | PASS B %d frames @ %.0f Hz | "
          "%d splices, %.2f %% flagged"
          % (tag, len(ta), SR / HOP_A, FA[1] - FA[0], len(tb), SR / DEC_B,
             n_splice, 100 * sb.mean()), flush=True)
    return tag, len(ta), len(tb)


if __name__ == "__main__":
    tags = sys.argv[1:] or list(ROUTES)
    print("=" * 104)
    print("GRIND PASS -- sub-100 Hz spectra @ %.4f Hz bins + AM envelopes @ %.0f Hz"
          % (SR / NFFT_A, SR / DEC_B))
    print("  PASS A: NFFT %d, hop %d -> %.3f Hz frames, %.4f Hz bins, 0-100 Hz stored"
          % (NFFT_A, HOP_A, SR / HOP_A, SR / NFFT_A))
    print("  PASS B: carriers %s" % ", ".join("%g-%g" % c for c in CARRIER))
    print("          envelope LP %.0f Hz, decimate to %.0f Hz => modulation Nyquist %.0f Hz"
          % (ENV_LP, SR / DEC_B, SR / DEC_B / 2))
    print("=" * 104)
    for t in tags:
        extract(t)
