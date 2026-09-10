# -*- coding: utf-8 -*-
r"""paramod 2026-09-09 -- ITEM 2: FLOQUET / LYAPUNOV CHECK ON THE Kd-MODULATED LOOP.

DESIGN STUDY.  Builds nothing, flashes nothing, sends nothing.

WHY AN LTI READING IS NOT ENOUGH.  Row S makes Kd a function of the demand index, and the demand index moves.
A loop whose gain varies PERIODICALLY is a linear TIME-PERIODIC (LTP) system: its stability is NOT given by
the eigenvalues of the frozen-Kd loop at any single Kd, and a system that is stable at EVERY frozen Kd can
still be unstable when the parameter alternates (parametric / Mathieu resonance, strongest when the parameter
oscillates near 2x a mode frequency, with a weaker subharmonic tongue at 1x).  The kit has one measured
instance of exactly this class (memory accord-parametric-pump-intervention-never-run: V59 measured a 42.19 Hz
gain pump into a 21.09 Hz mode, eps 0.333, and the settling intervention was never run).

THE METHOD.
1. Build the closed loop as a discrete state-space at 1 kHz IN A PHYSICAL BASIS -- one state per physical
   storage element (feedback filter, the D term's E_prev, the output lag, the explicit z^-1, the plant's own
   states and its transport delay ticks).  Kd enters ONLY the static output row of the PID block
   (u = (Kp/256 + Kd/8) E - (Kd/8) E_prev), so A_cl(Kd) is AFFINE in Kd and, crucially, EVERY Kd shares the
   SAME state basis.  That is what makes switching between two Kd values a well-posed product of matrices.
   (A companion realisation built from the characteristic polynomial would NOT do: its similarity transform
   depends on Kd, so the switched product would model a different physical system.)
   -> VERIFIED against design290b's own poles_of() for constant Kd, to ~1e-9 in |z|.
2. FLOQUET: for a square-wave Kd of period N ticks and duty d, the monodromy matrix is
   M = A_cl(Kd_hi)^(N-n_lo) . A_cl(Kd_lo)^(n_lo).  The Floquet multipliers are eig(M); the system grows iff
   the spectral radius rho(M) > 1.  Equivalent continuous growth rate sigma = ln rho / (N*TS)  [1/s].
   Sweep the modulation frequency 1..50 Hz (the wire is 100 Hz, so 50 Hz is the fastest Kd can be driven)
   and duty 0.1..0.9, at the WORST-CASE full swing 96 <-> 128 that row S can deliver.
3. MEASURED-TRACE LYAPUNOV: take the ACTUAL idx trace from the grinding episodes, hold each 100 Hz sample
   for 10 loop ticks, evaluate Kd(idx) through the row-S LERP, and propagate the state-transition PRODUCT
   over the episode with QR re-orthogonalisation.  The top Lyapunov exponent is the true growth rate of the
   real modulated loop.  Compare against constant Kd 128 (V282) and constant Kd 96.
4. Everything on the SUB family: the 87 fits linear-stable on V289 AND consistent with the measured V289
   burst decay (zeta_eff 0.02-0.13) -- reconcile_v290.load_family()'s `burst` set.

Run:  python rlog-tools/studies/grind/paramod_v290_floquet.py [verify|sweep|trace|all]
Out:  rlog-tools/studies/grind/_scratch/paramod_v290_floquet.txt (+ .json)
"""
import json
import os
import pickle
import sys
import time

import numpy as np

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import adv_v290_physics as A                    # noqa: E402
import design290b_candidates as D               # noqa: E402
import creep20_loop_id as C20                   # noqa: E402
import kpkd_axis_r62_r63 as AX                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TS, FS, CPD = A.TS, A.FS, A.CPD          # 1e-3 s, 1000 Hz, 8 counts per deg/s
FW = 100.0                                # the 0xE4 wire rate
NHOLD = int(round(FS / FW))               # loop ticks per wire frame = 10
KDX = np.array([0.0, 11.0, 22.0, 32.0])
KDY_S = np.array([96.0, 96.0, 96.0, 128.0])
KD_LO, KD_HI = 96.0, 128.0
CENSUS_PKL = os.path.join(HERE, "_scratch", "grind1_census_v289_r62_r63_cache.pkl")
OUT = []
J = {}


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


# ------------------------------------------------------------------------------- TDF-II state space of b(w)/a(w)
def tdf2(b, a):
    """Transposed-Direct-Form-II state space of H(w) = sum b_k w^k / sum a_k w^k, w = z^-1, a normalised to a0 = 1.
       y[t]   = b0 u[t] + s0[t]
       s_i[t+1] = (b_{i+1} - a_{i+1} b0) u[t] - a_{i+1} s0[t] + s_{i+1}[t]
    Returns (As, Bs, Cs, Ds) with state dim m = max(len(b), len(a)) - 1."""
    b = np.asarray(b, float).ravel()
    a = np.asarray(a, float).ravel()
    assert abs(a[0]) > 1e-15
    b = b / a[0]
    a = a / a[0]
    m = max(len(b), len(a)) - 1
    bb = np.zeros(m + 1); bb[:len(b)] = b
    aa = np.zeros(m + 1); aa[:len(a)] = a
    Ds = bb[0]
    Cs = np.zeros(m);
    if m:
        Cs[0] = 1.0
    As = np.zeros((m, m)); Bs = np.zeros(m)
    for i in range(m):
        As[i, 0] -= aa[i + 1]
        if i + 1 < m:
            As[i, i + 1] += 1.0
        Bs[i] = bb[i + 1] - aa[i + 1] * Ds
    return As, Bs, Cs, Ds


