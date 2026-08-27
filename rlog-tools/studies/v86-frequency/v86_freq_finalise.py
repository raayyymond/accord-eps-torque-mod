#!/usr/bin/env python3
"""Merge parts 1-5 into `_scratch/cache/r6f/v86_freq_test.json`, add the verdict block and the design
sensitivity, and render the two-panel figure."""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402

ROOT = V.ROOT
C = ROOT / "_scratch/cache/r6f"

M = {}
_p1 = json.loads((C / "v86_freq_test.json").read_text())
# idempotent: the merged file lives at the same path, so unwrap it on a re-run
M["part1_primary"] = _p1.get("part1_primary", _p1)
for k, f in (("part2_gate_power", "v86_freq_test_part2.json"),
             ("part3_surrogate", "v86_freq_test_part3.json"),
             ("part4_residuals", "v86_freq_test_part4.json"),
             ("part5_hf_mode", "v86_freq_test_part5.json"),
             ("part6_anchors_ordering", "v86_freq_test_part6.json")):
    M[k] = json.loads((C / f).read_text())

p1, p3, p5, p6 = (M["part1_primary"], M["part3_surrogate"], M["part5_hf_mode"],
                  M["part6_anchors_ordering"])
r = p1["ratio"]["V86/r6f|V85/r6e|f_free"]

M["VERDICT"] = {
    "verdict": "FALSIFIED",
    "verdict_text": ("The peak did NOT land in [6.2, 6.9] Hz and the ratio CI does not exclude "
                     "1.00. It stayed where V85 had it. The linear-loop hypothesis, as "
                     "pre-registered, DIES."),
    "f_V86_r6f_Hz": p1["f_c"]["V86/r6f"]["f_free"][:3],
    "f_V85_r6e_Hz": p1["f_c"]["V85/r6e"]["f_free"][:3],
    "f_V86B_r70_Hz": p1["f_c"]["V86B/r70"]["f_free"][:3],
    "ratio": [r["ratio"], r["lo"], r["hi"]],
    "prereg_ratio": [V.RATIO_LO, V.RATIO_HI],
    "prereg_band_Hz": [V.PREREG_LO, V.PREREG_HI],
    "ratio_CI_disjoint_from_prereg": bool(r["lo"] > V.RATIO_HI),
    "ratio_CI_includes_1": bool(r["lo"] <= 1.0 <= r["hi"]),
    "adequately_powered": True,
    "power_basis": ("frequency-shift surrogate: 6f's own line moved by x0.797/0.843/0.875 is "
                    "recovered with a CI excluding 1.00 in ALL THREE cases; smallest resolvable "
                    "shift is ~x0.94 (0.48 Hz), 2.6x smaller than the pre-registered x0.843"),
    "mdd_ratio": p3.get("mdd_ratio"),
    "lever_in_force": True,
    "lever_in_force_basis": ("0xC40D4 = 286 byte-verified in the flown image; aggregator gate "
                             "b4 OPEN 100.00%; residual gp-0x6b70 non-zero 99.88% and >=512 on "
                             "94.6% of engaged frames; AND the 18-27 Hz mode moved +10.6% with "
                             "the alpha-unchanged control V86B staying put"),
    # 🛑 the record's 7.79 anchor was NOT V85's measured centre.  The primary statistic was
    # always a ratio against a SPEED-MATCHED V85, so the anchor never entered it -- but score
    # every defensible denominator and both absolute windows anyway.
    "anchor_robustness": p6["anchors"],
    "absolute_windows": p6["windows"],
    "anchor_defect_changes_verdict": False,
    # 🛑 V85 and V86B carry the SAME alpha (573).  Their cross-route ratio is a pure null on
    # the whole pipeline and bounds any alpha claim from below.
    "build_to_build_null_same_alpha": p6["pairs"]["V86B/r70|V85/r6e"]["r"],
    "three_point_ordering": p6["ordering"],
    "pooled_stock_alpha_vs_half": p6["pooled_stock"],
    "probe_reconciliation": p6["probe_reconcile"],
}

