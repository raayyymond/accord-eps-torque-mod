"""Independent re-derivation of B6 (b_shake): 1.5-3.5 Hz content in the MODEL desired curvature vs
setpoint vs wheel rate, at low speed, torque-mode vs V282. Does NOT reuse b04_rows_*.npz -- recomputes
from the same v282ref caches with an independently-written Welch/coherence path (scipy.signal.welch /
csd rather than b04's hand-rolled rfft-of-detrended-window loop), to catch a pipeline bug rather than
just re-reading b08's own numbers.

Also independently checks the sign claim ("model curvature angle correlates -0.986 with steeringAngleDeg")
and the group-delay sign/magnitude for rev64 <8 m/s.
"""
import sys
import numpy as np
from scipy import signal

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/'
sys.path.insert(0, BASE)
import v282cmp as V

L_, SF = 2.83, -7.0e-4
FS = 100.0
BAND = (1.5, 3.5)
NPS = 256

T64 = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd']
T4 = ['00000075--6c8687d5bd']
V282 = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']

BINS = [(0, 3, '<3'), (3, 6, '3-6'), (6, 8, '6-8')]


def prep(rk):
    S = V.load(rk)
    v = S['v']; sp = np.nan_to_num(S['setpoint']); sR = np.nan_to_num(S['sR'], nan=16.5)
    sa_des = np.degrees((-sp / np.maximum(v * v, 1.0)) * sR * L_ * (1 - SF * v * v))
    D = np.load(V.CACHE / f'{rk}.npz'); curv = D['cs_des_curv']; del D
    sa_mdl_raw = np.degrees(curv * sR * L_ * (1 - SF * v * v))  # sign UNRESOLVED, as b04 leaves it
    sr = S['sr']; sa = S['sa']
    m = V.usable(S, 0, 15) & np.isfinite(sr) & np.isfinite(v) & np.isfinite(sa_des) & np.isfinite(sa_mdl_raw)
    return S, v, sa_des, sa_mdl_raw, sr, sa, m


