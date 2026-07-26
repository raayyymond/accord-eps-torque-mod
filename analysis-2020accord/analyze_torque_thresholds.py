"""Characterize STEERING COLUMN TORQUE (torsion-bar, msg399 STEER_TORQUE_SENSOR)
for normal openpilot-engaged driving vs gentle-EME onsets, on V31 2x-LKAS 2020 Accord.

Q1 normal-engaged stats, Q2 per-event before/during/after, Q3 separation.
"""
import io, sys
from pathlib import Path
from collections import Counter
import zstandard as zstd
import capnp

KIT = Path(__file__).resolve().parent.parent
CEREAL = KIT / "rlog-tools" / "cereal"
capnp.remove_import_hook()
log_capnp = capnp.load(str(CEREAL / "log.capnp"))

def be_bits(data, start, length):
    val = 0; bit = start
    for _ in range(length):
        byte, b_in = bit // 8, bit % 8
        val = (val << 1) | ((data[byte] >> b_in) & 1)
        bit = bit + 15 if b_in == 0 else bit - 1
    return val

def s16(u):
    return u - 0x10000 if u & 0x8000 else u

def dec399(d):
    if len(d) < 7: return None
    return {
        "status": be_bits(d, 39, 4),
        "active": be_bits(d, 35, 1),
        "tbar":   -s16(be_bits(d, 7, 16)),
    }

def events(path):
    raw = Path(path).read_bytes()
    data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(raw)).read()
    it = log_capnp.Event.read_multiple_bytes(data)
    while True:
        try: yield next(it)
        except StopIteration: break
        except capnp.KjException: break

def collect(path):
    """Return list of (ts, tbar, status, active, lat, veg) for every msg399 frame,
    carrying forward latest lat/veg from carControl/carState."""
    rows = []; t0 = None
    cur = {"lat": None, "veg": None}
    for evt in events(path):
        t = evt.logMonoTime
        if t0 is None: t0 = t
        ts = (t - t0)/1e9
        w = evt.which()
        if w == "can":
            for c in evt.can:
                if c.address == 399 and c.src == 1:
                    dd = dec399(bytes(c.dat))
                    if dd:
                        rows.append((ts, dd["tbar"], dd["status"], dd["active"],
                                     cur["lat"], cur["veg"]))
        elif w == "carState":
            cur["veg"] = evt.carState.vEgo
        elif w == "carControl":
            cur["lat"] = bool(evt.carControl.latActive)
    return rows

def find_onsets(rows):
    """STEER_STATUS rising into ==4. Return list of (idx, ts)."""
    onsets = []
    prev = None
    for i, r in enumerate(rows):
        st = r[2]
        if st == 4 and prev != 4:
            onsets.append((i, r[0]))
        prev = st
    return onsets

def pct(sorted_vals, p):
    if not sorted_vals: return float('nan')
    k = (len(sorted_vals)-1) * p/100.0
    lo = int(k); hi = min(lo+1, len(sorted_vals)-1)
    return sorted_vals[lo] + (sorted_vals[hi]-sorted_vals[lo])*(k-lo)

# ---- load both routes ----
R37 = r"C:\Users\dudei\Desktop\Projects\firmware-analysis-kit\analysis-2020accord\rlogs\75604b0a432fdc89_00000037--81d3101c48--9--rlog.zst"
R36 = r"C:\Users\dudei\Desktop\Projects\firmware-analysis-kit\analysis-2020accord\rlogs\75604b0a432fdc89_00000036--e85b8d0fc7--5--rlog.zst"

rows37 = collect(R37)
rows36 = collect(R36)

print("ROUTE37 frames:", len(rows37), " status hist:", Counter(r[2] for r in rows37))
print("ROUTE36 frames:", len(rows36), " status hist:", Counter(r[2] for r in rows36))
print("ROUTE37 onsets:", [round(t,3) for _,t in find_onsets(rows37)])
print("ROUTE36 onsets:", [round(t,3) for _,t in find_onsets(rows36)])

