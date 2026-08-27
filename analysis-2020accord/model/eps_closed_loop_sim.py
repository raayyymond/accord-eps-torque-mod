"""Closed-loop simulator for the gp-0x4f50 -> gp-0x6c2c -> gp-0x6b26 lane.

WHY THIS EXISTS
---------------
V104..V107 sized this lane with an OPEN-LOOP push-through: take a measured
distribution of gp-0x6c2c, scale it by a ratio of two flash tables, predict the
clamp duty. V107 predicted <=1.05 % and route 1e measured 33.49 % at 10-25 km/h
-- a 32x miss. The reason is structural: gp-0x6b26 -> aggregator -> motor ->
motor rate -> gp-0x6c2c is a CLOSED LOOP, so the input distribution is not
invariant to the gain.

WHAT IS AND IS NOT TRUSTWORTHY HERE
-----------------------------------
* The firmware arithmetic (SECTION 1) is exact integer and is validated against
  Ghidra's own disassembly and P-code IR at every site. Trust it.
* The plant (SECTION 2) is the kit's identified column model, whose measured
  validity band is 5 to ~13 Hz. The gp-0x6b26 lane peaks at 61.1 Hz with a
  -3 dB span of 25.1-153.0 Hz. THE LEVER ACTS ENTIRELY OUTSIDE THE BAND WHERE
  THE PLANT IS IDENTIFIED. Every routine that would use the plant above 13 Hz
  raises unless explicitly overridden, and `PlantValidity` records why.
* Rail duty is a functional of the MARGINAL distribution of |gp-0x6c2c|, not of
  its spectrum. The 49.8 Hz CAN-427 tap samples instantaneous values, so its
  marginal is unbiased even though its spectrum is aliased. Duty measurements
  off that tap are sound; spectral claims off it are not.

Addresses: gp = 0xFEDF8000, tp = 0xBF000, control task 1 kHz, V850 is LE.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

import numpy as np

FS = 1000.0                      # control-task rate, Hz  (accord-control-task-tick-confirmed-1khz)

# ---- calibration addresses (tp = 0xBF000; anchored, not tp-arithmetic'd) ----
A_ALPHA0 = 0xC643C               # ld.hu 0x743c[tp] @0x415DA   EMA1 coeff, >> 7   SHARED
A_ALPHA2 = 0xC40DC               # ld.hu 0x50dc[tp] @0x41626   EMA2 coeff, >> 6   THE LEVER
A_ALPHA2B = 0xC40DA              # ld.hu 0x50da[tp] @0x4162A   parallel EMA, >> 7 -> gp-0x6c2e
A_CLAMP = 0xC407E                # ld.h  0x507e[tp] @0x36C34   gp-0x6b26 clamp, = 511
A_REC2627 = 0xD7A54              # mode 26/27 record: [n, X0,X1,X2, Y0,Y1,Y2, 0]

# ---- exact integer constants read out of the instruction stream -------------
IN_RANGE = 13000                 # |gp-0x4f50| <= 13000    (addi 13000 / cmp 26000)
Y0_SENTINEL = 0x7FFFFFFF
Y0_GUARD = 0xCB2000              # 13000 * 1024, @0x415F4
D32_LIMIT = 0xFA0000             # movhi 0xfa @0x4160C
D32_PRECLAMP = 0x7D000           # mov 0x7d000,r16 @0x41604   (== D32_LIMIT / 32)
C2C_GATE = 32000                 # (c2c + 0x7d00) <u 0xfa01  @0x36C26..0x36C2C
B26_MUL = 0x111                  # movea 0x111 @0x36CC0
B26_SHIFT = 0x12                 # sar 0x12 @0x36CCA

#: |gp-0x6c2c| at which the gp-0x6b26 clamp is reached, as K / |Y_eff(v)|.
#: ((|c2c| * |Y|) >> 6) * 0x111 >> 0x12 >= clamp   <=>   |c2c| >= K / |Y|
RAIL_K = 511 * (1 << B26_SHIFT) * 64 / B26_MUL          # = 31_403_506.9

#: the CAN-427 wire rail. |c2c| above this is censored, so duty is only bounded.
WIRE_RAIL = 1636.8


def _s32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >> 31 else v


def _s16(v: int) -> int:
    v &= 0xFFFF
    return v - (1 << 16) if v >> 15 else v


# =============================================================================
# SECTION 1 -- the firmware's own integer arithmetic
# =============================================================================
@dataclass
class Calibration:
    """Every constant a candidate build could move, read FROM AN IMAGE FILE."""
    alpha0: int
    alpha2: int
    alpha2b: int
    clamp: int
    X: tuple
    Y: tuple
    name: str = ''

    @classmethod
    def from_image(cls, path: str, name: str = '') -> 'Calibration':
        img = open(path, 'rb').read()
        return cls(
            alpha0=struct.unpack_from('<H', img, A_ALPHA0)[0],
            alpha2=struct.unpack_from('<H', img, A_ALPHA2)[0],
            alpha2b=struct.unpack_from('<H', img, A_ALPHA2B)[0],
            clamp=struct.unpack_from('<h', img, A_CLAMP)[0],
            X=tuple(struct.unpack_from('<3h', img, A_REC2627 + 2)),
            Y=tuple(struct.unpack_from('<3h', img, A_REC2627 + 8)),
            name=name or path.split('/')[-1][:24],
        )

    def replace(self, **kw) -> 'Calibration':
        d = dict(alpha0=self.alpha0, alpha2=self.alpha2, alpha2b=self.alpha2b,
                 clamp=self.clamp, X=self.X, Y=self.Y, name=self.name)
        d.update(kw)
        return Calibration(**d)

    # ---- FUN_00036c12, the speed schedule -----------------------------------
    def y_eff(self, v_kph: float) -> int:
        """LERP on X (counts @ 64 ct/km/h). INT_SDIV truncates toward zero."""
        ct = v_kph * 64.0
        X, Y = self.X, self.Y
        if ct <= X[0]:
            return Y[0]
        if ct >= X[2]:
            return Y[2]
        i = 0 if ct < X[1] else 1
        num = (Y[i + 1] - Y[i]) * (ct - X[i])
        q = int(abs(num) // (X[i + 1] - X[i]))
        return Y[i] + (q if num >= 0 else -q)

    def rail_threshold(self, v_kph: float) -> float:
        """|gp-0x6c2c| at which gp-0x6b26 hits +-clamp, at this speed.

        Found by integer bisection on the real arithmetic, NOT from the closed
        form K/|Y|. `sar` floors toward -inf, so the clamp is reached at a
        slightly smaller magnitude on whichever side the product is negative --
        a ~0.2 % asymmetry the closed form silently averages away.
        """
        return float(_rail_thr_for_y(self.y_eff(v_kph), self.clamp))


from functools import lru_cache


@lru_cache(maxsize=None)
def _rail_thr_for_y(y_eff: int, clamp: int) -> int:
    """Smallest |c2c| with |b26| >= clamp. Depends only on y_eff, so cacheable
    exactly -- no speed quantisation. Bisection on the real integer arithmetic."""
    def mag(c):
        x = c if -C2C_GATE <= c <= C2C_GATE else 0
        t = (x * y_eff) >> 6
        return abs(max(-clamp, min(clamp, _s32(t * B26_MUL) >> B26_SHIFT)))
    lo, hi = 0, C2C_GATE
    while lo < hi:
        mid = (lo + hi) // 2
        if mag(mid) >= clamp:
            hi = mid
        else:
            lo = mid + 1
    return lo


def b26_from_c2c(c2c: int, v_kph: float, cal: Calibration) -> int:
    """FUN_00036c12 @0x36C1A..0x36CE2 -- exact.

    gate  @0x36C26/0x36C2A/0x36C2C : x = c2c if |c2c| <= 32000 else 0
    mulh  @0x36CBE                 : signed 16x16 -> 32
    sar 6 @0x36CC4                 : ARITHMETIC
    mul   @0x36CC6                 : * 0x111, low 32 bits
    sar 18@0x36CCA                 : ARITHMETIC
    clamp @0x36CCC..0x36CE2        : +- cal(0xC407E)
    """
    x = int(c2c) if -C2C_GATE <= int(c2c) <= C2C_GATE else 0
    x = _s16(x)
    t = (x * cal.y_eff(v_kph)) >> 6
    t = _s32(t * B26_MUL) >> B26_SHIFT
    return max(-cal.clamp, min(cal.clamp, t))


def cascade(u: np.ndarray, cal: Calibration, state: dict | None = None):
    """FUN_00041464 @0x415C8..0x41640 -- exact integer, one sample per call site.

    y0    += ((u * 1024 - y0) * alpha0) >> 7      EMA1   @0x415DA..0x415E8
    d32    = clamp((y0[n] - y0[n-1]) * 32, +-0xFA0000)   @0x41600..0x4161A
    s1    += ((d32 - s1) * alpha2) >> 6           EMA2   @0x41626..0x4163A
    c2c    = (short)(s1 >> 9)                            @0x41A..  (decompile)

    Returns (c2c, state). `u` is gp-0x4f50, int16 motor rate in counts.
    """
    st = state or {'y0': Y0_SENTINEL, 's1': 0, 's2': 0}
    y0, s1, s2 = st['y0'], st['s1'], st['s2']
    A0, A2, A2B = cal.alpha0, cal.alpha2, cal.alpha2b
    out = np.empty(len(u), dtype=np.int32)

    for n, raw in enumerate(u):
        ui = int(raw)
        ui = max(-32768, min(32767, ui))
        if not (-IN_RANGE <= ui <= IN_RANGE):        # out of range -> reset
            y0, s1, s2 = Y0_SENTINEL, 0, 0
            out[n] = 0x7FFF
            continue
        prev = y0
        target = ui * 1024
        if y0 == Y0_SENTINEL:
            y0_new = target
        else:
            y0_new = _s32(y0 + (_s32((target - y0) * A0) >> 7))
        if prev == Y0_SENTINEL or prev > Y0_GUARD:   # @0x415FA/0x415FE
            prev = y0_new
        diff = y0_new - prev
        if diff > D32_PRECLAMP:                      # bgt @0x41610
            d32 = D32_LIMIT
        else:
            d32 = _s32(diff * 32)
            if d32 <= -D32_LIMIT:                    # cmovle @0x4161A
                d32 = -D32_LIMIT
        s1 = _s32(s1 + (_s32((d32 - s1) * A2) >> 6))
        s2 = _s32(s2 + (_s32((d32 - s2) * A2B) >> 7))
        y0 = y0_new
        out[n] = _s16(s1 >> 9)

    return out, {'y0': y0, 's1': s1, 's2': s2}


def analytic_H(f, alpha0: float, alpha2: float, fs: float = FS):
    """|H| of gp-0x4f50 -> gp-0x6c2c, as a continuous LTI stand-in.

    H = 64 * H1 * (1 - z^-1) * H2,  H1/H2 one-pole EMAs.
    The 64 is 1024 (EMA1 input scale) * 32 (d32) / 512 (>>9).
    """
    f = np.asarray(f, dtype=float)
    z = np.exp(2j * np.pi * f / fs)
    H1 = alpha0 / (1 - (1 - alpha0) / z)
    H2 = alpha2 / (1 - (1 - alpha2) / z)
    return 64 * H1 * (1 - 1 / z) * H2


def ratio_filter(f, cal_old: Calibration, cal_new: Calibration, fs: float = FS):
    """|H_new / H_old| -- EXACT for the same input, both being LTI.

    This is the open-loop reshaping factor. It is exact as a filter identity and
    says nothing about how the closed loop moves the input.
    """
    a2o, a2n = cal_old.alpha2 / 64.0, cal_new.alpha2 / 64.0
    a0o, a0n = cal_old.alpha0 / 128.0, cal_new.alpha0 / 128.0
    return analytic_H(f, a0n, a2n, fs) / analytic_H(f, a0o, a2o, fs)


# =============================================================================
# SECTION 2 -- the plant, and the band in which it is allowed to speak
# =============================================================================
class PlantValidityError(RuntimeError):
    pass


@dataclass
class ColumnPlant:
    """The kit's identified upper-column model, hands-off:

        J_w * theta'' + b_w * theta' = -T_bar     =>   Z = T_bar/Omega_w = -(b_w + j w J_w)

    STOCK  J_w = 1.248 [1.110, 1.358], b_w = 35.8, b/J = 28.7 rad/s  (corner 4.57 Hz)
    V100   J_w = 1.202,                b_w = 35.0, b/J = 29.1 rad/s
    Two independent drives agreeing to 4 % on J and 2 % on b.
    Source: docs/handoffs/2026-08/HANDOFF-2026-08-22-hs-identification-and-five-instrument-defects.md

    MEASURED VALIDITY BAND: 5 to ~13 Hz.  Above ~13 Hz |Z| rolls off un-modelled
    (STOCK |Z|/w: flat 1.54->1.33 over 6-12 Hz, then 1.15 @14, 0.45 @16) and the
    handoff records that this may be either real plant or an internal low-pass in
    the torque channel -- unresolved, so THE SIGN OF THE EXTRAPOLATION ERROR IS
    NOT KNOWN.  A 2-parameter fit also shows a systematic smooth error on every
    route (log-log slope -0.51 to -4.32 where 0 is required).
    """
    J_w: float = 1.248
    b_w: float = 35.8
    valid_lo: float = 5.0
    valid_hi: float = 13.0
    J_ci: tuple = (1.110, 1.358)

    @property
    def corner_hz(self) -> float:
        return self.b_w / self.J_w / (2 * np.pi)

    def admittance(self, f, strict: bool = True):
        """Omega_w / (-T_bar) = 1 / (b_w + j w J_w), normalised to unit DC gain."""
        f = np.asarray(f, dtype=float)
        if strict and (np.max(f) > self.valid_hi or np.min(f) < self.valid_lo):
            raise PlantValidityError(
                f'plant asked for {np.min(f):.3g}-{np.max(f):.3g} Hz; identified '
                f'band is {self.valid_lo}-{self.valid_hi} Hz. Above ~13 Hz |Z| rolls '
                'off un-modelled and the sign of the error is unknown. Pass '
                'strict=False only to make an explicitly-labelled extrapolation.')
        w = 2 * np.pi * f
        return self.b_w / (self.b_w + 1j * w * self.J_w)

    def lane_band_is_outside(self, cal: Calibration) -> dict:
        """Where the gp-0x6b26 lane actually acts, vs where the plant is valid."""
        f = np.linspace(0.5, FS / 2 - 1, 200000)
        mag = np.abs(analytic_H(f, cal.alpha0 / 128.0, cal.alpha2 / 64.0))
        pk = f[np.argmax(mag)]
        keep = np.where(mag >= mag.max() / np.sqrt(2))[0]
        lo, hi = f[keep[0]], f[keep[-1]]
        band = np.linspace(lo, hi, 4000)
        frac_out = float(np.mean(band > self.valid_hi))
        return {'peak_hz': pk, 'minus3db': (lo, hi),
                'plant_valid': (self.valid_lo, self.valid_hi),
                'fraction_of_lane_band_above_plant_ceiling': frac_out,
                'peak_is_outside': bool(pk > self.valid_hi)}


# =============================================================================
# SECTION 3 -- duty, measured or simulated
# =============================================================================
def rail_duty(c2c_mag, v_kph, cal: Calibration):
    """P(|gp-0x6b26| == clamp). Exact integer, per sample -- no distributional
    assumption. Returns (duty, censored_fraction)."""
    c2c_mag = np.asarray(c2c_mag, dtype=float)
    v_kph = np.asarray(v_kph, dtype=float)
    thr = np.array([cal.rail_threshold(v) for v in v_kph])
    railed = c2c_mag >= thr
    censored = float(np.mean(thr > WIRE_RAIL))
    return float(np.mean(railed)), censored


def duty_by_bin(c2c_mag, v_kph, cal: Calibration,
                bins=((0, 10), (10, 25), (24, 40), (40, 64), (65, 999))):
    rows = []
    for lo, hi in bins:
        m = (v_kph >= lo) & (v_kph < hi)
        if m.sum() == 0:
            rows.append({'bin': (lo, hi), 'n': 0})
            continue
        duty, cens = rail_duty(c2c_mag[m], v_kph[m], cal)
        thr = cal.rail_threshold(float(np.median(v_kph[m])))
        rows.append({'bin': (lo, hi), 'n': int(m.sum()), 'duty': duty,
                     'threshold': thr, 'censored': thr > WIRE_RAIL})
    return rows


def episode_bootstrap(c2c_mag, v_kph, episode_id, cal, lo, hi, n_boot=3000, seed=0):
    """Bootstrap over EPISODES, not windows (feedback-episodes-not-windows)."""
    rng = np.random.default_rng(seed)
    m = (v_kph >= lo) & (v_kph < hi)
    if m.sum() == 0:
        return None
    eps = np.asarray(episode_id)[m]
    c, v = np.asarray(c2c_mag)[m], np.asarray(v_kph)[m]
    uniq = np.unique(eps)
    if len(uniq) < 2:
        return None
    groups = [(c[eps == e], v[eps == e]) for e in uniq]
    stats = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        cc = np.concatenate([groups[i][0] for i in pick])
        vv = np.concatenate([groups[i][1] for i in pick])
        stats.append(rail_duty(cc, vv, cal)[0])
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


# =============================================================================
# SECTION 4 -- the closed loop
# =============================================================================
@dataclass
class ClosedLoopSim:
    """u -> cascade -> c2c -> b26 -> (-K_loop, through the plant) -> u.

    K_loop is the ONE free parameter: the DC gain from a gp-0x6b26 count to a
    gp-0x4f50 count. It is not identified anywhere in the kit, so it must be fit
    to a measurement and the fit must be held out.
    """
    cal: Calibration
    plant: ColumnPlant = field(default_factory=ColumnPlant)
    K_loop: float = 0.0
    allow_extrapolation: bool = False

    def _plant_taps(self, n: int = 512):
        """1 kHz FIR of the normalised admittance. Uses the plant OUTSIDE its
        identified band, which is exactly why every result carries a warning."""
        f = np.fft.rfftfreq(n, 1 / FS)
        Hc = self.plant.admittance(np.maximum(f, 1e-6), strict=False)
        h = np.fft.irfft(Hc, n)
        return np.roll(h, n // 2)[n // 2 - 32: n // 2 + 96]

    def run(self, drive: np.ndarray, v_kph, warmup: int = 2000):
        """`drive` is the exogenous motor-rate excitation in gp-0x4f50 counts."""
        if not self.allow_extrapolation:
            raise PlantValidityError(
                'ClosedLoopSim.run() drives the plant across the whole 0-500 Hz '
                'lane; the identified plant covers 5-13 Hz. Set '
                'allow_extrapolation=True to run it as a LABELLED EXTRAPOLATION, '
                'and do not quote the output as a prediction.')
        taps = self._plant_taps()
        v = np.broadcast_to(np.asarray(v_kph, dtype=float), drive.shape)
        n = len(drive)
        u = np.zeros(n)
        c2c = np.zeros(n, dtype=np.int32)
        hist = np.zeros(len(taps))
        st = None
        fb = 0.0
        for k in range(n):
            u[k] = drive[k] + fb
            c, st = cascade(np.array([u[k]]), self.cal, st)
            c2c[k] = c[0]
            b = b26_from_c2c(c[0], float(v[k]), self.cal)
            hist[1:] = hist[:-1]
            hist[0] = -self.K_loop * b
            fb = float(np.dot(hist, taps))
        return {'u': u[warmup:], 'c2c': c2c[warmup:], 'v': v[warmup:]}


# =============================================================================
# SECTION 5 -- the control. Run this BEFORE any duty number.
# =============================================================================
def self_check(verbose: bool = True) -> bool:
    """Known-answer cases. feedback-run-the-control-before-the-measurement."""
    ok = True
    a0, a2 = 37 / 128.0, 22 / 64.0

    # (1) analytic |H| against the kit's recorded table
    ref = {1: 0.40, 7.79: 3.08, 21.73: 7.72, 40: 11.15, 61.1: 12.14,
           100: 10.86, 200: 7.15, 300: 5.45, 499: 4.49}
    for f, want in ref.items():
        got = abs(analytic_H(f, a0, a2))
        if abs(got - want) > 0.011 * max(1.0, want):
            ok = False
            if verbose:
                print(f'  FAIL |H|({f}) = {got:.4f}, recorded {want}')
    f = np.linspace(0.5, 499, 200000)
    mag = np.abs(analytic_H(f, a0, a2))
    pk = f[np.argmax(mag)]
    keep = np.where(mag >= mag.max() / np.sqrt(2))[0]
    if not (61.0 <= pk <= 61.2 and abs(f[keep[0]] - 25.1) < 0.1
            and abs(f[keep[-1]] - 153.0) < 0.3):
        ok = False
        if verbose:
            print(f'  FAIL peak/-3dB: {pk:.2f} Hz, {f[keep[0]]:.2f}-{f[keep[-1]]:.2f}')
    if verbose:
        print(f'  |H| table + peak {pk:.2f} Hz + -3 dB '
              f'{f[keep[0]]:.2f}-{f[keep[-1]]:.2f} Hz: '
              f'{"PASS" if ok else "FAIL"}')

    # (2) the INTEGER cascade must reproduce the analytic |H| on a pure sinusoid
    cal = Calibration(alpha0=37, alpha2=22, alpha2b=3, clamp=511,
                      X=(0, 1280, 5760), Y=(-29490, -24000, -16000), name='self')
    if verbose:
        print('  integer cascade vs analytic |H| on a pure sinusoid '
              '(amplitudes BELOW the d32 clamp onset):')
    for f0, amp in ((7.79, 1000), (21.73, 1000), (61.1, 1000), (100.0, 1000),
                    (200.0, 1000)):
        n = int(FS * 12)
        t = np.arange(n) / FS
        x = np.round(amp * np.sin(2 * np.pi * f0 * t)).astype(int)
        y, _ = cascade(x, cal)
        y = y[3000:]
        ref_amp = amp * abs(analytic_H(f0, a0, a2))
        # single-bin DFT at f0 -> amplitude
        tt = np.arange(len(y)) / FS
        got = 2 * abs(np.sum(y * np.exp(-2j * np.pi * f0 * tt))) / len(y)
        rel = got / ref_amp
        good = 0.97 <= rel <= 1.03
        ok &= good
        if verbose:
            print(f'    {f0:6.2f} Hz: integer {got:9.1f}  analytic {ref_amp:9.1f} '
                  f' ratio {rel:.4f}  {"PASS" if good else "FAIL"}')

    # (3) the d32 clamp onset -- the lane is NOT linear above it, and the kit's
    #     whole alpha2 sweep table was computed from the linear |H|.
    if verbose:
        print('  d32 clamp onset (input amplitude at which +-0xFA0000 binds):')
    for f0 in (7.79, 21.73, 61.1, 100.0):
        z = np.exp(2j * np.pi * f0 / FS)
        h1 = abs(a0 / (1 - (1 - a0) / z))
        a_max = D32_LIMIT / (32 * 1024 * h1 * abs(1 - 1 / z))
        n = int(FS * 8)
        t = np.arange(n) / FS
        lin, sat = [], []
        for A, box in ((int(a_max * 0.5), lin), (int(a_max * 4), sat)):
            x = np.round(A * np.sin(2 * np.pi * f0 * t)).astype(int)
            y, _ = cascade(x, cal)
            y = y[3000:]
            tt = np.arange(len(y)) / FS
            box.append(2 * abs(np.sum(y * np.exp(-2j * np.pi * f0 * tt))) / len(y)
                       / (A * abs(analytic_H(f0, a0, a2))))
        good = lin[0] > 0.99 and sat[0] < 0.85
        ok &= good
        if verbose:
            print(f'    {f0:6.2f} Hz: A_max {a_max:7.0f} ct | at 0.5x '
                  f'ratio {lin[0]:.4f} (linear), at 4x ratio {sat[0]:.4f} '
                  f'(saturated)  {"PASS" if good else "FAIL"}')

    # (4) the rail threshold, by integer bisection on the real arithmetic
    for v, want_y in ((0, -29490), (20, -24000), (90, -16000)):
        thr = cal.rail_threshold(v)
        assert cal.y_eff(v) == want_y, (v, cal.y_eff(v), want_y)
        below = abs(b26_from_c2c(int(thr) - 1, v, cal))
        at = abs(b26_from_c2c(int(thr), v, cal))
        good = below < cal.clamp <= at
        ok &= good
        if verbose:
            print(f'    rail threshold @{v:3d} km/h = {thr:7.0f} ct  '
                  f'(|b26| at thr-1 = {below}, at thr = {at})  '
                  f'{"PASS" if good else "FAIL"}')
    return bool(ok)


if __name__ == '__main__':
    print('=== eps_closed_loop_sim self_check ===')
    print('OK' if self_check() else 'FAILURES ABOVE')
