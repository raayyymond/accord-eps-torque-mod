---
name: reference_accord_c520c_empirically_slack_on_route_a6_and_scale_anchor
description: "Settles a scale dispute (4.7121 ct/column-deg/s IS correct, externally anchored via Honda's own CAN 0x14A rate field cross-validated r>=0.985 against a differentiated angle channel) and empirically STRIKES the 0xC520C governor ceiling as a practical rate-cap explanation: on route a6 (V106's own flown route, 1238s engaged), gp-0x6ac0 crosses X[0]=1050 only 0.11% of the time and NEVER reaches X[1]=1700+; gp-0x4f64 sits at its own max (4762) for p50/p90/p99, dipping only to ~4221-4257 at the single most extreme moment of the whole route. Matches b6=0.000000 and V41's 2026-07-20 null exactly. Also computes: a vibration would need 0.73-4.48 deg amplitude (8-100Hz) to alone cross X[0] -- 18x+ larger than what rails gp-0x6b26 -- so goal1/goal5 do not tie together through this table."
metadata:
  type: reference
---

# `0xC520C` is real but empirically slack; the "4.7121" scale is correctly anchored

Traced 2026-08-26 (`ratecap` task), resolving a direct dispute with `arc-delta`'s report.

## 1. [EVIDENCE] The scale: 4.7121 counts per column deg/s, externally anchored

Anchor: `analysis-2020accord/model/eps_lkas_chain_model.py` documents Honda's own broadcast CAN 0x14A
rate field as "factor 1 deg/s," **cross-validated r>=0.985, slope 0.95-1.00 against a differentiated
angle channel from real telemetry** — this is the external ground truth, not an inference. From there,
pure arithmetic (all cals byte-verified): `0x14A_raw = (-gp-0x69ea)>>3`, `gp-0x69ea = -gp-0x6a56` (exact
negation, sole writer `FUN_00040a50`), `gp-0x6a56 = gp-0x6abe * 48*1159/32768` (`cal(0xC613A)`=1159).
Composing: `gp-0x6abe = 8*column_degps/1.698046875 = 4.7113`, matching **4.7121** to 4 sig figs.
**Independently reproduced** in `rlog-tools/studies/identification/gp6ac0_operating_point.py` from the
identical underlying firmware constants (`2^18/(48*1159)`), different author, same answer.

🛑 `reference_accord_gp6abe_column_degps_scale_settled.md` (this dir) was internally self-contradictory
— a stale unretracted mid-file section argued the opposite (0.58901, "4.7121 wrong by 8x") by applying
0x14A's documented scale to `gp-0x6a56`, which is actually **0x18F's** raw field, not 0x14A's. **Fixed
in place 2026-08-26** — the dead section is now clearly marked, not deleted (audit trail).

## 2. [EVIDENCE] Route `a6` measurement — `0xC520C` almost never engages in practice

`_scratch/cache/ra6/ra6.npz`, 123,802 engaged frames / 1238.0 s, 3 independent rate estimators
(Honda's own `cs_rate`, raw central-difference, light Savitzky-Golay), converted via the 4.7121 scale
and checked against the REAL `0xC520C` knots `[1050, 1700, 2500, 3700, 4100]`:

```
              p50   p90    p99    p99.9   MAX(ct)  MAX(deg/s)
cs_rate (E1)  5.9   60.2   585.5  1084.6  1462.1   310.3
raw diff (UB) 5.4   63.3   593.4  1082.9  1448.7   307.4

frac(count > X[0]=1050):  0.108-0.118%  (1.3-1.5 s of 1238 s engaged)
frac(count > X[1]=1700):  0.0000%  (never, all 3 estimators)
frac(count > X[2..4]):    0.0000%  (never)

gp-0x4f64 (ceiling) at p50/p90/p99/p99.9:  4762/4762/4762/4762 (its own MAX)
gp-0x4f64 at the single MAX moment of the whole route: ~4221-4257 (an 11-12% cut, NOT the floor)
```

⇒ **This directly reconciles the measured `b6`=0.000000** (`|gp-0x6b94|>=|gp-0x4f64|`, 65,959 frames,
cited as retiring hypothesis H3) — since `gp-0x4f64` sits at its own max 99.9%+ of the time, a clamp
test against it reading zero needs no separate explanation.

⇒ **And it explains V41's 2026-07-20 null** (`memory/builds/v40-governor-slew-root-cause.md`: cap
flattened, "fixed NEITHER the ratchet nor the vibration... do not spend another build here"). V41's
drive almost certainly never reached the table's collapsing region either, for the same structural
reason `a6` doesn't — two independent measurements 37 days apart, different base builds, agreeing.

## 3. `0xC520C` STRUCK as a practical lever — the mechanism stands, the recommendation does not

My own earlier ranking (this session, same task) called `0xC520C` "the first/tightest bind" on a fast
manoeuvre — that was a THEORETICAL/structural ranking. This measurement refutes it as a PRACTICAL
claim: the car's real achieved rates, including genuinely hard manoeuvres on `a6`, essentially never
reach where the table matters. **Retracted as the practical answer.** The formula/mechanism (item in
[[reference_accord_governor_final_clamp_and_gp4f64_selftest_writers]]) remains correct and documented.

## 4. [EVIDENCE] Oscillation-inflation: computed, clean NO for this table specifically

Amplitude of a pure sinusoid at f needed to ALONE push `gp-0x6ac0` past X[0]=1050, through the ~55 Hz
EMA (`alpha=37/128`, `fc=54.83 Hz`, exact formula from the governor derivation):

```
f(Hz)   |H(f)|   amplitude needed (peak)
  8     0.989    4.48 deg
 22     0.928    1.74 deg
 61     0.669    0.87 deg
100     0.485    0.73 deg (43.9 arcmin)
```

Compare `hfmech`'s `gp-0x6b26` (a DIFFERENT cell, same 1kHz cascade): rails at only **~0.04 deg (2.5
arcmin) at 100 Hz** — 18x smaller. ⇒ any vibration large enough to matter for `gp-0x6ac0`/`0xC520C`
rails `gp-0x6b26` first, by more than an order of magnitude, at every frequency checked. The rare X[0]
crossings in section 2 (0.1% of engaged time) are almost certainly genuine large manoeuvres, not
background vibration. **The operator's rate-limit complaint (goal 1) and the grinding/vibration
complaint (goal 5) do NOT tie together through `0xC520C`.** If they tie together at all, it's through
`gp-0x6b26` (a different, additive, acceleration-opposing mechanism — see
[[reference_accord_governor_final_clamp_and_gp4f64_selftest_writers]] section 3).

## Related
[[reference_accord_governor_final_clamp_and_gp4f64_selftest_writers]] — the formula this measurement
tests. [[reference_accord_c61be_c61b4_c61b2_diagnostic_cluster_not_lkas_ceiling]] — the ceiling that
IS a plausible practical answer (flat, not rate-adaptive, upstream of the gain). `v40-governor-slew-root-cause`
(kit `memory/builds/`) — V41's original null, now explained rather than merely cited.