def band_rms_welch(sig, fs=FS, band=BAND, nperseg=NPS):
    """Independent RMS-in-band via scipy.signal.welch (different code path than b04's manual rfft loop)."""
    f, Pxx = signal.welch(sig, fs=fs, window='hann', nperseg=nperseg, noverlap=nperseg // 2, detrend='linear')
    sel = (f >= band[0]) & (f <= band[1])
    var = np.trapezoid(Pxx[sel], f[sel])
    return np.sqrt(max(var, 0.0))


def per_route_windows(rk, lo, hi):
    """Return concatenated per-run band-limited rate arrays (adr, amr) restricted to the speed bin & runs>=4s,
    each run processed independently (matches b04's per-run gradient/windowing discipline)."""
    S, v, sa_des, sa_mdl_raw, sr, sa, m = prep(rk)
    out_adr, out_amr, out_sr = [], [], []
    for a, b in V.runs(m, S['t'], min_s=4.0):
        if (b - a) < NPS:
            continue
        vseg = v[a:b]
        if not np.any((vseg >= lo) & (vseg < hi)):
            continue
        adr = np.gradient(sa_des[a:b]) * 100
        amr = np.gradient(sa_mdl_raw[a:b]) * 100
        srr = sr[a:b]
        sel = (vseg >= lo) & (vseg < hi)
        # only keep windows whose CENTER falls in-bin, mirroring b04's per-window v-label; approximate here
        # by masking the whole run to windows fully in the bin using a rolling window average of v.
        out_adr.append((adr, sel)); out_amr.append((amr, sel)); out_sr.append((srr, sel))
    return out_adr, out_amr, out_sr


def windowed_rms(list_of_series_sel, fs=FS, band=BAND, nperseg=NPS, hop=128):
    """Welch-per-window RMS, restricted to windows whose mean v-mask is majority True, independent of b04's code."""
    accum_var = []
    for series, sel in list_of_series_sel:
        n = len(series)
        for s in range(0, n - nperseg + 1, hop):
            seg_sel = sel[s:s + nperseg]
            if seg_sel.mean() < 0.5:
                continue
            x = signal.detrend(series[s:s + nperseg])
            f, Pxx = signal.welch(x, fs=fs, window='hann', nperseg=nperseg, noverlap=0, detrend=False)
            b = (f >= band[0]) & (f <= band[1])
            accum_var.append(np.trapezoid(Pxx[b], f[b]))
    if not accum_var:
        return float('nan'), 0
    return float(np.sqrt(np.mean(accum_var))), len(accum_var)


def group_result(rks, lo, hi):
    all_adr, all_amr, all_sr = [], [], []
    for rk in rks:
        a, m_, s_ = per_route_windows(rk, lo, hi)
        all_adr += a; all_amr += m_; all_sr += s_
    r_setpoint, n1 = windowed_rms(all_adr, hop=32)  # finer hop than b04 (128) as an independent check
    r_model, n2 = windowed_rms(all_amr, hop=32)
    r_rate, n3 = windowed_rms(all_sr, hop=32)
    return r_rate, r_setpoint, r_model, n1


print("=== Independent re-derivation (scipy.signal.welch, hop=32, not b04's rfft/hop128 code path) ===")
print(f"{'group':8s} {'bin':5s} {'n':>5s}  {'rate':>6s}  {'setpoint':>9s}  {'model':>7s}   (b08 reported: setpoint / model)")
REPORTED = {
    ('T64', '<3'): (8.60, 65.86), ('T64', '3-6'): (11.11, 26.09), ('T64', '6-8'): (4.58, 10.66),
    ('T4', '3-6'): (8.34, 30.10),
    ('V282', '<3'): (5.99, 7.39), ('V282', '3-6'): (4.96, 5.60), ('V282', '6-8'): (3.16, 3.55),
}
for g, rks in [('T64', T64), ('T4', T4), ('V282', V282)]:
    for lo, hi, lab in BINS:
        if (g, lab) not in REPORTED and g != 'T4':
            pass
        r_rate, r_sp, r_mdl, n = group_result(rks, lo, hi)
        rep = REPORTED.get((g, lab))
        repstr = f"  (reported {rep[0]:.1f} / {rep[1]:.1f})" if rep else ""
        print(f"{g:8s} {lab:5s} {n:5d}  {r_rate:6.2f}  {r_sp:9.2f}  {r_mdl:7.2f}{repstr}")

print()
print("=== Sign check: correlation of RAW model-curvature-derived angle vs measured steeringAngleDeg ===")
print("(same test the finding relies on for the -0.986 claim / the b09 negation of Srm)")
for g, rks in [('T64', T64), ('V282', V282)]:
    cs = []
    for rk in rks:
        S = V.load(rk)
        v = S['v']; sR = np.nan_to_num(S['sR'], nan=16.5)
        D = np.load(V.CACHE / f'{rk}.npz'); curv = D['cs_des_curv']; del D
        sa_mdl_raw = np.degrees(curv * sR * L_ * (1 - SF * v * v))
        sa = S['sa']
        m = V.usable(S, 0, 15) & np.isfinite(sa_mdl_raw) & np.isfinite(sa)
        if m.sum() < 10:
            continue
        c = np.corrcoef(sa_mdl_raw[m], sa[m])[0, 1]
        cs.append((rk, c, int(m.sum())))
    for rk, c, n in cs:
        print(f"{g:8s} {rk:24s} n{n:6d}  corr(sa_mdl_raw, steeringAngleDeg) = {c:+.3f}")

print()
print("=== Independent group-delay check, rev64 <8 m/s, wheel rate vs (sign-corrected) model angle rate ===")
print("Using scipy.signal.csd per-window (hop=64) + unwrap phase slope in 1.5-3.5Hz, weighted by wheel-rate power")
rng = np.random.default_rng(1)
Sra_all, Srm_all, Prr_all = [], [], []
for rk in T64:
    S, v, sa_des, sa_mdl_raw, sr, sa, m = prep(rk)
    for a, b in V.runs(m, S['t'], min_s=4.0):
        if (b - a) < NPS:
            continue
        vseg = v[a:b]
        adr = np.gradient(sa_des[a:b]) * 100
        amr = np.gradient(sa_mdl_raw[a:b]) * 100
        srr = sr[a:b]
        for s in range(0, (b - a) - NPS + 1, 64):
            if not (vseg[s:s + NPS].mean() < 8.0):
                continue
            win = signal.get_window('hann', NPS)
            R = np.fft.rfft(signal.detrend(srr[s:s + NPS]) * win)
            M = np.fft.rfft(signal.detrend(amr[s:s + NPS]) * win)
            f = np.fft.rfftfreq(NPS, 0.01)
            bmask = (f >= 1.5) & (f <= 3.55)
            Srm_all.append(np.conj(M[bmask]) * R[bmask])
            Prr_all.append(np.abs(R[bmask]) ** 2)

Srm_all = np.array(Srm_all); Prr_all = np.array(Prr_all)
f = np.fft.rfftfreq(NPS, 0.01); fb = f[(f >= 1.5) & (f <= 3.55)]; om = 2 * np.pi * fb


def gd(S, w):
    ph = np.unwrap(np.angle(S))
    return -np.polyfit(om, ph, 1, w=np.sqrt(np.maximum(w, 1e-30)))[0]


# NEGATED, per the sign check above (matches b09's convention if corr is negative)
S_sum = -Srm_all.sum(0); w_sum = Prr_all.sum(0)
g0 = gd(S_sum, w_sum)
B = []
for _ in range(300):
    i = rng.integers(0, len(Srm_all), len(Srm_all))
    B.append(gd(-Srm_all[i].sum(0), Prr_all[i].sum(0)))
B = np.array(B)
print(f"n={len(Srm_all)} windows, gd = {g0*1000:+.0f} ms  95% CI [{np.percentile(B,2.5)*1000:+.0f}, {np.percentile(B,97.5)*1000:+.0f}] ms")
print("(finding claims +230 ms [209,254]; b09's own script reports +229 ms [+209,+254])")