# Known onsets per the prompt
ONSETS = [
    ("R37", rows37, 543.469, "Event A RIGHT+bump"),
    ("R37", rows37, 554.469, ""),
    ("R36", rows36, 317.017, ""),
    ("R36", rows36, 325.537, "Event B LEFT+bump"),
    ("R36", rows36, 334.109, ""),
]

def nearest_onset_idx(rows, t_target):
    # nearest actual status==4 onset frame to t_target
    onsets = find_onsets(rows)
    best = min(onsets, key=lambda x: abs(x[1]-t_target))
    return best  # (idx, ts)

# ================= Q1 =================
print("\n" + "="*70)
print("Q1: NORMAL engaged-driving column torque (|tbar|), EME windows excluded")
print("="*70)

# build exclusion windows (±2.0 s) keyed by route using the ACTUAL onset ts
excl = {"R37": [], "R36": []}
for tag, rows, t, _ in ONSETS:
    _, real_ts = nearest_onset_idx(rows, t)
    excl[tag].append(real_ts)

def is_excluded(tag, ts):
    return any(abs(ts - o) <= 2.0 for o in excl[tag])

normal_abs = []
for tag, rows in (("R37", rows37), ("R36", rows36)):
    for ts, tbar, st, active, lat, veg in rows:
        engaged = (lat is True) or (active == 1)
        if not engaged: continue
        if is_excluded(tag, ts): continue
        normal_abs.append(abs(tbar))

normal_abs.sort()
n = len(normal_abs)
print(f"  n normal-engaged frames = {n}")
mean = sum(normal_abs)/n
median = pct(normal_abs, 50)
print(f"  mean   = {mean:8.1f}")
print(f"  median = {median:8.1f}")
print(f"  p90    = {pct(normal_abs,90):8.1f}")
print(f"  p95    = {pct(normal_abs,95):8.1f}")
print(f"  p99    = {pct(normal_abs,99):8.1f}")
print(f"  max    = {normal_abs[-1]:8.1f}")
print("  exceedance fractions:")
for thr in (320, 640, 960, 1600):
    frac = sum(1 for v in normal_abs if v > thr)/n
    print(f"    |tbar| > {thr:5d} : {frac*100:7.4f}%  ({sum(1 for v in normal_abs if v>thr)} frames)")

# ================= Q2 =================
print("\n" + "="*70)
print("Q2: Per-EME column torque BEFORE / DURING / AFTER")
print("="*70)
print(f"  {'event':22} {'route':5} {'onset_t':>8} {'base|t|':>8} {'peak150':>8} {'onset_t':>8} {'peak600after':>12}")
def window(rows, lo, hi):
    return [r for r in rows if lo <= r[0] <= hi]

for tag, rows, t_req, label in ONSETS:
    idx, ts = nearest_onset_idx(rows, t_req)
    onset_tbar = rows[idx][1]
    # BEFORE: ~250ms steady prior (t-0.30 .. t-0.05) baseline = median |tbar|
    before = [abs(r[1]) for r in window(rows, ts-0.30, ts-0.05)]
    before.sort()
    base = pct(before, 50) if before else float('nan')
    # DURING: peak |tbar| in 150ms leading into onset (t-0.15 .. t)
    during = [abs(r[1]) for r in window(rows, ts-0.15, ts)]
    peak_during = max(during) if during else float('nan')
    # AFTER: peak |tbar| in 600ms after onset (t .. t+0.60)
    after = [abs(r[1]) for r in window(rows, ts, ts+0.60)]
    peak_after = max(after) if after else float('nan')
    name = label if label else "(secondary)"
    print(f"  {name:22} {tag:5} {ts:8.3f} {base:8.0f} {peak_during:8.0f} {onset_tbar:8.0f} {peak_after:12.0f}")