# ---- design sensitivity from the ONE mode that did move ---------------------------------------
hf = p5["hf_ratio"]["V86/r6f|V85/r6e|f_hf"]
a1, a0 = 573 / 4096.0, 286 / 4096.0
sens = np.log(hf["ratio"]) / np.log(a0 / a1)
M["design"] = {
    "note": ("The pre-registered 7.79 Hz test is FALSIFIED, so no design number exists for the "
             "ratchet. These numbers are for the 18-27 Hz mode, which DID move. n=2 dose levels "
             "(573, 286) -- a two-point slope, NOT to be extrapolated far."),
    "f_hf_V86": p5["hf"]["V86/r6f"]["argmax"][:3],
    "f_hf_V85": p5["hf"]["V85/r6e"]["argmax"][:3],
    "f_hf_V86B_control": p5["hf"]["V86B/r70"]["argmax"][:3],
    "ratio_V86_V85": [hf["ratio"], hf["lo"], hf["hi"]],
    "d_ln_f_d_ln_alpha": float(sens),
    "alpha_573": a1, "alpha_286": a0,
    "added_lag_deg_at_8Hz": M["part2_gate_power"]["added_lag_deg_at_8Hz"],
    "loop_bound_from_null": M["part2_gate_power"]["bound"],
}
for tgt in (21.0, 18.0, 15.0):
    f_now = p5["hf"]["V86/r6f"]["argmax"][0]
    need = (tgt / f_now) ** (1.0 / sens)
    al = a0 * need
    M["design"].setdefault("to_move_HF_mode_to", {})[str(tgt)] = {
        "alpha_multiplier": float(need), "alpha": float(al),
        "cell_value": float(al * 4096),
        # 🛑 alpha is a Q12 FRACTION: alpha <= 1 means the cell caps at 4096, NOT at 65535.
        "reachable": bool(al <= 1.0)}

(C / "v86_freq_test.json").write_text(json.dumps(M, indent=1, default=float))
print("merged -> %s" % (C / "v86_freq_test.json"))
print(json.dumps(M["VERDICT"], indent=1)[:1400])
print("\nd(ln f)/d(ln alpha) = %.4f   (f ~ alpha^%.3f)" % (sens, sens))
for k, v in M["design"]["to_move_HF_mode_to"].items():
    print("   to put the HF mode at %5s Hz: alpha x%.2f -> 0xC40D4 = %.0f  (alpha<=1 reachable: %s)"
          % (k, v["alpha_multiplier"], v["cell_value"], v["reachable"]))

# ---- figure -----------------------------------------------------------------------------------
import matplotlib                                                            # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                              # noqa: E402

lo = np.array(M["part1_primary"]["mean_spectrum"]["rows"], float)
hi = np.array(M["part5_hf_mode"]["spectrum_16_32"], float)

fig, ax = plt.subplots(1, 2, figsize=(14, 5.4))
a = ax[0]
a.axvspan(V.PREREG_LO, V.PREREG_HI, color="tab:orange", alpha=0.18, zorder=0)
a.plot(lo[:, 0], lo[:, 2], lw=2.0, color="tab:blue", label="V85 / 6e   (alpha=573)")
a.plot(lo[:, 0], lo[:, 1], lw=2.4, color="tab:red", label="V86 / 6f   (alpha=286)")
a.plot(lo[:, 0], lo[:, 3], lw=1.4, color="tab:green", ls="--", label="V86B / 70 (alpha=573)")
a.axvline(7.79, color="0.3", lw=0.9, ls=":")
a.set_title("PRE-REGISTERED TEST: the ~7.79 Hz ratchet\nshaded = CONFIRMED window [6.2, 6.9] Hz "
            "-- NOTHING MOVED THERE")
a.set_xlabel("Hz"); a.set_ylabel("prominence over local floor")
a.legend(fontsize=8.5); a.grid(alpha=0.3)

b = ax[1]
b.plot(hi[:, 0], hi[:, 2], lw=2.0, color="tab:blue", label="V85 / 6e   (alpha=573)")
b.plot(hi[:, 0], hi[:, 1], lw=2.4, color="tab:red", label="V86 / 6f   (alpha=286)")
b.plot(hi[:, 0], hi[:, 3], lw=1.4, color="tab:green", ls="--", label="V86B / 70 (alpha=573)")
b.annotate("", xy=(23.66, 26), xytext=(20.97, 26),
           arrowprops=dict(arrowstyle="->", color="k", lw=1.6))
b.text(22.3, 27.5, "+10.6%\n[+7.3, +14.4]", ha="center", fontsize=9)
b.set_title("NOT pre-registered: the engaged-only ~21 Hz mode\nDID move -- and the "
            "alpha-unchanged control stayed put")
b.set_xlabel("Hz"); b.grid(alpha=0.3); b.legend(fontsize=8.5)
fig.suptitle("V86 (0xC40D4 573->286, command-branch EMA alpha 0.1399->0.0698) -- "
             "speed-matched engaged, v in [0.5, 5.0) m/s, torsion bar", fontsize=10.5)
fig.tight_layout()
fig.savefig(C / "v86_freq_test.png", dpi=140)
print("\nwrote %s" % (C / "v86_freq_test.png"))