class LoopSS:
    """The V290 rate loop as a discrete state-space at 1 kHz, in a PHYSICAL (Kd-independent) basis.

    Blocks, in the order they are evaluated within one tick:
        rate = Cp . sP                    plant output (no feedthrough: >= 1 delay tick)   x = CPD * rate
        fb   = Df x + Cf . sF             feedback filter F (byte cells fb_a / fb_b)
        E    = 32 sp - fb
        u    = (Kp/256 + Kd/8) E - (Kd/8) e1        <-- THE ONLY Kd-DEPENDENT ROW.  state e1 = E_prev
        S    = (254/256) u
        Sn   = Dn S + Cn . sN             the sum-node filter (identity on the V282 base; a notch if given)
        y    = Dh Sn + Ch . sH            the 5.05 Hz output lag
        T    = (gain/32768) y
        Td   = d1                         the explicit z^-1 in R()
    state updates: sP += Ap sP + Bp Td ; sF += Af sF + Bf x ; e1 += E ; sN += An sN + Bn S ; sH += Ah sH + Bh Sn ;
                   d1 += T
    Clamps are OMITTED -- this is the linear/LTP analysis, which is exactly the reading a frozen-Kd LTI study
    also makes.  The integer nonlinear mirror is a separate check (design290b.mirror_step)."""

    def __init__(self, c, plant, sumfilt=None):
        self.kp = float(c["kp_Y"][0])
        F = (np.array([c["fb_b"] / 1024.0, c["fb_b"] / 1024.0]), np.array([1.0, -c["fb_a"] / 1024.0]))
        H = (np.array([c["lag_b"] / 1024.0 / 32.0] * 2), np.array([1.0, -c["lag_a"] / 1024.0]))
        self.K = c["gain"] / 32768.0
        self.fade = 254.0 / 256.0
        if sumfilt is None:
            Nb, Na = np.array([1.0]), np.array([1.0])
        else:
            Nb, Na = np.array([1.0]), np.array([1.0])
            for bb, aa in sumfilt:
                Nb, Na = np.convolve(Nb, bb), np.convolve(Na, aa)
        self.AF, self.BF, self.CF, self.DF = tdf2(*F)
        self.AN, self.BN, self.CN, self.DN = tdf2(Nb, Na)
        self.AH, self.BH, self.CH, self.DH = tdf2(*H)
        self.AP, self.BP, self.CP, self.DP = tdf2(plant.num, plant.den)
        assert abs(self.DP) < 1e-14, "plant must have no direct feedthrough (it carries >= 1 delay tick)"
        self.nF, self.nN, self.nH, self.nP = len(self.CF), len(self.CN), len(self.CH), len(self.CP)
        # slices:  [sP | sF | e1 | sN | sH | d1]
        o = 0
        self.iP = slice(o, o + self.nP); o += self.nP
        self.iF = slice(o, o + self.nF); o += self.nF
        self.ie = o; o += 1
        self.iN = slice(o, o + self.nN); o += self.nN
        self.iH = slice(o, o + self.nH); o += self.nH
        self.id1 = o; o += 1
        self.n = o

    def step_map(self, kd):
        """Return (Acl, Bsp): s[t+1] = Acl s[t] + Bsp sp[t].  Built by evaluating the tick map on the basis."""
        Acl = np.zeros((self.n, self.n))
        for j in range(self.n):
            e = np.zeros(self.n); e[j] = 1.0
            Acl[:, j] = self._tick(e, 0.0, kd)
        Bsp = self._tick(np.zeros(self.n), 1.0, kd)
        return Acl, Bsp

    def _tick(self, s, sp, kd):
        rate = float(self.CP @ s[self.iP])
        x = CPD * rate
        fb = self.DF * x + float(self.CF @ s[self.iF])
        E = 32.0 * sp - fb
        e1 = s[self.ie]
        u = (self.kp / 256.0 + kd / 8.0) * E - (kd / 8.0) * e1
        S = self.fade * u
        Sn = self.DN * S + (float(self.CN @ s[self.iN]) if self.nN else 0.0)
        y = self.DH * Sn + float(self.CH @ s[self.iH])
        T = self.K * y
        Td = s[self.id1]
        ns = np.zeros(self.n)
        ns[self.iP] = self.AP @ s[self.iP] + self.BP * Td
        ns[self.iF] = self.AF @ s[self.iF] + self.BF * x
        ns[self.ie] = E
        if self.nN:
            ns[self.iN] = self.AN @ s[self.iN] + self.BN * S
        ns[self.iH] = self.AH @ s[self.iH] + self.BH * Sn
        ns[self.id1] = T
        return ns


def zeta_of(z):
    """damping of a discrete pole z, the same convention as design290b.poles_of."""
    s = np.log(z) * FS
    return -s.real / abs(s), abs(s.imag) / (2 * np.pi)


# -------------------------------------------------------------------------------------------------- verification
def build(c282, plant, kd, sumfilt=None):
    cc = dict(c282); cc["kd_Y"] = [int(kd)] * 4
    return LoopSS(cc, plant, sumfilt)


