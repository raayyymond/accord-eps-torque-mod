r"""SECOND ACOUSTIC PASS -- BAND-LIMITED ANALYTIC (HILBERT) ENVELOPES at 125 Hz.

WHY A SECOND PASS.  The first pass (`decode/extract_audio.py`) stores 1024-point FFT band powers.  At
16 kHz that is a **15.625 Hz bin spacing**, and its `wide` band list asks for (5,15) and (21,28) Hz
-- neither of which contains a single FFT bin.

    bin centres:  0.000  15.625  31.250  46.875  62.500  78.125  93.750  109.375 ...
    5-15 Hz  -> 0 bins   (column is IDENTICALLY ZERO)
    21-28 Hz -> 0 bins   (column is IDENTICALLY ZERO)
    15-21, 28-40, 40-60 Hz -> ONE bin each; single-bin leakage, not a band power

⇒ **The 21-28 Hz column of `*_audio.npz` is all zeros and must never be used**, and the whole
sub-100 Hz `wide` set is at best three usable numbers.  That matters a lot, because 21-28 Hz is
where the wheel-rate work already has an almost perfect stock-vs-6x separation, and it is
therefore the ONLY available POSITIVE CONTROL for the microphone as an instrument.

WHAT THIS PASS PRODUCES INSTEAD -- the right tool for every remaining question:
    for each band:  4th-order Butterworth band-pass (zero-phase `sosfiltfilt`)
                    -> TRUE ANALYTIC ENVELOPE |hilbert(x)|
                    -> low-passed at 50 Hz and decimated to **125 Hz**
    125 Hz keeps a Nyquist of 62.5 Hz on the envelope, far above the operator's 6-12 /s ratchet.

    `env`    (n, nband) float32   the envelopes
    `env_f`  (nband, 2)           band edges
    `t`                           seconds on the cache's own `t0_mono` base
    `splice`  bool                True where a PCM discontinuity is within +-0.5 s -- these frames
                                  carry a filter transient and MUST be dropped by the analysis

🛑 SPLICES ARE MARKED, NOT HIDDEN.  Blocks are concatenated per segment; the first pass measured
17-89 small gaps per route.  Concatenating across a gap injects a step, which a band-pass turns
into a decaying ring that looks exactly like a burst.  Every such frame is flagged.

usage:  python decode/extract_audio_env.py            # all six routes
        python decode/extract_audio_env.py ra4 r97
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
DEC = 128                      # -> 125 Hz
FR = SR / DEC

# 🛑 THE FIRST BAND IS THE POSITIVE CONTROL.  21-28 Hz is where the wheel-rate instrument already
#    separates stock (burst duty 0.056) from 6x (0.93-0.95).  If the microphone cannot see THAT,
#    a null anywhere else on this channel is uninterpretable rather than informative.
BANDS = [(21, 28),            # POSITIVE CONTROL -- the known engaged-only mode
         (6, 13),             # the ratchet repetition rate itself, as a carrier
         (13, 21), (28, 40), (40, 70), (70, 100),
         (100, 300), (300, 800), (800, 2000), (2000, 5000), (5000, 7800),
         (100, 7800)]         # the whole audible range, one channel


def segments(prefix):
    return sorted(RLOGS.glob("%s--*--rlog.zst" % prefix),
                  key=lambda p: int(p.name.split("--")[2]))


def _sos(lo, hi):
    ny = SR / 2
    return signal.butter(4, [lo / ny, min(hi / ny, 0.99)], btype="band", output="sos")


SOS = [_sos(a, b) for a, b in BANDS]
LP = signal.butter(4, 50.0 / (SR / 2), btype="low", output="sos")


def extract(tag):
    prefix, label = ROUTES[tag]
    segs = segments(prefix)
    cache = ROOT / "analysis-2020accord" / ("_cache_%s" % tag)
    t0 = float(np.load(cache / ("%s.npz" % tag), allow_pickle=True)["t0_mono"][0])
    print("  %s (%s): %d segments" % (tag, label, len(segs)), flush=True)

    T, E, S = [], [], []
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
        n = len(blocks[0])
        # per-sample time, and the splice mask: a block whose start is off its predecessor's end
        ts = np.concatenate([t + np.arange(len(b)) / SR for t, b in zip(bt, blocks)]) - t0
        bad = np.zeros(len(x), bool)
        off = 0
        for k in range(1, len(blocks)):
            off += len(blocks[k - 1])
            if abs(bt[k] - (bt[k - 1] + len(blocks[k - 1]) / SR)) > 0.5 * n / SR:
                bad[max(off - SR // 2, 0):off + SR // 2] = True
                n_splice += 1
        x = x - x.mean()
        ev = np.empty((len(x[::DEC]), len(BANDS)), np.float32)
        for j, sos in enumerate(SOS):
            y = signal.sosfiltfilt(sos, x)
            a = np.abs(signal.hilbert(y))
            a = signal.sosfiltfilt(LP, a)
            ev[:, j] = a[::DEC]
        T.append(ts[::DEC])
        E.append(ev)
        S.append(bad[::DEC])
        if si % 4 == 0:
            print("     seg %2d done (%d frames)" % (si, sum(len(t) for t in T)), flush=True)

    t = np.concatenate(T)
    e = np.concatenate(E)
    s = np.concatenate(S)
    o = np.argsort(t)
    out = cache / ("%s_env.npz" % tag)
    np.savez_compressed(out, t=t[o], env=e[o], splice=s[o],
                        env_f=np.array(BANDS, float), fr=np.array([FR]))
    print("  %s: %d frames @ %.1f Hz, %.1f s, %d splices, %.2f %% frames flagged"
          % (tag, len(t), FR, len(t) / FR, n_splice, 100 * s.mean()), flush=True)
    return tag, len(t), n_splice, float(s.mean())


if __name__ == "__main__":
    tags = sys.argv[1:] or list(ROUTES)
    print("=" * 100)
    print("BAND-LIMITED ANALYTIC ENVELOPES @ %.0f Hz" % FR)
    print("  bands: " + ", ".join("%g-%g" % b for b in BANDS))
    print("=" * 100)
    rep = [extract(t) for t in tags]
    print()
    for r in rep:
        print("  %-5s frames %7d   splices %4d   flagged %.2f %%" % (r[0], r[1], r[2], 100 * r[3]))
