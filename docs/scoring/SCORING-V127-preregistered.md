# SCORING V127 (was V127) — pre-registered BEFORE the drive, 2026-08-28

🛑 **Written and committed before any V127 flight exists.** Endpoints, bands and decision rules
are fixed here so the result cannot be chosen after seeing the data. Scorer:
`rlog-tools/score/score_v126_rail.py`, whose guard **refuses to score a cache from any other
build** (verified against r24, which returns "CORRECTLY REFUSED").

## What V127 changes

| addr | old | new | what |
|---|---|---|---|
| `0xC640A` | −8192 | **−1966** | the oscillation-branch `Y` for `gp-0x6b26` |
| `0x55DF2` | `9544` | `94DA` | 427 probe source, `gp-0x6ABC` → `gp-0x6B26` |
| `0x55E10` | `a3` | `a2` | packer sar 3 → 2, sized to the ±511 clamp |

Base V124. Cal-only, no code or cave edit. 56/56 assertions, CRC 50/50.
image `706363366c017817e34f6f66ece5ea192ca98787f45e45a21e9c33d9b927ed62` (60/60)

🛑 **V127 (−3277) was superseded before flight and its artifacts deleted**: −3277 still
railed at the detector's arming threshold (682 vs the 511 clamp), so it would have left the
term a Coulomb relay in exactly the state it was built to fix. −1966 gives 409, linear at
80 % of clamp. The builder now enforces this as a hard assertion.

## PRIMARY endpoint — rail duty of `gp-0x6b26`

Engaged, stratified on V107's own speed bins, **bootstrapped over EPISODES, never windows**.

| worst bin | verdict | action |
|---|---|---|
| **≤ 2 %** | **DE-RAILED** — the term is linear, the fix is in force | hold `0xC640A` at −3277 |
| **2–10 %** | **PARTIAL** | the branch is already at −1966; the next lever is the mode record `0xCBE74` |
| **> 10 %** | **STILL RAILING** | go to the mode record `0xCBE74` — the NORMAL LERP rails at mid speed too |

Reference, V107 measured: `<10` 1.68 % · `10–25` **32.32 %** · `24–40` 21.27 % · `40–64` 4.27 %
· `≥65` ≤0.23 %.

⚠ **This is a duty endpoint, not a symptom endpoint.** It says whether the mechanism moved, not
whether the car feels better. **The operator's report is the primary symptom endpoint** — the kit's
own standing rule is *score bands, let the OPERATOR score symptoms*, and the 21–26 Hz instrument
has already been shown not to track what he hears (V122 read "NOT RESOLVED" while he reported a
real improvement).

## SECONDARY — the three complaints, reported by the operator

1. **grinding** — better / same / worse than V122, and at which speeds;
2. **peak-turn oscillation**, hands-off engaged in a slow hard turn — the V122 instance was
   segment 11, 09:15:12, 44 km/h, 7.81 Hz;
3. **LKAS authority** — 🛑 **V127 is the FIRST build since V112 to change authority** (V122 carried
   V112's gain unchanged). Expect ×1.333 at the rail from 6× → 8×, less after the 2.9× efficiency
   fall, so **≈1.1–1.2× in delivered rate**, not 1.33×.

## What will NOT be claimed

- 🛑 **No spectrum of the 427 wire.** 427 is 49.9 Hz ⇒ Nyquist 24.95 Hz; the lane's −3 dB band is
  25–153 Hz. Duty is a level statistic and survives undersampling; a spectrum does not. Confusing
  the two is exactly what voided V107's safety case.
- 🛑 **No open-loop duty prediction, before or after.** V107 predicted ≤1.05 % and measured
  33.49 % — a **32× miss** — because `gp-0x6b26 → aggregator → motor → motor rate → gp-0x6c2c` is
  a closed loop. This build measures; it does not predict.
- 🛑 **No grind-#1 claim from this wire.** Grind #1's band is 21–26 Hz, which straddles Nyquist.
  Grind must be scored from `cs_rate` at 99.8 Hz, or by the operator.

## Confounds stated in advance

- **Route variance is large**: two drives on identical firmware (r22/r23, both V112) differ 2.74×
  at 20–60°, and 6–9 Hz p90 spans 2.909 vs 8.320. A single drive cannot resolve a small effect.
- **V127 changes authority AND the oscillation branch.** They are not separable on one drive. The
  authority change is expected to be felt as *more* assist; the oscillation change as *less*
  ratcheting during hard turns. If both move together, attribution needs the rail-duty endpoint,
  which is why the probe is on the build.
- **The branch only fires when the reversal counter saturates.** If a drive contains no
  oscillation episode, the edit is inert by construction and the rail-duty bins will be near
  zero for a reason that is *not* the fix working. **Check episode count before concluding.**
