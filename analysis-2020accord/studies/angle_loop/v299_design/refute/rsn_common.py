# -*- coding: utf-8 -*-
"""rsn_common.py -- metric helpers for the stability-nonlinear refuter (mine).  ANALYSIS ONLY."""
import numpy as np

SYS = {"V298": ("V298", "V298"), "V299A": ("V299", "A"), "V299B": ("V299", "B")}


def runs(m, nmin=1):
    d = np.diff(np.r_[0, m.astype(np.int8), 0])
    a, b = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    k = (b - a) >= nmin
    return np.c_[a[k], b[k]]


def toggles(x):
    return int(np.count_nonzero(x[1:] != x[:-1]))


def mov(x, n):
    return np.convolve(x, np.ones(n) / n, "same")


def stall_surge(om100):
    """m4 stall-surge definition (S2's stall_surge_count, re-typed): stall < 0.25 |mean| then surge > 0.75 |mean|."""
    mbar = mov(om100, 50)
    turn = np.abs(mbar) >= 10.0
    f3 = mov(om100 * np.sign(mbar), 3)
    stall = turn & (f3 < 0.25 * np.abs(mbar))
    surge = np.flatnonzero(turn & (f3 > 0.75 * np.abs(mbar)))
    n = 0
    for a, b in runs(stall, 2):
        j = np.searchsorted(surge, b)
        i = np.searchsorted(surge, a) - 1
        if j < len(surge) and surge[j] - b <= 25 and i >= 0 and a - surge[i] <= 25:
            n += 1
    return n


def bp(x, lo, hi, fs=1000.0):
    from scipy import signal
    sos = signal.butter(2, [lo, hi], "bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0)


def episodes(b):
    b = np.asarray(b, bool)
    return int(np.count_nonzero(b[1:] & ~b[:-1]) + (1 if len(b) and b[0] else 0))


def limit_cycle(x, thr):
    """count sign changes of the de-meaned signal whose half-cycle peak exceeds thr (a crude sustained-cycle count)."""
    y = x - np.median(x)
    s = np.sign(y)
    idx = np.flatnonzero(s[1:] != s[:-1])
    if len(idx) < 3:
        return 0
    pk = [np.abs(y[a:b]).max() for a, b in zip(idx[:-1], idx[1:])]
    return int(np.count_nonzero(np.array(pk) >= thr))