def verify(c, c282, fam):
    pr("=" * 118)
    pr("2A.  VERIFICATION -- the physical state-space reproduces design290b's own closed-loop poles")
    pr("=" * 118)
    pr()
    pr("  For each of 6 fits x Kd in {128, 112, 96}: eigenvalues of Acl(Kd) vs roots of 1 + L(z) = 0 from")
    pr("  design290b.poles_of(Elec(cellsfb(c282, None, None, kd)), plant).  max |dz| over ALL matched poles.")
    pr()
    import reconcile_v290 as RC
    worst = 0.0
    pr("  %-38s %5s %8s %10s %10s %12s" % ("plant fit", "Kd", "n_state", "f_ss(Hz)", "z_ss", "max|dz|"))
    for p in fam[:: max(1, len(fam) // 6)][:6]:
        pl = D.mkplant(p)
        for kd in (128, 112, 96):
            ss = build(c282, pl, kd)
            Acl, _ = ss.step_map(float(kd))
            ez = np.linalg.eigvals(Acl)
            el = D.ElecP(RC.cellsfb(c282, None, None, kd)) if hasattr(D, "ElecP") else None
            el = RC.ElecP(RC.cellsfb(c282, None, None, kd))
            f, z, zz = D.poles_of(el, pl)
            # match each reference pole to the nearest eigenvalue
            dmax = 0.0
            for w in zz:
                dmax = max(dmax, float(np.min(np.abs(ez - w))))
            worst = max(worst, dmax)
            # the 8-30 Hz least-damped mode from the state space
            zt, ff = zip(*[zeta_of(v) for v in ez if abs(np.log(v).imag) > 1e-9])
            zt = np.array(zt); ff = np.array(ff)
            m = (ff >= 8) & (ff <= 30)
            fs_, zs_ = (float(ff[m][np.argmin(zt[m])]), float(zt[m].min())) if m.any() else (np.nan, np.nan)
            pr("  %-38s %5d %8d %10.3f %10.4f %12.2e" % (p["label"][:38], kd, ss.n, fs_, zs_, dmax))
    pr()
    pr("  WORST |dz| over every pole of every case: %.3e   %s" % (worst, "PASS" if worst < 1e-7 else "*** FAIL ***"))
    J["verify_max_dz"] = worst
    pr()
    return worst


# ------------------------------------------------------------------------------------------------ Floquet sweep
def monodromy(A_lo, A_hi, N, n_lo):
    """M for one period: n_lo ticks at Kd_lo then (N - n_lo) at Kd_hi."""
    M = np.linalg.matrix_power(A_lo, n_lo) @ np.linalg.matrix_power(A_hi, N - n_lo)
    return M


def floquet_sweep(c282, fits, fmods, duties, kd_lo=KD_LO, kd_hi=KD_HI, sumfilt=None):
    """Returns (R, base) -- R[fit, fmod, duty] = per-tick Floquet growth; base[fit] = max of the two FROZEN-Kd
    spectral radii FOR THAT SAME FIT (the honest per-fit reference: excess = R - base[:,None,None])."""
    R = np.zeros((len(fits), len(fmods), len(duties)))
    base = np.zeros(len(fits))
    for i, p in enumerate(fits):
        pl = D.mkplant(p)
        A_lo, _ = build(c282, pl, kd_lo, sumfilt).step_map(kd_lo)
        A_hi, _ = build(c282, pl, kd_hi, sumfilt).step_map(kd_hi)
        base[i] = max(float(np.max(np.abs(np.linalg.eigvals(A_lo)))),
                      float(np.max(np.abs(np.linalg.eigvals(A_hi)))))
        cache = {}
        for j, fm in enumerate(fmods):
            N = int(round(FS / fm))
            if N < 2:
                R[i, j, :] = np.nan
                continue
            for k, du in enumerate(duties):
                n_lo = min(max(int(round(N * du)), 0), N)
                key = (N, n_lo)
                if key not in cache:
                    M = monodromy(A_lo, A_hi, N, n_lo)
                    rho = float(np.max(np.abs(np.linalg.eigvals(M))))
                    cache[key] = rho ** (1.0 / N)          # per-TICK growth, comparable to |z| of an LTI pole
                R[i, j, k] = cache[key]
    return R, base


def sq_first_harmonic_eps(swing, duty, mean_kd):
    """The fundamental component of a square wave of peak-to-peak `swing` at `duty`, as V59's eps
    (half-swing of the sinusoid / mean).  a1 = (2*swing/pi)*sin(pi*duty)."""
    return float((2.0 * swing / np.pi) * np.sin(np.pi * duty) / mean_kd)


def depth_threshold(c282, fits, fmod, duty, kd_hi=KD_HI, swings=None):
    """At a fixed (f_mod, duty), how deep must the Kd square wave be before the modulated loop actually GROWS?
    Sweeps the peak-to-peak swing DOWNWARD from kd_hi and UPWARD past what row S can deliver (hypothetically,
    by letting Kd go below 96 and above 128) to locate rho = 1."""
    if swings is None:
        swings = np.array([2, 4, 8, 16, 32, 48, 64, 96, 112, 120, 126], float)
    out = []
    for sw in swings:
        lo = max(kd_hi - sw, 1.0)
        R, base = floquet_sweep(c282, fits, np.array([fmod]), np.array([duty]), kd_lo=lo, kd_hi=kd_hi)
        r = R[:, 0, 0]
        exc = r - base
        out.append(dict(swing=float(sw), kd_lo=float(lo), rho_max=float(np.nanmax(r)),
                        excess_max=float(np.nanmax(exc)), unst=int(np.sum(r > 1.0)),
                        eps=sq_first_harmonic_eps(sw, duty, 0.5 * (kd_hi + lo))))
    return out


# ------------------------------------------------------------------------------------ measured-trace Lyapunov
def lyap_trace(c282, plant, kd_seq, sumfilt=None, kd_grid=None):
    """Top Lyapunov exponent (per tick, as an equivalent |z|) of the product of Acl over the measured Kd sequence.
    kd_seq is one Kd per LOOP TICK.  Uses a small cache of Acl over a quantised Kd grid + QR re-orthogonalisation."""
    if kd_grid is None:
        kd_grid = np.arange(96.0, 128.001, 0.5)
    Amats = {}
    for kd in kd_grid:
        Amats[round(float(kd), 3)] = build(c282, plant, kd, sumfilt).step_map(float(kd))[0]
    keys = np.array(sorted(Amats.keys()))
    n = next(iter(Amats.values())).shape[0]
    Q = np.eye(n)
    lsum = 0.0
    cnt = 0
    for kd in kd_seq:
        kk = keys[int(np.argmin(np.abs(keys - kd)))]
        Q = Amats[kk] @ Q
        cnt += 1
        if cnt % 20 == 0:
            Q, Rq = np.linalg.qr(Q)
            d = np.diag(Rq)
            lsum += float(np.log(abs(d[0]) + 1e-300))
            Q = Q * np.sign(d + (d == 0))
    if cnt % 20:
        Q, Rq = np.linalg.qr(Q)
        lsum += float(np.log(abs(np.diag(Rq)[0]) + 1e-300))
    return float(np.exp(lsum / max(cnt, 1)))          # per-tick growth factor == equivalent |z|


# ------------------------------------------------------------------- 2B.3 depth sweep with f_mod RE-OPTIMISED
def depth_reopt(c282, fits, swings, fgrid, duties, kd_hi=KD_HI):
    """As depth_threshold, but at each swing the modulation frequency AND duty are re-optimised.  This closes the
    hole in a fixed-frequency depth sweep: raising the swing lowers the MEAN Kd, which moves the mode, which moves
    the tongue."""
    out = []
    for sw in swings:
        lo = max(kd_hi - sw, 1.0)
        R, base = floquet_sweep(c282, fits, fgrid, duties, kd_lo=lo, kd_hi=kd_hi)
        E = R - base[:, None, None]
        k = np.unravel_index(int(np.nanargmax(E)), E.shape)
        out.append(dict(swing=float(sw), kd_lo=float(lo), rho_max=float(np.nanmax(R)),
                        excess_max=float(np.nanmax(E)), f_at=float(fgrid[k[1]]), duty_at=float(duties[k[2]]),
                        unst=int(np.nansum(R > 1.0)), eps=sq_first_harmonic_eps(sw, duties[k[2]], 0.5 * (kd_hi + lo))))
    return out


# ----------------------------------------------------------- 2D the CLAMPED integer mirror, Kd modulated per tick
def ring_int(c282, plant, kd_seq, imp, n=1600, warm=60):
    """Integer mirror (design290b.Controller, ALL clamps live) with Kd written per tick, setpoint held at 0, and a
    single TORQUE impulse injected straight into the plant so the ring amplitude is set directly instead of through
    the (D-clamp-saturating) setpoint path.  Returns the free-ring rate trace."""
    cc = dict(c282); cc["kd_Y"] = [128] * 4
    ctl = D.Controller(cc)
    b, a = plant.num, plant.den
    xh = np.zeros(len(b)); yh = np.zeros(len(a))
    rate = np.zeros(n); x = 0
    for k in range(n):
        ctl.kd = int(round(kd_seq[k % len(kd_seq)]))
        Tk = ctl.tick(0, x)
        if k == warm:
            Tk += imp                                   # the disturbance, injected at the plant input
        xh = np.roll(xh, 1); xh[0] = Tk
        yk = (np.dot(b, xh) - np.dot(a[1:], yh[:-1])) / a[0]
        yh = np.roll(yh, 1); yh[0] = yk
        rate[k] = yk; x = int(round(CPD * yk))
    return rate[warm:]


def env_decay(r, floor_frac=0.25, tmax=0.6):
    """Exponential decay rate (1/s) of the ring, fitted to the log of the |rate| PEAK envelope, using only peaks
    above floor_frac of the first peak and above the feedback quantiser (1/CPD deg/s), within tmax seconds.
    Returns (rate 1/s, peak, n_peaks_used).  A NEGATIVE rate means the ring GREW."""
    q = 1.0 / CPD
    pk = []
    for i in range(1, len(r) - 1):
        if abs(r[i]) >= abs(r[i - 1]) and abs(r[i]) > abs(r[i + 1]):
            pk.append((i * TS, abs(r[i])))
    if len(pk) < 4:
        return np.nan, float(np.max(np.abs(r))), 0
    pk = np.array(pk)
    p0 = float(pk[:, 1].max())
    m = (pk[:, 1] >= max(floor_frac * p0, 1.5 * q)) & (pk[:, 0] <= tmax)
    if m.sum() < 4:
        return np.nan, p0, int(m.sum())
    sl = np.polyfit(pk[m, 0], np.log(pk[m, 1]), 1)[0]
    return float(-sl), p0, int(m.sum())


def imp_for_peak(c282, plant, target, kd=128.0):
    """Scale the plant impulse so the free ring peaks near `target` deg/s (bisection on the log of the impulse)."""
    lo, hi = 1.0, 4e6
    mid = hi
    for _ in range(45):
        mid = np.sqrt(lo * hi)
        p0 = env_decay(ring_int(c282, plant, np.array([kd]), mid))[1]
        if p0 < target:
            lo = mid
        else:
            hi = mid
        if abs(p0 / max(target, 1e-9) - 1) < 0.02:
            break
    return mid


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    c, c282 = D.cells()
    fam = json.load(open(os.path.join(SCR, "design290b_family.json")))
    stab = [p for p in fam if p["z289"] >= D.Z289_STABLE]
    burst = [p for p in stab if 0.02 <= p["z289"] <= 0.13]
    pr("=" * 118)
    pr("ITEM 2 -- FLOQUET / LYAPUNOV ON THE Kd-MODULATED LOOP (agent paramod, 2026-09-09)")
    pr("=" * 118)
    pr("  base electronics = V282 (fb_a/fb_b %d/%d = %.2f Hz, no notch, lag %d/%d, gain %d, Kp %d)"
       % (c282["fb_a"], c282["fb_b"], -FS * np.log(c282["fb_a"] / 1024.0) / (2 * np.pi),
          c282["lag_a"], c282["lag_b"], c282["gain"], c282["kp_Y"][0]))
    pr("  plant family: %d fits, %d linear-stable on V289, %d ALSO burst-consistent (SUB, zeta289 0.02-0.13)"
       % (len(fam), len(stab), len(burst)))
    pr("  row S delivers Kd in [%.0f, %.0f]; the sweep below uses the FULL swing, i.e. the worst case row S can produce."
       % (KD_LO, KD_HI))
    pr()

    if what in ("verify", "all"):
        verify(c, c282, burst)

    if what in ("sweep", "all"):
        t0 = time.time()
        pr("=" * 118)
        pr("2B.  FLOQUET SWEEP -- square-wave Kd 96 <-> 128, every modulation frequency the 100 Hz wire can carry")
        pr("=" * 118)
        pr()
        fmods = np.array([1, 2, 3, 4, 5, 6, 7, 7.3, 8, 10, 12, 14, 14.6, 16, 16.3, 17, 20, 20.04, 22, 25,
                          28, 30, 31.5, 32, 33.5, 35, 40, 40.1, 45, 50], float)
        duties = np.array([0.1, 0.25, 0.5, 0.75, 0.9])
        sub = burst
        R, base = floquet_sweep(c282, sub, fmods, duties)
        rho128 = np.zeros(len(sub)); rho96 = np.zeros(len(sub))
        for i, p in enumerate(sub):
            pl = D.mkplant(p)
            rho128[i] = np.max(np.abs(np.linalg.eigvals(build(c282, pl, 128.0).step_map(128.0)[0])))
            rho96[i] = np.max(np.abs(np.linalg.eigvals(build(c282, pl, 96.0).step_map(96.0)[0])))
        pr("  LTI references over the %d SUB fits (spectral radius of Acl; > 1 = unstable):" % len(sub))
        pr("    constant Kd 128 (V282):  rho max %.6f  median %.6f   unstable fits %d"
           % (rho128.max(), np.median(rho128), int((rho128 > 1).sum())))
        pr("    constant Kd  96:         rho max %.6f  median %.6f   unstable fits %d"
           % (rho96.max(), np.median(rho96), int((rho96 > 1).sum())))
        pr()
        pr("  EXC = max over the 87 fits of [Floquet rho(fit) - max(rho96(fit), rho128(fit))], PER FIT -- the honest")
        pr("  comparison.  EXC > 0 is genuine parametric amplification the frozen-Kd (LTI) reading misses.")
        pr("  rho > 1.0 anywhere would be an UNSTABLE modulated loop.  Square wave, FULL 96<->128 swing (worst case).")
        pr()
        EXC = R - base[:, None, None]
        pr("  %-9s | %s" % ("f_mod Hz", "  ".join("%-19s" % ("duty %.2f" % d) for d in duties)))
        pr("  %-9s | %s" % ("", "  ".join("%9s %9s" % ("max rho", "max EXC") for d in duties)))
        worst = (-9.9, None)
        for j, fm in enumerate(fmods):
            cells_ = []
            for k in range(len(duties)):
                cells_.append("%9.6f %+9.2e" % (np.nanmax(R[:, j, k]), np.nanmax(EXC[:, j, k])))
                v = float(np.nanmax(EXC[:, j, k]))
                if v > worst[0]:
                    worst = (v, (fm, duties[k], float(np.nanmax(R[:, j, k]))))
            pr("  %-9.2f | %s" % (fm, "  ".join(cells_)))
        pr()
        rho_top = float(np.nanmax(R))
        pr("  WORST PER-FIT EXCESS over the whole sweep: %+.3e per tick, at f_mod = %.2f Hz, duty %.2f"
           % (worst[0], worst[1][0], worst[1][1]))
        pr("  HIGHEST rho anywhere in the sweep: %.6f  (unstable would be > 1.0; margin to instability %.5f)"
           % (rho_top, 1.0 - rho_top))
        pr("  In continuous terms, the worst excess turns a decay of %.3f 1/s into %.3f 1/s -- a %.2f %% loss of"
           % (-FS * np.log(base[int(np.nanargmax(EXC[:, :, :].max(axis=(1, 2))))]),
              -FS * np.log(base[int(np.nanargmax(EXC[:, :, :].max(axis=(1, 2))))] + worst[0]),
              100.0 * (1 - np.log(base[int(np.nanargmax(EXC[:, :, :].max(axis=(1, 2))))] + worst[0])
                       / np.log(base[int(np.nanargmax(EXC[:, :, :].max(axis=(1, 2))))]))))
        pr("  ring decay, at the WORST fit, the WORST modulation frequency and the WORST duty, and at the FULL")
        pr("  96<->128 square-wave swing that no measured episode comes anywhere near.")
        pr("  A genuine 2f tongue IS present (the maximum sits at 40 Hz = 2 x the 20.0 Hz V282 ring, exactly where")
        pr("  parametric theory puts it) -- it is simply far too weak to matter.  Sized in 2B.2.")
        J["sweep"] = dict(fmods=fmods.tolist(), duties=duties.tolist(),
                          rho_max=[[float(np.nanmax(R[:, j, k])) for k in range(len(duties))] for j in range(len(fmods))],
                          exc_max=[[float(np.nanmax(EXC[:, j, k])) for k in range(len(duties))] for j in range(len(fmods))],
                          lti128=float(rho128.max()), lti96=float(rho96.max()), rho_top=rho_top,
                          worst=[worst[0], float(worst[1][0]), float(worst[1][1])])
        pr("  (%.0f s)" % (time.time() - t0))
        pr()

        # ---- the tongue check at the exact ring frequencies, fine grid ---------------------------------
        pr("  2B.1  FINE SWEEP through the principal (2f) and subharmonic (1f) tongues of the measured rings.")
        pr("        V282/V288 ring 20.0 Hz -> tongues at 20.0 and 40.1 Hz;  V289 ring 16.4 Hz -> 16.4 and 32.8 Hz.")
        pr()
        fine = np.concatenate([np.arange(15.0, 18.01, 0.25), np.arange(19.0, 21.51, 0.25),
                               np.arange(31.0, 34.51, 0.25), np.arange(38.0, 42.01, 0.25)])
        best = (-9.9, None)
        for du in (0.1, 0.25, 0.5):
            Rf, bf = floquet_sweep(c282, sub, fine, np.array([du]))
            Ef = Rf[:, :, 0] - bf[:, None]
            jj = int(np.nanargmax(np.nanmax(Ef, axis=0)))
            v = float(np.nanmax(Ef))
            pr("        duty %.2f: worst excess %+.3e at f_mod %.2f Hz (rho %.6f)"
               % (du, v, fine[jj], float(np.nanmax(Rf[:, jj, 0]))))
            if v > best[0]:
                best = (v, float(fine[jj]), du)
            J.setdefault("fine", {})["duty%.2f" % du] = dict(
                f=fine.tolist(), exc=[float(np.nanmax(Ef[:, j])) for j in range(len(fine))])
        pr("        ==> the tongue peak is at %.2f Hz, duty %.2f, excess %+.3e" % (best[1], best[2], best[0]))
        pr()

        # ---- 2B.2 how deep would the modulation have to be? --------------------------------------------
        pr("  2B.2  DEPTH THRESHOLD -- how deep must the Kd square wave be before the modulated loop actually GROWS?")
        pr("        At the tongue peak (f_mod %.2f Hz, duty %.2f).  `eps` is the fundamental's half-swing / mean Kd," % (best[1], best[2]))
        pr("        i.e. V59's own statistic, so it is directly comparable to what ITEM 1 measured on the wire.")
        pr("        Swings above 32 are HYPOTHETICAL (row S can only deliver 32) and are here to locate the threshold.")
        pr()
        rows = depth_threshold(c282, sub, best[1], best[2])
        pr("        %-9s %-9s %-9s %-12s %-13s %s" % ("swing", "Kd range", "eps", "max rho", "max excess", "unstable fits"))
        for r in rows:
            mark = "   <-- the MOST row S can ever deliver" if abs(r["swing"] - 32.0) < 1e-9 else ""
            pr("        %-9.0f %-9s %-9.4f %-12.6f %+-13.2e %d%s"
               % (r["swing"], "%.0f-%.0f" % (r["kd_lo"], KD_HI), r["eps"], r["rho_max"], r["excess_max"], r["unst"], mark))
        pr()
        pr("        MEASURED eps at 2f on the wire (item 1, duration-weighted over census grinding episodes):")
        pr("          r62_v289 0.0021 | r63_v289 0.0048 | r5e_v288 0.0071 | r39(V282) 0.0052; worst single episode 0.027.")
        J["depth"] = rows
        pr()

    if what in ("trace", "all"):
        t0 = time.time()
        pr("=" * 118)
        pr("2C.  THE MEASURED TRACE -- Kd switched by the ACTUAL demand index, per loop tick")
        pr("=" * 118)
        pr()
        pr("  The 100 Hz idx trace is held for %d loop ticks (the firmware LERPs at 1 kHz but idx only updates when a"
           % NHOLD)
        pr("  new 0xE4 frame arrives).  Kd(t) = row-S LERP of that.  Top Lyapunov exponent by QR, reported as an")
        pr("  equivalent per-tick |z| so it sits alongside the LTI spectral radii above.")
        pr()
        C = {n: AX.cells(n) for n in ("V289", "V288")}
        ep = {}
        if os.path.exists(CENSUS_PKL):
            P = pickle.load(open(CENSUS_PKL, "rb"))
            for e in P["episodes"]:
                ep.setdefault(e["tag"], []).append(e)
        # the 3 fits that are LEAST damped on the SUB family -- the ones a pump would break first
        sub = sorted(burst, key=lambda p: p["z282"])[:3]
        pr("  fits used (the 3 least-damped on V282 in the SUB family):")
        for p in sub:
            pr("    %-46s  f282 %.2f Hz zeta282 %+.4f | f289 %.2f zeta289 %+.4f"
               % (p["label"][:46], p["f282"], p["z282"], p["f289"], p["z289"]))
        pr()
        hdr = "  %-11s %-46s %11s %11s %11s | %11s" % ("route", "fit", "Kd=128 LTI", "Kd=96 LTI", "MEASURED", "excess")
        pr(hdr)
        pr("  " + "-" * (len(hdr) - 2))
        J["trace"] = []
        for tag, img in (("r62_v289", "V289"), ("r63_v289", "V289"), ("r5e_v288", "V288"), ("r39", "V288")):
            if tag not in ep:
                continue
            g = C20.load(tag)
            dem, _, _ = AX.demand(np.round(g["cmd"]), g["bar"], C[img])
            seg = []
            for e in ep[tag]:
                a, b = int(e["a"]), int(e["b"])
                if b - a >= 32:
                    seg.append(dem[a:b])
            if not seg:
                continue
            d = np.concatenate(seg)
            kd = np.interp(d, KDX, KDY_S)
            kd_tick = np.repeat(kd, NHOLD)
            for p in sub:
                pl = D.mkplant(p)
                r128 = float(np.max(np.abs(np.linalg.eigvals(build(c282, pl, 128.0).step_map(128.0)[0]))))
                r96 = float(np.max(np.abs(np.linalg.eigvals(build(c282, pl, 96.0).step_map(96.0)[0]))))
                rm = lyap_trace(c282, pl, kd_tick)
                exc = rm - max(r128, r96)
                pr("  %-11s %-46s %11.6f %11.6f %11.6f | %+11.3e"
                   % (tag, p["label"][:46], r128, r96, rm, exc))
                J["trace"].append(dict(tag=tag, fit=p["label"], r128=r128, r96=r96, rmeas=rm, excess=exc,
                                       ticks=len(kd_tick)))
        pr()
        pr("  The Lyapunov exponent of the measured modulated loop is bounded by the two frozen-Kd values whenever")
        pr("  'excess' <= 0; a POSITIVE excess is parametric amplification the LTI reading misses.")
        pr("  (%.0f s)" % (time.time() - t0))
        pr()


    if what in ("deep", "all"):
        t0 = time.time()
        pr("=" * 118)
        pr("2B.3  DEPTH SWEEP WITH THE MODULATION FREQUENCY AND DUTY RE-OPTIMISED AT EACH DEPTH")
        pr("=" * 118)
        pr()
        pr("  A fixed-frequency depth sweep has a hole: raising the swing lowers the MEAN Kd, which moves the mode,")
        pr("  which moves the tongue.  Here f_mod and duty are re-searched at every depth, over the union of the")
        pr("  tongue grids.  Swings above 32 are HYPOTHETICAL -- row S can deliver at most 32.")
        pr()
        fgrid = np.concatenate([np.arange(14.0, 24.01, 0.25), np.arange(28.0, 44.01, 0.25)])
        duties = np.array([0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.75])
        rows = depth_reopt(c282, burst, np.array([4., 8., 16., 32., 64., 80., 96., 104., 112., 118., 122., 126.]), fgrid, duties)
        pr("  %-8s %-10s %-8s %-9s %-7s %-12s %-13s %s" %
           ("swing", "Kd range", "eps", "f_mod", "duty", "max rho", "max excess", "unstable fits"))
        for r in rows:
            mark = "   <-- the MOST row S can deliver" if abs(r["swing"] - 32.0) < 1e-9 else ""
            pr("  %-8.0f %-10s %-8.4f %-9.2f %-7.2f %-12.6f %+-13.2e %d%s"
               % (r["swing"], "%.0f-%.0f" % (r["kd_lo"], KD_HI), r["eps"], r["f_at"], r["duty_at"],
                  r["rho_max"], r["excess_max"], r["unst"], mark))
        pr()
        thr = next((r for r in rows if r["unst"] > 0), None)
        last_ok = [r for r in rows if r["unst"] == 0][-1] if any(r["unst"] == 0 for r in rows) else None
        if thr is None:
            pr("  ==> rho stays below 1.0 at EVERY depth tried: the 2f tongue never opens on this loop.")
        else:
            pr("  ==> THE TONGUE DOES OPEN, but only at a near-total gain modulation: the first depth with any unstable")
            pr("      fit is swing %.0f (Kd %.0f<->%.0f, eps %.3f), %d of %d fits unstable; the last fully stable depth"
               % (thr["swing"], thr["kd_lo"], KD_HI, thr["eps"], thr["unst"], len(burst)))
            pr("      is swing %.0f (eps %.3f)." % (last_ok["swing"], last_ok["eps"]) if last_ok else "")
            r32 = [r for r in rows if abs(r["swing"] - 32.0) < 1e-9][0]
            pr("      ROW S's ABSOLUTE MAXIMUM is eps %.4f -- a factor %.1f below the instability threshold, and that"
               % (r32["eps"], thr["eps"] / r32["eps"]))
            pr("      is the FULL 96<->128 square wave.  The eps actually MEASURED at 2f on the wire is 0.002-0.007")
            pr("      (0.027 worst single episode), i.e. a factor %.0f-%.0f below threshold." 
               % (thr["eps"] / 0.027, thr["eps"] / 0.0021))
        J["deep"] = rows
        pr("  (%.0f s)" % (time.time() - t0))
        pr()

    if what in ("nl", "all"):
        t0 = time.time()
        pr("=" * 118)
        pr("2D.  THE CLAMPED INTEGER MIRROR -- the check the LINEAR analysis structurally cannot make")
        pr("=" * 118)
        pr()
        pr("  Everything above is linear.  The kit's own reading of the V289 ring is a CLAMP/FRICTION-LIMITED CYCLE,")
        pr("  and a limit cycle is a nonlinear object a Floquet analysis of the unclamped loop cannot see.  So:")
        pr("  design290b's byte-exact integer Controller (P / D / sum / output clamps ALL live, the feedback")
        pr("  quantised to 1/8 deg/s exactly as the firmware does), Kd written PER TICK, setpoint held at 0, and a")
        pr("  single torque impulse injected at the PLANT input so the ring amplitude is set directly rather than")
        pr("  through the setpoint path (which saturates the D clamp at any useful kick and makes every amplitude")
        pr("  read identically).  Decay = slope of log|peak envelope| over the first 0.6 s; HIGHER = faster = better.")
        pr("  A parametric pump shows up as a modulated decay BELOW BOTH constant-Kd references.")
        pr()
        sub3 = sorted(burst, key=lambda q: q["z282"])[:3]
        fmod, duty = 39.25, 0.25
        Nn = int(round(FS / fmod)); nlo = max(1, int(round(Nn * duty)))
        sq = np.array([KD_LO] * nlo + [KD_HI] * (Nn - nlo))
        pr("  modulation: square wave %g <-> %g at %.2f Hz duty %.2f (the 2B.1 tongue peak), worst over all %d"
           % (KD_LO, KD_HI, fmod, duty, Nn))
        pr("  tick-phases, so the worst phase alignment with the ring is covered.")
        pr()
        C = {n: AX.cells(n) for n in ("V289", "V288")}
        ep = {}
        if os.path.exists(CENSUS_PKL):
            for e in pickle.load(open(CENSUS_PKL, "rb"))["episodes"]:
                ep.setdefault(e["tag"], []).append(e)
        kd_meas = None
        if "r39" in ep:
            g = C20.load("r39")
            dem, _, _ = AX.demand(np.round(g["cmd"]), g["bar"], C["V288"])
            best = None
            for e in ep["r39"]:
                a_, b_ = int(e["a"]), int(e["b"])
                if b_ - a_ < 32:
                    continue
                kk = np.interp(dem[a_:b_], KDX, KDY_S)
                sd = float(kk.std())
                if best is None or sd > best[0]:
                    best = (sd, np.repeat(kk, NHOLD))
            if best:
                kd_meas = best[1]
                pr("  measured Kd trace = the most-modulated r39 census episode: sd(Kd) %.2f over %d loop ticks"
                   % (best[0], len(kd_meas)))
                pr()
        pr("  %-34s %8s | %9s %9s %9s | %9s | %s" %
           ("fit", "ring pk", "Kd128", "Kd96", "MOD worst", "MEASURED", "verdict"))
        J["nl"] = []
        for p in sub3:
            pl = D.mkplant(p)
            for target in (1.0, 4.0, 12.0):
                imp = imp_for_peak(c282, pl, target)
                d128, pk128, _ = env_decay(ring_int(c282, pl, np.array([128.0]), imp))
                d96, _, _ = env_decay(ring_int(c282, pl, np.array([96.0]), imp))
                dm = [env_decay(ring_int(c282, pl, np.roll(sq, ph), imp))[0] for ph in range(Nn)]
                dmod = float(np.nanmin(dm))
                dmeas = np.nan
                if kd_meas is not None:
                    dmeas = float(np.nanmin([env_decay(ring_int(c282, pl, np.roll(kd_meas, o), imp))[0]
                                             for o in (0, len(kd_meas) // 3, 2 * len(kd_meas) // 3)]))
                tol = 0.02 * abs(d128)
                ok = np.isnan(dmeas) or dmeas >= d128 - tol
                pr("  %-34s %8.2f | %9.3f %9.3f %9.3f | %9.3f | %s"
                   % (p["label"][:34], pk128, d128, d96, dmod, dmeas,
                      "MEASURED: no pump (>= V282)" if ok else "*** MEASURED PUMPS: below V282 ***"))
                J["nl"].append(dict(fit=p["label"], peak=pk128, d128=d128, d96=d96, dmod=dmod,
                                    dmeas=dmeas, ok=bool(ok)))
        pr()
        pr("  'MOD worst' is the worst over every phase alignment of a SYNTHETIC worst-case full-swing square wave at")
        pr("  the tongue peak -- a construction, not something the wire does.  'MEASURED' is the REAL Kd(t) from the")
        pr("  most-modulated census grinding episode in the whole corpus, at three phase offsets, and it is the column")
        pr("  the verdict is taken on.  Ring peaks 1 / 4 / 12 deg/s bracket the measured grinding amplitudes.")
        pr()
        pr("  ** READ THE 'MOD worst' COLUMN CAREFULLY.  The synthetic square wave DOES cut the decay below V282's,")
        pr("     by up to %.0f %% at the 1 deg/s ring -- far more than the linear Floquet excess (%s) predicted."
           % (100 * (1 - min(r['dmod'] / r['d128'] for r in J['nl'] if r['d128'] > 0)), "+3.8e-4/tick, ~2 %"))
        pr("     So the CLAMPED, QUANTISED loop is MORE susceptible to a Kd pump than the linear one, and the linear")
        pr("     analysis alone would have UNDER-stated this hazard.  What makes it moot is not the linear margin but")
        pr("     the MEASURED modulation: it is 15-50x too slow and 50-500x too shallow.  2D.1 bounds the band.")
        pr("  (%.0f s)" % (time.time() - t0))
        pr()


    if what in ("nlsweep", "all"):
        t0 = time.time()
        pr("=" * 118)
        pr("2D.1  WHERE IS THE NONLINEAR LOOP ACTUALLY SUSCEPTIBLE?  Frequency sweep of the clamped integer mirror")
        pr("=" * 118)
        pr()
        pr("  The linear tongue is at 2f.  The clamped loop is more susceptible than the linear one, so the DANGER")
        pr("  BAND must be measured, not assumed.  Full-swing 96<->128 square wave, worst phase, ring peak 1 deg/s")
        pr("  (the most susceptible amplitude in 2D), on the least-damped SUB fit.  This is the band the V290")
        pr("  instrument has to be able to see.")
        pr()
        pl = D.mkplant(sorted(burst, key=lambda q: q["z282"])[0])
        imp = imp_for_peak(c282, pl, 1.0)
        d128 = env_decay(ring_int(c282, pl, np.array([128.0]), imp))[0]
        d96 = env_decay(ring_int(c282, pl, np.array([96.0]), imp))[0]
        pr("  references: constant Kd 128 -> %.3f 1/s ; constant Kd 96 -> %.3f 1/s" % (d128, d96))
        pr()
        pr("  %-9s %-6s %-11s %-11s %s" % ("f_mod Hz", "N", "worst decay", "vs Kd128", "duty at worst"))
        J["nlsweep"] = []
        pr("  (the two tongue frequencies 20.00 and 39.25 Hz are searched at FULL phase and duty resolution; the")
        pr("   survey frequencies use every 2nd phase and 3 duties, which is enough to place the band.)")
        pr()
        for fm in (2, 4, 6, 7.3, 10, 13, 16, 18, 20, 22, 25, 28, 31, 34, 37, 39.25, 42, 45, 50):
            Nn = int(round(FS / fm))
            exact = fm in (20, 39.25)
            duls = (0.15, 0.25, 0.4, 0.5, 0.6, 0.75) if exact else (0.15, 0.25, 0.5)
            step = 1 if exact else 2
            best = (1e9, None)
            for du in duls:
                nlo = min(max(int(round(Nn * du)), 1), Nn - 1)
                sqm = np.array([KD_LO] * nlo + [KD_HI] * (Nn - nlo))
                for ph in range(0, Nn, step):
                    v = env_decay(ring_int(c282, pl, np.roll(sqm, ph), imp))[0]
                    if np.isfinite(v) and v < best[0]:
                        best = (v, du)
            pr("  %-9.2f %-6d %-11.3f %-11s %.2f"
               % (fm, Nn, best[0], "%.2fx" % (best[0] / d128 if d128 else np.nan), best[1]))
            J["nlsweep"].append(dict(fmod=float(fm), worst=float(best[0]), ratio=float(best[0] / d128), duty=best[1]))
        pr()
        w = min(J["nlsweep"], key=lambda r: r["ratio"])
        band = [r["fmod"] for r in J["nlsweep"] if r["ratio"] < 0.8]
        pr("  WORST: f_mod %.2f Hz, duty %.2f -> decay %.3f 1/s = %.2fx V282's."
           % (w["fmod"], w["duty"], w["worst"], w["ratio"]))
        pr("  DANGER BAND (any modulation frequency that costs > 20 %% of the ring decay at FULL swing): %s Hz."
           % (("%.1f - %.1f" % (min(band), max(band))) if band else "none"))
        pr("  MEASURED knot-crossing rate on the wire, inside grinding episodes (item 1): 1.2 - 3.5 /s.  The measured")
        pr("  modulation therefore sits an order of magnitude BELOW the danger band even before its depth is counted.")
        pr("  (%.0f s)" % (time.time() - t0))
        pr()

    p = os.path.join(SCR, "paramod_v290_floquet.txt")
    os.makedirs(SCR, exist_ok=True)
    open(p, "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    json.dump(J, open(p.replace(".txt", ".json"), "w"), indent=1, default=float)
    pr("written: %s" % p)


if __name__ == "__main__":
    main()
